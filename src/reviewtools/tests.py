#!/usr/bin/python -tt
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
This module contains automatic test for Fedora Packaging guidelines
'''

import os
import os.path

from reviewtools import Helpers, Source, SRPMFile, SpecFile

TEST_STATES = {'pending': '[ ]','pass': '[x]','fail': '[!]','na': '[-]'}

class TestBase(Helpers):
    def __init__(self, tag, base):
        Helpers.__init__(self)
        self.base = base
        self.spec = base.spec
        self.srpm = base.srpm
        self.tag = tag
        self.url = None
        self.text = None
        self.description = None
        self.automatic = False 
        self.state = 'pending'
        self.result = None
        self.output_extra = None
    
    def run(self):
        raise NotImplementedError()
    
    def set_passed(self, result, output_extra = None):
        '''
        Set if the test is passed, failed or N/A
        and set optional extra output to be shown in repost
        '''
        if result == None:
            self.state = 'na'
        elif result == True:
            self.state = 'pass'
        else:
            self.state = 'fail'
        if output_extra:
            self.output_extra = output_extra
            
    
    def get_result(self):
        '''
        Get the test report result for this test
        '''
        msg ='%s : %s' % (TEST_STATES[self.state], self.text)
        if self.output_extra:
            for line in self.output_extra.split('\n'):
                msg += '\n        %s' % line
        return msg
    
    def is_applicable(self):
        '''
        check if this test is applicable 
        overload in child class if needed
        '''
        return True
    
    
class TestName(TestBase):
    def __init__(self, tag, base):
        TestBase.__init__(self, tag, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging/NamingGuidelines'
        self.text = 'Package is named according to the Package Naming Guidelines.'
        self.automatic = True
        
    def run(self):
        allowed_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._+"
        output = ''
        passed = True
        for char in self.spec.name:
            if not char in allowed_chars:
                output += "^"
                passed = False
            else:
                output += ' '
        if passed:
            self.set_passed(passed)
        else:
            self.set_passed(passed, '%s\n%s' % (self.spec.name,output))
            
class TestBuildroot(TestBase):
    def __init__(self, tag, base):
        TestBase.__init__(self, tag, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging/NamingGuidelines'
        self.text = 'Buildroot is correct (%{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)).'
        self.automatic = True
        
    def run(self):
        br = self.spec.find_tag('BuildRoot')
        legal_buildroots = ['%{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)']
        if br in legal_buildroots:
            self.set_passed(True)
        else:
            self.set_passed(False,br)
               

class TestSpecName(TestBase):
    def __init__(self, tag, base):
        TestBase.__init__(self, tag, base)
        self.text = 'Spec file name must match the spec package %{name}, in the format %{name}.spec.'
        self.automatic = True
        
    def run(self):
        spec_name = '%s.spec' % self.spec.name
        if os.path.basename(self.spec.filename) == spec_name:
            self.set_passed(True)
        else:
            self.set_passed(False, "%s should be %s " % (os.path.basename(self.spec.filename),spec_name))


class TestIllegalSpecTags(TestBase):
    def __init__(self, tag, base):
        TestBase.__init__(self, tag, base)
        self.text = 'Spec file lacks Packager, Vendor, PreReq tags.'
        self.automatic = True
        
    def run(self):
        passed = True
        output = ''
        for tag in ('Packager', 'Vendor', 'PreReq'):
            value = self.spec.get_from_spec(tag)
            if value:
                passed = False
                output += 'Found : %s: %s\n' % (tag,value)
        if not passed:
            self.set_passed(passed, output)
        else:
            self.set_passed(passed)

class TestClean(TestBase):
    def __init__(self, tag, base):
        TestBase.__init__(self, tag, base)
        self.text = 'Package has a %clean section, which contains rm -rf %{buildroot} (or $RPM_BUILD_ROOT).'
        self.automatic = True
        
    def run(self):
        passed = False
        sec_clean = self.spec.get_section('%clean')
        for sec in sec_clean:
            sec_lines = sec_clean[sec]
            if sec_lines:
                for line in sec_lines:
                    if line in ('rm -rf %{buildroot}', 'rm -rf $RPM_BUILD_ROOT'):
                        passed = True
                        break
        self.set_passed(passed)
            
class TestInstall(TestBase):
    def __init__(self, tag, base):
        TestBase.__init__(self, tag, base)
        self.text = 'Package run rm -rf %{buildroot} (or $RPM_BUILD_ROOT) and the beginning of %install.'
        self.automatic = True
        
    def run(self):
        passed = False
        sec_clean = self.spec.get_section('%install')
        for sec in sec_clean:
            sec_lines = sec_clean[sec]
            if sec_lines:
                for line in sec_lines:
                    if line in ('rm -rf %{buildroot}', 'rm -rf $RPM_BUILD_ROOT'):
                        passed = True
                        break
        self.set_passed(passed)

class TestDefattr(TestBase):
    def __init__(self, tag, base):
        TestBase.__init__(self, tag, base)
        self.text = 'Each %files section contains %defattr'
        self.automatic = True
        
    def run(self):
        passed = True
        output = ''
        sec_files = self.spec.get_section('%files')
        for sec in sec_files:
            sec_lines = sec_files[sec]
            if sec_lines:
                if not sec_lines[0].startswith('%defattr('):
                    passed = False
                    output = 'Missing defattr(....) in %s section' % sec
                    break
        if passed:
            self.set_passed(passed)
        else:
            self.set_passed(passed,output)

class TestSourceMD5(TestBase):
    def __init__(self, tag, base):
        TestBase.__init__(self, tag, base)
        self.text = 'Sources used to build the package matches the upstream source, as provided in the spec URL.'
        self.automatic = True
        
    def run(self):
        self.srpm.install()
        local = self.base.srpm.check_source_md5()
        upstream = self.base.source.check_source_md5()
        output = "MD5SUM this package     : %s\n" % local
        output += "MD5SUM upstream package : %s" % upstream     
        if local == upstream:
            self.set_passed(True, output)
        else:
            self.set_passed(False, output)


class TestBuild(TestBase):
    def __init__(self, tag, base):
        TestBase.__init__(self, tag, base)
        self.text = 'Package successfully compiles and builds into binary rpms on at least one supported architecture.'
        self.automatic = True
        
    def run(self):
        rc = self.srpm.build()
        if rc == 0:
            self.set_passed(True)
        else:
            self.set_passed(False)

class TestRpmLint(TestBase):
    def __init__(self, tag, base):
        TestBase.__init__(self, tag, base)
        self.text = 'Rpmlint output is silent.'
        self.automatic = True
        
    def run(self):
        failed = False
        no_errors, rc = self.srpm.rpmlint()
        if not no_errors:
            failed = True
        self.output_extra = rc
        no_errors, rc = self.srpm.rpmlint_rpms()
        if not no_errors:
            failed = True
        self.output_extra += rc
        if not failed:
            self.set_passed(True)   
        else:     
            self.set_passed(False)   
            
class Checks:
    def __init__(self, spec_file, srpm_file, src_file=None, src_url=None):
        self.tests = {}
        self.taglist = []
        self.spec = SpecFile(spec_file)
        self.source = Source(filename=src_file, URL=src_url)
        self.srpm = SRPMFile(srpm_file, self.spec)
    
        
    def add(self,tag, class_name):
        self.taglist.append(tag)
        self.tests[tag] = class_name(tag, self)
        
    def show_file(self, filename):
        fd = open(filename, "r")
        lines =  fd.readlines()
        fd.close()
        for line in lines:
            print(line[:-1])
        
    def run_tests(self, header=None, footer=None):
        if header:
            self.show_file(header)
        for tag in self.taglist:
            test = self.tests[tag]
            test.run()
            result = test.get_result()
            if result:
                print result
        if footer:
            self.show_file(footer)

