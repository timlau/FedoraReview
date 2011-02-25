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
This module contains misc helper funtions and classes
'''
import sys

from reviewtools import Source, SRPMFile, SpecFile

import reviewtools.checks

HEADER = """
Package Review
==============

Key:
- = N/A
x = Check
! = Problem
? = Not evaluated

"""

from reviewtools import get_logger


class Checks:
    def __init__(self, args, spec_file, srpm_file, src_file=None, src_url=None, cache=False):
        self.checks = {'MUST' : [], 'SHOULD' : []}
        self.args = args # Command line arguments & options
        self.cache = cache
        self.spec = SpecFile(spec_file)
        self.source = Source(cache=cache)
        self.log = get_logger()
        if src_file:
            self.source.filename=src_file
        elif src_url:
            self.source.get_source(src_url)
        self.srpm = SRPMFile(srpm_file, cache=cache)
        self.add_check_classes()

    def add_check_classes(self):
        """ get all the check classes in the reviewtools.checks and add them
        to be excuted
        """
        objs = reviewtools.checks.__dict__
        for mbr in sorted(objs):
            if mbr.startswith('Check'):
                obj = objs[mbr]
                base_cls = obj.__bases__
                if base_cls and base_cls[0].__name__ == 'CheckBase':
                    self.add(obj)

    def add(self, class_name):
        cls = class_name(self)
        typ = cls.type
        self.checks[typ].append(cls)

    def show_file(self, filename, output=sys.stdout):
        fd = open(filename, "r")
        lines =  fd.readlines()
        fd.close()
        for line in lines:
            output.write(line)

    def run_checks(self, output=sys.stdout):
        output.write(HEADER)
        failed = []
        self.log.info("Running check for : %s" % self.args.dist)
        for typ in ['MUST','SHOULD']:
            # Automatic Checks
            checks = self.checks[typ]
            for test in checks:
                self.log.debug('----> Running check : %s ' % (test.__class__))
                self.log.debug('      Distributions : %s ' % (",".join(test.distribution)))
                if not self.args.dist in test.distribution: # skip test not for the selected distro
                    continue
                if test.is_applicable():
                    if test.automatic:
                        test.run()
                else:
                    test.state = 'na'
                result = test.get_result()
                if result:
                    if result.startswith('[!] : MUST'):
                        failed.append(result)
                    output.write(result)
                    output.write('\n')
        output.write("\nIssues:\n")
        for fail in failed:
            output.write(fail)
            output.write('\n')

