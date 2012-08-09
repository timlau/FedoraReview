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
Unit tests for utilities
'''

import unittest
import os
import shutil

from glob import glob
from subprocess import check_call
from test_env import no_net

class TestExt(unittest.TestCase):

    def setUp(self):
        os.environ['REVIEW_EXT_DIRS'] = os.getcwd() + '/api'
        if os.path.exists('python-test'):
            shutil.rmtree('python-test')
        self.startdir = os.getcwd()

    def tearDown(self):
        del os.environ['REVIEW_EXT_DIRS']

    def test_display(self):
        check_call('../fedora-review -d | grep test1.sh >/dev/null', 
                   shell=True)

    @unittest.skipIf(no_net, 'No network available')
    def test_single(self):
        path  = os.environ['REVIEW_EXT_DIRS'] + '/test1.sh'
        check_call('../fedora-review -n python-test  -s ' + path + 
                   ' >/dev/null', 
                   shell=True)
        check_call('grep test1.sh python-test/python-test-review.txt' +
                   ' >/dev/null',
                    shell=True)

    @unittest.skipIf(no_net, 'No network available')
    def test_exclude(self):
        path  = os.environ['REVIEW_EXT_DIRS'] + '/test1.sh'
        check_call('../fedora-review -n python-test  -x ' + path + 
                   ' >/dev/null',
                   shell=True)
        check_call('grep -v test1.sh python-test/python-test-review.txt'+
                   ' >/dev/null',
                    shell=True)
