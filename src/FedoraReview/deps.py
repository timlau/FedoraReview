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

''' Interface to package dependencies. '''

import subprocess
try:
    from subprocess import check_output          # pylint: disable=E0611
except ImportError:
    from FedoraReview.el_compat import check_output

from settings import Settings


def list_deps(pkgs):
    ''' Return list of all dependencies for named packages. '''

    if not pkgs:
        return []
    if not isinstance(pkgs, list):
        pkgs = [pkgs]
    cmd = ['repoquery', '-C', '--requires', '--resolve']
    cmd.extend(pkgs)
    Settings.get_logger().debug("Running: " + ' '.join(cmd))
    try:
        yum = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    except OSError:
        Settings.get_logger().warning("Cannot run " + " ".join(cmd))
        return []
    deps = []
    while True:
        try:
            line = yum.stdout.next().strip()
        except StopIteration:
            return list(set(deps))
        name = line.rsplit('.', 2)[0]
        deps.append(name.rsplit('-', 2)[0])


def resolve(reqs):
    ''' Return the packages providing the reqs symbols. '''

    if not reqs:
        return []
    if not isinstance(reqs, list):
        reqs = [reqs]
    cmd = ['repoquery', '-C', '--whatprovides']
    cmd.extend(reqs)
    Settings.get_logger().debug("Running: " + ' '.join(cmd))
    try:
        yum = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    except OSError:
        Settings.get_logger().warning("Cannot run " + " ".join(cmd))
        return []
    pkgs = []
    while True:
        try:
            line = yum.stdout.next().strip()
        except StopIteration:
            return list(set(pkgs))
        pkg = line.rsplit('.', 2)[0]
        pkgs.append(pkg.rsplit('-', 2)[0])


def list_dirs(pkg_filename):
    ''' Return list of directories in local pkg. '''

    cmd = ['rpm', '-ql', '--dump', '-p', pkg_filename]
    try:
        rpm = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    except OSError:
        Settings.get_logger().warning("Cannot run " + " ".join(cmd))
        return []
    dirs = []
    while True:
        try:
            line = rpm.stdout.next().strip()
        except StopIteration:
            return dirs
        path, mode = line.split()[0:5:4]
        mode = int(mode, 8)
        if mode & 040000:
            dirs.append(path)


def list_owners(paths):
    ''' Return list of packages owning paths (single path or list).'''
    if not paths:
        return []
    if not isinstance(paths, list):
        paths = [paths]

    owners = []
    paths_to_exam = list(paths)
    for i in range(len(paths)):
        p = subprocess.Popen(['rpm', '--qf', '%{NAME}\n', '-qf', paths[i]],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        path_owners = p.communicate()[0].split()
        if p.returncode != 0:
            continue
        path_owners = [p.strip() for p in path_owners]
        if path_owners and path_owners[0]:
            path_owners = [p for p in path_owners
                               if not p.startswith('error:')]
        if not path_owners or not path_owners[0]:
            continue
        paths_to_exam.remove(paths[i])
        owners.extend(path_owners)
    for path in paths_to_exam:
        cmd = ['repoquery', '-C', '-qf', path]
        Settings.get_logger().debug("Running: " + ' '.join(cmd))
        try:
            lines = check_output(cmd).split()
            lines = [l.strip() for l in lines]
            if not lines or not lines[0]:
                continue
            lines = [l.rsplit('.', 2)[0] for l in lines]
            lines = [l.rsplit('-', 2)[0] for l in lines]
            owners.extend(list(set(lines)))
        except subprocess.CalledProcessError:
            Settings.get_logger().error("Cannot run " + " ".join(cmd))
            return owners
    return owners


def list_paths(pkgs):
    ''' Return list of all files in pkgs (single name or list). '''
    if not pkgs:
        return []
    cmd = ['repoquery', '-C', '-l']
    if isinstance(pkgs, list):
        cmd.extend(pkgs)
    else:
        cmd.append(pkgs)
    Settings.get_logger().debug("Running: " + ' '.join(cmd))
    try:
        Settings.get_logger().debug("Running: " + ' '.join(cmd))
        paths = check_output(cmd)
    except OSError:
        Settings.get_logger().warning("Cannot run repoquery")
        return []
    return paths.split()


class Deps:
    ''' Models the dependencies. '''

    def get_spec(self, pkg):
        ''' Return a Spec object for a given dependency pkg.'''
        pass


# vim: set expandtab ts=4 sw=4:
