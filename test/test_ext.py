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
#    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#    MA  02110-1301 USA.
#
# pylint: disable=C0103,R0904,R0913
# (C) 2011 - Tim Lauridsen <timlau@fedoraproject.org>
'''
Unit tests for utilities
'''

import os
import sys
import unittest2 as unittest

from subprocess import check_call

import srcpath                                   # pylint: disable=W0611
from FedoraReview.checks import Checks
from FedoraReview.name_bug import NameBug

from fr_testcase import FR_TestCase


class TestExt(FR_TestCase):
    ''' Tests for externally loaded plugins and scripts. '''

    def setUp(self):
        FR_TestCase.setUp(self)
        os.environ['REVIEW_EXT_DIRS'] = os.getcwd() + '/api'
        os.environ['XDG_DATA_HOME'] = os.getcwd()

    def tearDown(self):
        del os.environ['XDG_DATA_HOME']
        del os.environ['REVIEW_EXT_DIRS']
        FR_TestCase.tearDown(self)

    @staticmethod
    def test_display():
        ''' Test  -d cli option. '''
        os.chdir('test_ext')
        check_call(srcpath.REVIEW_PATH + ' -d | grep test1 >/dev/null',
                   shell=True)

    @staticmethod
    def test_single():
        ''' Test  -s test cli option. '''
        os.chdir('test_ext')
        check_call(srcpath.REVIEW_PATH + ' -n python-test'
                   ' -s unittest-test1'
                   ' --cache --no-build >/dev/null',
                   shell=True)

    def test_exclude(self):
        ''' Test  -x test cli option. '''
        self.init_test('test_ext', argv=['-b', '1'], wd='review-python-test')
        os.chdir('..')
        check_call(srcpath.REVIEW_PATH + ' -pn python-test'
                   '  -x unittest-test1' +
                   ' -m ' + self.BUILDROOT +
                   ' --cache --no-build >/dev/null',
                   shell=True)

    def test_sh_api(self):
        ''' Basic shell API test. '''
        self.init_test('test_ext',
                       argv=['-pn', 'python-test', '--cache',
                              '--no-build'],
                       wd='review-python-test')
        bug = NameBug('python-test')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)
        checks.checkdict['CreateEnvCheck'].run()
        checks.checkdict['unittest-test2'].run()
        self.assertTrue(checks.checkdict['unittest-test2'].is_pending)

    def test_sh_attach(self):
        ''' Test shell attachments. '''

        self.init_test('test_ext',
                       argv=['-rn', 'python-test', '--no-build'])
        bug = NameBug('python-test')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file).get_checks()
        checks['CreateEnvCheck'].run()
        check = checks['test-attachments']
        check.run()
        self.assertEqual(len(check.result.attachments), 2)
        a1 = filter(lambda a: 'attachment 1' in a.text,
                    check.result.attachments)[0]
        a2 = filter(lambda a: 'attachment 2' in a.text,
                    check.result.attachments)[0]
        self.assertEqual('Heading 1', a1.header)
        self.assertEqual(8, a1.order_hint)
        self.assertEqual('Heading 2', a2.header)
        self.assertEqual(9, a2.order_hint)

    def test_srv_opt(self):
        ''' Test check of no files in /srv, /opt and /usr/local. '''
        self.init_test('srv-opt',
                       argv=['-rn', 'dummy', '--cache',
                              '--no-build'])
        os.chdir('..')
        bug = NameBug('dummy')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)
        check = checks.checkdict['CheckBuildCompleted'].run()
        check = checks.checkdict['CreateEnvCheck'].run()
        check = checks.checkdict['generic-srv-opt']
        check.run()
        self.assertTrue('/srv' in check.result.output_extra)
        self.assertTrue('/opt' in check.result.output_extra)
        self.assertTrue('/usr/local' in check.result.output_extra)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        suite = unittest.TestSuite()
        for test in sys.argv[1:]:
            suite.addTest(TestExt(test))
    else:
        suite = unittest.TestLoader().loadTestsFromTestCase(TestExt)
    unittest.TextTestRunner(verbosity=2).run(suite)

# vim: set expandtab ts=4 sw=4:
