# -*- coding: utf-8 -*-
''' Checks for ruby and rubygem packages.'''

import re
import rpm

from FedoraReview import CheckBase, RegistryBase

_GUIDELINES_URI = 'http://fedoraproject.org/wiki/Packaging:Ruby'
_GUIDELINES_SECTION_URI = '%(uri)s#%%(section)s' % {'uri': _GUIDELINES_URI}


def _is_nongem(spec):
    """ Return true for pure ruby packages"""
    return spec.name.startswith('ruby-')


def _is_gem(spec):
    """ Return true for rubygem packages"""
    return spec.name.startswith('rubygem-')


def _has_extension(check):
    """ Return True if the package contains native extension """
    # pylint: disable=W0511
    # TODO: will need altering for jruby .jar files
    return check.rpms.find_re(r'.*\.c(?:pp)')


def _gl_uri():
    """ Returns default URL for packaging guidelines """
    return _GUIDELINES_URI


def _gl_fmt_uri(fmt):
    """ Returns formatted subsection of packaging guidelines"""
    return _GUIDELINES_SECTION_URI % fmt


class Registry(RegistryBase):
    ''' Register all checks in this file in group 'Ruby' '''

    group = 'Ruby'

    def is_applicable(self):
        """ Check if the tests are applicable, here it checks whether
        it is either ruby or rubygem package
        """
        if self.is_user_enabled():
            return self.user_enabled_value()
        return _is_gem(self.checks.spec) or _is_nongem(self.checks.spec)


class RubyCheckBase(CheckBase):
    """ Base class for all general Ruby checks. """
    def __init__(self, base):
        CheckBase.__init__(self, base, __file__)


class GemCheckBase(CheckBase):
    """ Base class for all Gem specific checks. """
    def __init__(self, base):
        CheckBase.__init__(self, base, __file__)

    def is_applicable(self):
        """ Return true for rubygem packages"""
        return _is_gem(self.spec)


class NonGemCheckBase(CheckBase):
    """ Base class for all non-Gem specific checks. """
    def __init__(self, base):
        CheckBase.__init__(self, base, __file__)

    def is_applicable(self):
        """ Return true for pure ruby packages"""
        return _is_nongem(self.spec)


class DisableCheckRubyPlugin(RubyCheckBase):
    ''' Disabke the plugin check code in generic_should.  '''
    def __init__(self, base):
        RubyCheckBase.__init__(self, base)
        self.url = 'https:not-used'
        self.text = 'not-used'
        self.automatic = True
        self.type = 'EXTRA'
        self.deprecates = ["CheckRubyPlugin"]

    def run(self):
        self.set_passed(self.NA)


class RubyCheckNotRequiresRubyAbi(RubyCheckBase):
    """ Check if package doesn't require ruby(abi) """
    def __init__(self, base):
        RubyCheckBase.__init__(self, base)
        self.url = _gl_fmt_uri({'section': 'Ruby_Compatibility'})
        self.text = 'Package does not contain Requires: ruby(abi).'
        self.automatic = True

    def run_on_applicable(self):
        br = self.spec.get_requires()
        self.set_passed('ruby(abi)' not in br)


class RubyCheckRequiresRubyRelease(RubyCheckBase):
    """ Check if package requires ruby(release) """
    def __init__(self, base):
        RubyCheckBase.__init__(self, base)
        self.url = _gl_fmt_uri({'section': 'Ruby_Compatibility'})
        self.text = 'Package contains Requires: ruby(release).'
        self.automatic = True

    def run_on_applicable(self):
        br = self.spec.get_requires()
        self.set_passed('ruby(release)' in br)


class RubyCheckBuildArchitecture(RubyCheckBase):
    """ Check if package is noarch """
    def __init__(self, base):
        RubyCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines' \
                   '#Architecture_Support'
        self.text = 'Pure Ruby package must be built as noarch'
        self.automatic = True

    def run_on_applicable(self):
        arch = self.spec.expand_tag('arch')
        if _has_extension(self):
            self.set_passed('noarch' not in arch,
                            "Package with binary extension can't be built"
                            " as noarch.")
        else:
            self.set_passed('noarch' in arch)


class RubyCheckPlatformSpecificFilePlacement(RubyCheckBase):
    """ Check if architecture specific files are placed in correct directories
    """
    def __init__(self, base):
        RubyCheckBase.__init__(self, base)
        self.url = _gl_fmt_uri({'section':
                                'Ruby_packages_with_binary_content.'
                                '2Fshared_libraries'})
        self.text = 'Platform specific files must be located under ' \
                    '/usr/lib[64]'
        self.automatic = True

    def is_applicable(self):
        return super(RubyCheckPlatformSpecificFilePlacement,
                     self).is_applicable() and _has_extension(self)

    def run_on_applicable(self):
        usr_lib_re = re.compile(r'/usr/lib')
        so_file_re = re.compile(r'\.so$')
        rc = self.PASS
        for f in self.checks.rpms.filelist:
            if so_file_re.match(f) and not usr_lib_re.match(f):
                rc = self.FAIL
                break
        self.set_passed(rc)


class RubyCheckTestsRun(RubyCheckBase):
    """ Check if test suite is being run """
    def __init__(self, base):
        RubyCheckBase.__init__(self, base)
        self.url = _gl_fmt_uri({'section': 'Running_test_suites'})
        self.text = 'Test suite of the library should be run.'
        self.automatic = True
        self.type = 'SHOULD'

    def run_on_applicable(self):
        # check_section = self.spec.get_section('%check')
        # Bug in rpm, see
        # http://lists.rpm.org/pipermail/rpm-maint/2013-August/thread.html
        # (or perhaps later) for patch from leamas.
        found = bool(self.spec.find_re('^[^#]*%check'))
        self.set_passed(self.PASS if found else self.FAIL)


class RubyCheckTestsNotRunByRake(RubyCheckBase):
    """ Check and fail if tests are being run by rake """
    def __init__(self, base):
        RubyCheckBase.__init__(self, base)
        self.url = _gl_fmt_uri({'section': 'Running_test_suites'})
        self.text = 'Test suite should not be run by rake.'
        self.automatic = True
        self.type = 'SHOULD'

    def run_on_applicable(self):
        rc = self.PASS
        check_section = self.spec.get_section('%check', raw=True)
        if check_section:
            if 'rake ' in check_section:
                rc = self.FAIL
        else:
            rc = self.NA
        self.set_passed(rc)


class NonGemCheckUsesMacros(NonGemCheckBase):
    """ Check if spec files uses proper macros instead of hardcoding """
    def __init__(self, base):
        NonGemCheckBase.__init__(self, base)
        self.url = _gl_fmt_uri({'section': 'Macros'})
        self.text = 'Specfile should utilize macros from ruby-devel package.'
        self.automatic = True
        self.type = 'SHOULD'

    def run_on_applicable(self):
        ok = False
        vendorarchdir = rpm.expandMacro('%{vendorarchdir}')
        vendorlibdir = rpm.expandMacro('%{vendorlibdir}')
        for pkg in self.spec.packages:
            for line in self.spec.get_files(pkg):
                if _has_extension(self) and vendorarchdir in line:
                    ok = True
                if not _has_extension(self) and vendorlibdir in line:
                    ok = True
        self.set_passed(self.PASS if ok else self.FAIL)


class NonGemCheckFilePlacement(NonGemCheckBase):
    """ Check if files are placed in correct directories"""
    def __init__(self, base):
        NonGemCheckBase.__init__(self, base)
        self.url = _gl_fmt_uri({'section':
                                'Build_Architecture_and_File_Placement'})
        self.text = 'Platform dependent files must go under ' \
            '%{ruby_vendorarchdir}, platform independent under ' \
            '%{ruby_vendorlibdir}.'
        self.automatic = False


class GemCheckFilePlacement(GemCheckBase):
    """ Check if gem files are placed in correct directories """
    def __init__(self, base):
        GemCheckBase.__init__(self, base)
        self.url = _gl_fmt_uri({'section': '.25install'})
        self.text = 'Platform dependent files must all go under ' \
            '%{gem_extdir_mri}, platform independent under %{gem_dir}.'
        self.automatic = False


class GemCheckGemExtdirMacro(GemCheckBase):
    """ Check for deprecated macro %{gem_extdir} """
    def __init__(self, base):
        GemCheckBase.__init__(self, base)
        self.url = _gl_fmt_uri({'section': '.25install'})
        self.text = 'Macro %{gem_extdir} is deprecated.'
        self.automatic = True

    def run_on_applicable(self):
        gem_extdir_macro = self.spec.find_re(r'\%\{gem_extdir\}')
        self.set_passed(self.FAIL if gem_extdir_macro else self.PASS)


class GemCheckRequiresProperDevel(GemCheckBase):
    """ Check that gem packages contain proper BuildRequires """
    def __init__(self, base):
        GemCheckBase.__init__(self, base)
        self.url = _gl_fmt_uri({'section': 'RubyGems'})
        self.text = 'Package contains BuildRequires: rubygems-devel.'
        self.automatic = True

    def run_on_applicable(self):
        """ Run the check """
        br = self.spec.build_requires
        self.set_passed('rubygems-devel' in br)
        if _has_extension(self):
            self.set_passed('ruby-devel' in br,
                            'The Gem package must have BuildRequires: '
                            'ruby-devel if the Gem contains binary extension.')


class NonGemCheckRequiresProperDevel(NonGemCheckBase):
    """ Check that non-gem packages contain proper BuildRequires """
    def __init__(self, base):
        NonGemCheckBase.__init__(self, base)
        self.url = _gl_fmt_uri({'section': 'Non-Gem_Packages'})
        self.text = 'Package contains BuildRequires: ruby-devel.'
        self.automatic = True

    def run_on_applicable(self):
        self.set_passed('ruby-devel' in self.spec.build_requires)


class GemCheckSetsGemName(GemCheckBase):
    """ Check for proper gem_name macro """
    def __init__(self, base):
        GemCheckBase.__init__(self, base)
        self.url = _gl_fmt_uri({'section': 'RubyGems'})
        self.text = 'Gem package must define %{gem_name} macro.'
        self.automatic = True

    def run_on_applicable(self):
        expanded = rpm.expandMacro('%{gem_name}')
        self.set_passed(self.FAIL if '%' in expanded else self.PASS)


class GemCheckProperName(GemCheckBase):
    """ Check for proper naming of package """
    def __init__(self, base):
        GemCheckBase.__init__(self, base)
        self.url = _gl_fmt_uri({'section': 'Naming_Guidelines'})
        self.text = 'Gem package is named rubygem-%{gem_name}'
        self.automatic = True

    def run_on_applicable(self):
        name = self.spec.find_re(r'^Name\s*:')
        self.set_passed('rubygem-%{gem_name}' in name)


class GemCheckDoesntHaveNonGemSubpackage(GemCheckBase):
    """ Check and fail if gem package contains non-gem subpackage """
    def __init__(self, base):
        GemCheckBase.__init__(self, base)
        self.url = _gl_fmt_uri({'section':
                                'Packaging_for_Gem_and_non-Gem_use'})
        self.text = 'Gem package must not define a non-gem subpackage'
        self.automatic = True

    def run_on_applicable(self):
        for pkg in self.spec.packages:
            if '-ruby-' in pkg or pkg.startswith('ruby-'):
                self.set_passed(self.FAIL)
                break
        else:
            self.set_passed(self.PASS)


class GemCheckRequiresRubygems(GemCheckBase):
    """ gems should have Requires: rubygem """
    def __init__(self, base):
        GemCheckBase.__init__(self, base)
        self.url = _gl_fmt_uri({'section': 'RubyGems'})
        self.text = 'gems should require rubygems package'
        self.automatic = True
        self.type = 'MUST'

    def run_on_applicable(self):
        # it seems easier to check whether .gem is not present in rpms
        # than to examine %files
        failed = []
        for pkg_name in self.spec.packages:
            for suffix in ['-doc', '-fonts', '-devel']:
                if pkg_name.endswith(suffix):
                    continue
            rpm_pkg = self.rpms.get(pkg_name)
            if 'rubygems' not in rpm_pkg.requires and \
                    'ruby(rubygems)' not in rpm_pkg.requires:
                failed.append(pkg_name)
        if failed:
            text = 'Requires: rubygems missing in ' + ', '.join(failed)
            self.set_passed(self.FAIL, text)
        else:
            self.set_passed(self.PASS)


class GemCheckGemInstallMacro(GemCheckBase):
    """ gems should use %gem_install macro """
    def __init__(self, base):
        GemCheckBase.__init__(self, base)
        self.url = _gl_fmt_uri({'section': 'Building_gems'})
        self.text = 'Gem should use %gem_install macro.'
        self.automatic = True
        self.type = 'SHOULD'

    def run_on_applicable(self):
        gem_install_re = re.compile(r'^.*gem\s+install', re.I)
        self.set_passed(
            self.FAIL if self.spec.find_re(gem_install_re) else self.PASS)


class GemCheckExcludesGemCache(GemCheckBase):
    """ Check if cached gem is excluded """
    def __init__(self, base):
        GemCheckBase.__init__(self, base)
        self.url = _gl_uri
        self.text = 'Gem package should exclude cached Gem.'
        self.automatic = True
        self.type = 'SHOULD'

    def run_on_applicable(self):
        # it seems easier to check whether .gem is not present in rpms
        # than to examine %files
        self.set_passed(
            self.FAIL if self.rpms.find('*.gem') else self.PASS)


class GemCheckUsesMacros(GemCheckBase):
    """ Check if spec files uses proper macros instead of hardcoding """
    def __init__(self, base):
        GemCheckBase.__init__(self, base)
        self.url = _gl_fmt_uri({'section': 'Macros'})
        self.text = 'Specfile should use macros from rubygem-devel package.'
        self.automatic = True
        self.type = 'SHOULD'

    def run_on_applicable(self):
        gem_libdir_re = re.compile(rpm.expandMacro('%{gem_libdir}'), re.I)
        gem_extdir_re = re.compile(rpm.expandMacro('%{gem_extdir_mri}'), re.I)
        doc_gem_docdir_re = \
            re.compile(rpm.expandMacro(r'%doc\s+%{gem_docdir}'), re.I)
        exclude_gem_cache_re = \
            re.compile(rpm.expandMacro(r'%exclude\s+%{gem_cache}'), re.I)
        gem_spec_re = re.compile(rpm.expandMacro('%{gem_spec}'), re.I)

        re_dict = {gem_libdir_re: False,
                   doc_gem_docdir_re: False,
                   exclude_gem_cache_re: False,
                   gem_spec_re: False}
        if _has_extension(self):
            re_dict[gem_extdir_re] = False

        # mark the present macro regexps with True
        for pkg in self.spec.packages:
            for line in self.spec.get_files(pkg):
                for macro_re in re_dict:
                    if macro_re.match(line):
                        re_dict[macro_re] = True

        err_message = []
        # construct the error message for all non-present macros
        for key, value in re_dict.iteritems():
            if value is False:
                err_message.append(key.pattern.replace('\\s+', ' '))

        if len(err_message) == 0:
            self.set_passed(self.PASS)
        else:
            self.set_passed(self.PENDING,
                            'The specfile doesn\'t use these macros: %s'
                            % ', '.join(err_message))

# vim: set expandtab ts=4 sw=4:
