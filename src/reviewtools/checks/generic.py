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
This module contains automatic test for Fedora Packaging guidelines
'''

import os
import os.path
import inspect
import re
import fnmatch

from reviewtools import Helpers, get_logger

TEST_STATES = {'pending': '[ ]','pass': '[x]','fail': '[!]','na': '[-]'}

class CheckBase(Helpers):

    deprecates = []
    header = "Generic"

    def __init__(self, base):
        Helpers.__init__(self)
        self.base = base
        self.spec = base.spec
        self.srpm = base.srpm
        self.sources = base.sources
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
        elif result == "inconclusive":
            self.state = 'pending'
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


    def has_files(self, pattern):
        ''' Check if rpms has file matching a pattern'''
        rpm_files = self.srpm.get_files_rpms()
        for rpm in rpm_files:
            for fn in rpm_files[rpm]:
                if fnmatch.fnmatch(fn, pattern):
                    return True
        return False

    def has_files_re(self, pattern_re):
        ''' Check if rpms has file matching a pattern'''
        fn_pat = re.compile(pattern_re)
        rpm_files = self.srpm.get_files_rpms()
        #print rpm_files, pattern_re
        for rpm in rpm_files:
            for fn in rpm_files[rpm]:
                if fn_pat.search(fn):
                    return True
        return False

    def get_files_by_pattern(self, pattern):
        result = {}
        rpm_files = self.srpm.get_files_rpms()
        for rpm in rpm_files:
            result[rpm] = []
            for fn in rpm_files[rpm]:
                if fnmatch.fnmatch(fn, pattern):
                    result[rpm].append(fn)
        return result

class CheckName(CheckBase):
    '''
    MUST: The package must be named according to the Package Naming Guidelines .
    http://fedoraproject.org/wiki/Packaging/NamingGuidelines
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/NamingGuidelines'
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
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#BuildRoot_tag
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#BuildRoot_tag'
        self.text = 'Buildroot is correct (EPEL5 & Fedora < 10)'
        self.automatic = True

    def run(self):
        br_tags = self.spec.find_tag('BuildRoot')
        if len(br_tags) > 1:
            self.set_passed(False, "Multiple BuildRoot definitions found")
            return

        br = br_tags[0]
        legal_buildroots = [
        '%(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)',
        '%{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)',
        '%{_tmppath}/%{name}-%{version}-%{release}-root']
        if br in legal_buildroots:
            self.set_passed(True,br)
        else:
            self.set_passed(False,br)

    def is_applicable(self):
        '''
        Buildroot tag is ignored for Fedora > 10, but is needed for EPEL5
        '''
        return len(self.spec.find_tag('BuildRoot')) > 0


class CheckSpecName(CheckBase):
    '''
    MUST: The spec file name must match the base package %{name},
    in the format %{name}.spec unless your package has an exemption.
    http://fedoraproject.org/wiki/Packaging/NamingGuidelines#Spec_file_name
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url='http://fedoraproject.org/wiki/Packaging/NamingGuidelines#Spec_file_name'
        self.text = 'Spec file name must match the spec package %{name}, in the format %{name}.spec.'
        self.automatic = True

    def run(self):
        spec_name = '%s.spec' % self.spec.name
        if os.path.basename(self.spec.filename) == spec_name:
            self.set_passed(True)
        else:
            self.set_passed(False, "%s should be %s " % (os.path.basename(self.spec.filename),spec_name))


class CheckIllegalSpecTags(CheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Tags
    '''
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
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#.25clean
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#.25clean'
        self.text = 'Package has a %clean section, which contains rm -rf %{buildroot} (or $RPM_BUILD_ROOT).(EPEL6 & Fedora < 13)'
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
    '''
    http://fedoraproject.org/wiki/EPEL/GuidelinesAndPolicies#Prepping_BuildRoot_For_.25install
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.text = 'Package run rm -rf %{buildroot} (or $RPM_BUILD_ROOT) and the beginning of %install. (EPEL5)'
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
    '''
    MUST: Permissions on files must be set properly.
    Executables should be set with executable permissions, for example.
    Every %files section must include a %defattr(...) line.
    http://fedoraproject.org/wiki/Packaging/Guidelines#FilePermissions
    Update: 29-04-2011 This is only for pre rpm 4.4 that this is needed
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#FilePermissions'
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
    '''
    MUST: The sources used to build the package must match the upstream source,
    as provided in the spec URL. Reviewers should use md5sum for this task.
    If no upstream URL can be specified for this package,
    please see the Source URL Guidelines for how to deal with this.
    http://fedoraproject.org/wiki/Packaging/SourceURL
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/SourceURL'
        self.text = 'Sources used to build the package matches the upstream source, as provided in the spec URL.'
        self.automatic = True

    def run(self):
        self.srpm.install()
        passed = True
        output = ""
        for source in self.base.sources.get_all():
            local = self.base.srpm.check_source_md5(source.filename)
            upstream = source.check_source_md5()
            output += "%s :\n" % source.filename
            output += "  MD5SUM this package     : %s\n" % local
            output += "  MD5SUM upstream package : %s\n" % upstream
            if local != upstream:
                passed = False
        if passed:
            self.set_passed(True, output)
        else:
            self.set_passed(False, output)


class CheckBuild(CheckBase):
    '''
    MUST: The package MUST successfully compile and build into binary rpms
    on at least one primary architecture.
    http://fedoraproject.org/wiki/Packaging/Guidelines#Architecture_Support
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#Architecture_Support'
        self.text = 'Package successfully compiles and builds into binary rpms on at least one supported architecture.'
        self.automatic = True

    def run(self):
        rc = self.srpm.build()
        if rc == 0:
            self.set_passed(True)
        else:
            self.set_passed(False)

class CheckRpmLint(CheckBase):
    '''
    MUST: rpmlint must be run on the source rpm and all binary rpms the build produces.
    The output should be posted in the review.
    http://fedoraproject.org/wiki/Packaging/Guidelines#rpmlint
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = "http://fedoraproject.org/wiki/Packaging/Guidelines#rpmlint"
        self.text = 'Rpmlint output is silent.'
        self.automatic = True

    def run(self):
        failed = False
        no_errors, rc = self.srpm.rpmlint_rpms()
        if not no_errors:
            failed = True
        self.output_extra = rc
        if not failed:
            self.set_passed(True)
        else:
            self.set_passed(False)


class CheckSpecLegibility(CheckBase):
    '''
    MUST: The spec file must be written in American English
    http://fedoraproject.org/wiki/Packaging/Guidelines#summary

    MUST: The spec file for the package MUST be legible.
    http://fedoraproject.org/wiki/Packaging/Guidelines#Spec_Legibility
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#Spec_Legibility'
        self.text = 'Spec file is legible and written in American English.'
        self.automatic = False
        self.type = 'MUST'


class CheckMacros(CheckBase):
    '''
    MUST: Each package must consistently use macros.
    http://fedoraproject.org/wiki/Packaging/Guidelines#macros
    http://fedoraproject.org/wiki/Packaging:RPMMacros
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#macros'
        self.text = 'Package consistently uses macros (instead of hard-coded directory names).'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        br_tag1 = self.spec.find_all(re.compile('.*%{buildroot}.*'))
        br_tag2 = self.spec.find_all(re.compile('.*\$RPM_BUILD_ROOT.*'))
        if br_tag1 and br_tag2:
            self.set_passed(False, 'Using both %{buildroot} and $RPM_BUILD_ROOT')
        else:
            self.set_passed('inconclusive')


class CheckDescMacroes(CheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Source_RPM_Buildtime_Macros
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#Source_RPM_Buildtime_Macros'
        self.text = 'Macros in Summary, %description expandable at SRPM build time.'
        self.automatic = False
        self.type = 'MUST'


class CheckRequires(CheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Requires
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#Requires'
        self.text = 'Requires correct, justified where necessary.'
        self.automatic = False
        self.type = 'MUST'


class CheckBuildRequires(CheckBase):
    '''
    MUST: All build dependencies must be listed in BuildRequires,
    except for any that are listed in the exceptions section of the Packaging Guidelines
    Inclusion of those as BuildRequires is optional. Apply common sense.
    http://fedoraproject.org/wiki/Packaging/Guidelines#Exceptions_2
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#Exceptions_2'
        self.text = 'All build dependencies are listed in BuildRequires, except for any that are \
listed in the exceptions section of Packaging Guidelines.'
        self.automatic = False
        self.type = 'MUST'


class CheckMakeinstall(CheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Why_the_.25makeinstall_macro_should_not_be_used
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#Why_the_.25makeinstall_macro_should_not_be_used'
        self.text = "Package use %makeinstall only when make install DESTDIR=... doesn't work."
        self.automatic = True
        self.type = 'MUST'

    def is_applicable(self):
        regex = re.compile(r'^(%makeinstall.*)')
        res = self.spec.find(regex)
        if res:
            self.set_passed(False, res.group(0))
            return True
        else:
            return False

    def run(self):
        pass


class CheckLocale(CheckBase):
    '''
    MUST: The spec file MUST handle locales properly.
    This is done by using the %find_lang macro. Using %{_datadir}/locale/* is strictly forbidden.
    http://fedoraproject.org/wiki/Packaging/Guidelines#Handling_Locale_Files
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#Handling_Locale_Files'
        self.text = 'The spec file handles locales properly.'
        self.automatic = False
        self.type = 'MUST'

    def is_applicable(self):
        return self.has_files("/usr/share/locale/*/LC_MESSAGES/*.mo")

    def run(self):
        pass


class CheckChangelogFormat(CheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Changelogs
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#Changelogs'
        self.text = 'Changelog in prescribed format.'
        self.automatic = False
        self.type = 'MUST'


class CheckLicenseField(CheckBase):
    '''
    MUST: The License field in the package spec file must match the actual license.
    http://fedoraproject.org/wiki/Packaging/LicensingGuidelines#ValidLicenseShortNames
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/LicensingGuidelines#ValidLicenseShortNames'
        self.text = 'License field in the package spec file matches the actual license.'
        self.automatic = False
        self.type = 'MUST'


class CheckLicensInDoc(CheckBase):
    '''
    MUST: If (and only if) the source package includes the text of the license(s) in its own file,
    then that file, containing the text of the license(s) for the package must be included in %doc.
    http://fedoraproject.org/wiki/Packaging/LicensingGuidelines#License_Text
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/LicensingGuidelines#License_Text'
        self.text = 'If (and only if) the source package includes the text of the license(s) in its own file, \
then that file, containing the text of the license(s) for the package is included in %doc.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        """ Check if there is a license file and if it is present in the
        %doc section.
        """
        haslicensefile = False
        licenses = []
        for f in ['COPYING','LICEN', 'copying', 'licen']:
            if self.has_files("*" + f + "*"):
                haslicensefile = True
                licenses.append(f)

        br = self.spec.find_all(re.compile("%doc.*"))
        for entry in br:
            entries = os.path.basename(entry.group(0)).strip().split()
            for entry in entries:
                for licensefile in licenses:
                    if entry.startswith(licensefile):
                        licenses.remove(licensefile)

        if not haslicensefile:
            self.set_passed("inconclusive")
        else:
            self.set_passed(licenses == [])


class CheckLicenseInSubpackages(CheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/LicensingGuidelines#Subpackage_Licensing
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/LicensingGuidelines#Subpackage_Licensing'
        self.text = 'License file installed when any subpackage combination is installed.'
        self.automatic = False
        self.type = 'MUST'

    def is_applicable(self):
        '''Check if subpackages exists'''
        sections = self.spec.get_section("%package")
        if len(sections) == 0:
            return False
        else:
            return True


class CheckApprovedLicense(CheckBase):
    '''
    MUST: The package must be licensed with a Fedora approved license and
    meet the Licensing Guidelines .
    http://fedoraproject.org/wiki/Packaging/LicensingGuidelines
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/LicensingGuidelines'
        self.text = 'Package is licensed with an open-source compatible license and meets other legal \
requirements as defined in the legal section of Packaging Guidelines.'
        self.automatic = False
        self.type = 'MUST'


class CheckCodeAndContent(CheckBase):
    '''
    MUST: The package must contain code, or permissable content.
    http://fedoraproject.org/wiki/Packaging/Guidelines#CodeVsContent
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#CodeVsContent'
        self.text = 'Sources contain only permissible code or content.'
        self.automatic = False
        self.type = 'MUST'


class CheckBuildCompilerFlags(CheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Compiler_flags
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#Compiler_flags'
        self.text = '%build honors applicable compiler flags or justifies otherwise.'
        self.automatic = False
        self.type = 'MUST'


class CheckOwnDirs(CheckBase):
    '''
    MUST: A package must own all directories that it creates.
    If it does not create a directory that it uses,
    then it should require a package which does create that directory.
    http://fedoraproject.org/wiki/Packaging/Guidelines#FileAndDirectoryOwnership
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#FileAndDirectoryOwnership'
        self.text = 'Package must own all directories that it creates.'
        self.automatic = False
        self.type = 'MUST'


class CheckOwnOther(CheckBase):
    '''
    MUST: Packages must not own files or directories already owned by other packages.
    The rule of thumb here is that the first package to be installed should own the files
    or directories that other packages may rely upon.
    This means, for example, that no package in Fedora should ever share ownership
    with any of the files or directories owned by the filesystem or man package.
    If you feel that you have a good reason to own a file or directory that another package owns,
    then please present that at package review time.
    http://fedoraproject.org/wiki/Packaging/Guidelines#FileAndDirectoryOwnership
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#FileAndDirectoryOwnership'
        self.text = 'Package does not own files or directories owned by other packages.'
        self.automatic = False
        self.type = 'MUST'


class CheckDirectoryRequire(CheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#The_directory_is_also_owned_by_a_package_implementing_required_functionality_of_your_package
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package requires other packages for directories it uses.'
        self.automatic = False
        self.type = 'MUST'


class CheckFilesDuplicates(CheckBase):
    '''
    MUST: A Fedora package must not list a file more than once in the spec file's %files listings.
    (Notable exception: license texts in specific situations)
    http://fedoraproject.org/wiki/Packaging/Guidelines#DuplicateFiles
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#DuplicateFiles'
        self.text = 'Package does not contain duplicates in %files.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        from subprocess import Popen, PIPE
        filename = '%s/build.log' % self.srpm.get_mock_dir()
        try:
            stream = open(filename)
            content = stream.read()
            stream.close()
            for line in content.split('\n'):
                if 'File listed twice' in line:
                    self.set_passed(False, line)
                    return
            self.set_passed(True)
        except Exception, er:
            self.set_passed('inconclusive')

class CheckFilePermissions(CheckBase):
    '''
    MUST: Permissions on files must be set properly.
    Executables should be set with executable permissions,
    for example. Every %files section must include a %defattr(...) line
    http://fedoraproject.org/wiki/Packaging/Guidelines#FilePermissions
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#FilePermissions'
        self.text = 'Permissions on files are set properly.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        for line in self.srpm.rpmlint_output:
            if 'non-standard-executable-perm' in line:
                self.set_passed(False, "See rpmlint output")
                return
        self.set_passed(True)


class CheckNoConfigInUsr(CheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Configuration_files
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#Configuration_files'
        self.text = 'No %config files under /usr.'
        self.automatic = False
        self.type = 'MUST'

    def is_applicable(self):
        sections = self.spec.get_section('%files')
        for section in sections:
            for line in sections[section]:
                if line.startswith('%config'):
                    return True
        return False

    def run(self):
        passed = True
        extra = ""
        sections = self.spec.get_section('%files')
        for section in sections:
            for line in sections[section]:
                if line.startswith('%config'):
                    fn = line.split(' ')[1]
                    if fn.startswith('%{_datadir}'):
                        passed = False
                        extra += line

        self.set_passed(passed,extra)

class CheckConfigNoReplace(CheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Configuration_files
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#Configuration_files'
        self.text = '%config files are marked noreplace or the reason is justified.'
        self.automatic = True
        self.type = 'MUST'

    def is_applicable(self):
        sections = self.spec.get_section('%files')
        for section in sections:
            for line in sections[section]:
                if line.startswith('%config'):
                    return True
        return False

    def run(self):
        passed = True
        extra = ""
        sections = self.spec.get_section('%files')
        for section in sections:
            for line in sections[section]:
                if line.startswith('%config'):
                    if not line.startswith('%config(noreplace)'):
                        passed = False
                        extra += line
        self.set_passed(passed,extra)



class CheckDesktopInstall(CheckBase):
    '''
    MUST: Packages containing GUI applications must include a %{name}.desktop file,
    and that file must be properly installed with desktop-file-install in the %install section.
    If you feel that your packaged GUI application does not need a .desktop file,
    you must put a comment in the spec file with your explanation.
    http://fedoraproject.org/wiki/Packaging/Guidelines#desktop
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#desktop'
        self.text = 'Package contains a properly installed %{name}.desktop using desktop-file-install file if it is a GUI application.'
        self.automatic = False
        self.type = 'MUST'

    def is_applicable(self):
        '''
        check if this test is applicable
        '''
        return self.has_files('*.desktop')



class CheckSysVScripts(CheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging:SysVInitScript
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package contains a SysV-style init script if in need of one.'
        self.automatic = False
        self.type = 'MUST'



class CheckUTF8Filenames(CheckBase):
    '''
    MUST: All filenames in rpm packages must be valid UTF-8.
    http://fedoraproject.org/wiki/Packaging/Guidelines#FilenameEncoding
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#FilenameEncoding'
        self.text = 'File names are valid UTF-8.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        print self.srpm.rpmlint_output
        for output in self.srpm.rpmlint_output:
            # TODO: add encoding check
            if 'wrong-file-end-of-line-encoding' in output:
                self.set_passed(False)
        self.set_passed(True)


class CheckLargeDocs(CheckBase):
    '''
    MUST: Large documentation files must go in a -doc subpackage.
    (The definition of large is left up to the packager's best judgement,
    but is not restricted to size. Large can refer to either size or quantity).
    http://fedoraproject.org/wiki/Packaging/Guidelines#PackageDocumentation
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#PackageDocumentation'
        self.text = 'Large documentation files are in a -doc subpackage, if required.'
        self.automatic = False
        self.type = 'MUST'



class CheckDocRuntime(CheckBase):
    '''
    MUST: If a package includes something as %doc, it must not affect the runtime of the application.
    To summarize: If it is in %doc, the program must run properly if it is not present.
    http://fedoraproject.org/wiki/Packaging/Guidelines#PackageDocumentation
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#PackageDocumentation'
        self.text = 'Package uses nothing in %doc for runtime.'
        self.automatic = False
        self.type = 'MUST'



class CheckBundledLibs(CheckBase):
    '''
    MUST: Packages must NOT bundle copies of system libraries.
    http://fedoraproject.org/wiki/Packaging:Guidelines#Duplication_of_system_libraries
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging:Guidelines#Duplication_of_system_libraries'
        self.text = 'Package contains no bundled libraries.'
        self.automatic = False
        self.type = 'MUST'



class CheckReqPkgConfig(CheckBase):
    '''
    rpm in EPEL5 and below does not automatically create dependencies for pkgconfig files.
    Packages containing pkgconfig(.pc) files must Requires: pkgconfig (for directory ownership and usability).
    http://fedoraproject.org/wiki/EPEL/GuidelinesAndPolicies#EL5
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/EPEL/GuidelinesAndPolicies#EL5'
        self.text = 'Package requires pkgconfig, if .pc files are present. (EPEL5)'
        self.automatic = False
        self.type = 'MUST'

    def is_applicable(self):
        '''
        check if this test is applicable
        '''
        return self.has_files('*.pc')

    def run(self):
        regex = re.compile("^Require:\s*.*pkgconfig.*",re.I)
        lines = self.spec.get_section('main')
        found = False
        for line in lines:
            print line
            res = regex.search(line)
            if res:
                found = True
        self.set_passed(found)





class CheckFullVerReqSub(CheckBase):
    '''
    MUST: In the vast majority of cases, devel packages must require the base
    package using a fully versioned dependency:
    Requires: %{name}%{?_isa} = %{version}-%{release}
    http://fedoraproject.org/wiki/Packaging/Guidelines#RequiringBasePackage
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#RequiringBasePackage'
        self.text = 'Fully versioned dependency in subpackages, if present.'
        self.automatic = True
        self.type = 'MUST'

    def is_applicable(self):
        '''Check if subpackages exists'''
        sections = self.spec.get_section("%package")
        if len(sections) == 0:
            return False
        else:
            return True

    def run(self):
        regex = re.compile(r'Requires:\s*%{name}\s*=\s*%{version}-%{release}')
        sections = self.spec.get_section("%package")
        extra = ""
        errors = False
        for section in sections:
            passed = False
            for line in sections[section]:
                if regex.search(line):
                    passed = True
            if not passed:
                # Requires: %{name}%{?_isa} = %{version}-%{release}
                extra += "Missing : Requires: %%{name}%%{?_isa} = %%{version}-%%{release} in %s" % section
                errors = False
        if errors:
            self.set_passed(False,extra)
        else:
            self.set_passed(True)




class CheckUsefulDebuginfo(CheckBase):
    '''
    Packages should produce useful -debuginfo packages, or explicitly disable them
    when it is not possible to generate a useful one but rpmbuild would do it anyway.
    Whenever a -debuginfo package is explicitly disabled,
    an explanation why it was done is required in the specfile.
    http://fedoraproject.org/wiki/Packaging/Guidelines#Debuginfo_packages
    http://fedoraproject.org/wiki/Packaging:Debuginfo
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#Debuginfo_packages'
        self.text = 'Useful -debuginfo package or justification otherwise.'
        self.automatic = False
        self.type = 'MUST'



class CheckNoConflicts(CheckBase):
    '''
    Whenever possible, Fedora packages should avoid conflicting with each other
    http://fedoraproject.org/wiki/Packaging/Guidelines#Conflicts
    http://fedoraproject.org/wiki/Packaging:Conflicts
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#Conflicts'
        self.text = 'Package does not generates any conflict.'
        self.automatic = False
        self.type = 'MUST'


class CheckExcludeArch(CheckBase):
    '''
    MUST: If the package does not successfully compile, build or work on an architecture,
    then those architectures should be listed in the spec in ExcludeArch.
    Each architecture listed in ExcludeArch MUST have a bug filed in bugzilla,
    describing the reason that the package does not compile/build/work on that architecture.
    The bug number MUST be placed in a comment, next to the corresponding ExcludeArch line.
    http://fedoraproject.org/wiki/Packaging/Guidelines#Architecture_Build_Failures
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#Architecture_Build_Failures'
        self.text = 'Package is not known to require ExcludeArch.'
        self.automatic = False
        self.type = 'MUST'



class CheckPackageInstalls(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package installs properly.'
        self.automatic = False
        self.type = 'MUST'



class CheckObeysFHS(CheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Filesystem_Layout
    http://www.pathname.com/fhs/
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#Filesystem_Layout'
        self.text = 'Package obeys FHS, except libexecdir and /usr/target.'
        self.automatic = False
        self.type = 'MUST'



class CheckMeetPackagingGuidelines(CheckBase):
    '''
    MUST: The package must meet the Packaging Guidelines
    https://fedoraproject.org/wiki/Packaging:Guidelines
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package meets the Packaging Guidelines.'
        self.automatic = False
        self.type = 'MUST'



class CheckFunctionAsDescribed(CheckBase):
    '''
    SHOULD: The reviewer should test that the package functions as described.
    A package should not segfault instead of running, for example.
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package functions as described.'
        self.automatic = False
        self.type = 'SHOULD'



class CheckLatestVersionIsPackaged(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Latest version is packaged.'
        self.automatic = False
        self.type = 'SHOULD'



class CheckLicenseUpstream(CheckBase):
    '''
    SHOULD: If the source package does not include license text(s)
    as a separate file from upstream, the packager SHOULD query upstream to include it.
    http://fedoraproject.org/wiki/Packaging/LicensingGuidelines#License_Text
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/LicensingGuidelines#License_Text'
        self.text = 'Package does not include license text files separate from upstream.'
        self.automatic = False
        self.type = 'SHOULD'



class CheckContainsLicenseText(CheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/LicensingGuidelines#License_Text
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/LicensingGuidelines#License_Text'
        self.text = 'If the source package does not include license text(s) as a separate file from \
upstream, the packager SHOULD query upstream to include it.'
        self.automatic = False
        self.type = 'SHOULD'


class CheckSpecDescTranlation(CheckBase):
    '''
    SHOULD: The description and summary sections in the package spec file
    should contain translations for supported Non-English languages, if available.
    http://fedoraproject.org/wiki/Packaging/Guidelines#summary
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#summary'
        self.text = 'Description and summary sections in the package spec file contains translations \
for supported Non-English languages, if available.'
        self.automatic = False
        self.type = 'SHOULD'


class CheckSourceUrl(CheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/SourceURL
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/SourceURL'
        self.text = 'SourceX is a working URL.'
        self.automatic = True
        self.type = 'SHOULD'

    def run(self):
        passed = True
        output = ""
        for source in self.sources.get_all():
            if source.URL: # this source should have an upstream file
                if not source.downloaded:
                    passed = False
                    output += "%s\n" % source.URL

        if passed:
            self.set_passed(True)
        else:
            self.set_passed(False, output)


class CheckSourcePatchPrefix(CheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/SourceURL
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/SourceURL'
        self.text = 'SourceX / PatchY prefixed with %{name}.'
        self.automatic = True
        self.type = 'SHOULD'

    def is_applicable(self):
        return self.spec.has_patches()

    def run(self):
        regex = re.compile(r'^(Source|Patch)\d*\s*:\s*(.*)')
        result = self.spec.find_all(regex)
        passed = True
        extra = ""
        if result:
            for res in result:
                value = os.path.basename(res.group(2))
                if value.startswith('%{name}') or value.startswith('%{'):
                    continue
                passed = False
                extra += "%s (%s)\n" % (res.string[:-1], value)
            self.set_passed(False, extra)
        else:
            passed = False
            extra = "No SourceX/PatchX tags found"
        self.set_passed(passed, extra)


class CheckFinalRequiresProvides(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Final provides and requires are sane (rpm -q --provides and rpm -q --requires).'
        self.automatic = False
        self.type = 'SHOULD'


class CheckTestSuites(CheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Test_Suites
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#Test_Suites'
        self.text = '%check is present and all tests pass.'
        self.automatic = False
        self.type = 'SHOULD'

class CheckBuildInMock(CheckBase):
    '''
    SHOULD: The reviewer should test that the package builds in mock.
    http://fedoraproject.org/wiki/PackageMaintainers/MockTricks
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/PackageMaintainers/MockTricks'
        self.text = 'Reviewer should test that the package builds in mock.'
        self.automatic = True
        self.type = 'SHOULD'

    def run(self):
        rc = self.srpm.build()
        if rc == 0:
            self.set_passed(True)
        else:
            self.set_passed(False)


class CheckSupportAllArchs(CheckBase):
    '''
    SHOULD: The package should compile and build into binary rpms on
    all supported architectures.
    http://fedoraproject.org/wiki/Packaging/Guidelines#ArchitectureSupport
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#ArchitectureSupport'
        self.text = 'Package should compile and build into binary rpms on all supported architectures.'
        self.automatic = False
        self.type = 'SHOULD'


class CheckDistTag(CheckBase):
    '''
    http://fedoraproject.org/wiki/DistTag
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Dist tag is present.'
        self.automatic = True
        self.type = 'SHOULD'

    def run(self):
        rel_tags = self.spec.find_tag('Release')
        if len(rel_tags) > 1:
            self.set_passed(False, "Multiple Release tags found")
            return
        rel = rel_tags[0]
        self.set_passed(rel.endswith('%{?dist}'))


class CheckUseGlobal(CheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#.25global_preferred_over_.25define
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#.25global_preferred_over_.25define'
        self.text = 'Spec use %global instead of %define.'
        self.automatic = True
        self.type = 'SHOULD'

    def run(self):
        regex = re.compile('(\%define.*)')
        result = self.spec.find_all(regex)
        if result:
            extra = ""
            for res in result:
                extra += "%s\n" % res.group(0)
            self.set_passed(False, extra)
        else:
            self.set_passed(True)


class CheckScriptletSanity(CheckBase):
    '''
    SHOULD: If scriptlets are used, those scriptlets must be sane.
    This is vague, and left up to the reviewers judgement to determine sanity.
    http://fedoraproject.org/wiki/Packaging/Guidelines#Scriptlets
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#Scriptlets'
        self.text = 'Scriptlets must be sane, if used.'
        self.automatic = False
        self.type = 'SHOULD'

    def is_applicable(self):
        regex = re.compile('%(post|postun|posttrans|preun|pretrans|pre)\s+')
        return self.spec.find(regex)


class CheckPkgConfigFiles(CheckBase):
    '''
    SHOULD: The placement of pkgconfig(.pc) files depends on their usecase,
    and this is usually for development purposes, so should be placed in a -devel pkg.
    A reasonable exception is that the main pkg itself is a devel tool
    not installed in a user runtime, e.g. gcc or gdb.
    http://fedoraproject.org/wiki/Packaging/Guidelines#PkgconfigFiles
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#PkgconfigFiles'
        self.text = 'The placement of pkgconfig(.pc) files are correct.'
        self.automatic = True
        self.type = 'SHOULD'

    def is_applicable(self):
        '''
        check if this test is applicable
        '''
        return self.has_files('*.pc')

    def run(self):
        files = self.get_files_by_pattern('*.pc')
        passed = True
        extra = ""
        for rpm in files:
            for fn in files[rpm]:
                if not '-devel' in rpm:
                    passed = False
                    extra += "%s : %s\n" % (rpm, fn)
        self.set_passed(passed, extra)

class CheckFileRequires(CheckBase):
    '''
    SHOULD: If the package has file dependencies outside of
    /etc, /bin, /sbin, /usr/bin, or /usr/sbin consider requiring
    the package which provides the file instead of the file itself.
    http://fedoraproject.org/wiki/Packaging/Guidelines#FileDeps
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#FileDeps'
        self.text = 'No file requires outside of /etc, /bin, /sbin, /usr/bin, /usr/sbin.'
        self.automatic = False
        self.type = 'SHOULD'


class CheckTimeStamps(CheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Timestamps
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#Timestamps'
        self.text = 'Packages should try to preserve timestamps of original installed files.'
        self.automatic = False
        self.type = 'SHOULD'


class CheckManPages(CheckBase):
    '''
    SHOULD: your package should contain man pages for binaries/scripts.
    If it doesn't, work with upstream to add them where they make sense.
    http://fedoraproject.org/wiki/Packaging/Guidelines#Man_pages
    '''
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#Man_pages'
        self.text = 'Man pages included for all executables.'
        self.automatic = False
        self.type = 'SHOULD'

    def is_applicable(self):
        return self.has_files("[/usr]/[s]bin/*")


class CheckParallelMake(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Uses parallel make.'
        self.automatic = False
        self.type = 'SHOULD'

    def is_applicable(self):
        '''
        check if this test is applicable
        '''
        regex = re.compile(r"^make")
        lines=self.spec.get_section('build')
        found = False
        for line in lines:
            res = regex.search(line)
            if res:
                found = True
        self.set_passed(found)
        return found

    def run(self):
        regex = re.compile(r"^make*.%{?_smp_mflags}")
        lines=self.spec.get_section('build')
        found = False
        for line in lines:
            res = regex.search(line)
            if res:
                found = True
        self.set_passed(found)


class CheckPatchComments(CheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Patches link to upstream bugs/comments/lists or are otherwise justified.'
        self.automatic = False
        self.type = 'SHOULD'

    def is_applicable(self):
        return self.spec.has_patches()


class LangCheckBase(CheckBase):
    """ Base class for language specific class. """
    header="Language"

    def is_applicable(self):
        """ By default, language specific check are disabled. """
        return False
