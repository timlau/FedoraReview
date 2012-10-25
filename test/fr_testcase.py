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

import os
import os.path
import shutil
import subprocess
import sys
import unittest2 as unittest

from urllib import urlopen

import srcpath
from FedoraReview import Mock, ReviewDirs, Settings
from FedoraReview.checks import Checks

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
        if 'REVIEW_TEST_GIT_STATUS' in os.environ:
            print
            subprocess.call('git status -uno | grep  "modified:"',
                            shell=True)
        os.chdir(self.startdir)

    def init_test(self, cd, argv=[], wd=None,
                  buildroot=None, options=None):
        # Initiate a test which runs in directory cd
        # kwargs:
        #    argv: fed to sys.argv and eventually to Settings
        #          fedora-review is prepended and mock_root appended.
        #    wd:   review directory, cleared.
        #    options: mock-options
        cd = os.path.abspath(cd)
        os.chdir(cd)
        if not wd:
            wd = os.getcwd()
        ReviewDirs.workdir_setup(wd, 'testing')
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
        Mock.clear_builddir()
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
