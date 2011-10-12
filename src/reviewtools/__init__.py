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
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
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
import sys
import shlex
import rpm
from yum.config import *
from urlparse import urlparse

SECTIONS = ['build', 'changelog', 'check', 'clean', 'description', 'files',
               'install', 'package', 'prep', 'pre', 'post', 'preun', 'postun',
               'trigger', 'triggerin', 'triggerun', 'triggerprein',
               'triggerpostun', 'pretrans', 'posttrans']
SPEC_SECTIONS = re.compile(r"^(\%(" + "|".join(SECTIONS) + "))\s*")
MACROS = re.compile(r"^%(define|global)\s+(\w*)\s+(.*)")

LOG_ROOT = 'reviewtools'


class Settings(BaseConfig):
    """ FedoraReview Config Setting"""
    # Editor to use to show review report & spec
    editor = Option('/usr/bin/gedit')
    # Work dir
    work_dir = Option('.')
    # Default bugzilla userid
    bz_user = Option('')
    distribution = Option('RAWHIDE')
    mock_dist = Option('rawhide')

    def __init__(self):
        BaseConfig.__init__(self)
        self.load_config('.config/FedoraReview/settings', 'review')

    def load_config(self, configfile, sec):
        parser = ConfigParser()
        configfile = os.environ['HOME'] + "/" + configfile
        isNew = self.create_conf(configfile, sec)
        parser.read(configfile)
        if not parser.has_section(sec):
            parser.add_section(sec)
        self.populate(parser, sec)
        if isNew:
            self.save_config(configfile)

    def create_conf(self, configfile, sec):
        if not os.path.exists(configfile):
            dn = os.path.dirname(configfile)
            if not os.path.exists(dn):
                os.makedirs(dn)
            fd = open(configfile, "w")
            print >> fd, "[%s]" % sec
            fd.close()
            return True
        return False

    def save_config(self, configfile):
        always = tuple([key for key in self.iterkeys()])
        fn = open(configfile, "w")
        self.write(fn, always=always)
        fn.close()


class Helpers(object):

    def __init__(self, cache=False, nobuild=False,
            mock_dist=Settings.mock_dist):
        self.work_dir = 'work/'
        self.log = get_logger()
        self.cache = cache
        self.nobuild = nobuild
        self.mock_dist = mock_dist

    def set_work_dir(self, work_dir):
        work_dir = os.path.abspath(os.path.expanduser(work_dir))
        if not os.path.exists(work_dir):
            os.makedirs(work_dir)
        if not work_dir[-1] == "/":
            work_dir += '/'
        self.work_dir = work_dir

    def _run_cmd(self, cmd):
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
        fname = os.path.basename(url.path)
        if os.path.exists(self.work_dir + fname) and self.cache:
            return  self.work_dir + fname
        call('wget --quiet --tries=1 --read-timeout=90 -O %s \
        --referer=%s %s' % (self.work_dir + fname, link, link), shell=True)
        if os.path.exists(self.work_dir + fname):
            return  self.work_dir + fname
        else:
            return None


class Sources(object):
    """ Store Source object for each source in Spec file"""
    def __init__(self, cache):
        self._sources = {}
        self.cache = cache
        self.work_dir = None
        self.log = get_logger()

    def set_work_dir(self, work_dir):
        self.work_dir = work_dir

    def add(self, tag, source_url):
        """Add a new Source Object based on spec tag and URL to source"""
        if urlparse(source_url)[0] != '':  # This is a URL, Download it
            self.log.info("Downloading (%s): %s" % (tag, source_url))
            source = Source(cache=self.cache)
            source.set_work_dir(self.work_dir)
            source.get_source(source_url)
        else:  # this is a local file in the SRPM
            self.log.info("No upstream for (%s): %s" % (tag, source_url))
            source = Source(filename=source_url, cache=self.cache)
            source.set_work_dir(self.work_dir)
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


class Source(Helpers):
    def __init__(self, filename=None, cache=False):
        Helpers.__init__(self, cache)
        self.filename = filename
        self.downloaded = False
        self.URL = None

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


class SRPMFile(Helpers):
    def __init__(self, filename, cache=False, nobuild=False,
            mock_dist=Settings.mock_dist):
        Helpers.__init__(self, cache, nobuild, mock_dist)
        self.filename = filename
        self.is_installed = False
        self.is_build = False
        self.build_failed = False
        self._rpm_files = None

    def install(self, wipe=False):
        if wipe:
            sourcedir = self.get_source_dir()
            if sourcedir != "" and sourcedir != "/":  # just to be safe
                call('rm -f %s/*  &>/dev/null' % sourcedir, shell=True)
        call('rpm -ivh %s &>/dev/null' % self.filename, shell=True)
        self.is_installed = True

    def build(self, force=False):
        if self.build_failed:
            return -1
        return self.mockbuild(force)

    def mockbuild(self, force=False):
        if not force and (self.is_build or self.nobuild):
            return 0
        #print "MOCKBUILD: ", self.is_build, self.nobuild
        self.log.info("Building %s using mock fedora-%s-i386" % (
            self.filename, self.mock_dist))
        rc = call('mock -r fedora-%s-i386  --rebuild %s' % (
            self.mock_dist, self.filename), shell=True)
        if rc == 0:
            self.is_build = True
            self.log.info("Build completed ok")
        else:
            self.log.info("Build failed rc = %i " % rc)
            self.build_failed = True
        return rc

    def get_mock_dir(self):
        mock_dir = '/var/lib/mock/fedora-%s-i386/result' % self.mock_dist
        return mock_dir

    def get_source_dir(self):
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
        sep = "%s\n" % (80 * "=")
        result = "\nrpmlint %s\n" % os.path.basename(filename)
        result += sep
        out = self._run_cmd(cmd)
        no_errors = self._check_errors(out)
        result += out
        result += sep
        return no_errors, result

    def rpmlint(self):
        return self.run_rpmlint(self.filename)

    def rpmlint_rpms(self):
        sep = "%s\n" % (80 * "=")
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
            proc = Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
            if value:
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
            print "OSError : %s" % str(e)
            return False
        return output

    def find_tag(self, tag):
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
        for line in self.lines:
            # check for release
            for key in keys:
                res = key.search(line)
                if res:
                    value = res.group(1).strip()
                    values.append(value)
        if len(values) == 1:  # this should prevent to break old tests
            return values[0]
        else:
            return values

    def get_section(self, section):
        '''
        get the lines in a section in the spec file
        ex. %install, %clean etc
        '''
        results = {}
        for sec in self._section_list:
            if sec.startswith(section):
                results[sec] = self._sections[sec]
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
