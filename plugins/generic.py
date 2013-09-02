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


''' Generic MUST checks, default Generic group. '''

import os
import os.path
import re
import rpm

from glob import glob
from StringIO import StringIO
from subprocess import Popen, PIPE
try:
    from subprocess import check_output          # pylint: disable=E0611
except ImportError:
    from FedoraReview.el_compat import check_output


from FedoraReview import CheckBase, Mock, ReviewDirs
from FedoraReview import ReviewError             # pylint: disable=W0611
from FedoraReview import RegistryBase, Settings

import FedoraReview.deps as deps

_DIR_SORT_KEY = '30'
_LICENSE_SORT_KEY = '20'
_GL_SORT_KEY = '90'


def in_list(what, list_):
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
        disttag = self.Flag('DISTTAG',
                            'Default disttag e. g., "fc21".',
                            __file__)
        batch = self.Flag('BATCH',
                          'Disable all build, install, rpmlint etc. tasks',
                           __file__)
        self.checks.flags.add(epel5)
        self.checks.flags.add(disttag)
        self.checks.flags.add(batch)

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
    '''

    sort_key = _LICENSE_SORT_KEY

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
        self.text = 'Package contains no bundled libraries without' \
                    ' FPC exception.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        pattern = '(.*?/)(3rdparty|thirdparty|libraries|libs|ext|external' \
            '|include|3rd_party|third_party)/.*'
        regex = re.compile(pattern, re.IGNORECASE)
        check_dirs = set()
        for i in self.sources.get_filelist():
            m = regex.match(i)
            if m:
                check_dirs.add(m.group(1) + m.group(2))
        if check_dirs:
            self.set_passed(self.PENDING,
                        'Especially check following dirs for bundled code: '
                        + ', '.join(check_dirs))
        else:
            self.set_passed(self.PENDING)


class CheckBuildCompilerFlags(GenericCheckBase):
    '''Thou shall use %{optflags}. '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Compiler_flags'
        self.text = '%build honors applicable compiler flags or ' \
                    'justifies otherwise.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        archs = self.checks.spec.expand_tag('BuildArchs')
        if len(archs) == 1 and archs[0].lower() == 'noarch':
            self.set_passed(self.NA)
            return
        self.set_passed(self.PENDING)


class CheckBuildRequires(GenericCheckBase):
    '''
    MUST: All build dependencies must be listed in BuildRequires,
    except for any that are listed in the exceptions section of the
    Packaging Guidelines Inclusion of those as BuildRequires is
    optional. Apply common sense.
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

        if self.checks.checkdict['CheckBuild'].is_pending or \
            Settings.prebuilt:
                self.set_passed(self.PENDING, 'Using prebuilt rpms.')
        elif self.checks.checkdict['CheckBuild'].is_passed:
            brequires = self.spec.build_requires
            pkg_by_default = ['bash', 'bzip2', 'coreutils', 'cpio',
                              'diffutils', 'fedora-release', 'findutils',
                              'gawk', 'gcc', 'gcc-c++', 'grep', 'gzip',
                              'info', 'make', 'patch', 'redhat-rpm-config',
                              'rpm-build', 'sed', 'shadow-utils', 'tar',
                              'unzip', 'util-linux-ng', 'which', 'xz']
            intersec = list(set(brequires).intersection(set(pkg_by_default)))
            if intersec:
                self.set_passed(self.FAIL, 'These BR are not needed: %s' % (
                    ' '.join(intersec)))
            else:
                self.set_passed(self.PASS)
        else:
            self.set_passed(self.FAIL,
                            'The package did not build.'
                            ' BR could therefore not be checked or the'
                            ' package failed to build because of'
                            ' missing BR')


class CheckChangelogFormat(GenericCheckBase):
    ''' Changelog in correct format. '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Changelogs'
        self.text = 'Changelog in prescribed format.'
        self.automatic = False
        self.type = 'MUST'


class CheckCodeAndContent(GenericCheckBase):
    ''' MUST: The package must contain code, or permissable content. '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#CodeVsContent'
        self.text = 'Sources contain only permissible' \
                    ' code or content.'
        self.automatic = False
        self.type = 'MUST'


class CheckConfigNoReplace(GenericCheckBase):
    ''' '%config files are marked noreplace or reason justified. '''

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
        bad_lines = []
        extra = None
        for pkg in self.spec.packages:
            for line in self.spec.get_files(pkg):
                if line.startswith('%config'):
                    if not line.startswith('%config(noreplace)'):
                        bad_lines.append(line)
                    else:
                        rc = self.PASS
        if bad_lines:
            extra = "No (noreplace) in " + ' '.join(bad_lines)
            rc = self.PENDING
        self.set_passed(rc, extra)


class CheckCleanBuildroot(GenericCheckBase):
    ''' Check that buildroot is cleaned as appropriate. '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.text = 'Package does not run rm -rf %{buildroot}' \
                    ' (or $RPM_BUILD_ROOT) at the beginning of %install.'
        self.automatic = True

    def run(self):
        has_clean = False
        regex = r'rm\s+\-[rf][rf]\s+(@buildroot@|$RPM_BUILD_ROOT)[^/]'
        buildroot = rpm.expandMacro('%{buildroot}')
        # BZ 908830: handle '+' in package name.
        buildroot = buildroot.replace('+', r'\+')
        regex = regex.replace('@buildroot@', buildroot)
        install_sec = self.spec.get_section('%install', raw=True)
        if not install_sec:
            self.set_passed(self.NA)
            return
        self.log.debug('regex: ' + regex)
        self.log.debug('install_sec: ' + install_sec)
        has_clean = install_sec and re.search(regex, install_sec)
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
    ''' Macros in description etc. should be expandable. '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#Source_RPM_Buildtime_Macros'
        self.text = 'Macros in Summary, %description expandable at' \
                    ' SRPM build time.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        bad_tags = []
        for pkg_name in self.spec.packages:
            if '%' in self.spec.expand_tag('Summary', pkg_name):
                bad_tags.append(pkg_name + ' (summary)')
            if '%' in self.spec.expand_tag('Description', pkg_name):
                bad_tags.append(pkg_name + ' (description)')
        if bad_tags:
            self.set_passed(self.PENDING,
                            'Macros in: ' + ', '.join(bad_tags))
        else:
            self.set_passed(self.PASS)


class CheckDesktopFile(GenericCheckBase):
    '''
    MUST: Packages containing GUI applications must include a
    %{name}.desktop file. If you feel that your packaged GUI
    application does not need a .desktop file, you must put a
    comment in the spec file with your explanation.
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
        have_desktop = self.rpms.find('*.desktop')
        self.set_passed(True if have_desktop else self.PENDING)


class CheckDesktopFileInstall(GenericCheckBase):
    '''
    MUST: Packages containing GUI applications must include a
    %{name}.desktop file, and that file must be properly installed
    with desktop-file-install in the %install section.
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#desktop'
        self.text = 'Package installs a  %{name}.desktop using' \
                    ' desktop-file-install or desktop-file-validate' \
                    ' if there is such a file.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        if not self.rpms.find('*.desktop'):
            self.set_passed(self.NA)
            return
        pattern = r'(desktop-file-install|desktop-file-validate)' \
                    r'.*(desktop|SOURCE|\$\w+)'
        found = self.spec.find_re(re.compile(pattern))
        self.set_passed(self.PASS if found else self.FAIL)


class CheckDevelFilesInDevel(GenericCheckBase):
    ''' MUST: Development files must be in a -devel package '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#DevelPackages'
        self.text = 'Development files must be in a -devel package'
        self.automatic = False
        self.type = 'MUST'


class CheckDirectoryRequire(GenericCheckBase):
    ''' Package should require directories it uses. '''

    sort_key = _DIR_SORT_KEY

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package requires other packages for directories it uses.'
        self.automatic = True
        self.type = 'MUST'

    def run_on_applicable(self):
        '''
        Build raw list of directory paths in pkg, package owning the
        leaf.
        Split list into /part1 /part1/part2 /part1/part2/part3...
        Remove all paths part of filesystem.
        Remove all paths part of package.
        Remaining dirs must have a owner, test one by one (painful).
        '''
        dirs = []
        for path in self.rpms.get_filelist():
            path = path.rsplit('/', 1)[0]  # We own the leaf.
            while path:
                dirs.append(path)
                path = path.rsplit('/', 1)[0]
        dirs = set(dirs)
        filesys_dirs = set(deps.list_paths('filesystem'))
        dirs -= filesys_dirs
        rpm_paths = set(self.rpms.get_filelist())
        dirs -= rpm_paths
        bad_dirs = [d for d in dirs if not deps.list_owners(d)]
        if bad_dirs:
            self.set_passed(self.PENDING,
                            "No known owner of " + ", ".join(bad_dirs))
        else:
            self.set_passed(self.PASS)


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
            self.set_passed(self.PENDING)
            return
        content = stream.read()
        stream.close()
        for line in content.split('\n'):
            if 'File listed twice' in line:
                self.set_passed(self.FAIL, line)
                return
        self.set_passed(self.PASS)


class CheckFilePermissions(GenericCheckBase):
    '''
    MUST: Permissions on files must be set properly.  Executables
    should be set with executable permissions, for example. Every
    %files section must include a %defattr(...) line
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#FilePermissions'
        self.text = 'Permissions on files are set properly.'
        self.automatic = True
        self.type = 'MUST'
        self.needs.append('CheckRpmlint')

    def run(self):
        if self.checks.checkdict['CheckRpmlint'].is_disabled:
            self.set_passed(self.PENDING, 'Rpmlint run disabled')
            return
        for line in Mock.rpmlint_output:
            if 'non-standard-executable-perm' in line:
                self.set_passed(self.FAIL, 'See rpmlint output')
                return
        self.set_passed(self.PASS)


class CheckGuidelines(GenericCheckBase):
    ''' MUST: The package complies to the Packaging Guidelines.  '''

    sort_key = _GL_SORT_KEY

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package complies to the Packaging Guidelines'
        self.automatic = False
        self.type = 'MUST'


class CheckIllegalSpecTags(GenericCheckBase):
    ''' Thou shall not use illegal spec tags. '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging:Guidelines#Tags'
        self.text = 'Packager, Vendor, PreReq, Copyright tags should not be ' \
                    'in spec file'
        self.automatic = True
        self.type = 'SHOULD'

    def run(self):
        passed = True
        output = ''
        for tag in ('Packager', 'Vendor', 'PreReq', 'Copyright'):
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
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#PackageDocumentation'
        self.text = 'Large documentation files are in a -doc' \
                    ' subpackage, if required.'
        self.automatic = False
        self.type = 'MUST'


class CheckLicenseField(GenericCheckBase):
    '''
    MUST: The License field in the package spec file must match the
    actual license.
    '''

    sort_key = _LICENSE_SORT_KEY
    unknown_license = 'Unknown or generated'

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
            for license_ in sorted(files_by_license.iterkeys()):
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
        if globs and len(globs) > 0:
            msg = 'Checking patched sources after %prep for licenses.'
            source_dir = globs[0]
        else:
            msg = 'There is no build directory. Running licensecheck ' \
                  'on vanilla upstream sources.'
            source_dir = ReviewDirs.upstream_unpacked
        return (source_dir, msg)

    def _parse_licenses(self, raw_text):
        ''' Convert licensecheck output to files_by_license dict. '''

        def license_is_valid(_license):
            ''' Test that license from licencecheck is parsed OK. '''
            return not 'UNKNOWN' in _license and \
                not 'GENERATED' in _license

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
                license_ = self.unknown_license
            if not license_ in files_by_license.iterkeys():
                files_by_license[license_] = []
            files_by_license[license_].append(file_)
        return files_by_license

    def run(self):
        try:
            source_dir, msg = self._get_source_dir()
            self.log.debug("Scanning sources in " + source_dir)
            if os.path.exists(source_dir):
                cmd = 'licensecheck -r ' + source_dir
                out = check_output(cmd, shell=True)
                self.log.debug("Got license reply, length: %d" % len(out))
                files_by_license = self._parse_licenses(out)
                filename = os.path.join(ReviewDirs.root,
                                        'licensecheck.txt')
                self._write_license(files_by_license, filename)
            else:
                self.log.error('Source directory %s does not exist!' %
                               source_dir)
            if not files_by_license:
                msg += ' No licenses found.'
                msg += ' Please check the source files for licenses manually.'
            else:
                msg += ' Licenses found: "' \
                       + '", "'.join(files_by_license.iterkeys()) + '".'
                if self.unknown_license in files_by_license:
                    msg += ' %d files have unknown license.' % \
                                len(files_by_license[self.unknown_license])
                msg += ' Detailed output of licensecheck in ' + filename
            self.set_passed(self.PENDING, msg)
        except OSError, e:
            self.log.error('OSError: %s' % str(e))
            msg = ' Programmer error: ' + e.strerror
            self.set_passed(self.PENDING, msg)


class CheckLicensInDoc(GenericCheckBase):
    ''' Package includes license text files. '''

    sort_key = _LICENSE_SORT_KEY

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
            licenses.extend(self.rpms.find_all(pattern))
        licenses = filter(lambda l: not self.rpms.find(l + '/*'),
                          licenses)
        licenses = map(lambda f: f.split('/')[-1], licenses)
        if licenses == []:
            self.set_passed(self.PENDING)
            return

        docs = []
        for pkg in self.spec.packages:
            nvr = self.spec.get_package_nvr(pkg)
            rpm_path = Mock.get_package_rpm_path(nvr)
            cmd = 'rpm -qldp ' + rpm_path
            doclist = check_output(cmd.split())
            docs.extend(doclist.split())
        docs = map(lambda f: f.split('/')[-1], docs)

        for _license in licenses:
            if not _license in docs:
                self.log.debug("Cannot find " + _license +
                               " in doclist")
                self.set_passed(self.FAIL,
                                "Cannot find %s in rpm(s)" % _license)
                return
        self.set_passed(self.PASS)


class CheckLicenseInSubpackages(GenericCheckBase):
    ''' License should always be installed when subpackages.'''

    sort_key = _LICENSE_SORT_KEY

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
        return self.rpms.find('/usr/share/locale/*/LC_MESSAGES/*.mo')


class CheckMacros(GenericCheckBase):
    ''' Each package must consistently use macros.  '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/' \
                   'wiki/Packaging/Guidelines#macros'
        self.text = 'Package consistently uses macros' \
                    ' (instead of hard-coded directory names).'
        self.automatic = False
        self.type = 'MUST'


class CheckBuildrootMacros(GenericCheckBase):
    '''Package must use either %{buildroot} or $RPM_BUILD_ROOT.  '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/' \
                   'wiki/Packaging/Guidelines#macros'
        self.text = 'Package uses either  %{buildroot} or $RPM_BUILD_ROOT'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        br_tag1 = self.spec.find_all_re('.*%{buildroot}.*', True)
        br_tag2 = self.spec.find_all_re(r'.*\$RPM_BUILD_ROOT.*', True)
        if br_tag1 and br_tag2:
            self.set_passed(self.FAIL,
                            'Using both %{buildroot} and $RPM_BUILD_ROOT')
        else:
            self.set_passed(self.PASS)


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

    def run_on_applicable(self):
        install = self.spec.get_section('%install', raw=True)
        if install and '%makeinstall' in install:
            self.set_passed(self.PENDING,
                            '%makeinstall used in %install section')
        else:
            self.set_passed(self.PASS)


class CheckMultipleLicenses(GenericCheckBase):
    ''' If multiple licenses, we should provide a break-down. '''

    sort_key = _LICENSE_SORT_KEY

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
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/NamingGuidelines'
        self.text = 'Package is named according to the Package Naming' \
                    ' Guidelines.'
        self.automatic = False
        self.type = 'MUST'


class CheckNoConfigInUsr(GenericCheckBase):
    ''' No config file under /usr. '''

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
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/' \
                   'wiki/Packaging/Guidelines#Conflicts'
        self.text = 'Package does not generate any conflict.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        text = None
        if self.spec.expand_tag('Conflicts'):
            text = 'Package contains Conflicts: tag(s)' \
                        ' needing fix or justification.'
        self.set_passed(self.PENDING, text)


class CheckObeysFHS(GenericCheckBase):
    ''' Package obeys FHS (besides /usr/libexec and /usr/target). '''

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

    sort_key = _DIR_SORT_KEY

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#FileAndDirectoryOwnership'
        self.text = 'Package must own all directories that it creates.'
        self.automatic = True
        self.type = 'MUST'

    def run_on_applicable(self):
        ''' Test if all directories created by us are owned by us or
        of a dependency. Dependency resolution recurses one level, but
        no more. This is partly to limit the result set, partly a
        a best practise not to trust deep dependency chains for
        package directory ownership.
        '''

        # pylint: disable=R0912
        def resolve(requires):
            '''
            Resolve list of symbols to packages in srpm or by repoquery.
            '''
            pkgs = []
            requires_to_process = list(requires)
            for r in requires:
                if r.startswith('rpmlib'):
                    requires_to_process.remove(r)
                    continue
                for pkg in self.spec.packages:
                    if r in self.rpms.get(pkg).provides:
                        pkgs.append(pkg)
                        requires_to_process.remove(r)
                        break
            if requires_to_process:
                pkgs.extend(deps.resolve(requires_to_process))
                pkgs.extend(deps.list_deps(pkgs))
            return list(set(pkgs))

        def get_deps_paths(pkg_deps):
            ''' Return aggregated  list of files in all pkg_deps. '''
            if not pkg_deps:
                return []
            paths = deps.list_paths(pkg_deps)
            for dep in pkg_deps:
                if dep in self.spec.packages:
                    paths.extend(self.rpms.get_filelist(dep))
            return paths

        bad_dirs = []
        for pkg in self.spec.packages:
            pkg_deps = resolve(self.rpms.get(pkg).requires)
            pkg_deps.append('filesystem')
            pkg_deps_paths = get_deps_paths(pkg_deps)
            rpm_paths = self.rpms.get_filelist(pkg)
            for p in rpm_paths:
                path = p.rsplit('/', 1)[0]  # We own leaf, for sure.
                while path:
                    if not path in rpm_paths:
                        if path in pkg_deps_paths:
                            break
                        else:
                            bad_dirs.append(path)
                    path = path.rsplit('/', 1)[0]
        if bad_dirs:
            bad_dirs = list(set(bad_dirs))
            self.set_passed(self.PENDING,
                            "Directories without known owners: "
                                 + ', '.join(bad_dirs))
        else:
            self.set_passed(self.PASS)


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

    sort_key = _DIR_SORT_KEY

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#FileAndDirectoryOwnership'
        self.text = 'Package does not own files or directories' \
                    ' owned by other packages.'
        self.automatic = True
        self.type = 'MUST'

    def run_on_applicable(self):

        def format_msg(owners_by_dir):
            ''' Message string for PENDING message. '''
            items = []
            for d in owners_by_dir:
                owners = ', '.join(owners_by_dir[d])
                items.append("{0}({1})".format(d, owners))
            return "Dirs in package are owned also by: " + \
                ', '.join(items)

        def skip_rpm(path):
            ' Return True if this rpm  should not be checked. '
            if path.endswith('.src.rpm'):
                return True
            pkg = path.rsplit('-', 2)[0]
            return pkg.endswith('-debuginfo')

        bad_owners_by_dir = {}
        rpm_files = glob(os.path.join(Mock.resultdir, '*.rpm'))
        rpm_files = [r for r in rpm_files if not skip_rpm(r)]
        for rpm_file in rpm_files:
            rpm_dirs = sorted(deps.list_dirs(rpm_file))
            my_dirs = []
            allowed = set(self.spec.packages)
            for rpm_dir in rpm_dirs:
                if [d for d in my_dirs if rpm_dir.startswith(d)]:
                    continue
                owners = set(deps.list_owners(rpm_dir))
                if owners.issubset(allowed):
                    my_dirs.append(rpm_dir)
                    continue
                bad_owners_by_dir[rpm_dir] = owners
        if bad_owners_by_dir:
            self.set_passed(self.PENDING, format_msg(bad_owners_by_dir))
        else:
            self.set_passed(self.PASS)


class CheckRelocatable(GenericCheckBase):
    '''
    MUST: If the package is designed to be relocatable,
    the packager must state this fact in the request for review,
    along with the rationalization for relocation of that specific package.
    Without this, use of Prefix: /usr is considered a blocker.
    '''
    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#RelocatablePackages'
        self.text = 'Package is not relocatable.'
        self.automatic = False
        self.type = 'MUST'

    def run_on_applicable(self):
        if self.spec.find_re('^Prefix:'):
            self.set_passed(self.FAIL, 'Package has a "Prefix:" tag')
        else:
            self.set_passed(self.PASS)


class CheckReqPkgConfig(GenericCheckBase):
    '''
    rpm in EPEL5 and below does not automatically create dependencies
    for pkgconfig files.  Packages containing pkgconfig(.pc) files
    must Requires: pkgconfig (for directory ownership and usability).
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
        if not self.rpms.find('*.pc') or not self.flags['EPEL5']:
            self.set_passed(self.NA)
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


class CheckSourceMD5(GenericCheckBase):
    '''
    MUST: The sources used to build the package must match the
    upstream source, as provided in the spec URL. Reviewers should use
    md5sum for this task.  If no upstream URL can be specified for
    this package, please see the Source URL Guidelines for how to deal
    with this.
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
        passed = True
        text = ''
        try:
            sources = [self.sources.get(s)
                           for s in self.sources.get_all()]
            passed, text = self.check_checksums(sources)
            if not passed:
                passed, diff = self.make_diff(sources)
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
                attachments = [self.Attachment('Source checksums', text)]
            else:
                attachments = []
            self.set_passed(passed, msg, attachments)


class CheckSpecLegibility(GenericCheckBase):
    ''' Spec file legible and written in American English. '''

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
            self.set_passed(self.PASS)
        else:
            self.set_passed(self.FAIL, '%s should be %s ' %
                            (os.path.basename(self.spec.filename), spec_name))


class CheckStaticLibs(GenericCheckBase):
    ''' MUST: Static libraries must be in a -static or -devel package.  '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines' \
                   '#StaticLibraries'
        self.text = 'Static libraries in -static or -devel subpackage, ' \
                     'providing  -devel if present.'
        self.automatic = False
        self.type = 'MUST'

    def is_applicable(self):
        ''' check if this test is applicable '''
        return self.rpms.find('*.a')

    def run_on_applicable(self):
        ''' Run the test, called if is_applicable() is True. '''
        extra = ''
        names = []
        bad_names = []
        no_provides = []
        for pkg in self.spec.packages:
            if self.rpms.find('*.a', pkg):
                names.append(pkg)
                if not (pkg.endswith('-static') or pkg.endswith('-devel')):
                    bad_names.append(pkg)
                rpm_pkg = self.rpms.get(pkg)
                ok = [r for r in rpm_pkg.requires if r.endswith('-static')]
                if not ok:
                    no_provides.append(pkg)
        if names:
            extra = 'Package has .a files: ' + ', '.join(names) + '. '
        if bad_names:
            extra += 'Illegal package name: ' + ', '.join(bad_names)  + '. '
        if no_provides:
            extra += \
                'Does not provide -static: ' + ', '.join(no_provides)  + '.'
        failed = bool(bad_names) or bool(no_provides)
        self.set_passed(self.FAIL if failed else self.PASS, extra)


class CheckSystemdScripts(GenericCheckBase):
    ''' systemd files if applicable. '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Package contains  systemd file(s) if in need.'
        self.automatic = False
        self.type = 'MUST'


class CheckUTF8Filenames(GenericCheckBase):
    ''' All filenames in rpm packages must be valid UTF-8.  '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/' \
                   'Packaging/Guidelines#FilenameEncoding'
        self.text = 'File names are valid UTF-8.'
        self.automatic = True
        self.type = 'MUST'
        self.needs.append('CheckRpmlint')

    def run(self):
        if self.checks.checkdict['CheckRpmlint'].is_disabled:
            self.set_passed(self.PENDING, 'Rpmlint run disabled')
            return
        for line in Mock.rpmlint_output:
            if 'wrong-file-end-of-line-encoding' in line or \
                    'file-not-utf8' in line:
                self.set_passed(self.FAIL)
        self.set_passed(self.PASS)


class CheckUsefulDebuginfo(GenericCheckBase):
    '''
    Packages should produce useful -debuginfo packages, or explicitly
    disable them when it is not possible to generate a useful one but
    rpmbuild would do it anyway.  Whenever a -debuginfo package is
    explicitly disabled, an explanation why it was done is required in
    the specfile.
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


class CheckNoNameConflict(GenericCheckBase):
    ''' Check that there isn't already a package with this name.  '''

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
        name = self.spec.name

        def already_exist(name):
            ''' Check if a package name is already in Fedora '''
            p = fedora.client.PackageDB()
            try:
                p.get_package_info(name)
                return True
            except fedora.client.AppError:
                return False

        try:
            if already_exist(name.lower()) or already_exist(name):
                self.set_passed(
                    self.FAIL,
                    'A package already exist with this name, please check'
                    ' https://admin.fedoraproject.org/pkgdb/acls/name/'
                    + name)
            else:
                self.set_passed(self.PASS)
        except pycurl.error:
            self.set_passed(self.PENDING,
                            "Couldn't connect to PackageDB, check manually")


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


class CheckUpdateIconCache(GenericCheckBase):
    ''' Check that gtk-update-icon-cache is run if required. '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging' \
                   ':ScriptletSnippets#Icon_Cache'
        self.text = 'gtk-update-icon-cache is invoked in %postun' \
                    ' and %posttrans if package contains icons.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        using = []
        failed = False
        for pkg in self.spec.packages:
            if self.rpms.find('/usr/share/icons/*', pkg):
                using.append(pkg)
                rpm_pkg = self.rpms.get(pkg)
                if not in_list('gtk-update-icon-cache',
                               [rpm_pkg.postun, rpm_pkg.posttrans]):
                    failed = True
        if not using:
            self.set_passed(self.NA)
            return
        text = "icons in " + ', '.join(using)
        self.set_passed(self.FAIL if failed else self.PENDING, text)


class CheckUpdateDesktopDatabase(GenericCheckBase):
    ''' Check that update-desktop-database is run if required. '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging' \
                   ':ScriptletSnippets#desktop-database'
        self.text = 'update-desktop-database is invoked in %post and' \
                    ' %postun if package contains desktop file(s)' \
                    ' with a MimeType: entry.'
        self.automatic = True
        self.needs.append('check-large-docs')   # Needed to unpack rpms
        self.type = 'MUST'

    def run(self):

        def has_mimetype(pkg, fname):
            ''' Return True if the file fname contains a MimeType entry. '''
            nvr = self.spec.get_package_nvr(pkg)
            rpm_dirs = glob(os.path.join(ReviewDirs.root,
                                        'rpms-unpacked',
                                        pkg + '-' + nvr.version + '*'))
            path = os.path.join(rpm_dirs[0], fname[1:])
            if os.path.isdir(path):
                return False
            elif not os.path.exists(path):
                self.log.warning("Can't access desktop file: " + path)
                return False
            with open(path) as f:
                for line in f.readlines():
                    if line.strip().lower().startswith('mimetype'):
                        return True
            return False

        using = []
        failed = False
        for pkg in self.spec.packages:
            dt_files = self.rpms.find_all('*.desktop', pkg)
            dt_files = [f for f in dt_files if has_mimetype(pkg, f)]
            if dt_files:
                using.append(pkg)
                rpm_pkg = self.rpms.get(pkg)
                if not in_list('update-desktop-database',
                               [rpm_pkg.post, rpm_pkg.postun]):
                    failed = True
        if not using:
            self.set_passed(self.NA)
            return
        text = "desktop file(s) with MimeType entry in " + ', '.join(using)
        self.set_passed(self.FAIL if failed else self.PENDING, text)


class CheckGioQueryModules(GenericCheckBase):
    ''' Check that gio-querymodules is run if required. '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging' \
                   ':ScriptletSnippets#GIO_modules'
        self.text = 'gio-querymodules is invoked in %postun and %post' \
                    ' if package has /lib/gio/modules/* files'

        self.automatic = True
        self.type = 'MUST'

    def run(self):
        using = []
        failed = False
        libdir = Mock.get_macro('%_libdir', self.spec, self.flags)
        gio_pattern = os.path.join(libdir, 'gio/modules/', '*')
        for pkg in self.spec.packages:
            if self.rpms.find(gio_pattern, pkg):
                using.append(pkg)
                rpmpkg = self.rpms.get(pkg)
                if not in_list('gio-querymodules',
                               [rpmpkg.post, rpmpkg.postun]):
                    failed = True
        if not using:
            self.set_passed(self.NA)
            return
        text = "gio module file(s) in " + ', '.join(using)
        self.set_passed(self.FAIL if failed else self.PENDING, text)


class CheckGtkQueryModules(GenericCheckBase):
    ''' Check that gtk-query-immodules is run if required. '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging' \
                   ':ScriptletSnippets#GTK.2B_modules'
        self.text = 'gtk-query-immodules is invoked when required'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        using = []
        failed = False
        libdir = Mock.get_macro('%_libdir', self.spec, self.flags)
        pattern = os.path.join(libdir, 'gtk-3.0/', '*')
        for pkg in self.spec.packages:
            if self.rpms.find(pattern, pkg):
                using.append(pkg)
                rpmpkg = self.rpms.get(pkg)
                if not in_list('gtk-query-immodules',
                               [rpmpkg.postun, rpmpkg.posttrans]):
                    failed = True
        if not using:
            self.set_passed(self.NA)
            return
        text = "Gtk module file(s) in " + ', '.join(using)
        self.set_passed(self.FAIL if failed else self.PENDING, text)


class CheckGlibCompileSchemas(GenericCheckBase):
    ''' Check that glib-compile-schemas is run if required. '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging' \
                   ':ScriptletSnippets#GSettings_Schema'
        self.text = 'glib-compile-schemas is run in %postun and' \
                    ' %posttrans if package has *.gschema.xml files. '
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        using = []
        failed = False
        for pkg in self.spec.packages:
            if self.rpms.find('*.gschema.xml', pkg):
                using.append(pkg)
                rpm_pkg = self.rpms.get(pkg)
                if not in_list('glib-compile-schemas',
                               [rpm_pkg.postun, rpm_pkg.posttrans]):
                    failed = True
        if not using:
            self.set_passed(self.NA)
            return
        text = 'gschema file(s) in ' + ', '.join(using)
        self.set_passed(self.FAIL if failed else self.PENDING, text)


class CheckGconfSchemaInstall(GenericCheckBase):
    ''' Check that gconf schemas are properly installed. '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging' \
                   ':ScriptletSnippets#GConf'
        self.text = 'GConf schemas are properly installed'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        using = []
        failed = False
        for pkg in self.spec.packages:
            if self.rpms.find('/etc/gconf/schemas/*.schemas', pkg):
                using.append(pkg)
                rpm_pkg = self.rpms.get(pkg)
                if not in_list('%gconf_schema',
                               [rpm_pkg.post, rpm_pkg.pre]):
                    failed = True
        if not using:
            self.set_passed(self.NA)
            return
        text = 'gconf file(s) in ' + ', '.join(using)
        self.set_passed(self.FAIL if failed else self.PENDING, text)


class CheckInfoInstall(GenericCheckBase):
    ''' Check that info files are properly installed. '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging' \
                   ':ScriptletSnippets#Texinfo'
        self.text = 'Texinfo files are installed using install-info' \
                    ' in %post and %preun if package has .info files.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        using = []
        failed = False
        for pkg in self.spec.packages:
            if self.rpms.find('/usr/share/info/*', pkg):
                using.append(pkg)
                rpm_pkg = self.rpms.get(pkg)
                if not in_list('install-info',
                               [rpm_pkg.post, rpm_pkg.preun]):
                    failed = True
        if not using:
            self.set_passed(self.NA)
            return
        text = 'Texinfo .info file(s) in ' + ', '.join(using)
        self.set_passed(self.FAIL if failed else self.PENDING, text)


class CheckSourceDownloads(GenericCheckBase):
    ''' Check that sources could be downloaded from their URI. '''

    def __init__(self, base):
        GenericCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging:Guidelines' \
                   '#Tags'
        self.text = 'Sources can be downloaded from URI in Source: tag'
        self.automatic = True
        self.type = 'SHOULD'

    def run(self):
        sources = [self.sources.get(s) for s in self.sources.get_all()]
        url_src = [s for s in sources if s.is_url]
        if not url_src:
            self.set_passed(self.NA)
            return
        failed_src = [s for s in url_src if s.is_failed]
        if not failed_src:
            self.set_passed(self.PASS)
            return
        self.set_passed(self.FAIL, "Could not download " +
                                   ', '.join([s.tag for s in failed_src]))




#
# vim: set expandtab ts=4 sw=4:
