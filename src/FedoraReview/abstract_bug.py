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
Common bug base class. A Bug is a filter that provides usable URL:s to
srpm and spec file given some kind of key when created.
'''
import os.path
import re
import shutil
import tempfile
import urllib2
import urllib

from glob import glob
from urlparse import urlparse

from BeautifulSoup import BeautifulSoup

from helpers import Helpers
from review_error import FedoraReviewError
from settings import Settings
from srpm_file import SRPMFile
from review_dirs import ReviewDirs


class BugException(FedoraReviewError):
    pass


class SettingsError(BugException):
    pass


class AbstractBug(Helpers):
    """ This class has an interesting name.
    Anyway, defines an object which can determine URLs for spec
    and srpm given a key like a name, bug nr etc. Attributes:
     - srpm_url: valid after find_urls, possibly None
     - spec_url: valid after find_urls, possibly None
     - srpm_file valid after download_files.
     - spec_file valid after download_files.
     - name: name of bug, possibly '?'.
    Concrete implementations basically understands how to
    set the urls, this base class handles the rest.
    """

    BZ_OPTIONS = [ 'assign', 'login', 'other_bz', 'user' ]

    def __init__(self):
        Helpers.__init__(self)
        self.spec_url = None
        self.srpm_url = None
        self.spec_file = None
        self.srpm_file = None

    def find_spec_url(self):
        """ Grab the spec url, update self.spec_url.  """
        self.log.error( "Calling abstract method" + __method__)

    def find_srpm_url(self):
        """ Grab the srpm url, update self.srpm_url.  """
        self.log.error( "Calling abstract method" + __method__)

    def get_location(self):
        """ Return visible label for source of srpm/spec """
        self.log.error( "Calling abstract method" + __method__)

    def do_download_spec(self):
        """ Download the spec file and srpm extracted from the page.
        """
        if not hasattr( self, 'dir'):
            self.dir = ReviewDirs.srpm

        spec_name = os.path.basename(self.spec_url)
        spec_path = os.path.join(self.dir, spec_name)
        file, headers = urllib.urlretrieve(self.spec_url, spec_path)
        self.spec_file =  file

    def do_download_srpm(self):
        """ Download the spec file and srpm extracted from the page.
        """
        if not hasattr( self, 'dir'):
            self.dir = ReviewDirs.srpm

        srpm_name = os.path.basename(self.srpm_url)
        srpm_path = os.path.join(self.dir, srpm_name)
        file, headers = urllib.urlretrieve(self.srpm_url, srpm_path)
        self.srpm_file = file

    def do_download_files(self):
        """ Download the spec file and srpm extracted from the page.
        """
        if not self.srpm_file:
            self.do_download_srpm()
        if not self.spec_file:
            self.do_download_spec()
        return True

    def is_downloaded(self):
        ok = (self.spec_file and os.path.exists(self.spec_file)
                and self.srpm_file and
                os.path.exists(self.srpm_file))
        return ok

    def _check_cache(self):
        try:
            specs = glob(os.path.join(self.dir, '*.spec'))
            found = len(specs)
            srpms = glob(os.path.join(self.dir, '*.src.rpm'))
            found += len(srpms)
            if found == 2:
                self.spec_file = specs[0]
                self.srpm_file = srpms[0]
                self.spec_url = 'file://' + specs[0]
                self.srpm_url = 'file://' + srpms[0]
                return True
            else:
                return False
        except:
            return False

    def download_files(self):
        """ Download the spec file and srpm extracted from the bug
        report.
        """
        if Settings.cache and self._check_cache():
            self.log.info("Using cached copies of spec and srpm")
            return True
        try:
            self.log.info('Downloading .spec and .srpm files')
            self.do_download_files()
        except:
            self.log.debug('bug download error', exc_info=True)
            self.log.error('Cannot download file(s)')
            return False
        return True

    def _get_spec_from_srpm(self):
        path = urlparse(self.srpm_url).path
        name = os.path.basename(path).rsplit('-',2)[0]
        ReviewDirs.workdir_setup(name)
        self.do_download_srpm()
        
        SRPMFile(self.srpm_file).unpack()
        file = glob(os.path.join(ReviewDirs.srpm_unpacked, '*.spec'))[0]
        self.spec_file = file
        self.spec_url = 'file://' + file

    def find_urls(self):
        """ Retrieve the page and parse for srpm and spec url. """
        try:
            self.find_srpm_url()
            self.log.info("  --> SRPM url: " + self.srpm_url)
            if Settings.rpm_spec:
                self._get_spec_from_srpm()
            else:
                self.find_spec_url()
            self.log.info("  --> Spec url: " + self.spec_url)
        except:
            self.log.debug('url_bug link parse error', exc_info=True)
            self.log.error('Cannot find usable urls here')
            return False
        return True

    def get_name(self):
       ''' Return name of bug. '''
       if self.spec_file:
           return os.path.basename(self.spec_file).rsplit('.',1)[0]
       elif self.spec_url:
           basename = os.path.basename(urlparse(self.spec_url).path)
           return basename.rsplit('.',1)[0]
       elif self.srpm_file:
           return  os.path.basename(self.srpm_file).rsplit('-',2)[0]
       elif self.srpm_url:
           basename = os.path.basename(urlparse(self.srpm_url).path)
           return basename.rsplit('-',2)[0]
       else:
           return '?'
           
    def get_dirname(self, prefix=''):
        ''' Return dirname to be used for this bug. '''
        if self.get_name() != '?':
            return prefix + self.get_name()
        else:
            return prefix + tempfile.mkdtemp(prefix='review-', 
                                             dir=os.getcwd())

    def do_check_options(self, mode, bad_opts):
       for opt in bad_opts:
           if hasattr(Settings, opt) and getattr(Settings, opt):
                raise SettingsError(
                    '--' + opt + ' can not be used with ' +  mode)


# vim: set expandtab: ts=4:sw=4:
