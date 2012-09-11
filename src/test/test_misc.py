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
sys.path.insert(0,os.path.abspath('../FedoraReview'))

import glob
import unittest
import os
import re
import subprocess

from FedoraReview.helpers_mixin import HelpersMixin
from checks import _CheckDict
from FedoraReview import AbstractCheck, Checks, \
     Sources, Source, ReviewDirs, SRPMFile, SpecFile, Mock, Settings
from FedoraReview import BugzillaBug, NameBug
from FedoraReview import ReviewError

from fr_testcase import FR_TestCase, FAST_TEST, NO_NET

class TestMisc(FR_TestCase):

    def setUp(self):
        sys.argv = ['fedora-review', '-b', '1']
        Settings.init(True)
        self.log = Settings.get_logger()
        self.helpers = HelpersMixin()
        self.srpm_file = os.path.join(os.path.abspath('.'),
                                      'test_misc',
                                      'python-test-1.0-1.fc16.src.rpm')
        self.spec_file = os.path.join(Mock.get_builddir('SOURCES'),
                                      'python-test.spec')
        self.startdir = os.getcwd()
        Mock.reset()

    def test_flags_1(self):
        ''' test a flag defined in python, set by user' '''
        self.init_test('test_misc',
                       argv=['-n','python-test', '--cache',
                             '--no-build', '-D', 'EPEL5'])
        bug = NameBug('python-test')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)
        self.assertTrue(checks.flags['EPEL5'])

    def test_flags_2(self):
        ''' Flag defined in python, not set by user' '''
        self.init_test('test_misc',
                       argv=['-n','python-test', '--cache',
                             '--no-build'])
        bug = NameBug('python-test')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)
        self.assertFalse(checks.flags['EPEL5'])

    def test_flags_3(self):
        ''' Flag not defined , set by user' '''

        self.init_test('test_misc',
                       argv=['-n','python-test', '--cache',
                             '--no-build', '-D', 'EPEL8'])
        bug = NameBug('python-test')
        bug.find_urls()
        bug.download_files()
        with  self.assertRaises(ReviewError):
            checks = Checks(bug.spec_file, bug.srpm_file)

    def test_flags_4(self):
        ''' Flag defined in shell script , set by user to value '''

        os.environ['XDG_DATA_HOME'] = os.getcwd()
        self.init_test('test_misc',
                       argv=['-n','python-test', '--cache',
                             '--no-build', '-D', 'EPEL6=foo'])
        bug = NameBug('python-test')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)
        self.assertEqual(str(checks.flags['EPEL6']), 'foo')

    def test_source_file(self):
        """ Test the SourceFile class """
        self.init_test('test_misc',
                       argv=['-n','python-test', '--cache',
                             '--no-build'])

        source = Source('Source0',
                        self.BASE_URL +  'python-test-1.0.tar.gz')
        # check that source exists and source.filename point to the right location
        expected = os.path.abspath('upstream/python-test-1.0.tar.gz')
        self.assertEqual(source.filename, expected)
        self.assertEqual(source.is_archive(), True)
        self.assertTrue(os.path.exists(source.filename))
        self.assertEqual(source.check_source_checksum(),
                         "7ef644ee4eafa62cfa773cad4056cdcea592e27dacd5ae"
                         "b4e8b11f51f5bf60d3")

    def test_sources(self):
        self.init_test('test_misc',
                       argv=['-n','python-test', '--cache',
                             '--no-build'])
        bug = NameBug('python-test')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file).get_checks()
        checks.set_single_check('CheckSourceMD5')
        check = checks['CheckSourceMD5']
        check.run()
        result = check.result
        self.log.debug('test_source, result : ' + result.result)
        if result.output_extra:
           self.log.debug("Result extra text: " + result.output_extra)
        self.assertTrue(check.is_passed)

    def test_mock_configdir(self):
        self.init_test('test_misc',
                       argv=['-n','python-test'],
                       buildroot='default',
                       options='--configdir=mock-config')
        Mock.reset()
        Mock._get_root()
        self.assertEqual(Mock.mock_root, 'fedora-12-i786')

    @unittest.skipIf(FAST_TEST, 'slow test disabled by REVIEW_FAST_TEST')
    def test_mock_uniqueext(self):
        self.init_test('test_misc',
                       argv=['-n','python-test'],
                       options='--uniqueext=hugo')
        bug = NameBug('python-test')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)
        Mock.init()
        for dirt in glob.glob('results/*.*'):
            os.unlink(dirt)
        check = checks.checkdict['CheckBuild']
        check.run()
        self.assertTrue(check.is_passed)
        results = glob.glob('results/*.rpm')
        self.assertEqual(len(results), 2)
        for dirt in glob.glob('results/*.*'):
            os.unlink(dirt)


    def test_spec_file(self):
        ''' Test the SpecFile class'''
        self.init_test('test_misc',
                       argv=['-n','python-test', '--cache',
                             '--no-build'])
        dest = Mock.get_builddir('SOURCES')
        if not os.path.exists(dest):
            os.makedirs(dest)
        spec = SpecFile(os.path.join(os.getcwd(), 'python-test.spec'))
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
                    ' --root $RPM_BUILD_ROOT']}
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

    @unittest.skipIf(FAST_TEST, 'slow test disabled by REVIEW_FAST_TEST')
    def test_mockbuild(self):
        """ Test the SRPMFile class """
        self.init_test('test_misc',
                       argv=['-n','python-test', '--cache',
                             '--no-build'])
        srpm = SRPMFile(self.srpm_file)
        # install the srpm
        srpm.unpack()
        self.assertTrue(srpm._unpacked_src != None)
        src_dir = srpm._unpacked_src
        src_files = glob.glob(os.path.expanduser(src_dir) + '/*')
        src_files = [os.path.basename(f) for f in  src_files]
        self.assertTrue('python-test-1.0.tar.gz' in src_files)
        self.log.info("Starting mock build (patience...)")
        Mock.build(srpm.filename)
        rpms = glob.glob(os.path.join(Mock.resultdir,
                                      'python-test-1.0-1*noarch.rpm'))
        self.assertEqual(1, len(rpms))

    def test_checksum_command_line(self):
        sys.argv = ['fedora-review','-b','1', '-k', 'sha1']
        Settings.init(True)
        helpers = HelpersMixin()
        checksum = helpers._checksum('scantailor.desktop')
        self.assertEqual(checksum, '5315b33321883c15c19445871cd335f7f698a2aa')

    def test_md5(self):
        sys.argv = ['fedora-review','-b','1']
        Settings.init(True)
        Settings.checksum = 'md5'
        helpers = HelpersMixin()
        checksum = helpers._checksum('scantailor.desktop')
        self.assertEqual(checksum, '4a1c937e62192753c550221876613f86')

    def test_sha1(self):
        sys.argv = ['fedora-review','-b','1']
        Settings.init(True)
        Settings.checksum = 'sha1'
        helpers = HelpersMixin()
        checksum = helpers._checksum('scantailor.desktop')
        self.assertEqual(checksum, '5315b33321883c15c19445871cd335f7f698a2aa')

    def test_sha224(self):
        sys.argv = ['fedora-review','-b','1']
        Settings.init(True)
        Settings.checksum = 'sha224'
        helpers = HelpersMixin()
        checksum = helpers._checksum('scantailor.desktop')
        self.assertEqual(checksum, '01959559db8ef8d596ff824fe207fc0345be67df6b8a51942214adb7')

    def test_sha256(self):
        sys.argv = ['fedora-review','-b','1']
        Settings.init(True)
        Settings.checksum = 'sha256'
        helpers = HelpersMixin()
        checksum = helpers._checksum('scantailor.desktop')
        self.assertEqual(checksum, 'd8669d49c8557ac47681f9b85e322849fa84186a8683c93959a590d6e7b9ae29')

    def test_sha384(self):
        sys.argv = ['fedora-review','-b','1']
        Settings.init(True)
        Settings.checksum = 'sha384'
        helpers = HelpersMixin()
        checksum = helpers._checksum('scantailor.desktop')
        self.assertEqual(checksum, '3d6a580100b1e8a40dc41892f6b289ff13c0b489b8079d8b7c01a17c67b88bf77283f784b4e8dacac6572050df8c948e')

    def test_sha512(self):
        sys.argv = ['fedora-review','-b','1']
        Settings.init(True)
        Settings.checksum = 'sha512'
        helpers = HelpersMixin()
        checksum = helpers._checksum('scantailor.desktop')
        self.assertEqual(checksum, '77a138fbd918610d55d9fd22868901bd189d987f17701498164badea88dd6f5612c118fc9e66d7b57f802bf0cddadc1cec54674ee1c3df2ddfaf1cac4007ac26')

    @unittest.skipIf(NO_NET, 'No network available')
    def test_bugzilla_bug(self):
        self.init_test('test_misc',
                       argv=['-b','817268'],
                       wd='python-test')
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

    def test_rpm_spec(self):
        self.init_test('test_misc',
                       argv=['-rn','python-test', '--cache',
                             '--no-build'])
        ReviewDirs.reset()
        bug = NameBug('python-test')
        bug.find_urls()
        expected = 'src/test/test_misc/python-test-1.0-1.fc16.src.rpm'
        self.assertTrue(bug.srpm_url.endswith(expected))
        expected = 'src/test/test_misc/python-test/srpm-unpacked/python-test.spec'
        self.assertTrue(bug.spec_url.endswith(expected))

    def test_jsonapi(self):
        self.init_test('test_misc',
                       argv=['-rpn','python-test', '--no-build'])
        ReviewDirs.reset(os.getcwd())
        os.environ['REVIEW_EXT_DIRS'] = os.path.normpath(os.getcwd() + '/../api')

        bug = NameBug('python-test')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file).get_checks()
        test1 = checks['test1']
        test2 = checks['ExtShellTest2']
        self.assertEqual( test1.group, 'Generic')
        self.assertEqual( test1.type, 'EXTRA')
        self.assertEqual( test1.text, 'A check solely for test purposes.')

        self.assertEqual( test2.group, 'Generic')
        self.assertEqual( test2.type, 'EXTRA')
        self.assertEqual( test2.text,
                          'A second check solely for test purposes.')


    def test_md5sum_diff_ok(self):
        self.init_test('md5sum-diff-ok',
                       argv=['-rpn','python-test', '--cache',
                             '--no-build'])
        ReviewDirs.reset(os.getcwd())
        bug = NameBug('python-test')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file).get_checks()
        checks.set_single_check('CheckSourceMD5')
        check = checks['CheckSourceMD5']
        check.run()
        self.assertTrue(check.is_passed)
        expected = 'diff -r shows no differences'
        self.assertTrue(expected in check.result.attachments[0].text)

    def test_md5sum_diff_fail(self):
        self.init_test('md5sum-diff-fail',
                       argv=['-rpn','python-test', '--cache',
                             '--no-build'])
        ReviewDirs.reset(os.getcwd())
        bug = NameBug('python-test')
        bug.find_urls()
        checks = Checks(bug.spec_file, bug.srpm_file).get_checks()
        checks.set_single_check('CheckSourceMD5')
        check = checks['CheckSourceMD5']
        check.run()
        self.assertTrue(check.is_failed)
        expected = 'diff -r also reports differences'
        self.assertTrue(expected in check.result.attachments[0].text)

    def test_dirty_resultdir(self):
        self.init_test('test_misc',
                       argv=['-n','python-test', '--cache'])
        bug = NameBug('python-test')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file).get_checks()
        checks.set_single_check('CheckResultdir')
        check = checks['CheckResultdir']

        for dirt in glob.glob('results/*.*'):
            os.unlink(dirt)
        check.run()
        self.assertTrue(check.is_passed)

        subprocess.check_call('touch results/orvar.rpm', shell=True)
        self.assertRaises(ReviewError, check.run)
        Settings.nobuild = True
        check.run()
        self.assertTrue(check.is_passed)
        os.unlink('results/orvar.rpm')

    def test_prebuilt_sources(self):
        self.init_test('test_misc',
                       argv=['-n','python-test', '--prebuilt'])
        ReviewDirs.startdir = os.getcwd()
        bug = NameBug('python-test')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)
        subprocess.check_call('touch orvar.rpm', shell=True)
        rpms = checks.srpm.get_used_rpms()
        self.assertEqual(len(rpms), 2)
        rpms = checks.srpm.get_used_rpms('.src.rpm')
        os.unlink('orvar.rpm')
        self.assertEqual(len(rpms), 1)

    def test_bad_specfile(self):
        self.init_test('bad-spec',
                       argv=['-n','python-test', '-p', '--cache',
                             '--no-build'])
        bug = NameBug('python-test')
        check = self.run_single_check(bug,'CheckSpecAsInSRPM')
        self.assertTrue(check.is_failed)
        self.assertTrue('#TestTag' in check.result.attachments[0].text)

    def test_desktop_file_bug(self):
        self.init_test('desktop-file',
                       argv=['-n','python-test', '--cache',
                             '--no-build'])
        bug = NameBug('python-test')
        check = self.run_single_check(bug,'CheckDesktopFileInstall', True)
        self.assertTrue(check.is_passed)

    def test_check_dict(self):

        class TestCheck(AbstractCheck):
             def run(self): pass
             def name(self): return 'foo'

        c = TestCheck('a-sourcefile')
        l = _CheckDict()
        l.add(c)
        self.assertEqual(len(l), 1)
        self.assertEqual(c.checkdict, l)
        c1 = TestCheck('sourcefile-1')
        c1.name = 'test1'
        c2 = TestCheck('sourcefile-2')
        c2.name = 'test2'
        l.extend([c1, c2])
        self.assertEqual(len(l), 3)
        self.assertEqual(l['test1'].name, c1.name)
        self.assertEqual(l['test2'].name, c2.name)
        self.assertEqual(l['test1'], c1)
        self.assertEqual(l['test2'], c2)
        self.assertEqual(l['test2'].checkdict, l)
        l.set_single_check('test1')
        self.assertEqual(len(l), 1)
        self.assertEqual(l['test1'], c1)

    def test_unversioned_so(self):
        self.init_test('unversioned-so',
                       argv=['-rpn','python-test'],
                       wd='python-test')
        ReviewDirs.reset(os.getcwd())
        bug = NameBug('python-test')
        check = self.run_single_check(bug,'CheckSoFiles')
        self.assertTrue(check.is_failed)

    def test_unversioned_so_private(self):
        self.init_test('unversioned-so-private',
                       argv=['-rpn','python-test'],
                       wd='python-test')
        ReviewDirs.reset(os.getcwd())
        bug = NameBug('python-test')
        check = self.run_single_check(bug,'CheckSoFiles')
        self.assertTrue(check.is_pending)

    @unittest.skipIf(FAST_TEST, 'slow test disabled by REVIEW_FAST_TEST')
    def test_local_repo(self):
        self.init_test('test_misc',
                       argv=['-rn','python-test', '--local-repo',
                             'repo', '--cache'])
        ReviewDirs.reset(os.getcwd())
        bug = NameBug('python-test')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)
        check = checks.checkdict['CheckPackageInstalls']
        check.run()
        self.assertTrue(check.is_passed)
        self.assertTrue(Mock.is_installed('dummy'))

    def test_bad_specname(self):
        self.init_test('bad-specname',
                       argv=['-rn','python-test', '--cache'])
        ReviewDirs.reset(os.getcwd())
        bug = NameBug('python-test')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)
        check = checks.checkdict['CheckSpecAsInSRPM']
        check.run()
        self.assertTrue(check.is_failed)
        self.assertIn('Bad spec filename:', check.result.output_extra)

    def test_perl_module(self):
        ''' test basic perl python + shell test '''
        self.init_test('perl',
                       argv=['-rn','perl-RPM-Specfile', '--no-build'])
        ReviewDirs.reset(os.getcwd())
        bug = NameBug('perl-RPM-Specfile')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)
        checks.checkdict['CreateEnvCheck'].run()
        check = checks.checkdict['PerlCheckBuildRequires']
        check.run()
        self.assertTrue(check.is_pending)
        check = checks.checkdict['perl-url-tag']
        check.run()
        self.assertTrue(check.is_pending)




if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMisc)
    unittest.TextTestRunner(verbosity=2).run(suite)
