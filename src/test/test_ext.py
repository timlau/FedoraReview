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

import os
import unittest2 as unittest

from subprocess import check_call

from FedoraReview import Checks, ReviewDirs, NameBug

from fr_testcase import FR_TestCase

class TestExt(FR_TestCase):

    def setUp(self):
        FR_TestCase.setUp(self)
        os.environ['REVIEW_EXT_DIRS'] = os.getcwd() + '/api'
        os.environ['XDG_DATA_HOME'] = os.getcwd()

    def tearDown(self):
        del os.environ['XDG_DATA_HOME']
        del os.environ['REVIEW_EXT_DIRS']
        FR_TestCase.tearDown(self)

    def test_display(self):
        ''' Test  -d cli option. '''
        os.chdir('test_ext')
        check_call('../../fedora-review -d | grep test1 >/dev/null',
                   shell=True)

    def test_single(self):
        ''' Test  -s test cli option. '''
        os.chdir('test_ext')
        check_call('../../fedora-review -n python-test'
                   ' -s unittest-test1'
                   ' --cache --no-build >/dev/null',
                   shell=True)

    def test_exclude(self):
        ''' Test  -x test cli option. '''
        self.init_test('test_ext',argv=['-b', '1'])
        check_call('../../fedora-review -n python-test'
                   '  -x unittest-test1'
                   ' --cache --no-build  >/dev/null',
                   shell=True)

    def test_sh_api(self):
        ''' Basic shell API test. '''
        self.init_test('test_ext',
                       argv=['-pn','python-test', '--cache',
                              '--no-build'])
        bug = NameBug('python-test')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)
        checks.checkdict['CreateEnvCheck'].run()
        checks.checkdict['unittest-test2'].run()
        self.assertTrue(checks.checkdict['unittest-test2'].is_pending)
        self.assertNotIn('CheckLargeDocs', checks.checkdict)

    def test_sh_attach(self):
        ''' Test shell attachments. '''

        self.init_test('test_ext',
                       argv=['-rn','python-test', '--no-build'])
        ReviewDirs.reset(os.getcwd())
        bug = NameBug('python-test')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file).get_checks()
        checks['CreateEnvCheck'].run()
        check = checks['test-attachments']
        check.run()
        self.assertEqual(len(check.result.attachments), 2)
        a1 = filter( lambda a: 'attachment 1' in a.text,
                     check.result.attachments)[0]
        a2 = filter( lambda a: 'attachment 2' in a.text,
                     check.result.attachments)[0]
        self.assertEqual('Heading 1',  a1.header)
        self.assertEqual(8,  a1.order_hint)
        self.assertEqual('Heading 2',  a2.header)
        self.assertEqual(9,  a2.order_hint)

    def test_srv_opt(self):
        ''' Test check of no files in /srv, /opt and /usr/local. '''
        self.init_test('srv-opt',
                       argv=['-rn','dummy', '--cache',
                              '--no-build'])
        ReviewDirs.reset(os.getcwd())
        bug = NameBug('dummy')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)
        check = checks.checkdict['CreateEnvCheck'].run()
        check = checks.checkdict['check-srv-opt-local']
        check.run()
        self.assertTrue( '/srv' in check.result.output_extra)
        self.assertTrue( '/opt' in check.result.output_extra)
        self.assertTrue( '/usr/local' in check.result.output_extra)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        suite = unittest.TestSuite()
        for test in sys.argv[1:]:
            suite.addTest(TestExt(test))
    else:
        suite = unittest.TestLoader().loadTestsFromTestCase(TestExt)
    unittest.TextTestRunner(verbosity=2).run(suite)
