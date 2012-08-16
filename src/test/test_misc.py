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

import glob
import logging
import unittest
import os
import re
import shutil

from FedoraReview.helpers import Helpers
from FedoraReview import Checks, NameBug, Sources, Source, ReviewDirs, \
     SRPMFile, SpecFile, Mock, Settings
from FedoraReview import BugzillaBug, NameBug

from base import *
from test_env import no_net

class TestMisc(unittest.TestCase):

    def setUp(self):
        sys.argv = ['fedora-review','-n','python-test','--prebuilt']
        Settings.init(True)
        ReviewDirs.reset()
        ReviewDirs.workdir_setup('.', True)
        self.log = Settings.get_logger()
        self.helpers = Helpers()
        self.srpm_file = os.path.join(os.path.abspath('.'),
                                      os.path.basename(TEST_SRPM))
        self.spec_file = os.path.join(Mock.get_builddir('SOURCES'),
                                        os.path.basename(TEST_SPEC))
        self.source_file = os.path.join(Mock.get_builddir('SOURCES'),
                                        os.path.basename(TEST_SRC))
        if not os.path.exists(TEST_WORK_DIR):
            os.makedirs(TEST_WORK_DIR)
        if not no_net:
            self.helpers._get_file(TEST_SRPM, TEST_WORK_DIR)
        self.startdir = os.getcwd()
        for tree in ['python-test', 'results']:
            if os.path.exists(tree):
                shutil.rmtree(tree)
        Mock.reset()


    def run_single_check(self, bug, the_check):
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)
        checks.set_single_check(the_check)
        self.assertEqual(len(checks.checks), 1)
        check = checks.checks[0]
        check.run()
        return check

    @unittest.skipIf(no_net, 'No network available')
    def test_source_file(self):
        """ Test the SourceFile class """
        if os.path.exists('python-test'):
            shutil.rmtree('python-test')
        sys.argv = ['fedora-review','-n','python-test']
        Settings.init(True)
        ReviewDirs.reset()
        ReviewDirs.workdir_setup('.', True)
        bug = NameBug('python-test')
        bug.find_urls()
        bug.download_files()

        spec = SpecFile(bug.spec_file)
        sources = Sources(spec)
        source = Source(sources, 'Source0', TEST_SRC)
        # check that source exists and source.filename point to the right location
        expected = os.path.abspath('./upstream/python-test-1.0.tar.gz')
        self.assertEqual(source.filename, expected)
        self.assertEqual(source.is_archive(), True)
        self.assertTrue(os.path.exists(source.filename))
        self.assertEqual(source.check_source_checksum(),
                         "7ef644ee4eafa62cfa773cad4056cdcea592e27dacd5ae"
                         "b4e8b11f51f5bf60d3")
        os.chdir(self.startdir)

    @unittest.skipIf(no_net, 'No network available')
    def test_sources(self):
        if os.path.exists('python-test'):
            shutil.rmtree('python-test')
        sys.argv = ['fedora-review','-n','python-test']
        Settings.init(True)
        ReviewDirs.reset()
        ReviewDirs.workdir_setup('.', True)
        bug = NameBug('python-test')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)
        checks.set_single_check('CheckSourceMD5')
        self.assertEqual(len(checks.checks), 1)
        check = checks.checks[0]
        check.run()
        result = check.get_result()
        self.log.debug('result : ' + result.result)
        if result.output_extra:
           self.log.debug("Result extra text: " + result.output_extra)
        self.assertEqual( result.result, 'pass')
        os.chdir(self.startdir)

    @unittest.skipIf(no_net, 'No network available')
    def test_spec_file(self):
        ''' Test the SpecFile class'''
        ReviewDirs.reset()
        ReviewDirs.workdir_setup('.', True)
        dest = Mock.get_builddir('SOURCES')
        if not os.path.exists(dest):
            os.makedirs(dest)
        self.helpers._get_file(TEST_SPEC, Mock.get_builddir('SOURCES'))
        spec = SpecFile(self.spec_file)
        # Test misc rpm values (Macro resolved)
        self.assertEqual(spec.name,'python-test')
        self.assertEqual(spec.version,'1.0')
        # resolve the dist-tag
        dist = self.helpers._run_cmd('rpm --eval %dist')[:-1]
        self.assertEqual(spec.release,'1'+dist)
        # test misc rpm values (without macro resolve)
        self.assertEqual(spec.find_tag('Release'), ['1%{?dist}'])
        self.assertEqual(spec.find_tag('License'), ['GPLv2+'])
        self.assertEqual(spec.find_tag('Group'), ['Development/Languages'])
        # Test rpm value not there
        self.assertEqual(spec.find_tag('PreReq'), [])
        # Test get sections
        expected = {'%clean': ['rm -rf $RPM_BUILD_ROOT']}
        self.assertEqual(spec.get_section('%clean'), expected)
        expected = {'%build': ['%{__python} setup.py build']}
        self.assertEqual(spec.get_section('%build'), expected)
        expected = {'%install': ['rm -rf $RPM_BUILD_ROOT',
                    '%{__python} setup.py install -O1 --skip-build'
                    ' --root $RPM_BUILD_ROOT','']}
        self.assertEqual(spec.get_section('%install'),expected)
        expected = {'%files': ['%defattr(-,root,root,-)',
                    '%doc COPYING', '%{python_sitelib}/*']}
        self.assertEqual(spec.get_section('%files'),expected)
        # Test get_sources (return the Source/Patch lines with macros resolved)
        expected = {'Source0': 'http://timlau.fedorapeople.org/'
                    'files/test/review-test/python-test-1.0.tar.gz'}
        self.assertEqual(spec.get_sources(), expected)
        # Test find
        regex = re.compile(r'^Release\s*:\s*(.*)')
        res = spec.find(regex)
        if res:
            self.assertEqual(res.groups(), ('1%{?dist}',))
        else:
            self.assertTrue(False)
        os.chdir(self.startdir)

    @unittest.skipIf(no_net, 'No network available')
    def test_srpm_mockbuild(self):
        """ Test the SRPMFile class """
        ReviewDirs.reset()
        ReviewDirs.workdir_setup('.', True)
        sys.argv = ['fedora-review','-b','817268', '-m', 'fedora-16-i386']
        Settings.init(True)
        self.helpers._get_file(TEST_SRPM, os.path.abspath('.'))
        srpm = SRPMFile(self.srpm_file)
        # install the srpm
        srpm.unpack()
        self.assertTrue(hasattr(srpm, 'unpacked_src'))
        src_dir = srpm.unpacked_src
        src_files = glob.glob(os.path.expanduser(src_dir) + '/*')
        src_files = [os.path.basename(f) for f in  src_files]
        self.assertTrue('python-test-1.0.tar.gz' in src_files)
        self.log.info("Starting mock build (patience...)")
        srpm.mockbuild()
        self.assertTrue(srpm.is_build)
        rpms = glob.glob(os.path.join(Mock.resultdir,
                                      'python-test-1.0-1*noarch.rpm'))
        self.assertEqual(1, len(rpms))
        os.chdir(self.startdir)

    def test_checksum_command_line(self):
        sys.argv = ['fedora-review','-n','python-test','--prebuilt',
                    '-k','sha1']
        Settings.init(True)
        helpers = Helpers()
        checksum = helpers._checksum('scantailor.desktop')
        self.assertEqual(checksum, '5315b33321883c15c19445871cd335f7f698a2aa')

    def test_md5(self):
        Settings.checksum = 'md5'
        helpers = Helpers()
        checksum = helpers._checksum('scantailor.desktop')
        self.assertEqual(checksum, '4a1c937e62192753c550221876613f86')

    def test_sha1(self):
        Settings.checksum = 'sha1'
        helpers = Helpers()
        checksum = helpers._checksum('scantailor.desktop')
        self.assertEqual(checksum, '5315b33321883c15c19445871cd335f7f698a2aa')

    def test_sha224(self):
        Settings.checksum = 'sha224'
        helpers = Helpers()
        checksum = helpers._checksum('scantailor.desktop')
        self.assertEqual(checksum, '01959559db8ef8d596ff824fe207fc0345be67df6b8a51942214adb7')

    def test_sha256(self):
        Settings.checksum = 'sha256'
        helpers = Helpers()
        checksum = helpers._checksum('scantailor.desktop')
        self.assertEqual(checksum, 'd8669d49c8557ac47681f9b85e322849fa84186a8683c93959a590d6e7b9ae29')

    def test_sha384(self):
        Settings.checksum = 'sha384'
        helpers = Helpers()
        checksum = helpers._checksum('scantailor.desktop')
        self.assertEqual(checksum, '3d6a580100b1e8a40dc41892f6b289ff13c0b489b8079d8b7c01a17c67b88bf77283f784b4e8dacac6572050df8c948e')

    def test_sha512(self):
        Settings.checksum = 'sha512'
        helpers = Helpers()
        checksum = helpers._checksum('scantailor.desktop')
        self.assertEqual(checksum, '77a138fbd918610d55d9fd22868901bd189d987f17701498164badea88dd6f5612c118fc9e66d7b57f802bf0cddadc1cec54674ee1c3df2ddfaf1cac4007ac26')

    @unittest.skipIf(no_net, 'No network available')
    def test_bugzilla_bug(self):
        sys.argv = ['fedora-review','-b','817268']
        Settings.init(True)
        ReviewDirs.reset()
        ReviewDirs.workdir_setup('.', True)
        bug = BugzillaBug('817268')
        bug.find_urls()
        expected ='http://dl.dropbox.com/u/17870887/python-faces-0.11.7-2' \
                  '/python-faces-0.11.7-2.fc16.src.rpm'
        self.assertEqual(expected, bug.srpm_url)
        expected = 'http://dl.dropbox.com/u/17870887/python-faces-0.11.7-2/' \
                   'python-faces.spec'
        self.assertEqual(expected, bug.spec_url)
        self.assertEqual(None, bug.spec_file)
        self.assertEqual(None, bug.srpm_file)
        os.chdir(self.startdir)

    @unittest.skipIf(no_net, 'No network available')
    def test_rpm_spec(self):
        sys.argv = ['fedora-review','-rn','python-test']
        Settings.init(True)
        ReviewDirs.reset()
        if os.path.exists('python-test'):
            shutil.rmtree('python-test')
        bug = NameBug('python-test')
        bug.find_urls()
        expected = 'src/test/python-test-1.0-1.fc16.src.rpm'
        self.assertTrue(bug.srpm_url.endswith(expected))
        expected = 'src/test/python-test/srpm-unpacked/python-test.spec'
        self.assertTrue(bug.spec_url.endswith(expected))
        os.chdir(self.startdir)

    @unittest.skipIf(no_net, 'No network available')
    def test_md5sum_diff_ok(self):
        os.chdir('md5sum-diff-ok')
        sys.argv = ['fedora-review','-n','python-test','-rp']
        Settings.init(True)
        ReviewDirs.reset()
        if os.path.exists('python-test'):
            shutil.rmtree('python-test')

        bug = NameBug('python-test')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)
        checks.set_single_check('CheckSourceMD5')
        self.assertEqual(len(checks.checks), 1)
        check = checks.checks[0]
        check.run()
        self.assertEqual(check.state, 'pass')
        expected = 'diff -r shows no differences'
        self.assertTrue(expected in check.attachments[0].text)
        os.chdir(self.startdir)

    @unittest.skipIf(no_net, 'No network available')
    def test_md5sum_diff_fail(self):
        os.chdir('md5sum-diff-fail')
        sys.argv = ['fedora-review','-rpn','python-test']
        Settings.init(True)
        ReviewDirs.reset()
        if os.path.exists('python-test'):
            shutil.rmtree('python-test')
        bug = NameBug('python-test')
        bug.find_urls()
        checks = Checks(bug.spec_file, bug.srpm_file)
        checks.set_single_check('CheckSourceMD5')
        self.assertEqual(len(checks.checks), 1)
        check = checks.checks[0]
        check.run()
        self.assertEqual(check.state, 'fail')
        expected = 'diff -r also reports differences'
        self.assertTrue(expected in check.attachments[0].text)
        os.chdir(self.startdir)

    def test_bad_specfile(self):
        os.chdir('bad-spec')
        if os.path.exists('python-test'):
            shutil.rmtree('python-test')
        sys.argv = ['fedora-review','-pn','python-test']
        Settings.init(True)
        ReviewDirs.reset()
        ReviewDirs.workdir_setup('.', True)
        bug = NameBug('python-test')
        check = self.run_single_check(bug,'CheckSpecAsInSRPM')
        self.assertEqual(check.state, 'fail')
        self.assertTrue('#TestTag' in check.attachments[0].text)
        os.chdir(self.startdir)

    def test_desktop_file_bug(self):
        os.chdir('desktop-file')
        ReviewDirs.reset()
        ReviewDirs.startdir = os.getcwd()
        if os.path.exists('python-test'):
            shutil.rmtree('python-test')
        sys.argv = ['fedora-review','-rpn','python-test']
        Settings.init(True)
        bug = NameBug('python-test')
        check = self.run_single_check(bug,'CheckDesktopFileInstall')
        self.assertEqual(check.state, 'pass')
        os.chdir(self.startdir)

    def test_unversioned_so(self):
        os.chdir('unversioned-so')
        if os.path.exists('python-test'):
            shutil.rmtree('python-test')
        sys.argv = ['fedora-review','-rpn','python-test']
        Settings.init(True)
        ReviewDirs.reset()
        ReviewDirs.startdir = os.getcwd()
        bug = NameBug('python-test')
        check = self.run_single_check(bug,'CheckSoFiles')
        self.assertEqual(check.state, 'fail')
        os.chdir(self.startdir)

    def test_unversioned_so_private(self):
        os.chdir('unversioned-so-private')
        if os.path.exists('python-test'):
            shutil.rmtree('python-test')
        sys.argv = ['fedora-review','-rpn','python-test']
        Settings.init(True)
        ReviewDirs.reset()
        ReviewDirs.startdir = os.getcwd()
        bug = NameBug('python-test')
        check = self.run_single_check(bug,'CheckSoFiles')
        self.assertEqual(check.state, 'pending')
        os.chdir(self.startdir)

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMisc)
    unittest.TextTestRunner(verbosity=2).run(suite)
