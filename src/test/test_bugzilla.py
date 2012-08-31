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
Unit tests for bugzilla bug handling
'''


import sys
import os.path
sys.path.insert(0,os.path.abspath('../'))

import os
import unittest

from FedoraReview import BugzillaBug

from fr_testcase import FR_TestCase, NO_NET

class TestBugzilla(FR_TestCase):
    TEST_BUG = '672280'

    @unittest.skipIf(NO_NET, 'No network available')
    def test_find_urls(self):
        self.init_test('bugzilla',
                       argv=['-b', self.TEST_BUG], wd='python-test')
        self.bug = BugzillaBug(self.TEST_BUG)
        ''' Test that we can get the urls from a bugzilla report'''
        rc = self.bug.find_urls()
        self.assertTrue(rc)
        home = 'http://timlau.fedorapeople.org/files/test/review-test'
        self.assertEqual(self.bug.srpm_url,
                         os.path.join(home,
                                      'python-test-1.0-1.fc14.src.rpm'))
        self.assertEqual(self.bug.spec_url,
                         os.path.join(home, 'python-test.spec'))


    @unittest.skipIf(NO_NET, 'No network available')
    def test_download_files(self):
        self.init_test('bugzilla',
                       argv=['-b', self.TEST_BUG], wd='python-test')
        self.bug = BugzillaBug(self.TEST_BUG)
        '''
        Test that we can download the spec and srpm from a bugzilla report
        '''
        self.bug.find_urls()
        rc = self.bug.download_files()
        self.assertTrue(rc)
        self.assertEqual(self.bug.srpm_url,
                         'http://timlau.fedorapeople.org/files/test'
                         '/review-test/python-test-1.0-1.fc14.src.rpm')
        self.assertEqual(self.bug.spec_url,
                         'http://timlau.fedorapeople.org/files/test/'
                          'review-test/python-test.spec')

        cd = os.path.abspath('./srpm')
        srpm = os.path.join(cd,  'python-test-1.0-1.fc14.src.rpm')
        spec = os.path.join(cd,  'python-test.spec')
        self.assertEqual(self.bug.srpm_file, srpm)
        self.assertEqual(self.bug.spec_file, spec)
        self.assertTrue(os.path.exists(srpm))
        self.assertTrue(os.path.exists(spec))

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestBugzilla)
    unittest.TextTestRunner(verbosity=2).run(suite)
