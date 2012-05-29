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

import os.path
from urlparse import urlparse

from helpers import Helpers
from review_dirs import ReviewDirs
from review_error import FedoraReviewError


class Source(Helpers):
    ''' A source defined in the specfile.
    Attributes:
         - url: complete url, possibly file://
         - filename: local filename
         - tag: as defined in specfile e. g., 'Source0'
         - sources: container holding this source.
         - local: True if the source is just a file, false
           if it's a downloaded url
    '''
    def __init__(self, sources, tag, url):
        Helpers.__init__(self)
        self.sources = sources
        self.tag = tag
        self.downloaded = True
        if urlparse(url)[0] != '':  # This is a URL, Download it
            self.url = url
            self.local = False
            self.log.info("Downloading (%s): %s" % (tag, url))
            try:
                dir = ReviewDirs.get_dir(ReviewDirs.UPSTREAM)
                self.filename = self._get_file(self.url, dir)
            except:
                self.log.debug('Download error on ' + url,
                                exc_info=True)
                self.log.warning('Cannot download url: ' + url)
                self.downloaded = False
        else:  # this is a local file in the SRPM
            self.log.info("No upstream for (%s): %s" % (tag, url))
            srcdir = ReviewDirs.get_dir(ReviewDirs.UPSTREAM_UNPACKED)
            self.filename = os.path.join(srcdir, url)
            self.url = 'file://' + self.filename
            self.local = True

    def check_source_md5(self):
        self.log.info("Checking source md5 : %s" % self.filename)
        if self.downloaded:
            sum = self._md5sum(self.filename)
            return sum
        else:
            raise FedoraReviewError(self.tag +
                                    ": upstream source not found")

    def extract(self ):
        """ Extract the sources in the mock chroot so that it can be
        destroy easily by mock. Prebuilt sources are extracted to
        temporary directory in current dir.
        """
        self.extract_dir = \
            ReviewDirs.get_dir(ReviewDirs.UPSTREAM_UNPACKED)
        self.rpmdev_extract(self.filename, self.extract_dir)

    def get_source_topdir(self):
        """
        Return the top directory of the unpacked source.
        """
        if not hasattr(self, 'extract_dir'):
            self.extract()
        return self.extract_dir

# vim: set expandtab: ts=4:sw=4:
