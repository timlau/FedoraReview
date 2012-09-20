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

import unittest
import os
import subprocess

from glob import glob

from FedoraReview import Checks, ReviewDirs, SpecFile, Settings, Sources
from FedoraReview import BugzillaBug, NameBug, UrlBug


from fr_testcase import FR_TestCase, NO_NET, FAST_TEST, VERSION

class TestOptions(FR_TestCase):

    def init_opt_test(self, argv= [], cd=None, wd=None,root=None):
        cd = cd if cd else 'options'
        wd = wd if wd else 'python-test'
        FR_TestCase.init_test(self, cd, argv, wd, buildroot=root)

    def test_name(self):
        """ Test -name option """
        self.init_opt_test(['-n','python-test', '--cache'])
        bug = NameBug(Settings.name)

        bug.find_urls()
        expected = self.abs_file_url('./python-test-1.0-1.fc16.src.rpm')
        self.assertEqual(expected, bug.srpm_url)
        expected = self.abs_file_url('./python-test.spec')
        self.assertEqual(expected, bug.spec_url),

        bug.download_files()
        expected = os.path.abspath('./python-test-1.0-1.fc16.src.rpm')
        self.assertEqual(expected, bug.srpm_file),
        expected = os.path.abspath('./python-test.spec')
        self.assertEqual(expected, bug.spec_file),

    @unittest.skipIf(NO_NET, 'No network available')
    def test_bug(self):
        """ Test -bug option """
        self.init_opt_test(['-b','818805'])
        bug = BugzillaBug(Settings.bug)

        bug.find_urls()
        home = 'http://leamas.fedorapeople.org/openerp-client'
        expected = os.path.join( home,
                                 'openerp-client-6.1-2.fc16.src.rpm')
        self.assertEqual(expected, bug.srpm_url)
        expected = os.path.join(home, 'openerp-client.spec')
        self.assertEqual(expected, bug.spec_url),

        bug.download_files()
        expected = os.path.abspath(
                             'srpm/openerp-client-6.1-2.fc16.src.rpm')
        self.assertEqual(expected, bug.srpm_file),
        expected = os.path.abspath('srpm/openerp-client.spec')
        self.assertEqual(expected, bug.spec_file)

    @unittest.skipIf(NO_NET, 'No network available')
    def test_url(self):
        """ Test -url option """
        self.init_opt_test(
            ['-u','https://bugzilla.rpmfusion.org/show_bug.cgi?id=2200'])
        bug = UrlBug(Settings.url)

        bug.find_urls()
        home = 'https://dl.dropbox.com/u/17870887/get-flash-videos'
        expected = os.path.join( home,
                'get-flash-videos-1.24-4.20120409gita965329.fc16.src.rpm')
        self.assertEqual(expected, bug.srpm_url)
        expected = os.path.join(home, 'get-flash-videos.spec')
        self.assertEqual(expected, bug.spec_url),

        bug.download_files()
        expected = os.path.abspath(
            'srpm/get-flash-videos-1.24-4.20120409gita965329.fc16.src.rpm')
        self.assertEqual(expected, bug.srpm_file),
        expected = os.path.abspath('srpm/get-flash-videos.spec')
        self.assertEqual(expected, bug.spec_file)

    def test_display(self):
        """ test -d/--display option. """
        cmd = '../fedora-review --display-checks'
        output = subprocess.check_output(cmd, shell=True)
        output = output.decode('utf-8')
        self.assertTrue(len(output) > 20)

    def test_git_source(self):
        ''' test use of local source0 tarball '''

        self.init_test('git-source',
                       argv= ['-rpn', 'get-flash-videos', '--cache'],
                       buildroot='fedora-16-i386')
        ReviewDirs.reset()
        ReviewDirs.startdir = os.getcwd()

        bug = NameBug('get-flash-videos')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)
        check = checks.checkdict['CheckBuildCompleted']
        check.run()
        check = checks.checkdict['CheckSourceMD5']
        check.run()
        self.assertTrue(check.is_passed)
        self.assertIn('Using local file',
                      check.result.attachments[0].text)

    def test_version(self):
        """ test --version option. """
        cmd = '../fedora-review --version'
        output = subprocess.check_output(cmd, shell=True)
        output = output.decode('utf-8')
        self.assertIn('fedora-review', output)
        self.assertIn(VERSION, output)

    @unittest.skipIf(NO_NET, 'No network available')
    @unittest.skipIf(FAST_TEST, 'slow test disabled by REVIEW_FAST_TEST')
    def test_cache(self):
        def get_mtime(pattern):
            pattern = os.path.join(os.getcwd(), pattern)
            path = glob(pattern)[0]
            return os.stat(path).st_mtime

        self.init_opt_test(['-b','818805'], 'options', '818805-openerp-client')
        bug = BugzillaBug(Settings.bug)
        bug.find_urls()
        bug.download_files()
        srpm_org_time = get_mtime('srpm/openerp-client*.src.rpm')
        spec = SpecFile(bug.spec_file)
        sources = Sources(spec)
        upstream_org_time = get_mtime('upstream/openerp-client*.gz')
        del bug

        os.chdir(self.startdir)
        self.init_opt_test(['-cb','818805'], 'options')
        bug = BugzillaBug(Settings.bug)
        bug.find_urls()
        bug.download_files()
        srpm_new_time = get_mtime('srpm/openerp-client*.src.rpm')
        spec = SpecFile(bug.spec_file)
        sources = Sources(spec)
        upstream_new_time = get_mtime('upstream/openerp-client*.gz')

        self.assertEqual(upstream_org_time, upstream_new_time, 'upstream')
        self.assertEqual(srpm_org_time, srpm_new_time, 'srpm')

    @unittest.skipIf(FAST_TEST, 'slow test disabled by REVIEW_FAST_TEST')
    def test_mock_options(self):
        ''' test -o/--mock-options and -m/mock-config '''
        v = '16' if '17' in self.BUILDROOT else '17'
        self.init_test('test_misc',
                       argv=['-n','python-test','--cache'],
                       options='--resultdir=results',
                       buildroot='fedora-%s-i386' % v)
        d = os.path.join(os.getcwd(), 'results')
        if os.path.exists(d):
            for crap in glob(os.path.join('results', '*.*')):
                os.unlink(crap)
        else:
            os.mkdir(d)
        bug = NameBug('python-test')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)
        check = checks.checkdict['CheckBuild']
        check.run()
        self.assertTrue(check.is_passed)
        rpms = glob(os.path.join('results', '*fc%s*.rpm' % v))
        self.assertTrue(len(rpms) > 0)

    def test_prebuilt(self):
        ''' test --name --prebuilt '''

        argv = ['-rpn', 'python-spiffgtkwidgets', '--cache']
        self.init_test('prebuilt', argv=argv)
        ReviewDirs.reset()

        bug = NameBug('python-spiffgtkwidgets')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)
        check = checks.checkdict['CheckBuild']
        check.run()
        self.assertTrue(check.is_pending)
        self.assertIn('Using prebuilt packages',
                       check.result.output_extra)

    def test_rpm_spec(self):
        """ Test --rpm-spec/-r option """
        self.init_opt_test(['-rn','python-test', '--cache'],
                           'desktop-file')
        ReviewDirs.reset()
        bug = NameBug(Settings.name)
        bug.find_urls()

        expected = self.abs_file_url('../python-test-1.0-1.fc16.src.rpm')
        self.assertEqual(expected, bug.srpm_url)
        expected = self.abs_file_url('./srpm-unpacked/python-test.spec')
        self.assertEqual(expected, bug.spec_url),

        bug.download_files()
        expected = os.path.abspath('../python-test-1.0-1.fc16.src.rpm')
        self.assertEqual(expected, bug.srpm_file),
        expected = os.path.abspath('./srpm-unpacked/python-test.spec')
        self.assertEqual(expected, bug.spec_file),

    def test_single(self):
        ''' test --single/-s option '''
        self.init_opt_test(['-n','python-test', '-s', 'CheckRequires',
                            '--cache'])
        bug = NameBug(Settings.name)
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)
        check = checks.checkdict['CheckRequires']
        self.assertEqual(check.name, 'CheckRequires')

    def test_exclude(self):
        ''' test --exclude/-x option. '''
        self.init_opt_test(['-n','python-test', '-x', 'CheckRequires',
                            '--cache'])
        bug = NameBug(Settings.name)
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)
        self.assertTrue(checks.checkdict['CheckRequires'].result == None)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        suite = unittest.TestSuite()
        for test in sys.argv[1:]:
            suite.addTest(TestOptions(test))
    else:
        suite = unittest.TestLoader().loadTestsFromTestCase(TestOptions)
    unittest.TextTestRunner(verbosity=2).run(suite)
