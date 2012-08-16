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

'''
python interface to XDG directories, implemented as-needed.
'''

import os
import os.path
import logging

class _XdgDirs(object):
    APPNAME = 'fedora-review'

    def _get_dir(self, path, app_dir=False):
        if app_dir:
            path = os.path.join(path, self.APPNAME)
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    def _configdir(self, app_dir=False):
        if 'XDG_CONFIG_HOME' in os.environ:
            path = os.environ['XDG_CONFIG_HOME']
        else:
            path = os.path.expanduser('~/.config')
        return self._get_dir(path, app_dir)

    def _cachedir(self, app_dir=False):
        if 'XDG_CACHE_HOME' in os.environ:
            path = os.environ['XDG_CACHE_HOME']
        else:
            path = os.path.expanduser('~/.cache')
        return self._get_dir(path, app_dir)

    def _datadir(self, app_dir=False):
        if 'XDG_DATA_HOME' in os.environ:
            path = os.environ['XDG_DATA_HOME']
        else:
            path = os.path.expanduser('~/.local/share')
        return self._get_dir(path, app_dir)

    datadir = property(lambda self: self._datadir())
    cachedir = property(lambda self: self._cachedir())
    configdir = property(lambda self: self._configdir())

    app_datadir = property(lambda self: self._datadir(True))
    app_cachedir = property(lambda self: self._cachedir(True))
    app_configdir = property(lambda self: self._configdir(True))

XdgDirs = _XdgDirs()



# vim: set expandtab: ts=4:sw=4:
