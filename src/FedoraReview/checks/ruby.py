#-*- coding: UTF-8 -*-

import re
import os
from generic import LangCheckBase, CheckBase, CheckLatestVersionIsPackaged


class RubyCheckBase(LangCheckBase):
    """ Base class for all Ruby specific checks. """
    def __init__(self):
        self._guidelines_uri = 'http://fedoraproject.org/wiki/Packaging:Ruby'
        self._guidelines_section_uri = '%(uri)#%%(section)' % {'uri': self._guidelines_uri}

    def is_applicable(self):
        return self.is_gem() or self.is_nongem()

    def is_nongem(self):
        return self.spec.name.startswith('ruby-')

    def is_gem(self):
        return self.spec_name.startswith('rubygem-')

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
        CheckBase.__init__(self, base)
        self.url = self.gl_fmt_uri({'section': 'Ruby_ABI'})
        self.text = 'Package contains Requires: ruby(abi).'
        self.automatic = True

    def run(self):
        """ Run the check """
        br = self.spec.find_tag('Requires')
        self.set_passed('ruby(abi)' in br)

class RubyCheckBuildArchitecture(RubyCheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines#Architecture_Support'
        self.text = 'Pure Ruby package must be built as noarch'
        self.automatic = True

    def run(self):
        arch = self.spec.find_tag('BuildArch')
        if self.has_extension():
            self.set_passed('noarch' not in arch, 'Package with binary extension can\'t be built as noarch.')
        else:
            self.set_passed('noarch' in arch)

class RubyPlatformSpecificFilePlacement(RubyCheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = self.gl_fmt_uri({'section': 'Ruby_packages_with_binary_content.2Fshared_libraries'})
        self.text = 'Platform specific files must be located under /usr/lib[64]'
        self.automatic = True

    def run(self.base):
        files = self.srpm.get_files_rpms()
        usr_share_re = re.compile(r'/usr/share/')
        so_file_re = re.compile(r'\.so$')
        set_passed(True)

        for file in files:
            if usr_share_re.match(file) and so_file_re.match(file):
                set_passed(False)

class NonGemCheckFilePlacement(NonGemCheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = self.gl_fmt_uri({'section': 'Build_Architecture_and_File_Placement'})
        self.text = 'Platform dependent files must go under %{ruby_vendorarchdir}, platform independent under %{ruby_vendorlibdir}.'
        self.automatic = False

class GemCheckFilePlacement(GemCheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = self.gl_fmt_uri({'section': '.25install'})
        self.text = 'Platform dependent files must all go under %{gem_extdir}, platform independent under %{gem_dir}.'
        self.automatic = False

class GemCheckRequiresProperDevel(GemCheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = self.gl_fmt_uri({'section': 'RubyGems'})
        self.text = 'Package contains BuildRequires: rubygems-devel.'
        self.automatic = True

    def run(self):
        """ Run the check """
        br = self.spec.find_tag('BuildRequires')
        self.set_passed('rubygems-devel' in br)
        if self.has_extension():
            self.set_passed('ruby-devel' in br, 'The Gem package must have BuildRequires: ruby-devel, if the Gem contains binary extension.')

class NonGemCheckRequiresProperDevel(NonGemCheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = self.gl_fmt_uri({'section': 'Non-Gem_Packages'})
        self.text = 'Package contains BuildRequires: ruby-devel.'
        self.automatic = True

    def run(self):
        """ Run the check """
        self.set_passed('ruby-devel' in self.spec.find_tag('BuildRequires'))

class GemCheckSetsGemName(GemCheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = gl_fmt_uri({'section': 'RubyGems'})
        self.text = 'Gem package must define %{gem_name} macro.'
        self.automatic = True

    def run(self):
        self.set_passed(len(self.find_tag('gem_name')) > 0)


class GemCheckProperName(GemCheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = self.gl_fmt_uri({'section': 'Naming_Guidelines'})
        self.text = 'Gem package is named rubygem-%{gem_name}'
        self.automatic = True

    def run(self):
        names = self.spec.find_tag('Name')
        self.set_passed('rubygem-%{gem_name}' in names)

class GemCheckDoesntHaveNonGemSubpackage(GemCheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = self.gl_fmt_uri({'section': 'Packaging_for_Gem_and_non-Gem_use'})
        self.text = 'Gem package must not define a non-gem subpackage'
        self.automatic = True

    def run(self):
        subpackage_re = re.compile(r'^%package\s+-n\s+ruby-.*')
        self.set_passed(True)

        for line in lines:
            if subpackage_re.match(line):
                self.set_passed(False)
                break

class GemCheckExcludesGemCache(GemCheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = self.gl_uri
        self.text = 'Gem package must exclude cached Gem.'
        self.automatic = True

    def run(self):
        # it seems easier to check whether .gem is not present in rpms than to examine %files
        gemfile_re = re.compile(r'.*\.gem$')
        self.set_passed(True)

        for file in self.srpm.get_files_rpms():
            if gemfile_re.match(file):
                self.set_passed(False)
