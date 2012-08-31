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

import os.path
import unittest


from FedoraReview import Checks

from fr_testcase import FR_TestCase

class TestChecks(FR_TestCase):

    def setUp(self):
        FR_TestCase.setUp(self)
        self.init_test('test-checks',
                        argv=['-b','1234', '--cache', '--no-build'])
        #for crap in glob(os.path.join(os.getcwd(), 'results', '*.*')):
        #      os.unlink(crap)

        self.checks = None
        self.srpm = os.path.join(os.getcwd(),
                            'python-test-1.0-1.fc16.src.rpm')
        self.spec = os.path.join(os.getcwd(),'python-test.spec')
        self.source = os.path.join(os.getcwd(),
                                   'python-test-1.0.tar.gz')


    #@unittest.skipIf(NO_NET, 'No network available')
    def test_all_checks(self):
        ''' Run all automated review checks'''
        checks = Checks(self.spec, self.srpm)
        checks.run_checks(writedown=False)
        checkdict = checks.get_checks()
        for check in checkdict.itervalues():
            self.assertTrue(check.is_run)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestChecks)
    unittest.TextTestRunner(verbosity=2).run(suite)
