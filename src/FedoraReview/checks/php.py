#-*- coding: utf-8 -*-

""" PHP specifics checks """

import re
import os
import urllib

from FedoraReview import LangCheckBase, Settings


class PhpCheckBase(LangCheckBase):
    """ Base class for all PHP specific checks. """
    group="PHP"
    DIR = ['%{packname}']
    DOCS = []
    URLS = []
    log = Settings.get_logger()

    def __init__(self, base):
        LangCheckBase.__init__(self, base, __file__)
        self.group = "PHP"

    def is_applicable(self):
        """ Check is the tests are applicable, here it checks whether
        it is a PHP package (spec starts with 'php-') or not.
        """
        if self.spec.name.startswith("php-"):
            return True
        else:
            return False


class PhpCheckPhpRequire(PhpCheckBase):
    """ Check if the php require is correct. """

    def __init__(self, base):
        """ Instanciate check variable """
        PhpCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging:PHP'
        self.text = 'Package requires php-common instead of php.'
        self.automatic = True

    def run_on_applicable(self):
        """ Run the check """
        brs = self.spec.find_tag('Requires')
        if ('php' in brs and not 'php-common' in brs):
            self.set_passed(False,
                "Package should require php-common rather than php.")
        else:
            self.set_passed('php-common' in brs)




