#-*- coding: utf-8 -*-

from FedoraReview import LangCheckBase

class AdaCheckBase(LangCheckBase):
    header='Ada'

    def is_applicable(self):
        """Need more comprehensive check and return True in valid cases"""
        if self.has_files('*.ads') or \
           self.has_files('*,adb') or \
           self.has_files('*.gpr') or \
           self.sources_have_files('*.adb') or \
           self.sources_have_files('*.gpr') or \
           self.sources_have_files('*.ads') :
           return True
        return False

class CheckLDConfig(AdaCheckBase):
    '''
    MUST: Every binary RPM package (or subpackage) which stores shared library files (not just symlinks)
    in any of the dynamic linker's default paths, must call ldconfig in %post and %postun.
    http://fedoraproject.org/wiki/Packaging/Guidelines#Shared_Libraries
    '''
    def __init__(self, base):
        AdaCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#Shared_Libraries'
        self.text = 'ldconfig called in %post and %postun if required.'
        self.automatic = True
        self.type = 'MUST'

    def is_applicable(self):
        '''
        check if this test is applicable
        '''
        return self.has_files_re('/usr/(lib|lib64)/[\w\-]*\.so\.[0-9]')


    def run(self):
        sources = ['%post','%postun']
        for source in sources:
            passed = False
            sections = self.spec.get_section(source)

            for seckey, section in sections.iteritems():
                if '/sbin/ldconfig' in seckey:
                    passed = True
                elif '/sbin/ldconfig' in section:
                    passed = True
                else:
                    for line in section:
                        if '/sbin/ldconfig' in line:
                            passed = True
                            break
            if not passed:
                self.set_passed(False, '/sbin/ldconfig not called in %s' % source)
                return
        self.set_passed(True)

class CheckHeaderFiles(AdaCheckBase):
    '''
    MUST: Spec files must be in a -devel package
    http://fedoraproject.org/wiki/Packaging/Guidelines#DevelPackages
    '''
    def __init__(self, base):
        AdaCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#DevelPackages'
        self.text = 'Header files in -devel subpackage, if present.'
        self.automatic = True
        self.type = 'MUST'

    def is_applicable(self):
        '''
        check if this test is applicable
        '''
        return self.has_files('*.ads')

    def run(self):
        files = self.get_files_by_pattern('*.ads')
        passed = True
        extra = ""
        for rpm in files:
            for fn in files[rpm]:
                # header files (.h) under /usr/src/debug/* will be in the -debuginfo package.
                if  fn.startswith('/usr/src/debug/') and '-debuginfo' in rpm:
                    continue
                # All other .h files should be in a -devel package.
                if not '-devel' in rpm:
                    passed = False
                    extra += "%s : %s\n" % (rpm, fn)
        self.set_passed(passed, extra)



class CheckStaticLibs(AdaCheckBase):
    '''
    MUST: Static libraries must be in a -static package.
    http://fedoraproject.org/wiki/Packaging/Guidelines#StaticLibraries
    '''
    def __init__(self, base):
        AdaCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#StaticLibraries'
        self.text = 'Static libraries in -static subpackage, if present.'
        self.automatic = False
        self.type = 'MUST'

    def is_applicable(self):
        '''
        check if this test is applicable
        '''
        return self.has_files('*.a')

    def run(self):
        files = self.get_files_by_pattern('*.a')
        passed = True
        extra = ""
        for rpm in files:
            for fn in files[rpm]:
                if not '-static' in rpm:
                    passed = False
                    extra += "%s : %s\n" % (rpm, fn)
        self.set_passed(passed, extra)




class CheckNoStaticExecutables(AdaCheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Staticly_Linking_Executables
    '''
    def __init__(self, base):
        AdaCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#Staticly_Linking_Executables'
        self.text = 'Package contains no static executables.'
        self.automatic = False
        self.type = 'MUST'

class CheckSoFiles(AdaCheckBase):
    '''
    MUST: If a package contains library files with a suffix (e.g. libfoo.so.1.1),
    then library files that end in .so (without suffix) must go in a -devel package.
    http://fedoraproject.org/wiki/Packaging/Guidelines#DevelPackages
    '''
    def __init__(self, base):
        AdaCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#DevelPackages'
        self.text = 'Development (unversioned) .so files in -devel subpackage, if present.'
        self.automatic = True
        self.type = 'MUST'

    def is_applicable(self):
        '''
        check if this test is applicable
        '''
        return self.has_files('*.so')

    def run(self):
        files = self.get_files_by_pattern('*.so')
        passed = True
        extra = "Unversioned so-files in non-devel package (fix or explain):"
        for rpm in files:
            for fn in files[rpm]:
                if not '-devel' in rpm:
                    passed = 'inconclusive'
                    extra += "%s : %s\n" % (rpm, fn)
        self.set_passed(passed, None if passed == True else extra)

class CheckLibToolArchives(AdaCheckBase):
    '''
    MUST: Packages must NOT contain any .la libtool archives,
    these must be removed in the spec if they are built.
    http://fedoraproject.org/wiki/Packaging/Guidelines#StaticLibraries
    '''
    def __init__(self, base):
        AdaCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#StaticLibraries'
        self.text = 'Package does not contain any libtool archives (.la)'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        if not self.has_files('*.la'):
            self.set_passed(True)
        else:
            extra = ""
            files = self.get_files_by_pattern('*.la')
            for rpm in files:
                for fn in files:
                    extra += "%s : %s\n" % (rpm, fn)
            self.set_passed(False, extra)


class CheckRPATH(AdaCheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Beware_of_Rpath
    '''
    def __init__(self, base):
        AdaCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#Beware_of_Rpath'
        self.text = 'Rpath absent or only used for internal libs.'
        self.automatic = True
        self.type = 'MUST'

    def run(self):
        for line in self.srpm.rpmlint_output:
            if 'binary-or-shlib-defines-rpath' in line:
                self.set_passed(False, 'See rpmlint output')
                return
        self.set_passed(True)



class CheckNoKernelModules(AdaCheckBase):
    '''
    At one point (pre Fedora 8), packages containing "addon" kernel modules were permitted.
    This is no longer the case. Fedora strongly encourages kernel module packagers to
    submit their code into the upstream kernel tree.
    http://fedoraproject.org/wiki/Packaging/Guidelines#No_External_Kernel_Modules
    '''
    def __init__(self, base):
        AdaCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#No_External_Kernel_Modules'
        self.text = 'Package does not contain kernel modules.'
        self.automatic = False
        self.type = 'MUST'


class CheckExecutiveArch(AdaCheckBase):
    '''
    The macro GNAT_arches expands to a list of architectures where GNAT packages are available in Fedora.
    Starting with Fedora 18, when there is a need to prevent attempts to build an Ada package on secondary
    architectures where GNAT has not been bootstrapped, this MUST be done with "ExclusiveArch: %{GNAT_arches}"
    https://fedoraproject.org/wiki/Packaging:Ada
    '''
    def __init__(self,base):
        AdaCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Ada#Compilation'
        self.text = 'Spec MUST be done with "ExclusiveArch: %{GNAT_arches}"'
        self.automatic = False
        self.type = 'MUST'

    def run(self):
        """ Run the check """
        brs = self.spec.find_tag('ExclusiveArch')
        self.set_passed(False)
        if len(brs) == 1:
            if brs[0].find("%{GNAT_arches}") != -1:
                self.set_passed(True)

class CheckFedoraGnatProject(AdaCheckBase):
    '''
    All packages that contain Ada code MUST have "BuildRequires: fedora-gnat-project-common"
    to ensure that the necessary RPM macros are defined.
    https://fedoraproject.org/wiki/Packaging:Ada
    '''
    def __init__(self,base):
        AdaCheckBase.__init__(self, base)
        self.url = 'https://fedoraproject.org/wiki/Packaging:Ada#Compilation'
        self.text = 'All packages that contain Ada code MUST have "BuildRequires: fedora-gnat-project-common"'
        self.automatic = False
        self.type = 'MUST'

    def run(self):
        """ Run the check
        """
        ## FIXME: find BR in main package and Requires in -devel
        brs = self.spec.find_tag('BuildRequires',section = "main")
        self.set_passed(False)
        if len(brs) != 0:
            for br in brs:
                if br.find("fedora-gnat-project-common") != -1:
                    self.set_passed(True)
        brs = self.spec.find_tag('Requires',section = "%package devel")
        if len(brs) != 0:
            for br in brs:
                if br.find("fedora-gnat-project-common") != -1:
                    self.set_passed(True)



# vim: set expandtab: ts=4:sw=4:
