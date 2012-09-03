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

import re
import rpm
import subprocess

from subprocess import Popen, PIPE

from settings import Settings

SECTIONS = ['build', 'changelog', 'check', 'clean', 'description', 'files',
               'install', 'package', 'prep', 'pre', 'post', 'preun', 'postun',
               'trigger', 'triggerin', 'triggerun', 'triggerprein',
               'triggerpostun', 'pretrans', 'posttrans']
SPEC_SECTIONS = re.compile(r"^(\%(" + "|".join(SECTIONS) + "))\s*")
MACROS = re.compile(r"^%(define|global)\s+(\w*)\s+(.*)")


class SpecFile(object):
    '''
    Wrapper classes for getting information from a .spec file
    '''
    def __init__(self, filename):
        self.log = Settings.get_logger()
        self._sections = {}
        self._section_list = []
        self.filename = filename
        with open(filename, "r") as f:
            self.lines = f.readlines()
        ts = rpm.TransactionSet()
        self.spec_obj = ts.parseSpec(self.filename)

        self.name = self.get_from_spec('name')
        self.version = self.get_from_spec('version')
        self.release = self.get_from_spec('release')
        self.process_sections()

    def get_sources(self, _type='Source'):
        ''' Get SourceX/PatchX lines with macros resolved '''
        result = {}
        for (url, num, flags) in self.spec_obj.sources:
            # rpmspec.h, rpm.org ticket #123
            srctype = "Source" if flags & 1 else "Patch"
            if _type != srctype:
                continue
            tag = srctype + str(num)
            result[tag] = url
        return result

    def has_patches(self):
        '''Returns true if source rpm contains patch files'''
        return len(self.get_sources('Patch')) > 0

    def process_sections(self):
        ''' Scan lines and build self._sections, self.section_list. '''
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
                if line:
                    section_lines.append(line.strip())
        self._section_list.append(cur_sec)
        self._sections[cur_sec] = section_lines
        cur_sec = this_sec

    def get_from_spec(self, macro):
        ''' Use rpm for a value for a given tag (macro is resolved)'''
        qf = '%{' + macro.upper() + "}\n"  # The RPM tag to search for
        # get the name
        cmd = ['rpm', '-q', '--qf', qf, '--specfile', self.filename]
                # Run the command
        try:
            proc = \
                Popen(cmd, stdout=PIPE, stderr=PIPE, env={'LC_ALL': 'C'})
            output, error = proc.communicate()
            #print "output : [%s], error : [%s]" % (output, error)
        except OSError, e:
            self.log.error("OSError : %s" % str(e))
            self.log.debug("OSError : %s" % str(e), exc_info=True)
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
                self.log.warning("Error : [%s]" % (error))
                return False

    def get_expanded(self):
        ''' Return expanded spec, as provided by rpmspec -P. '''
        cmd = ['rpmspec', '-P', self.filename]
        try:
            proc = Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
            output, error = proc.communicate()
            if proc.wait() != 0:
                return None
            return output
        except OSError, e:
            self.log.error("OSError: %s" % str(e))
            self.log.debug("OSError: %s stderr: %s " % (str(e), error),
                           exc_info=True)
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
        keys = [re.compile(r"^%s\d*\s*:\s*(.*)" % tag, re.I),
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
        ''' Return first line matching regex or None. '''
        for line in self.lines:
            res = regex.search(line)
            if res:
                return res
        return None

    def find_all(self, regex, skip_changelog=False):
        ''' Find all non-changelog lines matching regex. '''
        my_lines = list(self.lines)
        if skip_changelog:
            line = my_lines.pop()
            while not '%changelog' in line.lower():
                line = my_lines.pop()
        result = []
        for line in my_lines:
            res = regex.search(line)
            if res:
                result.append(res)
        return result

# vim: set expandtab: ts=4:sw=4:
