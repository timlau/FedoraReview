#-*- coding: utf-8 -*-

from FedoraReview import LangCheckBase

class CCppCheckBase(LangCheckBase):
    header='C/C++'

    def is_applicable(self):
        """Need more comprehensive check and return True in valid cases"""
        if self.has_files_re('/usr/(lib|lib64)/[\w\-]*\.so\.[0-9]') or \
           self.has_files('*.h') or \
           self.has_files('*.a') or \
           self.sources_have_files('*.c') or \
           self.sources_have_files('*.C') or \
           self.sources_have_files('*.cpp') :
           return True
        return False

class CheckLDConfig(CCppCheckBase):
    '''
    MUST: Every binary RPM package (or subpackage) which stores shared library files (not just symlinks)
    in any of the dynamic linker's default paths, must call ldconfig in %post and %postun.
    http://fedoraproject.org/wiki/Packaging/Guidelines#Shared_Libraries
    '''
    def __init__(self, base):
        CCppCheckBase.__init__(self, base)
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

class CheckHeaderFiles(CCppCheckBase):
    '''
    MUST: Header files must be in a -devel package
    http://fedoraproject.org/wiki/Packaging/Guidelines#DevelPackages
    '''
    def __init__(self, base):
        CCppCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#DevelPackages'
        self.text = 'Header files in -devel subpackage, if present.'
        self.automatic = True
        self.type = 'MUST'

    def is_applicable(self):
        '''
        check if this test is applicable
        '''
        return self.has_files('*.h')

    def run(self):
        files = self.get_files_by_pattern('*.h')
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



class CheckStaticLibs(CCppCheckBase):
    '''
    MUST: Static libraries must be in a -static package.
    http://fedoraproject.org/wiki/Packaging/Guidelines#StaticLibraries
    '''
    def __init__(self, base):
        CCppCheckBase.__init__(self, base)
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




class CheckNoStatucExecutables(CCppCheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Staticly_Linking_Executables
    '''
    def __init__(self, base):
        CCppCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#Staticly_Linking_Executables'
        self.text = 'Package contains no static executables.'
        self.automatic = False
        self.type = 'MUST'

class CheckSoFiles(CCppCheckBase):
    '''
    MUST: If a package contains library files with a suffix (e.g. libfoo.so.1.1),
    then library files that end in .so (without suffix) must go in a -devel package.
    http://fedoraproject.org/wiki/Packaging/Guidelines#DevelPackages
    '''
    def __init__(self, base):
        CCppCheckBase.__init__(self, base)
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
        extra = ""
        for rpm in files:
            for fn in files[rpm]:
                if not '-devel' in rpm:
                    passed = False
                    extra += "%s : %s\n" % (rpm, fn)
        self.set_passed(passed, extra)

class CheckLibToolArchives(CCppCheckBase):
    '''
    MUST: Packages must NOT contain any .la libtool archives,
    these must be removed in the spec if they are built.
    http://fedoraproject.org/wiki/Packaging/Guidelines#StaticLibraries
    '''
    def __init__(self, base):
        CCppCheckBase.__init__(self, base)
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


class CheckRPATH(CCppCheckBase):
    '''
    http://fedoraproject.org/wiki/Packaging/Guidelines#Beware_of_Rpath
    '''
    def __init__(self, base):
        CCppCheckBase.__init__(self, base)
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



class CheckNoKernelModules(CCppCheckBase):
    '''
    At one point (pre Fedora 8), packages containing "addon" kernel modules were permitted.
    This is no longer the case. Fedora strongly encourages kernel module packagers to
    submit their code into the upstream kernel tree.
    http://fedoraproject.org/wiki/Packaging/Guidelines#No_External_Kernel_Modules
    '''
    def __init__(self, base):
        CCppCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#No_External_Kernel_Modules'
        self.text = 'Package does not contain kernel modules.'
        self.automatic = False
        self.type = 'MUST'


class CheckRelocatable(CCppCheckBase):
    '''
    MUST: If the package is designed to be relocatable,
    the packager must state this fact in the request for review,
    along with the rationalization for relocation of that specific package.
    Without this, use of Prefix: /usr is considered a blocker.
    http://fedoraproject.org/wiki/Packaging/Guidelines#RelocatablePackages
    '''
    def __init__(self, base):
        CCppCheckBase.__init__(self, base)
        self.url = 'http://fedoraproject.org/wiki/Packaging/Guidelines#RelocatablePackages'
        self.text = 'Package is not relocatable.'
        self.automatic = False
        self.type = 'MUST'

# vim: set expandtab: ts=4:sw=4:
