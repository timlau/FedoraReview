#-*- coding: utf-8 -*-

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

from glob import glob
from urlparse import urlparse
from subprocess import call, Popen, PIPE, STDOUT

from helpers import Helpers
from review_dirs import ReviewDirs
from settings import Settings


_RPMLINT_SCRIPT="""
mock  @config@ --shell << 'EOF'
echo 'rpmlint:'
rpmlint @rpm_names@
echo 'rpmlint-done:'
EOF
"""

class _Mock(Helpers):
    """ Some basic operations on the mock chroot env, a singleton. """

    def __init__(self):
        Helpers.__init__(self)

    def _get_root(self):
        config = 'default'
        if Settings.mock_config:
            config  = Settings.mock_config
        mockdir = Settings.configdir if Settings.configdir \
            else '/etc/mock'
        path = os.path.join(mockdir , config + '.cfg')

        config_opts = {}
        with open(path) as f:
            config = [line for line in f.readlines() if \
                      line.find("config_opts['root']") >= 0]
        exec config[0]
        self.mock_root = config_opts['root']
        if Settings.uniqueext:
            self.mock_root += Settings.uniqueext

    def _get_dir(self, subdir=None):
        if not hasattr(self, 'mock_root'):
            self._get_root()
        p = os.path.join( '/var/lib/mock', self.mock_root )
        p = os.path.join(p, subdir) if subdir else p
        if not os.path.exists(p):
            os.makedirs(p)
        return p

    def reset(self):
        """ Clear all persistent state. """
        if hasattr(self, 'mock_root'):
            delattr(self, 'mock_root')

    def get_resultdir(self):
        if Settings.resultdir:
            return Settings.resultdir
        else:
            return ReviewDirs.results

    def get_builddir(self, subdir=None):
        """ Return the directory which corresponds to %_topdir inside
        mock. Optional subdir argument is added to returned path.
        """
        p = self._get_dir('root/builddir/build')
        return os.path.join(p, subdir) if subdir else p

    """ The directory where mock leaves built rpms and logs """
    resultdir = property(get_resultdir)

    """ Mock's %_topdir seen from the outside. """
    topdir = property(lambda self: get_builddir(self))

    def _mock_cmd(self):
        cmd = ["mock"]
        if Settings.mock_config:
             cmd.extend(['-r', Settings.mock_config])
        cmd.extend(self.get_mock_options().split())
        return cmd

    def _run_cmd(self, cmd, header='Mock'):

        def log_text(out, err):
           return  header + " output: " + str(out) + ' ' + str(err)

        self.log.debug(header + ' command: ' + ', '.join(cmd))
        try:
            p = Popen(cmd, stdout=PIPE, stderr=STDOUT)
            output, error = p.communicate()
            logging.debug(log_text(output, error), exc_info=True)
        except OSError as e:
            logging.warning(log_text(output, error), exc_info=True)
            return str(output)
        if p.returncode != 0:
            logging.warning(header + " command returned error code %i",
                            p.returncode)
        return None if p.returncode == 0 else str(output)

    def _run_script(self, script):
        """ Run a script,  return (ok, output). """
        try:
            p = Popen(script, stdout=PIPE, stderr=STDOUT, shell=True)
            output, error = p.communicate()
        except OSError as e:
            return False, e.strerror
        return True, output

    def _clear_rpm_db(self):
        """ mock install uses host's yum -> bad rpm database. """
        cmd = self._mock_cmd()
        cmd.extend(['--shell', 'rm -f /var/lib/rpm/__db*'])
        self._run_cmd(cmd)

    def _mock_cmd(self):
        cmd = ["mock"]
        if Settings.mock_config:
             cmd.extend(['-r', Settings.mock_config])
        cmd.extend(self.get_mock_options().split())
        return cmd

    def get_mock_options(self):
        """ --mock-config option, with a guaranteed ---'resultdir' part
        """
        opt = Settings.mock_options
        if not opt:
            opt = ''
        if not 'resultdir' in opt:
            opt += ' --resultdir=' + ReviewDirs.results + ' '
        return opt

    def is_installed(self, package):
        cmd = self._mock_cmd()
        cmd.append('--shell')
        cmd.append('"rpm -q ' + package + '" &>/dev/null' )
        cmd = ' '.join(cmd)
        rc = call(cmd, shell=True)
        self.log.debug('is_installed: Tested ' + package +
                        ', result: ' + str(rc))
        return rc == 0

    def rpmbuild_bp(self, srpm_file):
        """ Try to rebuild the sources from srpm. """

        cmd = self._mock_cmd()
        cmd.append('--copyin')
        cmd.append(srpm_file)
        cmd.append(os.path.basename(srpm_file))
        errmsg = self._run_cmd(cmd)
        if  errmsg:
             self.log.warning("Cannot run mock --copyin: " + errmsg)
             return errmsg
        cmd = self._mock_cmd()
        cmd.append('--shell')
        cmd.append('rpm -i '+ os.path.basename(srpm_file))
        errmsg = self._run_cmd(cmd)
        if  errmsg:
             self.log.warning("Cannot run mock install src: " + errmsg)
             return errmsg
        cmd = self._mock_cmd()
        cmd.append('--shell')
        cmd.append('rpmbuild --nodeps -bp /builddir/build/SPECS/*spec')
        errmsg = self._run_cmd(cmd)
        if  errmsg:
             self.log.warning("Cannot run mock --shell rpmbuild -bp: "
                              + errmsg)
             return errmsg
        return None

    def install(self, packages):
        """
        Run  'mock install' on a list of files or packages,
        return None if OK, else the stdout+stderr
        """

        def log_text(out, err):
           return  "Install output: " + str(out) + ' ' + str(err)

        def is_not_installed(package):
            p = package
            if os.path.exists(p):
                p = os.path.basename(p).rsplit('-',2)[0]
            if self.is_installed(p):
                self.log.debug('Skipping already installed: ' + p)
                return False
            return True

        rpms = filter(is_not_installed, packages)
        if len(rpms) == 0:
            return
        self._clear_rpm_db()

        cmd = self._mock_cmd()
        cmd.append("install")
        cmd.extend(rpms)
        return self._run_cmd(cmd, 'Install')


    def init(self):
        """ Run a mock --init command. """
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

        error =  self.install(['rpmlint'])
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
        ok, output = self._run_script(script)
        self.log.debug( "Script output: " + output)
        if not ok:
            return False, output + '\n'
        ok, err_msg = self.check_rpmlint_errors(output, self.log)
        if err_msg:
            return False, err_msg

        lines = output.split('\n')
        l = ''
        while not l.startswith('rpmlint:') and len(lines) > 0:
            l = lines.pop(0)
        text = ''
        for l in lines:
            if l.startswith('<mock-'):
                l=l[l.find('#'):]
            if l.startswith('rpmlint-done:'):
                break
            text += l + '\n'
        with open('rpmlint.txt', 'a') as f:
            f.write(text)
        return ok, text

    def have_cache_for(self, name):
        ''' Return true if there is at least one srpm and one rpm in
        resultdir, prefixed with the given name
        '''
        path = self.get_resultdir()
        if len(glob(os.path.join(path, name + '*.src.rpm'))) == 0:
             return False
        return len(glob(os.path.join(path, name +'*.rpm'))) >= 2

    def builddir_cleanup(self):
        ''' Remove broken symlinks left by mock command. '''
        paths = glob(os.path.join(self.get_builddir('BUILD'), '*'))
        for p in paths:
           try:
              os.stat(p)
           except:
              try:
                  os.lstat(p)
                  os.unlink(p)
              except:
                   pass


Mock = _Mock()

# vim: set expandtab: ts=4:sw=4:
