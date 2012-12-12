#-*- coding: utf-8 -*-

#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#    MA  02110-1301 USA.
#
# pylint: disable=C0103,R0904,R0913,W0201
# (C) 2011 - Tim Lauridsen <timlau@fedoraproject.org>
'''
Unit checks for automatic test of fedora review guidelines
'''

import sys
import unittest2 as unittest

import srcpath                                   # pylint: disable=W0611

from fr_testcase import FR_TestCase


class Testspec():
    ''' Simple container for testdata. '''
    pass


class TestChecks(FR_TestCase):
    ''' Some complete tests, all results checked.'''

    def test_ruby_racc(self):
        ''' Run automated generic + ruby tests. '''
        spec = Testspec()
        spec.args = []
        spec.testcase = 'ruby-racc'
        spec.workdir = 'ruby-racc'
        spec.groups_ok = ['Setup', 'Generic', 'Ruby']
        spec.expected = [('pass', 'CheckResultdir'),
                        ('pending', 'CheckBuild'),
                        ('pass', 'CheckRpmlint'),
                        ('pass', 'CheckPackageInstalls'),
                        ('pass', 'CheckRpmlintInstalled'),
                        ('pending', 'CheckObeysFHS'),
                        ('pass', 'CheckFileRequires'),
                        ('pass', 'CheckUTF8Filenames'),
                        ('pass', 'RubyCheckRequiresRubyAbi'),
                        ('pending', 'CheckNoConflicts'),
                        ('pending', 'CheckDirectoryRequire'),
                        ('pass', 'RubyCheckBuildArchitecture'),
                        ('pending', 'CheckTestSuites'),
                        ('pending', 'CheckBuildroot'),
                        ('pending', 'CheckNaming'),
                        ('pending', 'CheckFinalRequiresProvides'),
                        ('pass', 'CheckDistTag'),
                        ('pending', 'CheckSupportAllArchs'),
                        ('pass', 'CheckFilePermissions'),
                        ('pending', 'CheckLatestVersionIsPackaged'),
                        ('pending', 'CheckObsoletesForRename'),
                        ('fail', 'NonGemCheckUsesMacros'),
                        ('pending', 'CheckClean'),
                        ('pending', 'CheckCleanBuildroot'),
                        ('pass', 'CheckDescMacros'),
                        ('pending', 'NonGemCheckFilePlacement'),
                        ('pending', 'CheckSpecDescTranslation'),
                        ('fail', 'CheckUseGlobal'),
                        ('pending', 'CheckDefattr'),
                        ('pending', 'CheckGuidelines'),
                        ('pass', 'NonGemCheckRequiresProperDevel'),
                        ('pass', 'CheckSourceUrl'),
                        ('pending', 'CheckExcludeArch'),
                        ('fail', 'RubyCheckTestsRun'),
                        ('pending', 'CheckOwnOther'),
                        ('pass', 'CheckFullVerReqSub'),
                        ('pending', 'CheckApprovedLicense'),
                        ('pending', 'CheckDocRuntime'),
                        ('pass', 'CheckFileDuplicates'),
                        ('pass', 'CheckSourceMD5'),
                        ('pending', 'CheckBundledLibs'),
                        ('fail', 'CheckBuildInMock'),
                        ('pending', 'CheckBuildRequires'),
                        ('pending', 'CheckOwnDirs'),
                        ('pass', 'CheckSourceComment'),
                        ('pending', 'CheckTimeStamps'),
                        ('fail', 'CheckRelocatable'),
                        ('pending', 'CheckLicenseUpstream'),
                        ('pending', 'CheckSystemdScripts'),
                        ('pending', 'CheckMacros'),
                        ('pending', 'CheckFunctionAsDescribed'),
                        ('pass', 'CheckLicensInDoc'),
                        ('pending', 'CheckRequires'),
                        ('pending', 'CheckCodeAndContent'),
                        ('pass', 'CheckNameCharset'),
                        ('pass', 'CheckIllegalSpecTags'),
                        ('pass', 'CheckSpecName'),
                        ('pending', 'CheckDevelFilesInDevel'),
                        ('pending', 'CheckSpecLegibility'),
                        ('na', 'CheckBuildCompilerFlags'),
                        ('pending', 'CheckContainsLicenseText'),
                        ('pending', 'CheckDesktopFile'),
                        ('pending', 'CheckLicenseField'),
                        ('pending', 'CheckPatchComments'),
                        ('pending', 'CheckChangelogFormat'),
                        ('pass', 'check-large-data'),
                        ('pass', 'check-srv-opt-local')]
        self.run_spec(spec)

    def test_logback(self):
        ''' Run automated generic+ java tests. '''
        spec = Testspec()
        spec.args = []
        spec.testcase = 'logback'
        spec.workdir = 'logback'
        spec.groups_ok = ['Setup', 'Generic', 'Java', 'Maven']
        spec.expected = [('pass', 'CheckResultdir'),
                         ('pending', 'CheckBuild'),
                         ('pass', 'CheckRpmlint'),
                         ('pass', 'CheckPackageInstalls'),
                         ('pass', 'CheckRpmlintInstalled'),
                         ('pending', 'CheckUpstremBuildMethod'),
                         ('pass', 'CheckNoOldMavenDepmap'),
                         ('pending', 'CheckObeysFHS'),
                         ('pass', 'CheckFileRequires'),
                         ('pass', 'CheckNoRequiresPost'),
                         ('pass', 'CheckUTF8Filenames'),
                         ('pending', 'CheckNoConflicts'),
                         ('pending', 'CheckDirectoryRequire'),
                         ('pass', 'CheckUseMavenpomdirMacro'),
                         ('pending', 'CheckTestSuites'),
                         ('pass', 'CheckBuildroot'),
                         ('pending', 'CheckNaming'),
                         ('pending', 'CheckFinalRequiresProvides'),
                         ('pass', 'CheckDistTag'),
                         ('pass', 'CheckUpdateDepmap'),
                         ('pending', 'CheckSupportAllArchs'),
                         ('pass', 'CheckFilePermissions'),
                         ('pending', 'CheckLatestVersionIsPackaged'),
                         ('pending', 'CheckObsoletesForRename'),
                         ('pass', 'CheckJavadocdirName'),
                         ('pass', 'CheckClean'),
                         ('pass', 'CheckCleanBuildroot'),
                         ('pass', 'CheckDescMacros'),
                         ('pending', 'CheckSpecDescTranslation'),
                         ('pass', 'CheckUseGlobal'),
                         ('pass', 'CheckDefattr'),
                         ('pending', 'CheckMultipleLicenses'),
                         ('pending', 'CheckGuidelines'),
                         ('pass', 'CheckSourceUrl'),
                         ('pending', 'CheckExcludeArch'),
                         ('pending', 'CheckAddMavenDepmap'),
                         ('pending', 'CheckLicenseInSubpackages'),
                         ('pending', 'CheckOwnOther'),
                         ('pass', 'CheckFullVerReqSub'),
                         ('pending', 'CheckApprovedLicense'),
                         ('pending', 'CheckDocRuntime'),
                         ('pass', 'CheckFileDuplicates'),
                         ('pass', 'CheckSourceMD5'),
                         ('pending', 'CheckBundledLibs'),
                         ('fail', 'CheckBuildInMock'),
                         ('pending', 'CheckBuildRequires'),
                         ('pending', 'CheckOwnDirs'),
                         ('fail', 'CheckJavaFullVerReqSub'),
                         ('pass', 'CheckSourceComment'),
                         ('pending', 'CheckTimeStamps'),
                         ('pass', 'CheckRelocatable'),
                         ('pending', 'CheckLicenseUpstream'),
                         ('pending', 'CheckSystemdScripts'),
                         ('pending', 'CheckMacros'),
                         ('pending', 'CheckFunctionAsDescribed'),
                         ('pass', 'CheckLicensInDoc'),
                         ('pending', 'CheckRequires'),
                         ('pending', 'CheckCodeAndContent'),
                         ('pass', 'CheckNameCharset'),
                         ('pending', 'CheckPomInstalled'),
                         ('pass', 'CheckIllegalSpecTags'),
                         ('pass', 'CheckSpecName'),
                         ('pass', 'CheckJPackageRequires'),
                         ('pass', 'CheckJavadoc'),
                         ('pending', 'CheckDevelFilesInDevel'),
                         ('pending', 'CheckSpecLegibility'),
                         ('na', 'CheckBuildCompilerFlags'),
                         ('pass', 'CheckJavadocJPackageRequires'),
                         ('pending', 'CheckContainsLicenseText'),
                         ('pending', 'CheckDesktopFile'),
                         ('pending', 'CheckLicenseField'),
                         ('pending', 'CheckPatchComments'),
                         ('pending', 'CheckChangelogFormat'),
                         ('pass', 'check-large-data'),
                         ('pass', 'check-srv-opt-local'),
                         ('pass', 'java-check-bundled-jars')]
        self.run_spec(spec)

    def test_scriptlets_fail(self):
        ''' Scriptlet tests mostly expected to file. '''
        spec = Testspec()
        spec.testcase = 'scriptlets-fail'
        spec.workdir = 'scriptlets-fail'
        spec.args = ['-x', 'CheckPackageInstalls,CheckUTF8Filenames']
        spec.groups_ok = ['Setup', 'Generic']
        spec.expected = [('fail', 'CheckGconfSchemaInstall'),
                         ('fail', 'CheckGtkQueryModules'),
                         ('fail', 'CheckGioQueryModules'),
                         ('fail', 'CheckUpdateIconCache'),
                         ('fail', 'CheckInfoInstall'),
                         ('fail', 'CheckGlibCompileSchemas'),
                         ('fail', 'CheckUpdateMimeDatabase'),
                         ('pending', 'CheckBundledFonts'),
                         ('pending', 'CheckSourcedirMacroUse'),
                         ('pending', 'CheckTmpfiles')]
        self.run_spec(spec)

    def test_scriptlets_ok(self):
        ''' Scriptlet tests mostly expected to pass (or pending). '''
        spec = Testspec()
        spec.testcase = 'scriptlets-ok'
        spec.workdir = 'scriptlets-ok'
        spec.args = ['-x', 'CheckPackageInstalls,CheckUTF8Filenames']
        spec.groups_ok = ['Setup', 'Generic']
        spec.expected = [('pending', 'CheckGconfSchemaInstall'),
                         ('pending', 'CheckGtkQueryModules'),
                         ('pending', 'CheckGioQueryModules'),
                         ('pending', 'CheckUpdateIconCache'),
                         ('pending', 'CheckInfoInstall'),
                         ('pending', 'CheckGlibCompileSchemas'),
                         ('pending', 'CheckUpdateMimeDatabase'),
                         ('pending', 'CheckBundledFonts'),
                         ('pending', 'CheckSourcedirMacroUse'),
                         ('pending', 'CheckTmpfiles')]
        self.run_spec(spec)

    def test_FreeSOLID(self):
        ''' Test the FreeSOLID spec. '''
        spec = Testspec()
        spec.args = []
        spec.testcase = 'FreeSOLID'
        spec.workdir = 'FreeSOLID'
        spec.groups_ok = ['Setup', 'Generic', 'C/C++']
        spec.expected = [('pass', 'CheckResultdir'),
                         ('pending', 'CheckBuild'),
                         ('pass', 'CheckRpmlint'),
                         ('pass', 'CheckPackageInstalls'),
                         ('pass', 'CheckRpmlintInstalled'),
                         ('fail', 'CheckParallelMake'),
                         ('pending', 'CheckObeysFHS'),
                         ('pass', 'CheckFileRequires'),
                         ('pass', 'CheckUTF8Filenames'),
                         ('pending', 'CheckNoConflicts'),
                         ('pending', 'CheckDirectoryRequire'),
                         ('pending', 'CheckTestSuites'),
                         ('pass', 'CheckBuildroot'),
                         ('pending', 'CheckNaming'),
                         ('pending', 'CheckFinalRequiresProvides'),
                         ('na', 'CheckSpecAsInSRPM'),
                         ('pending', 'CheckScriptletSanity'),
                         ('pass', 'CheckDistTag'),
                         ('pending', 'CheckSupportAllArchs'),
                         ('pass', 'CheckFilePermissions'),
                         ('pending', 'CheckLatestVersionIsPackaged'),
                         ('pending', 'CheckObsoletesForRename'),
                         ('pass', 'CheckClean'),
                         ('pass', 'CheckCleanBuildroot'),
                         ('pass', 'CheckDescMacros'),
                         ('pending', 'CheckSpecDescTranslation'),
                         ('pass', 'CheckUseGlobal'),
                         ('pass', 'CheckSoFiles'),
                         ('pass', 'CheckDefattr'),
                         ('pending', 'CheckGuidelines'),
                         ('pass', 'CheckSourceUrl'),
                         ('pending', 'CheckExcludeArch'),
                         ('pending', 'CheckLicenseInSubpackages'),
                         ('pending', 'CheckNoKernelModules'),
                         ('pending', 'CheckOwnOther'),
                         ('pending', 'CheckFullVerReqSub'),
                         ('pending', 'CheckApprovedLicense'),
                         ('pending', 'CheckDocRuntime'),
                         ('pass', 'CheckFileDuplicates'),
                         ('pass', 'CheckSourceMD5'),
                         ('pending', 'CheckBundledLibs'),
                         ('fail', 'CheckBuildInMock'),
                         ('pass', 'CheckLDConfig'),
                         ('pending', 'CheckBuildRequires'),
                         ('pending', 'CheckOwnDirs'),
                         ('pending', 'CheckNoStaticExecutables'),
                         ('pass', 'CheckRPATH'),
                         ('pending', 'CheckUsefulDebuginfo'),
                         ('pass', 'CheckSourceComment'),
                         ('pending', 'CheckTimeStamps'),
                         ('pass', 'CheckHeaderFiles'),
                         ('pass', 'CheckRelocatable'),
                         ('pending', 'CheckLicenseUpstream'),
                         ('pending', 'CheckSystemdScripts'),
                         ('pending', 'CheckMacros'),
                         ('pending', 'CheckFunctionAsDescribed'),
                         ('pass', 'CheckLicensInDoc'),
                         ('pending', 'CheckRequires'),
                         ('pass', 'CheckPkgConfigFiles'),
                         ('pending', 'CheckCodeAndContent'),
                         ('pass', 'CheckNameCharset'),
                         ('pass', 'CheckLibToolArchives'),
                         ('pass', 'CheckIllegalSpecTags'),
                         ('pass', 'CheckSpecName'),
                         ('pending', 'CheckDevelFilesInDevel'),
                         ('pending', 'CheckSpecLegibility'),
                         ('pending', 'CheckBuildCompilerFlags'),
                         ('pending', 'CheckContainsLicenseText'),
                         ('pending', 'CheckDesktopFile'),
                         ('pending', 'CheckLicenseField'),
                         ('pending', 'CheckPatchComments'),
                         ('pending', 'CheckChangelogFormat'),
                         ('pass', 'check-large-data'),
                         ('pass', 'check-srv-opt-local')]
        self.run_spec(spec)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        suite = unittest.TestSuite()
        for test in sys.argv[1:]:
            suite.addTest(TestChecks(test))
    else:
        suite = unittest.TestLoader().loadTestsFromTestCase(TestChecks)
    unittest.TextTestRunner(verbosity=2).run(suite)
