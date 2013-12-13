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

'''  Generic SHOULD  and EXTRA checks. '''

import os.path
import os
import re

import rpm

from glob import glob
from subprocess import Popen, PIPE

from FedoraReview import CheckBase, Mock, ReviewDirs
from FedoraReview import ReviewError             # pylint: disable=W0611
from FedoraReview import RegistryBase, Settings

from generic import in_list


class Registry(RegistryBase):
    '''
    Module registration, register all checks, supplements MUST module.
    '''

    group = 'Generic.should'

    def is_applicable(self):
        return self.checks.groups['Generic'].is_applicable()


class GenericShouldCheckBase(CheckBase):
    ''' Base class for all generic SHOULD + EXTRA tests. '''

    def __init__(self, checks):
        CheckBase.__init__(self, checks, __file__)


class CheckBuildInMock(GenericShouldCheckBase):
    '''
    SHOULD: The reviewer should test that the package builds in mock.
    http://fedoraproject.org/wiki/PackageMaintainers/MockTricks
    '''
    def __init__(self, base):
        GenericShouldCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'PackageMaintainers/MockTricks'
        self.text = 'Reviewer should test that the package builds in mock.'
        self.automatic = True
        self.type = 'SHOULD'

    def run(self):
        self.set_passed(self.checks.checkdict['CheckBuild'].is_passed)


class CheckBuildroot(GenericShouldCheckBase):
    ''' Is buildroot defined as appropriate? '''

    def __init__(self, base):
        GenericShouldCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#BuildRoot_tag'
        self.text = 'Buildroot is not present'
        if self.flags['EPEL5']:
            self.text = \
                "Explicit BuildRoot: tag as required by EPEL5 present."
        self.automatic = True
        self.type = 'SHOULD'

    def run(self):
        br_tags = self.spec.find_all_re('^BuildRoot')
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


class CheckClean(GenericShouldCheckBase):
    ''' Packags has or has not %clean depending on EPEL5. '''

    def __init__(self, base):
        GenericShouldCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#.25clean'
        self.text = 'Package has no %clean section with rm -rf' \
                    ' %{buildroot} (or $RPM_BUILD_ROOT)'
        self.automatic = True
        self.type = 'SHOULD'

    def run(self):
        has_clean = False
        sec_clean = self.spec.find_re('%clean')
        if sec_clean:
            sec_clean = self.spec.get_section('%clean', raw=True)
            buildroot = rpm.expandMacro('%{buildroot}')
            buildroot = buildroot.replace('+', r'\+')
            regex = r'rm\s+\-[rf][rf]\s+(%{buildroot}|\$RPM_BUILD_ROOT)'
            regex = regex.replace('%{buildroot}', buildroot)
            has_clean = re.search(regex, sec_clean)
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


class CheckDistTag(GenericShouldCheckBase):
    ''' Disttag %{?dist} is present in Release: '''

    def __init__(self, base):
        GenericShouldCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:DistTag'
        self.text = 'Dist tag is present (not strictly required in GL).'
        self.automatic = True
        self.type = 'SHOULD'

    def run(self):
        rel_tags = self.spec.find_all_re(r'^Release\s*:')
        found = in_list('%{?dist}', rel_tags)
        if len(rel_tags) > 1:
            self.set_passed(found, 'Multiple Release: tags found')
        elif len(rel_tags) == 0:
            self.set_passed(found, 'No Release: tags found')
        else:
            self.set_passed(found)


class CheckContainsLicenseText(GenericShouldCheckBase):
    ''' Handle missing license info.  '''

    def __init__(self, base):
        GenericShouldCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/LicensingGuidelines#License_Text'
        self.text = 'If the source package does not include license' \
                    ' text(s) as a separate file from upstream, the' \
                    ' packager SHOULD query upstream to include it.'
        self.automatic = False
        self.type = 'SHOULD'


class CheckFileRequires(GenericShouldCheckBase):
    '''
    If the package has file dependencies outside of /etc,
    /bin, /sbin, /usr/bin, or /usr/sbin consider requiring the package
    which provides the file instead of the file itself.
    '''
    def __init__(self, base):
        GenericShouldCheckBase.__init__(self, base)
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
        attachments = [self.Attachment('Requires', req_txt),
                       self.Attachment('Provides', prov_txt)]
        if len(wrong_req) == 0:
            self.set_passed(self.PASS, None, attachments)
        else:
            text = "Incorrect Requires : %s " % (', '.join(wrong_req))
            self.set_passed(self.FAIL, text, attachments)


class CheckFinalRequiresProvides(GenericShouldCheckBase):
    ''' Final Requires: and Provides: should be sane. '''

    def __init__(self, base):
        GenericShouldCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Final provides and requires are sane' \
                    ' (see attachments).'
        self.automatic = False
        self.type = 'SHOULD'


class CheckFunctionAsDescribed(GenericShouldCheckBase):
    '''
    The reviewer should test that the package functions as described.
    A package should not segfault instead of running, for example.
    '''
    def __init__(self, base):
        GenericShouldCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package functions as described.'
        self.automatic = False
        self.type = 'SHOULD'


class CheckFullVerReqSub(GenericShouldCheckBase):
    ''' Sub-packages requires base package using fully-versioned dep. '''

    HDR = 'No Requires: %{name}%{?_isa} = %{version}-%{release} in '
    REGEX = r'%{name}%{?_isa} = %{version}-%{release}'

    def __init__(self, base):
        GenericShouldCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#RequiringBasePackage'
        self.text = 'Fully versioned dependency in subpackages' \
                    ' if applicable.'
        self.automatic = True
        self.type = 'SHOULD'

    def run(self):
        bad_pkgs = []
        archs = self.checks.spec.expand_tag('BuildArchs')
        if len(self.spec.packages) == 1:
            self.set_passed(self.NA)
            return
        if len(archs) == 1 and archs[0].lower() == 'noarch':
            isa = ''
        else:
            isa = Mock.get_macro('%_isa', self.spec, self.flags)
        regex = self.REGEX.replace('%{?_isa}', isa)
        regex = rpm.expandMacro(regex)
        regex = re.sub('[.](fc|el)[0-9]+', '', regex)
        for pkg in self.spec.packages:
            if pkg == self.spec.base_package:
                continue
            for pkg_end in ['debuginfo', '-javadoc', '-doc']:
                if pkg.endswith(pkg_end):
                    continue
            reqs = ''.join(self.rpms.get(pkg).format_requires)
            if not regex in reqs:
                bad_pkgs.append(pkg)
        if bad_pkgs:
            self.set_passed(self.PENDING,
                            self.HDR + ' , '.join(bad_pkgs))
        else:
            self.set_passed(self.PASS)


class CheckLatestVersionIsPackaged(GenericShouldCheckBase):
    ''' We package latest version, don't we? '''

    def __init__(self, base):
        GenericShouldCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Latest version is packaged.'
        self.automatic = False
        self.type = 'SHOULD'


class CheckLicenseUpstream(GenericShouldCheckBase):
    '''
    If the source package does not include license text(s)
    as a separate file from upstream, the packager SHOULD query upstream
    to include it.
    '''
    def __init__(self, base):
        GenericShouldCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/LicensingGuidelines#License_Text'
        self.text = 'Package does not include license text files' \
                    ' separate from upstream.'
        self.automatic = False
        self.type = 'SHOULD'


class CheckManPages(GenericShouldCheckBase):
    '''
    your package should contain man pages for binaries or
    scripts.  If it doesn't, work with upstream to add them where they
    make sense.
    '''
    def __init__(self, base):
        GenericShouldCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Man_pages'
        self.text = 'Man pages included for all executables.'
        self.automatic = False
        self.type = 'SHOULD'

    def is_applicable(self):
        return self.rpms.find('[/usr]/[s]bin/*')


class CheckParallelMake(GenericShouldCheckBase):
    ''' Thou shall use parallell make. '''

    def __init__(self, base):
        GenericShouldCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Uses parallel make %{?_smp_mflags} macro.'
        self.automatic = False
        self.type = 'SHOULD'

    def run(self):
        rc = self.NA
        build_sec = self.spec.get_section('build')
        if build_sec:
            smp_mflags = rpm.expandMacro('%{?_smp_mflags}')
            for line in build_sec:
                if line.startswith('make'):
                    ok = smp_mflags in line
                    rc = self.PASS if ok else self.FAIL
        self.set_passed(rc)


class CheckPatchComments(GenericShouldCheckBase):
    ''' Patches should have comments. '''

    def __init__(self, base):
        GenericShouldCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/' \
                   'Packaging:Guidelines'
        self.text = 'Patches link to upstream bugs/comments/lists' \
                    ' or are otherwise justified.'
        self.automatic = False
        self.type = 'SHOULD'

    def is_applicable(self):
        return len(self.spec.patches_by_tag) > 0


class CheckPkgConfigFiles(GenericShouldCheckBase):
    '''
    The placement of pkgconfig(.pc) files depends on their
    usecase, and this is usually for development purposes, so should
    be placed in a -devel pkg.  A reasonable exception is that the
    main pkg itself is a devel tool not installed in a user runtime,
    e.g. gcc or gdb.
    '''
    def __init__(self, base):
        GenericShouldCheckBase.__init__(self, base)
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
            self.set_passed(self.NA)
            return
        passed = 'pass'
        extra = ''
        for pkg in files_by_pkg.iterkeys():
            for fn in files_by_pkg[pkg]:
                if not '-devel' in pkg:
                    passed = 'pending'
                    extra += '%s : %s\n' % (pkg, fn)
        self.set_passed(passed, extra)


class CheckScriptletSanity(GenericShouldCheckBase):
    '''
    SHOULD: If scriptlets are used, those scriptlets must be sane.
    This is vague, and left up to the reviewers judgement to determine
    sanity.
    '''
    def __init__(self, base):
        GenericShouldCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Scriptlets'
        self.text = 'Scriptlets must be sane, if used.'
        self.automatic = False
        self.type = 'SHOULD'

    def is_applicable(self):
        regex = re.compile(r'%(post|postun|posttrans|preun|pretrans|pre)\s+')
        return self.spec.find_re(regex)


class CheckSourceComment(GenericShouldCheckBase):
    ''' Source tarballs shoud have comment on how to generate it. '''
    def __init__(self, base):
        GenericShouldCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging:SourceURL'
        self.text = 'SourceX tarball generation or download is documented.'
        self.automatic = True
        self.type = 'SHOULD'

    def run(self):
        passed = True
        for source_tag in self.sources.get_all():
            source = self.sources.get(source_tag)
            if source.local and source.is_archive():
                passed = False

        if passed:
            self.set_passed(self.NA)
        else:
            self.set_passed(self.PENDING,
                'Package contains tarball without URL, check comments')


class CheckSourceUrl(GenericShouldCheckBase):
    ''' SourceX is a working URL. '''

    def __init__(self, base):
        GenericShouldCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/SourceURL'
        self.text = 'SourceX is a working URL.'
        self.type = 'SHOULD'
        self.automatic = True

    def run(self):
        output = ''
        passed = True
        for source_tag in self.sources.get_all():
            source = self.sources.get(source_tag)
            if not source.url.startswith('file:'):
                if not source.downloaded:
                    passed = False
                    output += '%s\n' % source.url

        if passed:
            self.set_passed(self.PASS)
        else:
            self.set_passed(self.FAIL, output)


class CheckSpecAsInSRPM(GenericShouldCheckBase):
    '''
    Not in guidelines, buth the spec in the spec URL should
    be the same as the one in the srpm.
    '''
    def __init__(self, base):
        GenericShouldCheckBase.__init__(self, base)
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
                                output)
            text = ('Spec file as given by url is not the same as in '
                    'SRPM (see attached diff).')
            self.set_passed(self.FAIL, text, [a])
        else:
            self.set_passed(self.PASS)
        return


class CheckSpecDescTranslation(GenericShouldCheckBase):
    '''
    The description and summary sections in the package spec file
    should contain translations for supported Non-English languages,
    if available.
    '''
    def __init__(self, base):
        GenericShouldCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#summary'
        self.text = 'Description and summary sections in the' \
                    ' package spec file contains translations' \
                    ' for supported Non-English languages, if available.'
        self.automatic = False
        self.type = 'SHOULD'


class CheckSupportAllArchs(GenericShouldCheckBase):
    '''
    The package should compile and build into binary rpms on
    all supported architectures.
    '''
    def __init__(self, base):
        GenericShouldCheckBase.__init__(self, base)
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


class CheckTestSuites(GenericShouldCheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Test_Suites
    '''
    def __init__(self, base):
        GenericShouldCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Test_Suites'
        self.text = '%check is present and all tests pass.'
        self.automatic = False
        self.type = 'SHOULD'


class CheckTimeStamps(GenericShouldCheckBase):
    ''' Preserve timestamps if possible. '''

    def __init__(self, base):
        GenericShouldCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Timestamps'
        self.text = 'Packages should try to preserve timestamps of' \
                    ' original installed files.'
        self.automatic = False
        self.type = 'SHOULD'


class CheckUseGlobal(GenericShouldCheckBase):
    ''' Thou shall not use %define. '''

    def __init__(self, base):
        GenericShouldCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/' \
                   'Guidelines#.25global_preferred_over_.25define'
        self.text = 'Spec use %global instead of %define unless' \
                    ' justified.'
        self.automatic = True
        self.type = 'SHOULD'

    def run(self):
        regex = re.compile(r'(\%define.*)')
        result = self.spec.find_all_re(regex, skip_changelog=True)
        if result:
            extra = '%define requiring justification: ' +  \
                    ', '.join(result)
            self.set_passed(self.PENDING, extra)
        else:
            self.set_passed(self.PASS)


class CheckTmpfiles(GenericShouldCheckBase):
    '''
    Check for files in /run, /var/run etc, candidates for tmpfiles.d
    '''
    def __init__(self, base):
        GenericShouldCheckBase.__init__(self, base)
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
            if self.rpms.find(p):
                self.set_passed(self.PENDING)
                break
        else:
            self.set_passed(self.NA)


class CheckBundledFonts(GenericShouldCheckBase):
    ''' Check for bundled font files '''

    def __init__(self, base):
        GenericShouldCheckBase.__init__(self, base)
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
            if self.rpms.find(p):
                self.set_passed(self.PENDING,
                                'Package contains font files')
                break
        else:
            self.set_passed(self.NA)


class CheckUpdateMimeDatabase(GenericShouldCheckBase):
    ''' Check that update-mime-database is run if required. '''

    def __init__(self, base):
        GenericShouldCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging' \
                   ':ScriptletSnippets#mimeinfo'
        self.text = 'update-mime-database is invoked in %post and' \
                    ' %postun if package stores mime configuration' \
                    ' in /usr/share/mime/packages.'

        self.automatic = True
        self.type = 'SHOULD'

    def run(self):
        using = []
        failed = False
        for pkg in self.spec.packages:
            if self.rpms.find('/usr/share/mime/packages/*', pkg):
                using.append(pkg)
                rpm_pkg = self.rpms.get(pkg)
                if not in_list('update-mime-database',
                                [rpm_pkg.postun, rpm_pkg.post]):
                    failed = True
        if not using:
            self.set_passed(self.NA)
            return
        text = "mimeinfo files in: " + ', '.join(using)
        self.set_passed(self.FAIL if failed else self.PENDING, text)



#
# vim: set expandtab ts=4 sw=4:
