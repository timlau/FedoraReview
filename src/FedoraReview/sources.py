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
import glob

from source import Source
from settings import Settings


class Sources(object):
    """ Container for Source objects, reflecting SourceX: lines
    int the spec file.
    """

    def __init__(self, spec):
        self.log = Settings.get_logger()
        self._sources_files = None
        self._sources = {}
        for tag, url in spec.get_sources('Source').iteritems():
            self.add(tag, url)


    def add(self, tag, url):
        """Add a new Source Object based on spec tag and URL to source"""
        source = Source(self, tag, url)
        self._sources[tag] = source
        if source.local:
            print 'The source %s in the srpm can not be retrieved. '\
            'This is a corner case not supported yet.' % url

    def get(self, tag):
        """ Get a single Source object"""
        if tag in self._sources:
            return self._sources[tag]
        else:
            return None

    def get_all(self):
        """ Get all source objects """
        return [self._sources[s] for s in self._sources]

    def extract_all(self):
        """ Extract all sources which are detected can be extracted based
        on their extension.
        """
        for source in self._sources.values():
            source.extract()

    def extract(self, source_url=None, source_filename=None):
        """ Extract the source specified by its url or filename.
        :arg source_url, the url used in the spec as used in the spec
        :arg souce_filename, the filename of the source as identified
        in the spec.
        """
        if source_url is None and source_filename is None:
            print 'No source set to extract'
        for source in self._sources:
            if source_url and source.URL == source_url:
                source.extract()
            elif source_filename and source.filename == source_filename:
                source.extract()

    def get_files_sources(self):
        """ Return the list of all files found in the sources. """
        if self._sources_files:
            return self._sources_files
        try:
            self.extract_all()
        except  OSError as error:
            print "Source", error
            self._source_files = []
            return []
        sources_files = []
        for source in self._sources.values():
            # If the sources are not extracted then we add the source itself
            if not source.extract_dir:
                self.log.debug('%s cannot be extracted, adding as such \
as sources' % source.filename)
                sources_files.append(source.filename)
            else:
                self.log.debug('Adding files found in %s' % source.filename)
                for root, subFolders, files in os.walk(source.extract_dir):
                    for filename in files:
                        sources_files.append(os.path.join(root, filename))
        self._sources_files = sources_files
        return sources_files


# vim: set expandtab: ts=4:sw=4:
