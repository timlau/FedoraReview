#-*- coding: utf-8 -*-
''' Python package tests '''


from FedoraReview import CheckBase, RegistryBase


class Registry(RegistryBase):
    ''' Register all checks in this file in group 'Python' '''

    group = 'Python'

    def is_applicable(self):
        ''' Return true if this is a python package. '''
        if self.is_user_enabled():
            return self.user_enabled_value()
        return self.checks.spec.name.startswith("python") or \
           self.checks.rpms.find('*.pyc')


class PythonCheckBase(CheckBase):
    """ Base class for all python  checks. """

    def __init__(self, base):
        CheckBase.__init__(self, base, __file__)


class CheckPythonBuildRequires(PythonCheckBase):
    """ Check if the BuildRequires have the mandatory elements. """

    def __init__(self, checks):
        PythonCheckBase.__init__(self, checks)
        self.url = 'http://fedoraproject.org/wiki/Packaging:Python' \
                   '#BuildRequires'
        self.text = 'Package contains BR: python2-devel or python3-devel'
        self.automatic = True

    def run_on_applicable(self):
        br = self.spec.build_requires
        passed = 'python2-devel' in br or 'python3-devel' in br
        self.set_passed(self.PASS if passed else self.FAIL)
