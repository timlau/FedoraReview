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
Tools handling resources identified with an url (download only).
No xmlrpc involved, for better or worse.
'''
import os.path
import urllib

from BeautifulSoup import BeautifulSoup

from abstract_bug import AbstractBug


class UrlBug(AbstractBug):
    """ This class handles interaction html web pages, by url.
    """

    def __init__(self, url):
        """ Constructor.
        :arg url, complete url to bug
        """
        AbstractBug.__init__(self)
        self.check_options()
        self.bug_url = url
        if not url.startswith('http'):
            self.bug_url = os.path.normpath(self.bug_url)

    def _find_urls_by_ending(self, pattern):
        """ Locate url based on links ending in .src.rpm and .spec.
        """
        if self.bug_url.startswith('file://'):
            tmpfile = self.bug_url.replace('file://', '')
        else:
            tmpfile = urllib.urlretrieve(self.bug_url)[0]
        soup = BeautifulSoup(open(tmpfile))
        links = soup.findAll('a')
        hrefs = map(lambda l: l['href'], links)
        found = []
        for href in reversed(hrefs):
            href = href.encode('ascii', 'ignore')
            if '?' in href:
                href = href[0: href.find('?')]
            if href.endswith(pattern):
                found.append(href)
        return found

    def find_srpm_url(self):
        urls = self._find_urls_by_ending('.src.rpm')
        if len(urls) == 0:
            raise self.BugError('Cannot find source rpm URL')
        self.srpm_url = urls[0]

    def find_spec_url(self):
        urls = self._find_urls_by_ending('.spec')
        if len(urls) == 0:
            raise self.BugError('Cannot find spec file URL')
        self.spec_url = urls[0]

    def get_location(self):
        return self.bug_url

    def check_options(self):                     # pylint: disable=R0201
        ''' Raise error if Settings  combination is invalid. '''
        AbstractBug.do_check_options('--url', ['prebuilt', 'other_bz'])


# vim: set expandtab: ts=4:sw=4:
