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
        if self.has_files_re(r'.*\.c(?:pp)'):
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
        self.url = gl_fmt_url({'section': 'RubyGems'})
        self.text = 'Gem package must define %{gem_name} macro.'
        self.automatic = True

    def run(self):
        self.set_passed(len(self.find_tag('gem_name')) > 0)


class GemCheckProperName(GemCheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = self.gl_fmt_url({'section': 'Naming_Guidelines'})
        self.text = 'Gem package is named rubygem-%{gem_name}'
        self.automatic = True

    def run(self):
        names = self.spec.find_tag('Name')
        self.set_passed('rubygem-%{gem_name}' in names)

class GemCheckDoesntHaveNonGemSubpackage(GemCheckBase):
    def __init__(self, base):
        CheckBase.__init__(self, base)
        self.url = self.gl_fmt_url({'section': 'Packaging_for_Gem_and_non-Gem_use'})
        self.text = 'Gem package must not define a non-gem subpackage'
        self.automatic = True

    def run(self):
        subpackage_re = re.compile(r'^%package\s+-n\s+ruby-.*')
        self.set_passed(True)

        for line in lines:
            if subpackage_re.match(line):
                self.set_passed(False)
                break
