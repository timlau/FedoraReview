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
# (C) 2011 - Tim Lauridsen <timlau@fedoraproject.org>
'''
Unit checks for automatic test of fedora review guidelines
'''

import os
import sys
sys.path.insert(0,os.path.abspath('../'))

import logging
import os.path
import unittest

from glob import glob

from FedoraReview import Checks, Settings, ReviewDirs
from FedoraReview.helpers import Helpers

from base import *
from test_env import no_net

class TestChecks(unittest.TestCase):

    def setUp(self):
        self.startdir = os.getcwd()
        if not os.path.exists(TEST_WORK_DIR):
            os.makedirs(TEST_WORK_DIR)
        else:
            crap = glob(os.path.join(TEST_WORK_DIR, 'results', '*.*'))
            for f in crap:
                os.unlink(f)


        sys.argv = ['test-checks','-b','1234']
        Settings.init(True)
        self.checks = None
        self.srpm = TEST_WORK_DIR + os.path.basename(TEST_SRPM)
        self.spec = TEST_WORK_DIR + os.path.basename(TEST_SPEC)
        self.source = TEST_WORK_DIR + os.path.basename(TEST_SRC)
        helper = Helpers()
        helper._get_file(TEST_SRPM, TEST_WORK_DIR)
        helper._get_file(TEST_SRC, TEST_WORK_DIR)
        helper._get_file(TEST_SPEC, TEST_WORK_DIR)
        del helper
        os.chdir(TEST_WORK_DIR)
        ReviewDirs.reset()
        ReviewDirs.workdir_setup('.', True)
        ReviewDirs.startdir = os.getcwd()


    @unittest.skipIf(no_net, 'No network available')
    def test_all_checks(self):
        ''' Run all automated review checks'''
        checks = Checks(self.spec, self.srpm)
        checks.run_checks(writedown=False)
        # Automatic Checks
        checkdict = checks.get_checks()
        for check in checkdict.itervalues():
            self.assertTrue(hasattr(check, 'result'))
        os.chdir(self.startdir)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestChecks)
    unittest.TextTestRunner(verbosity=2).run(suite)
