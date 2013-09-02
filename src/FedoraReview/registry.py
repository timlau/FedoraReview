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


from review_error import ReviewError
from settings import Settings
from version import __version__, BUILD_ID


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
    contain a class Registry. This has:
      - A single function register() which return a list of checks
        defined by the module.
      - Registration of flags, also in the register() function
      - Metadata: name, version etc.

    A plugin module serves a specific group such as 'java', 'PHP',
    or 'generic'. The group property reflects that group, and the
    is_applicable method returns if a given test is valid for current
    srpm.
    """
    # pylint: disable=R0201,W0613

    group = 'Undefined'
    name  = 'fedora-review'
    version = __version__
    build_id = BUILD_ID

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

    @staticmethod
    def get_build_id(path):
        ''' get the build_id from a file. Filename is deduced from
        path by replacing .py with .build. File should contain just
        the build id, it's used verbatim.
        '''
        file_ = os.path.basename(path).replace('.py', '.build')
        id_path = os.path.join(os.path.dirname(path), file_)
        with open(id_path) as f:
             return f.read().strip()


    def get_plugin_nvr(self):
        """
        NOTES:
        The name-scheme enforcing is nice IMHO. However, we have multiple
        problems here:
           - The interface should really be uniform, a plugin still in
             f-r mainline should return f-r's nvr, shouldn't it? It's
             sort of a vendor thing IMHO.
           - Using rpm means that we always will refer to the installed
             variant.  Problems when running git snapshots or basically
             anything not installed - so far we have promised only to access
             plugins in the instance we are running.
           - The 'release' part is problematic for reasons above: what is
             the release of a git snapshot?
           - Also, we need a build-id, this is really the only way to
             manage variants which are not released. And we need to handle
             that imho. We could use the release field for either release
             or build-id, but why?

        Ergo: the plugins must carry their own version information, f-r
        nvr should be the default and if release should be used it should
        be part of the version field. Something like

            class Javaplugin....
               ...
               group = 'java.guidelines'
               name = 'java_guidelines'
               version = '0.1'
               build_id = self.registry.get_build_id(__file__)

        This is to require plugins to carry their own version
        and name hardcoded in source. The build_id is the an exception,
        it can't be checked in (because it's unknown until after commit).
        So, require the build_id in a separate file, presumably done by
        a git post-commit. File sits in same directory as plugin source.
        -------
        Return information about plugin for current group. Default
        implementation returns nvr for fedora-review.

        Return tuple is (name, version, build_id). Not really required, we
        have the attributes. nvr is used all over the place as an
        object with attributes, a tuple might cause some confusion.
        """
        return self.name, self.version, self.build_id

    def is_plugin_installed(self):
        """
        NOTE: why is this needed?

        Return True if there is external plugin for current group is installed
        or False otherwise
        """
        return self.name != 'fedora-review'

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
