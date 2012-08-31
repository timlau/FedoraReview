#-*- coding: utf-8 -*-

""" PHP specifics checks """

from FedoraReview import LangCheckBase, Settings, RegistryBase


class Registry(RegistryBase):
    group = 'PHP'

    def is_applicable(self):
        """ Check is the tests are applicable, here it checks whether
        it is a PHP package (spec starts with 'php-') or not.
        """
        return self.checks.spec.name.startswith("php-")


class PhpCheckBase(LangCheckBase):
    """ Base class for all PHP specific checks. """
    DIR = ['%{packname}']
    DOCS = []
    URLS = []
    log = Settings.get_logger()

    def __init__(self, base):
        LangCheckBase.__init__(self, base, __file__)


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




