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

import os.path
import shutil

from settings import Settings


class ReviewDirs(object):
    SRPM_SRC          = 'review/srpm'
    SRPM_UNPACKED     = 'review/srpm-unpacked'
    UPSTREAM          = 'review/upstream'
    UPSTREAM_UNPACKED = 'review/upstream-unpacked'

    @staticmethod
    def get_dir(dir, keep_old=False):
        dir = os.path.abspath(dir)
        if os.path.exists(dir) and not keep_old:
            Settings.get_logger().debug("Clearing temp dir: " + dir)
            shutil.rmtree(dir)
        os.makedirs(dir)
        return dir

    @staticmethod
    def root():
        return os.path.abspath('.')

    @staticmethod
    def report_path(name):
        return os.path.abspath('./%s-review.txt' % name)



# vim: set expandtab: ts=4:sw=4:
