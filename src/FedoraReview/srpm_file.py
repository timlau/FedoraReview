# -*- coding: utf-8 -*-

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

import os.path
import shutil

from glob import glob
from subprocess import call

from helpers_mixin import HelpersMixin
from review_dirs import ReviewDirs
from settings import Settings


class SRPMFile(HelpersMixin):
    ''' Models the srpm and it's methods. '''

    def __init__(self, filename):
        HelpersMixin.__init__(self)
        self._rpm_files = None
        self._prebuilt_info = None
        self._unpacked_src = None
        self.filename = filename
        self.name = os.path.basename(filename).rsplit('-', 2)[0]
        self.unpack()

    def unpack(self, src=None):
        """ Local unpack using rpm2cpio. """
        if self._unpacked_src:
            return

        wdir = ReviewDirs.srpm_unpacked
        oldpwd = os.getcwd()
        os.chdir(wdir)
        src = src if src else self.filename
        cmd = 'rpm2cpio ' + src + ' | cpio -u -i -m --quiet'
        rc = call(cmd, shell=True)
        if rc != 0:
            self.log.warn(
                "Cannot unpack %s into %s" % (self.filename, wdir))
        else:
            self._unpacked_src = wdir
        os.chdir(oldpwd)

    def extract(self, path):
        """ Extract a named source and return containing directory. """
        self.filename = os.path.basename(path)
        self.unpack(path)
        files = glob(os.path.join(self._unpacked_src, '*'))
        if self.filename not in [os.path.basename(f) for f in files]:
            self.log.error(
                'Trying to unpack non-existing source: ' + path)
            return None
        extract_dir = os.path.join(self._unpacked_src,
                                   self.filename + '-extract')
        if os.path.exists(extract_dir):
            return extract_dir
        else:
            os.mkdir(extract_dir)
        rv = self.rpmdev_extract(os.path.join(self._unpacked_src,
                                              self.filename),
                                 extract_dir)
        if not rv:
            self.log.debug("Cannot unpack %s, so probably not an "
                           "archive. Copying instead" % self.filename)
            shutil.copy(os.path.join(self._unpacked_src, self.filename),
                        extract_dir)
        return extract_dir

    def check_source_checksum(self, path):
        '''Return checksum for archive. '''
        filename = os.path.basename(path)
        self.unpack(self.filename)
        if not self._unpacked_src:
            self.log.warn("check_source_checksum: Cannot unpack (?)")
            return "ERROR"
        src_files = glob(self._unpacked_src + '/*')
        if not src_files:
            self.log.warn('No unpacked sources found (!)')
            return "ERROR"
        if filename not in [os.path.basename(f) for f in src_files]:
            self.log.warn('Cannot find source: ' + filename)
            return "ERROR"
        path = os.path.join(self._unpacked_src, filename)
        self.log.debug("Checking {0} for {1}".format(Settings.checksum, path))
        return self._checksum(path)


# vim: set expandtab ts=4 sw=4:
