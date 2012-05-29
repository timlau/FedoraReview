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

import logging
import sys
import os.path
import re
sys.path.insert(0,os.path.abspath('../'))

import os
import unittest
import glob
from FedoraReview import Helpers, Source, Sources, SRPMFile, SpecFile, Mock, Settings
from FedoraReview.checks_class import Checks
from FedoraReview.name_bug import NameBug
import FedoraReview
from base import *

class TestMisc(unittest.TestCase):

    def setUp(self):
        sys.argv = ['fedora-review','-n','python-test','--prebuilt']
        Settings.init()
        FedoraReview.do_logger_setup(loglvl=logging.DEBUG)
        self.log = FedoraReview.get_logger()
        self.helper = Helpers()
        self.srpm_file = os.path.join(os.path.abspath('.'),
                                      os.path.basename(TEST_SRPM))
        self.spec_file = os.path.join(Mock.get_builddir('SOURCES'),
                                        os.path.basename(TEST_SPEC))
        self.source_file = os.path.join(Mock.get_builddir('SOURCES'),
                                        os.path.basename(TEST_SRC))
        if not os.path.exists(TEST_WORK_DIR):
            os.makedirs(TEST_WORK_DIR)
        self.helper._get_file(TEST_SRPM, TEST_WORK_DIR)
        #self.helper._get_file(TEST_SRC)

    def test_source_file(self):
        """ Test the SourceFile class """
        bug = NameBug('python-test')
        bug.find_urls()
        bug.download_files()
        spec = SpecFile(bug.spec_file)
        sources = Sources(spec)
        source = Source(sources, 'Source0', TEST_SRC)
        # check that source exists and source.filename point to the right location
        expected = os.path.abspath(
                       './review/upstream/python-test-1.0.tar.gz')
        self.assertEqual(source.filename, expected)
        self.assertTrue(os.path.exists(self.source_file))
        self.assertEqual(source.check_source_md5(),
                         "289cb714af3a85fe36a51fa3612b57ad")

    def test_sources(self):
        bug = NameBug('python-test')
        bug.find_urls()
        bug.download_files()
        checks = Checks(bug.spec_file, bug.srpm_file)
        checks.add_check_classes()
        checks.set_single_check('CheckSourceMD5')
        self.assertEqual(len(checks.checks), 1)
        check = checks.checks[0]
        check.run()
        result = check.get_result()
        self.log.debug('result : ' + result.result)
        if result.output_extra:
           self.log.debug("Result extra text: " + result.output_extra)
        self.assertEqual( result.result, 'pass')

    def test_spec_file(self):
        ''' Test the SpecFile class'''
        self.helper._get_file(TEST_SPEC, Mock.get_builddir('SOURCES'))
        spec = SpecFile(self.spec_file)
        # Test misc rpm values (Macro resolved)
        self.assertEqual(spec.name,'python-test')
        self.assertEqual(spec.version,'1.0')
        # resolve the dist-tag
        dist = self.helper._run_cmd('rpm --eval %dist')[:-1]
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
        expected = {'%install': ['rm -rf $RPM_BUILD_ROOT', '%{__python} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT']}
        self.assertEqual(spec.get_section('%install'),expected)
        expected = {'%files': ['%defattr(-,root,root,-)', '%doc COPYING', '%{python_sitelib}/*']}
        self.assertEqual(spec.get_section('%files'),expected)
        # Test get_sources (return the Source/Patch lines with macros resolved)
        expected = {'Source0': 'http://timlau.fedorapeople.org/files/test/review-test/python-test-1.0.tar.gz'}
        self.assertEqual(spec.get_sources(), expected)
        # Test find
        regex = re.compile(r'^Release\s*:\s*(.*)')
        res = spec.find(regex)
        if res:
            self.assertEqual(res.groups(), ('1%{?dist}',))
        else:
            self.assertTrue(False)

    def test_srpm_mockbuild(self):
        """ Test the SRPMFile class """
        self.helper._get_file(TEST_SRPM, os.path.abspath('.'))
        srpm = SRPMFile(self.srpm_file)
        # install the srpm
        srpm.unpack()
        self.assertTrue(hasattr(srpm, 'unpacked_src'))
        src_dir = srpm.unpacked_src
        src_files = glob.glob(os.path.expanduser(src_dir) + '/*')
        src_files = [os.path.basename(f) for f in  src_files]
        self.assertTrue('python-test-1.0.tar.gz' in src_files)
        print "Starting mock build (patience...)"
        srpm.mockbuild(silence=True)
        self.assertTrue(srpm.is_build)
        rpms = glob.glob(os.path.join(Mock.resultdir,
                                      'python-test-1.0-1*noarch.rpm'))
        self.assertTrue(len(rpms)==1)

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMisc)
    unittest.TextTestRunner(verbosity=2).run(suite)
