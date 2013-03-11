#-*- coding: utf-8 -*-
"""Java language specific checks"""

import re
from FedoraReview import CheckBase, RegistryBase


class Registry(RegistryBase):
    ''' Register all checks in this file in group 'Java'. '''

    group = 'Java'

    def is_applicable(self):
        ''' Return True if this is a java package. '''
        rpms = self.checks.rpms
        return rpms.find("*.jar") or rpms.find("*.pom")


class JavaCheckBase(CheckBase):
    """Base check for Java checks"""

    def __init__(self, base):
        CheckBase.__init__(self, base, __file__)

    def _is_maven_pkg(self):
        """Returns True if this is likely Maven package"""
        for build_r in self.spec.build_requires:
            if 'maven-local' in build_r:
                return True
        return False

    def _is_xmvn_pkg(self):
        """Returns True if this package is being built with XMvn (new style
        Maven packaging)"""
        return self.spec.find_re('[^#]*%mvn_build')

    def _get_javadoc_sub(self):
        """Returns name of javadoc rpm or None if no such subpackage
        exists."""
        for pkg in self.spec.packages:
            if pkg.endswith('-javadoc'):
                return pkg
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
        found_trigger = False
        found_pivot = False
        for line in reversed(section):
            if trigger.search(line):
                found_trigger = True

            if found_trigger and pivot.search(line):
                found_pivot = True
                continue

            # we already found mvn command. Any non-empty line now has
            # to be a comment or we fail this test
            if found_pivot and not empty_regex.search(line):
                if judge.search(line):
                    return True
                else:
                    self.set_passed(self.FAIL)
                    return False

        return None


class CheckNotJavaApplicable(JavaCheckBase):
    """Class that disables generic tests that make no sense for java
    packages"""

    deprecates = ['CheckBuildCompilerFlags', 'CheckUsefulDebuginfo',
                  'CheckLargeDocs']

    def is_applicable(self):
        return False


class CheckJavadoc(JavaCheckBase):
    """Check if javadoc subpackage exists and contains documentation"""

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Java' \
                   '#Javadoc_installation'
        self.text = "Javadoc documentation files are generated and " \
                    "included in -javadoc subpackage"
        self.automatic = True

    def run_on_applicable(self):
        """ run check for java packages """
        pkg = self._get_javadoc_sub()
        if not pkg:
            self.set_passed(self.FAIL, "No javadoc subpackage present")
            return

        # and now look for at least one html file
        if self.rpms.find('*.html', pkg):
            self.set_passed(self.PASS)
            return
        self.set_passed(self.FAIL, "No javadoc html files found in %s" % pkg)


class CheckJavadocdirName(JavaCheckBase):
    """Check if deprecated javadoc symlinks are present"""

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Java' \
                   '#Javadoc_installation'
        self.text = "Javadocs are placed in %{_javadocdir}/%{name} " \
                    "(no -%{version} symlink)"
        self.automatic = True

    def run_on_applicable(self):
        pkg = self._get_javadoc_sub()
        if not pkg:
            self.set_passed(self.FAIL, "No javadoc subpackage present")
            return
        name_ver_pattern = "/usr/share/javadoc/%s-%s/*" \
                                       % (self.spec.name, self.spec.version)
        if self.rpms.find_all(name_ver_pattern, pkg):
            self.set_passed(self.FAIL,
                            "Found deprecated versioned javadoc paths " +
                            name_ver_pattern)
            return
        name_pattern = "/usr/share/javadoc/%s/*" % self.spec.name
        if not self.rpms.find_all(name_pattern, pkg):
            self.set_passed(self.FAIL,
                            "No /usr/share/javadoc/%s found" % self.spec.name)
            return
        self.set_passed(self.PASS)


class CheckJPackageRequires(JavaCheckBase):
    """Check if (Build)Requires on jpackage-utils are correct"""

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Java'
        self.text = "Packages have proper BuildRequires/Requires on " \
                    "jpackage-utils"
        self.automatic = True

    def run_on_applicable(self):
        """ run check for java packages """
        brs = self.spec.build_requires
        requires = self.spec.get_requires()
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

        if self._is_maven_pkg():
            extra = "Maven packages do not need to (Build)Require " \
                    "jpackage-utils. It is pulled in by maven-local"
            self.set_passed(not (br_found or r_found), extra)
        else:
            self.set_passed(br_found and r_found)


class CheckJavadocJPackageRequires(JavaCheckBase):
    """Check if javadoc subpackage has requires on jpackage-utils"""

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Java'
        self.text = 'Javadoc subpackages do not have Requires: jpackage-utils'
        self.automatic = True

    def run_on_applicable(self):
        """ run check for java packages """
        pkgs = [pkg for pkg in self.spec.packages
                     if pkg.endswith('-javadoc')]
        if len(pkgs) == 0:
            self.set_passed(self.NA)
        elif len(pkgs) > 1:
            self.set_passed(self.PENDING,
                            'More than one javadoc package')
        else:
            extra = "jpackage-utils requires are automatically generated by " \
                    "the buildsystem"
            ok = 'jpackage-utils' not in self.spec.get_requires(pkgs[0])
            self.set_passed(self.PASS if ok else self.FAIL,
                            extra if not ok else None)


class CheckJavaFullVerReqSub(JavaCheckBase):
    """Check if subpackages have proper Requires on main package
    except javadoc subpackage that doesn't have this requirement"""

    deprecates = ['CheckFullVerReqSub']
    MSG = "Missing: Requires: %{name} = %{version}-%{release} in "

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines' \
                   '#RequiringBasePackage'
        self.text = 'Fully versioned dependency in subpackages, if present.'
        self.automatic = True
        self.type = 'MUST'

    def run_on_applicable(self):
        """ Run check for java packages """
        req = "%s = %s-%s" % tuple(self.spec.name_vers_rel)
        bad_ones = []
        extra = None
        for pkg_name in self.spec.packages:
            if pkg_name.endswith("-javadoc"):
                continue
            if pkg_name == self.spec.base_package:
                continue
            if not req in self.rpms.get(pkg_name).requires:
                bad_ones.append(pkg_name)
        if bad_ones:
            extra = self.MSG + ', '.join(bad_ones)
        self.set_passed(self.FAIL if extra else self.PASS, extra)


class CheckNoOldMavenDepmap(JavaCheckBase):
    """Check if old add_to_maven_depmap macro is being used"""
    group = "Maven"

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Java' \
                   '#add_maven_depmap_macro'
        self.text = 'Old add_to_maven_depmap macro is not being used'
        self.automatic = True
        self.type = 'MUST'
        self.regex = re.compile(r'^\s*%add_to_maven_depmap\s+.*')

    def run_on_applicable(self):
        """ run check for java packages """
        self.set_passed(not self.spec.find_re(self.regex))


class CheckAddMavenDepmap(JavaCheckBase):
    """Check if POM files have correct Maven mapping"""
    group = "Maven"

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Java' \
                   '#add_maven_depmap_macro'
        self.text = 'Pom files have correct Maven mapping'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        if not self.rpms.find("*.pom"):
            self.set_passed(self.NA)
            return
        if self._is_xmvn_pkg():
            self.set_passed(self.PASS)
        elif not self.spec.find_re('[^#]*%add_maven_depmap'):
            self.set_passed(self.FAIL, """Old style Maven package found, no
                            add_maven_depmap calls found but pom files
                            present""")
        else:
            self.set_passed(self.PENDING, """Some add_maven_depmap
                            calls found. Please check if they are correct or
                            update to latest guidelines""")


class CheckUseMavenpomdirMacro(JavaCheckBase):
    """Use proper _mavenpomdir macro instead of old path"""
    group = "Maven"

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Java' \
                   '#add_maven_depmap_macro'
        self.text = 'Packages use %{_mavenpomdir} instead of ' \
                    '%{_datadir}/maven2/poms'
        self.automatic = True
        self.type = 'MUST'
        self.regex = re.compile('%{_datadir}/maven2/poms')

    def run(self):
        if not self.rpms.find("*.pom"):
            self.set_passed(self.NA)
            return
        self.set_passed(not self.spec.find_re(self.regex))


class CheckUpdateDepmap(JavaCheckBase):
    """Check if there is deprecated %update_maven_depmap macro being used"""
    group = "Maven"

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Java' \
                   '#add_maven_depmap_macro'
        self.text = 'Package DOES NOT use %update_maven_depmap in ' \
                    '%post/%postun'
        self.automatic = True
        self.type = 'MUST'
        self.regex = re.compile(r'^\s*%update_maven_depmap\s+.*')

    def run(self):
        if not self.rpms.find("*.pom"):
            self.set_passed(self.NA)
            return
        self.set_passed(not self.spec.find_re(self.regex))


class CheckNoRequiresPost(JavaCheckBase):
    """Check if package still has requires(post/postun) on
    jpackage-utils"""
    group = "Maven"

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Java'
        self.text = "Packages DOES NOT have Requires(post) and " \
                    "Requires(postun) on jpackage-utils for " \
                    "%update_maven_depmap macro"
        self.automatic = True
        self.type = 'MUST'
        self.regex = \
            re.compile(r'^\s*Requires\((post|postun)\):\s*jpackage-utils.*')

    def run(self):

        def _find(what, where):
            ''' True if what is part of the list where. '''
            for item in where:
                if not item:
                    continue
                if what in item:
                    return True
            return False

        if not self.rpms.find("*.pom"):
            self.set_passed(self.NA)
            return
        bad_ones = []
        txt = ''
        for pkg_name in self.spec.packages:
            rpm_pkg = self.rpms.get(pkg_name)
            if _find('jpackage-utils', [rpm_pkg.post, rpm_pkg.postun]):
                bad_ones.append(pkg_name)
        if bad_ones:
            txt = 'jpackage-utils post/postun in ' + ', '.join(bad_ones)
        self.set_passed(self.FAIL if txt else self.PASS, txt)


class CheckTestSkip(JavaCheckBase):
    """Check if -Dmaven.test.skip is being used and look for
    comment"""
    group = "Maven"

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Java'
        self.text = 'If package uses "-Dmaven.test.skip=true" explain' \
                    ' why it was needed in a comment'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        skip_regex = re.compile(r'^\s+-Dmaven.test.skip.*')
        mvn_regex = re.compile(r'^\s*mvn-rpmbuild\s+')
        comment_regex = re.compile(r'^\s*#.*')
        build_sec = self.spec.get_section('%build')

        if not self.spec.find_re(skip_regex) or not build_sec:
            self.set_passed(self.NA)
            return
        result = self._search_previous_line(build_sec,
                                            skip_regex,
                                            mvn_regex,
                                            comment_regex)
        if result == None:
            # weird. It has skip regex but no maven call?
            self.set_passed(self.PASS)
        else:
            self.set_passed(self.PENDING, "Some comment is used "
                               "before mvn-rpmbuild command. Please"
                               " verify it explains use of "
                               "-Dmaven.test.skip")
            self.set_passed(self.FAIL)


class CheckLocalDepmap(JavaCheckBase):
    """Check if -Dmaven.local.depmap is being used and look for
    comment"""
    group = "Maven"

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Java'
        self.text = "If package uses '-Dmaven.local.depmap' explain " \
                    "why it was needed in a comment"
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        depmap_regex = re.compile(r'^\s+-Dmaven.local.depmap.*')
        mvn_regex = re.compile(r'^\s*mvn-rpmbuild\s+')
        comment_regex = re.compile(r'^\s*#.*')
        build_sec = self.spec.get_section('%build')
        if not self.spec.find_re(depmap_regex) or not build_sec:
            self.set_passed(self.NA)
            return
        result = self._search_previous_line(build_sec,
                                            depmap_regex,
                                            mvn_regex,
                                            comment_regex)
        if not result:
            # weird. It has skip regex but no maven call?
            self.set_passed(self.PASS)
        else:
            self.set_passed(self.PENDING, """Some comment is
                used before mvn-rpmbuild command. Please verify
                it explains use of -Dmaven.local.depmap""")


class CheckBundledJars(JavaCheckBase):
    """Check for bundled jar/class files in source tarball"""

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging:Java' \
                   '#Pre-built_JAR_files_.2F_Other_bundled_software'
        self.text = """If source tarball includes bundled jar/class
        files these need to be removed prior to building"""
        self.automatic = False
        self.type = 'MUST'


class JarFilename(JavaCheckBase):
    """Check correct naming of jar files in _javadir"""

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.text = """Jar files are installed to %{_javadir}/%{name}.jar"""
        self.url = 'https://fedoraproject.org/wiki/Packaging:Java' \
                   '#JAR_file_installation'
        self.automatic = False
        self.type = 'MUST'


class CheckPomInstalled(JavaCheckBase):
    """Check if pom.xml files from source tarballs are installed"""
    group = "Maven"

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.text = "If package contains pom.xml files install it " \
                    "(including depmaps) even when building with ant"
        self.url = 'https://fedoraproject.org/wiki/Packaging:Java' \
                   '#Maven_pom.xml_files_and_depmaps'
        self.automatic = False
        self.type = 'MUST'


class CheckUpstremBuildMethod(JavaCheckBase):
    """Verify package uses upstream preferred build method"""

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.text = """Package uses upstream build method (ant/maven/etc.)"""
        self.url = 'https://fedoraproject.org/wiki/Packaging:Java'
        self.automatic = False
        self.type = 'SHOULD'


class CheckNoArch(JavaCheckBase):
    """Package should be noarch in most cases"""

    def __init__(self, base):
        JavaCheckBase.__init__(self, base)
        self.text = """Package has BuildArch: noarch (if possible)"""
        self.url = 'https://fedoraproject.org/wiki/Packaging:Java'
        self.automatic = False
        self.type = 'SHOULD'

# vim: set expandtab: ts=4:sw=4:
