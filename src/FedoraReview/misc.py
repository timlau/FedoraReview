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

from FedoraReview import Sources, SRPMFile, SpecFile
from FedoraReview.jsonapi import JSONPlugin

HEADER = """
Package Review
==============

Key:
- = N/A
x = Check
! = Problem
? = Not evaluated

"""
from straight.plugin import load

from FedoraReview import get_logger, Settings


class Checks(object):
    def __init__(self, args, spec_file, srpm_file, cache=False,
            nobuild=False, mock_config='fedora-rawhide-i386'):
        self.checks = []
        self.ext_checks = []
        self.args = args  # Command line arguments & options
        self.cache = cache
        self.nobuild = nobuild
        self._results = {'PASSED': [], 'FAILED': [], 'NA': [], 'USER': []}
        self.deprecated = []
        self.spec = SpecFile(spec_file)
        self.sources = Sources(cache=cache, mock_config=mock_config)
        self.log = get_logger()
        self.srpm = SRPMFile(srpm_file, cache=cache, nobuild=nobuild,
            mock_config=mock_config, spec=self.spec)
        self.plugins = load('FedoraReview.checks')
        self.add_check_classes()

    def add_check_classes(self):
        """ get all the check classes in the FedoraReview.checks and add
        them to be excuted
        """

        for module in self.plugins:
            objs = module.__dict__
            for mbr in sorted(objs):
                if 'Check' in mbr and not mbr.endswith('Base'):
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
        self.deprecated.extend(cls.deprecates)

    def show_file(self, filename, output=sys.stdout):
        fd = open(filename, "r")
        lines = fd.readlines()
        fd.close()
        for line in lines:
            output.write(line)

    def run_checks(self, output=sys.stdout, writedown=True):
        issues = []
        results = []
        # run external checks first so we can get what they deprecate
        for ext in self.ext_checks:
            self.log.debug('Running external module : %s' % ext.plugin_path)
            ext.run()
            for result in ext.get_results():
                results.append(result)
                if result.type == 'MUST' and result.result == "fail":
                    issues.append(result.get_text())
                self.deprecated.extend(result.deprecates)

        for test in self.checks:
            if test.is_applicable() and test.__class__.__name__ \
                        not in self.deprecated:
                if test.automatic:
                    test.run()
                else:
                    test.state = 'pending'

                result = test.get_result()
                results.append(result)
                self.log.debug('Running check : %s %s [%s] ' % (
                    test.__class__.__name__,
                    " " * (30 - len(test.__class__.__name__)),
                    test.state))
                if result:
                    if result.type == 'MUST' and result.result == "fail":
                        issues.append(result.get_text())

        if writedown:
            self.__show_output(output,
                               sorted(results, key=attrgetter('group', 'type', 'name')),
                               issues)

    def __show_output(self, output, results, issues):
        output.write(HEADER)
        current_section = None
        for res in results:
            if res.group != current_section:
                output.write("\n\n==== %s ====\n" % res.group)
                current_section = res.group

            output.write(res.get_text())
            output.write('\n')

        if issues:
            output.write("\nIssues:\n")
            for fail in issues:
                output.write(fail)
                output.write('\n')
