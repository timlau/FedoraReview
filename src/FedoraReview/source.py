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
import shutil

from urlparse import urlparse

from helpers import Helpers
from review_dirs import ReviewDirs
from review_error import FedoraReviewError
from settings import Settings

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

        def my_logger(cache):
             if cache:
                 path = urlparse(url).path
                 self.log.info("Using cached data for (%s): %s" %
                               (tag, os.path.basename(path)))
             else:
                 self.log.info("Downloading (%s): %s" % (tag, url))


        Helpers.__init__(self)
        self.sources = sources
        self.tag = tag
        self.downloaded = True
        is_url = urlparse(url)[0] != ''
        if is_url:  # This is a URL, Download it
            self.url = url
            self.local = False
            try:
                self.filename = self._get_file(url,
                                               ReviewDirs.upstream,
                                               my_logger)
            except:
                self.log.debug('Download error on ' + url,
                                exc_info=True)
                self.log.warning('Cannot download url: ' + url)
                self.downloaded = False
                # get the filename
                url = urlparse(url)[2].split('/')[-1]

        if not is_url or not self.downloaded:  # this is a local file in the SRPM
            local_src = os.path.join(ReviewDirs.startdir, url)
            if os.path.isfile(local_src):
                self.log.info(
                    "Using local file " + url + " as " + tag)
                srcdir = ReviewDirs.startdir
                self.local_src = local_src
                self.local = False
            else:
                self.log.info("No upstream for (%s): %s" % (tag, url))
                srcdir = ReviewDirs.srpm_unpacked
                self.local = True
            self.filename = os.path.join(srcdir, url)
            self.url = 'file://' + self.filename

    def check_source_checksum(self):
        self.log.debug("Checking source {0} : {1}".format(Settings.checksum,
                                                          self.filename))
        if self.downloaded:
            sum = self._checksum(self.filename)
            return sum
        else:
            raise FedoraReviewError(self.tag +
                                    ": upstream source not found")

    def is_archive(self):
        filename = self.filename.split('/')[-1]
        for i in ('.tar.gz','.tar.bz2','.tar.lzma','.tar.xz','.zip', '.7z'):
            if filename.endswith(i):
                return True
        return False

    def extract(self ):
        ''' Extract the source into a directory under upstream-unpacked,
            available in the extract_dir property. Sources which not
            could be extracted e. g., plain files are copied to the
            extract-dir.
        '''
        self.extract_dir = os.path.join(ReviewDirs.upstream_unpacked,
                                        self.tag)
        if not os.path.exists(self.extract_dir):
            os.mkdir(self.extract_dir)
        if self.downloaded:
            if not self.rpmdev_extract(self.filename, self.extract_dir):
                shutil.copy(self.filename, self.extract_dir)

    def get_source_topdir(self):
        """
        Return the top directory of the unpacked source.
        """
        if not hasattr(self, 'extract_dir'):
            self.extract()
        return self.extract_dir

# vim: set expandtab: ts=4:sw=4:
