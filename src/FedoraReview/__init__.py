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
from subprocess import call, Popen
import os.path
import re
import glob
import requests
import sys
import shlex
import tarfile
import rpm
import platform
import StringIO
from textwrap import TextWrapper
import ConfigParser
from urlparse import urlparse

from .version import __version__

SECTIONS = ['build', 'changelog', 'check', 'clean', 'description', 'files',
               'install', 'package', 'prep', 'pre', 'post', 'preun', 'postun',
               'trigger', 'triggerin', 'triggerun', 'triggerprein',
               'triggerpostun', 'pretrans', 'posttrans']
SPEC_SECTIONS = re.compile(r"^(\%(" + "|".join(SECTIONS) + "))\s*")
MACROS = re.compile(r"^%(define|global)\s+(\w*)\s+(.*)")
TEST_STATES = {'pending': '[ ]', 'pass': '[x]', 'fail': '[!]', 'na': '[-]'}

LOG_ROOT = 'FedoraReview'

class FedoraReviewError(Exception):
    """ General Error class for fedora-review. """

    def __init__(self, value):
        """ Instanciante the error. """
        self.value = value

    def __str__(self):
        """ Represent the error. """
        return repr(self.value)


class Settings(object):
    """ FedoraReview Config Setting"""
    # Editor to use to show review report & spec (default use EDITOR env)
    editor = ''
    # Work dir
    work_dir = '.'
    # Default bugzilla userid
    bz_user = ''
    mock_config = 'fedora-rawhide-i386'
    ext_dirs =  "/usr/share/fedora-review/plugins:%s" % os.environ['HOME'] \
        + "/.config/fedora-review/plugins"

    def __init__(self):
        '''Constructor of the Settings object.
        This instanciate the Settings object and load into the _dict
        attributes the default configuration which each available option.
        '''
        self._dict = {'editor' : self.editor,
                    'work_dir' : self.work_dir,
                    'bz_user' : self.bz_user,
                    'mock_config' : self.mock_config,
                    'ext_dirs' : self.ext_dirs}
        self.load_config('.config/fedora-review/settings', 'review')

    def load_config(self, configfile, sec):
        '''Load the configuration in memory.

        :arg configfile, name of the configuration file loaded.
        :arg sec, section of the configuration retrieved.
        '''
        parser = ConfigParser.ConfigParser()
        configfile = os.environ['HOME'] + "/" + configfile
        isNew = self.create_conf(configfile)
        parser.read(configfile)
        if not parser.has_section(sec):
            parser.add_section(sec)
        self.populate(parser, sec)
        if isNew:
            self.save_config(configfile, parser)

    def create_conf(self, configfile):
        '''Check if the provided configuration file exists, generate the
        folder if it does not and return True or False according to the
        initial check.

        :arg configfile, name of the configuration file looked for.
        '''
        if not os.path.exists(configfile):
            dn = os.path.dirname(configfile)
            if not os.path.exists(dn):
                os.makedirs(dn)
            return True
        return False

    def save_config(self, configfile, parser):
        '''Save the configuration into the specified file.

        :arg configfile, name of the file in which to write the configuration
        :arg parser, ConfigParser object containing the configuration to
        write down.
        '''
        with open(configfile, 'w') as conf:
                parser.write(conf)

    def __getitem__(self, key):
        hash = self._get_hash(key)
        if not hash:
            raise KeyError(key)
        return self._dict.get(hash)

    def populate(self,parser, section):
        '''Set option values from a INI file section.

        :arg parser: ConfigParser instance (or subclass)
        :arg section: INI file section to read use.
        '''
        if parser.has_section(section):
            opts = set(parser.options(section))
        else:
            opts = set()

        for name in self._dict.iterkeys():
            value = None
            if name in opts:
                value = parser.get(section, name)
                setattr(self, name, value)
                parser.set(section, name, value)
            else:
                parser.set(section, name, self._dict[name])

class Helpers(object):

    def __init__(self, cache=False, nobuild=False,
            mock_config=Settings.mock_config):
        self.work_dir = 'work/'
        self.log = get_logger()
        self.cache = cache
        self.nobuild = nobuild
        self.mock_config = mock_config
        self.rpmlint_output = []

    def set_work_dir(self, work_dir):
        work_dir = os.path.abspath(os.path.expanduser(work_dir))
        if not os.path.exists(work_dir):
            os.makedirs(work_dir)
        if not work_dir[-1] == "/":
            work_dir += '/'
        self.work_dir = work_dir

    def get_mock_dir(self):
        mock_dir = '/var/lib/mock/%s/result' % self.mock_config
        return mock_dir

    def _run_cmd(self, cmd):
        self.log.debug('Run command: %s' % cmd)
        cmd = cmd.split(' ')
        try:
            proc = Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
                %(request.status_code, link))
        fname = os.path.basename(url.path)
        if os.path.exists(self.work_dir + fname) and self.cache:
            return  self.work_dir + fname
        try:
            stream = open(self.work_dir + fname, 'w')
            stream.write(request.content)
            stream.close()
        except IOError, err:
            raise FedoraReviewError('Getting error "%s" while trying to write file: %s'
                %(err, self.work_dir + fname))
        if os.path.exists(self.work_dir + fname):
            return  self.work_dir + fname
        else:
            return None


class Sources(object):
    """ Store Source object for each source in Spec file"""
    def __init__(self, cache, mock_config=Settings.mock_config):
        self._sources = {}
        self.cache = cache
        self.mock_config = mock_config
        self.work_dir = None
        self.log = get_logger()
        self._sources_files = None

    def set_work_dir(self, work_dir):
        self.work_dir = work_dir

    def add(self, tag, source_url):
        """Add a new Source Object based on spec tag and URL to source"""
        if urlparse(source_url)[0] != '':  # This is a URL, Download it
            self.log.info("Downloading (%s): %s" % (tag, source_url))
            source = Source(cache=self.cache, mock_config=self.mock_config)
            source.set_work_dir(self.work_dir)
            source.get_source(source_url)
        else:  # this is a local file in the SRPM
            self.log.info("No upstream for (%s): %s" % (tag, source_url))
            source = Source(filename=source_url, cache=self.cache,
            mock_config=self.mock_config)
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
            if os.path.splitext(source.filename)[1] in \
                ['.zip', '.tar', '.gz', '.bz2']:
                if not source.extract_dir:
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
        except tarfile.ReadError, error:
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
    def __init__(self, filename=None, cache=False,
        mock_config=Settings.mock_config):
        Helpers.__init__(self, cache, mock_config=mock_config)
        self.filename = filename
        self.downloaded = False
        self.URL = None
        self.extract_dir = None

    def get_source(self, URL):
        self.URL = URL
        self.filename = self._get_file(URL)
        if self.filename and os.path.exists(self.filename):
            self.downloaded = True

    def check_source_md5(self):
        if self.downloaded:
            self.log.info("Checking source md5 : %s" % self.filename)
            sum, file = self._md5sum(self.filename)
        else:
            sum = "upstream source not found"
        return sum

    def extract(self):
        """ Extract the sources in the mock chroot so that it can be
        destroy easily by mock.
        """
        self.extract_dir = self.get_mock_dir() + \
                "/../root/builddir/build/sources/"
        self.log.debug("Extracting %s in %s " % (self.filename,
                self.extract_dir))
        if not os.path.exists(self.extract_dir):
            try:
                os.makedirs(self.extract_dir)
            except IOError, err:
                self.log.debug(err)
                print "Could not generate the folder %s" % self.extract_dir
        tar = tarfile.open(self.filename)
        tar.extractall(self.extract_dir)
        tar.close()


class SRPMFile(Helpers):
    def __init__(self, filename, cache=False, nobuild=False,
            mock_config=Settings.mock_config, spec=None):
        Helpers.__init__(self, cache, nobuild, mock_config)
        self.filename = filename
        self.spec = spec
        self.log = get_logger()
        self.is_installed = False
        self.is_build = False
        self.build_failed = False
        self._rpm_files = None

    def install(self, wipe=False):
        """ Install the source rpm into the local filesystem.

        :arg wipe, boolean which clean the source directory.
        """
        if wipe:
            sourcedir = self.get_source_dir()
            if sourcedir != "" and sourcedir != "/":  # just to be safe
                call('rm -f %s/*  &>/dev/null' % sourcedir, shell=True)
        call('rpm -ivh %s &>/dev/null' % self.filename, shell=True)
        self.is_installed = True

    def build(self, force=False, silence=False):
        """ Returns the build status, -1 is the build failed, the
        output code from mock otherwise.

        :kwarg force, boolean to force the mock build even if the
            package was already built.
        :kwarg silence, boolean to set/remove the output from the mock
            build.
        """
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
        if not force and (self.is_build or self.nobuild):
            return 0
        #print "MOCKBUILD: ", self.is_build, self.nobuild
        self.log.info("Building %s using mock %s" % (
            self.filename, self.mock_config))
        cmd = 'mock -r %s  --rebuild %s ' % (
                self.mock_config, self.filename)
        if self.log.level == logging.DEBUG:
            cmd = cmd + ' -v '
        if silence:
            cmd = cmd + ' 2>&1 | grep "Results and/or logs" '
        rc = call(cmd,
            shell=True)
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
        mock_dir = self.get_mock_dir()
        bdir_root = '%s/../root/builddir/build/BUILD/' % mock_dir
        for entry in os.listdir(bdir_root):
            if os.path.isdir(bdir_root + entry):
                return bdir_root + entry
        return None

    def get_source_dir(self):
        """ Retrieve the source directory from rpm.
        """
        sourcedir = Popen(["rpm", "-E", '%_sourcedir'],
                stdout=subprocess.PIPE).stdout.read()[:-1]
        # replace %{name} by the specname
        package_name = Popen(["rpm", "-qp", self.filename,
                '--qf', '%{name}'], stdout=subprocess.PIPE).stdout.read()
        sourcedir = sourcedir.replace("%{name}", package_name)
        sourcedir = sourcedir.replace("%name", package_name)
        return sourcedir

    def check_source_md5(self, filename):
        if self.is_installed:
            sourcedir = self.get_source_dir()
            src_files = glob.glob(sourcedir + '/*')
            # src_files = glob.glob(os.path.expanduser('~/rpmbuild/SOURCES/*'))
            if src_files:
                for name in src_files:
                    if filename and \
                    os.path.basename(filename) != os.path.basename(name):
                        continue
                    self.log.debug("Checking md5 for %s" % name)
                    sum, file = self._md5sum(name)
                    return sum
            else:
                print('no sources found in install SRPM')
                return "ERROR"
        else:
            print "SRPM is not installed"
            return "ERROR"

    def _check_errors(self, out):
        problems = re.compile('(\d+)\serrors\,\s(\d+)\swarnings')
        lines = out.split('\n')[:-1]
        last = lines[-1]
        res = problems.search(last)
        if res and len(res.groups()) == 2:
            errors, warnings = res.groups()
            if errors == '0' and warnings == '0':
                return True
        return False

    def run_rpmlint(self, filename):
        """ Runs rpmlint against the provided file.

        karg: filename, the name of the file to run rpmlint on
        """
        cmd = 'rpmlint -f .rpmlint %s' % filename
        sep = "\n"
        result = "\nrpmlint %s\n" % os.path.basename(filename)
        result += sep
        out = self._run_cmd(cmd)
        for line in out.split('\n'):
            if line and not 'specfiles checked' in line:
                self.rpmlint_output.append(line)
        no_errors = self._check_errors(out)
        result += out
        result += sep
        return no_errors, result

    def rpmlint(self):
        """ Runs rpmlint against the file.
        """
        return self.run_rpmlint(self.filename)

    def rpmlint_rpms(self):
        """ Runs rpmlint against the rpm generated by the mock build.
        """
        results = ''
        success = True
        rpms = glob.glob(self.get_mock_dir() + '/*.rpm')
        for rpm in rpms:
            no_errors, result = self.run_rpmlint(rpm)
            if not no_errors:
                success = False
            results += result
        return success, results

    def get_files_rpms(self):
        """ Generate the list files contained in RPMs generated by the
        mock build
        """
        if self._rpm_files:
            return self._rpm_files
        self.build()
        rpms = glob.glob(self.get_mock_dir() + '/*.rpm')
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


class TestResult(object):
    nowrap = ["CheckRpmLint", "CheckSourceMD5"]

    def __init__(self, name, url, group, deprecates, text, check_type,
                 result, output_extra):
        self.name = name
        self.url = url
        self.group = group
        self.deprecates = deprecates
        self.text = re.sub("\s+", " ", text)
        self.type = check_type
        self.result = result
        self.output_extra = output_extra
        if self.output_extra and self.name not in TestResult.nowrap:
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
            if self.name in TestResult.nowrap:
                strbuf.write(self.output_extra)
            else:
                extra_lines = self.wrapper.wrap("     Note: %s" %
                                               self.output_extra)
                strbuf.write('\n'.join(extra_lines))

        return strbuf.getvalue()


def get_logger():
    return logging.getLogger(LOG_ROOT)


def do_logger_setup(logroot=LOG_ROOT, logfmt='%(message)s',
    loglvl=logging.INFO):
    ''' Setup Python logging using a TextViewLogHandler '''
    logger = logging.getLogger(logroot)
    logger.setLevel(loglvl)
    formatter = logging.Formatter(logfmt, "%H:%M:%S")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.propagate = False
    logger.addHandler(handler)
    return handler
