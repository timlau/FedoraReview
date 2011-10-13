#-*- coding: utf-8 -*-
import re
from reviewtools.checks.generic import LangCheckBase


class JavaCheckBase(LangCheckBase):
    """Base check for Java checks"""

    def is_applicable(self):
        if self.has_files("*.jar") or self.has_files("*.pom"):
            return True
        else:
            return False

    def _get_javadoc_sub(self):
        """Returns name of javadoc rpm or None if no such subpackage
        exists"""
        rpm_files = self.srpm.get_files_rpms()
        for rpm in rpm_files:
            if '-javadoc' in rpm:
                return rpm
        return None


class CheckJavadoc(JavaCheckBase):
    """Check if javadoc subpackage exists and contains documentation"""

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Java#Javadoc_installation'
        self.text = 'Javadoc documentation files are generated and included in -javadoc subpackage'
        self.automatic = True

    def run(self):
        files = self.get_files_by_pattern("/usr/share/javadoc/%s/*.html" % self.spec.name)
        key = self._get_javadoc_sub()
        if not key:
            self.set_passed(False, "No javadoc subpackage present")

        # and now look for at least one html file
        for f in files[key]:
            if '.html' in f:
                self.set_passed(True)
                return
        self.set_passed(False, "No javadoc html files found in %s" % key)

class CheckJavadocdirName(JavaCheckBase):
    """Check if deprecated javadoc symlinks are present"""

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Java#Javadoc_installation'
        self.text = 'Javadocs are placed in %{_javadocdir}/%{name} (no -%{version} symlink)'
        self.automatic = True

    def run(self):
        name = self.get_files_by_pattern("/usr/share/javadoc/%s" % self.spec.name)
        name_ver = self.get_files_by_pattern("/usr/share/javadoc/%s-%s" %
                                             (self.spec.name, self.spec.version))
        key = self._get_javadoc_sub()
        if not key:
            self.set_passed(False, "No javadoc subpackage present")

        paths = name[key]
        paths_ver = name_ver[key]
        if len(paths_ver) != 0:
            self.set_passed(False, "Found deprecated versioned javadoc path %s" % paths_ver[0])
            return

        if len(paths) != 1:
            self.set_passed(False, "No /usr/share/javadoc/%s found" % self.spec.name )
            return

        self.set_passed(True)

class CheckJPackageRequires(JavaCheckBase):
    """Check if (Build)Requires on jpackage-utils are present"""

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Java'
        self.text = 'Packages have proper BuildRequires/Requires on jpackage-utils'
        self.automatic = True

    def run(self):
        brs = self.spec.find_tag('BuildRequires')
        rs = self.spec.find_tag('Requires')
        br_found = False
        r_found = False
        for br in brs:
            if 'jpackage-utils' in br:
                br_found = True

        # this not not 100% correct since we just look for this
        # require anywhere in spec.
        for req in rs:
            if 'jpackage-utils' in req:
                r_found = True
        self.set_passed(br_found and r_found)


