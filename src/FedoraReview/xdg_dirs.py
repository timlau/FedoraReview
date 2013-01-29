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


class _XdgDirs(object):
    ''' Methods to retrieve XDG standard paths. '''

    APPNAME = 'fedora-review'

    def _get_dir(self, path, app_dir=False):
        ''' Return a dir, create if not existing. '''
        if app_dir:
            path = os.path.join(path, self.APPNAME)
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    def get_configdir(self, app_dir=False):
        ''' Return XDG config dir, with possible app dir appended. '''
        if 'XDG_CONFIG_HOME' in os.environ:
            path = os.environ['XDG_CONFIG_HOME']
        else:
            path = os.path.expanduser('~/.config')
        return self._get_dir(path, app_dir)

    def get_cachedir(self, app_dir=False):
        ''' Return XDG cache dir, with possible app dir appended. '''
        if 'XDG_CACHE_HOME' in os.environ:
            path = os.environ['XDG_CACHE_HOME']
        else:
            path = os.path.expanduser('~/.cache')
        return self._get_dir(path, app_dir)

    def get_datadir(self, app_dir=False):
        ''' Return XDG data dir, with possible app dir appended. '''
        if 'XDG_DATA_HOME' in os.environ:
            path = os.environ['XDG_DATA_HOME']
        else:
            path = os.path.expanduser('~/.local/share')
        return self._get_dir(path, app_dir)

    datadir = property(lambda self: self.get_datadir())
    cachedir = property(lambda self: self.get_cachedir())
    configdir = property(lambda self: self.get_configdir())

    app_datadir = property(lambda self: self.get_datadir(True))
    app_cachedir = property(lambda self: self.get_cachedir(True))
    app_configdir = property(lambda self: self.get_configdir(True))


XdgDirs = _XdgDirs()


# vim: set expandtab ts=4 sw=4:
