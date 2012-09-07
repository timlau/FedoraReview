#-*- coding: utf-8 -*-
<<<<<<< HEAD
''' Checks for perl packages. '''
=======

import re
>>>>>>> b75ec62... First shot on perl module

from FedoraReview import CheckBase, RegistryBase

class Registry(RegistryBase):
<<<<<<< HEAD
    ''' Register all checks in this file in group 'Perl'. '''
=======
>>>>>>> b75ec62... First shot on perl module

    group = 'Perl'

    def is_applicable(self):
        return self.checks.spec.name.startswith("perl-") or \
           self.has_files('*.pm') or self.has_files('*.pl')


class PerlCheckBase(CheckBase):
    """ Base class for all R specific checks. """

    def __init__(self, base):
        CheckBase.__init__(self, base, __file__)


class PerlCheckBuildRequires(PerlCheckBase):
    """ Check if the BuildRequires have the mandatory elements. """

    def __init__(self, checks):
        PerlCheckBase.__init__(self, checks)
        self.url = 'http://fedoraproject.org/wiki/Packaging:Perl'
        self.text = 'Package contains the mandatory BuildRequires' \
                    ' and Reguires:.'
        self.automatic = True

    def run_on_applicable(self):
        """
        Check that we don't have BR:perl-devel and do have the
        Requires: perl_compat thin.
        """

        perl_compat = 'perl(:MODULE_COMPAT_%(eval "`%{__perl}' \
                      ' -V:version`"; echo $version))'
        for br in self.spec.get_build_requires():
            if br.startswith('perl-devel'):
                self.set_passed(self.FAIL,
                                'Explicit dependency on perl-devel'
                                ' is not allowed')
                return
        compat = self.spec.rpm_eval(perl_compat)
        for r in self.spec.get_requires():
            if r == compat:
                break
        else:
            self.set_passed(self.PENDING,
                            'Requires: ' + perl_compat + ' missing?')
            return
        self.set_passed(self.PENDING)
