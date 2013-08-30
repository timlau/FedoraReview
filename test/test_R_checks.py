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
# pylint: disable=C0103,R0904,R0913,W0201
'''
Unit checks for automatic test of fedora R review guidelines
'''

import os
import sys
import unittest2 as unittest

import srcpath                                   # pylint: disable=W0611
from FedoraReview.checks import Checks
from FedoraReview.name_bug import NameBug
from FedoraReview.spec_file import SpecFile

from fr_testcase import FR_TestCase, FAST_TEST


class TestRChecks(FR_TestCase):
    ''' Some R specific tests. '''

    R_TEST_SRPM = 'https://fedorahosted.org/releases/F/e' \
                  '/FedoraReview/R-Rdummypkg-1.0-2.fc15.src.rpm'
    R_TEST_SPEC = FR_TestCase.BASE_URL + 'R-Rdummypkg.spec'
    R_TEST_SRC  = FR_TestCase.BASE_URL + 'Rdummypkg_1.0.tar.gz'

    def setUp(self):
        if not srcpath.PLUGIN_PATH in sys.path:
            sys.path.append(srcpath.PLUGIN_PATH)
        self.startdir = os.getcwd()

    def test_good_R_spec(self):
        ''' test R spec, expected to pass. '''
        # pylint: disable=F0401,R0201,C0111

        from plugins.R import RCheckInstallSection

        class ChecksMockup(object):
            pass

        class ApplicableRCheckInstallSection(RCheckInstallSection):
            def is_applicable(self):
                return True

        self.init_test('test-R',
                        argv=['-rpn', 'R-Rdummypkg', '--no-build'])
        spec = SpecFile(os.path.join(os.getcwd(), 'R-Rdummypkg.spec'))
        check = ApplicableRCheckInstallSection(ChecksMockup())
        check.checks.spec = spec
        check.run()
        self.assertTrue(check.is_passed)

    def test_bad_R_spec(self):
        ''' test R spec, expected to fail. '''
        # pylint: disable=F0401,R0201,C0111

        from plugins.R import RCheckInstallSection

        class ChecksMockup(object):
            pass

        class ApplicableRCheckInstallSection(RCheckInstallSection):
            def is_applicable(self):
                return True

        self.init_test('test-R',
                        argv=['-rpn', 'R-Rdummypkg', '--no-build'])
        spec = SpecFile(os.path.join(os.getcwd(), 'R-Rdummypkg-bad.spec'))
        check = ApplicableRCheckInstallSection(ChecksMockup())
        check.checks.spec = spec
        check.run()
        note = check.result.output_extra
        self.assertTrue(check.is_failed)
        self.assertTrue('directory creation' in note)
        self.assertTrue('removal of *.o and *.so' in note)
        self.assertTrue('removal of the R.css file' in note)
        self.assertTrue('R CMD INSTALL function' in note)

    @unittest.skipIf(FAST_TEST, 'slow test disabled by REVIEW_FAST_TEST')
    def test_all_checks(self):
        ''' Run all automated review checks'''
        self.init_test('test-R',
                        argv=['-rpn', 'R-Rdummypkg', '--no-build'])
        self.bug = NameBug('R-Rdummypkg')
        self.bug.find_urls()
        self.bug.download_files()
        self.checks = Checks(self.bug.spec_file, self.bug.srpm_file)
        self.checks.run_checks(writedown=False)
        for check in self.checks.checkdict.itervalues():
            if check.is_passed or check.is_pending or check.is_failed:
                ok_groups = ['Generic.build', 'Generic', 'Generic.should', 'R']
                self.assertIn(check.group, ok_groups)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        suite = unittest.TestSuite()
        for test in sys.argv[1:]:
            suite.addTest(TestRChecks(test))
    else:
        suite = unittest.TestLoader().loadTestsFromTestCase(TestRChecks)
    unittest.TextTestRunner(verbosity=2).run(suite)

# vim: set expandtab ts=4 sw=4:
