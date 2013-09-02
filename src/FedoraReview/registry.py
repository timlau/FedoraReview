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

import rpm

from review_error import ReviewError
from settings import Settings


class _Flag(object):
    ''' A flag such as EPEL5, set byuser, handled by checks. '''

    def __init__(self, name, doc, defined_in):
        '''
        Create a flag. Parameters:
          - name: Short name of flag
          - doc: flag's doc-string.
        As created, flag is 'off' i. e., False. If user sets flag using
        -D flag, flag is 'set'i. e., True. If set using -Dflag=value,
        value is available as str(flag).
        '''
        self.name = name
        self.doc = doc
        self.defined_in = defined_in
        self.value = False

    def __nonzero__(self):
        return bool(self.value)

    def __str__(self):
        return self.value if self.value else ''

    def activate(self):
        ''' Turn 'on' flag from default 'off' state. '''
        self.value = '1'


class AbstractRegistry(object):
    """
    The overall interface for a plugin module is that it must
    contain a class Registry. This has a single function register()
    which return a list of checks defined by the module. It also
    defines the flags used by the module.

    A plugin module serves a specific group such as 'java', 'PHP',
    or 'generic'. The group property reflects that group, and the
    is_applicable method returns if a given test is valid for current
    srpm.
    """
    # pylint: disable=R0201,W0613

    group = 'Undefined'

    class Flag(_Flag):
        ''' A value defined in a check, set by user e. g., EPEL5. '''
        pass

    def register(self, plugin):
        """
        Define flags and return list of checks in current module.
        Returns:   CheckDict instance.

        """
        raise ReviewError('Abstract register() called')

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
        raise ReviewError(
            'abstract Registry.is_applicable() called')


class RegistryBase(AbstractRegistry):
    """
    Register all classes containing 'Check' and not ending with 'Base'
    """

    def __init__(self, checks, path=None):      # pylint: disable=W0613
        AbstractRegistry.__init__(self, checks)

    def get_plugin_nvr(self):
        """
        Return information about external plugin for current group

        Return tuple is (name, version, release) or (None, None, None) if
        plugin is not found
        """
        pkg_name = 'fedora-review-plugin-{group}'.format(
            group=self.group.lower())
        ts = rpm.TransactionSet()
        match = ts.dbMatch('name', pkg_name)
        if match.count() == 0:
            return (None, None, None)
        else:
            headers = match.next()
            return (headers[rpm.RPMTAG_NAME], headers[rpm.RPMTAG_VERSION],
                    headers[rpm.RPMTAG_RELEASE])

    def is_plugin_installed(self):
        """
        Return True if there is external plugin for current group is installed
        or False otherwise
        """
        if self.get_plugin_nvr() != (None, None, None):
            return True
        return False

    def is_applicable(self):
        return self.registry.is_applicable()

    def register_flags(self):
        ''' Register flags used by this module. '''
        pass

    def register(self, plugin):
        self.register_flags()
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

    def find_re(self, regex):
        ''' Files in rpms matching regex. '''
        return self.checks.rpms.find_re(regex)

    def find(self, glob_pattern):
        ''' Files in rpms matching glob_pattern. '''
        return self.checks.rpms.find(glob_pattern)

    def is_user_enabled(self):
        '''' True if this group is enabled/disabled using --plugins. '''
        g = self.group.split('.')[0] if '.' in self.group else self.group
        return g in Settings.plugins

    def user_enabled_value(self):
        '''' The actual value set if is_user_enabled() is True '''
        g = self.group.split('.')[0] if '.' in self.group else self.group
        return Settings.plugins[g]


# vim: set expandtab ts=4 sw=4:
