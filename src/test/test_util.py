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

from glob import glob
from subprocess import check_call

class TestUtil(unittest.TestCase):

    def setUp(self):
        pass

    def test_make_release(self):
        for f in glob('../../dist/*'):
            os.remove(f)
        check_call('../../make_release -b &> /dev/null', shell=True)
        distfiles = glob('../../dist/*.gz')
        self.assertEqual( len(distfiles), 1)


