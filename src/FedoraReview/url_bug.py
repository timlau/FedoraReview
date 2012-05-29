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
import logging
import os.path
import re
import shutil
import urllib2
import urllib

from BeautifulSoup import BeautifulSoup

from helpers import Helpers
from settings import Settings
from abstract_bug import AbstractBug, SettingsError


class UrlBugException(Exception):
    pass

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
        tmpfile, properties = urllib.urlretrieve(self.bug_url)
        soup=BeautifulSoup(open(tmpfile))
        links=soup.findAll('a')
        links = filter(lambda l: l.has_key('href'), links)
        hrefs = map(lambda l: l['href'],  links)
        found = []
        for href in reversed(hrefs):
            href = href.encode('ascii', 'ignore')
            if '?' in href:
                href = href[0: href.find('?')]
            if href.endswith(pattern):
                found.append(href)
        return found

    def find_srpm_url(self):
        urls = self.find_urls('.src.rpm')
        if len(urls) == 0:
           raise UrlBugException('Cannot find source rpm URL')
        self.srpm_url = urls[0]

    def find_spec_url(self):
        urls = self.find_urls('.spec')
        if len(urls) == 0:
           raise UrlBugException('Cannot find spec file URL')
        self.spec_url = urls[0]

    def get_location(self):
        return self.bug_url

    def check_options(self):
        bad_opts = AbstractBug.BZ_OPTIONS
        bad_opts.extend( ['prebuilt'])
        AbstractBug.do_check_options(self, '--url', bad_opts)


# vim: set expandtab: ts=4:sw=4:
