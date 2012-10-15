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
Base class for FedoraReview tests
'''

import sys
import os.path
sys.path.insert(0,os.path.abspath('../'))

import unittest2 as unittest
import os
import shutil

from urllib import urlopen

from FedoraReview import Checks, ReviewDirs,  Mock, Settings

STARTDIR = os.getcwd()

VERSION = '0.3.1'

try:
    urlopen('http://bugzilla.redhat.com')
    NO_NET = False
except:
    NO_NET = True

FAST_TEST = 'REVIEW_FAST_TEST' in os.environ


class  FR_TestCase(unittest.TestCase):

    BUILDROOT = "fedora-17-i386"
    BASE_URL  = 'https://fedorahosted.org/releases/F/e/FedoraReview/'

    def abs_file_url(self, path):
        return 'file://' +  os.path.abspath(path)

    def setUp(self):
        self.log = Settings.get_logger()
        self.startdir = os.getcwd()

    def tearDown(self):
        os.chdir(self.startdir)

    def init_test(self, cd, argv=[], wd=None,
                  buildroot=None, options=None):
        # Initiate a test which runs in directory cd
        # kwargs:
        #    argv: fed to sys.argv and eventually to Settings
        #          fedora-review is prepended and mock_root appended.
        #    wd:   review directory, cleared.
        #    options: mock-options
        os.chdir(cd)
        if wd:
            if os.path.exists(wd):
                shutil.rmtree(wd)
        ReviewDirs.reset(cd)
        ReviewDirs.workdir_setup(os.getcwd(), True)
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
            argv.append('--mock-options=' +  ' '.join(opts))
        sys.argv = argv
        Settings.init(True)
        Mock.reset()

    def run_single_check(self, bug, check_name, run_build=False):
        # Run a single check, return check.
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file).get_checks()
        checks.set_single_check(check_name)
        if run_build:
            checks['CheckBuild'].run()
        check = checks[check_name]
        check.run()
        return check
