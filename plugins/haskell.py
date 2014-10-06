# -*- coding: utf-8 -*-

'''
Haskell specifics checks, http://fedoraproject.org/wiki/Packaging:Haskell
'''

from FedoraReview import CheckBase, RegistryBase


class Registry(RegistryBase):
    ''' Register all checks in this file in group 'Haskell' '''

    group = 'Haskell'

    def is_applicable(self):
        """ Check if the tests are applicable, here it checks whether
        it is a Haskell package or not.
        """
        if self.is_user_enabled():
            return self.user_enabled_value()
        return self.checks.spec.name.startswith("ghc-") or \
            bool(self.checks.spec.find_re('%cabal'))


class HaskellCheckBase(CheckBase):
    """ Base class for all Haskell specific checks. """
    def __init__(self, base):
        CheckBase.__init__(self, base, __file__)


class HaskellCheckStaticLibs(HaskellCheckBase):
    ''' Disable static lib checking, haskell has an exception. '''
    # TBD: checks that libraries provides themselves as -devel.

    def __init__(self, checks):
        HaskellCheckBase.__init__(self, checks)
        self.text = 'This should never happen'
        self.deprecates.append('CheckStaticLibs')
        self.automatic = True

    def run_on_applicable(self):
        self.set_passed(self.NA)
