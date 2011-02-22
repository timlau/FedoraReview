#!/usr/bin/python -tt
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

BZ_URL='https://bugzilla.redhat.com/xmlrpc.cgi'

from reviewtools import Helpers, get_logger

class ReviewBug(Helpers):
    def __init__(self,bug,user=None,password=None):
        self.bug_num = bug
        self.spec_url = None
        self.srpm_url = None
        self.spec_file = None
        self.srpm_file = None
        self.bugzilla = Bugzilla(url=BZ_URL)
        self.is_login = False
        if user and password:
            rc = self.bugzilla.login(user=user, password=password)
            if rc > 0:
                self.is_login = True
        self.user = user
        self.bug = self.bugzilla.getbug(self.bug_num)
        self.log = get_logger()

    def login(self, user, password):
        if self.bugzilla.login(user=user, password=password) > 0:
            self.is_login = True
            self.user = user
        else:
            self.is_login = False
        return self.is_login

    def find_urls(self):
        found = True
        if self.bug.longdescs:
            for c in self.bug.longdescs:
                body = c['body']
                #self.log.debug(body)
                urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+~]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', body)
                if urls:
                    for url in urls:
                        if url.endswith(".spec"):
                            self.spec_url = url
                        elif url.endswith(".src.rpm"):
                            self.srpm_url = url
        if not self.spec_url:
            self.log.info('not spec file URL found in bug #%s' % self.bug_num)
            found = False
        if not self.srpm_url:
            self.log.info('not SRPM file URL found in bug #%s' % self.bug_num)
            found = False
        return found
            
            

    def assign_bug(self):    
        if self.is_login:
            self.bug.setstatus('ASSIGNED')
            self.bug.setassignee(assigned_to=self.user)
            self.bug.addcomment('I will review this bug')
            flags = {'fedora-review' : '?'}
            self.bug.updateflags(flags)
            self.bug.addcc([self.user])
        else:
            self.log.info("You need to login before assigning a bug")

    def add_comment(self,comment):    
        if self.is_login:
            self.bug.addcomment(comment)
        else:
            self.log.info("You need to is_login before commenting on a bug")

    def add_comment_from_file(self,fname):
        fd = open(fname,"r")
        lines = fd.readlines()
        fd.close
        self.add_comment("".join(lines))
                            
    def download_files(self):
        found = True
        if not self.spec_url or not self.srpm_url:
            found = self.find_urls()
        if found and self.spec_url and self.srpm_url:
            self.spec_file = self._get_file(self.spec_url)
            self.srpm_file = self._get_file(self.srpm_url)
            if self.spec_file and self.srpm_file:
                return True
        return False

    
