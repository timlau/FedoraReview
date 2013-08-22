#-*- coding: utf-8 -*-

''' PHP specifics checks, http://fedoraproject.org/wiki/Packaging:PHP '''

from FedoraReview import CheckBase, RegistryBase


class Registry(RegistryBase):
    ''' Register all checks in this file in group 'PHP' '''

    group = 'PHP'

    def is_applicable(self):
        """ Check is the tests are applicable, here it checks whether
        it is a PHP package (spec starts with 'php-') or not.
        """
        if self.is_user_enabled():
            return self.user_enabled_value()
        return self.checks.spec.name.startswith("php-")


class PhpCheckBase(CheckBase):
    """ Base class for all PHP specific checks. """
    def __init__(self, base):
        CheckBase.__init__(self, base, __file__)
