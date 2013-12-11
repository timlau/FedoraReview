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
# pylint: disable=C0103,R0904,R0913,W0212
# (C) 2011 - Tim Lauridsen <timlau@fedoraproject.org>
'''
Unit tests for bugzilla bug handling
'''

import glob
import logging
import shutil
import os
import os.path
import re
import rpm
import subprocess
import sys
import unittest2 as unittest

try:
    from subprocess import check_output          # pylint: disable=E0611
except ImportError:
    from FedoraReview.el_compat import check_output

import srcpath                                   # pylint: disable=W0611
from FedoraReview import AbstractCheck, Mock, ReviewDirs
from FedoraReview import ReviewError, Settings

from FedoraReview.checks import Checks
from FedoraReview.datasrc import BuildFilesSource, RpmDataSource
from FedoraReview.bugzilla_bug import BugzillaBug
from FedoraReview.check_base import AbstractCheck
from FedoraReview.checks import _CheckDict
from FedoraReview.helpers_mixin import HelpersMixin
from FedoraReview.name_bug import NameBug
from FedoraReview.review_helper import ReviewHelper
from FedoraReview.source import Source
from FedoraReview.spec_file import SpecFile
from FedoraReview.rpm_file import RpmFile
from FedoraReview.srpm_file import SRPMFile

from fr_testcase import FR_TestCase, FAST_TEST, NO_NET, VERSION, RELEASE


class TestMisc(FR_TestCase):
    ''' Low-level, true unit tests. '''

    def setUp(self):
        if not srcpath.PLUGIN_PATH in sys.path:
            sys.path.append(srcpath.PLUGIN_PATH)
        sys.argv = ['fedora-review', '-b', '1']
        Settings.init(True)
        self.log = Settings.get_logger()
        self.helpers = HelpersMixin()
        self.srpm_file = os.path.join(os.path.abspath('.'),
                                      'test_misc',
                                      'python-test-1.0-1.fc17.src.rpm')
        self.startdir = os.getcwd()
        Mock.reset()

    def test_version(self):
        ''' Test version and update-version. '''
        vers_path = os.path.join(
                            srcpath.SRC_PATH, 'FedoraReview', 'version')
        if os.path.exists(vers_path):
            os.unlink(vers_path)
        import FedoraReview.version
        reload(FedoraReview.version)
        self.assertTrue(os.path.exists(vers_path))
        self.assertEqual(FedoraReview.__version__, VERSION)

    def test_rpm_source(self):
        ''' Test a rpm datasource. '''
        self.init_test('test_misc',
                       argv=['-rpn', 'python-test', '--cache',
                             '--no-build'])
        bug = NameBug('python-test')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)
        src = RpmDataSource(checks.spec)
        files = src.get_filelist()
        self.assertEqual(len(files), 11)
        rpms = src.get_all()
        self.assertEqual(rpms, ['python-test'])
        rpm_pkg = src.get('python-test')
        self.assertEqual(rpm_pkg.header['name'], 'python-test')
        all_files = src.find_all('*')
        self.assertEqual(len(all_files), 11)

    def test_buildsrc(self):
        ''' Test a BuildFilesData  datasource. '''
        self.init_test('perl',
                       argv=['-rpn', 'perl-RPM-Specfile', '--no-build'],
                       wd='perl-RPM-Specfile')
        bug = NameBug('perl-RPM-Specfile')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)  # pylint: disable=W0612
        src = BuildFilesSource()
        files = src.get_filelist()
        self.assertEqual(len(files), 8)
        root = src.get_all()
        expected_root = os.getcwd() + '/BUILD/RPM-Specfile-1.51'
        self.assertEqual(src.get_all(), [expected_root])
        root = src.get()
        self.assertEqual(root, expected_root)
        all_files = src.find_all('*')
        self.assertEqual(len(all_files), 8)

    def test_generic_static(self):
        ''' test generic static -a checks  '''
        # pylint: disable=F0401,R0201,C0111,W0613

        from plugins.generic import CheckStaticLibs

        class ChecksMockup(object):
            pass

        class RpmsMockup(object):

            def find(self, what, where):
                return True

            def get(self, pkg_name):
                return RpmFile("python-test", "1.0", "1.fc" + RELEASE)

        class ApplicableCheckStaticLibs(CheckStaticLibs):

            def is_applicable(self):
                return True

        self.init_test('test_misc',
                       argv=['-n', 'python-test', '--cache',
                             '--no-build'])
        check = ApplicableCheckStaticLibs(ChecksMockup())
        check.checks.spec = SpecFile(os.path.join(os.getcwd(),
                                                  'python-test.spec'))
        check.checks.rpms = RpmsMockup()
        check.run()

    def test_ccpp_gnulib(self):
        ''' test ccpp bundled gnulib  '''
        # pylint: disable=F0401,R0201,C0111,W0613

        from plugins.ccpp import CheckBundledGnulib

        class ChecksMockup(object):
            pass

        class BuildSrcMockup(object):
            def find(self, what):
                return True

        class ApplicableCheckBundledGnulib(CheckBundledGnulib):
            def is_applicable(self):
                return True

        self.init_test('test_misc',
                       argv=['-n', 'python-test', '--cache',
                             '--no-build'])
        check = ApplicableCheckBundledGnulib(ChecksMockup())
        check.checks.spec = SpecFile(os.path.join(os.getcwd(),
                                                  'python-test.spec'))
        check.checks.buildsrc = BuildSrcMockup()
        check.checks.rpms = RpmDataSource(check.checks.spec)
        check.run()
        self.assertTrue(check.is_failed)

    def test_disabled(self):
        ''' test normally disabled checks  '''
        # pylint: disable=F0401,R0201,C0111,W0613,W0201

        from plugins.generic_should import CheckSourceComment
        from plugins.generic import CheckDefattr
        from FedoraReview.datasrc import SourcesDataSource

        class ChecksMockup(object):

            def __init__(self):

                class Data(object):
                    pass

                self.data = Data()

        self.init_test('test_misc',
                       argv=['-pn', 'disabled', '--cache',
                             '--no-build'])
        checks = ChecksMockup()
        checks.spec = SpecFile(os.path.join(os.getcwd(), 'disabled.spec'))
        checks.sources = SourcesDataSource(checks.spec)
        checks.flags = {'EPEL5': False}
        check = CheckSourceComment(checks)
        check.run()
        self.assertTrue(check.is_pending)
        check = CheckDefattr(checks)
        check.run()
        self.assertTrue(check.is_pending)

    def test_hardened_build(self):
        ''' test %global _hardened_build  '''
        # pylint: disable=F0401,R0201,C0111,W0613

        from plugins.generic import CheckDaemonCompileFlags

        class ChecksMockup(object):
            pass

        class RpmsMockup(object):

            def find_all(self, what):
                return ['a_file']

        self.init_test('test_misc',
                       argv=['-n', 'python-test', '--cache',
                             '--no-build'])
        check = CheckDaemonCompileFlags(ChecksMockup())
        check.checks.spec = SpecFile(os.path.join(os.getcwd(),
                                                  'python-test.spec'))
        check.checks.rpms = RpmsMockup()
        check.checks.log = self.log
        check.run()
        self.assertTrue(check.is_passed)
        check.checks.spec = SpecFile(os.path.join(os.getcwd(),
                                                  'disabled.spec'))
        check.run()
        self.assertTrue(check.is_failed)

    def test_rm_buildroot(self):
        ''' test rm -rf $BUILDROOT/a_path '''
        # pylint: disable=F0401,R0201,C0111,W0613,W0201

        from plugins.generic import CheckCleanBuildroot

        class ChecksMockup(object):
            pass

        self.init_test('test_misc',
                       argv=['-n', 'python-test', '--cache',
                             '--no-build'])
        checks = ChecksMockup()
        flags = {'EPEL5': False}
        checks.log = self.log
        checks.flags = flags
        check = CheckCleanBuildroot(checks)
        check.checks.spec = SpecFile(os.path.join(os.getcwd(),
                                                  'rm_buildroot.spec'))
        check.run()
        self.assertTrue(check.is_passed)

    def test_autotools(self):
        ''' test ccpp static -a checs  '''
        # pylint: disable=F0401,R0201,C0111,W0613,W0201

        from plugins.generic_autotools import CheckAutotoolsObsoletedMacros

        class BuildSrcMockup(object):
            def __init__(self):
                self.containers = ['configure.ac']

            def find_all(self, what):
                return ["configure.ac"] if what.endswith('ac') else []

            def is_available(self):
                return True

        class ChecksMockup(object):
            pass

        class RpmsMockup(object):
            def find(self, what, where):
                return True

        self.init_test('test_misc',
                       argv=['-n', 'python-test', '--cache',
                             '--no-build'])
        checks_mockup = ChecksMockup()
        checks_mockup.log = self.log
        checks_mockup.buildsrc = BuildSrcMockup()
        check = CheckAutotoolsObsoletedMacros(checks_mockup)
        check.checks.spec = SpecFile(os.path.join(os.getcwd(),
                                                  'gc.spec'))
        check.checks.rpms = RpmsMockup()
        check.run()
        note = check.result.output_extra
        self.assertTrue(check.is_failed)
        self.assertTrue('Some obsoleted macros' in note)
        self.assertEqual(len(check.result.attachments), 1)
        self.assertIn('AC_PROG_LIBTOOL found in: configure.ac:519',
                      check.result.attachments[0].text)
        self.assertIn('AM_CONFIG_HEADER found in: configure.ac:29',
                      check.result.attachments[0].text)

    def test_flags_1(self):
        ''' test a flag defined in python, set by user' '''
        self.init_test('test_misc',
                       argv=['-n', 'python-test', '--cache',
                             '--no-build', '-D', 'EPEL5'])
        bug = NameBug('python-test')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)
        self.assertTrue(checks.flags['EPEL5'])

    def test_flags_2(self):
        ''' Flag defined in python, not set by user' '''
        self.init_test('test_misc',
                       argv=['-n', 'python-test', '--cache',
                             '--no-build'])
        bug = NameBug('python-test')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)
        self.assertFalse(checks.flags['EPEL5'])

    def test_flags_3(self):
        ''' Flag not defined , set by user' '''

        self.init_test('test_misc',
                       argv=['-n', 'python-test', '--cache',
                             '--no-build', '-D', 'EPEL8'])
        bug = NameBug('python-test')
        bug.find_urls()
        bug.download_files()
        with self.assertRaises(ReviewError):
            # pylint: disable=W0612
            checks = Checks(bug.spec_file, bug.srpm_file)

    def test_flags_4(self):
        ''' Flag defined in shell script , set by user to value '''

        os.environ['XDG_DATA_HOME'] = os.getcwd()
        self.init_test('test_misc',
                       argv=['-n', 'python-test', '--cache',
                             '--no-build', '-D', 'EPEL6=foo'])
        bug = NameBug('python-test')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)
        self.assertEqual(str(checks.flags['EPEL6']), 'foo')

    def test_source_file(self):
        """ Test the SourceFile class """
        self.init_test('test_misc',
                       argv=['-n', 'python-test', '--cache',
                             '--no-build'])
        source = Source('Source0',
                        self.BASE_URL + 'python-test-1.0.tar.gz')
        # source exists and source.filename point to the right location?
        expected = os.path.abspath('upstream/python-test-1.0.tar.gz')
        self.assertEqual(source.filename, expected)
        self.assertEqual(source.is_archive(), True)
        self.assertTrue(os.path.exists(source.filename))
        self.assertEqual(source.check_source_checksum(),
                         "7ef644ee4eafa62cfa773cad4056cdcea592e27dacd5ae"
                         "b4e8b11f51f5bf60d3")
        source.extract()
        self.assertTrue(os.path.exists(ReviewDirs.upstream_unpacked +
                                       '/Source0/python-test-1.0'))
        source.log.setLevel(logging.ERROR)
        source = Source('Source0', 'http://nowhere.internet/a_file.txt')
        self.assertFalse(source.downloaded)

    def test_sources_data(self):
        ''' Test a SourcesDataSource. '''
        self.init_test('test_misc',
                       argv=['-n', 'python-test', '--cache',
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
        paths = check.checks.sources.find_all_re('.*[.]py')
        files = [os.path.basename(p) for p in paths]
        self.assertEqual(set(files), set(['setup.py', '__init__.py']))
        files = check.checks.sources.get_filelist()
        self.assertEqual(len(files), 10)

    def test_review_helper(self):
        ''' Test review_helper error handling. '''
        # pylint: disable=C0111,W0212

        class Null:
            def write(self, msg):
                pass

        loglevel = None
        argv = ['-rn', 'foo', '--no-build']
        self.init_test('.', argv)
        helper = ReviewHelper()
        stdout = sys.stdout
        sys.stdout = Null()
        helper.log.setLevel(logging.CRITICAL)
        rc = helper.run('review.txt')
        sys.stdout = stdout
        if loglevel:
            os.environ['REVIEW_LOGLEVEL'] = loglevel
        self.assertEqual(rc, 2)

    def test_review_dir(self):
        ''' Test ReviewDir setup functions. '''
        self.init_test('.', argv=['-n', 'python-test', '--no-build'])
        from FedoraReview.review_dirs import _ReviewDirs
        os.chdir('review_dir')
        check_output('rm -rf testdirs; mkdir testdirs', shell=True)
        ReviewDirs.workdir_setup('testdirs', 'testing')
        check_output(['touch', 'results/dummy.rpm'])
        os.chdir('..')
        rd = _ReviewDirs()
        rd.workdir_setup('testdirs')
        self.assertEqual(len(glob.glob('*')), 7)
        self.assertEqual(os.path.basename(os.getcwd()), 'testdirs')
        self.assertTrue(os.path.exists('results/dummy.rpm'))
        self.assertEqual(glob.glob('BUILD/*'), ['BUILD/pkg-1.0'])

    def test_mock_configdir(self):
        ''' Test internal scanning of --configdir option. '''
        self.init_test('test_misc',
                       argv=['-n', 'python-test'],
                       buildroot='default',
                       options='--configdir=mock-config')
        Mock.reset()
        Mock._get_root()
        self.assertEqual(Mock.mock_root, 'fedora-12-i786')

    def test_mock_clear(self):
        ''' test mock.clear_builddir(). '''
        self.init_test('test_misc',
                       argv=['-n', 'python-test', '--cache',
                             '--no-build'])
        wdir = Mock.get_builddir('BUILD')
        len1 = len(glob.glob(os.path.join(wdir, "*")))
        s = "cd {0}; ln -sf foo bar || :".format(wdir)
        check_output(s, shell=True)
        Mock.builddir_cleanup()
        len2 = len(glob.glob(os.path.join(wdir, "*")))
        self.assertEqual(len2, len1)

    @unittest.skipIf(FAST_TEST, 'slow test disabled by REVIEW_FAST_TEST')
    def test_mock_uniqueext(self):
        ''' Test --uniqueext option. '''
        loglevel = os.environ['REVIEW_LOGLEVEL']
        os.environ['REVIEW_LOGLEVEL'] = 'ERROR'
        self.init_test('mock-uniqueext',
                       argv=['-cn', 'python-test'],
                       options='--uniqueext=hugo')
        os.environ['REVIEW_LOGLEVEL'] = loglevel
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

    def test_java_spec(self):
        ''' Test the ChecktestSkip check. '''
        # pylint: disable=F0401,R0201,C0111

        from plugins.java import CheckJavaPlugin

        class ChecksMockup(object):
            def is_external_plugin_installed(self, name):
                return False

        class ApplicableCheckJavaPlugin(CheckJavaPlugin):
            class Registry(object):
                group = "Java"
                version = "1.2.3"
                build_id = "somebuild"

            registry = Registry()

            def is_applicable(self):
                return True

        self.init_test('test_misc',
                       argv=['-n', 'python-test', '--no-build'])
        spec = SpecFile(os.path.join(os.getcwd(), 'jettison.spec'))
        check = ApplicableCheckJavaPlugin(ChecksMockup())
        check.checks.spec = spec
        check.run()
        self.assertTrue(check.is_pending)

    def test_spec_file(self):
        ''' Test the SpecFile class'''

        def fix_usr_link(path):
            ''' Convert absolute paths to /usr/path. '''
            if not '/' in path:
                return path
            lead = path.split('/')[1]
            if lead in ['bin', 'sbin', 'lib', 'lib64']:
                return '/usr' + path
            return path

        self.init_test('test_misc',
                       argv=['-n', 'python-test', '--no-build'])
        dest = Mock.get_builddir('SOURCES')
        if not os.path.exists(dest):
            os.makedirs(dest)
        spec = SpecFile(os.path.join(os.getcwd(), 'python-test.spec'))
        self.assertEqual(spec.name, 'python-test')
        self.assertEqual(spec.version, '1.0')
        dist = Mock.get_macro('%dist', None, {})
        self.assertEqual(spec.release, '1' + dist)
        self.assertEqual(spec.expand_tag('Release'), '1' + dist)
        self.assertEqual(spec.expand_tag('License'), 'GPLv2+')
        self.assertEqual(spec.expand_tag('Group'), 'Development/Languages')
        # Test rpm value not there
        self.assertEqual(spec.expand_tag('PreReq'), None)
        # Test get sections
        expected = ['rm -rf $RPM_BUILD_ROOT']
        self.assertEqual(spec.get_section('%clean'), expected)
        expected = '%{__python} setup.py build'
        expected = ['LANG=C', 'export LANG', 'unset DISPLAY',
                   '/usr/bin/python setup.py build']

        build = spec.get_section('%build')
        build = map(fix_usr_link, build)
        self.assertIn(''.join(build), ''.join(expected))
        install = spec.get_section('%install')
        install = map(fix_usr_link, install)
        expected = ['LANG=C', 'export LANG', 'unset DISPLAY',
                    'rm -rf $RPM_BUILD_ROOT',
                    '/usr/bin/python setup.py install -O1 --skip-build'
                    ' --root $RPM_BUILD_ROOT']
        self.assertIn(''.join(install), ''.join(expected))

        # Test get_sources (return the Source/Patch lines with macros resolved)
        expected = {'Source0': 'http://timlau.fedorapeople.org/'
                    'files/test/review-test/python-test-1.0.tar.gz'}
        self.assertEqual(spec.sources_by_tag, expected)
        expected = ['%defattr(-,root,root,-)',
                    '%doc COPYING',
                    rpm.expandMacro('%{python_sitelib}') + '/*']
        self.assertEqual(spec.get_files(), expected)

        # Test find
        regex = re.compile(r'^Release\s*:\s*(.*)')
        res = spec.find_re(regex)
        if res:
            self.assertEqual(res.split(':')[1].strip(), '1%{?dist}')
        else:
            self.assertTrue(False)

    @unittest.skipIf(FAST_TEST, 'slow test disabled by REVIEW_FAST_TEST')
    def test_mockbuild(self):
        """ Test the SRPMFile class """
        self.init_test('mockbuild', argv=['-rn', 'python-test'])
        srpm = SRPMFile(self.srpm_file)
        # install the srpm
        srpm.unpack()
        self.assertTrue(srpm._unpacked_src is not None)
        src_dir = srpm._unpacked_src
        src_files = glob.glob(os.path.expanduser(src_dir) + '/*')
        src_files = [os.path.basename(f) for f in src_files]
        self.assertTrue('python-test-1.0.tar.gz' in src_files)
        self.log.info("Starting mock build (patience...)")
        Mock.clear_builddir()
        Mock.build(srpm.filename)
        rpms = glob.glob(os.path.join(Mock.resultdir,
                                      'python-test-1.0-1*noarch.rpm'))
        self.assertEqual(1, len(rpms))

    def test_checksum_command_line(self):
        ''' Default checksum test. '''
        sys.argv = ['fedora-review', '-b', '1', '-k', 'sha1']
        Settings.init(True)
        helpers = HelpersMixin()
        checksum = helpers._checksum('scantailor.desktop')
        self.assertEqual(checksum, '5315b33321883c15c19445871cd335f7f698a2aa')

    def test_md5(self):
        ''' MD5 checksum test. '''
        sys.argv = ['fedora-review', '-b', '1']
        Settings.init(True)
        Settings.checksum = 'md5'
        helpers = HelpersMixin()
        checksum = helpers._checksum('scantailor.desktop')
        self.assertEqual(checksum, '4a1c937e62192753c550221876613f86')

    def test_sha1(self):
        ''' SHA1 checksum test. '''
        sys.argv = ['fedora-review', '-b', '1']
        Settings.init(True)
        Settings.checksum = 'sha1'
        helpers = HelpersMixin()
        checksum = helpers._checksum('scantailor.desktop')
        self.assertEqual(checksum, '5315b33321883c15c19445871cd335f7f698a2aa')

    def test_sha224(self):
        ''' SHA2 checksum test. '''
        sys.argv = ['fedora-review', '-b', '1']
        Settings.init(True)
        Settings.checksum = 'sha224'
        helpers = HelpersMixin()
        checksum = helpers._checksum('scantailor.desktop')
        self.assertEqual(checksum,
            '01959559db8ef8d596ff824fe207fc0345be67df6b8a51942214adb7')

    def test_sha256(self):
        ''' SHA2 checksum test. '''
        sys.argv = ['fedora-review', '-b', '1']
        Settings.init(True)
        Settings.checksum = 'sha256'
        helpers = HelpersMixin()
        checksum = helpers._checksum('scantailor.desktop')
        self.assertEqual(checksum,
            'd8669d49c8557ac47681f9b85e322849fa84186a8683c93959a590d6e7b9ae29')

    def test_sha384(self):
        ''' SHA3 checksum test. '''
        sys.argv = ['fedora-review', '-b', '1']
        Settings.init(True)
        Settings.checksum = 'sha384'
        helpers = HelpersMixin()
        checksum = helpers._checksum('scantailor.desktop')
        self.assertEqual(checksum,
           '3d6a580100b1e8a40dc41892f6b289ff13c0b489b8079d8b7'
           'c01a17c67b88bf77283f784b4e8dacac6572050df8c948e')

    def test_sha512(self):
        ''' SHA5 checksum test. '''
        sys.argv = ['fedora-review', '-b', '1']
        Settings.init(True)
        Settings.checksum = 'sha512'
        helpers = HelpersMixin()
        checksum = helpers._checksum('scantailor.desktop')
        self.assertEqual(checksum,
            '77a138fbd918610d55d9fd22868901bd189d987f17701498'
            '164badea88dd6f5612c118fc9e66d7b57f802bf0cddadc1c'
            'ec54674ee1c3df2ddfaf1cac4007ac26')

    @unittest.skipIf(NO_NET, 'No network available')
    def test_bugzilla_bug(self):
        ''' Scanning of bugzilla bugpage test. '''
        subprocess.check_call('mkdir -p tmp/python-test || :', shell=True)
        self.init_test('tmp',
                       argv=['-b', '817268'],
                       wd='python-test')
        bug = BugzillaBug('817268')
        bug.find_urls()
        expected = 'http://dl.dropbox.com/u/17870887/python-faces-0.11.7-2' \
                  '/python-faces-0.11.7-2.fc16.src.rpm'
        self.assertEqual(expected, bug.srpm_url)
        expected = 'http://dl.dropbox.com/u/17870887/python-faces-0.11.7-2/' \
                   'python-faces.spec'
        self.assertEqual(expected, bug.spec_url)
        self.assertEqual(None, bug.spec_file)
        self.assertEqual(None, bug.srpm_file)

    def test_rpm_spec(self):
        ''' Internal -r check. '''
        self.init_test('test_misc',
                       argv=['-rn', 'python-test', '--cache',
                             '--no-build'])
        bug = NameBug('python-test')
        bug.find_urls()
        expected = 'test/test_misc/python-test-1.0-1.fc17.src.rpm'
        self.assertTrue(bug.srpm_url.endswith(expected))
        expected = 'test/test_misc/srpm-unpacked/python-test.spec'
        self.assertTrue(bug.spec_url.endswith(expected))

    def test_md5sum_diff_ok(self):
        ''' Complete MD5sum test expected to pass. '''
        self.init_test('md5sum-diff-ok',
                       argv=['-rpn', 'python-test', '--cache',
                             '--no-build'])
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
        ''' Complete MD5sum test expected to fail. '''
        loglevel = os.environ['REVIEW_LOGLEVEL']
        os.environ['REVIEW_LOGLEVEL'] = 'ERROR'
        self.init_test('md5sum-diff-fail',
                       argv=['-rpn', 'python-test', '--cache',
                             '--no-build'])
        os.environ['REVIEW_LOGLEVEL'] = loglevel
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
        ''' Test that non-empty resultdir quits. '''
        self.init_test('test_misc',
                       argv=['-n', 'python-test', '--cache'])
        bug = NameBug('python-test')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file).get_checks()
        checks.set_single_check('CheckResultdir')
        check = checks['CheckResultdir']
        if not os.path.exists('results.bak'):
            os.makedirs('results.bak')
        for dirt in glob.glob('results/*.*'):
            shutil.move(dirt, 'results.bak')
        check.run()
        self.assertTrue(check.is_na)

        try:
            subprocess.check_call('touch results/orvar.rpm', shell=True)
        except OSError:
            pass
        self.assertRaises(ReviewError, check.run)
        Settings.nobuild = True
        check.run()
        self.assertTrue(check.is_na)
        os.unlink('results/orvar.rpm')
        for dirt in glob.glob('results.bak/*'):
            shutil.move(dirt, 'results')

    def test_prebuilt_sources(self):
        ''' Local built RPM:s (-n) test. '''
        self.init_test('test_misc',
                       argv=['-cn', 'python-test', '--prebuilt'])
        ReviewDirs.startdir = os.getcwd()
        bug = NameBug('python-test')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)
        subprocess.check_call('touch orvar.rpm', shell=True)
        rpms = Mock.get_package_rpm_paths(checks.spec)
        self.assertEqual(len(rpms), 1)

    def test_bad_specfile(self):
        ''' Specfile with syntactic errors test. '''
        loglevel = os.environ['REVIEW_LOGLEVEL']
        os.environ['REVIEW_LOGLEVEL'] = 'ERROR'
        self.init_test('bad-spec',
                       argv=['-n', 'python-test', '-p', '--cache',
                             '--no-build', '-D', 'DISTTAG=fc19'])
        os.environ['REVIEW_LOGLEVEL'] = loglevel
        bug = NameBug('python-test')
        check = self.run_single_check(bug, 'CheckSpecAsInSRPM')
        self.assertTrue(check.is_failed)
        self.assertTrue('#TestTag' in check.result.attachments[0].text)

    def test_desktop_file_bug(self):
        ''' desktop file handling test. '''

        self.init_test('desktop-file',
                       argv=['-n', 'python-test', '--cache',
                             '--no-build'])
        bug = NameBug('python-test')
        check = self.run_single_check(bug, 'CheckDesktopFileInstall', True)
        self.assertTrue(check.is_passed)

    def test_check_dict(self):
        ''' CheckDict component test. '''

        class TestCheck(AbstractCheck):
            ''' Check mockup. '''
            def run(self):
                pass

            @staticmethod
            # pylint: disable=E0202
            def name():
                ''' return test's name.'''
                return 'foo'

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

    def test_1_unversioned_so(self):
        ''' Handling unversioned-sofile, expected to fail. '''
        self.init_test('unversioned-so',
                       argv=['-rpn', 'python-test'])
        bug = NameBug('python-test')
        check = self.run_single_check(bug, 'CheckSoFiles')
        self.assertTrue(check.is_failed)

    def test_1_unversioned_so_private(self):
        ''' Handling unversioned-sofile, expected to fail. '''
        self.init_test('unversioned-so-private',
                       argv=['-rpn', 'python-test'])
        bug = NameBug('python-test')
        check = self.run_single_check(bug, 'CheckSoFiles')
        self.assertTrue(check.is_pending)

    @unittest.skipIf(FAST_TEST, 'slow test disabled by REVIEW_FAST_TEST')
    def test_local_repo(self):
        ''' Local repo with prebuilt rpms test. '''
        self.init_test('test_misc',
                       argv=['-rn', 'python-test', '--local-repo',
                             'repo', '--cache'])
        bug = NameBug('python-test')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)
        check = checks.checkdict['CheckPackageInstalls']
        check.run()
        self.assertTrue(check.is_passed)

    def test_bad_specname(self):
        ''' Specfile with bad name test. '''
        loglevel = os.environ['REVIEW_LOGLEVEL']
        os.environ['REVIEW_LOGLEVEL'] = 'ERROR'
        self.init_test('bad-specname',
                       argv=['-rn', 'python-test', '--cache'])
        os.environ['REVIEW_LOGLEVEL'] = loglevel
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
                       argv=['-rpn', 'perl-RPM-Specfile', '--no-build'])
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
    if len(sys.argv) > 1:
        suite = unittest.TestSuite()
        for test in sys.argv[1:]:
            suite.addTest(TestMisc(test))
    else:
        suite = unittest.TestLoader().loadTestsFromTestCase(TestMisc)
    unittest.TextTestRunner(verbosity=2).run(suite)

# vim: set expandtab ts=4 sw=4:
