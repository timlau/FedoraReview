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
This module contains misc helper funtions and classes
'''

import sys
import os
from operator import attrgetter
from sets import Set
from straight.plugin import load

from check_base import CheckDict
from settings import  Settings
from srpm_file import  SRPMFile
from spec_file import  SpecFile
from sources import  Sources
from version import  __version__, build_id, build_date
from jsonapi import JSONPlugin


HEADER = """
Package Review
==============

Key:
- = N/A
x = Pass
! = Fail
? = Not evaluated

"""


class Checks(object):
    ''' Interface class to load, select and run checks. '''

    def __init__(self, spec_file, srpm_file):
        ''' Create a Checks set. srpm_file and spec_file are required,
        unless invoked from ChecksLister.
        '''
        self._results = {'PASSED': [], 'FAILED': [], 'NA': [], 'USER': []}
        self.log = Settings.get_logger()
        if hasattr(self, 'sources'):
            # This is  a listing instance
            self.srpm = None
            self.spec=None
        else:
            self.spec = SpecFile(spec_file)
            self.sources = Sources(self.spec)
            self.srpm = SRPMFile(srpm_file, self.spec)
        self.plugins = load('FedoraReview.checks')
        self.add_check_classes()
        if Settings.single:
            self.set_single_check(Settings.single)
        elif Settings.exclude:
            self.exclude_checks(Settings.exclude)

    def add_check_classes(self):
        """ 
        Get all check classes in FedoraReview.checks + external plugin
        directories and add them to self.checkdict
        """
        self.checkdict = CheckDict()

        for plugin in self.plugins:
            tests = plugin.Registry().register(plugin, self)
            self.checkdict.extend(tests)

        ext_dirs = []
        if "REVIEW_EXT_DIRS" in os.environ:
            ext_dirs = os.environ["REVIEW_EXT_DIRS"].split(":")
        ext_dirs.extend(Settings.ext_dirs.split(":"))
        for ext_dir in ext_dirs:
            if not os.path.isdir(ext_dir):
                continue
            for plugin in os.listdir(ext_dir):
                full_path = os.path.join(ext_dir, plugin)
                if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                    self.log.debug('Add external module: %s' % full_path)
                    pl = JSONPlugin(self, full_path)
                    tests = pl.register()
                    self.checkdict.extend(tests)

    def show_file(self, filename, output=sys.stdout):
        fd = open(filename, "r")
        lines = fd.readlines()
        fd.close()
        for line in lines:
            output.write(line)

    def exclude_checks(self, exclude_arg):
        for c in [l.strip() for l in exclude_arg.split(',')]:
            if  c in self.checkdict:
                del self.checkdict[c]
            else:
                self.log.warn("I can't remove check: " + c)

    def set_single_check(self, check):
        self.checkdict.set_single_check(check)

    def get_checks(self):
        return self.checkdict

    def run_checks(self, output=sys.stdout, writedown=True):

        issues = []
        results = []
        deprecated = []
        attachments = []
        names = list(self.checkdict.iterkeys())

        # "Horrible Hack (tm)"
        # First, run state-changing build and install:
        if 'CheckPackageInstalls' in names:
            names.remove('CheckPackageInstalls')
            names.insert(0, 'CheckPackageInstalls')
        if 'CheckBuild' in names:
            names.remove('CheckBuild')
            names.insert(0, 'CheckBuild')
            
        for name in names:
            check = self.checkdict[name]
            check.run()
            if check.result:
                results.append(check.result)
                attachments.extend(check.result.attachments)
                if check.result.type == 'MUST' and \
                     check.result.result == "fail":
                        issues.append(check.result)

        if writedown:
            key_getter = attrgetter('group', 'type', 'name')
            self.__show_output(output,
                               sorted(results, key=key_getter),
                               issues,
                               attachments)

    def __show_output(self, output, results, issues, attachments):

        def write_sections(results):
            groups = sorted(list(set([test.group for test in results])))
            for group in groups:
                 res = filter(lambda t: t.group == group, results)
                 if res == []:
                    continue
                 output.write('\n' + group + ':\n')
                 for r in res:
                     output.write(r.get_text() + '\n')

        output.write(HEADER)

        output.write("\n\n===== MUST items =====\n")
        musts = filter( lambda r: r.type == 'MUST', results)
        write_sections(musts)

        output.write("\n===== SHOULD items =====\n")
        shoulds = filter( lambda r: r.type == 'SHOULD', results)
        write_sections(shoulds)

        output.write("\n===== EXTRA items =====\n")
        extras = filter( lambda r: r.type == 'EXTRA', results)
        write_sections(extras)

        if issues:
            output.write("\nIssues:\n=======\n")
            for fail in issues:
                output.write(fail.get_text() + "\n")
                output.write("See: %s\n" % fail.url)

        if len(attachments) > 0:
            output.write('\n')
        for a in sorted(attachments):
            output.write(a.__str__())

        output.write('\n\nGenerated by fedora-review'
                     ' %s (%s) last change: %s\n' % 
                     (__version__, build_id, build_date))
        output.write('Command line :' + ' '.join(sys.argv) +'\n')


class ChecksLister(Checks):
    """ A Checks instance only capable of get_checks. """
    def __init__(self):
        self.sources = None
        Checks.__init__(self,None, None)

# vim: set expandtab: ts=4:sw=4:
