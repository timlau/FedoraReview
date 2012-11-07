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
import tempfile

from abc import ABCMeta, abstractmethod
from glob import glob
from urlparse import urlparse

from helpers_mixin import HelpersMixin
from review_error import ReviewError
from settings import Settings
from srpm_file import SRPMFile
from review_dirs import ReviewDirs


class AbstractBug(HelpersMixin):
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
    # pylint:disable=R0201

    __metaclass__ = ABCMeta

    class BugError(ReviewError):
        ''' Generic error thrown in bugs, not showing logs. '''

        def __init__(self, what):
            ReviewError.__init__(self, what, 2)
            self.show_logs = False

    def __init__(self):
        HelpersMixin.__init__(self)
        self.log = Settings.get_logger()
        self.spec_url = None
        self.srpm_url = None
        self.spec_file = None
        self.srpm_file = None
        self.dir = None

    @abstractmethod
    def find_spec_url(self):
        """ Grab the spec url, update self.spec_url.  """
        assert False

    @abstractmethod
    def find_srpm_url(self):
        """ Grab the srpm url, update self.srpm_url.  """
        assert False

    @abstractmethod
    def get_location(self):
        """ Return visible label for source of srpm/spec """
        assert False

    def do_download_spec(self):
        """
        Download the spec file and srpm extracted from the page.
        Raises IOError.
        """
        if not self.dir:
            self.dir = ReviewDirs.srpm

        spec_name = os.path.basename(self.spec_url)
        self.spec_file = os.path.join(self.dir, spec_name)
        self.urlretrieve(self.spec_url, self.spec_file)

    def do_download_srpm(self):
        """
        Download the spec file and srpm extracted from the page.
        Raises IOError.
        """

        def has_srpm():
            ''' Return true iff self.srpmfile is a valid path. '''
            return hasattr(self, 'srpm_file')  and self.srpm_file and  \
                   os.path.exists(self.srpm_file)

        if not self.dir:
            self.dir = ReviewDirs.srpm

        if has_srpm() and Settings.cache:
            self.log.debug("Using cached source: " + self.srpm_file)
            return
        srpm_name = os.path.basename(self.srpm_url)
        self.srpm_file = os.path.join(self.dir, srpm_name)
        self.urlretrieve(self.srpm_url, self.srpm_file)

    def do_download_files(self):
        """
        Download the spec file and srpm extracted from the page.
        Raises IOError.
        """
        if not self.srpm_file:
            self.do_download_srpm()
        if not self.spec_file:
            self.do_download_spec()
        return True

    def is_downloaded(self):
        ''' Return true iff self.{specfile, srpmfile} are valid. '''
        ok = (self.spec_file and os.path.exists(self.spec_file)
                and self.srpm_file and
                os.path.exists(self.srpm_file))
        return ok

    def _check_cache(self):
        ''' return True iff srpm and spec are in srpm dir . '''
        name = self.get_name()
        assert(name != '?')
        specs = glob(os.path.join(ReviewDirs.srpm,
                                  name + '*.spec'))
        found = len(specs)
        srpms = glob(os.path.join(ReviewDirs.srpm,
                     name + '*.src.rpm'))
        found += len(srpms)
        if found == 2:
            self.spec_file = specs[0]
            self.srpm_file = srpms[0]
            self.spec_url = 'file://' + specs[0]
            self.srpm_url = 'file://' + srpms[0]
            return True
        else:
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
        except IOError as ex:
            self.log.debug('bug download error', exc_info=True)
            self.log.error('Cannot download file(s): ' + str(ex))
            return False
        return True

    def _get_spec_from_srpm(self):
        ''' Extract spec from srpm and update self.spec_url. '''
        path = urlparse(self.srpm_url).path
        name = os.path.basename(path).rsplit('-', 2)[0]
        ReviewDirs.workdir_setup(name, Settings.cache)
        self.do_download_srpm()

        SRPMFile(self.srpm_file).unpack()
        path = glob(os.path.join(ReviewDirs.srpm_unpacked,
                                 name + '*.spec'))[0]
        self.spec_file = path
        self.spec_url = 'file://' + path

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
        except ReviewError as fre:
            raise fre
        except:
            self.log.debug('url_bug link parse error', exc_info=True)
            self.log.error('Cannot find usable urls here')
            return False
        return True

    def get_name(self):
        ''' Return name of bug. '''
        if self.spec_file:
            return os.path.basename(self.spec_file).rsplit('.', 1)[0]
        elif self.spec_url:
            basename = os.path.basename(urlparse(self.spec_url).path)
            return basename.rsplit('.', 1)[0]
        elif self.srpm_file:
            return  os.path.basename(self.srpm_file).rsplit('-', 2)[0]
        elif self.srpm_url:
            basename = os.path.basename(urlparse(self.srpm_url).path)
            return basename.rsplit('-', 2)[0]
        else:
            return '?'

    def get_dirname(self, prefix='review-'):
        ''' Return dirname to be used for this bug. '''
        if self.get_name() != '?':
            return prefix + self.get_name()
        else:
            return prefix + tempfile.mkdtemp(prefix=prefix,
                                             dir=os.getcwd())

    @staticmethod
    def do_check_options(mode, bad_opts):
        '''
        Verify that Settings don't have bad options, raise
        SettingsError if so.
        '''

        class SettingsError(ReviewError):
            ''' Thrown for invalid settings combinations. '''
            def __init__(self, what):
                ReviewError.__init__(self, "Incompatible settings: " + what)

        for opt in bad_opts:
            if hasattr(Settings, opt) and getattr(Settings, opt):
                raise SettingsError(
                    '--' + opt + ' can not be used with ' + mode)


# vim: set expandtab: ts=4:sw=4:
