#!/usr/bin/python -tt
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
from urlparse import urlparse
import os.path
import re
import glob
import sys
import shlex
import rpm


SECTIONS = ['build', 'changelog', 'check', 'clean', 'description', 'files',
               'install', 'package', 'prep', 'pre', 'post', 'preun', 'postun',
               'trigger', 'triggerin', 'triggerun', 'triggerprein',
               'triggerpostun', 'pretrans', 'posttrans']               
SPEC_SECTIONS = re.compile(r"^(\%("+"|".join(SECTIONS)+"))\s*")
MACROS = re.compile(r"^%(define|global)\s+(\w*)\s+(.*)")

LOG_ROOT = 'reviewtools'

class Helpers:

    def __init__(self):
        self.work_dir = 'work/'
        
    def set_work_dir(self,work_dir):
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
        lines = out.split(' ',1)
        if len(lines) == 2:
            return lines[0], lines[1][1:-1]
        else:
            return None,out

    def _get_file(self, link):
        url = urlparse(link)
        fname = os.path.basename(url.path)
        call('wget --quiet --tries=1 --read-timeout=90 -O %s --referer=%s %s' % (self.work_dir+fname, link, link) , shell=True)
        if os.path.exists(self.work_dir+fname):
            return  self.work_dir+fname
        else:
            return None    
            
class Source(Helpers) :
    def __init__(self,filename=None):
        Helpers.__init__(self)
        self.filename = filename
            
    def get_source(self, URL):
        self.filename = self._get_file(URL)
        
    def check_source_md5(self):
        sum,file = self._md5sum(self.filename)      
        return sum



class SRPMFile(Helpers) :
    def __init__(self,filename):
        Helpers.__init__(self)
        self.filename = filename
        self.is_installed = False
        self.is_build = False
        
    def install(self, wipe = True):
        if wipe:
            call('rpmdev-wipetree &>/dev/null', shell=True)
        call('rpm -ivh %s &>/dev/null' % self.filename, shell=True)
        self.is_installed = True
        
    def build(self, force = False):
        if not force and self.is_build:
            return 0
        call('rpmdev-wipetree &>/dev/null',shell = True)
        call('sudo yum-builddep -y %s &>yum.log' % self.filename, shell = True)
        rc = call('rpmbuild --rebuild %s &>build.log' % self.filename, shell = True)
        if rc == 0:
            self.is_build = True
        return rc
        
    def check_source_md5(self):
        if self.is_installed:
            src_files = glob.glob(os.path.expanduser('~/rpmbuild/SOURCES/*'))
            if src_files:
                src = src_files[0]         
                sum,file = self._md5sum(src)    
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

    def rpmlint(self):
        cmd = 'rpmlint %s' % self.filename
        sep = "%s\n" % (80*"=")
        result = "\nrpmlint %s\n" % os.path.basename(self.filename)
        result += sep
        out = self._run_cmd(cmd)   
        no_errors = self._check_errors(out)        
        result += out 
        result += sep
        return no_errors,result
        
    def rpmlint_rpms(self):
        sep = "%s\n" % (80*"=")
        result = ''
        success = True
        self.build()
        rpms = glob.glob(os.path.expanduser('~/rpmbuild/RPMS/*/*.rpm'))
        for rpm in rpms:
            cmd = 'rpmlint %s' % rpm
            result += "\nrpmlint %s\n" % os.path.basename(rpm)
            result += sep
            rc = self._run_cmd(cmd)           
            no_errors = self._check_errors(rc)
            if not no_errors:
                success = False      
            result += rc
            result += sep
        return success, result
        
        
class SpecFile:
    '''
    Wrapper classes for getting information from a .spec file
    '''
    def __init__(self, filename):
        self._sections = {}
        self._section_list = []
        self.filename = filename
        f = None
        try:
             f = open(filename,"r")
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
            if flags & 1: # rpmspec.h, rpm.org ticket #123
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
                print "macro: %s = %s" %(res.group(2),res.group(3))
            
              
    def process_sections(self):
        section_lines = []
        cur_sec = 'main'
        for l in self.lines:
            # check for release
            line = l[:-1] 
            res = SPEC_SECTIONS.search(line)
            if res:
                this_sec = line
                if cur_sec != this_sec: # This is a new section, store lines in old one
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
        
    def dump_sections(self, section = None):
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
        qf = '%{' + macro.upper() + "}\n" # The RPM tag to search for
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
            if 'unknown tag' in error: # rpm dont know the tag, so it is not found
                return None
            value = self.find_tag(macro)
            if value:
                return value
            else:
                print "error : [%s]" % ( error)
                return False
            
    def get_rpm_eval(self,filter):
        lines = "\n".join(self.get_section('main')['main'])
        #print lines
        args = ['rpm','--eval', lines]
        print len(args), args
        try:
            proc = Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
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
        This get the text precise as in is written in the spec, no resolved macros
        '''
        key = re.compile(r"^%s\d*\s*:\s*(.*)" % tag, re.I)
        value = None
        for line in self.lines:
            # check for release
            res = key.search(line)
            if res:
                value = res.group(1)
                break
        return value
    
    def get_section(self,section):
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

def get_logger():
    return logging.getLogger(LOG_ROOT)

def do_logger_setup(logroot = LOG_ROOT, logfmt='%(message)s', loglvl=logging.INFO):
    ''' Setup Python logging using a TextViewLogHandler '''
    logger = logging.getLogger(logroot)
    logger.setLevel(loglvl)
    formatter = logging.Formatter(logfmt, "%H:%M:%S")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.propagate = False
    logger.addHandler(handler)
    return handler
