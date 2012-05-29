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

from FedoraReview import Settings, FedoraReviewError, Mock
from FedoraReview.bugz import ReviewBug
from FedoraReview.url_bug import UrlBug
from FedoraReview.name_bug import NameBug
from FedoraReview.abstract_bug import SettingsError,BugException
from FedoraReview.checks_class import Checks, ChecksLister


class ConfigError(FedoraReviewError):
    def __init__(self, what):
        FedoraReviewError.__init__(self, 'Configuration error: ' + what)


class HandledError(FedoraReviewError):
    def __init__(self, msg='Errors encountered, goodbye'):
        FedoraReviewError.__init__(self, msg)


class ReviewHelper:

    def __init__(self):
        self.bug = None
        self.checks = None
        Settings.workdir = os.path.expanduser(Settings.workdir)
        self.log = FedoraReview.get_logger()
        self.verbose = False
        self.outfile = None
        self.prebuilt = False

    def __download_sources(self):
        sources = self.checks.spec.get_sources('Source')
        return True

    def __do_report(self):
        ''' Create a review report'''

        self.log.info('Getting .spec and .srpm Urls from : '
                       + self.bug.get_location())
        if Settings.bug:
            Settings.workdir = os.path.join(Settings.workdir,
                                            Settings.bug)
        Settings.dump()
        if not self.bug.find_urls():
            self.log.error( 'Cannot find .spec or .srpm URL(s)')
            raise HandledError()
        if Settings.grab:
            print "Srpm URL:" + self.bug.srpm_url
            print "Spec URL:" + self.bug.spec_url
            return

        if not self.bug.download_files():
            self.log.error('Cannot download .spec and .srpm')
            raise HandledError()

        Settings.name = self.bug.get_name()
        self.__run_checks(self.bug.spec_file, self.bug.srpm_file)

    def __list_checks(self):
        """ List all the checks available.
        """
        ChecksLister().list()

    def __print_version(self):
        print('fedora-review version ' + FedoraReview.__version__)

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

    def run(self):
        try:
            Settings.init()
            lvl = logging.DEBUG if Settings.verbose else None
            FedoraReview.do_logger_setup(loglvl=lvl)

            if Settings.list_checks:
                self.__list_checks()
                return 0
            elif Settings.version:
                self.__print_version()
                return 0

            if Settings.url:
                self.log.info("Processing bug on url: " + Settings.url )
                self.bug = UrlBug(Settings.url)
            elif Settings.bug:
                self.log.info("Processing bugzilla bug: " + Settings.bug )
                self.bug = ReviewBug(Settings.bug, user=Settings.user)
            elif Settings.name:
                self.log.info("Processing local files: " + Settings.name )
                self.bug = NameBug(Settings.name)
            if not Settings.noreport:
                self.__do_report()

        except BugException as err:
            print str(err)
            return 2
        except HandledError as err:
            print str(err)
            return 2
        except SettingsError as err:
            self.log.error("Incompatible settings: " + str(err))
            return 2
        except:
            self.log.debug("Exception down the road...", exc_info=True)
            self.log.error("Exception down the road...")
            return 1
        return 0


if __name__ == "__main__":
    review = ReviewHelper()
    review.run()

# vim: set expandtab: ts=4:sw=4:
