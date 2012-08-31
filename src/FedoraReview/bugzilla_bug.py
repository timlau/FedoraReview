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
import re

from bugzilla import Bugzilla

from settings import Settings
from abstract_bug import AbstractBug, BugException


class BugzillaBug(AbstractBug):
    """ This class handles interaction with bugzilla using
    xmlrpc.
    """

    def __init__(self, bug, user=None, password=None):
        """ Constructor.
        :arg bug, the bug number on bugzilla
        :kwarg user, the username with which to log in in bugzilla.
        :kwarg password, the password associated with this account.
        """
        AbstractBug.__init__(self)
        self.check_options()
        self.bug_num = bug
        bz_url = os.path.join(Settings.current_bz_url, 'xmlrpc.cgi')
        self.bugzilla = Bugzilla(url=bz_url)

        self.log.info("Trying bugzilla cookies for authentication")
        self.user = user
        self.bug = self.bugzilla.getbug(self.bug_num)

    def _find_urls(self):
        """ Reads the page on bugzilla, search for all urls and extract
        the last urls for the spec and the srpm.
        """
        urls = []
        if self.bug.longdescs:
            for cat in self.bug.longdescs:
                body = cat['body']

                # workaround for bugzilla/xmlrpc bug. When comment
                # text is pure number it converts to number type (duh)
                if type(body) != str and type(body) != unicode:
                    continue
                urls.extend(re.findall('(?:ht|f)tp[s]?://'
                    '(?:[a-zA-Z]|[0-9]|[$-_@.&+~]|[!*\(\),]|'
                    '(?:%[0-9a-fA-F~\.][0-9a-fA-F]))+', body))
        return urls

    def find_spec_url(self):
        urls = self._find_urls()
        urls = filter(lambda u: '.spec' in u, urls)
        if len(urls) == 0:
            raise BugException (
                 'No spec file URL found in bug #%s' % self.bug_num)
        url = urls[-1]
        self.spec_url = url

    def find_srpm_url(self):
        urls = self._find_urls()
        urls = filter(lambda u: '.src.rpm' in u, urls)
        if len(urls) == 0:
            raise BugException (
                 'No srpm file URL found in bug #%s' % self.bug_num)
        url = urls[-1]
        self.srpm_url = url

    def get_location(self):
        return Settings.bug

    def get_dirname(self):
        ''' Return dirname to be used for this bug. '''
        if self.get_name() != '?':
            return self.bug_num + '-' + self.get_name()
        else:
            return self.bug_num

    def check_options(self):
        AbstractBug.do_check_options(self, '--bug', ['prebuilt'])

    def handle_xmlrpc_err(self, exception):
        self.log.error("Server error: %s" % str(exception))


# vim: set expandtab: ts=4:sw=4:
