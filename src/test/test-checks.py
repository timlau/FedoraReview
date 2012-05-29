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
Unit checks for automatic test of fedora review guidelines
'''

import logging
import sys
import os.path
sys.path.insert(0,os.path.abspath('../'))

import os
import unittest

import FedoraReview
from FedoraReview import Helpers, Settings
from FedoraReview.checks_class import Checks
from bugzilla import Bugzilla
from base import *

class TestChecks(unittest.TestCase):

    def setUp(self):
        FedoraReview.do_logger_setup(loglvl=logging.INFO)
        sys.argv = ['test-checks','-b','1234']
        Settings.init()
        if not os.path.exists(TEST_WORK_DIR):
            os.makedirs(TEST_WORK_DIR)
        self.checks = None
        self.srpm = TEST_WORK_DIR + os.path.basename(TEST_SRPM)
        self.spec = TEST_WORK_DIR + os.path.basename(TEST_SPEC)
        self.source = TEST_WORK_DIR + os.path.basename(TEST_SRC)
        helper = Helpers()
        helper._get_file(TEST_SRPM, TEST_WORK_DIR)
        helper._get_file(TEST_SRC, TEST_WORK_DIR)
        helper._get_file(TEST_SPEC, TEST_WORK_DIR)
        del helper

    def test_all_checks(self):
        ''' Run all automated review checks'''
        print('Setup Checks')
        self.checks = Checks(self.spec, self.srpm)
        print('Running All Checks')
        self.checks.run_checks(writedown=False)
        # Automatic Checks
        checks = self.checks.checks
        for check in checks:
            result = check.get_result()
            self.assertNotEqual(result, None)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestChecks)
    unittest.TextTestRunner(verbosity=2).run(suite)
