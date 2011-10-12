#-*- coding: utf-8 -*-

import re
import os
import urllib
from generic import LangCheckBase, CheckBase, CheckLatestVersionIsPackaged
from reviewtools import get_logger


class RCheckBase(LangCheckBase):
    """ Base class for all R specific checks. """
    
    doc = ['doc','DESCRIPTION','NEWS', 'CITATION']
    URLS = [
                'http://www.bioconductor.org/packages/release/data/experiment/src/contrib/PACKAGES',
                'http://www.bioconductor.org/packages/release/data/annotation/src/contrib/PACKAGES',
                'http://www.bioconductor.org/packages/release/bioc/src/contrib/PACKAGES',
                'http://cran.at.r-project.org/src/contrib/PACKAGES',
                'http://r-forge.r-project.org/src/contrib/PACKAGES',
                ]
    log = get_logger()

    def is_applicable(self):
        """ Check is the tests are applicable, here it checks whether
        it is a R package (spec starts with 'R-') or not.
        """
        if self.spec.name.startswith("R-"):
            return True
        else:
            return False
    
    def getUpstreamRPackageVersion(self):
        """ Browse the PACKAGE file of the different repo to find the
        latest version number of the given package name.
        """
        name = self.spec.name[2:]

        ok = []
        version = None
        for url in self.URLS:
            f = urllib.urlopen(url)
            s = f.read()
            f.close()
            res = re.search('Package: %s\nVersion:.*' % name, s)
            if res is not None:
                self.log.debug("Found in: %s" % url)
                ok.append(url)
                if version is None:
                    ver = res.group().split('\n')[1]
                    version = ver.replace('Version:','').strip()
                else:
                    " * Found two version of the package in %s" %(" ".join(ok))
        return version


class RCheckBuildRequires(RCheckBase):
    """ Check if the BuildRequires have the mandatory elements. """

    def __init__(self, base):
        """ Instanciate check variable """
        RCheckBase.__init__(self, base)
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
        RCheckBase.__init__(self, base)
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
        RCheckBase.__init__(self, base)
        print self.spec.find_tag('packname')
        self.doc_found = []
        for f in self.doc:
            if self.has_files("*" + f):
                self.doc_found.append(f)
        self.url = 'http://fedoraproject.org/wiki/Packaging:R'
        self.text = 'Package have the default element marked as %%doc : %s' % (
        ", ".join(self.doc_found))
        self.automatic = True

    def run(self):
        """ Run the check """
        br = self.spec.find_all(re.compile("%doc.*"))
        for entry in br:
            entry = os.path.basename(entry.group(0)).strip()
            if str(entry) in self.doc_found:
                self.doc_found.remove(entry)
        self.set_passed(self.doc_found == [])


class RCheckLatestVersionIsPackaged(RCheckBase):

    deprecates = [CheckLatestVersionIsPackaged]

    def __init__(self, base):
        """ Instanciate check variable """
        RCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Latest version is packaged.'
        self.automatic = True
        self.type = 'SHOULD'
    
    def run(self):
        """ Run the check """
        cur_version = self.spec.find_tag('Version')
        up_version = self.getUpstreamRPackageVersion()
        up_version = up_version.replace('-','.')

        self.set_passed(up_version == cur_version, "Latest upstream " +
                "version is %s, packaged version is %s" % 
                (up_version, cur_version))
        
