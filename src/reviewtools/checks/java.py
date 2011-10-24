#-*- coding: utf-8 -*-
"""Java language specific checks"""

import re
from reviewtools.checks.generic import LangCheckBase, CheckFullVerReqSub, \
    CheckBuildCompilerFlags, CheckUsefulDebuginfo, CheckLargeDocs


class JavaCheckBase(LangCheckBase):
    """Base check for Java checks"""
    header="Java"

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
    def _search_previous_line(self, section, trigger, pivot, judge):
        """This function returns True if we find 'judge' regex
        immediately before pivot (empty lines ignored) in section. This only
        applies if we find trigger regex after pivot as well. If no
        trigger is found we return None. Example use on spec like
        this:

        mvn-rpmbuild -Dmaven.test.skip
        with: -Dmaven.test.skip being trigger
              mvn-rpmbuild being pivot
              any comment would be judge
        """
        empty_regex = re.compile(r'^\s*$')
        found_trigger=False
        found_pivot=False
        for line in reversed(section):
            if trigger.search(line):
                found_trigger=True

            if found_trigger and pivot.search(line):
                found_pivot=True
                continue

            # we already found mvn command. Any non-empty line now has
            # to be a comment or we fail this test
            if found_pivot and not empty_regex.search(line):
                if judge.search(line):
                    return True
                else:
                    self.set_passed(False)
                    return False

        return None

    def run(self):
        """ Run the check """
        pass


class CheckNotJavaApplicable(JavaCheckBase):
    """Class that disables generic tests that make no sense for java packages"""
    deprecates = [CheckBuildCompilerFlags, CheckUsefulDebuginfo, CheckLargeDocs]

    def is_applicable(self):
        return False

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
        for html in files[key]:
            if '.html' in html:
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
        requires = self.spec.find_tag('Requires')
        br_found = False
        r_found = False
        for build_r in brs:
            if 'jpackage-utils' in build_r:
                br_found = True

        # this not not 100% correct since we just look for this
        # require anywhere in spec.
        for req in requires:
            if 'jpackage-utils' in req:
                r_found = True
        self.set_passed(br_found and r_found)


class CheckJavadocJPackageRequires(JavaCheckBase):
    """Check if javadoc subpackage has requires on jpackage-utils"""

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Java'
        self.text = 'Javadoc subpackages have Requires: jpackage-utils'
        self.automatic = True


    def run(self):
        brs = self.spec.find_tag('Requires', '%package javadoc')
        self.set_passed('jpackage-utils' in brs)

class CheckJavaFullVerReqSub(JavaCheckBase):
    """Check if subpackages have proper Requires on main package
    except javadoc subpackage that doesn't have this requirement"""

    deprecates = [CheckFullVerReqSub]

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#RequiringBasePackage'
        self.text = 'Fully versioned dependency in subpackages, if present.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        regex = re.compile(r'Requires:\s*%{name}\s*=\s*%{version}-%{release}')
        sections = self.spec.get_section("%package")
        extra = ""
        errors = False
        for section in sections:
            if section == "%package javadoc":
                continue
            passed = False
            for line in sections[section]:
                if regex.search(line):
                    passed = True
            if not passed:
                extra += "Missing : Requires: %%{name} = %%{version}-%%{release} in %s" % section
                errors = False
        if errors:
            self.set_passed(False, extra)
        else:
            self.set_passed(True)

class CheckNoOldMavenDepmap(JavaCheckBase):
    """Check if old add_to_maven_depmap macro is being used"""

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Java#add_maven_depmap_macro'
        self.text = 'Old add_to_maven_depmap macro is not being used'
        self.automatic = True
        self.type = 'MUST'
        self.regex = re.compile(r'^\s*%add_to_maven_depmap\s+.*')

    def run(self):
        self.set_passed(not self.spec.find(self.regex))

class CheckAddMavenDepmap(JavaCheckBase):
    """Check if there is a proper call of add_maven_depmap macro"""

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Java#add_maven_depmap_macro'
        self.text = 'Pom files have correct add_maven_depmap call'
        self.automatic = True
        self.type = 'MUST'
        self.regex = re.compile(r'^\s*%add_maven_depmap\s+.*')

    def is_applicable(self):
        return self.has_files("*.pom")

    def run(self):
        if not self.spec.find(self.regex):
            self.set_passed(False, "No add_maven_depmap calls found but pom files present")
        else:
            self.set_passed("inconclusive", "Some add_maven_depmap"\
                             "calls found. Please check if they are correct")

class CheckUseMavenpomdirMacro(JavaCheckBase):
    """Use proper _mavenpomdir macro instead of old path"""

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Java#add_maven_depmap_macro'
        self.text = 'Packages use %{_mavenpomdir} instead of %{_datadir}/maven2/poms'
        self.automatic = True
        self.type = 'MUST'
        self.regex = re.compile(r'%{_datadir}/maven2/poms')

    def is_applicable(self):
        return self.has_files("*.pom")

    def run(self):
        self.set_passed(not self.spec.find(self.regex))

class CheckUpdateDepmap(JavaCheckBase):
    """Check if there is deprecated %update_maven_depmap macro being used"""

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Java#add_maven_depmap_macro'
        self.text = 'Package DOES NOT use %update_maven_depmap in %post/%postun'
        self.automatic = True
        self.type = 'MUST'
        self.regex = re.compile(r'^\s*%update_maven_depmap\s+.*')

    def is_applicable(self):
        return self.has_files("*.pom")

    def run(self):
        self.set_passed(not self.spec.find(self.regex))

class CheckNoRequiresPost(JavaCheckBase):
    """Check if package still has requires(post/postun) on
    jpackage-utils"""

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Java'
        self.text = 'Packages DOES NOT have Requires(post) and Requires(postun)'\
                    ' on jpackage-utils for %update_maven_depmap macro'
        self.automatic = True
        self.type = 'MUST'
        self.regex = re.compile(r'^\s*Requires\((post|postun)\):\s*jpackage-utils.*')

    def is_applicable(self):
        return self.has_files("*.pom")

    def run(self):
        self.set_passed(not self.spec.find(self.regex))

class CheckTestSkip(JavaCheckBase):
    """Check if -Dmaven.test.skip is being used and look for
    comment"""

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Java'
        self.text = 'If package uses "-Dmaven.test.skip=true" explain why it was needed in a comment'
        self.automatic = True
        self.type = 'MUST'
        self.skip_regex = re.compile(r'^\s+-Dmaven.test.skip.*')
        self.mvn_regex = re.compile(r'^\s*mvn-rpmbuild\s+')
        self.comment_regex = re.compile(r'^\s*#.*')
        self.empty_regex = re.compile(r'^\s*$')
        self.build_sec = self.spec.get_section('%build')['%build']

    def is_applicable(self):
        return self.spec.find(self.skip_regex)

    def run(self):
        result = self._search_previous_line(self.build_sec,
                                            self.skip_regex,
                                            self.mvn_regex,
                                            self.comment_regex)
        if result == None:
            # weird. It has skip regex but no maven call?
            self.set_passed(True)
        else:
            if result:
                self.set_passed("inconclusive", "Some comment is used "
                                    "before mvn-rpmbuild command. Please verify "
                                    "it explains use of -Dmaven.test.skip")
            else:
                self.set_passed(False)

class CheckLocalDepmap(JavaCheckBase):
    """Check if -Dmaven.local.depmap is being used and look for
    comment"""

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Java'
        self.text = 'If package uses "-Dmaven.local.depmap" explain why it was needed in a comment'
        self.automatic = True
        self.type = 'MUST'
        self.depmap_regex = re.compile(r'^\s+-Dmaven.local.depmap.*')
        self.mvn_regex = re.compile(r'^\s*mvn-rpmbuild\s+')
        self.comment_regex = re.compile(r'^\s*#.*')
        self.empty_regex = re.compile(r'^\s*$')
        self.build_sec = self.spec.get_section('%build')['%build']

    def is_applicable(self):
        return self.spec.find(self.depmap_regex)

    def run(self):
        result = self._search_previous_line(self.build_sec,
                                            self.depmap_regex,
                                            self.mvn_regex,
                                            self.comment_regex)
        if result == None:
            # weird. It has skip regex but no maven call?
            self.set_passed(True)
        else:
            if result:
                self.set_passed("inconclusive", "Some comment is used "
                                    "before mvn-rpmbuild command. Please verify "
                                    "it explains use of -Dmaven.local.depmap")
            else:
                self.set_passed(False)
