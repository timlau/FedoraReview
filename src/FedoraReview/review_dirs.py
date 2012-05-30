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
import os
import os.path
import shutil
import logging

SRPM              = 'srpm'
SRPM_UNPACKED     = 'srpm-unpacked'
UPSTREAM          = 'upstream'
UPSTREAM_UNPACKED = 'upstream-unpacked'

class _ReviewDirs(object):

    def __init__(self):
        self.startdir = os.getcwd()

    def report_path(self, name):
        return os.path.abspath('./%s-review.txt' % name)

    def workdir_setup(self, wd, keep_data=False, force=False):
        if not keep_data and not force and os.path.exists(wd):
            d = ''.join(wd.split(os.getcwd(), 1))
            print "The directory %s in in the way, please remove" % d
            raise CleanExitError("Cannot create review directory")
        wd = os.path.abspath(wd)
        if hasattr(self, 'wd'):
            if self.wd != wd and not force:
               logging.debug('Attempt to create new working dir ' +
                              wd + ' in existing dir ' + self.wd)
               return
        if os.path.exists(wd) and not keep_data:
            logging.info("Clearing old review directory: " + wd)
            shutil.rmtree(wd)
            os.mkdir(wd)
        if not os.path.exists(wd):
            os.mkdir(wd)
        os.chdir(wd)
        logging.info("Using review directory: " + wd)
        self.wd = wd
        for d in [UPSTREAM, UPSTREAM_UNPACKED, SRPM, SRPM_UNPACKED]:
            if not os.path.exists(d):
                os.mkdir(d)

    is_inited = property(lambda self: hasattr(self, 'wd'))
    root = property(lambda self: self.wd)

    srpm = property(lambda self: os.path.join(self.wd, SRPM))
    srpm_unpacked = property(lambda self: os.path.join(self.wd, 
                                                       SRPM_UNPACKED))
    upstream = property(lambda self: os.path.join(self.wd, UPSTREAM))
    upstream_unpacked = property(lambda self: 
                                     os.path.join(self.wd, 
                                                  UPSTREAM_UNPACKED))

ReviewDirs = _ReviewDirs()

# vim: set expandtab: ts=4:sw=4:
