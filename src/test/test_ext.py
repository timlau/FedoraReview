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
Unit tests for utilities
'''
import sys
import os.path
sys.path.insert(0,os.path.abspath('../'))

import unittest
import os
import shutil

from glob import glob
from subprocess import check_call
from test_env import no_net

from FedoraReview import Checks, Settings, ReviewDirs, NameBug

class TestExt(unittest.TestCase):

    def setUp(self):
        os.environ['REVIEW_EXT_DIRS'] = os.getcwd() + '/api'
        os.environ['REVIEW_SCRIPT_DIRS'] = os.getcwd() + '/sh-api'
        if os.path.exists('python-test'):
            shutil.rmtree('python-test')
        self.startdir = os.getcwd()

    def run_single_check(self, bug, check_name):
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file).get_checks()
        checks.set_single_check(check_name)
        self.assertEqual(len(checks), 1)
        check = checks[check_name]
        check.run()
        return check


    def tearDown(self):
        del os.environ['REVIEW_EXT_DIRS']

    def test_display(self):
        check_call('../fedora-review -d | grep test1 >/dev/null', 
                   shell=True)

    @unittest.skipIf(no_net, 'No network available')
    def test_single(self):
        check_call('../fedora-review -n python-test  -s test1 '  
                   ' >/dev/null', 
                   shell=True)

    @unittest.skipIf(no_net, 'No network available')
    def test_exclude(self):
        check_call('../fedora-review -n python-test  -x test1' 
                   ' >/dev/null',
                   shell=True)
