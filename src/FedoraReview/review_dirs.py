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
import tempfile

from FedoraReview.review_error import FedoraReviewError
from FedoraReview.settings     import Settings

SRPM              = 'srpm'
SRPM_UNPACKED     = 'srpm-unpacked'
UPSTREAM          = 'upstream'
UPSTREAM_UNPACKED = 'upstream-unpacked'
RESULTS           = 'results'


class ResultDirNotEmptyError(FedoraReviewError):
    ''' Thrown when trying to reuse old review dir without --cache. '''
    def __init__(self):
        FedoraReviewError.__init__(self, 'resultdir not empty')


class ReviewDirExistsError(FedoraReviewError):
    ''' The review dir is already in place. '''
    def __init__(self, path):
        FedoraReviewError.__init__(self, os.path.abspath(path))


class ReviewDirChangeError(FedoraReviewError):
    ''' Attempt to change directory already set. '''
    pass


class _ReviewDirs(object):
    ''' Wraps the review directory and it's paths. '''

    WD_DIRS = [UPSTREAM, UPSTREAM_UNPACKED, SRPM, SRPM_UNPACKED, RESULTS]

    def __init__(self):
        self.startdir = os.getcwd()
        self.wdir = None

    def reset(self, startdir=None):
        ''' Clear persistent state (test tool). '''
        self.wdir = None
        if startdir:
            self.startdir = startdir

    @staticmethod
    def report_path(name):
        ''' Return path for report. '''
        return os.path.abspath('./%s-review.txt' % name)

    def _create_and_copy_wd(self, wd, reuse_old):
        ''' Create wd, possibly filled with cached data. '''
        if os.path.exists(wd) and not reuse_old:
            if Settings.cache:
                cache = tempfile.mkdtemp(dir='.')
                for d in self.WD_DIRS:
                    shutil.move(os.path.join(wd, d), cache)
                try:
                    buildlink = os.readlink('BUILD')
                except  OSError:
                    buildlink = None
            logging.info("Clearing old review directory: " + wd)
            shutil.rmtree(wd)
            os.mkdir(wd)
            if Settings.cache:
                for d in self.WD_DIRS:
                    shutil.move(os.path.join(cache, d), wd)
                    if buildlink:
                        shutil.symlink(buildlink, 'BUILD')
                shutil.rmtree(cache)
        if not os.path.exists(wd):
            os.mkdir(wd)

    def workdir_setup(self, wd, reuse_old=False):
        ''' Initiate a new review directory, or re-use an old one. '''
        reuse = reuse_old or Settings.cache
        if not reuse and os.path.exists(wd):
            d = ''.join(wd.split(os.getcwd(), 1))
            raise ReviewDirExistsError(d)
        wd = os.path.abspath(wd)
        if self.wdir:
            if self.wdir != wd and not reuse_old:
                raise ReviewDirChangeError('Old dir ' + self.wdir +
                                           ' new dir: ' + wd)
        self._create_and_copy_wd(wd, reuse_old)
        os.chdir(wd)
        logging.info("Using review directory: " + wd)
        self.wdir = wd
        for d in self.WD_DIRS:
            if not os.path.exists(d):
                os.mkdir(d)

    is_inited = property(lambda self: bool(self.wdir))
    root = property(lambda self: self.wdir)

    srpm = property(lambda self: os.path.join(self.wdir, SRPM))
    srpm_unpacked = property(lambda self: os.path.join(self.wdir,
                                                       SRPM_UNPACKED))
    upstream = property(lambda self: os.path.join(self.wdir, UPSTREAM))
    upstream_unpacked = property(lambda self:
                                     os.path.join(self.wdir,
                                                  UPSTREAM_UNPACKED))
    results = property(lambda self: os.path.join(self.wdir, RESULTS))

ReviewDirs = _ReviewDirs()

# vim: set expandtab: ts=4:sw=4:
