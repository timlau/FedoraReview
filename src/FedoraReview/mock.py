# -*- coding: utf-8 -*-

#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# (C) 2011 - Tim Lauridsen <timlau@fedoraproject.org>

'''
Tools for helping Fedora package reviewers
'''

import logging
import os
import os.path
import re

from glob import glob
from subprocess import call, Popen, PIPE, STDOUT, CalledProcessError

try:
    from subprocess import check_output          # pylint: disable=E0611
except ImportError:
    from FedoraReview.el_compat import check_output

from helpers_mixin import HelpersMixin
from review_dirs import ReviewDirs
from settings import Settings
from review_error import ReviewError


_RPMLINT_SCRIPT = " mock  @config@ --chroot " \
    """ "echo 'rpmlint:'; rpmlint @rpm_names@; echo 'rpmlint-done:'" """


def _run_script(script):
    """ Run a script,  return (ok, output). """
    try:
        p = Popen(script, stdout=PIPE, stderr=STDOUT, shell=True)
        output, error = p.communicate()
    except OSError as e:
        return False, e.strerror + ' stderr: ' + error
    return True, output


def _get_tag(paths):
    ''' Return common disttag from prebuilt files, possibly "" '''
    if not paths:
        return ''
    releases = [p.rsplit('-', 2)[2] for p in paths]
    releases = [r.rsplit('.', 2)[0] for r in releases]
    if not len(set(releases)) == 1:
        return ""
    match = re.search('(fc|el)[0-9][0-9]', releases[0])
    return match.group() if match else ''


def _get_tag_from_flags(self, flags):
    ''' Retrieve disttag from user defined flag value. '''
    if flags['DISTTAG']:
        self.log.info("Using disttag from DISTTAG flag.")
        return flags['DISTTAG'].value
    self.log.warning('No disttag found in prebuilt packages')
    self.log.info('Use --define DISTTAG to set proper dist.'
                  ' e. g. --define DISTTAG fc21.')
    raise ReviewError('No disttag in package and no DISTTAG flag.'
                      ' Use --define DISTTAG to set proper dist'
                      ' e. g., --define DISTTAG=fc21.')


def _add_disttag_macros(macros, tag):
    ''' Add macros derived from disttag. '''
    if tag.startswith('el'):
        macros['%epel'] = tag[2:]
        macros['%fedora'] = '%fedora'
    else:
        macros['%fedora'] = tag[2:]
        macros['%epel'] = '%epel'
    macros['%dist'] = '.' + tag
    return macros


def _add_buildarch_macros(macros, paths):
    ''' Add macros derived from buildarch. '''
    if not paths:
        return '', macros
    arches = [p.rsplit('.', 2)[1] for p in paths]
    if set(arches) == set(['noarch']):
        buildarch = 'noarch'
    else:
        buildarch = [a for a in arches if a is not 'noarch'][0]
    macros['%buildarch'] = buildarch
    if buildarch == 'x86_64':
        macros['%_libdir'] = '/usr/lib64'
        macros['%_isa'] = '(x86-64)'
    else:
        macros['%_libdir'] = '/usr/lib'
        macros['%_isa'] = '(x86-32)'
    return buildarch, macros


class _Mock(HelpersMixin):
    """ Some basic operations on the mock chroot env, a singleton. """
    # pylint: disable=R0904

    def __init__(self):
        HelpersMixin.__init__(self)
        self.log = Settings.get_logger()
        self.build_failed = None
        self.mock_root = None
        self._rpmlint_output = None
        self._topdir = None
        self._macros = None

    def _get_default_macros(self):
        ''' Evaluate macros using rpm in mock. '''
        tags = '%dist %fedora %epel %buildarch %_libdir %_isa %arch'
        macros = {}
        values = self._rpm_eval(tags).split()
        taglist = tags.split()
        for i in range(0, len(taglist)):
            macros[taglist[i]] = values[i]
        return macros

    def _get_prebuilt_macros(self, spec, flags):
        ''' Evaluate macros based on prebuilt packages (#208).'''

        paths = self.get_package_rpm_paths(spec)
        tag = _get_tag(paths)
        if not tag.startswith('fc') and not tag.startswith('el'):
            tag = _get_tag_from_flags(self, flags)
        macros = _add_disttag_macros({}, tag)
        buildarch, macros = _add_buildarch_macros(macros, paths)
        try:
            _arch = check_output('rpm --eval %_arch'.split()).strip()
        except CalledProcessError:
            raise ReviewError("Can't evaluate 'rpm --eval %_arch")
        if buildarch is 'x86_64' and _arch is not 'x86_64':
            raise ReviewError("Can't build x86_64 on i86 host")
        return macros

    def _get_root(self):
        ''' Return mock's root according to Settings. '''
        config = 'default'
        if Settings.mock_config:
            config = Settings.mock_config
        mockdir = Settings.configdir if Settings.configdir \
            else '/etc/mock'
        path = os.path.join(mockdir, config + '.cfg')

        config_opts = {}
        with open(path) as f:
            config = [line for line in f.readlines() if
                      line.find("config_opts['root']") >= 0]
        exec config[0]                           # pylint: disable=W0122
        self.mock_root = config_opts['root']
        if Settings.uniqueext:
            self.mock_root += Settings.uniqueext

        if 'rawhide' not in self.mock_root:
            self.log.info('WARNING: Probably non-rawhide buildroot used. ' +
                          'Rawhide should be used for most package reviews')

    def _get_dir(self, subdir=None):
        ''' Return a directory under root, try to create if non-existing. '''
        if not self.mock_root:
            self._get_root()
        p = os.path.join('/var/lib/mock', self.mock_root)
        p = os.path.join(p, subdir) if subdir else p
        if not os.path.exists(p):
            try:
                os.makedirs(p)
            except OSError:
                pass
        return p

    def _get_rpmlint_output(self):
        ''' Return output from last rpmlint, list of lines. '''
        if not self._rpmlint_output:
            if os.path.exists('rpmlint.txt'):
                with open('rpmlint.txt') as f:
                    self._rpmlint_output = f.readlines()
        return self._rpmlint_output

    def _mock_cmd(self):
        ''' Return mock +  default options, a list of strings. '''
        cmd = ["mock"]
        if Settings.mock_config:
            cmd.extend(['-r', Settings.mock_config])
        cmd.extend(self.get_mock_options().split())
        return cmd

    def _run_cmd(self, cmd, header='Mock'):

        def log_text(out, err):
            ''' Format stdout + stderr. '''
            return header + " output: " + str(out) + ' ' + str(err)

        self.log.debug(header + ' command: ' + ', '.join(cmd))
        try:
            p = Popen(cmd, stdout=PIPE, stderr=STDOUT)
            output, error = p.communicate()
            logging.debug(log_text(output, error), exc_info=True)
        except OSError:
            logging.error("Command failed", exc_info=True)
            return "Command utterly failed. See logs for details"
        if p.returncode != 0:
            logging.info(header + " command returned error code %i",
                         p.returncode)
        return None if p.returncode == 0 else str(output)

    def _get_topdir(self):
        ''' Update _topdir to reflect %_topdir in current mock config. '''
        if self._topdir:
            return
        cmd = self._mock_cmd()
        cmd.extend(['-q', '--chroot', '--', 'rpm --eval %_topdir'])
        try:
            self._topdir = check_output(cmd).strip()
            self.log.debug("_topdir: " + str(self._topdir))
        except (CalledProcessError, OSError):
            self.log.info("Cannot evaluate %topdir in mock, using"
                          " hardcoded /builddir/build")
            self._topdir = '/builddir/build'

    def _clear_rpm_db(self):
        """ Mock install uses host's yum -> bad rpm database. """
        cmd = self._mock_cmd()
        cmd.extend(['--shell', "'rm -f /var/lib/rpm/__db*'"])
        self._run_cmd(cmd)

    def _get_rpm_paths(self, pattern):
        ''' Return paths matching a rpm name pattern. '''
        if Settings.prebuilt:
            paths = glob(os.path.join(ReviewDirs.startdir, pattern))
        else:
            paths = glob(os.path.join(self.get_resultdir(), pattern))
        return paths

    def _rpm_eval(self, arg):
        ''' Run rpm --eval <arg> inside mock, return output. '''
        cmd = self._mock_cmd()
        cmd.extend(['--quiet', '--chroot', '--', 'rpm --eval "' + arg + '"'])
        return check_output(cmd).decode('utf-8').strip()

# Last (cached?) output from rpmlint, list of lines.
    rpmlint_output = property(_get_rpmlint_output)

    # The directory where mock leaves built rpms and logs
    resultdir = property(lambda self: self.get_resultdir())

    # Mock's %_topdir seen from the outside.
    topdir = property(lambda self: self.get_builddir())

    @property
    def buildroot(self):
        ''' Return path to current buildroot' '''
        if not self.mock_root:
            self._get_root()
        return self.mock_root

    def reset(self):
        """ Clear all persistent state. """
        if self.mock_root:
            self.mock_root = None

    def get_resultdir(self):                     # pylint: disable=R0201
        ''' Return resultdir used by mock. '''
        if Settings.resultdir:
            return Settings.resultdir
        else:
            return ReviewDirs.results

    def get_package_rpm_path(self, nvr):
        '''
        Return path to generated pkg_name rpm, throws ReviewError
        on missing or multiple matches. Argument should have
        have name, version and release attributes.
        '''
        pattern = '%s-%s*' % (nvr.name, nvr.version)
        paths = self._get_rpm_paths(pattern)
        paths = filter(lambda p: p.endswith('.rpm')
                       and not p.endswith('.src.rpm'), paths)
        if len(paths) == 0:
            raise ReviewError('No built package found for ' + nvr.name)
        elif len(paths) > 1:
            raise ReviewError('Multiple packages found for ' + nvr.name)
        else:
            return paths[0]

    def get_package_rpm_paths(self, spec, with_srpm=False):
        '''
        Return a list of paths to binary rpms corresponding to
        the packages generated by given spec.
        '''

        def get_package_srpm_path(spec):
            ''' Return path to srpm given a spec. '''
            pattern = '*%s-%s*' % (spec.name, spec.version)
            paths = self._get_rpm_paths(pattern)
            paths = [p for p in paths if p.endswith('.src.rpm')]
            if len(paths) == 0:
                raise ReviewError('No srpm found for ' + spec.name)
            elif len(paths) > 1:
                raise ReviewError('Multiple srpms found for ' + spec.name)
            else:
                return paths[0]

        result = []
        for pkg in spec.packages:
            nvr = spec.get_package_nvr(pkg)
            result.append(self.get_package_rpm_path(nvr))
        if with_srpm:
            result.append(get_package_srpm_path(spec))
        return result

    def get_package_debuginfo_paths(self, nvr):
        ''' Return paths to debuginfo rpms for given nvr.  '''
        pattern = '%s-*debuginfo*-%s-*' % (nvr.name, nvr.version)
        return self._get_rpm_paths(pattern)

    def get_builddir(self, subdir=None):
        """ Return the directory which corresponds to %_topdir inside
        mock. Optional subdir argument is added to returned path.
        """
        self._get_topdir()
        p = self._get_dir(os.path.join('root', self._topdir[1:]))
        return os.path.join(p, subdir) if subdir else p

    def get_macro(self, macro, spec, flags):
        ''' Return value of one of the system-defined rpm macros. '''
        if not self._macros:
            if Settings.prebuilt:
                self._macros = self._get_prebuilt_macros(spec, flags)
            else:
                self._macros = self._get_default_macros()
        key = macro if macro.startswith('%') else '%' + macro
        return self._macros[key] if key in self._macros else macro

    @staticmethod
    def get_mock_options():
        """ --mock-config option, with a guaranteed ---'resultdir' part
        """
        if not hasattr(Settings, 'mock_options'):
            return ''
        opt = Settings.mock_options
        if not opt:
            opt = ''
        if 'resultdir' not in opt:
            opt += ' --resultdir=' + ReviewDirs.results + ' '
        return opt

    def clear_builddir(self):
        ''' Remove all sources installed in BUILD. '''
        cmd = self._mock_cmd()
        cmd += ['--chroot', '--']
        cmd.append('rm -rf $(rpm --eval %_builddir)/*')
        errmsg = self._run_cmd(cmd)
        if errmsg:
            self.log.debug('Cannot clear build area: ' + errmsg +
                           ' (ignored)')
        return None

    @staticmethod
    def is_available():
        ''' Test if mock command is installed and usable. '''
        try:
            check_output(['mock', '--version'])
            return True
        except (CalledProcessError, OSError):
            return False

    def is_installed(self, package):
        ''' Return true iff package is installed in mock chroot. '''
        cmd = self._mock_cmd()
        cmd += ('--chroot', '--')
        cmd.append('"rpm -q ' + package + '" &>/dev/null')
        cmd = ' '.join(cmd)
        rc = call(cmd, shell=True)
        self.log.debug('is_installed: Tested ' + package +
                       ', result: ' + str(rc))
        return rc == 0

    def rpmbuild_bp(self, srpm):
        """ Try to rebuild the sources from srpm. """

        cmd = self._mock_cmd()
        cmd.append('--copyin')
        cmd.append(srpm.filename)
        cmd.append(os.path.basename(srpm.filename))
        errmsg = self._run_cmd(cmd)
        if errmsg:
            self.log.warning("Cannot run mock --copyin: " + errmsg)
            return errmsg
        cmd = self._mock_cmd()
        cmd += ['--chroot', '--']
        script = 'rpm -i ' + os.path.basename(srpm.filename) + '; '
        script += 'rpmbuild --nodeps -bp $(rpm --eval %_specdir)/' \
                  + srpm.name + '.spec;'
        script += 'chmod -R  go+r  $(rpm --eval %_builddir)/* || :'
        cmd.append(script)
        errmsg = self._run_cmd(cmd)
        if errmsg:
            self.log.warning("Cannot run mock --chroot rpmbuild -bp: "
                             + errmsg)
            return errmsg
        return None

    def build(self, filename):
        """
        Run a mock build against the srpm filename.
        Raises ReviewError on build errors, return
        nothing.
        """
        self.clear_builddir()
        cmd = ' '.join(self._mock_cmd())
        if Settings.log_level > logging.INFO:
            cmd += ' -q'
        cmd += ' --rebuild'
        cmd += ' ' + filename + ' 2>&1 | tee build.log'
        if not Settings.verbose and ' -q' not in cmd:
            cmd += ' | egrep "Results and/or logs|ERROR" '
        self.log.debug('Build command: %s' % cmd)
        rc = call(cmd, shell=True)
        self.builddir_cleanup()
        rc = str(rc)
        try:
            with open('build.log') as f:
                log = '\n'.join(f.readlines())
                if 'ERROR' in log:
                    rc = 'Build error(s)'
        except IOError:
            rc = "Can't open logfile"
        if rc == '0':
            self.log.info('Build completed')
            return None
        else:
            self.log.debug('Build failed rc = ' + rc)
            error = ReviewError('mock build failed, see ' + self.resultdir
                                + '/build.log')
            error.show_logs = False
            raise error

    def install(self, packages):
        """
        Run  'mock install' on a list of files or packages,
        return None if OK, else the stdout+stderr
        """

        def log_text(out, err):                  # pylint: disable=W0612
            ''' Log message + default prefix. '''
            return "Install output: " + str(out) + ' ' + str(err)

        def is_not_installed(package):
            ''' Test if package (path or name) isn't installed. '''
            p = package
            if os.path.exists(p):
                p = os.path.basename(p).rsplit('-', 2)[0]
            if self.is_installed(p):
                self.log.debug('Skipping already installed: ' + p)
                return False
            return True

        cmd = self._mock_cmd()
        cmd.append('--init')
        self._run_cmd(cmd, '--init')
        cmd = self._mock_cmd()
        rpms = filter(is_not_installed, packages)
        if len(rpms) == 0:
            return
        self._clear_rpm_db()

        cmd = self._mock_cmd()
        cmd.append("install")
        cmd.extend(rpms)
        return self._run_cmd(cmd, 'Install')

    def init(self, force=False):
        """ Run a mock --init command. """
        if not force:
            try:
                self._rpm_eval('%{_libdir}')
                self.log.debug("Avoiding init of working mock root")
                return
            except (CalledProcessError, OSError):
                pass
            self.log.info("Re-initializing mock build root")
        cmd = ["mock"]
        if hasattr(Settings, 'mock_config') and Settings.mock_config:
            cmd.extend(['-r', Settings.mock_config])
        for option in self.get_mock_options().split():
            if option.startswith('--uniqueext'):
                cmd.append(option)
            if option.startswith('--configdir'):
                cmd.append(option)
        cmd.append('--init')
        self._run_cmd(cmd, 'Init')

    def rpmlint_rpms(self, rpms):
        """ Install and run rpmlint on  packages,
        Requires packages already installed.
        Return (True,  text) or (False, error_string)"""

        def filter_output(output):
            ''' Return part of output to be displayed. '''
            lines = output.split('\n')
            l = ''
            while not l.startswith('rpmlint:') and len(lines) > 0:
                l = lines.pop(0)
            text = ''
            for l in lines:
                if l.startswith('<mock-'):
                    l = l[l.find('#'):]
                if l.startswith('rpmlint-done:'):
                    break
                text += l + '\n'
            return text

        error = self.install(['rpmlint'])
        if error:
            return False, error

        script = _RPMLINT_SCRIPT
        basenames = [os.path.basename(r) for r in rpms]
        names = [r.rsplit('-', 2)[0] for r in basenames]
        rpm_names = ' '.join(list(set(names)))

        config = ''
        if Settings.mock_config:
            config = '-r ' + Settings.mock_config
        script = script.replace('@config@', config)
        script = script.replace('@rpm_names@', rpm_names)
        ok, output = _run_script(script)
        self.log.debug("Script output: " + output)
        if not ok:
            return False, output + '\n'
        ok, err_msg = self.check_rpmlint_errors(output, self.log)
        if err_msg:
            return False, err_msg
        text = filter_output(output)
        self._rpmlint_output = text.split('\n')
        return ok, text

    def have_cache_for(self, spec):
        ''' True if all binary rpms for package are in resultdir. '''
        for p in self.get_package_rpm_paths(spec):
            if not os.path.exists(p):
                return False
        return True

    def builddir_cleanup(self):
        ''' Remove broken symlinks left by mock command. '''
        paths = glob(os.path.join(self.get_builddir('BUILD'), '*'))
        for p in paths:
            if not os.path.exists(p) and os.path.lexists(p):
                os.unlink(p)


Mock = _Mock()

# vim: set expandtab ts=4 sw=4:
