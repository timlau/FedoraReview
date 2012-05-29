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
from FedoraReview import Helpers, Source, Sources, SRPMFile, SpecFile, Mock
from FedoraReview.ReviewHelper import ReviewHelper
import FedoraReview
from base import *

class MiscTests(unittest.TestCase):

    def setUp(self):
        self.reviewHelper = ReviewHelper()
        self.helper = Helpers()
        self.srpm_file = os.path.join(os.path.abspath('.'),
                                      os.path.basename(TEST_SRPM))
        self.spec_file = os.path.join(Mock.get_builddir('SOURCES'),
                                        os.path.basename(TEST_SPEC))
        self.source_file = os.path.join(Mock.get_builddir('SOURCES'),
                                        os.path.basename(TEST_SRC))
        if not os.path.exists(TEST_WORK_DIR):
            os.makedirs(TEST_WORK_DIR)
        self.helper.set_work_dir(TEST_WORK_DIR)
        self.helper._get_file(TEST_SRPM)
        #self.helper._get_file(TEST_SRC)

    def test_spec_file(self):
        ''' Test the SpecFile class'''
        self.helper.set_work_dir(Mock.get_builddir('SOURCES'))
        self.helper._get_file(TEST_SPEC)
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



    def test_source_file(self):
        """ Test the SourceFile class """
        sources = Sources()
        source = Source(sources)
        # download the upstream source file
        source.set_work_dir(Mock.get_builddir('SOURCES'))
        source.get_source(TEST_SRC)
        # check that source exists and source.filename point to the right location
        self.assertEqual(source.filename, self.source_file)
        self.assertTrue(os.path.exists(self.source_file))
        self.assertEqual(source.check_source_md5(), "289cb714af3a85fe36a51fa3612b57ad")

    def test_srpm_file(self):
        """ Test the SRPMFile class """
        self.helper.set_work_dir(os.path.abspath('.'))
        self.helper._get_file(TEST_SRPM)
        srpm = SRPMFile(self.srpm_file)
        # install the srpm
        srpm.unpack()
        self.assertTrue(hasattr(srpm, 'unpacked_src'))
        src_dir = srpm.unpacked_src
        src_files = glob.glob(os.path.expanduser(src_dir) + '/*')
        src_files = [os.path.basename(f) for f in  src_files]
        expected = 'python-test-1.0.tar.gz'
        self.assertTrue(expected in src_files)
        print "Starting mock build (patience...)"
        srpm.build(silence=True)
        self.assertTrue(srpm.is_build)
        # Retrieve the list of files in the mock folder and below
        rpms = glob.glob(os.path.join(Mock.resultdir,
                                      'python-test-1.0-1*noarch.rpm'))
        self.assertTrue(len(rpms)==1)

suite = unittest.TestLoader().loadTestsFromTestCase(MiscTests)
sys.argv.extend(['-b','1234'])
FedoraReview.do_logger_setup(loglvl=logging.DEBUG)
unittest.TextTestRunner(verbosity=2).run(suite)
