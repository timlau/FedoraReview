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

import logging
import os.path

from glob import glob
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
        self.unpack()

    def unpack(self, src=None):
        """ Local unpack using rpm2cpio. """
        if hasattr(self, 'unpacked_src'):
            return;

        wdir = ReviewDirs.srpm_unpacked
        oldpwd = os.getcwd()
        os.chdir(wdir)
        src = src if src else self.filename
        cmd = 'rpm2cpio ' + src + ' | cpio -u -i --quiet'
        rc = call(cmd, shell=True)
        if rc != 0:
            self.log.warn(
                  "Cannot unpack %s into %s" % (self.filename, wdir))
        else:
            self.unpacked_src = wdir
        os.chdir(oldpwd)

    def extract(self, path):
        """ Extract a named source and return containing directory. """
        self.filename = os.path.basename(path)
        self.unpack(path)
        files = glob( os.path.join(self.unpacked_src, '*'))
        if not self.filename in [os.path.basename(f) for f in files]:
            self.log.error(
               'Trying to unpack non-existing source: ' + path)
            return None
        extract_dir = os.path.join(self.unpacked_src,
                                   self.filename  + '-extract')
        if os.path.exists(extract_dir):
            return extract_dir
        else:
            os.mkdir(extract_dir)
        rv = self.rpmdev_extract(os.path.join(self.unpacked_src,
                                              self.filename),
                                 extract_dir)
        if not rv:
            self.log.error("Cannot unpack " +  self.filename)
            return None
        return extract_dir

    def build(self, force=False):
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
        if force:
            return self.mockbuild(True)
        if self.is_build or Settings.nobuild:
            if Mock.have_cache_for(self.spec.name):
                self.log.debug('Using already built rpms.')
                return SRPMFile.BUILD_OK
            else:
                self.log.info(
                     'No valid cache, building despite --no-build.')
        return self.mockbuild(force)

    def mockbuild(self, force=False):
        """ Run a mock build against the package.

        :kwarg force, boolean to force the mock build even if the
            package was already built.
        :kwarg silence, boolean to set/remove the output from the mock
            build.
        """
        info = 'Rebuilding ' + self.filename + ' using '
        if Settings.mock_config:
             self.log.info(info + 'mock root ' + Settings.mock_config)
        else:
             self.log.info(info + 'default root')
        cmd = 'mock'
        if Settings.mock_config:
            cmd += ' -r ' + Settings.mock_config
        if Settings.log_level > logging.INFO:
            cmd += ' -q'
        cmd += ' --rebuild'
        cmd +=  ' ' + Mock.get_mock_options()
        cmd += ' ' + self.filename + ' 2>&1 | tee build.log'
        if not Settings.verbose and not ' -q' in cmd:
            cmd += ' | egrep "Results and/or logs|ERROR" '
        self.log.debug('Mock command: %s' % cmd)
        rc = call(cmd, shell=True)
        Mock.builddir_cleanup()
        rc = str(rc)
        try:
            with open('build.log') as f:
                log  = '\n'.join(f.readlines())
                if 'ERROR' in log:
                    rc = 'Build error(s)'
        except:
            rc = "Can't open logfile"
        if rc == '0':
            self.is_build = True
            self.log.info('Build completed')
        else:
            self.log.info('Build failed rc = ' + rc)
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
        src_files = glob(self.unpacked_src + '/*')
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

        arg: filenames, list of filenames  to run rpmlint on
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
        no_errors, msg  = self.check_rpmlint_errors(out, self.log)
        return no_errors, msg if msg else out

    def rpmlint(self):
        """ Runs rpmlint against the file.
        """
        return self.run_rpmlint([self.filename])

    def rpmlint_rpms(self):
        """ Runs rpmlint against the used rpms - prebuilt or built in mock.
        """
        rpms = self.get_used_rpms()
        no_errors, result = self.run_rpmlint(rpms)
        return no_errors, result + '\n'

    def get_used_rpms(self, exclude_pattern=None):
        """ Return list of mock built or prebuilt rpms. """
        if Settings.prebuilt:
            rpms = glob(os.path.join(ReviewDirs.startdir, '*.rpm'))
        else:
            rpms = glob(os.path.join(Mock.resultdir, '*.rpm'))
        if not exclude_pattern:
            return rpms
        return filter(lambda s: not exclude_pattern in s, rpms)

    def get_files_rpms(self):
        """ Generate the list files contained in RPMs generated by the
        mock build or present using --prebuilt
        """
        if self._rpm_files:
            return self._rpm_files
        if Settings.prebuilt and not hasattr(self, 'prebuilt_info'):
            rpms = self.get_used_rpms()
            hdr = "Using local rpms: "
            sep = '\n' + ' ' * len(hdr)
            self.log.info(hdr + sep.join(rpms))
            self.prebuilt_info = True
        else:
            self.build()
            rpms = glob(os.path.join(Mock.resultdir, '*.rpm'))
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
