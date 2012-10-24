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
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# (C) 2011 - Tim Lauridsen <timlau@fedoraproject.org>


'''
This module contains automatic test for Fedora Packaging guidelines
'''

import os
import os.path
import re

from glob import glob
from StringIO import StringIO
from subprocess import Popen, PIPE
try:
    from subprocess import check_output
except ImportError:
    from FedoraReview.el_compat import check_output


from FedoraReview import CheckBase, Mock, ReviewDirs, ReviewError
from FedoraReview import RegistryBase, Settings


def _in_list(what, list_):
    ''' test if 'what' is in each item in list_. '''
    for item in list_:
        if not item:
            return False
        if not what in item:
            return False
    return True


class Registry(RegistryBase):
    ''' Module registration, register all checks. '''
    group = 'Generic'

    def register_flags(self):
        epel5 = self.Flag('EPEL5', 'Review package for EPEL5', __file__)
        self.checks.flags.add(epel5)

    def is_applicable(self):
        return True


class GenericCheckBase(CheckBase):
    ''' Base class for all generic tests. '''

    def __init__(self, checks):
        CheckBase.__init__(self, checks, __file__)


class CheckApprovedLicense(GenericCheckBase):
    '''
    MUST: The package must be licensed with a Fedora approved license and
    meet the Licensing Guidelines .
    http://fedoraproject.org/wiki/Packaging/LicensingGuidelines
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/LicensingGuidelines'
        self.text = 'Package is licensed with an open-source'       \
                    ' compatible license and meets other legal'     \
                    ' requirements as defined in the legal section' \
                    ' of Packaging Guidelines.'
        self.automatic = False
        self.type = 'MUST'


class CheckBundledLibs(GenericCheckBase):
    '''
    MUST: Packages must NOT bundle copies of system libraries.
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging:Guidelines#Duplication_of_system_libraries'
        self.text = 'Package contains no bundled libraries.'
        self.automatic = False
        self.type = 'MUST'


class CheckBuildCompilerFlags(GenericCheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Compiler_flags
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Compiler_flags'
        self.text = '%build honors applicable compiler flags or ' \
                    'justifies otherwise.'
        self.automatic = False
        self.type = 'MUST'


class CheckBuildInMock(GenericCheckBase):
    '''
    SHOULD: The reviewer should test that the package builds in mock.
    http://fedoraproject.org/wiki/PackageMaintainers/MockTricks
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'PackageMaintainers/MockTricks'
        self.text = 'Reviewer should test that the package builds in mock.'
        self.automatic = True
        self.type = 'SHOULD'

    def run(self):
        self.set_passed(self.checks.checkdict['CheckBuild'].is_passed)


class CheckBuildroot(GenericCheckBase):
    ''' Is buildroot defined as appropriate? '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#BuildRoot_tag'
        self.text = 'Buildroot is not present'
        self.automatic = True
        self.type = 'SHOULD'

    def run(self):
        br_tags = self.spec.find_all('^BuildRoot')
        if len(br_tags) == 0:
            if self.flags['EPEL5']:
                self.set_passed(self.FAIL,
                                'Missing buildroot (required for EPEL5)')
            else:
                self.set_passed(self.PASS)
            return
        elif len(br_tags) > 1:
            self.set_passed(self.FAIL,
                            'Multiple BuildRoot definitions found')
            return

        try:
            br = br_tags[0].split(':')[1].strip()
        except IndexError:
            br = 'Illegal buildroot line:' + br_tags[0]
        legal_buildroots = [
        '%(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)',
        '%{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)',
        '%{_tmppath}/%{name}-%{version}-%{release}-root']
        if br in legal_buildroots:
            if self.flags['EPEL5']:
                self.set_passed(self.PASS)
            else:
                self.set_passed(self.PENDING,
                               'Buildroot: present but not needed')
        else:
            self.set_passed(self.FAIL,
                            'Invalid buildroot found: %s' % br)


class CheckBuildRequires(GenericCheckBase):
    '''
    MUST: All build dependencies must be listed in BuildRequires,
    except for any that are listed in the exceptions section of the
    Packaging Guidelines Inclusion of those as BuildRequires is
    optional. Apply common sense.
    http://fedoraproject.org/wiki/Packaging/Guidelines#Exceptions_2
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Exceptions_2'
        self.text = 'All build dependencies are listed in BuildRequires,' \
                    ' except for any that are  listed in the exceptions' \
                    ' section of Packaging Guidelines.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):

        if  self.checks.checkdict['CheckBuild'].is_pending:
            self.set_passed('pending', 'Using prebuilt rpms.')
        elif self.checks.checkdict['CheckBuild'].is_passed:
            brequires = self.spec.build_requires
            pkg_by_default = ['bash', 'bzip2', 'coreutils', 'cpio',
                'diffutils', 'fedora-release', 'findutils', 'gawk',
                'gcc', 'gcc-c++', 'grep', 'gzip', 'info', 'make',
                'patch', 'redhat-rpm-config', 'rpm-build', 'sed',
                'shadow-utils', 'tar', 'unzip', 'util-linux-ng',
                'which', 'xz']
            intersec = list(set(brequires).intersection(set(pkg_by_default)))
            if intersec:
                self.set_passed(False, 'These BR are not needed: %s' % (
                ' '.join(intersec)))
            else:
                self.set_passed(True)
        else:
            self.set_passed(False,
                            'The package did not build '
                            'BR could therefore not be checked or the'
                            ' package failed to build because of'
                            ' missing BR')


class CheckChangelogFormat(GenericCheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Changelogs
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Changelogs'
        self.text = 'Changelog in prescribed format.'
        self.automatic = False
        self.type = 'MUST'


class CheckClean(GenericCheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#.25clean
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#.25clean'
        self.text = 'Package has no %clean section with rm -rf' \
                    ' %{buildroot} (or $RPM_BUILD_ROOT)'
        self.automatic = True
        self.type = 'SHOULD'

    def run(self):
        has_clean = False
        sec_clean = self.spec.get_section('%clean')
        if sec_clean:
            regex = re.compile('^(rm|%{__rm})\s+\-rf\s+(%{buildroot}|'
                               '\$RPM_BUILD_ROOT)\s*$')
            for line in sec_clean:
                if regex.search(line):
                    has_clean = True
                    break
        if self.flags['EPEL5']:
            self.text = 'EPEL5 requires explicit %clean with rm -rf' \
                             ' %{buildroot} (or $RPM_BUILD_ROOT)'
            self.type = 'MUST'
            if has_clean:
                self.set_passed(self.PASS)
            else:
                self.set_passed(self.FAIL)
        else:
            if has_clean:
                self.set_passed(self.PENDING,
                                '%clean present but not required')
            else:
                self.set_passed(self.PASS)


class CheckDistTag(GenericCheckBase):
    '''
    http://fedoraproject.org/wiki/DistTag
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Dist tag is present.'
        self.automatic = True
        self.type = 'SHOULD'

    def run(self):
        rel_tags = self.spec.find_all('^Release\s*:')
        if len(rel_tags) > 1:
            self.set_passed(False, 'Multiple Release tags found')
            return
        rel = rel_tags[0]
        self.set_passed(rel.endswith('%{?dist}'))


class CheckCodeAndContent(GenericCheckBase):
    '''
    MUST: The package must contain code, or permissable content.
    http://fedoraproject.org/wiki/Packaging/Guidelines#CodeVsContent
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#CodeVsContent'
        self.text = 'Sources contain only permissible' \
                    ' code or content.'
        self.automatic = False
        self.type = 'MUST'


class CheckConfigNoReplace(GenericCheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Configuration_files
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Configuration_files'
        self.text = '%config files are marked noreplace or the reason' \
                    ' is justified.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        rc = self.NA
        extra = ''
        for pkg in self.spec.packages:
            for line in self.spec.get_files(pkg):
                if line.startswith('%config'):
                    if not line.startswith('%config(noreplace)'):
                        extra += line
                    else:
                        rc = self.PASS
        self.set_passed(self.FAIL if extra else rc, extra)


class CheckContainsLicenseText(GenericCheckBase):
    ''' Handle missing license info.  '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/LicensingGuidelines#License_Text'
        self.text = 'If the source package does not include license' \
                    ' text(s) as a separate file from upstream, the' \
                    ' packager SHOULD query upstream to include it.'
        self.automatic = False
        self.type = 'SHOULD'


class CheckCleanBuildroot(GenericCheckBase):
    ''' Check that buildroot is cleaned as appropriate. '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.text = 'Package does not run rm -rf %{buildroot}' \
                    ' (or $RPM_BUILD_ROOT) at the beginning of %install.'
        self.automatic = True

    def run(self):
        has_clean = False
        regex = re.compile('^(rm|%{__rm})\s\-rf\s(%{buildroot}|'
                           '\$RPM_BUILD_ROOT)\s*$')
        install_sec = self.spec.get_section('%install', raw=True)
        has_clean = install_sec and regex.search(install_sec)
        if self.flags['EPEL5']:
            self.text = 'EPEL5: Package does run rm -rf %{buildroot}' \
                  ' (or $RPM_BUILD_ROOT) at the beginning of %install.'
        if has_clean and self.flags['EPEL5']:
            self.set_passed(self.PASS)
        elif has_clean and not self.flags['EPEL5']:
            self.set_passed(self.PENDING,
                           'rm -rf %{buildroot} present but not required')
        elif not has_clean and self.flags['EPEL5']:
            self.set_passed(self.FAIL)
        else:
            self.set_passed(self.PASS)


class CheckDefattr(GenericCheckBase):
    '''
    MUST: Permissions on files must be set properly.  Executables
    should be set with executable permissions, for example.  Every
    %files section must include a %defattr(...) line.
    http://fedoraproject.org/wiki/Packaging/Guidelines#FilePermissions
    Update: 29-04-2011 This is only for pre rpm 4.4 that this is needed
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#FilePermissions'
        self.text = 'Each %files section contains %defattr if rpm < 4.4'
        self.automatic = True

    def run(self):
        has_defattr = False
        for pkg in self.spec.packages:
            if pkg.endswith('-debuginfo'):
                #auto-generated %defattr, ignore
                continue
            for line in self.spec.get_files(pkg):
                if line.startswith('%defattr('):
                    has_defattr = True
                    break
        if has_defattr and self.flags['EPEL5']:
            self.set_passed(self.PASS)
        elif has_defattr and not self.flags['EPEL5']:
            self.set_passed(self.PENDING,
                            '%defattr present but not needed')
        elif not has_defattr and self.flags['EPEL5']:
            self.set_passed(self.FAIL,
                            '%defattr missing, required by EPEL5')
        else:
            self.set_passed(self.PASS)


class CheckDescMacros(GenericCheckBase):
    ''' Macros is description etc. should be expandable. '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Source_RPM_Buildtime_Macros'
        self.text = 'Macros in Summary, %description expandable at' \
                    ' SRPM build time.'
        self.automatic = False
        self.type = 'MUST'


class CheckDesktopFile(GenericCheckBase):
    '''
    MUST: Packages containing GUI applications must include a
    %{name}.desktop file. If you feel that your packaged GUI
    application does not need a .desktop file, you must put a
    comment in the spec file with your explanation.
    http://fedoraproject.org/wiki/Packaging/Guidelines#desktop
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#desktop'
        self.text = 'Package contains desktop file if it is a GUI' \
                    ' application.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        have_desktop = self.rpms.has_files('*.desktop')
        self.set_passed(True if have_desktop else 'inconclusive')


class CheckDesktopFileInstall(GenericCheckBase):
    '''
    MUST: Packages containing GUI applications must include a
    %{name}.desktop file, and that file must be properly installed
    with desktop-file-install in the %install section.
    http://fedoraproject.org/wiki/Packaging/Guidelines#desktop
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#desktop'
        self.text = 'Package installs a  %{name}.desktop using' \
                    ' desktop-file-install' \
                    ' if there is such a file.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        if not self.rpms.has_files('*.desktop'):
            self.set_passed('not_applicable')
            return
        pattern = r'(desktop-file-install|desktop-file-validate)' \
                   '.*(desktop|SOURCE)'
        found = self.spec.find(re.compile(pattern))
        self.set_passed(self.PASS if found else self.FAIL)


class CheckDevelFilesInDevel(GenericCheckBase):
    '''
    MUST: Development files must be in a -devel package
    '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#DevelPackages'
        self.text = 'Development files must be in a -devel package'
        self.automatic = False
        self.type = 'MUST'


class CheckDirectoryRequire(GenericCheckBase):
    ''' Package should require directories it uses. '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package requires other packages for directories it uses.'
        self.automatic = False
        self.type = 'MUST'


class CheckDocRuntime(GenericCheckBase):
    '''
    MUST: If a package includes something as %doc, it must not affect
    the runtime of the application.  To summarize: If it is in %doc,
    the program must run properly if it is not present.
    http://fedoraproject.org/wiki/Packaging/Guidelines#PackageDocumentation
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#PackageDocumentation'
        self.text = 'Package uses nothing in %doc for runtime.'
        self.automatic = False
        self.type = 'MUST'


class CheckExcludeArch(GenericCheckBase):
    '''
    MUST: If the package does not successfully compile, build or work
    on an architecture, then those architectures should be listed in
    the spec in ExcludeArch.  Each architecture listed in ExcludeArch
    MUST have a bug filed in bugzilla, describing the reason that the
    package does not compile/build/work on that architecture.  The bug
    number MUST be placed in a comment, next to the corresponding
    ExcludeArch line.
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Architecture_Build_Failures'
        self.text = 'Package is not known to require ExcludeArch.'
        self.automatic = False
        self.type = 'MUST'


class CheckFileDuplicates(GenericCheckBase):
    '''
    MUST: A Fedora package must not list a file more than once in the
    spec file's %files listings.  (Notable exception: license texts in
    specific situations)
    http://fedoraproject.org/wiki/Packaging/Guidelines#DuplicateFiles
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#DuplicateFiles'
        self.text = 'Package does not contain duplicates in %files.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        filename = os.path.join(Mock.resultdir, 'build.log')
        try:
            stream = open(filename)
        except IOError:
            self.set_passed('inconclusive')
            return
        content = stream.read()
        stream.close()
        for line in content.split('\n'):
            if 'File listed twice' in line:
                self.set_passed(False, line)
                return
        self.set_passed(True)


class CheckFilePermissions(GenericCheckBase):
    '''
    MUST: Permissions on files must be set properly.  Executables
    should be set with executable permissions, for example. Every
    %files section must include a %defattr(...) line
    http://fedoraproject.org/wiki/Packaging/Guidelines#FilePermissions
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#FilePermissions'
        self.text = 'Permissions on files are set properly.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        for line in Mock.rpmlint_output:
            if 'non-standard-executable-perm' in line:
                self.set_passed(False, 'See rpmlint output')
                return
        self.set_passed(True)


class CheckFileRequires(GenericCheckBase):
    '''
    SHOULD: If the package has file dependencies outside of /etc,
    /bin, /sbin, /usr/bin, or /usr/sbin consider requiring the package
    which provides the file instead of the file itself.
    http://fedoraproject.org/wiki/Packaging/Guidelines#FileDeps
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#FileDeps'
        self.text = 'No file requires outside of' \
                    ' /etc, /bin, /sbin, /usr/bin, /usr/sbin.'
        self.automatic = True
        self.type = 'SHOULD'

    def run(self):

        def is_acceptable(req):
            ''' Is a requiremetn acceptable? '''
            for acceptable in ['/usr/bin/', '/etc/', '/bin/', '/sbin/',
                               '/usr/sbin/']:
                if req.startswith(acceptable):
                    return True
            return not req.startswith('/')

        def get_requires(rpm_name, requires):
            ''' Return printable requirements for a rpm. '''
            requires = filter(lambda s: not 'rpmlib' in s, requires)
            requires = filter(lambda s: not 'GLIBC' in s, requires)
            requires = sorted(list(set(requires)))
            hdr = rpm_name + ' (rpmlib, GLIBC filtered):'
            requires.insert(0, hdr)
            return '\n    '.join(requires) + '\n'

        def get_provides(rpm_name, provides):
            ''' Return printable Provides:  for a rpm. '''
            provides = sorted(list(set(provides)))
            provides.insert(0, rpm_name + ':')
            return '\n    '.join(provides) + '\n'

        wrong_req = []
        req_txt = ''
        prov_txt = ''
        for pkg in self.rpms.get_keys():
            rpm_pkg = self.rpms.get(pkg)
            requires = rpm_pkg.requires
            for req in requires:
                if not is_acceptable(req):
                    wrong_req.append(req)
            req_txt += get_requires(pkg, requires) + '\n'
            prov_txt += get_provides(pkg, rpm_pkg.provides) + '\n'
        attachments = [self.Attachment('Requires', req_txt, 10),
                       self.Attachment('Provides', prov_txt, 10)]
        if len(wrong_req) == 0:
            self.set_passed(True, None, attachments)
        else:
            text = "Incorrect Requires : %s " % (', '.join(wrong_req))
            self.set_passed(False, text, attachments)


class CheckFinalRequiresProvides(GenericCheckBase):
    ''' Final Requires: and Provides: should be sane. '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Final provides and requires are sane' \
                    ' (rpm -q --provides and rpm -q --requires).'
        self.automatic = False
        self.type = 'SHOULD'


class CheckFullVerReqSub(GenericCheckBase):
    '''
    MUST: In the vast majority of cases, devel packages must require the base
    package using a fully versioned dependency:
    Requires: %{name}%{?_isa} = %{version}-%{release}
    '''

    HDR = 'No Requires: %{name}%{?_isa} = %{version}-%{release} in '
    REGEX = r'Requires:\s*%{name}\s*=\s*%{version}-%{release}'

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#RequiringBasePackage'
        self.text = 'Fully versioned dependency in subpackages,' \
                    ' if present.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        bad_pkgs = []
        regex = re.compile(self.REGEX)
        for pkg in self.spec.packages:
            if not pkg.endswith('-devel'):
                continue
            requires = ' '.join(self.spec.get_requires(pkg))
            if not regex.search(requires):
                bad_pkgs.append(pkg)
        if bad_pkgs:
            self.set_passed(self.PENDING,
                            self.HDR + ' , '.join(bad_pkgs))
        else:
            self.set_passed(self.PASS)


class CheckFunctionAsDescribed(GenericCheckBase):
    '''
    SHOULD: The reviewer should test that the package functions as described.
    A package should not segfault instead of running, for example.
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package functions as described.'
        self.automatic = False
        self.type = 'SHOULD'


class CheckGuidelines(GenericCheckBase):
    '''
    MUST: The package complies to the Packaging Guidelines.
    http://fedoraproject.org/wiki/Packaging:Guidelines
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package complies to the Packaging Guidelines'
        self.automatic = False
        self.type = 'MUST'


class CheckIllegalSpecTags(GenericCheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Tags
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.text = 'Spec file lacks Packager, Vendor, PreReq tags.'
        self.automatic = True

    def run(self):
        passed = True
        output = ''
        for tag in ('Packager', 'Vendor', 'PreReq'):
            value = self.spec.expand_tag(tag)
            if value:
                passed = False
                output += 'Found : %s: %s\n' % (tag, value)
        if not passed:
            self.set_passed(passed, output)
        else:
            self.set_passed(passed)


class CheckLargeDocs(GenericCheckBase):
    '''
    MUST: Large documentation files must go in a -doc subpackage.
    (The definition of large is left up to the packager's best
    judgement, but is not restricted to size. Large can refer to
    either size or quantity).
    http://fedoraproject.org/wiki/Packaging/Guidelines#PackageDocumentation
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#PackageDocumentation'
        self.text = 'Large documentation files are in a -doc' \
                    ' subpackage, if required.'
        self.automatic = False
        self.type = 'MUST'


class CheckLatestVersionIsPackaged(GenericCheckBase):
    ''' We package latest version, don't we? '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Latest version is packaged.'
        self.automatic = False
        self.type = 'SHOULD'


class CheckLicenseField(GenericCheckBase):

    '''
    MUST: The License field in the package spec file must match the
    actual license.
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/' \
                   'LicensingGuidelines#ValidLicenseShortNames'
        self.text = 'License field in the package spec file' \
                    ' matches the actual license.'
        self.automatic = True
        self.type = 'MUST'

    @staticmethod
    def _write_license(files_by_license, filename):
        ''' Dump files_by_license to filename. '''
        with open(filename, 'w') as f:
            for license_ in files_by_license.iterkeys():
                f.write('\n' + license_ + '\n')
                f.write('-' * len(license_) + '\n')
                for path in sorted(files_by_license[license_]):
                    f.write(path + '\n')

    @staticmethod
    def _get_source_dir():
        ''' Decide which directory to run licensecheck on. This can be
        either patched sources, or we use vanilla unpacked upstream
        tarballs if first option fails '''
        s = Mock.get_builddir('BUILD') + '/*'
        globs = glob(s)
        if globs:
            msg = 'Checking patched sources after %prep for licenses.'
            source_dir = globs[0]
        else:
            msg = 'There is no build directory. Running licensecheck ' \
                   'on vanilla upstream sources.'
            source_dir = ReviewDirs.upstream_unpacked
        return (source_dir, msg)

    def run(self):

        def license_is_valid(_license):
            ''' Test that license from licencecheck is parsed OK. '''
            return not 'UNKNOWN'  in _license and \
                  not 'GENERATED' in _license

        def parse_licenses(raw_text):
            ''' Convert licensecheck output to files_by_license. '''
            files_by_license = {}
            raw_file = StringIO(raw_text)
            while True:
                line = raw_file.readline()
                if not line:
                    break
                try:
                    file_, license_ = line.split(':')
                except ValueError:
                    continue
                file_ = file_.strip()
                license_ = license_.strip()
                if not license_is_valid(license_):
                    license_ = 'Unknown or generated'
                if not license in files_by_license.iterkeys():
                    files_by_license[license_] = []
                files_by_license[license_].append(file_)
            return files_by_license

        try:
            source_dir, msg = self._get_source_dir()
            self.log.debug("Scanning sources in " + source_dir)
            licenses = []
            if os.path.exists(source_dir):
                cmd = 'licensecheck -r ' + source_dir
                out = check_output(cmd, shell=True)
                self.log.debug("Got license reply, length: %d" % len(out))
                licenses = parse_licenses(out)
                filename = os.path.join(ReviewDirs.root,
                                        'licensecheck.txt')
                self._write_license(licenses, filename)
            else:
                self.log.error('Source directory %s does not exist!' %
                                source_dir)
            if not licenses:
                msg += ' No licenses found.'
                msg += ' Please check the source files for licenses manually.'
                self.set_passed(False, msg)
            else:
                msg += ' Licenses found: "' \
                         + '", "'.join(licenses.iterkeys()) + '".'
                msg += ' %d files have unknown license.' % len(licenses)
                msg += ' Detailed output of licensecheck in ' + filename
                self.set_passed('inconclusive', msg)
        except OSError, e:
            self.log.error('OSError: %s' % str(e))
            msg = ' Programmer error: ' + e.strerror
            self.set_passed('inconclusive', msg)


class CheckLicensInDoc(GenericCheckBase):
    '''
    MUST: If (and only if) the source package includes the text of the
    license(s) in its own file, then that file, containing the text of
    the license(s) for the package must be included in %doc.
    http://fedoraproject.org/wiki/Packaging/LicensingGuidelines#License_Text
    '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/LicensingGuidelines#License_Text'
        self.text = 'If (and only if) the source package includes' \
                    ' the text of the license(s) in its own file,' \
                    ' then that file, containing the text of the'  \
                    ' license(s) for the package is included in %doc.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        """ Check if there is a license file and if it is present in the
        %doc section.
        """

        licenses = []
        for potentialfile in ['COPYING', 'LICEN', 'copying', 'licen']:
            pattern = '*' + potentialfile + '*'
            for pkg in self.spec.packages:
                licenses.extend(
                            self.rpms.find_all(pattern, pkg))
        licenses = map(lambda f: f.split('/')[-1], licenses)
        if licenses == []:
            self.set_passed('inconclusive')
            return

        docs = []
        for pkg in self.spec.packages:
            rpm_path = Mock.get_package_rpm_path(pkg, self.spec)
            cmd = 'rpm -qldp ' + rpm_path
            doclist = check_output(cmd.split())
            docs.extend(doclist.split())
        docs = map(lambda f: f.split('/')[-1], docs)

        for _license in licenses:
            if not _license in docs:
                self.log.debug("Cannot find " + _license +
                               " in doclist")
                self.set_passed(False,
                                "Cannot find %s in rpm(s)" % _license)
                return
        self.set_passed(True)


class CheckLicenseInSubpackages(GenericCheckBase):
    ''' License should always be installed when subpackages.'''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/LicensingGuidelines#Subpackage_Licensing'
        self.text = 'License file installed when any subpackage' \
                    ' combination is installed.'
        self.automatic = False
        self.type = 'MUST'

    def is_applicable(self):
        '''Check if subpackages exists'''
        return len(self.spec.packages) > 1


class CheckLocale(GenericCheckBase):
    '''
    MUST: The spec file MUST handle locales properly.  This is done by
    using the %find_lang macro. Using %{_datadir}/locale/* is strictly
    forbidden.
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Handling_Locale_Files'
        self.text = 'The spec file handles locales properly.'
        self.automatic = False
        self.type = 'MUST'

    def is_applicable(self):
        return self.rpms.has_files('/usr/share/locale/*/LC_MESSAGES/*.mo')


class CheckLicenseUpstream(GenericCheckBase):
    '''
    SHOULD: If the source package does not include license text(s)
    as a separate file from upstream, the packager SHOULD query upstream
    to include it.
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/LicensingGuidelines#License_Text'
        self.text = 'Package does not include license text files' \
                    ' separate from upstream.'
        self.automatic = False
        self.type = 'SHOULD'


class CheckMacros(GenericCheckBase):
    '''
    MUST: Each package must consistently use macros.
    http://fedoraproject.org/wiki/Packaging/Guidelines#macros
    http://fedoraproject.org/wiki/Packaging:RPMMacros
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/' \
                   'wiki/Packaging/Guidelines#macros'
        self.text = 'Package consistently uses macro' \
                    ' is (instead of hard-coded directory names).'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        br_tag1 = self.spec.find_all(re.compile('.*%{buildroot}.*'),
                                     True)
        br_tag2 = self.spec.find_all(re.compile('.*\$RPM_BUILD_ROOT.*'),
                                     True)
        if br_tag1 and br_tag2:
            self.set_passed(False,
                            'Using both %{buildroot} and $RPM_BUILD_ROOT')
        else:
            self.set_passed('inconclusive')


class CheckMakeinstall(GenericCheckBase):
    ''' Thou shall not use %makeinstall. '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines' \
                   '#Why_the_.25makeinstall_macro_should_not_be_used'
        self.text = "Package use %makeinstall only when make install' \
                    ' DESTDIR=... doesn't work."
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


class CheckManPages(GenericCheckBase):
    '''
    SHOULD: your package should contain man pages for binaries or
    scripts.  If it doesn't, work with upstream to add them where they
    make sense.
    http://fedoraproject.org/wiki/Packaging/Guidelines#Man_pages
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Man_pages'
        self.text = 'Man pages included for all executables.'
        self.automatic = False
        self.type = 'SHOULD'

    def is_applicable(self):
        return self.rpms.has_files('[/usr]/[s]bin/*')


class CheckMultipleLicenses(GenericCheckBase):
    ''' If multiple licenses, we should provide a break-down. '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/LicensingGuidelines#Multiple_Licensing_Scenarios'
        self.text = 'If the package is under multiple licenses, the licensing'\
                    ' breakdown must be documented in the spec.'
        self.automatic = False
        self.type = 'MUST'

    def is_applicable(self):
        license_ = self.spec.expand_tag('License').lower().split()
        return 'and' in license_ or 'or' in license_


class CheckNameCharset(GenericCheckBase):
    '''
    MUST:all Fedora packages must be named using only the following
         ASCII characters...
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/NamingGuidelines'
        self.text = 'Package is named using only allowed ASCII characters.'
        self.automatic = True
        self.type = 'MUST'

    def run_on_applicable(self):
        allowed_chars = 'abcdefghijklmnopqrstuvwxyz' \
            'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._+'
        output = ''
        passed = True
        for char in self.spec.name:
            if not char in allowed_chars:
                output += '^'
                passed = False
            else:
                output += ' '
        if passed:
            self.set_passed(passed)
        else:
            self.set_passed(passed, '%s\n%s' % (self.spec.name, output))


class CheckNaming(GenericCheckBase):
    '''
    MUST: The package must be named according to the Package Naming
    Guidelines.
    http://fedoraproject.org/wiki/Packaging/NamingGuidelines
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/NamingGuidelines'
        self.text = 'Package is named according to the Package Naming' \
                    ' Guidelines.'
        self.automatic = False
        self.type = 'MUST'


class CheckNoConfigInUsr(GenericCheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Configuration_files
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Configuration_files'
        self.text = 'No %config files under /usr.'
        self.automatic = False
        self.type = 'MUST'

    def is_applicable(self):
        for pkg in self.spec.packages:
            for line in self.spec.get_files(pkg):
                if line.startswith('%config'):
                    return True
        return False

    def run_on_applicable(self):
        passed = True
        extra = ''
        for pkg in self.spec.packages:
            for line in self.spec.get_files(pkg):
                if line.startswith('%config'):
                    l = line.replace("%config", "")
                    l = l.replace("(noreplace)", "").strip()
                    if l.startswith('/usr'):
                        passed = False
                        extra += line

        self.set_passed(passed, extra)


class CheckNoConflicts(GenericCheckBase):
    '''
    Whenever possible, Fedora packages should avoid conflicting
    with each other
    http://fedoraproject.org/wiki/Packaging/Guidelines#Conflicts
    http://fedoraproject.org/wiki/Packaging:Conflicts
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/' \
                   'wiki/Packaging/Guidelines#Conflicts'
        self.text = 'Package does not generate any conflict.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        if self.spec.expand_tag('Conflicts'):
            self.set_passed(False,
                            'Package contains Conflicts: tag(s)'
                            ' needing fix or justification.')
        else:
            self.set_passed('inconclusive',
                            'Package contains no Conflicts: tag(s)')


class CheckObeysFHS(GenericCheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Filesystem_Layout
    http://www.pathname.com/fhs/
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Filesystem_Layout'
        self.text = 'Package obeys FHS, except libexecdir and /usr/target.'
        self.automatic = False
        self.type = 'MUST'


class CheckObsoletesForRename(GenericCheckBase):
    ''' If package is a rename, we should provide Obsoletes: etc. '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines' \
                   'Renaming.2FReplacing_Existing_Packages'
        self.text = 'If the package is a rename of another package, proper' \
                    ' Obsoletes and Provides are present.'
        self.automatic = False
        self.type = 'MUST'


class CheckOwnDirs(GenericCheckBase):
    '''
    MUST: A package must own all directories that it creates.  If it
    does not create a directory that it uses, then it should require a
    package which does create that directory.
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#FileAndDirectoryOwnership'
        self.text = 'Package must own all directories that it creates.'
        self.automatic = False
        self.type = 'MUST'


class CheckOwnOther(GenericCheckBase):
    '''
    MUST: Packages must not own files or directories already owned by
    other packages.  The rule of thumb here is that the first package
    to be installed should own the files or directories that other
    packages may rely upon.  This means, for example, that no package
    in Fedora should ever share ownership with any of the files or
    directories owned by the filesystem or man package.  If you feel
    that you have a good reason to own a file or directory that
    another package owns, then please present that at package review
    time.
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#FileAndDirectoryOwnership'
        self.text = 'Package does not own files or directories' \
                    ' owned by other packages.'
        self.automatic = False
        self.type = 'MUST'


class CheckParallelMake(GenericCheckBase):
    ''' Thou shall use parallell make. '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Uses parallel make.'
        self.automatic = False
        self.type = 'SHOULD'

    def run(self):
        rc = self.NA
        build_sec = self.spec.get_section('build')
        if build_sec:
            for line in build_sec:
                if line.startswith('make'):
                    ok = '%{?_smp_mflags}' in line
                    rc = self.PASS if ok else self.FAIL
        self.set_passed(rc)


class CheckPatchComments(GenericCheckBase):
    ''' Patches should have comments. '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/' \
                   'Packaging:Guidelines'
        self.text = 'Patches link to upstream bugs/comments/lists' \
                    ' or are otherwise justified.'
        self.automatic = False
        self.type = 'SHOULD'

    def is_applicable(self):
        return len(self.spec.patches_by_tag) > 0


class CheckPkgConfigFiles(GenericCheckBase):
    '''
    SHOULD: The placement of pkgconfig(.pc) files depends on their
    usecase, and this is usually for development purposes, so should
    be placed in a -devel pkg.  A reasonable exception is that the
    main pkg itself is a devel tool not installed in a user runtime,
    e.g. gcc or gdb.
    http://fedoraproject.org/wiki/Packaging/Guidelines#PkgconfigFiles
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#PkgconfigFiles'
        self.text = 'The placement of pkgconfig(.pc) files are correct.'
        self.automatic = True
        self.type = 'SHOULD'

    def run(self):
        files_by_pkg = {}
        for pkg in self.spec.packages:
            file_list = self.rpms.find_all('*.pc', pkg)
            if file_list:
                files_by_pkg[pkg] = file_list
        if files_by_pkg == {}:
            self.set_passed('not_applicable')
            return
        passed = 'pass'
        extra = ''
        for pkg in files_by_pkg.iterkeys():
            for fn in files_by_pkg[pkg]:
                if not '-devel' in pkg:
                    passed = 'pending'
                    extra += '%s : %s\n' % (pkg, fn)
        self.set_passed(passed, extra)


class CheckRelocatable(GenericCheckBase):
    '''
    MUST: If the package is designed to be relocatable,
    the packager must state this fact in the request for review,
    along with the rationalization for relocation of that specific package.
    Without this, use of Prefix: /usr is considered a blocker.
    http://fedoraproject.org/wiki/Packaging/Guidelines#RelocatablePackages
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#RelocatablePackages'
        self.text = 'Package is not relocatable.'
        self.automatic = False
        self.type = 'MUST'


class CheckReqPkgConfig(GenericCheckBase):
    '''
    rpm in EPEL5 and below does not automatically create dependencies
    for pkgconfig files.  Packages containing pkgconfig(.pc) files
    must Requires: pkgconfig (for directory ownership and usability).
    http://fedoraproject.org/wiki/EPEL/GuidelinesAndPolicies#EL5
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'EPEL/GuidelinesAndPolicies#EL5'
        self.text = 'EPEL5: Package requires pkgconfig, if .pc files' \
                    ' are present.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        if not self.rpms.has_files('*.pc') or not self.flags['EPEL5']:
            self.set_passed('not_applicable')
            return
        result = self.FAIL
        for line in self.spec.get_requires():
            if 'pkgconfig' in line:
                result = self.PASS
                break
        self.set_passed(result)


class CheckRequires(GenericCheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Requires
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Requires'
        self.text = 'Requires correct, justified where necessary.'
        self.automatic = False
        self.type = 'MUST'


class CheckScriptletSanity(GenericCheckBase):
    '''
    SHOULD: If scriptlets are used, those scriptlets must be sane.
    This is vague, and left up to the reviewers judgement to determine
    sanity.
    http://fedoraproject.org/wiki/Packaging/Guidelines#Scriptlets
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Scriptlets'
        self.text = 'Scriptlets must be sane, if used.'
        self.automatic = False
        self.type = 'SHOULD'

    def is_applicable(self):
        regex = re.compile('%(post|postun|posttrans|preun|pretrans|pre)\s+')
        return self.spec.find(regex)


class CheckSourceComment(GenericCheckBase):
    ''' Source tarballs shoud have comment on how to generate it. '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging:SourceURL'
        self.text = 'SourceX tarball generation or download is documented.'
        self.automatic = True
        self.type = 'SHOULD'

    def run(self):
        passed = True
        for source in self.sources.get_all():
            if source.local and source.is_archive():
                passed = False

        if passed:
            self.set_passed(True)
        else:
            self.set_passed('inconclusive',
                'Package contains tarball without URL, check comments')


class CheckSourceMD5(GenericCheckBase):
    '''
    MUST: The sources used to build the package must match the
    upstream source, as provided in the spec URL. Reviewers should use
    md5sum for this task.  If no upstream URL can be specified for
    this package, please see the Source URL Guidelines for how to deal
    with this.
    http://fedoraproject.org/wiki/Packaging/SourceURL
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/SourceURL'
        self.text = 'Sources used to build the package match the' \
                    ' upstream source, as provided in the spec URL.'
        self.automatic = True

    def make_diff(self, sources):
        """
        For all sources, run a diff -r between upstream and what's in the
        srpm. Return (passed, text) where passed is True/False
        and text is either the possibly large diff output or None
        """
        for s in sources:
            s.extract()
            upstream = s.extract_dir
            local = self.srpm.extract(s.filename)
            if not local:
                self.log.warn(
                    "Cannot extract local source: " + s.filename)
                return(False, None)
            cmd = '/usr/bin/diff -U2 -r %s %s' % (upstream, local)
            self.log.debug(' Diff cmd: ' + cmd)
            try:
                p = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
                output = p.communicate()[0]
            except OSError:
                self.log.error("Cannot run diff", exc_info=True)
                return (False, None)
            if output and len(output) > 0:
                return (False, output)
        return (True, None)

    def check_checksums(self, sources):
        ''' For all sources, compare checksum with upstream. '''
        text = ''
        all_sources_passed = True
        for source in sources:
            if source.local:
                self.log.debug('Skipping md5-test for '
                                + source.filename)
                continue
            if source.local_src:
                text += "Using local file " + source.local_src + \
                        " as upstream\n"
            local = self.srpm.check_source_checksum(source.filename)
            upstream = source.check_source_checksum()
            text += source.url + ' :\n'
            text += '  CHECKSUM({0}) this package     : {1}\n'.\
                    format(Settings.checksum.upper(), local)
            text += '  CHECKSUM({0}) upstream package : {1}\n'.\
                    format(Settings.checksum.upper(), upstream)
            if local != upstream:
                all_sources_passed = False
        return (all_sources_passed, text)

    def run(self):
        sources = self.sources.get_all()
        if sources == []:
            self.log.debug('No testable sources')
            self.set_passed(self.PENDING, 'Package has no sources or they'
                            ' are generated by developer')
            return
        msg = 'Check did not complete'
        text = ''
        try:
            passed, text = self.check_checksums(self.sources.get_all())
            if not passed:
                passed, diff = self.make_diff(self.sources.get_all())
                if passed:
                    text += 'However, diff -r shows no differences\n'
                    msg = 'checksum differs but diff -r is OK'
                elif not diff:
                    msg += 'checksum differs and there are problems '\
                           'running diff. Please verify manually.\n'
                else:
                    p = os.path.join(ReviewDirs.root, 'diff.txt')
                    with open(p, 'w') as f:
                        f.write(diff)
                    text += 'diff -r also reports differences\n'
                    msg = 'Upstream MD5sum check error, diff is in ' + p
        except AttributeError as e:
            self.log.debug("CheckSourceMD5(): Attribute error " + str(e),
                           exc_info=True)
            msg = 'Internal Error!'
            passed = False
        finally:
            if passed:
                msg = None
            if text:
                attachments = [
                    self.Attachment('MD5-sum check', text, 10)]
            else:
                attachments = []
            self.set_passed(passed, msg, attachments)


class CheckSourcePatchPrefix(GenericCheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/SourceURL
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/SourceURL'
        self.text = 'SourceX / PatchY prefixed with %{name}.'
        self.automatic = True
        self.type = 'SHOULD'

    def run(self):
        sources = self.spec.sources_by_tag
        sources.update(self.spec.patches_by_tag)
        extra = ''
        passed = True
        if len(sources) == 0:
            passed = False
            extra = 'No SourceX/PatchX tags found'
        for tag, path in sources.iteritems():
            basename = os.path.basename(path)
            if not basename.startswith(self.spec.name):
                passed = False
                extra += '%s (%s)\n' % (tag, basename)
        self.set_passed(passed, extra if extra != '' else None)


class CheckSourceUrl(GenericCheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/SourceURL
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/SourceURL'
        self.text = 'SourceX is a working URL.'
        self.automatic = True
        self.type = 'SHOULD'

    def run(self):
        passed = True
        output = ''
        for source in self.sources.get_all():
            if not source.url.startswith('file:'):
                if not source.downloaded:
                    passed = False
                    output += '%s\n' % source.url

        if passed:
            self.set_passed(True)
        else:
            self.set_passed(False, output)


class CheckSpecAsInSRPM(GenericCheckBase):
    '''
    SHOULD: Not in guidelines, buth the spec in the spec URL should
    be the same as the one in the srpm.
    '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.text = 'Spec file according to URL is the same as in SRPM.'
        self.automatic = True
        self.type = 'EXTRA'

    def run(self):
        self.srpm.unpack()
        pattern = os.path.join(ReviewDirs.srpm_unpacked, '*.spec')
        spec_files = glob(pattern)
        if len(spec_files) != 1:
            self.set_passed(self.FAIL,
                            '0 or more than one spec file in srpm(!)')
            return
        srpm_spec_file = spec_files[0]
        pkg_name = \
             os.path.basename(self.srpm.filename).rsplit('-', 2)[0]
        if os.path.basename(srpm_spec_file) != pkg_name + '.spec':
            self.set_passed(self.FAIL,
                            "Bad spec filename: " + srpm_spec_file)
            return
        if Settings.rpm_spec:
            self.set_passed(self.NA)
            return
        url_spec_file = self.spec.filename
        cmd = ["diff", '-U2', url_spec_file, srpm_spec_file]
        try:
            p = Popen(cmd, stdout=PIPE, stderr=PIPE)
            output = p.communicate()[0]
        except OSError:
            self.log.error("Cannot run diff", exc_info=True)
            self.set_passed(self.FAIL, "OS error runnning diff")
            return
        if output and len(output) > 0:
            a = self.Attachment("Diff spec file in url and in SRPM",
                                output,
                                8)
            text = ('Spec file as given by url is not the same as in '
                    'SRPM (see attached diff).')
            self.set_passed(self.FAIL, text, [a])
        else:
            self.set_passed(self.PASS)
        return


class CheckSpecLegibility(GenericCheckBase):
    '''
    MUST: The spec file must be written in American English
    http://fedoraproject.org/wiki/Packaging/Guidelines#summary

    MUST: The spec file for the package MUST be legible.
    http://fedoraproject.org/wiki/Packaging/Guidelines#Spec_Legibility
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Spec_Legibility'
        self.text = 'Spec file is legible and written in American English.'
        self.automatic = False
        self.type = 'MUST'


class CheckSpecName(GenericCheckBase):
    '''
    MUST: The spec file name must match the base package %{name},
    in the format %{name}.spec unless your package has an exemption.
    http://fedoraproject.org/wiki/Packaging/NamingGuidelines#Spec_file_name
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                    'Packaging/NamingGuidelines#Spec_file_name'
        self.text = 'Spec file name must match the spec package' \
                    ' %{name}, in the format %{name}.spec.'
        self.automatic = True

    def run(self):
        spec_name = '%s.spec' % self.spec.name
        if os.path.basename(self.spec.filename) == spec_name:
            self.set_passed(True)
        else:
            self.set_passed(False, '%s should be %s ' %
                (os.path.basename(self.spec.filename), spec_name))


class CheckSpecDescTranslation(GenericCheckBase):
    '''
    SHOULD: The description and summary sections in the package spec file
    should contain translations for supported Non-English languages,
    if available.
    http://fedoraproject.org/wiki/Packaging/Guidelines#summary
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#summary'
        self.text = 'Description and summary sections in the' \
                    ' package spec file contains translations' \
                    ' for supported Non-English languages, if available.'
        self.automatic = False
        self.type = 'SHOULD'


class CheckSupportAllArchs(GenericCheckBase):
    '''
    SHOULD: The package should compile and build into binary rpms on
    all supported architectures.
    http://fedoraproject.org/wiki/Packaging/Guidelines#ArchitectureSupport
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#ArchitectureSupport'
        self.text = 'Package should compile and build into binary' \
                    ' rpms on all supported architectures.'
        self.automatic = True
        self.type = 'SHOULD'

    def run(self):
        build_ok = self.checks.checkdict['CheckBuild'].is_passed

        arch = self.spec.expand_tag('BuildArch')
        noarch = arch and arch[0].lower() == 'noarch'
        one_arch = self.spec.expand_tag('ExclusiveArch')
        if build_ok and (one_arch or noarch):
            self.set_passed(self.PASS)
        else:
            self.set_passed(self.PENDING)


class CheckSystemdScripts(GenericCheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging:Systemd
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package contains  systemd file(s) if in need.'
        self.automatic = False
        self.type = 'MUST'


class CheckTestSuites(GenericCheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Test_Suites
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Test_Suites'
        self.text = '%check is present and all tests pass.'
        self.automatic = False
        self.type = 'SHOULD'


class CheckTimeStamps(GenericCheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Timestamps
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Timestamps'
        self.text = 'Packages should try to preserve timestamps of' \
                    ' original installed files.'
        self.automatic = False
        self.type = 'SHOULD'


class CheckUTF8Filenames(GenericCheckBase):
    '''
    MUST: All filenames in rpm packages must be valid UTF-8.
    http://fedoraproject.org/wiki/Packaging/Guidelines#FilenameEncoding
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#FilenameEncoding'
        self.text = 'File names are valid UTF-8.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        for line in Mock.rpmlint_output:
            if 'wrong-file-end-of-line-encoding' in line or \
            'file-not-utf8' in line:
                self.set_passed(False)
        self.set_passed(True)


class CheckUsefulDebuginfo(GenericCheckBase):
    '''
    Packages should produce useful -debuginfo packages, or explicitly
    disable them when it is not possible to generate a useful one but
    rpmbuild would do it anyway.  Whenever a -debuginfo package is
    explicitly disabled, an explanation why it was done is required in
    the specfile.
    http://fedoraproject.org/wiki/Packaging/Guidelines#Debuginfo_packages
    http://fedoraproject.org/wiki/Packaging:Debuginfo
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Debuginfo_packages'
        self.text = 'Useful -debuginfo package or justification' \
                    ' otherwise.'
        self.automatic = False
        self.type = 'MUST'

    def is_applicable(self):
        for path in Mock.get_package_rpm_paths(self.spec):
            if not path.endswith('noarch.rpm'):
                return True
        return False


class CheckUseGlobal(GenericCheckBase):
    ''' Thou shall not use %define. '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/' \
                   'Guidelines#.25global_preferred_over_.25define'
        self.text = 'Spec use %global instead of %define.'
        self.automatic = True
        self.type = 'SHOULD'

    def run(self):
        regex = re.compile('(\%define.*)')
        result = self.spec.find_all(regex, skip_changelog=True)
        if result:
            extra = ''
            for res in result:
                extra += res + '\n'
            self.set_passed(False, extra)
        else:
            self.set_passed(True)


class CheckNoNameConflict(GenericCheckBase):
    '''
    Check that there isn't already a package with this name.
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = "https://fedoraproject.org/wiki/Packaging/" \
                   "NamingGuidelines#Conflicting_Package_Names"
        self.text = 'Package do not use a name that already exist'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        import fedora.client
        import pycurl
        p = fedora.client.PackageDB()
        name = self.spec.name.lower()
        try:
            p.get_package_info(name)
            self.set_passed(
                     self.FAIL,
                    'A package already exist with this name, please check'
                        ' https://admin.fedoraproject.org/pkgdb/acls/name/'
                        + name)
        except fedora.client.AppError:
            self.set_passed(self.PASS)
        except pycurl.error:
            self.set_passed(self.PENDING,
                            "Couldn't connect to PackageDB, check manually")


class CheckTmpfiles(GenericCheckBase):
    '''
    Check for files in /run, /var/run etc, candidates for tmpfiles.d
    '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Tmpfiles.d'
        self.text = 'Files in /run, var/run and /var/lock uses tmpfiles.d' \
                    ' when appropriate'
        self.automatic = True
        self.type = 'SHOULD'

    def run(self):
        if self.flags['EPEL5']:
            self.set_passed(self.NA)
            return
        for p in ['/run/*', '/var/run/*', '/var/lock/*', '/run/lock/*']:
            if self.rpms.has_files(p):
                self.set_passed(self.PENDING)
                break
        else:
            self.set_passed(self.NA)


class CheckBundledFonts(GenericCheckBase):
    ''' Check for bundled font files '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging:Guidelines' \
                   '#Avoid_bundling_of_fonts_in_other_packages'
        self.text = 'Avoid bundling fonts in non-fonts packages. '
        self.automatic = True
        self.type = 'SHOULD'

    def run(self):
        if self.spec.name.endswith('-fonts'):
            self.set_passed(self.NA)
            return
        for p in ['*.pfb', '*.pfa', '*.afm', '*.ttf', '*.otf']:
            if self.rpms.has_files(p):
                self.set_passed(self.PENDING,
                                'Package contains font files')
                break
        else:
            self.set_passed(self.NA)


class CheckSourcedirMacroUse(GenericCheckBase):
    ''' Check for usage of %_sourcedir macro. '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging:Guidelines' \
                   '#Improper_use_of_.25_sourcedir'
        self.text = 'Only use %_sourcedir in very specific situations.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        text = ''.join(self.spec.lines)
        if '%_sourcedir' in text or '$RPM_SOURCE_DIR' in text or \
        '%{_sourcedir}' in text:
            self.set_passed(self.PENDING,
                            '%_sourcedir/$RPM_SOURCE_DIR is used.')
        else:
            self.set_passed(self.NA)



#
# vim: set expandtab: ts=4:sw=4:
