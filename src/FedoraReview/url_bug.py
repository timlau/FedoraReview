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

import FedoraReview
from FedoraReview import Helpers, Settings
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

    def _find_urls_by_label(self):
        """ locate urls based on labels like 'spec url:' or
        'srpm:' Not pretty. :(
        """
        tmpfile, properties = urllib.urlretrieve(self.bug_url)
        soup=BeautifulSoup(open(tmpfile))
        regex1 = re.compile('srpm[ url]*:\s*$',re.I)
        regex2 = re.compile('spec[ url]*:\s*$',re.I)
        links1 = soup.findAll(text=regex1)[-1].parent.findAll('a')
        links2 = soup.findAll(text=regex2)[-1].parent.findAll('a')
        link1=links1[-1]['href'].__str__().encode('ascii', 'ignore')
        link2=links1[-2]['href'].__str__().encode('ascii', 'ignore')
        if len(links1) == len(links2) and len(links2) > 1:
             # OK, We have two labels with a common parent and links.
             # we have no idea which link is what, size gives a hint:
             f1 = urllib2.urlopen(link1)
             f2 = urllib2.urlopen(link2)
             size1 = int(f1.info().getheader('content-length'))
             size2 = int(f2.info().getheader('content-length'))
             if size2 < 40000 and size1 > 40000:
                  self.srpm_url = link1
                  self.spec_url = link2
             elif size2 > 40000 and size1 < 40000:
                  self.srpm_url = link2
                  self.spec_url = link1
             else:
                  log.debug( "Bad sizes, 1: %d, 2: %d" % (size1, size2),
                             exc_info=True)
                  raise UrlBugException(
                               "Can't find srpm and/or spec links")
        else:
            log.debug( "find_urls_by_label: No matching links...")
            raise UrlBugException("Can't find srpm and/or spec links")

    def _find_urls_by_name(self):
        """ Locate url based on links ending in .src.rpm and .spec.
        """
        tmpfile, properties = urllib.urlretrieve(self.bug_url)
        soup=BeautifulSoup(open(tmpfile))
        links=soup.findAll('a')
        links = filter(lambda l: l.has_key('href'), links)
        hrefs = map(lambda l: l['href'],  links)
        for href in reversed(hrefs):
            href = href.encode('ascii', 'ignore')
            if '?' in href:
                href = href[0: href.find('?')]
            if not self.srpm_url and href.endswith('.src.rpm'):
                self.srpm_url = href
            elif not  self.spec_url and href.endswith('.spec'):
                self.spec_url = href

        if not self.spec_url:
           raise UrlBugException('Cannot find spec file URL')
        if not self.srpm_url:
           raise UrlBugException('Cannot find source rpm URL')

    def do_find_urls(self):
        """ Retrieve the page and parse for srpm and spec url. """
        try:
            self._find_urls_by_name()
        except:
            self._find_urls_by_label()
        return True

    def get_location(self):
        return self.bug_url

    def check_options(self):
        bad_opts = AbstractBug.BZ_OPTIONS
        bad_opts.extend( ['prebuilt'])
        AbstractBug.do_check_options(self, '--url', bad_opts)


# vim: set expandtab: ts=4:sw=4:
