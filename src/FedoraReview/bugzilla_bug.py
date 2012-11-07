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

from url_bug import UrlBug
from settings import Settings
from abstract_bug import AbstractBug


class BugzillaBug(UrlBug):
    ''' Bugzilla handling, a special case of the url_bug case. '''

    def __init__(self, bug):
        """ Constructor.
        :arg bug, the bug number on bugzilla
        """
        self.check_options()
        self.bug_num = bug
        url = os.path.join(Settings.current_bz_url,
                           'show_bug.cgi?id=' + str(bug))
        UrlBug.__init__(self, url)

    def get_location(self):
        return Settings.bug

    def get_dirname(self, prefix=''):
        ''' Return dirname to be used for this bug. '''
        if self.get_name() != '?':
            return self.bug_num + '-' + self.get_name()
        else:
            return self.bug_num

    def check_options(self):                    # pylint: disable=R0201
        ''' Raise SettingsError if Settings combinations is invalid. '''
        AbstractBug.do_check_options('--bug', ['prebuilt'])


# vim: set expandtab: ts=4:sw=4:
