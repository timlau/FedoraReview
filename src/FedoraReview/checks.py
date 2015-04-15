# -*- coding: utf-8 -*-

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
This module contains misc helper funtions and classes
'''

import os
import sys
import time

from operator import attrgetter
from straight.plugin import load                  # pylint: disable=F0401

from datasrc import RpmDataSource, BuildFilesSource, SourcesDataSource
from settings import Settings
from srpm_file import SRPMFile
from spec_file import SpecFile
from review_error import ReviewError
from xdg_dirs import XdgDirs
from reports import write_xml_report, write_template


_BATCH_EXCLUDED = 'CheckBuild,CheckPackageInstalls,CheckRpmlintInstalled,' \
    'CheckNoNameConflict,CheckInitDeps,CheckRpmlint'


class _CheckDict(dict):
    """
    A Dictionary of AbstractCheck, with some added behaviour:
        - Deprecated checks are removed when new items enter.
        - Duplicates (overwriting existing entry) is not allowed.
        - Inserted entry gets a checkdict property pointing to
          containing CheckDict instance.
        - On insertion, items listed in the 'deprecates'property
          are removed.
    """
    # pylint: disable=R0904

    def __init__(self, *args, **kwargs):
        dict.__init__(self)
        self.update(*args, **kwargs)
        self.log = Settings.get_logger()
        self.deprecations = {}

    def __setitem__(self, key, value):

        def log_duplicate(first, second):
            ''' Log warning for duplicate test. '''
            self.log.warning("Duplicate checks %s in %s, %s in %s" %
                             (first.name, first.defined_in,
                              second.name, second.defined_in))

        if key in self.iterkeys():
            log_duplicate(value, self[key])
        dict.__setitem__(self, key, value)
        value.checkdict = self

    def update(self, *args, **kwargs):
        if len(args) > 1:
            raise TypeError("update: at most 1 arguments, got %d" %
                            len(args))
        other = dict(*args, **kwargs)
        for key in other.iterkeys():
            self[key] = other[key]

    def add(self, check):
        ''' As list.add(). '''
        self[check.name] = check

    def extend(self, checks):
        ''' As list.extend() '''
        for c in checks:
            self.add(c)

    def set_single_check(self, check_name):
        ''' Remove all checks besides check_name and it's deps. '''

        def reap_needed(node):
            ''' Collect all deps into needed. '''
            needed.append(node)
            node.result = None
            for n in node.needs:
                reap_needed(self[n])

        needed = []
        reap_needed(self[check_name])
        self.clear()
        self.extend(needed)
        delattr(self[check_name], 'result')

    def fix_deprecations(self, key):
        ''' Remove deprecated tests, needs Registry.is_applicable(). '''

        def log_kill(victim, killer):
            ''' Log test skipped due to deprecation. '''
            self.log.debug("Skipping %s in %s, deprecated by %s in %s" %
                           (victim.name, victim.defined_in,
                            killer.name, killer.defined_in))

        value = self[key]
        for victim in value.deprecates:
            if victim in self.iterkeys():
                log_kill(self[victim], value)
                del self[victim]
        for killer in self.itervalues():
            if key in killer.deprecates:
                log_kill(value, killer)
                return


class _Flags(dict):
    ''' A dict storing Flag  entries with some added behaviour. '''

    def __init__(self):
        dict.__init__(self)

    def add(self, flag):
        ''' As list.add(). '''
        self[flag.name] = flag

    def update(self, optarg):
        '''
        Try to update a flag with command line setting.
        Raises KeyError if flag not registered.
        '''
        if '=' in optarg:
            key, value = optarg.split('=')
            self[key].value = value
        else:
            self[optarg].set_active()


class _ChecksLoader(object):
    """
    Interface class to load  and select checks.
    Properties:
       - checkdict: checks by name, all loaded (not deprecated) checks.
    """

    class Data(object):
        ''' Simple DataSource stuff container. '''
        pass

    def __init__(self):
        ''' Create a Checks, load checkdict. '''
        self.log = Settings.get_logger()
        self.checkdict = None
        self.flags = _Flags()
        self.groups = None
        self._load_checks()
        if Settings.single:
            self.set_single_check(Settings.single)
        elif Settings.exclude:
            self.exclude_checks(Settings.exclude)
        self._update_flags()
        if self.flags['BATCH']:
            self.exclude_checks(_BATCH_EXCLUDED)

    def _update_flags(self):
        ''' Update registered flags with user -D settings. '''
        for flag_opt in Settings.flags:
            try:
                if '=' not in flag_opt:
                    key = flag_opt
                    self.flags[flag_opt].activate()
                else:
                    key, value = flag_opt.split('=')
                    self.flags[key].value = value
            except KeyError:
                raise ReviewError(key + ': No such flag')

    def _load_checks(self):
        """
        Load all checks in FedoraReview.checks + external plugin
        directories and add them to self.checkdict
        """

        self.checkdict = _CheckDict()
        self.groups = {}

        appdir = os.path.realpath(
            os.path.join(os.path.dirname(__file__)))
        sys.path.insert(0, appdir)
        sys.path.insert(0, XdgDirs.app_datadir)
        plugins = load('plugins')
        for plugin in sorted(plugins, key=lambda p: len(p.__name__)):
            if plugin.__name__ == 'plugins.plugins':
                continue
            registry = plugin.Registry(self)
            tests = registry.register(plugin)
            self.checkdict.extend(tests)
            self.groups[registry.group] = registry
        for c in self.checkdict:
            if not self.checkdict[c].registry:
                self.checkdict[c].registry = self.groups[c.group]
        sys.path.remove(XdgDirs.app_datadir)
        sys.path.remove(appdir)

    def exclude_checks(self, exclude_arg):
        ''' Mark all checks in exclude_arg (string) as already done. '''
        for c in [l.strip() for l in exclude_arg.split(',')]:
            if c in self.checkdict:
                # Mark check as run, don't delete it. We want
                # checks depending on this to run.
                self.checkdict[c].result = None
                self.checkdict[c].is_disabled = True
            else:
                self.log.warn("I can't remove check: " + c)

    def set_single_check(self, check):
        ''' Remove all checks but arg and it's deps. '''
        self.checkdict.set_single_check(check)
        self.checkdict[check].needs = []

    def get_checks(self):
        ''' Return the Checkdict instance holding all checks. '''
        return self.checkdict

    def get_plugins(self, state='true_or_false'):
        ''' Return list of groups (i. e., plugins) being active/passive. '''
        plugins = []
        for p in self.groups.iterkeys():
            if state != 'true_or_false':
                r = self.groups[p]
                if r.is_user_enabled():
                    if r.user_enabled_value() != state:
                        continue
                elif not bool(r.is_applicable()) == state:
                    continue
            plugins.append(p.split('.')[0] if '.' in p else p)
        return list(set(plugins))


class ChecksLister(_ChecksLoader):
    ''' A class only exporting get_checks() and checkdict. '''

    def __init__(self):
        self.spec = None
        self.srpm = None
        self.data = self.Data()
        self.data.rpms = None
        self.data.buildsrc = None
        self.data.sources = None
        _ChecksLoader.__init__(self)


class Checks(_ChecksLoader):
    ''' Interface class to run checks.  '''

    def __init__(self, spec_file, srpm_file):
        ''' Create a Checks set. srpm_file and spec_file are required,
        unless invoked from ChecksLister.
        '''
        _ChecksLoader.__init__(self)
        self.spec = SpecFile(spec_file, self.flags)
        self.srpm = SRPMFile(srpm_file)
        self.data = self.Data()
        self.data.rpms = RpmDataSource(self.spec)
        self.data.buildsrc = BuildFilesSource()
        self.data.sources = SourcesDataSource(self.spec)
        self._clock = None

    rpms = property(lambda self: self.data.rpms)
    sources = property(lambda self: self.data.sources)
    buildsrc = property(lambda self: self.data.buildsrc)

    @staticmethod
    def _write_testdata(results):
        ''' Write hidden file usable when writing tests. '''
        with open('.testlog.txt', 'w') as f:
            for r in results:
                f.write('\n' + 24 * ' '
                        + "('%s', '%s')," % (r.state, r.name))

    def _ready_to_run(self, name):
        """
        Check that check 'name' havn't already run and that all checks
        listed in 'needs' have run i. e., it's ready to run.
        """
        try:
            check = self.checkdict[name]
        except KeyError:
            return False
        if check.is_run:
            return False
        if check.registry.is_user_enabled() and not \
            check.registry.user_enabled_value():
                return False
        for dep in check.needs:
            if dep not in self.checkdict:
                self.log.warning('%s depends on deprecated %s' %
                                 (name, dep))
                self.log.warning('Removing %s, cannot resolve deps' %
                                 name)
                del self.checkdict[name]
                return True
            elif not self.checkdict[dep].is_run:
                return False
        return True

    def deprecate(self):
        ''' Mark all deprecated tests as run. '''
        allkeys = list(self.checkdict.iterkeys())
        for c in allkeys:
            if c not in self.checkdict:
                continue
            if self.checkdict[c].is_applicable():
                self.checkdict.fix_deprecations(c)

    def _get_ready_to_run(self):
        ''' Return checks ready to run, deprecating checks first. '''
        names = list(self.checkdict.iterkeys())
        tests_to_run = filter(self._ready_to_run, names)
        return sorted(tests_to_run,
                      key=lambda t: len(self.checkdict[t].deprecates),
                      reverse=True)

    def is_external_plugin_installed(self, group_name):
        ''' Return True if external plugin install for given group. '''
        for reg_group, registry in self.groups.iteritems():
            basename = reg_group.split('.')[0]
            if basename == group_name and registry.external_plugin:
                return True
        return False

    def run_checks(self, output=sys.stdout, writedown=True):
        ''' Run all checks. '''

        def run_check(name):
            """ Run check. Update results, attachments and issues. """
            check = self.checkdict[name]
            if check.is_run:
                return
            self.log.debug('Running check: ' + name)
            check.run()
            now = time.time()
            self.log.debug('    %s completed: %.3f seconds'
                           % (name, (now - self._clock)))
            self._clock = now
            attachments.extend(check.attachments)
            result = check.result
            if not result:
                return
            results.append(result)
            if result.type == 'MUST' and result.result == "fail":
                issues.append(result)

        issues = []
        results = []
        attachments = []
        has_deprecated = False

        tests_to_run = self._get_ready_to_run()
        self._clock = time.time()
        while tests_to_run != []:
            for name in tests_to_run:
                if self.checkdict[name].deprecates and not has_deprecated:
                    self.deprecate()
                    has_deprecated = True
                    break
                run_check(name)
            tests_to_run = self._get_ready_to_run()

        if writedown:
            key_getter = attrgetter('group', 'type', 'name')
            write_template(output,
                           sorted(results, key=key_getter),
                           issues,
                           attachments)
            write_xml_report(self.spec, results)
        else:
            with open('.testlog.txt', 'w') as f:
                for r in results:
                    f.write('\n' + 24 * ' '
                            + "('%s', '%s')," % (r.state, r.name))


# vim: set expandtab ts=4 sw=4:
