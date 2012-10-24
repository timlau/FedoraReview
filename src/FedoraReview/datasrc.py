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
Common data src base class. A DataSrc is a collection of containers
(source tarballs, source rpm, binary rpms...) each of which holding
a filelist.
'''
import os
import os.path
import re

from abc import ABCMeta, abstractmethod
from fnmatch import fnmatch
from glob import glob

from review_dirs import ReviewDirs
from rpm_file import RpmFile
from settings import Settings
from source import Source


class AbstractDataSource():
    '''
     A collection of file containers.
       - The contained files can be retrieved either for a
         single container or for all
       - Likewise, single containers or complete file list
         can be searched in different ways
       - Each container can be accessed using a key, normally
         a printable name.
     '''
    # pylint:disable=R0201,W0613

    __metaclass__ = ABCMeta

    def __init__(self):
        self.log = Settings.get_logger()

    @abstractmethod
    def filelist(self, container=None):
        '''
        Return list of all files in a container or consolidated list
        of files in all containers if container == None.
        '''
        assert False

    @abstractmethod
    def get(self, key=None):
        ''' Return the container object bound to key. '''

    @abstractmethod
    def get_keys(self):
        ''' Return all keys usable with get(). '''
        pass

    def get_all(self):
        ''' Return list of all containers. '''
        return self.containers

    def find(self, glob_pattern, container=None):
        ''' Find first file matching glob_pattern, or None. '''
        if container and not container in self.containers:
            raise ValueError('DataSource: bad source: ' + container)
        if hasattr(glob_pattern, 'match'):
            return self.find_re(glob_pattern, container)
        for s in [container] if container else self.containers:
            for f in self.filelist(s):
                if fnmatch(f, glob_pattern):
                    return f
        return None

    def find_re(self, regex, container=None):
        ''' Find first file matching regex, or None. '''
        if container and not container in self.containers:
            raise ValueError('DataSource: bad source: ' + container)
        if isinstance(regex, str):
            regex = re.compile(regex, re.IGNORECASE)
        for s in [container] if container else self.containers:
            for f in self.filelist(s):
                if regex.match(f):
                    return f
        return None

    def has_files(self, glob_pattern, container=None):
        ''' True if there's at least one matching file. '''
        if container and not container in self.containers:
            raise ValueError('DataSource: bad source: ' + container)
        if hasattr(glob_pattern, 'match'):
            return self.has_files_re(glob_pattern, container)
        return self.find(glob_pattern, container) != None

    def has_files_re(self, regex, container=None):
        ''' True if there's at least one matching file. '''
        if container and not container in self.containers:
            raise ValueError('DataSource: bad source: ' + container)
        if isinstance(regex, str):
            regex = re.compile(regex, re.IGNORECASE)
        return self.find_re(regex, container) != None

    def find_all(self, glob_pattern, container=None):
        ''' List of all files matching glob_pattern. '''
        if container and not container in self.containers:
            raise ValueError('DataSource: bad source: ' + container)
        if hasattr(glob_pattern, 'match'):
            return self.find_all_re(glob_pattern, container)
        result = []
        for s in [container] if container else self.containers:
            for f in self.filelist(s):
                if fnmatch(f, glob_pattern):
                    result.append(f)
        return result

    def find_all_re(self, regex, container=None):
        ''' List of all files matching regex. '''
        if container and not container in self.containers:
            raise ValueError('DataSource: bad source: ' + container)
        if isinstance(regex, str):
            regex = re.compile(regex, re.IGNORECASE)
        result = []
        for s in [container] if container else self.containers:
            for f in self.filelist(s):
                if regex.match(f):
                    result.append(f)
        return result


class BuildFilesSource(AbstractDataSource):
    ''' Patched sources created using rpmbuild -bp. '''

    def __init__(self):
        AbstractDataSource.__init__(self)
        self._containers = None
        self.files = None

    def _get_containers(self):
        ''' Return the list of containers, i. e., builddir. '''
        self.init()
        return self._containers

    containers = property(_get_containers)

    def init(self):
        ''' Lazy init, hopefully not called until BUILD is there. '''
        if self._containers:
            return
        build_dir_pat = os.path.join(ReviewDirs.root, 'BUILD', '*')
        entries = glob(build_dir_pat)
        if not entries:
            raise LookupError('No build directory found in BUILD')
        if len(entries) > 1:
            raise LookupError('More than one build directory in BUILD')
        self._containers = [entries[0]]
        self.files = None

    def filelist(self, container=None):
        self.init()
        if container and not container in self.containers:
            raise ValueError('BuildFilesSource: illegal rootdir')
        if self.files == None:
            self.files = []
            # pylint: disable=W0612
            for root, dirs, files in os.walk(self.containers[0]):
                paths = [os.path.join(root, f) for f in files]
                self.files.extend(paths)
        return self.files

    def get(self, key=None):
        ''' Return the root builddir under BUILD.'''
        self.init()
        return  self.containers[0]

    def get_keys(self):
        return [None]


class RpmDataSource(AbstractDataSource):
    ''' The binary rpms and their filelists. '''

    def __init__(self, spec):
        AbstractDataSource.__init__(self)
        self.containers = spec.packages
        self.spec = spec
        self.rpms_by_pkg = {}
        for pkg in spec.packages:
            self.rpms_by_pkg[pkg] = \
                RpmFile(pkg, spec.version, spec.release)

    def filelist(self, container=None):
        if container and not container in self.containers:
            raise ValueError('RpmSource: bad package: ' + container)
        if container:
            return self.rpms_by_pkg[container].filelist()
        all_ = []
        for pkg in self.rpms_by_pkg.iterkeys():
            all_.extend(self.rpms_by_pkg[pkg].filelist())
        return all_

    def get(self, key=None):
        ''' Return RpmFile object for a package name key. '''
        if key and key in  self.rpms_by_pkg.iterkeys():
            return self.rpms_by_pkg[key]
        return None

    def get_keys(self):
        return self.rpms_by_pkg.iterkeys()


class SourcesDataSource(AbstractDataSource):
    ''' The tarballs listed as SourceX: in specfile. '''

    def __init__(self, spec):
        AbstractDataSource.__init__(self)
        self.sources_by_tag = {}
        for tag, url in spec.sources_by_tag.iteritems():
            self.sources_by_tag[tag] = Source(tag, url)
        self.containers = [s for s in self.sources_by_tag.itervalues()]
        self.files_by_tag = {}

    def _load_files_(self, tag):
        """ Ensure that file list for tag is in files_by_tag. """

        if tag in self.files_by_tag.iterkeys():
            return
        source = self.sources_by_tag[tag]
        if not source.extract_dir:
            source.extract()
        self.log.debug('Adding files in : %s' % source.filename)
        self.files_by_tag[tag] = []
        for root, files in os.walk(source.extract_dir)[0:3:2]:
            paths = [os.path.join(root, f) for f in files]
            self.files_by_tag[source.tag].extend(paths)
        self.log.debug('Loaded %d files',
                       len(self.files_by_tag[source.tag]))

    def filelist(self, container=None):
        if container and not container in self.containers:
            raise ValueError('SourcesDataSource: bad package: '
                             + container)
        if container:
            self._load_files(container)
            return self.files_by_tag[container]
        all_ = []
        for key in self.files_by_tag.iterkeys():
            self._load_files(key)
            all_.extend(self.files_by_tag[key])
        return all_

    def get(self, tag=None):
        ''' Return Source object bound to a Source/patch tag '''
        if not tag:
            tag = 'Source0'
            self.log.warning('Retrieving default source as Source0')
        if not tag in self.sources_by_tag.iterkeys():
            return None
        return self.sources_by_tag[tag]

    def get_keys(self):
        return self.sources_by_tag.iterkeys()

    def get_files_sources(self):
        ''' Compatibility, to be removed. '''
        self.log.warning('SourcesDataSource: calling get_files_sources')
        return self.filelist()


# vim: set expandtab: ts=4:sw=4:
