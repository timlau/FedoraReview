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

from FedoraReview import Checks, Settings, ReviewDirs, NameBug

from fr_testcase import FR_TestCase, NO_NET

class TestExt(FR_TestCase):

    def setUp(self):
        FR_TestCase.setUp(self)
        os.environ['REVIEW_EXT_DIRS'] = os.getcwd() + '/api'
        os.environ['REVIEW_SCRIPT_DIRS'] = os.getcwd() + '/sh-api'

    def tearDown(self):
        FR_TestCase.tearDown(self)
        del os.environ['REVIEW_EXT_DIRS']

    def test_display(self):
        os.chdir('test_ext')
        check_call('../../fedora-review -d | grep test1 >/dev/null',
                   shell=True)

    @unittest.skipIf(NO_NET, 'No network available')
    def test_single(self):
        os.chdir('test_ext')
        check_call('../../fedora-review -n python-test  -s test1 '
                   ' >/dev/null',
                   shell=True)

    @unittest.skipIf(NO_NET, 'No network available')
    def test_exclude(self):
        self.init_test('test_ext',argv=['-b', '1'], wd='python-test')
        check_call('../../fedora-review -n python-test  -x test1'
                   ' >/dev/null',
                   shell=True)

    def test_sh_api(self):
        self.init_test('test_ext',
                       argv=['-pn','python-test'], wd='python-test')
        bug = NameBug('python-test')
        check = self.run_single_check(bug,'check-large-docs.sh')
        self.assertEqual(check.result.result, 'pending')

