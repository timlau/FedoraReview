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

import ansi
import os.path
import sys
import time

from bugzilla_bug import BugzillaBug
from check_base import SimpleTestResult
from checks import Checks, ChecksLister
from mock import Mock
from name_bug import NameBug
from review_dirs import ReviewDirs
from review_error import ReviewError, SpecParseReviewError
from settings import Settings
from url_bug import UrlBug
from version import __version__, BUILD_FULL
from reports import write_xml_report


_EXIT_MESSAGE = """\
fedora-review is automated tool, but *YOU* are responsible for manually
reviewing the results and finishing the review. Do not just copy-paste
the results without understanding them.
"""


def _print_version():
    ''' Handle --version option. '''
    print('fedora-review version ' + __version__ + ' ' + BUILD_FULL)


class _Nvr(object):
    ''' Simple name-version-release container. '''

    def __init__(self, name, version='?', release='?'):
        self.name = name
        self.version = version
        self.release = release


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

    def _do_report(self, outfile=None):
        ''' Create a review report'''
        clock = time.time()
        self.log.info('Getting .spec and .srpm Urls from : '
                       + self.bug.get_location())

        Settings.dump()
        if not self.bug.find_urls():
            raise self.HelperError('Cannot find .spec or .srpm URL(s)')
        self.log.debug("find_urls completed: %.3f"
                           % (time.time() - clock))
        clock = time.time()

        if not ReviewDirs.is_inited:
            wd = self.bug.get_dirname()
            ReviewDirs.workdir_setup(wd)
        if Mock.is_available():
            Mock.init()

        if not self.bug.download_files():
            raise self.HelperError('Cannot download .spec and .srpm')
        self.log.debug("Url download completed: %.3f" % (time.time() - clock))

        Settings.name = self.bug.get_name()
        self._run_checks(self.bug.spec_file, self.bug.srpm_file, outfile)

    def _run_checks(self, spec, srpm, outfile=None):
        ''' Register and run all checks. '''

        def apply_color(s, formatter):
            ''' Return s formatted by formatter or plain s. '''
            return formatter(s) if Settings.use_colors else s

        self.checks = Checks(spec, srpm)
        if outfile:
            self.outfile = outfile
        elif Settings.no_report:
            self.outfile = '/dev/null'
        else:
            self.outfile = ReviewDirs.report_path()
        with open(self.outfile, "w") as output:
            self.log.info('Running checks and generating report')
            self.checks.run_checks(output=output,
                                   writedown=not Settings.no_report)
        if not Settings.no_report:
            print apply_color("Review template in: " + self.outfile,
                              ansi.green)
            print apply_color(_EXIT_MESSAGE, ansi.red)

    @staticmethod
    def _list_flags():
        ''' List all flags in simple, user-friendly format. '''
        checks_lister = ChecksLister()
        for flag in checks_lister.flags.itervalues():
            print flag.name + ': ' + flag.doc

    @staticmethod
    def _list_plugins():
        ''' --display-plugins implementation. '''
        checks_lister = ChecksLister()
        plugins = checks_lister.get_plugins()
        print ', '.join(plugins)

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
                        print '    %s: %s' % (c.name, c.text)
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

    def _do_run(self, outfile=None):
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
        elif Settings.list_plugins:
            self._list_plugins()
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
            if not Mock.is_available() and not Settings.prebuilt:
                raise ReviewError("Mock unavailable, --prebuilt must be used.")
            self._do_report(outfile)

    def run(self, outfile=None):
        ''' Load urls, run checks and make report, '''
        started_at = time.time()
        self.log.debug('fedora-review ' + __version__ + ' ' +
                         BUILD_FULL + ' started')
        self.log.debug("Command  line: " + ' '.join(sys.argv))
        try:
            rcode = 0
            self._do_run(outfile)
        except ReviewError as err:
            if isinstance(err, SpecParseReviewError):
                nvr = _Nvr(self.bug.get_name())
                result = SimpleTestResult("SpecFileParseError",
                                          "Can't parse the spec file: ",
                                          str(err))
                write_xml_report(nvr, [result])
            self.log.debug("ReviewError: " + str(err), exc_info=True)
            if not err.silent:
                msg = 'ERROR: ' + str(err)
                if err.show_logs:
                    msg += ' (logs in ' + Settings.session_log + ')'
                self.log.error(msg)
            rcode = err.exitcode
        except:
            self.log.debug("Exception down the road...", exc_info=True)
            self.log.error('Exception down the road...'
                           '(logs in ' + Settings.session_log + ')')
            rcode = 1
        self.log.debug("Report completed:  %.3f seconds"
                           % (time.time() - started_at))
        return rcode


if __name__ == "__main__":
    ReviewHelper().run()

# vim: set expandtab ts=4 sw=4:
