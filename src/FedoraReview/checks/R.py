#-*- coding: utf-8 -*-

""" R specifics checks """

import re
import os
import urllib
from FedoraReview.checks.generic import LangCheckBase, CheckLatestVersionIsPackaged
from FedoraReview import get_logger


class RCheckBase(LangCheckBase):
    """ Base class for all R specific checks. """
    header="R"
    DIR = ['%{packname}']
    DOCS = ['doc', 'DESCRIPTION', 'NEWS', 'CITATION']
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

    def get_upstream_r_package_version(self):
        """ Browse the PACKAGE file of the different repo to find the
        latest version number of the given package name.
        """
        name = self.spec.name[2:]

        ok = []
        version = None
        for url in self.URLS:
            try:
                stream = urllib.urlopen(url)
                content = stream.read()
                stream.close()
            except IOError, err:
                print 'Could not retrieve info from %s' % url
                self.log.debug('Error: %s' % err)
                continue
            res = re.search('Package: %s\nVersion:.*' % name, content)
            if res is not None:
                self.log.debug("Found in: %s" % url)
                ok.append(url)
                if version is None:
                    ver = res.group().split('\n')[1]
                    version = ver.replace('Version:','').strip()
                else:
                    " * Found two version of the package in %s" % (
                        " ".join(ok))
        return version

    def run(self):
        """ Run the check """
        pass

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
        brs = self.spec.find_tag('BuildRequires')
        tocheck = ['R-devel','tex(latex)']
        if set(tocheck).intersection(set(brs)):
            self.set_passed(True)
        else:
            self.set_passed(False, 'Missing BuildRequires on %s' %
                        ', '.join(set(tocheck).difference(set(brs))))


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
        brs = self.spec.find_tag('Requires')
        if ('R' in brs and not 'R-core' in brs):
            self.set_passed(False,
                "Package should requires R-core rather than R")
        else:
            self.set_passed('R-core' in brs)


class RCheckDoc(RCheckBase):
    """ Check if the package has the usual %doc. """

    def __init__(self, base):
        """ Instanciate check variable """
        RCheckBase.__init__(self, base)
        self.doc_found = []
        for doc in self.DOCS:
            if self.srpm and self.has_files("*" + doc):
                self.doc_found.append(doc)
        self.url = 'http://fedoraproject.org/wiki/Packaging:R'
        self.text = 'Package have the default element marked as %%doc : %s' % (
        ", ".join(self.doc_found))
        self.automatic = True

    def run(self):
        """ Run the check """
        docs = self.spec.find_all(re.compile("%doc.*"))
        for entry in docs:
            entry = os.path.basename(entry.group(0)).strip()
            if str(entry) in self.doc_found:
                self.doc_found.remove(entry)
        self.set_passed(self.doc_found == [])


class RCheckLatestVersionIsPackaged(RCheckBase):
    """ Check if the last version of the R package is the one proposed """

    deprecates = [CheckLatestVersionIsPackaged.__name__]

    def __init__(self, base):
        """ Instanciate check variable """
        RCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Latest version is packaged.'
        self.automatic = True
        self.type = 'SHOULD'

    def run(self):
        """ Run the check """
        cur_version = self.spec.find_tag('Version')[0]
        up_version = self.get_upstream_r_package_version()
        if up_version is None:
            self.set_passed('inconclusive',
                'The package does not come from one of the standard sources')
            return
        up_version = up_version.replace('-','.')

        self.set_passed(up_version == cur_version, "Latest upstream " +
                "version is %s, packaged version is %s" %
                (up_version, cur_version))


class RCheckCheckMacro(RCheckBase):
    """ Check if the section %check is present in the spec """

    def __init__(self, base):
        """ Instanciate check variable """
        RCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'The %check macro is present'
        self.automatic = True
        self.type = 'SHOULD'

    def run(self):
        """ Run the check """
        sec_check = self.spec.get_section('%check')
        self.set_passed(sec_check != None)


class RCheckDir(RCheckBase):
    """ Check if the directory %{packname} is owned by the package """

    def __init__(self, base):
        """ Instanciate check variable """
        RCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'The package owns the created directory.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        """ Run the check """
        dirs = self.spec.find_tag('%dir')
        #print dirs

class RCheckBuildSection(RCheckBase):
    """ Check if the build section follows the expected behavior """

    def __init__(self, base):
        """ Instanciate check variable """
        RCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'The package has the standard %build section.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        """ Run the check """
        b_dir = False
        b_test = False
        b_rm = False
        b_install = False
        for line in self.spec.lines:
            if 'mkdir -p' in line and ('/R/library' in line or 'rlibdir' in line):
                b_dir = True
            if "test -d %{packname}/src && (cd %{packname}/src; rm -f *.o *.so)" in line:
                b_test = True
            if 'rm' in line and 'R.css' in line:
                b_rm = True
            if 'R CMD INSTALL' in line \
                    and '-l ' in line \
                    and '%{packname}' in line \
                    and ('/R/library' in line or 'rlibdir' in line):
                b_install = True
        if b_dir is True and b_test is True and b_rm is True and \
            b_install is True:
            self.set_passed(True)
        else:
            cmt = ''
            if b_dir is False:
                cmt += "Package doesn't have the standard directory creation.\n"
            if b_test is False:
                cmt += "Package doesn't have the standard removal of *.o and *.so.\n"
            if b_rm is False:
                cmt += "Package doesn't have the standard removal of the R.css file\n"
            if b_install is False:
                cmt += "Package doesn't have the standard R CMD INSTALL function\n"
            self.set_passed(False, cmt)
