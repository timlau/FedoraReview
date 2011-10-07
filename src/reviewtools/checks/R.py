#-*- coding: UTF-8 -*-

from generic import LangCheckBase, CheckBase


class RCheckBase(LangCheckBase):
    """ Base class for all R specific checks. """

    def is_applicable(self):
        """ Check is the tests are applicable, here it checks whether
        it is a R package (spec starts with 'R-') or not.
        """
        if self.spec.name.startswith("R-"):
            return True
        else:
            return False

class RCheckBuildRequires(RCheckBase):
    """ Check if the BuildRequires have the mandatory elements. """

    def __init__(self, base):
        """ Instanciate check variable """
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging:R'
        self.text = 'Package contains the mandatory BuildRequires.'
        self.automatic = True

    def run(self):
        """ Run the check """
        br = self.spec.find_tag('BuildRequires')
        self.set_passed('R-devel' in br and 'tex(latex)' in br)

