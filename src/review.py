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

import argparse
import sys
import logging
import glob
import os
from subprocess import Popen

from reviewtools.bugz import ReviewBug
from reviewtools.misc import Checks
from reviewtools import get_logger, do_logger_setup
from urlparse import urlparse

class ReviewHelper:

    def __init__(self):
        self.bug = None
        self.checks = None
        self.args = self.get_args()
        self.verbose = False
        self.log = get_logger()
        self.outfile = None

    def get_args(self):
        parser = argparse.ArgumentParser(description='Review a Fedora Package')
        parser.add_argument('-b','--bug', metavar='[bug]',
                   help='the bug number contain the package review')
        parser.add_argument('-w','--workdir', default='~/tmp/reviewhelper/', metavar='[dir]',
                            help='Work directory (default = ~/tmp/reviewhelper/')
        parser.add_argument('--assign', action='store_true',
                            help = 'Assign the bug and set review flags')
        parser.add_argument('--cache', action='store_true', dest='cache',
                            help = 'do not redownload files from bugzilla, use the ones in the cache')
        parser.add_argument('--nobuild', action='store_true', dest='nobuild',
                            help = 'do not rebuild the srpm, use currently build ones')
        parser.add_argument('-u','--user', metavar='[userid]',
                   help='The Fedora Bugzilla userid')
        parser.add_argument('-p','--password', metavar='[password]',
                   help='The Fedora Bugzilla password')
        parser.add_argument('-v','--verbose',  action='store_true',
                            help='Show more output')
        parser.add_argument('--no-report',  action='store_true', dest='noreport',
                            help='Do not make a review report')
        parser.add_argument('-n','--name', metavar='<name prefix>',
                   help='run on local <name prefix>.spec & <name prefix>*.src.rpm located in work dir')
        parser.add_argument('-D','--dist', metavar='<distribution>', default = 'RAWHIDE',
                   help='Run check of a given distribution (F13,F14,F15,RAWHIDE,EPEL5 & EPEL6)')
        args = parser.parse_args()
        return args

    def download_sources(self):
        self.checks.source.set_work_dir('%s/%s' % (self.args.workdir, self.args.bug))
        sources = self.checks.spec.get_sources()
        found = False
        if sources:
            found = True
            for tag in sources:
                if tag.startswith('Source') and urlparse(sources[tag])[0] != '':
                    self.log.debug("Downloading (%s): %s" % (tag,sources[tag]))
                    self.checks.source.get_source(sources[tag])
        return found

    def do_report(self):
        ''' Create a review report'''
        self.log.info('Getting .spec and .srpm Urls from bug report : %s' % self.args.bug)
        # get urls
        rc = self.bug.find_urls()
        if not rc:
            self.log.info('Cannot find any .spec and .srpm URLs in bugreport')
            sys.exit(1)
        self.log.debug("  --> Spec url : %s" % self.bug.spec_url)
        self.log.debug("  --> SRPM url : %s" % self.bug.srpm_url)
        # get the spec and SRPM file
        rc = self.bug.download_files()
        if not rc:
            self.log.info('Cannot download .spec and .srpm')
            sys.exit(1)
        self.log.debug("  --> Spec file : %s" % self.bug.spec_file)
        self.log.debug("  --> SRPM file : %s" % self.bug.srpm_file)
        self.checks = Checks(self.args, self.bug.spec_file, self.bug.srpm_file, cache=self.args.cache, nobuild=self.args.nobuild)
        self.outfile = "%s/%s-review.txt" % (self.bug.work_dir, self.checks.spec.name)
        output = open(self.outfile,"w")
        # get upstream sources
        rc = self.download_sources()
        if self.args.nobuild:
            self.checks.srpm.is_build = True
        if not rc:
            self.log.info('Cannot download upstream sources')
            sys.exit(1)
        self.log.info('Running checks and generate report\n')
        self.checks.run_checks(output=output)
        output.close()
        self.show_results()

    def show_results(self):
        if self.outfile and self.checks.spec.filename:
            Popen(["/usr/bin/gedit", self.outfile, self.checks.spec.filename])

    def do_report_local(self):
        ''' Create a review report on already downloaded .spec & .src.rpm'''
        work_dir = '%s/%s' % (os.path.abspath(os.path.expanduser(self.args.workdir)), self.args.bug)
        spec_filter = '%s/%s*.spec' % (work_dir, self.args.name)
        srpm_filter = '%s/%s*.src.rpm' % (work_dir, self.args.name)
        files_spec = glob.glob(spec_filter)
        files_srpm = glob.glob(srpm_filter)
        if files_spec and files_srpm:
            spec = files_spec[0]
            srpm = files_srpm[0]
            self.log.debug("  --> Spec file : %s" % spec)
            self.log.debug("  --> SRPM file : %s" % srpm)
            self.checks = Checks(spec, srpm)
            outfile = "%s/%s-review.txt" % (self.bug.work_dir, self.checks.spec.name)
            output = open(outfile,"w")
            # get upstream sources
            rc = self.download_sources()
            if not rc:
                self.log.info('Cannot download upstream sources')
                sys.exit(1)
            self.log.info('Running checks and generate report\n')
            self.checks.run_checks(output=self.args.output)
            output.close()
        else:
            if not files_spec:
                self.log.error('Cannot find : %s ' % spec_filter)
            if not files_srpm:
                self.log.error('Cannot find : %s ' % srpm_filter)


    def do_assign(self):
        ''' assign bug'''
        if self.args.user and self.args.password:
            self.log.info("Assigning bug to user")
            self.bug.assign_bug()
        else:
            self.log.info('You need to add bugzilla userid/password (-u/-p) to assign bug')

    def run(self):
        self.verbose = self.args.verbose
        if self.verbose:
            do_logger_setup(loglvl=logging.DEBUG)
        else:
            do_logger_setup()
        if self.args.bug:
            # get the bug
            self.log.info("Processing review bug : %s" % self.args.bug )
            if self.args.user and self.args.password:
                self.bug = ReviewBug(self.args.bug, user = self.args.user, password= self.args.password, cache=self.args.cache)
            else:
                self.bug = ReviewBug(self.args.bug, cache=self.args.cache, nobuild=self.args.nobuild)
            self.bug.set_work_dir('%s/%s' % (self.args.workdir, self.args.bug))
            self.log.debug("  --> Working dir : %s" % self.bug.work_dir)
            if self.args.assign:
                self.do_assign()
            if not self.args.noreport:
                self.do_report()
        elif self.args.name:
            self.do_report_local()

if __name__ == "__main__":
    review = ReviewHelper()
    review.run()


