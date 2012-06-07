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
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# (C) 2011 - Tim Lauridsen <timlau@fedoraproject.org>

'''
Tools for helping Fedora package reviewers
'''

import glob
import logging
import os.path

from subprocess import call

from helpers import Helpers
from mock import Mock
from review_dirs import ReviewDirs
from review_error import FedoraReviewError
from settings import Settings


class SRPMFile(Helpers):

    # Codes > 0 as returned by mock(1)
    BUILD_OK       = 0
    BUILD_FAIL     = -1
    BUILD_PREBUILT = -2

    def __init__(self, filename, spec=None):
        Helpers.__init__(self)
        self.filename = filename
        self.spec = spec
        self.is_build = False
        self.build_failed = False
        self._rpm_files = None
        self.rpmlint_output = []

    def unpack(self, src=None):
        """ Local unpack using rpm2cpio. """
        if hasattr(self, 'unpacked_src'):
            return;

        wdir = ReviewDirs.get_dir(ReviewDirs.SRPM_UNPACKED)
        oldpwd = os.getcwd()
        os.chdir(wdir)
        src = src if src else self.filename
        cmd = 'rpm2cpio ' + src + ' | cpio -i --quiet'
        rc = call(cmd, shell=True)
        if rc != 0:
            self.log.warn(
                  "Cannot unpack %s into %s" % (self.filename, wdir))
        else:
            self.unpacked_src = wdir
        os.chdir(oldpwd)

    def extract(self, path):
        """ Extract a named source and return containing directory. """
        self.filename=os.path.basename(path)
        self.unpack(path)
        files = glob.glob( self.unpacked_src  + '/*' )
        if not filename in [os.path.basename(f) for f in files]:
            self.log.error(
               'Trying to unpack non-existing source: ' + filename)
            return None
        extract_dir = self.unpacked_src + '/' +  filename  + '-extract'
        if os.path.exists(extract_dir):
            return extract_dir
        else:
            os.mkdir(extract_dir)
        rc = self.rpmdev_extract(os.path.join(self.unpacked_src,
                                              filename),
                                 extract_dir)
        if rc != 0:
            self.log.error( "Cannot unpack " + filename)
            return None
        return extract_dir

    def build(self, force=False, silence=False):
        """ Returns the build status, -1 is the build failed, -2
         reflects prebuilt rpms output code from mock otherwise.

        :kwarg force, boolean to force the mock build even if the
            package was already built.
        :kwarg silence, boolean to set/remove the output from the mock
            build.
        """
        if Settings.prebuilt:
            return SRPMFile.BUILD_PREBUILT
        if self.build_failed:
            return SRPMFile.BUILD_FAIL
        return self.mockbuild(force, silence=silence)

    def mockbuild(self, force=False, silence=False):
        """ Run a mock build against the package.

        :kwarg force, boolean to force the mock build even if the
            package was already built.
        :kwarg silence, boolean to set/remove the output from the mock
            build.
        """
        if not force and (self.is_build or Settings.nobuild):
            if Mock.have_cache_for(self.spec.name):
                self.log.info('Using already built rpms.')
                return SRPMFile.BUILD_OK
            else:
                self.log.info(
                     'No valid cache, building despite --nobuild.')
        self.log.info("Building %s using mock %s" % (
            self.filename, Settings.mock_config))
        cmd = 'mock -r %s  --rebuild %s ' % (
                Settings.mock_config, self.filename)
        if self.log.level == logging.DEBUG:
            cmd = cmd + ' -v '
        if Settings.mock_config:
            cmd = cmd + '--root ' + Settings.mock_config
        if Settings.mock_options:
            cmd = cmd + ' ' + Settings.mock_options
        if silence:
            cmd = cmd + ' 2>&1 | grep "Results and/or logs" '
        self.log.debug('Mock command: %s' % cmd)
        rc = call(cmd, shell=True)
        if rc == 0:
            self.is_build = True
            self.log.info('Build completed ok')
        else:
            self.log.info('Build failed rc = %i ' % rc)
            self.build_failed = True
            raise FedoraReviewError('Mock build failed.')
        return rc

    def get_build_dir(self):
        """ Return the BUILD directory from the mock environment.
        """
        bdir_root = Mock.get_builddir('BUILD')
        for entry in os.listdir(bdir_root):
            if os.path.isdir(bdir_root + entry):
                return bdir_root + entry
        return None

    def check_source_md5(self, path):
        filename = os.path.basename(path)
        self.unpack(self.filename)
        if not hasattr(self, 'unpacked_src'):
            self.log.warn("check_source_md5: Cannot unpack (?)")
            return "ERROR"
        src_files = glob.glob(self.unpacked_src + '/*')
        if not src_files:
            self.log.warn('No unpacked sources found (!)')
            return "ERROR"
        if not filename in [os.path.basename(f) for f in src_files]:
            self.log.warn('Cannot find source: ' + filename)
            return "ERROR"
        path = os.path.join(self.unpacked_src, filename)
        self.log.debug("Checking md5 for " + path)
        sum = self._md5sum(path)
        return sum

    def run_rpmlint(self, filenames):
        """ Runs rpmlint against the provided files.

        karg: filenames, list of filenames  to run rpmlint on
        """
        cmd = 'rpmlint -f .rpmlint ' + ' '.join( filenames )
        out = 'Checking: '
        sep = '\n' + ' ' * len( out )
        out += sep.join([os.path.basename(f) for f in filenames])
        out += '\n'
        out += self._run_cmd(cmd)
        out += '\n'
        for line in out.split('\n'):
            if line and len(line) > 0:
                self.rpmlint_output.append(line)
        no_errors, msg  = self.check_rpmlint_errors(out)
        return no_errors, msg if msg else out

    def rpmlint(self):
        """ Runs rpmlint against the file.
        """
        return self.run_rpmlint([self.filename])

    def rpmlint_rpms(self):
        """ Runs rpmlint against the used rpms - prebuilt or built in mock.
        """
        if Settings.prebuilt:
            rpms = glob.glob('*.rpm')
        else:
            rpms = glob.glob(Mock.resultdir + '/*.rpm')
        no_errors, result = self.run_rpmlint(rpms)
        return no_errors, result + '\n'

    def get_used_rpms(self, exclude_pattern=None):
        """ Return list of mock built or prebuilt rpms. """
        if Settings.prebuilt:
            rpms = set( glob.glob('*.rpm'))
        else:
            rpms = set(glob.glob(Mock.resultdir + '/*.rpm'))
        if not exclude_pattern:
            return list(rpms)
        matched = filter( lambda s: s.find(exclude_pattern) > 0, rpms)
        rpms = rpms - set(matched)
        return list(rpms)

    def get_files_rpms(self):
        """ Generate the list files contained in RPMs generated by the
        mock build or present using --prebuilt
        """
        if self._rpm_files:
            return self._rpm_files
        if Settings.prebuilt:
            rpms = glob.glob('*.rpm')
            hdr = "Using local rpms: "
            sep = '\n' + ' ' * len(hdr)
            self.log.info(hdr + sep.join(rpms))
        else:
            self.build()
            rpms = glob.glob(Mock.resultdir + '/*.rpm')
        rpm_files = {}
        for rpm in rpms:
            if rpm.endswith('.src.rpm'):
                continue
            cmd = 'rpm -qpl %s' % rpm
            rc = self._run_cmd(cmd)
            rpm_files[os.path.basename(rpm)] = rc.split('\n')
        self._rpm_files = rpm_files
        return rpm_files


# vim: set expandtab: ts=4:sw=4:
