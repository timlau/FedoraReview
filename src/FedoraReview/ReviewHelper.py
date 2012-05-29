#!/usr/bin/python -tt
#-*- coding: utf-8 -*-
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
'''
Tools for helping Fedora package reviewers
'''
import argparse
import glob
import grp
import logging
import sys
import os
import subprocess
import errno

import FedoraReview

from FedoraReview import Settings, FedoraReviewError, __version__, Mock
from FedoraReview.bugz import ReviewBug
from FedoraReview.url_bug import UrlBug
from FedoraReview.name_bug import NameBug
from FedoraReview.abstract_bug import SettingsError
from FedoraReview.checks_class import Checks

class ConfigError(FedoraReviewError):
    def __init__(self, why):
        FedoraReviewError.__init__(self, 'Configuration error: ' + why)
from FedoraReview import get_logger, do_logger_setup, \
    Settings, FedoraReviewError
from FedoraReview.bugz import ReviewBug
from FedoraReview.checks_class import Checks
from FedoraReview import __version__


class ReviewHelper:

    def __init__(self):
        self.bug = None
        self.checks = None
        self._init_settings()
        Settings.workdir = os.path.expanduser(Settings.workdir)
        self.log = FedoraReview.get_logger()
        self.verbose = False
        self.log = get_logger()
        self.outfile = None
        self.prebuilt = False

    def _init_settings(self):
        def _check_some_args(args):
            if not args.bug:
               if args.user or args.assign or  args.other_bz:
                    print( '--user, --assign and --other_bz'
                           ' only works with -b')

        def _check_mock_grp():
             try:
                 mock_gid = grp.getgrnam('mock')[2]
                 if not mock_gid in os.getgroups():
                     raise ConfigError('Not in mock group, see manpage')
             except:
                 raise ConfigError('No mock group - mock not installed?')


        parser = argparse.ArgumentParser(
                    description='Review a package using Fedora Guidelines',
                    add_help=False)
        mode =  parser.add_argument_group('Operation mode - one is required')
        modes =  mode.add_mutually_exclusive_group(required=True)
        optional =  parser.add_argument_group('General options')
        bz_only = parser.add_argument_group(
                     'Only to be used with bugzilla.redhat.com i. e., --bug')
        modes.add_argument('-b', '--bug', metavar='<bug>',
                    help='Operate on fedora bugzilla using its bug number.')
        modes.add_argument('-n', '--name', metavar='<name>',
                    help='Operate on local files <name>.spec &'
                         ' <name>*.src.rpm located in work dir.')
        modes.add_argument('-u', '--url', default = None, dest='url',
                    metavar='<url>',
                     help='Operate on another bugzilla, using complete'
                          ' url to bug page.')
        modes.add_argument('-d','--display-checks', default = False,
                    action='store_true',dest='list_checks',
                    help='List all available checks.')
        modes.add_argument('-V', '--version', default = False,
                    action='store_true',
                    help='Display version information and exit.')
        optional.add_argument('-c','--cache', action='store_true', dest='cache',
                    help = 'Do not redownload files from bugzilla,'
                           ' use the ones in the cache.')
        optional.add_argument('-h','--help', action='help',
                    help = 'Display this help message')
        optional.add_argument('-m','--mock-config', metavar='<config>',
                    default = 'fedora-rawhide-i386', dest='mock_config',
                    help='Configuration to use for the mock build,'
                             ' defaults to fedora-rawhide-i686.')
        optional.add_argument('--no-report',  action='store_true',
                    dest='noreport',
                    help='Do not make a review report.')
        optional.add_argument('--no-build', action='store_true',
                    dest='nobuild',
                    help = 'Do not rebuild the srpm, use currently'
                           ' built in mock.')
        optional.add_argument('-o','--mock-options', metavar='<mock options>',
                    default = '--no-cleanup-after', dest='mock_options',
                    help='Options to specify to mock for the build,'
                         ' defaults to --no-cleanup-after')
        optional.add_argument('-p', '--prebuilt',  action='store_true',
                    dest='prebuilt', help='When using -n <name>, use'
                    ' prebuilt rpms in current directory.')
        optional.add_argument('-s', '--single',
                    default='', dest='single',
                    metavar='<test>',
                    help='Single test to run, as named by --display-checks.')
        optional.add_argument('-v', '--verbose',  action='store_true',
                    help='Show more output.')
        optional.add_argument('-C', '--workdir',
                    default=Settings.workdir, dest='workdir', metavar='<dir>',
                    help='Work directory, default current dir')
        optional.add_argument('-x', '--exclude',
                    default='', dest='exclude',
                    metavar='"test,..."',
                    help='Comma-separated list of tests to exclude.')
        bz_only.add_argument('-a','--assign', action='store_true',
                    help = 'Assign the bug and set review flags')
        bz_only.add_argument('-l', '--login', action='store_true',
                    default=False,
                    help='Login into Fedora Bugzilla before starting')
        bz_only.add_argument('--other-bz', default=None,
                    metavar='<bugzilla url>', dest='other_bz',
                    help='Alternative bugzilla URL')
        bz_only.add_argument('-i','--user', dest='user',
                    metavar="<user id>",
                    help = 'The bugzilla user Id')
        args = parser.parse_args()
        args.workdir = os.path.abspath(os.path.expanduser(args.workdir))
        Settings.add_args(args)
        _check_some_args(args)
        _check_mock_grp()

    def __download_sources(self):
        self.checks.sources.set_work_dir(Settings.workdir)
        sources = self.checks.spec.get_sources('Source')
        for tag,src in sources.iteritems():
             try:
                 self.checks.sources.add(tag, sources[tag])
             except:
                 return False
        return True

    def __do_report(self):
        ''' Create a review report'''

        self.log.info('Getting .spec and .srpm Urls from : '
                       + self.bug.get_location())
        if Settings.bug:
            Settings.workdir = os.path.join(Settings.workdir,
                                            Settings.bug)
        self.log.debug("  --> Working dir: " + Settings.workdir)
        if not self.bug.find_urls():
            self.log.error( 'Cannot find .spec or .srpm URL(s)')
            sys.exit(1)

        if not self.bug.download_files():
            self.log.error('Cannot download .spec and .srpm')
            sys.exit(1)

        Settings.name = self.bug.get_name()
        self.__run_checks(self.bug.spec_file, self.bug.srpm_file)

    def __list_checks(self):
        """ List all the checks available.
        """
        self.checks = Checks(None, None)
        self.checks.list_checks()

    def __print_version(self):
        print('fedora-review version ' + __version__)

    def __run_checks(self, spec, srpm):
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

    def do_run(self):
        self.bug.check_settings()
        if not Settings.noreport:
            self.__do_report()

    def run(self):
        try:
            if Settings.verbose:
                FedoraReview.do_logger_setup(loglvl=logging.DEBUG)
            else:
                FedoraReview.do_logger_setup()
            if Settings.list_checks:
                self.__list_checks()
                return 0
            elif Settings.version:
                self.__print_version()
                return 0

            if Settings.url:
                self.log.info("Processing bug on url: " + Settings.url )
                self.bug = UrlBug(Settings.url)
                self.do_run()
            elif Settings.bug:
                self.log.info("Processing bugzilla bug: " + Settings.bug )
                self.bug = ReviewBug(Settings.bug, user=Settings.user)
                self.bug.check_settings()
                if Settings.login:
                    self.bug.login(Settings.user)
                if Settings.assign:
                    self.__do_assign()
                self.do_run()
            elif Settings.name:
                self.log.info("Processing local bug: " + Settings.name )
                self.bug = NameBug(Settings.name)
                self.do_run()
        except SettingsError as err:
            self.log.error("Incompatible settings: " + str(err))
            return 2
        except:
            self.log.error("Exception down the road...", exc_info=True)
            return 1
        return 0


if __name__ == "__main__":
    review = ReviewHelper()
    review.run()

# vim: set expandtab: ts=4:sw=4:
