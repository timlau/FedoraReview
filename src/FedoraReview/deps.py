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

''' Interface to package dependencies using packagekit, yum and rpm. '''
#
# See: http://www.packagekit.org/gtk-doc/index.html
# See: https://github.com/tseliot/ubuntu-drivers-common
#

# pylint: disable=E0611,W0611,F0401
from gi.repository import PackageKitGlib as PackageKit

import subprocess
try:
    from subprocess import check_output
except ImportError:
    from FedoraReview.el_compat import check_output

# pylint: enable=E0611,W0611,F0401

from settings import Settings

_id_by_name = {}


def _resolve(pk, name):
    ''' Resolve a package name into a packagekit id. '''
    if not name in _id_by_name:
        pk = PackageKit.Client()
        results = pk.resolve(PackageKit.FilterEnum.NONE,
                             [name],
                             None,
                             lambda p, t, d: True,
                             None)
        if results.get_exit_code() != PackageKit.ExitEnum.SUCCESS:
            Settings.get_logger().warning("Cannot resolve: " + name)
            return None
        pkgs = results.get_package_array()
        _id_by_name[name] = pkgs[0].get_id() if pkgs else None
    return _id_by_name[name]


def init():
    ''' Setup module for subsequent calls. '''
    # pk.refresh_cache would be better, but requires privileges.
    # Might be solvable, see
    # https://bugs.launchpad.net/ubuntu/+source/packagekit/+bug/1008106
    try:
        check_output(['yum', 'makecache'])
    except subprocess.CalledProcessError:
        Settings.get_logger().warning(
                            "Cannot run yum makecache, trouble ahead")


def list_deps(pkgs):
    ''' Return list of all dependencies for named packages. '''

    if not pkgs:
        return []
    if not isinstance(pkgs, list):
        pkgs = [pkgs]
    pk = PackageKit.Client()
    ids = [_resolve(pk, pkg) for pkg in pkgs]
    result = pk.get_depends(PackageKit.FilterEnum.NONE,
                            ids,
                            False,
                            None,
                            lambda p, t, d: True,
                            None)
    if result.get_exit_code() != PackageKit.ExitEnum.SUCCESS:
        Settings.get_logger().warning("Cannot run get_requires")
        return []
    pkgs = result.get_package_array()
    return list(set([p.get_name() for p in pkgs]))


def resolve(reqs):
    ''' Return the packages providing the reqs symbols. '''

    if not reqs:
        return []
    if not isinstance(reqs, list):
        reqs = [reqs]
    pk = PackageKit.Client()
    results = pk.what_provides(PackageKit.FilterEnum.NONE,
                               PackageKit.ProvidesEnum.ANY,
                               reqs,
                               None,
                               lambda p, t, d: True,
                               None)
    if results.get_exit_code() != PackageKit.ExitEnum.SUCCESS:
        Settings.get_logger().warning("Cannot run what_provides")
        return []
    pkgs = results.get_package_array()
    pkgs = list(set([p.get_name() for p in pkgs]))
    return pkgs


def listpaths(pkg_filename):
    ''' Return lists of files and dirs in local pkg. '''

    cmd = ['rpm', '-ql', '--dump', '-p', pkg_filename]
    try:
        rpm = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    except OSError:
        Settings.get_logger().warning("Cannot run " + " ".join(cmd))
        return []
    files = []
    dirs = []
    while True:
        try:
            line = rpm.stdout.next().strip()
        except StopIteration:
            return dirs, files
        path, mode = line.split()[0:5:4]
        mode = int(mode, 8)
        if mode & 040000:
            dirs.append(path)
        else:
            files.append(path)


def list_dirs(pkg_filename):
    ''' Return list of directories in local pkg matching mode. '''
    return listpaths(pkg_filename)[0]


def list_owners(paths):
    ''' Return list of packages owning paths (single path or list).'''
    if not paths:
        return []
    if not isinstance(paths, list):
        paths = [paths]
    pk = PackageKit.Client()
    results = pk.search_files(PackageKit.FilterEnum.NONE,
                              paths,
                              None,
                              lambda p, t, d: True,
                              None)
    if results.get_exit_code() != PackageKit.ExitEnum.SUCCESS:
        Settings.get_logger().warning("Cannot run search_files")
        return []
    pkgs = results.get_package_array()
    return [p.get_name() for p in pkgs]


def list_paths(pkgs):
    ''' Return list of all files in pkgs (single name or list). '''
    if not pkgs:
        return []
    if not isinstance(pkgs, list):
        pkgs = [pkgs]
    pk = PackageKit.Client()
    ids = [_resolve(pk, pkg) for pkg in pkgs]
    result = pk.get_files(ids,
                          None,
                          lambda p, t, d: True,
                          None)
    if result.get_exit_code() != PackageKit.ExitEnum.SUCCESS:
        Settings.get_logger().warning("Cannot run get_files")
        return []
    paths = []
    for f in result.get_files_array():
        paths.extend(f.get_property('files'))
    return paths


class Deps:
    ''' Models the dependencies. '''

    def get_spec(self, pkg):
        ''' Return a Spec object for a given dependency pkg.'''
        pass


# vim: set expandtab ts=4 sw=4:
