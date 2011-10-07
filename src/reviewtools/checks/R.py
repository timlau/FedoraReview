#-*- coding: UTF-8 -*-

import re
import os
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


class RCheckRequires(RCheckBase):
    """ Check if the Requires have R-core. """

    def __init__(self, base):
        """ Instanciate check variable """
        CheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging:R'
        self.text = 'Package requires R-core.'
        self.automatic = True

    def run(self):
        """ Run the check """
        br = self.spec.find_tag('BuildRequires')
        if 'R ' in br and not 'R-core':
            self.type= "SHOULD"
            self.text= "Package should requires R-core rather than R"
            self.set_passed(False)
        else:
            self.set_passed('R-core' in br)


class RCheckDoc(RCheckBase):
    """ Check if the package has the usual %doc. """

    def __init__(self, base):
        """ Instanciate check variable """
        CheckBase.__init__(self, base)
        print self.spec.find_tag('packname')
        self.doc = []
        for f in ['doc','DESCRIPTION','NEWS', 'CITATION']:
            if self.has_files("*" + f):
                self.doc.append(f)
        self.url = 'http://fedoraproject.org/wiki/Packaging:R'
        self.text = 'Package have the default element marked as %%doc : %s' % (
        ", ".join(self.doc))
        self.automatic = True

    def run(self):
        """ Run the check """
        br = self.spec.find_all(re.compile("%doc.*"))
        for entry in br:
            entry = os.path.basename(entry.group(0)).strip()
            if str(entry) in self.doc:
                self.doc.remove(entry)
        self.set_passed(self.doc == [])
