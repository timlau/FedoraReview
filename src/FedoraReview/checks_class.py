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
        self.checks = []
        self.ext_checks = []
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
        """ get all the check classes in the FedoraReview.checks and add
        them to be excuted
        """

        for module in self.plugins:
            objs = module.__dict__
            for mbr in sorted(objs):
                if not 'Check' in mbr:
                    continue
                if  mbr.endswith('Base'):
                    continue
                if mbr in self.checks:
                    continue
                obj = objs[mbr]
                self.log.debug('Add module: %s' % mbr)
                self.add(obj)

        ext_dirs = []
        if "REVIEW_EXT_DIRS" in os.environ:
            ext_dirs = os.environ["REVIEW_EXT_DIRS"].split(":")
        ext_dirs.extend(Settings.ext_dirs.split(":"))
        for ext_dir in ext_dirs:
            if not os.path.isdir(ext_dir):
                continue
            for plugin in os.listdir(ext_dir):
                full_path = "%s/%s" % (ext_dir, plugin)
                if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                    self.log.debug('Add external module: %s' % full_path)
                    pl = JSONPlugin(self, full_path)
                    self.ext_checks.append(pl)

    def add(self, class_name):
        cls = class_name(self)
        self.checks.append(cls)

    def show_file(self, filename, output=sys.stdout):
        fd = open(filename, "r")
        lines = fd.readlines()
        fd.close()
        for line in lines:
            output.write(line)

    def exclude_checks(self, exclude_arg):
        for c in [l.strip() for l in exclude_arg.split(',')]:
            found = filter( lambda  i: i.name == c,  self.checks)
            if  len(found) > 0:
                self.checks = list( set(self.checks) - set(found))
                continue
            found = filter(lambda  i: i.name == c,  self.ext_checks)
            if  len(found) > 0:
                self.ext_checks = list(set(self.ext_checks) - set(found))
                continue
            self.log.warn("I can't remove check: " + c)

    def set_single_check(self, check):
        found = filter(lambda c: c.name == check, self.checks)
        if len(found) > 0:
              self.checks = found
              self.ext_checks = []
              return
        found = filter(lambda c: c.name == check, self.ext_checks)
        if len(found) > 0:
              self.ext_checks = found
              self.checks = []
              return
        self.log.warn("I can't find check: " + check)

    def get_checks(self):
        c = self.ext_checks
        c.extend([t.name for t in self.checks])
        return c

    def run_checks(self, output=sys.stdout, writedown=True):

        def mv_check_to_front(name):
            for check in self.checks:
                if check.name == name:
                     self.checks.remove(check)
                     self.checks.insert(0,check)

        issues = []
        results = []
        deprecated = []
        attachments = []

        # First, run state-changing build and install:
        mv_check_to_front('CheckPackageInstalls')
        mv_check_to_front('CheckBuild')

        # run external checks first so we can get what they deprecate
        for ext in self.ext_checks:
            self.log.debug('Running external module : %s' % ext.plugin_path)
            ext.run()
            for result in ext.get_results():
                if result.result == 'not_applicable':
                    continue
                results.append(result)
                if result.type == 'MUST' and result.result == "fail":
                    issues.append(result)
                deprecated.extend(result.deprecates)
                attachments.extend(result.attachments)

        # we only add to deprecates is deprecating test will be run
        for test in self.checks:
            if test.is_applicable():
                deprecated.extend(test.deprecates)

        for test in self.checks:
            if  test.name not in deprecated:
                test.run()
                result = test.result
                if result:
                    self.log.debug('Running check : %s %s [%s] ' % (
                        test.name,
                        " " * (30 - len(test.name)),
                        result.result))
                    results.append(result)
                    attachments.extend(result.attachments)
                    if result.type == 'MUST' and result.result == "fail":
                        issues.append(result)

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
                 res = filter(lambda t: 
                                  t.group == group and 
                                  t.result != 'not_applicable', 
                              results)
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

        for a in sorted(attachments):
            output.write('\n\n')
            output.write(a.__str__())

        output.write('\n\nGenerated by fedora-review'
                     ' %s (%s) last change: %s\n' %
                     (__version__, build_id, build_date))
        output.write('Command line :' + ' '.join(sys.argv) +'\n')
        output.write("External plugins:\n")
        for plugin in self.ext_checks:
            output.write("%s version: %s\n" % (plugin.plugin_path,
                                               plugin.version))


class ChecksLister(Checks):
    """ A Checks instance only capable of listing checks. """
    def __init__(self):
        self.sources = None
        Checks.__init__(self,None, None)

    def list(self):
        """ List all the checks available. """
        for ext in self.ext_checks:
            print ext.name
        for test in self.checks:
            print test.name, ' -- ', test.text

# vim: set expandtab: ts=4:sw=4:
