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
# (C) 2011 - Tim Lauridsen <timlau@@fedoraproject.org>
'''
Handles -n, srpm and spec file already downloaded
'''

import os
import os.path

from glob import glob
from review_dirs import ReviewDirs
from settings import Settings
from urlparse import urlparse

from abstract_bug import AbstractBug


class NameBug(AbstractBug):
    """ Handles -n, spec and srpm already downloaded.
    """
    # pylint: disable=R0201

    def __init__(self, name):
        """ Constructor.
        :arg  name, basename used to search for rpm
        """
        AbstractBug.__init__(self)
        self.check_options()
        self.name = name

    def get_location(self):
        return 'Local files in ' + ReviewDirs.startdir

    def find_srpm_url(self):
        """ Retrieve the page and parse for srpm url. """
        if Settings.rpm_spec:
            if os.path.isfile(self.name):
                self.srpm_url = 'file://' + os.path.abspath(self.name)
                return
        pattern = os.path.join(ReviewDirs.startdir,
                               self.name + '*.src.rpm')
        srpms = glob(pattern)
        if len(srpms) == 0:
            raise self.BugError("Cannot find srpm: " + pattern)
        elif len(srpms) > 1:
            raise self.BugError("More than one srpm found for: "
                                + pattern)
        self.srpm_url = 'file://' + srpms[0]

    def find_spec_url(self):
        """ Retrieve the page and parse for spec url. """
        pattern = os.path.join(ReviewDirs.startdir,
                               self.name + '*.spec')
        specs = glob(pattern)
        if len(specs) == 0:
            raise self.BugError("Cannot find spec: " + pattern)
        elif len(specs) > 1:
            raise self.BugError("More than one spec found for: "
                                + pattern)
        self.spec_url = 'file://' + specs[0]

    def check_options(self):
        ''' Raise error if Settings options combination is invalid. '''
        AbstractBug.do_check_options('--name', ['other_bz'])

    def download_files(self):
        self.srpm_file = urlparse(self.srpm_url).path
        self.spec_file = urlparse(self.spec_url).path
        return True

# vim: set expandtab ts=4 sw=4:
