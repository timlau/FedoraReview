# -*- coding: utf-8 -*-

'''
Ocaml specifics checks, http://fedoraproject.org/wiki/Packaging:Ocaml
'''

from FedoraReview import CheckBase, RegistryBase


class Registry(RegistryBase):
    ''' Register all checks in this file in group 'ocaml' '''

    group = 'Ocaml'

    def is_applicable(self):
        """ Check if the tests are applicable, here it checks whether
        it is a ocaml library or not. Ocaml applications are handled
        as general applications.
        """
        if self.is_user_enabled():
            return self.user_enabled_value()
        return self.checks.spec.name.startswith("ocaml-")


class OcamlCheckBase(CheckBase):
    """ Base class for all Ocaml specific checks. """
    def __init__(self, base):
        CheckBase.__init__(self, base, __file__)


class OcamlCheckStaticLibs(OcamlCheckBase):
    ''' Disable static lib checking, ocaml has an exception. '''

    def __init__(self, checks):
        OcamlCheckBase.__init__(self, checks)
        self.automatic = True
        self.text = 'This should never happen'
        self.deprecates.append('CheckStaticLibs')

    def run_on_applicable(self):
        self.set_passed(self.PASS)
