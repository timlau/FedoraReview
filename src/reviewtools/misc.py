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
This module contains misc helper funtions and classes
'''
import sys
import os
from operator import attrgetter

from reviewtools import Sources, SRPMFile, SpecFile
from reviewtools.jsonapi import JSONPlugin

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

from reviewtools import get_logger


class Checks(object):
    def __init__(self, args, spec_file, srpm_file, cache=False,
            nobuild=False, mock_config='fedora-rawhide-i686'):
        self.checks = []
        self.ext_checks = []
        self.args = args  # Command line arguments & options
        self.cache = cache
        self.nobuild = nobuild
        self._results = {'PASSED': [], 'FAILED': [], 'NA': [], 'USER': []}
        self.deprecated = []
        self.spec = SpecFile(spec_file)
        self.sources = Sources(cache=cache)
        self.log = get_logger()
        self.srpm = SRPMFile(srpm_file, cache=cache, nobuild=nobuild,
            mock_config=mock_config)
        self.plugins = load('reviewtools.checks')
        self.add_check_classes()

    def reset_results(self):
        self._results = []

    def add_check_classes(self):
        """ get all the check classes in the reviewtools.checks and add them
        to be excuted
        """

        for module in self.plugins:
            objs = module.__dict__
            for mbr in sorted(objs):
                if 'Check' in mbr and not mbr.endswith('Base'):
                    obj = objs[mbr]
                    self.log.debug('Add module: %s' % mbr)
                    self.add(obj)

        ext_dirs = os.environ["REVIEW_EXT_DIRS"].split(":")
        for ext_dir in ext_dirs:
            for plugin in os.listdir(ext_dir):
                full_path = "%s/%s" % (ext_dir, plugin)
                if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
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

    def parse_result(self, test):
        result = test.get_result()
        self._results.append(result)

    def show_result(self, output):
        for line in self._results:
            output.write(line)
            output.write('\n')

    def run_checks(self, output=sys.stdout):
        output.write(HEADER)
        issues = []
        self.reset_results()
        sorted_checks = sorted(self.checks, key=attrgetter('header','type','__class__.__name__'))
        current_section = None
        for test in sorted_checks:
            if test.is_applicable() and test.__class__ \
                        not in self.deprecated:
                if test.automatic:
                    test.run()
                else:
                    test.state = 'pending'

                if test.header != current_section:
                    self._results.append("\n\n==== %s ====\n" % test.header)
                    current_section = test.header

                self.parse_result(test)

                result = test.get_result()
                self.log.debug('Running check : %s %s [%s] ' % (
                    test.__class__.__name__,
                    " " * (30 - len(test.__class__.__name__)),
                    test.state ))
                if result:
                    if result.startswith('[!] : MUST'):
                        issues.append(result)

        # run external checks. we probably want to merge this into
        # previous run, i.e create some layer so that all checks will
        # be equal and we can sort them etc
        for ext in self.ext_checks:
            ext.run()

        self.show_result(output)
        if issues:
            output.write("\nIssues:\n")
        for fail in issues:
            output.write(fail)
            output.write('\n')
