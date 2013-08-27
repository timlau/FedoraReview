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


class ReviewError(Exception):
    """ General Error class for fedora-review. It always terminates
        the session, possibly writing a message before exiting.
    """

    def __init__(self, value, exitcode=1, silent=False):
        Exception.__init__(self, value)
        self.value = value
        self.exitcode = exitcode
        self.silent = silent
        self.show_logs = True

    def __str__(self):
        """ Represent the error. """
        return repr(self.value)


class SpecParseReviewError(ReviewError):
    ''' Thrown at an early stage, no spec available. '''
    pass


# vim: set expandtab ts=4 sw=4:
