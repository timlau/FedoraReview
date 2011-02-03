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
import inspect
import re

from reviewtools import Helpers, get_logger

TEST_STATES = {'pending': '[ ]','pass': '[x]','fail': '[!]','na': '[-]'}

class CheckBase(Helpers):
    def __init__(self, base):
        Helpers.__init__(self)
        self.base = base
        self.spec = base.spec
        self.srpm = base.srpm
        self.url = None
        self.text = None
        self.description = None
        self.state = 'pending'
        self.type = 'MUST'
        self.result = None
        self.output_extra = None
        self.log = get_logger()
    
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
        msg ='%s : %s - %s' % (TEST_STATES[self.state],self.type, self.text)
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
    
    
class CheckName(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
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
            
class CheckBuildroot(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
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
               

class CheckSpecName(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.text = 'Spec file name must match the spec package %{name}, in the format %{name}.spec.'
        self.automatic = True
        
    def run(self):
        spec_name = '%s.spec' % self.spec.name
        if os.path.basename(self.spec.filename) == spec_name:
            self.set_passed(True)
        else:
            self.set_passed(False, "%s should be %s " % (os.path.basename(self.spec.filename),spec_name))


class CheckIllegalSpecTags(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
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

class CheckClean(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.text = 'Package has a %clean section, which contains rm -rf %{buildroot} (or $RPM_BUILD_ROOT).'
        self.automatic = True
        
    def run(self):
        passed = False
        sec_clean = self.spec.get_section('%clean')
        for sec in sec_clean:
            sec_lines = sec_clean[sec]
            regex = re.compile('^(rm|%{__rm})\s\-rf\s(%{buildroot}|$RPM_BUILD_ROOT)*.')
            if sec_lines:
                for line in sec_lines:
                    if regex.search(line):
                        passed = True
                        break
        self.set_passed(passed)
            
class CheckInstall(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.text = 'Package run rm -rf %{buildroot} (or $RPM_BUILD_ROOT) and the beginning of %install.'
        self.automatic = True
        
    def run(self):
        passed = False
        sec_clean = self.spec.get_section('%install')
        for sec in sec_clean:
            sec_lines = sec_clean[sec]
            regex = re.compile('^(rm|%{__rm})\s\-rf\s(%{buildroot}|$RPM_BUILD_ROOT)*.')
            if sec_lines:
                for line in sec_lines:
                    if regex.search(line):
                        passed = True
                        break
        self.set_passed(passed)

class CheckDefattr(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
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

class CheckSourceMD5(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
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


class CheckBuild(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.text = 'Package successfully compiles and builds into binary rpms on at least one supported architecture.'
        self.automatic = True
        
    def run(self):
        rc = self.srpm.build(force=True) # Force build
        if rc == 0:
            self.set_passed(True)
        else:
            self.set_passed(False)

class CheckRpmLint(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
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
            

class CheckXNum0001(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Spec file is legible and written in American English.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0002(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Spec uses macros instead of hard-coded directory names.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0003(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package consistently uses macros.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0004(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Macros in Summary, %description expandable at SRPM build time.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0005(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Requires correct, justified where necessary.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0006(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'All build dependencies are listed in BuildRequires, except for any that are listed in the exceptions section of Packaging Guidelines.'
        self.automatic = False
        self.type = 'MUST'



class CheckMakeinstall(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = "Package use %makeinstall only when make install DESTDIR=... doesn't work."
        self.automatic = True
        self.type = 'MUST'
        
    def run(self):
        regex = re.compile(r'^(%makeinstall.*)')
        res = self.spec.find(regex)
        if res:
            self.set_passed(False, res.group(0))
        else:
            self.set_passed(True)



class CheckXNum0008(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'The spec file handles locales properly.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0009(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Changelog in prescribed format.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0010(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'License field in the package spec file matches the actual license.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0011(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'If (and only if) the source package includes the text of the license(s) in its own file, then that file, containing the text of the license(s) for the package is included in %doc.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0012(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'License file installed when any subpackage combination is installed.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0013(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package is licensed with an open-source compatible license and meets other legal requirements as defined in the legal section of Packaging Guidelines.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0014(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Sources contain only permissible code or content.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0015(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Compiler flags are appropriate.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0016(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = '%build honors applicable compiler flags or justifies otherwise.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0017(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'ldconfig called in %post and %postun if required.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0018(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package must own all directories that it creates.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0019(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package does not own files or directories owned by other packages.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0020(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package requires other packages for directories it uses.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0021(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package does not contain duplicates in %files.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0022(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Permissions on files are set properly.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0023(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'No %config files under /usr.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0024(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = '%config files are marked noreplace or the reason is justified.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0025(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package contains a properly installed %{name}.desktop using desktop-file-install file if it is a GUI application.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0026(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package contains a valid .desktop file.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0027(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package contains code, or permissable content.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0028(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package contains a SysV-style init script if in need of one.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0029(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'File names are valid UTF-8.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0030(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Large documentation files are in a -doc subpackage, if required.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0031(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package uses nothing in %doc for runtime.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0032(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package contains no bundled libraries.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0033(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Header files in -devel subpackage, if present.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0034(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Static libraries in -static subpackage, if present.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0035(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package contains no static executables.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0036(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package requires pkgconfig, if .pc files are present.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0037(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Development .so files in -devel subpackage, if present.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0038(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Fully versioned dependency in subpackages, if present.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0039(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package does not contain any libtool archives (.la).'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0040(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Useful -debuginfo package or justification otherwise.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0041(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Rpath absent or only used for internal libs.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0042(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package does not genrate any conflict.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0043(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package does not contains kernel modules.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0044(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package is not relocatable.'
        self.automatic = False
        self.type = 'MUST'


class CheckXNum0046(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package is not known to require ExcludeArch.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0047(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package installs properly.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0048(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package obeys FHS, except libexecdir and /usr/target.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0049(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package meets the Packaging Guidelines.'
        self.automatic = False
        self.type = 'MUST'



class CheckXNum0050(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package functions as described.'
        self.automatic = False
        self.type = 'SHOULD'



class CheckXNum0051(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Latest version is packaged.'
        self.automatic = False
        self.type = 'SHOULD'



class CheckXNum0052(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package does not include license text files separate from upstream.'
        self.automatic = False
        self.type = 'SHOULD'



class CheckXNum0053(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'If the source package does not include license text(s) as a separate file from upstream, the packager SHOULD query upstream to include it.'
        self.automatic = False
        self.type = 'SHOULD'



class CheckXNum0054(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Description and summary sections in the package spec file contains translations for supported Non-English languages, if available.'
        self.automatic = False
        self.type = 'SHOULD'



class CheckSourceUrl(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'SourceX is a working URL.'
        self.automatic = True
        self.type = 'SHOULD'

    def run(self):
        # We download the source before running checks, so we will never
        # get here is Source Url is not working
        self.set_passed(True)


class CheckXNum0056(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'SourceX / PatchY prefixed with %{name}.'
        self.automatic = False
        self.type = 'SHOULD'



class CheckXNum0057(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Final provides and requires are sane (rpm -q --provides and rpm -q --requires).'
        self.automatic = False
        self.type = 'SHOULD'



class CheckXNum0058(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = '%check is present and all tests pass.'
        self.automatic = False
        self.type = 'SHOULD'



class CheckXNum0059(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Usually, subpackages other than devel should require the base package using a fully versioned dependency.'
        self.automatic = False
        self.type = 'SHOULD'



class CheckXNum0060(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Reviewer should test that the package builds in mock.'
        self.automatic = False
        self.type = 'SHOULD'



class CheckXNum0061(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package should compile and build into binary rpms on all supported architectures.'
        self.automatic = False
        self.type = 'SHOULD'



class CheckDistTag(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Dist tag is present.'
        self.automatic = True
        self.type = 'SHOULD'

    def run(self):
        self.set_passed(self.spec.find_tag('Release').endswith('%{?dist}'))

class CheckXNum0063(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Spec use %global instead of %define.'
        self.automatic = False
        self.type = 'SHOULD'



class CheckXNum0064(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Scriptlets must be sane, if used.'
        self.automatic = False
        self.type = 'SHOULD'



class CheckXNum0065(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'The placement of pkgconfig(.pc) files are correct.'
        self.automatic = False
        self.type = 'SHOULD'



class CheckXNum0066(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'No file requires outside of /etc, /bin, /sbin, /usr/bin, /usr/sbin.'
        self.automatic = False
        self.type = 'SHOULD'



class CheckXNum0067(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Packages should try to preserve timestamps of original installed files.'
        self.automatic = False
        self.type = 'SHOULD'



class CheckXNum0068(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'File based requires are sane.'
        self.automatic = False
        self.type = 'SHOULD'



class CheckXNum0069(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Man pages included for all executables.'
        self.automatic = False
        self.type = 'SHOULD'



class CheckXNum0070(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Uses parallel make.'
        self.automatic = False
        self.type = 'SHOULD'



class CheckXNum0071(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Patches link to upstream bugs/comments/lists or are otherwise justified.'
        self.automatic = False
        self.type = 'SHOULD'


