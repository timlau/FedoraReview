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
from test_env import no_net, check_python_test

from FedoraReview import Checks, Settings, ReviewDirs, Mock, NameBug

class TestExt(unittest.TestCase):

    def setUp(self):
        os.environ['REVIEW_EXT_DIRS'] = os.path.join(os.getcwd(),
                                                     'api')
        os.environ['REVIEW_SCRIPT_DIRS'] = os.path.join(os.getcwd(),
                                                     'sh-api')
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
        os.chdir('python-test.repo')
        check_call('../../fedora-review -d | grep test1 >/dev/null', 
                   shell=True)
        os.chdir(self.startdir)

    def test_single(self):
        check_python_test()
        os.chdir('python-test.repo')
        check_call('../../fedora-review --no-build -rcpn python-test'
                      ' -s test1  >/dev/null', 
                   shell=True)
        os.chdir(self.startdir)

    def test_exclude(self):
        check_python_test()
        os.chdir('python-test.repo')
        check_call('../../fedora-review --no-build -rcpn python-test'
                      ' -x test1  >/dev/null',
                   shell=True)
        os.chdir(self.startdir)

    def test_sh_api(self):
        check_python_test()
        os.chdir('python-test.repo')
        sys.argv = ['../../fedora-review']
        sys.argv .extend(['--no-build', '-rcpn','python-test'])
        Settings.init(True)
        ReviewDirs.reset('.')
        bug = NameBug('python-test')
        check = self.run_single_check(bug,'check-large-docs.sh')
        self.assertEqual(check.result.result, 'pending')
        os.chdir(self.startdir)

