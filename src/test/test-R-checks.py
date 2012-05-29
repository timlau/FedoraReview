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
'''
Unit checks for automatic test of fedora R review guidelines
'''



import logging
import sys
import os
import os.path
sys.path.insert(0,os.path.abspath('../'))
import unittest
import FedoraReview
from FedoraReview import Helpers, Settings
from FedoraReview.checks_class import Checks
from FedoraReview.checks import R
from bugzilla import Bugzilla
from base import *

class TestRChecks(unittest.TestCase):

    def setUp(self):
        sys.argv = ['test-R-checks','-b','1234']
        Settings.init()
        FedoraReview.do_logger_setup(loglvl=logging.DEBUG)
        self.checks = None
        self.srpm = TEST_WORK_DIR + os.path.basename(R_TEST_SRPM)
        self.spec = TEST_WORK_DIR + os.path.basename(R_TEST_SPEC)
        self.source = TEST_WORK_DIR + os.path.basename(R_TEST_SRC)
        if not os.path.exists(TEST_WORK_DIR):
            os.makedirs(TEST_WORK_DIR)
        helper = Helpers()
        helper._get_file(R_TEST_SRPM, TEST_WORK_DIR)
        helper._get_file(R_TEST_SPEC, TEST_WORK_DIR)
        helper._get_file(R_TEST_SRC, TEST_WORK_DIR)
        del helper

    def test_all_checks(self):
        ''' Run all automated review checks'''
        print('Setup Checks')
        self.checks = Checks(self.spec, self.srpm)
        print('Running R Checks')
        self.checks.run_checks(writedown=False)
        for check in self.checks.checks:
            if check.is_applicable():
                self.assertTrue(check.header == 'Generic' or check.header == 'R')
                result = check.get_result()
                self.assertNotEqual(result[1:2], '!')


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRChecks)
    unittest.TextTestRunner(verbosity=2).run(suite)
