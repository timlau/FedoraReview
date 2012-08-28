#!/usr/bin/python -tt
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
#    Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
'''
Unit checks for automatic test of fedora R review guidelines
'''


import os
import os.path
import shutil
import sys
import unittest

sys.path.insert(0,os.path.abspath('../'))
from FedoraReview import Settings, Checks, ReviewDirs, NameBug
from FedoraReview.checks import R

from fr_testcase import FR_TestCase, NO_NET

class TestRChecks(FR_TestCase):

    R_TEST_SRPM =            'https://fedorahosted.org/releases/F/e' \
                             '/FedoraReview/R-Rdummypkg-1.0-2.fc15.src.rpm'
    R_TEST_SPEC = FR_TestCase.BASE_URL + 'R-Rdummypkg.spec'
    R_TEST_SRC  = FR_TestCase.BASE_URL + 'Rdummypkg_1.0.tar.gz'

    def test_all_checks(self):
        ''' Run all automated review checks'''
        self.init_test('test-R',
                        argv=['-rpn','R-Rdummypkg', '--cache'])
        ReviewDirs.reset()
        self.bug = NameBug('R-Rdummypkg')
        self.bug.find_urls()
        self.bug.download_files()
        self.checks = Checks(self.bug.spec_file, self.bug.srpm_file)
        self.checks.run_checks(writedown=False)
        for check in self.checks.checkdict.itervalues():
            if check.result:
                self.assertTrue(check.group == 'Generic' or
                                check.group == 'R')
                self.assertIn(check.result.result,
                              ['pass','pending','fail'])


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRChecks)
    unittest.TextTestRunner(verbosity=2).run(suite)
