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

import sys
import os.path

from FedoraReview import  BugzillaBug, Checks, ChecksLister, ReviewDirs, \
                          ReviewError, NameBug, Settings, UrlBug

from FedoraReview import __version__, BUILD_FULL


def _print_version():
    ''' Handle --version option. '''
    print('fedora-review version ' + __version__ + ' ' + BUILD_FULL)


class ReviewHelper(object):
    ''' Make most of the actual work doing the review. '''

    class HelperError(ReviewError):
        ''' Error while processing bug. '''
        def __init__(self, msg):
            ReviewError.__init__(self, msg)

    def __init__(self):
        self.bug = None
        self.checks = None
        self.log = Settings.get_logger()
        self.verbose = False
        self.outfile = None
        self.prebuilt = False

    def __download_sources(self):
        ''' Download and extract all upstream sources. '''
        self.sources.extract_all()
        return True

    def __do_report(self):
        ''' Create a review report'''
        self.log.info('Getting .spec and .srpm Urls from : '
                       + self.bug.get_location())

        Settings.dump()
        if not self.bug.find_urls():
            raise self.HelperError('Cannot find .spec or .srpm URL(s)')

        if not ReviewDirs.is_inited:
            wd = self.bug.get_dirname()
            ReviewDirs.workdir_setup(wd)

        if not self.bug.download_files():
            raise self.HelperError('Cannot download .spec and .srpm')

        Settings.name = self.bug.get_name()
        self.__run_checks(self.bug.spec_file, self.bug.srpm_file)

    def __run_checks(self, spec, srpm):
        ''' Register and run all checks. '''
        self.checks = Checks(spec, srpm)
        if Settings.no_report:
            self.outfile = '/dev/null'
        else:
            self.outfile = ReviewDirs.report_path(self.checks.spec.name)
        with open(self.outfile, "w") as output:
            if Settings.nobuild:
                self.checks.srpm.is_build = True
            self.log.info('Running checks and generate report\n')
            self.checks.run_checks(output=output,
                                   writedown=not Settings.no_report)
            output.close()
        if not Settings.no_report:
            print "\033[92mReview template in: %s\033[0m" % self.outfile
            print "\033[91mfedora-review is automated tool, but *YOU* " \
                  "are responsible for manually reviewing the results " \
                  "and finishing the review. Do not just copy-paste the " \
                  "results without understanding them.\033[0m"

    @staticmethod
    def _list_flags():
        ''' List all flags in simple, user-friendly format. '''
        checks_lister = ChecksLister()
        for flag in checks_lister.flags.itervalues():
            print flag.name + ': ' + flag.doc


    @staticmethod
    def _list_checks():
        """ List all the checks and flags available.  """

        def list_data_by_file(files, checks_list):
            ''' print filename + flags and checks defined in it. '''
            for f in sorted(files):
                print 'File:  ' + f
                flags_by_src = filter(lambda c: c.defined_in == f,
                                      checks_lister.flags.itervalues())
                for flag in flags_by_src:
                    print 'Flag: ' + flag.name
                files_per_src = filter(lambda c: c.defined_in == f,
                                       checks_list)
                groups = list(set([c.group for c in files_per_src]))
                for group in sorted(groups):

                    def check_match(c):
                        ''' check in correct group and file? '''
                        return c.group == group and c.defined_in == f

                    checks = filter(check_match, checks_list)
                    if checks == []:
                        continue
                    print 'Group: ' + group
                    for c in sorted(checks):
                        print '    ' + c.name
                print

        checks_lister = ChecksLister()
        checks_list = list(checks_lister.get_checks().itervalues())
        files = list(set([c.defined_in for c in checks_list]))
        list_data_by_file(files, checks_list)
        deps_list = filter(lambda c: c.needs != [] and
                               c.needs != ['CheckBuildCompleted'],
                           checks_list)
        for dep in deps_list:
            print'Dependencies: ' + dep.name + ': ' + \
                os.path.basename(dep.defined_in)
            for needed in dep.needs:
                print '     ' + needed
        deprecators = filter(lambda c: c.deprecates != [], checks_list)
        for dep in deprecators:
            print 'Deprecations: ' + dep.name + ': ' + \
                os.path.basename(dep.defined_in)
            for victim in dep.deprecates:
                print '    ' + victim

    def _do_run(self):
        ''' Initiate, download url:s, run checks a write report. '''
        Settings.init()
        make_report = True
        if Settings.list_checks:
            self._list_checks()
            make_report = False
        elif Settings.list_flags:
            self._list_flags()
            make_report = False
        elif Settings.version:
            _print_version()
            make_report = False
        elif Settings.url:
            self.log.info("Processing bug on url: " + Settings.url)
            self.bug = UrlBug(Settings.url)
        elif Settings.bug:
            self.log.info("Processing bugzilla bug: " + Settings.bug)
            self.bug = BugzillaBug(Settings.bug)
        elif Settings.name:
            self.log.info("Processing local files: " + Settings.name)
            self.bug = NameBug(Settings.name)
        if make_report:
            self.__do_report()

    def run(self):
        ''' Load urls, run checks and make report, '''
        self.log.debug("Command  line: " + ' '.join(sys.argv))
        try:
            rcode = 0
            self._do_run()
        except ReviewError as err:
            rcode = err.exitcode
            self.log.debug("ReviewError: " + str(err), exc_info=True)
            if not err.silent:
                msg = 'Error: ' + str(err)
                if err.show_logs:
                    msg += ' (logs in ~/.cache/fedora-review.log)'
                self.log.error(msg)
        except:
            self.log.debug("Exception down the road...", exc_info=True)
            self.log.error('Exception down the road...'
                           '(logs in ~/.cache/fedora-review.log)')
            rcode = 1
        return rcode


if __name__ == "__main__":
    ReviewHelper().run()

# vim: set expandtab: ts=4:sw=4:
