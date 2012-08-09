#-*- coding: UTF-8 -*-

import re
import os
import itertools

from FedoraReview import LangCheckBase, RegistryBase


class Registry(RegistryBase):
    pass


class RubyCheckBase(LangCheckBase):
    """ Base class for all Ruby specific checks. """
    _guidelines_uri = 'http://fedoraproject.org/wiki/Packaging:Ruby'
    _guidelines_section_uri = '%(uri)s#%%(section)s' % {'uri': _guidelines_uri}

    def __init__(self, base):
        LangCheckBase.__init__(self, base, __file__)
        self.group = 'Ruby'
 

    def is_applicable(self):
        return self.is_gem() or self.is_nongem()

    def is_nongem(self):
        return self.spec.name.startswith('ruby-')

    def is_gem(self):
        return self.spec.name.startswith('rubygem-')

    def has_extension(self): # TODO: will need altering for jruby .jar files
        return self.has_files_re(r'.*\.c(?:pp)')

    @property
    def gl_uri(self):
        return self._guidelines_uri

    def gl_fmt_uri(self, fmt):
        return self._guidelines_section_uri % fmt

class GemCheckBase(RubyCheckBase):
    """ Base class for all Gem specific checks. """
    def is_applicable(self):
        return self.is_gem()

class NonGemCheckBase(RubyCheckBase):
    """ Base class for all non-Gem specific checks. """
    def is_applicable(self):
        return self.is_nongem()

class RubyCheckRequiresRubyAbi(RubyCheckBase):
    def __init__(self, base):
        RubyCheckBase.__init__(self, base)
        self.url = self.gl_fmt_uri({'section': 'Ruby_ABI'})
        self.text = 'Package contains Requires: ruby(abi).'
        self.automatic = True

    def run_if_applicable(self):
        """ Run the check """
        br = self.spec.find_tag('Requires')
        self.set_passed('ruby(abi)' in br)

class RubyCheckBuildArchitecture(RubyCheckBase):
    def __init__(self, base):
        RubyCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines#Architecture_Support'
        self.text = 'Pure Ruby package must be built as noarch'
        self.automatic = True

    def run_if_applicable(self):
        arch = self.spec.find_tag('BuildArch')
        if self.has_extension():
            self.set_passed('noarch' not in arch, 'Package with binary extension can\'t be built as noarch.')
        else:
            self.set_passed('noarch' in arch)

class RubyCheckPlatformSpecificFilePlacement(RubyCheckBase):
    def __init__(self, base):
        RubyCheckBase.__init__(self, base)
        self.url = self.gl_fmt_uri({'section': 'Ruby_packages_with_binary_content.2Fshared_libraries'})
        self.text = 'Platform specific files must be located under /usr/lib[64]'
        self.automatic = True

    def is_applicable(self):
        return super(RubyCheckBase, self).is_applicable() and self.has_extension()

    def run_if_applicable(self):
        usr_lib_re = re.compile(r'/usr/lib')
        so_file_re = re.compile(r'\.so$')
        self.set_passed(True)

        for one_rpm in self.srpm.get_files_rpms().values():
            for file in one_rpm:
                if so_file_re.match(file) and not usr_lib_re.match(file):
                    self.set_passed(False)

class RubyCheckTestsRun(RubyCheckBase):
    def __init__(self, base):
        RubyCheckBase.__init__(self, base)
        self.url = self.gl_fmt_uri({'section': 'Running_test_suites'})
        self.text = 'Test suite of the library should be run.'
        self.automatic = True
        self.type = 'SHOULD'

    def run_if_applicable(self):
        check_sections = self.spec.get_section('%check')
        self.set_passed(True)

        if len(check_sections) == 0:
            self.set_passed(False)


class RubyCheckTestsNotRunByRake(RubyCheckTestsRun):
    def __init__(self, base):
        RubyCheckTestsRun.__init__(self, base)
        self.text = 'Test suite should not be run by rake.'

    def run_if_applicable(self):
        self.set_passed(True)
        if self.spec.get_section('%check'):
            for line in self.spec.get_section('%check')['%check']:
                if line.find('rake') != -1:
                    self.set_passed(False)

class NonGemCheckUsesMacros(NonGemCheckBase):
    def __init__(self, base):
        NonGemCheckBase.__init__(self, base)
        self.url = self.gl_fmt_uri({'section': 'Macros'})
        self.text = 'Specfile should utilize macros from ruby-devel package.'
        self.automatic = True
        self.type = 'SHOULD'

    def run_if_applicable(self):
        self.set_passed(False)
        vendorarchdir_re = re.compile('%{vendorarchdir}', re.I)
        vendorlibdir_re = re.compile('%{vendorlibdir}', re.I)

        for line in self.spec.get_section('%files')['%files']:
            if self.has_extension() and vendorarchdir_re.match(line):
                self.set_passed(True)
            if not self.has_extension() and vendorlibdir_re.match(line):
                self.set_passed(True)

class NonGemCheckFilePlacement(NonGemCheckBase):
    def __init__(self, base):
        NonGemCheckBase.__init__(self, base)
        self.url = self.gl_fmt_uri({'section': 'Build_Architecture_and_File_Placement'})
        self.text = 'Platform dependent files must go under %{ruby_vendorarchdir}, platform independent under %{ruby_vendorlibdir}.'
        self.automatic = False

class GemCheckFilePlacement(GemCheckBase):
    def __init__(self, base):
        GemCheckBase.__init__(self, base)
        self.url = self.gl_fmt_uri({'section': '.25install'})
        self.text = 'Platform dependent files must all go under %{gem_extdir}, platform independent under %{gem_dir}.'
        self.automatic = False

class GemCheckRequiresProperDevel(GemCheckBase):
    def __init__(self, base):
        GemCheckBase.__init__(self, base)
        self.url = self.gl_fmt_uri({'section': 'RubyGems'})
        self.text = 'Package contains BuildRequires: rubygems-devel.'
        self.automatic = True

    def run_if_applicable(self):
        """ Run the check """
        br = self.spec.find_tag('BuildRequires')
        self.set_passed('rubygems-devel' in br)
        if self.has_extension():
            self.set_passed('ruby-devel' in br, 'The Gem package must have BuildRequires: ruby-devel, if the Gem contains binary extension.')

class NonGemCheckRequiresProperDevel(NonGemCheckBase):
    def __init__(self, base):
        NonGemCheckBase.__init__(self, base)
        self.url = self.gl_fmt_uri({'section': 'Non-Gem_Packages'})
        self.text = 'Package contains BuildRequires: ruby-devel.'
        self.automatic = True

    def run_if_applicable(self):
        """ Run the check """
        self.set_passed('ruby-devel' in self.spec.find_tag('BuildRequires'))

class GemCheckSetsGemName(GemCheckBase):
    def __init__(self, base):
        GemCheckBase.__init__(self, base)
        self.url = self.gl_fmt_uri({'section': 'RubyGems'})
        self.text = 'Gem package must define %{gem_name} macro.'
        self.automatic = True

    def run_if_applicable(self):
        self.set_passed(len(self.spec.find_tag('gem_name')) > 0)


class GemCheckProperName(GemCheckBase):
    def __init__(self, base):
        GemCheckBase.__init__(self, base)
        self.url = self.gl_fmt_uri({'section': 'Naming_Guidelines'})
        self.text = 'Gem package is named rubygem-%{gem_name}'
        self.automatic = True

    def run_if_applicable(self):
        names = self.spec.find_tag('Name')
        self.set_passed('rubygem-%{gem_name}' in names)

class GemCheckDoesntHaveNonGemSubpackage(GemCheckBase):
    def __init__(self, base):
        GemCheckBase.__init__(self, base)
        self.url = self.gl_fmt_uri({'section': 'Packaging_for_Gem_and_non-Gem_use'})
        self.text = 'Gem package must not define a non-gem subpackage'
        self.automatic = True

    def run_if_applicable(self):
        subpackage_re = re.compile(r'^%package\s+-n\s+ruby-.*')
        self.set_passed(True)

        for line in self.spec.lines:
            if subpackage_re.match(line):
                self.set_passed(False)
                break

class GemCheckExcludesGemCache(GemCheckBase):
    def __init__(self, base):
        GemCheckBase.__init__(self, base)
        self.url = self.gl_uri
        self.text = 'Gem package must exclude cached Gem.'
        self.automatic = True

    def run_if_applicable(self):
        # it seems easier to check whether .gem is not present in rpms than to examine %files
        gemfile_re = re.compile(r'.*\.gem$')
        self.set_passed(True)

        for one_rpm in self.srpm.get_files_rpms().values():
            for file in one_rpm:
                if gemfile_re.match(file):
                    self.set_passed(False)

class GemCheckUsesMacros(GemCheckBase):
    def __init__(self, base):
        GemCheckBase.__init__(self, base)
        self.url = self.gl_fmt_uri({'section': 'Macros'})
        self.text = 'Specfile should utilize macros from rubygem-devel package.'
        self.automatic = True
        self.type = 'SHOULD'

    def run_if_applicable(self):
        gem_libdir_re = re.compile('%{gem_libdir}', re.I)
        gem_extdir_re = re.compile('%{gem_extdir}', re.I)
        doc_gem_docdir_re = re.compile('%doc\s+%{gem_docdir}', re.I)
        exclude_gem_cache_re = re.compile(r'%exclude\s+%{gem_cache}', re.I)
        gem_spec_re = re.compile('%{gem_spec}', re.I)

        re_dict = {gem_libdir_re: False,
                   doc_gem_docdir_re: False,
                   exclude_gem_cache_re: False,
                   gem_spec_re: False}
        if self.has_extension():
            re_dict[gem_extdir_re] = False

        # mark the present macro regexps with True
        files_sections = itertools.chain(*self.spec.get_section('%files').values())
        for line in files_sections:
            for macro_re in re_dict:
                if macro_re.match(line):
                    re_dict[macro_re] = True

        err_message = []
        # construct the error message for all non-present macros
        for key, value in re_dict.iteritems():
            if value == False:
                err_message.append(key.pattern.replace('\\s+', ' '))

        if len(err_message) == 0:
            self.set_passed(True)
        else:
            self.set_passed(False, 'The specfile doesn\'t use these macros: %s' % ', '.join(err_message))

# vim: set expandtab: ts=4:sw=4:
