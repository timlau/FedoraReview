#-*- coding: utf-8 -*-

""" R specifics checks """
# Let's disable the complain about how short R is
# pylint: disable=C0103


import re
import os
import urllib

import rpm

from FedoraReview import CheckBase, RegistryBase


class Registry(RegistryBase):
    ''' Register all check in this file in group 'R' '''

    group = 'R'

    def is_applicable(self):
        """ Check is the tests are applicable, here it checks whether
        it is a R package (spec starts with 'R-') or not.
        """
        if self.is_user_enabled():
            return self.user_enabled_value()
        return self.checks.spec.name.startswith("R-")


class RCheckBase(CheckBase):
    """ Base class for all R specific checks. """
    DIR = ['%{packname}']
    DOCS = ['doc', 'DESCRIPTION', 'NEWS', 'CITATION']
    URLS = [
        'http://www.bioconductor.org/packages/release/data/'
        'experiment/src/contrib/PACKAGES',
        'http://www.bioconductor.org/packages/release/data/'
        'annotation/src/contrib/PACKAGES',
        'http://www.bioconductor.org/packages/release/bioc/'
        'src/contrib/PACKAGES',
        'http://cran.at.r-project.org/src/contrib/PACKAGES',
        'http://r-forge.r-project.org/src/contrib/PACKAGES',
    ]

    def __init__(self, base):
        CheckBase.__init__(self, base, __file__)

    def get_upstream_r_package_version(self):
        """ Browse the PACKAGE file of the different repo to find the
        latest version number of the given package name.
        """
        name = self.spec.name[2:]

        versionok = []
        version = None
        for url in self.URLS:
            try:
                stream = urllib.urlopen(url)
                content = stream.read()
                stream.close()
            except IOError, err:
                self.log.warning('Could not retrieve info from ' + url)
                self.log.debug('Error: %s' % err, exc_info=True)
                continue
            res = re.search('Package: %s\nVersion:.*' % name, content)
            if res is not None:
                self.log.debug("Found in: %s" % url)
                versionok.append(url)
                if version is None:
                    ver = res.group().split('\n')[1]
                    version = ver.replace('Version:', '').strip()
                else:
                    self.log.warning(
                        " * Found two version of the package in %s" % (
                        " ".join(versionok)))
        return version


class RCheckBuildRequires(RCheckBase):
    """ Check if the BuildRequires have the mandatory elements. """

    def __init__(self, base):
        """ Instanciate check variable """
        RCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging:R'
        self.text = 'Package contains the mandatory BuildRequires.'
        self.automatic = True

    def run_on_applicable(self):
        """ Run the check """
        brs = self.spec.build_requires
        tocheck = ['R-devel', 'tex(latex)']
        if set(tocheck).intersection(set(brs)):
            self.set_passed(self.PASS)
        else:
            self.set_passed(self.FAIL, 'Missing BuildRequires on %s' %
                        ', '.join(set(tocheck).difference(set(brs))))


class RCheckRequires(RCheckBase):
    """ Check if the Requires have R-core. """

    def __init__(self, base):
        """ Instanciate check variable """
        RCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging:R'
        self.text = 'Package requires R-core.'
        self.automatic = True

    def run_on_applicable(self):
        """ Run the check """
        brs = self.spec.get_requires()
        if ('R' in brs and not 'R-core' in brs):
            self.set_passed(self.FAIL,
                "Package should requires R-core rather than R")
        else:
            self.set_passed('R-core' in brs)


class RCheckDoc(RCheckBase):
    """ Check if the package has the usual %doc. """

    def __init__(self, base):
        """ Instanciate check variable """
        RCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging:R'
        self.automatic = True
        self.text = 'Package have the default element marked as %%doc :'

    def run_on_applicable(self):
        """ Run the check """
        doc_found = []
        for doc in self.DOCS:
            if self.checks.rpms.find("*" + doc):
                doc_found.append(doc)
        docs = self.spec.find_all_re("%doc.*")
        self.text += ", ".join(doc_found)
        for entry in docs:
            entry = os.path.basename(entry).strip()
            if str(entry) in doc_found:
                doc_found.remove(entry)
        self.set_passed(doc_found == [])


class RCheckLatestVersionIsPackaged(RCheckBase):
    """ Check if the last version of the R package is the one proposed """

    deprecates = ['CheckLatestVersionIsPackaged']

    def __init__(self, base):
        """ Instanciate check variable """
        RCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'Latest version is packaged.'
        self.automatic = True
        self.type = 'SHOULD'

    def run_on_applicable(self):
        """ Run the check """
        cur_version = self.spec.expand_tag('Version')
        up_version = self.get_upstream_r_package_version()
        if up_version is None:
            self.set_passed(self.PENDING,
                'The package does not come from one of the standard sources')
            return
        up_version = up_version.replace('-', '.')

        self.set_passed(up_version == cur_version, "Latest upstream " +
                "version is %s, packaged version is %s" %
                (up_version, cur_version))


class RCheckCheckMacro(RCheckBase):
    """ Check if the section %check is present in the spec """

    def __init__(self, base):
        """ Instantiate check variable """
        RCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Guidelines'
        self.text = 'The %check macro is present'
        self.automatic = True
        self.type = 'SHOULD'

    def run_on_applicable(self):
        """ Run the check """
        sec_check = self.spec.get_section('%check')
        self.set_passed(bool(sec_check))


class RCheckInstallSection(RCheckBase):
    """ Check if the build section follows the expected behavior """

    def __init__(self, base):
        """ Instanciate check variable """
        RCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging:R'
        self.text = 'The package has the standard %install section.'
        self.automatic = True
        self.type = 'MUST'

    def run_on_applicable(self):
        """ Run the check """
        b_dir = False
        b_test = False
        b_rm = False
        b_install = False
        section = self.spec.get_section('%install')
        if not section:
            self.set_passed(self.FAIL)
            return

        for line in section:
            if 'mkdir -p' in line and \
                ('/R/library' in line or 'rlibdir' in line):
                b_dir = True
            if rpm.expandMacro("test -d %{packname}/src && "
            "(cd %{packname}/src; rm -f *.o *.so)") in line:
                b_test = True
            if 'rm' in line and 'R.css' in line:
                b_rm = True
            if 'R CMD INSTALL' in line \
                and '-l ' in line \
                and rpm.expandMacro('%{packname}') in line \
                and ('/R/library' in line or 'rlibdir' in line):
                    b_install = True
        if b_dir and b_test and b_rm and b_install:
            self.set_passed(self.PASS)
        else:
            cmt = ''
            if not b_dir:
                cmt += "Package doesn't have the standard " \
                    "directory creation.\n"
            if not b_test:
                cmt += "Package doesn't have the standard " \
                    "removal of *.o and *.so.\n"
            if not b_rm:
                cmt += "Package doesn't have the standard " \
                    "removal of the R.css file\n"
            if not b_install:
                cmt += "Package doesn't have the standard " \
                    "R CMD INSTALL function\n"
            self.set_passed(self.FAIL, cmt)

# vim: set expandtab ts=4 sw=4:
