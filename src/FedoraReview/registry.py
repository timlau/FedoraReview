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
Test module registration support
'''

import inspect

from check_base import FileChecks
from review_error import FedoraReviewError


class AbstractRegistry(object):
    """
    The overall interface for a plugin module is that it must
    contain a class Registry. This has a single function register()
    which return a list of checks defined by the module.

    A plugin module serves a specific group such as 'java', 'PHP',
    or 'generic'. The group property reflects that group, and the
    is_applicable method returns is a given test is valid for current
    srpm.
    """

    group = 'Undefined'

    def register(self, plugin):
        """
        Return list of checks in current module
        Returns:   CheckDict instance.

        """
        raise FedoraReviewError('Abstract register() called')

    def __init__(self, checks):
        """
        Parameters:
           - checks: Checks instance.
        """
        self._group = None
        self.checks = checks

    def is_applicable(self):
        """
        Return True if these tests are applicable for current srpm.
        """
        raise FedoraReviewError(
             'abstract Registry.is_applicable() called')



class RegistryBase(AbstractRegistry, FileChecks):
    """
    Register all classes containing 'Check' and not ending with 'Base'
    """

    def __init__(self, checks, path=None):
        AbstractRegistry.__init__(self, checks)
        FileChecks.__init__(self, checks)

    def is_applicable(self):
        return self.registry.is_applicable()

    def register(self, plugin):
        tests = []
        id_and_classes = inspect.getmembers(plugin, inspect.isclass)
        for c in id_and_classes:
            if not 'Check' in c[0]:
                continue
            if c[0].endswith('Base'):
                continue
            obj = (c[1])(self.checks)
            obj.registry = self
            tests.append(obj)
        return tests


# vim: set expandtab: ts=4:sw=4:
