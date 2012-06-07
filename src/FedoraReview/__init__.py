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

import subprocess
import logging
from subprocess import call, Popen, PIPE, STDOUT
import os.path
import re
import glob
import requests
import sys
import shlex
import shutil
import tempfile
import rpm
import platform
import StringIO
from textwrap import TextWrapper
import ConfigParser
from urlparse import urlparse

from kitchen.text.converters import to_bytes

from .version import __version__

SECTIONS = ['build', 'changelog', 'check', 'clean', 'description', 'files',
               'install', 'package', 'prep', 'pre', 'post', 'preun', 'postun',
               'trigger', 'triggerin', 'triggerun', 'triggerprein',
               'triggerpostun', 'pretrans', 'posttrans']
SPEC_SECTIONS = re.compile(r"^(\%(" + "|".join(SECTIONS) + "))\s*")
MACROS = re.compile(r"^%(define|global)\s+(\w*)\s+(.*)")
TEST_STATES = {'pending': '[ ]', 'pass': '[x]', 'fail': '[!]', 'na': '[-]'}

LOG_ROOT = 'FedoraReview'

PARSER_SECTION = 'review'
CONFIG_FILE    = '.config/fedora-review/settings'
SYS_PLUGIN_DIR = "/usr/share/fedora-review/plugins:%s"
MY_PLUGIN_DIR  = ".config/fedora-review/plugins"

# see ticket https://fedorahosted.org/FedoraReview/ticket/43
requests.decode_unicode=False

def rpmdev_extract(working_dir, archive, log):
    """
    Unpack archive in working_dir. Returns return value
    from subprocess.call()
    """
    cmd = 'rpmdev-extract -qC ' + working_dir + ' ' + archive
    rc = call(cmd, shell=True)
    if rc != 0:
        log.warn("Cannot unpack "  + archive)
    return rc


def _check_rpmlint_errors(out, log):
    """ Check the rpmlint output, return(ok, errmsg)
    If ok, output is OK and there is 0 warnings/errors
    If not ok, and errmsg!= None there is system errors,
    reflected in errmsg. If not ok and sg == None parsing
    is ok but there are warnings/errors"""

    problems = re.compile('(\d+)\serrors\,\s(\d+)\swarnings')
    lines = out.split('\n')[:-1]
    err_lines = filter( lambda l: l.lower().find('error') != -1, lines)
    if len(err_lines) == 0:
        log.debug('Cannot parse rpmlint output: ' + out )
        return False, 'Cannot parse rpmlint output:'

    res = problems.search(err_lines[-1])
    if res and len(res.groups()) == 2:
        errors, warnings = res.groups()
        if errors == '0' and warnings == '0':
            return True, None
        else:
            return False, None
    else:
        log.debug('Cannot parse rpmlint output: ' + out )
        return False, 'Cannot parse rpmlint output:'


def get_logger():
    return logging.getLogger(LOG_ROOT)


def do_logger_setup(lvl=None):
    ''' Setup Python logging. lvl is a logging.* thing like
    logging.DEBUG. If None, respects FR_LOGLEVEL environment
    variable, defaulting to logging.INFO.
    '''
    msg = None
    if not lvl:
        if 'FR_LOGLEVEL' in os.environ:
            try:
                lvl = eval('logging.' +
                           os.environ['FR_LOGLEVEL'].upper())
            except:
                msg = "Cannot set loglevel from FR_LOGLEVEL"
                lvl = logging.INFO
        else:
            lvl = logging.INFO
    logger = logging.getLogger(LOG_ROOT)
    logger.setLevel(lvl)
    formatter = logging.Formatter('%(message)s', "%H:%M:%S")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.propagate = False
    logger.addHandler(handler)
    if msg:
        get_logger().warning(msg)
    return handler


class FedoraReviewError(Exception):
    """ General Error class for fedora-review. """

    def __init__(self, value):
        """ Instanciante the error. """
        self.value = value

    def __str__(self):
        """ Represent the error. """
        return repr(self.value)



_RPMLINT_SCRIPT="""
mock --shell << 'EOF'
echo 'rpmlint:'
rpmlint @rpm_names@
echo 'rpmlint-done:'
EOF
"""
class _Mock(object):
    """ Some basic operations on the mock chroot env, a singleton. """

    def __init__(self):

    def _get_dir(self, subdir=None):
        p = os.path.join( '/var/lib/mock', Settings.mock_config )
        return os.path.join(p, subdir) if subdir else p

    def get_resultdir(self):
        return self._get_dir('result')

    def get_builddir(self, subdir=None):
        """ Return the directory which corresponds to %_topdir inside
        mock. Optional subdir argument is added to returned path.
        """
        p = self._get_dir('root/builddir/build')
        return os.path.join(p, subdir) if subdir else p

    """  The directory where mock leaves built rpms and logs """
    resultdir=property(get_resultdir)

    """ Mock's %_topdir seen from the outside. """
    topdir = property(lambda self: get_builddir(self))

       self.log = get_logger()

    def _get_dir(self, subdir=None):
        p = os.path.join( '/var/lib/mock', Settings.mock_config )
        return os.path.join(p, subdir) if subdir else p

    def get_resultdir(self):
        return self._get_dir('result')

    def get_builddir(self, subdir=None):
        """ Return the directory which corresponds to %_topdir inside
        mock. Optional subdir argument is added to returned path.
        """
        p = self._get_dir('/root/builddir/build')
        return os.path.join(p, subdir) if subdir else p

    """  The directory where mock leaves built rpms and logs """
    resultdir=property(get_resultdir)

    """ Mock's %_topdir seen from the outside. """
    topdir = property(lambda self: get_builddir(self))

    def install(self, rpm_files):
        """
        Run  'mock install' on a list of files, return None if
        OK, else the stdout+stderr
        """
        cmd = ["mock", "install"]
        cmd.extend(rpm_files)
        try:
            p = Popen(cmd, stdout=PIPE, stderr=STDOUT)
            output, error = p.communicate()
        except OSError as e:
            return output[0]
        return None

    def _run(self, script):
        """ Run a script,  return (ok, output). """
        try:
            p = Popen(script, stdout=PIPE, stderr=STDOUT, shell=True)
            output, error = p.communicate()
        except OSError as e:
            return False, e.strerror
        return True, output

    def rpmlint_rpms(self, rpms):
        """ Install and run rpmlint on  packages,
        return (True,  text) or (False, error_string)"""

        rpms.insert(0, 'rpmlint')
        error =  self.install(rpms)
        if error:
            return False, error
        rpms.pop(0)

        script = _RPMLINT_SCRIPT
        basenames = [ os.path.basename(r) for r in rpms]
        names = [r.rsplit('-', 2)[0] for r in basenames]
        rpm_names = ' '.join(list(set(names)))
        script = script.replace('@rpm_names@', rpm_names)
        ok, output = self._run(script)
        if not ok:
            return False, output + '\n'

        ok, err_msg = _check_rpmlint_errors(output, self.log)
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
        return ok, text

Mock = _Mock()


class _Settings(object):
    """
    FedoraReview singleton Config Setting, based on config file and
    command line options. All config values are accessed as attributes.
    """
    path = MY_PLUGIN_DIR + ":" + os.environ['HOME'] + ":" + SYS_PLUGIN_DIR
    defaults = {
        # review, report & spec editor(default EDITOR env)
        'editor':       '',
        'work_dir':     '.',
        'bz_user':      '',
        'mock_config':  'fedora-rawhide-i386',
        'mock_options': '--no-cleanup-after',
        'ext_dirs':     path
    }

    def __init__(self):
        '''Constructor of the Settings object.
        This instanciate the Settings object and load into the _dict
        attributes the default configuration which each available option.
        '''
        for key,value in self.defaults.iteritems():
            setattr(self, key, value)
        self._dict = self.defaults
        self._load_config(CONFIG_FILE, PARSER_SECTION)

    def _load_config(self, configfile, sec):
        '''Load the configuration in memory.

        :arg configfile, name of the configuration file loaded.
        :arg sec, section of the configuration retrieved.
        '''
        parser = ConfigParser.ConfigParser()
        self.parser = parser
        configfile = os.environ['HOME'] + "/" + configfile
        isNew = self._create_conf()
        parser.read(configfile)
        if not parser.has_section(sec):
            parser.add_section(sec)
        self._populate()
        if isNew:
            self.save_config()

    def _create_conf(self):
        '''Check if the provided configuration file exists, generate the
        folder if it does not and return True or False according to the
        initial check.

        :arg configfile, name of the configuration file looked for.
        '''
        if not os.path.exists(CONFIG_FILE):
            dn = os.path.dirname(CONFIG_FILE)
            if not os.path.exists(dn):
                os.makedirs(dn)
            return True
        return False

    def save_config(self ):
        '''Save the configuration into the specified file.

        :arg configfile, name of the file in which to write the configuration
        :arg parser, ConfigParser object containing the configuration to
        write down.
        '''
        with open(CONFIG_FILE, 'w') as conf:
                self.parser.write(conf)

    def __getitem__(self, key):
        hash = self._get_hash(key)
        if not hash:
            raise KeyError(key)
        return self._dict.get(hash)

    def _populate(self):
        '''Set option values from a INI file section.

        :arg parser: ConfigParser instance (or subclass)
        :arg section: INI file section to read use.
        '''
        if self.parser.has_section(PARSER_SECTION):
            opts = set(self.parser.options(PARSER_SECTION))
        else:
            opts = set()

        for name in self._dict.iterkeys():
            value = None
            if name in opts:
                value = self.parser.get(PARSER_SECTION, name)
                setattr(self, name, value)
                self.parser.set(PARSER_SECTION, name, value)
            else:
                self.parser.set(PARSER_SECTION, name, self._dict[name])

    def add_args(self, args):
        """ Load all command line options in args. """
        dict = vars(args)
        for key, value in dict.iteritems():
            setattr(self, key, value)
            self.parser.set( PARSER_SECTION, key, value)


Settings = _Settings()

class Helpers(object):

    def __init__(self):
        self.work_dir = 'work/'
        self.log = get_logger()
        self.mock_options = Settings.mock_options
        self.rpmlint_output = []

    def set_work_dir(self, work_dir):
        work_dir = os.path.abspath(os.path.expanduser(work_dir))
        if not os.path.exists(work_dir):
            os.makedirs(work_dir)
        if not work_dir[-1] == "/":
            work_dir += '/'
        self.work_dir = work_dir

    def get_mock_dir(self):
        mock_dir = '/var/lib/mock/%s/result' % Settings.mock_config
        return mock_dir

    def _run_cmd(self, cmd):
        self.log.debug('Run command: %s' % cmd)
        cmd = cmd.split(' ')
        try:
            proc = Popen(cmd, stdout=PIPE, stderr=PIPE)
            output, error = proc.communicate()
        except OSError, e:
            print "OSError : %s" % str(e)
        return output

    def _md5sum(self, file):
        ''' get the md5sum for a file

        :arg file: the file to get the the md5sum for
        :return: (md5sum, file) tuple
        '''
        cmd = "md5sum %s" % file
        out = self._run_cmd(cmd)
        lines = out.split(' ', 1)
        if len(lines) == 2:
            return lines[0], lines[1][1:-1]
        else:
            return None, out

    def _get_file(self, link):
        self.log.debug("  --> %s : %s" % (self.work_dir, link))
        url = urlparse(link)
        request = requests.get(link)
        if str(request.status_code).startswith('4'):
            raise FedoraReviewError('Getting error "%s" while trying to download: %s'
                % (request.status_code, link))
        fname = os.path.basename(url.path)
        if os.path.exists(self.work_dir + fname) and Settings.cache:
            return  self.work_dir + fname
        try:
            stream = open(self.work_dir + fname, 'w')
            stream.write(to_bytes(request.content))
            stream.close()
        except IOError, err:
            raise FedoraReviewError('Getting error "%s" while trying to write file: %s'
                % (err, self.work_dir + fname))
        if os.path.exists(self.work_dir + fname):
            return  self.work_dir + fname
        else:
            return None


class Sources(object):
    """ Store Source object for each source in Spec file"""
    def __init__(self):
        self._sources = {}
        self.work_dir = None
        self.log = get_logger()
        self._sources_files = None

    def set_work_dir(self, work_dir):
        self.work_dir = work_dir

    def add(self, tag, source_url):
        """Add a new Source Object based on spec tag and URL to source"""
        if urlparse(source_url)[0] != '':  # This is a URL, Download it
            self.log.info("Downloading (%s): %s" % (tag, source_url))
            source = Source(self)
            source.set_work_dir(self.work_dir)
            source.get_source(source_url )
        else:  # this is a local file in the SRPM
            self.log.info("No upstream for (%s): %s" % (tag, source_url))
            source = Source(self, filename=source_url)
            source.set_work_dir(self.work_dir)
            ## When sources are not remote we need to extract them from
            ## the srpm.
            print 'The source %s in the srpm can not be retrieved. '\
            'This is a corner case not supported yet.' % source_url
            return
        self._sources[tag] = source

    def get(self, tag):
        """ Get a single Source object"""
        if tag in self._sources:
            return self._sources[tag]
        else:
            return None

    def get_all(self):
        """ Get all source objects """
        return [self._sources[s] for s in self._sources]

    def extract_all(self):
        """ Extract all sources which are detected can be extracted based
        on their extension.
        """
        for source in self._sources.values():
            source.extract()

    def extract(self, source_url=None, source_filename=None):
        """ Extract the source specified by its url or filename.
        :arg source_url, the url used in the spec as used in the spec
        :arg souce_filename, the filename of the source as identified
        in the spec.
        """
        if source_url is None and source_filename is None:
            print 'No source set to extract'
        for source in self._sources:
            if source_url and source.URL == source_url:
                source.extract()
            elif source_filename and source.filename == source_filename:
                source.extract()

    def get_files_sources(self):
        """ Return the list of all files found in the sources. """
        if self._sources_files:
            return self._sources_files
        try:
            self.extract_all()
        except  OSError as error:
            print "Source", error
            self._source_files = []
            return []
        sources_files = []
        for source in self._sources.values():
            # If the sources are not extracted then we add the source itself
            if not source.extract_dir:
                self.log.debug('%s cannot be extracted, adding as such \
as sources' % source.filename)
                sources_files.append(source.filename)
            else:
                self.log.debug('Adding files found in %s' % source.filename)
                for root, subFolders, files in os.walk(source.extract_dir):
                    for filename in files:
                        sources_files.append(os.path.join(root, filename))
        self._sources_files = sources_files
        return sources_files


class Source(Helpers):
    def __init__(self, sources, filename=None):
        Helpers.__init__(self)
        self.filename = filename
        self.sources = sources
        self.downloaded = False
        self.URL = None

    def get_source(self, URL):
        self.URL = URL
        self.filename = self._get_file(URL)
        if self.filename and os.path.exists(self.filename):
            self.downloaded = True
            self.extract()

    def check_source_md5(self):
        if self.downloaded:
            self.log.info("Checking source md5 : %s" % self.filename)
            sum, file = self._md5sum(self.filename)
        else:
            sum = "upstream source not found"
        return sum

    def extract(self ):
        """ Extract the sources in the mock chroot so that it can be
        destroy easily by mock. Prebuilt sources are extracted to
        temporary directory in current dir.
        """
        if Settings.prebuilt:
            self.extract_dir = 'review-tmp-src'
            if os.path.exists(self.extract_dir):
                self.log.debug("Clearing temporary source dir " +
                                self.extract_dir)
                shutil.rmtree(self.extract_dir)
                os.mkdir(self.extract_dir)
        else:
            self.extract_dir = Mock.get_builddir('sources')
        self.log.debug("Extracting %s in %s " % (self.filename,
                       self.extract_dir))
        if not os.path.exists(self.extract_dir):
            try:
                os.makedirs(self.extract_dir)
            except IOError, err:
                self.log.debug(err)
                print "Could not generate the folder %s" % self.extract_dir
        rpmdev_extract(self.extract_dir, self.filename)

    def get_source_topdir(self):
        """
        Return the top directory of the unpacked source. Fails for
        archives not including the top directory. FIXME
        """
        if not hasattr(self, 'extract_dir'):
            self.extract()
        topdir = glob.glob(self.extract_dir + '/*')
        if len(topdir) > 1:
              print "Returning illegal topdir. Bad things ahead"

    def extract_gem(self):
        """Every gem contains a data.tar.gz file with the actual sources"""
        gem_extract_dir = os.path.join(self.extract_dir, os.path.basename(self.filename)[0:-4])
        os.makedirs(gem_extract_dir)
        gem_data = tarfile.open(os.path.join(self.extract_dir, 'data.tar.gz'))
        gem_data.extractall(gem_extract_dir)
        gem_data.close()

        return tarfile.TarInfo(name = os.path.basename(self.filename)[0:-4])


class SRPMFile(Helpers):

    def __init__(self, filename, spec=None):
        Helpers.__init__(self)
        self.filename = filename
        self.spec = spec
        self.log = get_logger()
        self.is_build = False
        self.build_failed = False
        self._rpm_files = None

    def unpack(self):
        """ Local unpack using rpm2cpio. """
        if hasattr(self, 'unpacked_src'):
            return;

        wdir = os.path.realpath(os.path.join(Settings.work_dir,
                                             'srpm-unpack'))
        if os.path.exists(wdir):
             shutil.rmtree(wdir)

        os.mkdir(wdir)
        oldpwd = os.getcwd()
        os.chdir(wdir)
        cmd = 'rpm2cpio ' + self.filename + ' | cpio -i --quiet'
        rc = call(cmd, shell=True)
        if rc != 0:
            self.log.warn(
                  "Cannot unpack %s into %s" % (self.filename, wdir))
        else:
            self.unpacked_src = wdir
        os.chdir(oldpwd)

    def extract(self, path):
        """ Extract a named source and return containing directory. """
        filename=os.path.basename(path)
        self.unpack()
        files = glob.glob( self.unpacked_src  + '/*' )
        if not filename in [os.path.basename(f) for f in files]:
            self.log.error(
               'Trying to unpack non-existing source: ' + filename)
            return None
        extract_dir = self.unpacked_src + '/' +  filename  + '-extract'
        if os.path.exists(extract_dir):
            return extract_dir
        else:
            os.mkdir(extract_dir)
        rc = rpmdev_extract(extract_dir,
                            os.path.join(self.unpacked_src, filename),
                            self.log)
        if rc != 0:
            self.log.error( "Cannot unpack " + filename)
            return None
        return extract_dir

    def build(self, force=False, silence=False):
        """ Returns the build status, -1 is the build failed, -2
         reflects prebuilt rpms output code from mock otherwise.

        :kwarg force, boolean to force the mock build even if the
            package was already built.
        :kwarg silence, boolean to set/remove the output from the mock
            build.
        """
        if Settings.prebuilt:
            return -2
        if self.build_failed:
            return -1
        return self.mockbuild(force, silence=silence)

    def mockbuild(self, force=False, silence=False):
        """ Run a mock build against the package.

        :kwarg force, boolean to force the mock build even if the
            package was already built.
        :kwarg silence, boolean to set/remove the output from the mock
            build.
        """
        if not force and (self.is_build or Settings.nobuild):
            return 0
        #print "MOCKBUILD: ", self.is_build, self.nobuild
        self.log.info("Building %s using mock %s" % (
            self.filename, Settings.mock_config))
        cmd = 'mock -r %s  --rebuild %s ' % (
                Settings.mock_config, self.filename)
        if self.log.level == logging.DEBUG:
            cmd = cmd + ' -v '
        if Settings.mock_options:
            cmd = cmd + ' ' + Settings.mock_options
        if silence:
            cmd = cmd + ' 2>&1 | grep "Results and/or logs" '
        self.log.debug('Mock command: %s' % cmd)
        rc = call(cmd, shell=True)
        if rc == 0:
            self.is_build = True
            self.log.info('Build completed ok')
        else:
            self.log.info('Build failed rc = %i ' % rc)
            self.build_failed = True
            raise FedoraReviewError('Mock build failed.')
        return rc

    def get_build_dir(self):
        """ Return the BUILD directory from the mock environment.
        """
        bdir_root = Mock.get_builddir('BUILD')
        for entry in os.listdir(bdir_root):
            if os.path.isdir(bdir_root + entry):
                return bdir_root + entry
        return None

    def check_source_md5(self, path):
        self.unpack()
        filename = os.path.basename(path)
        if not hasattr(self, 'unpacked_src'):
            self.log.warn("check_source_md5: Cannot unpack (?)")
            return "ERROR"
        src_files = glob.glob(self.unpacked_src + '/*')
        if not src_files:
            self.log.warn('No unpacked sources found (!)')
            return "ERROR"
        if not filename in [os.path.basename(f) for f in src_files]:
            self.log.warn('Cannot find source: ' + filename)
            return "ERROR"
        path = os.path.join(self.unpacked_src, filename)
        self.log.debug("Checking md5 for %s" % path)
        sum, file = self._md5sum(path)
        return sum

    def run_rpmlint(self, filenames):
        """ Runs rpmlint against the provided files.

        karg: filenames, list of filenames  to run rpmlint on
        """
        cmd = 'rpmlint -f .rpmlint ' + ' '.join( filenames )
        out = 'Checking: '
        sep = '\n' + ' ' * len( out )
        out += sep.join([os.path.basename(f) for f in filenames])
        out += '\n'
        out += self._run_cmd(cmd)
        out += '\n'
        for line in out.split('\n'):
            if line and len(line) > 0:
                self.rpmlint_output.append(line)
        no_errors, msg  = _check_rpmlint_errors(out, self.log)
        return no_errors, msg if msg else out

    def rpmlint(self):
        """ Runs rpmlint against the file.
        """
        return self.run_rpmlint([self.filename])

    def rpmlint_rpms(self):
        """ Runs rpmlint against the used rpms - prebuilt or built in mock.
        """
        if Settings.prebuilt:
            rpms = glob.glob('*.rpm')
        else:
            rpms = glob.glob(Mock.resultdir + '/*.rpm')
        no_errors, result = self.run_rpmlint(rpms)
        return no_errors, result + '\n'

    def get_used_rpms(self, exclude_pattern=None):
        """ Return list of mock built or prebuilt rpms. """
        if Settings.prebuilt:
            rpms = set( glob.glob('*.rpm'))
        else:
            rpms = set(glob.glob(self.get_mock_dir() + '/*.rpm'))
        if not exclude_pattern:
            return list(rpms)
        matched = filter( lambda s: s.find(exclude_pattern) > 0, rpms)
        rpms = rpms - set(matched)
        return list(rpms)

    def get_files_rpms(self):
        """ Generate the list files contained in RPMs generated by the
        mock build or present using --prebuilt
        """
        if self._rpm_files:
            return self._rpm_files
        if Settings.prebuilt:
            rpms = glob.glob('*.rpm')
            hdr = "Using local rpms: "
            sep = '\n' + ' ' * len(hdr)
            self.log.info(hdr + sep.join(rpms))
        else:
            self.build()
            rpms = glob.glob(Mock.resultdir + '/*.rpm')
        rpm_files = {}
        for rpm in rpms:
            if rpm.endswith('.src.rpm'):
                continue
            cmd = 'rpm -qpl %s' % rpm
            rc = self._run_cmd(cmd)
            rpm_files[os.path.basename(rpm)] = rc.split('\n')
        self._rpm_files = rpm_files
        return rpm_files


class SpecFile(object):
    '''
    Wrapper classes for getting information from a .spec file
    '''
    def __init__(self, filename):
        self._sections = {}
        self._section_list = []
        self.filename = filename
        self.log = get_logger()
        f = None
        try:
            f = open(filename, "r")
            self.lines = f.readlines()
        finally:
            f and f.close()

        ts = rpm.TransactionSet()
        self.spec_obj = ts.parseSpec(self.filename)

        self.name = self.get_from_spec('name')
        self.version = self.get_from_spec('version')
        self.release = self.get_from_spec('release')
        self.process_sections()

    def get_sources(self):
        ''' Get SourceX/PatchX lines with macros resolved '''
        result = {}
        sources = self.spec_obj.sources
        for src in sources:
            (url, num, flags) = src
            if flags & 1:  # rpmspec.h, rpm.org ticket #123
                srctype = "Source"
            else:
                srctype = "Patch"
            tag = '%s%s' % (srctype, num)
            result[tag] = url
        return result

    def has_patches(self):
        '''Returns true if source rpm contains patch files'''
        sources = self.get_sources()
        for source in sources.keys():
            if 'Patch' in source:
                return True
        return False

    def get_macros(self):
        for lin in self.lines:
            res = MACROS.search(lin)
            if res:
                print "macro: %s = %s" % (res.group(2), res.group(3))

    def process_sections(self):
        section_lines = []
        cur_sec = 'main'
        for l in self.lines:
            # check for release
            line = l[:-1]
            res = SPEC_SECTIONS.search(line)
            if res:
                this_sec = line
                # This is a new section, store lines in old one
                if cur_sec != this_sec:
                    self._section_list.append(cur_sec)
                    self._sections[cur_sec] = section_lines
                    section_lines = []
                    cur_sec = this_sec
            else:
                if line and line.strip() != '':
                    section_lines.append(line)
        self._sections[cur_sec] = section_lines
        cur_sec = this_sec
        #self.dump_sections()

    def dump_sections(self, section=None):
        if section:
            sections = self.get_section(section)
            lst = sorted(sections)
        else:
            sections = self._sections
            lst = self._section_list
        for sec in lst:
            print "-->", sec
            for line in sections[sec]:
                print "      %s" % line

    def get_from_spec(self, macro):
        ''' Use rpm for a value for a given tag (macro is resolved)'''
        qf = '%{' + macro.upper() + "}\n"  # The RPM tag to search for
        # get the name
        cmd = ['rpm', '-q', '--qf', qf, '--specfile', self.filename]
                # Run the command
        try:
            proc = Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         env={'LC_ALL':'C'})
            output, error = proc.communicate()
            #print "output : [%s], error : [%s]" % (output, error)
        except OSError, e:
            print "OSError : %s" % str(e)
            return False
        if output:
            rc = output.split("\n")[0]
            #print "RC: ", rc
            if rc == '(none)':
                rc = None
            return rc
        else:
            # rpm dont know the tag, so it is not found
            if 'unknown tag' in error:
                return None
            value = self.find_tag(macro)
            if len(value) > 0:
                return value
            else:
                print "error : [%s]" % (error)
                return False

    def get_rpm_eval(self, filter):
        lines = "\n".join(self.get_section('main')['main'])
        #print lines
        args = ['rpm', '--eval', lines]
        #print len(args), args
        try:
            proc = Popen(args, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, shell=True)
            output, error = proc.communicate()
            print "output : [%s], error : [%s]" % (output, error)
        except OSError, e:
            self.log.error("OSError : %s" % str(e))
            return False
        return output

    def get_expanded(self):
        cmd = ['rpmspec', '-P', self.filename]
        try:
            proc = Popen(cmd, stdin = subprocess.PIPE, stdout = subprocess.PIPE,
                         stderr = subprocess.PIPE)
            output, error = proc.communicate()
            if proc.wait() != 0:
                return None
            return output
        except OSError, e:
            self.log.error("OSError: %s" % str(e))
            return None

    def find_tag(self, tag, section = None, split_tag = True):
        '''
        find at given tag in the spec file.
        Ex. Name:, Version:
        This get the text precise as in is written in the spec,
        no resolved macros
        '''
        # Maybe we can merge the last two regex in one but using
        # (define|global) leads to problem with the res.group(1)
        # so for the time being let's go with 2 regex
        keys = [ re.compile(r"^%s\d*\s*:\s*(.*)" % tag, re.I),
                 re.compile(r"^.define\s*%s\s*(.*)" % tag, re.I),
                 re.compile(r"^.global\s*%s\s*(.*)" % tag, re.I)
               ]
        values = []
        lines = self.lines
        if section:
            lines = self.get_section(section)
            if lines:
                lines = lines[section]
        for line in lines:
            # check for release
            for key in keys:
                res = key.search(line)
                if res:
                    value = res.group(1).strip()
                    value = value.replace(',', ' ')
                    value = value.replace('  ', ' ')
                    if split_tag:
                        values.extend(value.split())
                    else:
                        values.append(value)
        return values

    def get_section(self, section):
        '''
        get the lines in a section in the spec file
        ex. %install, %clean etc
        '''
        results = {}
        for sec in self._section_list:
            if sec.startswith(section):
                results[sec.strip()] = self._sections[sec]
        return results

    def find(self, regex):
        for line in self.lines:
            res = regex.search(line)
            if res:
                return res
        return None

    def find_all(self, regex):
        result = []
        for line in self.lines:
            res = regex.search(line)
            if res:
                result.append(res)
        return result


class Attachment(object):
    """ Text written after the test lines. """

    def __init__(self, header, text, order_hint=10):
        """
        Setup an attachment. Args:
         -  header: short header, < 40 char.
         -  text: printed as-is.
         -  order_hint: Sorting hint, lower hint goes first.
                0 <= order_hint <= 10
        """

        self.header = header
        self.text = text
        self.order_hint = order_hint

    def __str__(self):
        s = self.header + '\n'
        s +=  '-' * len(self.header) + '\n'
        s +=  self.text
        return s

    def __cmp__(self, other):
        if not hasattr(other, 'order_hint'):
            return NotImplemented
        if self.order_hint < other.order_hint:
            return -1
        if self.order_hint > other.order_hint:
            return 1
        return 0


class TestResult(object):

    def __init__(self, name, url, group, deprecates, text, check_type,
                 result, output_extra, attachments=[]):
        self.name = name
        self.url = url
        self.group = group
        self.deprecates = deprecates
        self.text = re.sub("\s+", " ", text)
        self.type = check_type
        self.result = result
        self.output_extra = output_extra
        self.attachments = attachments
        if self.output_extra:
            self.output_extra = re.sub("\s+", " ", self.output_extra)
        self.wrapper = TextWrapper(width=78, subsequent_indent=" " * 5,
                                   break_long_words=False, )

    def get_text(self):
        strbuf = StringIO.StringIO()
        main_lines = self.wrapper.wrap("%s: %s %s" %
                                                     (TEST_STATES[self.result],
                                                      self.type,
                                                      self.text))
        strbuf.write("%s" % '\n'.join(main_lines))
        if self.output_extra and self.output_extra != "":
            strbuf.write("\n")
            extra_lines = self.wrapper.wrap("     Note: %s" %
                                            self.output_extra)
            strbuf.write('\n'.join(extra_lines))

        return strbuf.getvalue()


# vim: set expandtab: ts=4:sw=4:
