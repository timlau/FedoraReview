#-*- coding: UTF-8 -*-

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
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
# (C) 2011 - Tim Lauridsen <timlau@fedoraproject.org>
'''
Tools for helping Fedora package reviewers
'''
import re
from bugzilla import Bugzilla

BZ_URL = 'https://bugzilla.redhat.com/xmlrpc.cgi'

from reviewtools import Helpers, get_logger


class ReviewBug(Helpers):
    """ This class handles interaction with bugzilla.
    """

    def __init__(self, bug, user=None, password=None, cache=False,
                nobuild=False, other_BZ=None):
        """ Constructord.
        :arg bug, the bug number on bugzilla
        :kwarg user, the username with which to log in in bugzilla.
        :kwarg password, the password associated with this account.
        :kwarg cache, boolean specifying whether the spec and srpm should
        be re-downloaded or not.
        :kwarg nobuild, boolean specifying whether to build or not the
        package.
        :kwarg other_BZ, url of an eventual other bugzilla system.
        """
        Helpers.__init__(self, cache, nobuild)
        self.bug_num = bug
        self.spec_url = None
        self.srpm_url = None
        self.spec_file = None
        self.srpm_file = None
        self.log = get_logger()
        if other_BZ:
            self.bugzilla = Bugzilla(url=other_BZ + '/xmlrpc.cgi')
        else:
            self.bugzilla = Bugzilla(url=BZ_URL)
        self.is_login = False
        if user and password:
            rc = self.bugzilla.login(user=user, password=password)
            if rc > 0:
                self.log.info("You are logged in to bugzilla")
                self.is_login = True
        self.user = user
        self.bug = self.bugzilla.getbug(self.bug_num)

    def login(self, user, password):
        """ Handles the login of the user into bugzilla.
        :arg user, the bugzilla username.
        :arg password, the bugzilla password associated with the given
        username.
        """
        if self.bugzilla.login(user=user, password=password) > 0:
            self.is_login = True
            self.user = user
        else:
            self.is_login = False
        return self.is_login

    def find_urls(self):
        """ Reads the page on bugzilla, search for all urls and extract
        the last urls for the spec and the srpm.
        """
        found = True
        if self.bug.longdescs:
            for cat in self.bug.longdescs:
                body = cat['body']
                #self.log.debug(body)
                urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|\
[$-_@.&+~]|[!*\(\),]|(?:%[0-9a-fA-F~\.][0-9a-fA-F]))+', body)
                if urls:
                    for url in urls:
                        if ".spec" in url:
                            self.spec_url = url
                        elif ".src.rpm" in url:
                            self.srpm_url = url
        if not self.spec_url:
            self.log.info('not spec file URL found in bug #%s' % self.bug_num)
            found = False
        if not self.srpm_url:
            self.log.info('not SRPM file URL found in bug #%s' % self.bug_num)
            found = False
        return found

    def assign_bug(self):
        """ Assign the bug to the reviewer.
        """
        if self.is_login:
            self.bug.setstatus('ASSIGNED')
            self.bug.setassignee(assigned_to=self.user)
            self.bug.addcomment('I will review this package')
            flags = {'fedora-review': '?'}
            self.bug.updateflags(flags)
            self.bug.addcc([self.user])
        else:
            self.log.info("You need to login before assigning a bug")

    def add_comment(self, comment):
        """ Add a given comment to the bugzilla page.
        :arg comment, the comment to be added to the page.
        """
        if self.is_login:
            self.bug.addcomment(comment)
        else:
            self.log.info("You need to is_login before commenting on a bug")

    def add_comment_from_file(self, fname):
        """ Add the content from a file as comment.
        :arg fname, the filename from which the content is added as
        comment on the bug.
        """
        stream = open(fname, "r")
        lines = stream.readlines()
        stream.close
        self.add_comment("".join(lines))

    def download_files(self):
        """ Download the spec file and srpm extracted from the bug
        report.
        """
        if not self.cache:
            self.log.info('Downloading .spec and .srpm files')
        found = True
        if not self.spec_url or not self.srpm_url:
            found = self.find_urls()
        if found and self.spec_url and self.srpm_url:
            self.spec_file = self._get_file(self.spec_url)
            self.srpm_file = self._get_file(self.srpm_url)
            if self.spec_file and self.srpm_file:
                return True
        return False
