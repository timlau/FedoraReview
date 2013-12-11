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
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#    MA  02110-1301 USA.
#
# pylint: disable=C0103,R0904,R0913,W0212
# (C) 2011 - Tim Lauridsen <timlau@fedoraproject.org>
'''
Unit tests for bugzilla bug handling
'''


import unittest2 as unittest

import srcpath                                   # pylint: disable=W0611
import FedoraReview.deps as deps

from fr_testcase import FEDORA

DEPLIST_OK = set(["bash",
                  "python",
                  "fedora-packager",
                  "python",
                  "python-BeautifulSoup",
                  "python",
                  "python-bugzilla",
                  "python-kitchen",
                  "python-straight-plugin",
                  "rpm-python",
                  "devscripts-minimal"])


DIRLIST_OK = set(["/usr/share/doc/ruby-racc-1.4.5",
                  "/usr/share/doc/ruby-racc-1.4.5/doc.en",
                  "/usr/share/doc/ruby-racc-1.4.5/doc.ja",
                  "/usr/share/ruby/vendor_ruby/racc"])
DIRLIST_PKG = 'ruby-racc/ruby-racc/results/ruby-racc-1.4.5-9.fc17.noarch.rpm'

OWNERS_OK = set(['rpm', 'yum', 'fedora-release'])


class TestDeps(unittest.TestCase):
    ''' Low-level, true unit tests. '''

    @unittest.skipIf(not FEDORA, 'Fedora-only test')
    def test_list_deps(self):
        ''' Test listing of package deps. '''
        deplist = deps.list_deps('fedora-review')
        if 'yum-utils' in deplist:              # F18-> F19 changes.
            deplist.remove('yum-utils')
        self.assertEqual(set(deplist), DEPLIST_OK)

    @unittest.skipIf(not FEDORA, 'Fedora-only test')
    def test_resolve(self):
        ''' Test resolving symbols -> packages. '''
        pkgs = deps.resolve(['config(rpm)', 'perl'])
        self.assertEqual(set(['rpm', 'perl']), set(pkgs))

    @unittest.skipIf(not FEDORA, 'Fedora-only test')
    def test_list_dirs(self):
        ''' Test listing of package dirs. '''
        dirlist = deps.list_dirs(DIRLIST_PKG)
        self.assertEqual(set(dirlist), DIRLIST_OK)

    @unittest.skipIf(not FEDORA, 'Fedora-only test')
    def test_list_owners(self):
        ''' Test listing of file owner(s). '''
        owners = deps.list_owners(['/var/lib/rpm', '/etc/yum.repos.d/'])
        if 'generic-release' in owners:  # F18 madness
            owners.remove('generic-release')
        self.assertEqual(set(owners), OWNERS_OK)

    @unittest.skipIf(not FEDORA, 'Fedora-only test')
    def test_list_paths(self):
        ''' test list_paths method. '''
        paths = deps.list_paths('fedora-release')
        self.assertTrue('/etc/fedora-release' in paths)
