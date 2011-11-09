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



import sys
import os.path
sys.path.insert(0,os.path.abspath('../'))

import os
import os.path
import unittest
from reviewtools import Helpers
from reviewtools.misc import Checks
from bugzilla import Bugzilla
from base import *

class CheckCaseChecks(unittest.TestCase):
    def __init__(self, methodName='runCheck'):
        unittest.TestCase.__init__(self, methodName)
        self.checks = None
        self.srpm = TEST_WORK_DIR + os.path.basename(TEST_SRPM)
        self.spec = TEST_WORK_DIR + os.path.basename(TEST_SPEC)
        self.source = TEST_WORK_DIR + os.path.basename(TEST_SRC)
        
    def setUp(self):
        if not os.path.exists(TEST_WORK_DIR):
            os.makedirs(TEST_WORK_DIR)
        helper = Helpers()
        helper.set_work_dir(TEST_WORK_DIR)
        helper._get_file(TEST_SRPM)
        helper._get_file(TEST_SRC)
        helper._get_file(TEST_SPEC)
        del helper 

    def test_all_checks(self):
        ''' Run all automated review checks'''
        print('Setup Checks')
        self.checks = Checks(None, spec_file=self.spec, srpm_file=self.srpm)
        print('Running All Checks')
        self.checks.run_checks(writedown=False)
        # Automatic Checks
        checks = self.checks.checks
        for check in checks:
            result = check.get_result()
            self.assertNotEqual(result, None)

suite = unittest.TestLoader().loadTestsFromTestCase(CheckCaseChecks)
unittest.TextTestRunner(verbosity=2).run(suite)
