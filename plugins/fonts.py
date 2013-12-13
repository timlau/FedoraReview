#-*- coding: utf-8 -*-

''' fonts specifics checks '''

from FedoraReview import CheckBase, RegistryBase


class Registry(RegistryBase):
    ''' Register all checks in this file in group 'fonts'. '''

    group = 'fonts'

    def is_applicable(self):
        """ Check if these tests are applicable i. e., if this is a fonts
        package.
        """
        if self.is_user_enabled():
            return self.user_enabled_value()
        return self.checks.spec.name.endswith("-fonts")


class FontsCheckBase(CheckBase):
    """ Base class for all fonts specific checks. """
    def __init__(self, base):
        CheckBase.__init__(self, base, __file__)
        self.url = 'https://fedoraproject.org/wiki/Packaging:FontsPolicy'
