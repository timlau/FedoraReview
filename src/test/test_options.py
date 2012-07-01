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
Unit tests for bugzilla bug handling
'''

import sys
import os.path
sys.path.insert(0,os.path.abspath('../'))

import logging
import unittest
import os
import shutil
import subprocess

from glob import glob

from FedoraReview.helpers import Helpers
from FedoraReview import Checks, NameBug, ReviewDirs, \
     SRPMFile, SpecFile, Mock, Settings, Sources, Source
from FedoraReview import BugzillaBug, NameBug, UrlBug
from FedoraReview.review_helper import ReviewHelper


from base import *
from test_env import no_net

startdir = os.getcwd()

VERSION = '0.2.0'

def abs_file_url(path):
    return 'file://' +  os.path.abspath(path)

class TestOptions(unittest.TestCase):

    def setUp(self):
        self.log = Settings.get_logger()

    def init_test(self, argv= ['fedora-review'], d=None):
        os.chdir(startdir)
        if d:
            os.chdir(d)
        if os.path.exists('python-test'):
            shutil.rmtree('python-test')
        ReviewDirs.reset()
        ReviewDirs.workdir_setup('.', True)
        sys.argv = argv
        Settings.init(True)


    @unittest.skipIf(no_net, 'No network available')
    def test_name(self):
        """ Test -name option """
        self.init_test(['fedora-review','-n','python-test'])
        bug = NameBug(Settings.name)

        bug.find_urls()
        expected = abs_file_url('./python-test-1.0-1.fc16.src.rpm')
        self.assertEqual(expected, bug.srpm_url)
        expected = abs_file_url('./python-test.spec')
        self.assertEqual(expected, bug.spec_url),

        bug.download_files()
        expected = os.path.abspath('./python-test-1.0-1.fc16.src.rpm')
        self.assertEqual(expected, bug.srpm_file),
        expected = os.path.abspath('./python-test.spec')
        self.assertEqual(expected, bug.spec_file),
                         
    @unittest.skipIf(no_net, 'No network available')
    def test_bug(self):
        """ Test -bug option """
        self.init_test(['fedora-review','-b','818805'])
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

    @unittest.skipIf(no_net, 'No network available')
    def test_url(self):
        """ Test -url option """
        self.init_test(
                    ['fedora-review','-u',
                    'https://bugzilla.rpmfusion.org/show_bug.cgi?id=2200'])
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
        os.chdir(startdir)
        cmd = '../fedora-review --display'
        output = subprocess.check_output(cmd, shell=True)
        output = output.decode('utf-8')
        self.assertTrue(len(output) > 20)

    def test_git_source(self):
        ''' test use of local source0 tarball '''

        argv = ['fedora-review', '-rpn', 'get-flash-videos']
        argv.extend(['--mock-config', 'fedora-16-i386-rpmfusion_nonfree'])
        sys.argv = argv
        os.chdir('git-source')
        if os.path.exists('get-flash-videos'):
            shutil.rmtree('get-flash-videos')
        ReviewDirs.reset()
        Settings.init(True)
  
        rh = ReviewHelper()
        sys.stdout = open( '/dev/null', 'w')
        rh.run()
        sys.stdout = sys.__stdout__
        rv = 'get-flash-videos-review.txt'
        with open(os.path.abspath(rv)) as f:
            log = f.read()
        self.assertIn('Using local file' , log)
        os.chdir(startdir)
 
    def test_version(self):
        """ test -d/--display option. """
        os.chdir(startdir)
        cmd = '../fedora-review --version'
        output = subprocess.check_output(cmd, shell=True)
        output = output.decode('utf-8')
        self.assertIn('fedora-review', output)
        self.assertIn(VERSION, output)

    @unittest.skipIf(no_net, 'No network available')
    def test_cache(self):
        def get_mtime(pattern):
            pattern = os.path.join(ReviewDirs.root, pattern)
            path = glob(pattern)[0]
            return os.stat(path).st_mtime 

        self.init_test(['fedora-review','-b','818805'])
        if os.path.exists('818805-openerp-client'):
            shutil.rmtree('818805-openerp-client')
        bug = BugzillaBug(Settings.bug)
        bug.find_urls()
        bug.download_files()
        srpm_org_time = get_mtime('srpm/python-test-1.0*.src.rpm')
        spec = SpecFile(bug.spec_file)
        sources = Sources(spec)
        upstream_org_time = get_mtime('upstream/python-test*.gz')
        del bug

        self.init_test(['fedora-review','-cb','818805'])
        bug = BugzillaBug(Settings.bug)
        bug.find_urls()
        bug.download_files()
        srpm_new_time = get_mtime('srpm/python-test-1.0*.src.rpm')
        spec = SpecFile(bug.spec_file)
        sources = Sources(spec)
        upstream_new_time = get_mtime('upstream/python-test*.gz')

        self.assertEqual(upstream_org_time, upstream_new_time, 'upstream')
        self.assertEqual(srpm_org_time, srpm_new_time, 'srpm')

    @unittest.skipIf(no_net, 'No network available')
    def test_mock_options(self):
        ''' test -o/--mock-options and -m/mock-config '''
        dflt = os.readlink('/etc/mock/default.cfg')
        v = '16' if '17' in dflt else '17'
        d = os.path.join(os.getcwd(), 'results')
        if os.path.exists(d):
            shutil.rmtree(d)
        os.mkdir(d)
        cmd = 'fedora-review -n python-test -m fedora-%s-i386' \
              ' -o=--resultdir=%s --no-report' % (v, d)
        self.init_test(cmd.split()) 

        rh = ReviewHelper()
        rh.run()
        rpms = glob(os.path.join(d, '*fc%s*.rpm' % v))
        self.assertTrue(len(rpms) > 0)

    @unittest.skipIf(no_net, 'No network available')
    def test_prebuilt(self):
        ''' test --name --prebuilt '''

        argv = ['fedora-review', '-rpn', 'python-spiffgtkwidgets']
        argv.extend(['--mock-config', 'fedora-16-i386'])
        sys.argv = argv
        os.chdir('prebuilt')
        if os.path.exists('python-spiffgtkwidgets'):
            shutil.rmtree('python-spiffgtkwidgets')
        ReviewDirs.reset()
        Settings.init(True)
  
        rpms = glob('/var/lib/mock/fedora-16-i386/*.rpm')
        for r in rpms:
            os.unlink(r)

        rh = ReviewHelper()
        sys.stdout = open( '/dev/null', 'w')
        rh.run()
        sys.stdout = sys.__stdout__
        self.assertEqual(len(rpms), 0)
        rv = 'python-spiffgtkwidgets-review.txt'
        with open(os.path.abspath(rv)) as f:
            log = '\n'.join(f.readlines())
        self.assertIn('Using prebuilt rpms', log)
        os.chdir(startdir)
 
    @unittest.skipIf(no_net, 'No network available')
    def test_rpm_spec(self):
        """ Test --rpm-spec/-r option """
        self.init_test(['fedora-review','-rn','python-test'],
                       'desktop-file')
        if os.path.exists('python-test'):
            shutil.rmtree('python-test')
        ReviewDirs.reset()
        bug = NameBug(Settings.name)
        bug.find_urls()

        expected = abs_file_url('../python-test-1.0-1.fc16.src.rpm')
        self.assertEqual(expected, bug.srpm_url)
        expected = abs_file_url('./srpm-unpacked/python-test.spec')
        self.assertEqual(expected, bug.spec_url),

        bug.download_files()
        expected = os.path.abspath('../python-test-1.0-1.fc16.src.rpm')
        self.assertEqual(expected, bug.srpm_file),
        expected = os.path.abspath('./srpm-unpacked/python-test.spec')
        self.assertEqual(expected, bug.spec_file),
        os.chdir(startdir)

    def test_single(self):
        ''' test --single/-s option '''
        self.init_test(['fedora-review',
                        '-n','python-test',
                        '-s', 'CheckRequires'])

        bug = NameBug(Settings.name)
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)
        self.assertEqual(len(checks.checks), 1)
        check = checks.checks[0]
        self.assertEqual(check.name, 'CheckRequires') 

    def test_exclude(self):
        ''' test --exclude/-x option. '''
        self.init_test(['fedora-review',
                        '-n','python-test',
                        '-x', 'CheckRequires'])

        bug = NameBug(Settings.name)
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)
        self.assertFalse('CheckRequires' in checks.get_checks()) 


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestOptions)
    unittest.TextTestRunner(verbosity=2).run(suite)
