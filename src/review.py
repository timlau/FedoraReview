#!/usr/bin/python -tt
#-*- coding: UTF-8 -*-

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
import glob
import logging
import sys
import os
from subprocess import Popen

from reviewtools import get_logger, do_logger_setup, Settings
from reviewtools.bugz import ReviewBug
from reviewtools.misc import Checks


class ReviewHelper:

    def __init__(self):
        self.bug = None
        self.checks = None
        self.settings = Settings()
        self.args = self.__get_args()
        self.args.workdir = os.path.expanduser(self.args.workdir)
        self.verbose = False
        self.log = get_logger()
        self.outfile = None

    def __get_args(self):
        parser = argparse.ArgumentParser(description='Review a Fedora Package')
        parser.add_argument('-b','--bug', metavar='[bug]',
                   help='the bug number contain the package review')
        parser.add_argument('-w','--workdir', default=self.settings.work_dir, metavar='[dir]',
                            help='Work directory (default = ~/tmp/reviewhelper/')
        parser.add_argument('--other-bz', default=None, metavar='[bugzilla url]', dest='other_bz',
                            help='alternative bugzilla URL')
        parser.add_argument('--assign', action='store_true',
                            help = 'Assign the bug and set review flags')
        parser.add_argument('--cache', action='store_true', dest='cache',
                            help = 'do not redownload files from bugzilla, use the ones in the cache')
        parser.add_argument('--nobuild', action='store_true', dest='nobuild',
                            help = 'do not rebuild the srpm, use currently build ones')
        parser.add_argument('-u','--user', metavar='[userid]', default = self.settings.bz_user,
                   help='The Fedora Bugzilla userid')
        parser.add_argument('-p','--password', metavar='[password]',
                   help='The Fedora Bugzilla password')
        parser.add_argument('-v','--verbose',  action='store_true',
                            help='Show more output')
        parser.add_argument('--no-report',  action='store_true', dest='noreport',
                            help='Do not make a review report')
        parser.add_argument('-n','--name', metavar='<name prefix>',
                   help='run on local <name prefix>.spec & <name prefix>*.src.rpm located in work dir')
        parser.add_argument('-D','--dist', metavar='<distribution>', default = self.settings.distribution,
                   help='Run check of a given distribution (F13,F14,F15,RAWHIDE,EPEL5 & EPEL6)')
        args = parser.parse_args()
        return args

    def __download_sources(self):
        self.checks.sources.set_work_dir(self.args.workdir)
        sources = self.checks.spec.get_sources()
        found = False
        if sources:
            found = True
            for tag in sources:
                if tag.startswith('Source'):
                   self.checks.sources.add(tag,sources[tag])
                   found = True
        return found

    def __do_report(self):
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
        self.args.name = os.path.basename(self.bug.spec_file).rsplit('.',1)[0]
        self.args.workdir = "%s/%s" % (self.args.workdir, self.args.bug)
        self.__do_report_local(self.args.workdir)
        self.__show_results()

    def __do_report_local(self, file_dir):
        ''' Create a review report on already downloaded .spec & .src.rpm'''
        spec_filter = '%s/%s*.spec' % (file_dir, self.args.name)
        srpm_filter = '%s/%s*.src.rpm' % (file_dir, self.args.name)
        files_spec = glob.glob(spec_filter)
        files_srpm = glob.glob(srpm_filter)
        if files_spec and files_srpm:
            self.__run_checks(files_spec[0], files_srpm[0])
        else:
            if not files_spec:
                self.log.error('Cannot find : %s ' % spec_filter)
            if not files_srpm:
                self.log.error('Cannot find : %s ' % srpm_filter)

    def __show_results(self):
        if self.outfile and self.checks.spec.filename:
            Popen([self.settings.editor, self.outfile, self.checks.spec.filename])

    def __run_checks(self, spec, srpm):
        self.log.debug("  --> Spec file : %s" % spec)
        self.log.debug("  --> SRPM file : %s" % srpm)
        self.checks = Checks(self.args, spec, srpm, 
            cache=self.args.cache, nobuild = self.args.nobuild)
        outfile = "%s/%s-review.txt" % (
            self.args.workdir, self.checks.spec.name)
        with open(outfile,"w") as output:
            # get upstream sources
            rc = self.__download_sources()
            if not rc:
                self.log.info('Cannot download upstream sources')
                sys.exit(1)
            if self.args.nobuild:
                self.checks.srpm.is_build = True
            self.log.info('Running checks and generate report\n')
            self.checks.run_checks(output=output)
            output.close()
        print "Review in: %s/%s-review.txt" % (self.args.workdir,
            self.checks.spec.name)

    def __do_assign(self):
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
                self.bug = ReviewBug(self.args.bug, user = self.args.user, password= self.args.password, cache=self.args.cache, other_BZ=self.args.other_bz)
            else:
                self.bug = ReviewBug(self.args.bug, cache=self.args.cache, nobuild=self.args.nobuild, other_BZ=self.args.other_bz)
            self.bug.set_work_dir('%s/%s' % (self.args.workdir, self.args.bug))
            self.log.debug("  --> Working dir : %s" % self.bug.work_dir)
            if self.args.assign and not self.args.other_bz: # can't use assign with alternate bugzilla url
                self.__do_assign()
            if not self.args.noreport:
                self.__do_report()
        elif self.args.name:
            self.__do_report_local(self.args.workdir)

if __name__ == "__main__":
    review = ReviewHelper()
    review.run()


