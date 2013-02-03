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
#    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#    MA  02110-1301 USA.
#
# pylint: disable=C0103,R0904,R0913
'''
Base class for FedoraReview tests
'''

import os
import os.path
import subprocess
import sys
import unittest2 as unittest

from urllib import urlopen

import srcpath                                   # pylint: disable=W0611
from FedoraReview import Mock, ReviewDirs, Settings
from FedoraReview.checks import Checks
from FedoraReview.name_bug import NameBug

STARTDIR = os.getcwd()

VERSION = '0.4.0'

try:
    urlopen('http://bugzilla.redhat.com')
    NO_NET = False
except IOError:
    NO_NET = True

FAST_TEST = 'REVIEW_FAST_TEST' in os.environ

FEDORA = os.path.exists('/etc/fedora-release')


class  FR_TestCase(unittest.TestCase):
    ''' Common base class for all tests. '''

    BUILDROOT = "fedora-17-i386"
    BASE_URL  = 'https://fedorahosted.org/releases/F/e/FedoraReview/'

    @staticmethod
    def abs_file_url(path):
        ''' Absolute path -> file: url. '''
        return 'file://' + os.path.abspath(path)

    def setUp(self):
        self.log = Settings.get_logger()
        self.startdir = os.getcwd()

    def tearDown(self):
        if 'REVIEW_TEST_GIT_STATUS' in os.environ:
            print
            subprocess.call('git status -uno | grep  "modified:"',
                            shell=True)
        os.chdir(self.startdir)

    def init_test(self, cd, argv=None, wd=None,
                  buildroot=None, options=None):
        '''
        Initiate a test which runs in directory cd
        kwargs:
           argv: fed to sys.argv and eventually to Settings
                 fedora-review is prepended and mock_root appended.
           wd:   review directory, cleared.
           options: mock-options'''

        cd = os.path.abspath(cd)
        os.chdir(cd)
        if not wd:
            wd = os.getcwd()
        ReviewDirs.workdir_setup(wd, 'testing')
        if not argv:
            argv = []
        args = argv
        args.insert(0, 'fedora-review')
        br = buildroot if buildroot else self.BUILDROOT
        args.append("--mock-config=" + br)
        opts = []
        if NO_NET:
            opts.append('--offline')
        if options:
            opts.append(options)
        if opts:
            argv.append('--mock-options=' + ' '.join(opts))
        sys.argv = argv
        Settings.init(True)
        Mock.clear_builddir()
        Mock.reset()

    @staticmethod
    def run_single_check(bug, check_name, run_build=False):
        ''' Run a single check, return check.'''
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file).get_checks()
        checks.set_single_check(check_name)
        if run_build:
            checks['CheckBuild'].run()
        check = checks[check_name]
        check.run()
        return check

    def run_spec(self, spec):
        ''' Run all tests for a test spec.... '''

        argv = ['-rn', spec.testcase, '-x', 'check-large-docs',
                '--no-build']
        argv.extend(spec.args)
        self.init_test(spec.testcase, wd=spec.workdir, argv=argv)
        bug = NameBug(spec.testcase)
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)
        Mock.clear_builddir()
        if os.path.exists('BUILD'):
            os.unlink('BUILD')
        with open('review.txt', 'w') as review:
            checks.run_checks(output=review)
        checkdict = checks.get_checks()
        for check in checkdict.itervalues():
            self.assertTrue(check.is_run)
            if check.is_passed or check.is_pending or check.is_failed:
                self.assertIn(check.group, spec.groups_ok,
                              check.name + ': group is ' + check.group)
        for (what, check) in spec.expected:
            state = checkdict[check].state
            if what in ['pass', 'fail', 'pending']:
                self.assertEqual(state, what,
                                 check + ': state is ' + str(state))
            elif what == 'na':
                self.assertEqual(state, None,
                                 check + ': state is ' + str(state))
            elif what.startswith == 'in_attachment':
                self.assertIn(what.split(':')[1],
                              checkdict[check].attachments[0].text)
            else:
                self.assertFalse(what)

# vim: set expandtab ts=4 sw=4:
