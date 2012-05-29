#!/usr/bin/python -tt
#-*- coding: utf-8 -*-
# vim: set expandtab: ts=4:sw=4:
#
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
import argparse
import glob
import logging
import os.path
import sys
import os
import subprocess
import errno

import FedoraReview

from FedoraReview import  Settings, FedoraReviewError
from FedoraReview.bugz import ReviewBug
from FedoraReview.checks_class import Checks
from FedoraReview import __version__


class ReviewHelper:

    def __init__(self):
        self.bug = None
        self.checks = None
        self._init_settings()
        Settings.workdir = os.path.expanduser(Settings.workdir)
        self.verbose = False
        self.log = FedoraReview.get_logger()
        self.outfile = None
        self.prebuilt = False

    def _init_settings(self):
        parser = argparse.ArgumentParser(description='Review a Fedora Package')
        parser.add_argument('-b', '--bug', metavar='[bug]',
                    help='the bug number contain the package review')
        parser.add_argument('-n', '--name', metavar='<name prefix>',
                    help='Run on local <name prefix>.spec & <name prefix>*.src.rpm located in work dir')
        parser.add_argument('-a','--assign', action='store_true',
                    help = 'Assign the bug and set review flags')
        parser.add_argument('-c','--cache', action='store_true', dest='cache',
                    help = 'Do not redownload files from bugzilla, use the ones in the cache')
        parser.add_argument('-d-','--display-checks', default = False,
                    action='store_true',dest='list_checks',
                    help='List all the checks available')
        parser.add_argument('-l', '--login', action='store_true', default=False,
                    help='Login into Fedora Bugzilla before starting')
        parser.add_argument('-m','--mock-config', metavar='<config>',
                    default = Settings.mock_config, dest='mock_config',
                    help='Configuration to use for the mock build (Defaults to fedora-rawhide-i686)')
        parser.add_argument('--no-report',  action='store_true', dest='noreport',
                    help='Do not make a review report')
        parser.add_argument('--nobuild', action='store_true', dest='nobuild',
                    help = 'Do not rebuild the srpm, use currently build ones')
        parser.add_argument('-o','--mock-options', metavar='<mock options>',
                    default = Settings.mock_options, dest='mock_options',
                    help='Options to specify to mock for the build (Defaults to None)')
        parser.add_argument('--other-bz', default=None, metavar='[bugzilla url]', dest='other_bz',
                    help='Alternative bugzilla URL')
        parser.add_argument('-p', '--prebuilt',  action='store_true', dest='prebuilt',
                    help='When using -n <name>, use prebuilt rpms in current directory')
        parser.add_argument('-u', '--user', metavar='[userid]', default = Settings.bz_user,
                    help='The Fedora Bugzilla userid')
        parser.add_argument('-v', '--verbose',  action='store_true',
                    help='Show more output')
        parser.add_argument('-w', '--workdir',
                    default=Settings.work_dir, metavar='[dir]',
                    help='Work directory (default = ~/tmp/reviewhelper/')
        parser.add_argument('-x', '--exclude',
                    default=Settings.exclude, dest='exclude', metavar='[excluded tests]',
                    help='Comma-separated list of tests to exclude')
        parser.add_argument('-s', '--single',
                    default=Settings.single, dest='single', metavar='[single test]',
                    help='Single test to run, as named by --list-checks')
        parser.add_argument('-V', '--version', default = False,
                    action='store_true',
                    help='Display version information and exit.')
        args = parser.parse_args()
        args.workdir = os.path.abspath(os.path.expanduser(args.workdir))
        Settings.add_args(args)

    def __download_sources(self):
        self.checks.sources.set_work_dir(Settings.workdir)
        sources = self.checks.spec.get_sources()
        found = False
        if sources:
            found = True
            for tag in sources:
                if tag.startswith('Source'):
                   self.checks.sources.add(tag, sources[tag])
                   found = True
        return found

    def __do_report(self):
        ''' Create a review report'''
        self.log.info('Getting .spec and .srpm Urls from bug report : %s' % Settings.bug)
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
        Settings.name = os.path.basename(self.bug.spec_file).rsplit('.',1)[0]
        Settings.workdir = "%s/%s" % (Settings.workdir, Settings.bug)
        self.__do_report_local(Settings.workdir)

    def __do_report_local(self, file_dir):
        ''' Create a review report on already downloaded .spec & .src.rpm'''
        spec_filter = '%s/%s*.spec' % (file_dir, Settings.name)
        srpm_filter = '%s/%s*.src.rpm' % (file_dir, Settings.name)
        files_spec = glob.glob(spec_filter)
        files_srpm = sorted(glob.glob(srpm_filter), reverse=True)
        if files_spec and files_srpm:
            self.__run_checks(files_spec[0], files_srpm[0])
        else:
            if not files_spec:
                self.log.error('Cannot find : %s ' % spec_filter)
            if not files_srpm:
                self.log.error('Cannot find : %s ' % srpm_filter)
        if Settings.edit:
            self.__show_results()

    def __list_checks(self):
        """ List all the checks available.
        """
        self.checks = Checks(None, None)
        self.checks.list_checks()

    def __print_version(self):
        print('fedora-review version ' + __version__)

    def __show_results(self):
        if self.outfile and self.checks.spec.filename:
            editor = Settings.editor
            if editor == '':
                if 'EDITOR' in os.environ:
                    editor = os.environ['EDITOR']
                else:
                    self.log.error("EDITOR variable not set and no"
                                   " editor set in configuration")
                    return

            try:
                subprocess.call([editor, self.outfile, self.checks.spec.filename])
            except OSError, e:
                if e.errno == errno.ENOENT:
                    self.log.error("EDITOR not set correctly or editor"
                                    " configuration is incorrect")
                    return
                raise e

    def __run_checks(self, spec, srpm):
        self.log.debug("  --> Spec file : %s" % spec)
        self.log.debug("  --> SRPM file : %s" % srpm)
        self.checks = Checks(spec, srpm )
        self.outfile = "%s/%s-review.txt" % (
            Settings.workdir, self.checks.spec.name)
        with open(self.outfile,"w") as output:
            # get upstream sources
            rc = self.__download_sources()
            if not rc:
                self.log.info('Cannot download upstream sources')
                sys.exit(1)
            if Settings.nobuild:
                self.checks.srpm.is_build = True
            self.log.info('Running checks and generate report\n')
            self.checks.run_checks(output=output)
            output.close()
        print "Review in: %s/%s-review.txt" % (Settings.workdir,
            self.checks.spec.name)

    def __do_assign(self):
        ''' assign bug'''
        if not Settings.user or Settings.user == "":
            self.log.error("Error: username not set in cofiguration and not"
                           " provided as argument (-u/--user).")
            return

        self.log.info("Assigning bug to user")
        self.bug.assign_bug()

    def run(self):
        try:
            self.verbose = Settings.verbose
            if self.verbose:
                FedoraReview.do_logger_setup(loglvl=logging.DEBUG)
            else:
                FedoraReview.do_logger_setup()
            if Settings.list_checks:
                self.__list_checks()
            elif Settings.version:
                self.__print_version()
            elif Settings.bug:
                # get the bug
                self.log.info("Processing review bug : %s" % Settings.bug )
                self.bug = ReviewBug(Settings.bug, user=Settings.user)
                if Settings.login:
                    self.bug.login(Settings.user)
                self.bug.set_work_dir('%s/%s' % (Settings.workdir, Settings.bug))
                self.log.debug("  --> Working dir : %s" % self.bug.work_dir)
                if Settings.assign and not Settings.other_bz: # can't use assign with alternate bugzilla url
                    self.__do_assign()
                if not Settings.noreport:
                    self.__do_report()
            elif Settings.name:
                self.__do_report_local(Settings.workdir)
        except FedoraReviewError, err:
            self.log.error("Exception down the road...", exc_info=True)
            return 1
        return 0


if __name__ == "__main__":
    review = ReviewHelper()
    review.run()

# vim: set expandtab: ts=4:sw=4:
