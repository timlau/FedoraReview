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
This module contains misc helper funtions and classes
'''

import sys
import os

from glob import glob
from operator import attrgetter
from straight.plugin import load

from settings import  Settings
from mock import Mock
from srpm_file import  SRPMFile
from spec_file import  SpecFile
from sources import  Sources
from review_dirs import ReviewDirs
from version import  __version__, BUILD_ID, BUILD_DATE
from review_error import ReviewError
from jsonapi import JSONPlugin


HEADER = """
Package Review
==============

Key:
[x] = Pass
[!] = Fail
[-] = Not applicable
[?] = Not evaluated
[ ] = Manual review needed

"""


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

    def __init__(self, *args, **kwargs):
        dict.__init__(self)
        self.update(*args, **kwargs)
        self.log = Settings.get_logger()
        self.deprecations = {}

    def __setitem__(self, key, value):

        def log_kill(victim, killer):
            ''' Log test skipped due to deprecation. '''
            self.log.debug("Skipping %s in %s, deprecated by %s in %s" %
                              (victim.name, victim.defined_in,
                               killer.name, killer.defined_in))

        def log_duplicate(first, second):
            ''' Log warning for duplicate test. '''
            self.log.warning("Duplicate checks %s in %s, %s in %s" %
                              (first.name, first.defined_in,
                              second.name, second.defined_in))

        for victim in value.deprecates:
            if victim in self.iterkeys():
                log_kill(self[victim], value)
                del(self[victim])
        for killer in self.itervalues():
            if key in killer.deprecates:
                log_kill(value, killer)
                return
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

class _Flags(dict):
    ''' A dict storing Flag  entries with some added baheviour. '''

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




class Checks(object):
    '''
    Interface class to load, select and run checks.
    Properties:
        checkdict: A dictionary of all tests by name (deprecated
                   removed).
    '''

    def __init__(self, spec_file, srpm_file):
        ''' Create a Checks set. srpm_file and spec_file are required,
        unless invoked from ChecksLister.
        '''
        self.log = Settings.get_logger()
        self.checkdict = None
        self.flags = _Flags()
        self.groups = None
        if hasattr(self, 'sources'):
            # This is  a listing instance
            self.srpm = None
            self.spec = None
        else:
            self.spec = SpecFile(spec_file)
            self.sources = Sources(self.spec)
            self.srpm = SRPMFile(srpm_file, self.spec)
        self.add_check_classes()
        if Settings.single:
            self.set_single_check(Settings.single)
        elif Settings.exclude:
            self.exclude_checks(Settings.exclude)
        self.update_flags()

    def update_flags(self):
        ''' Update registered flags with user -D settings. '''
        for flag_opt in Settings.flags:
            try:
                if not '=' in flag_opt:
                    key = flag_opt
                    self.flags[flag_opt].activate()
                else:
                    key, value = flag_opt.split('=')
                    self.flags[key].value = value
            except KeyError:
                raise ReviewError(key + ': No such flag')

    def add_check_classes(self):
        """
        Get all check classes in FedoraReview.checks + external plugin
        directories and add them to self.checkdict
        """

        self.checkdict = _CheckDict()
        self.groups = {}

        appdir = os.path.abspath(os.path.join(__file__, '../../..'))
        sys.path.insert(0, appdir)
        plugins = load('plugins')
        for plugin in plugins:
            registry = plugin.Registry(self)
            tests = registry.register(plugin)
            self.checkdict.extend(tests)
            self.groups[registry.group] = registry

        ext_dirs = []
        if "REVIEW_EXT_DIRS" in os.environ:
            ext_dirs = os.environ["REVIEW_EXT_DIRS"].split(":")
        ext_dirs.extend(Settings.ext_dirs.split(":"))
        for ext_dir in ext_dirs:
            if not os.path.isdir(ext_dir):
                continue
            for plugin in os.listdir(ext_dir):
                full_path = os.path.join(ext_dir, plugin)
                if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                    self.log.debug('Add external module: %s' % full_path)
                    pl = JSONPlugin(self, full_path)
                    tests = pl.register()
                    self.checkdict.extend(tests)

    def exclude_checks(self, exclude_arg):
        ''' Mark all checks in exclude_arg (string) as already done. '''
        for c in [l.strip() for l in exclude_arg.split(',')]:
            if  c in self.checkdict:
                # Mark check as run, don't delete it. We want
                # checks depending on this to run.
                self.checkdict[c].result = None
            else:
                self.log.warn("I can't remove check: " + c)

    def set_single_check(self, check):
        ''' Remove all checks but arg and it's deps. '''
        self.checkdict.set_single_check(check)
        self.checkdict[check].needs = []

    def get_checks(self):
        ''' Return the Checkdict instance holding all checks. '''
        return self.checkdict

    def run_checks(self, output=sys.stdout, writedown=True):
        ''' Run all checks. '''

        def ready_to_run(name):
            """
            Check if all checks listed in 'needs' have run and not
            already run.
            """
            check = self.checkdict[name]
            if check.is_run:
                return False
            for dep in check.needs:
                if not dep in self.checkdict:
                    self.log.warning('%s depends on deprecated %s' %
                                        (name, dep))
                    self.log.warning('Removing %s, cannot resolve deps' %
                                     name)
                    del(self.checkdict[name])
                    return True
                elif not self.checkdict[dep].is_run:
                    return False
            return True

        def run_check(name):
            """ Run check. Update results, attachments and issues. """
            check = self.checkdict[name]
            if check.is_run:
                return
            self.log.debug('Running check: ' + name)
            check.run()
            result = check.result
            if not result:
                return
            results.append(result)
            attachments.extend(result.attachments)
            if result.type == 'MUST' and result.result == "fail":
                issues.append(result)

        issues = []
        results = []
        attachments = []

        names = list(self.checkdict.iterkeys())

        tests_to_run = filter(ready_to_run, names)
        while tests_to_run != []:
            for name in tests_to_run:
                run_check(name)
            tests_to_run = filter(ready_to_run, names)

        if writedown:
            key_getter = attrgetter('group', 'type', 'name')
            self.show_output(output,
                             sorted(results, key=key_getter),
                             issues,
                             attachments)

    @staticmethod
    def show_output(output, results, issues, attachments):
        ''' Print test results on output. '''

        def write_sections(results):
            ''' Print a {SHOULD,MUST, EXTRA} section. '''
            groups = sorted(list(set([test.group for test in results])))
            for group in groups:
                res = filter(lambda t: t.group == group, results)
                if res == []:
                    continue
                output.write('\n' + group + ':\n')
                for r in res:
                    output.write(r.get_text() + '\n')

        def dump_local_repo():
            ''' print info on --local-repo rpms used. '''
            repodir = Settings.repo
            if not repodir.startswith('/'):
                repodir = os.path.join(ReviewDirs.startdir, repodir)
            rpms = glob(os.path.join(repodir, '*.rpm'))
            output.write("\nBuilt with local dependencies:\n")
            for rpm in rpms:
                output.write("    " + rpm + '\n')

        output.write(HEADER)

        if issues:
            output.write("\nIssues:\n=======\n")
            for fail in issues:
                output.write(fail.get_text() + "\n")
                output.write("See: %s\n" % fail.url)

        output.write("\n\n===== MUST items =====\n")
        musts = filter(lambda r: r.type == 'MUST', results)
        write_sections(musts)

        output.write("\n===== SHOULD items =====\n")
        shoulds = filter(lambda r: r.type == 'SHOULD', results)
        write_sections(shoulds)

        output.write("\n===== EXTRA items =====\n")
        extras = filter(lambda r: r.type == 'EXTRA', results)
        write_sections(extras)

        for a in sorted(attachments):
            output.write('\n\n')
            output.write(a.__str__())

        if Settings.repo:
            dump_local_repo()

        output.write('\n\nGenerated by fedora-review'
                     ' %s (%s) last change: %s\n' %
                     (__version__, BUILD_ID, BUILD_DATE))
        output.write('Buildroot used: %s\n' % Mock.mock_root)
        output.write('Command line :' + ' '.join(sys.argv) + '\n')


class ChecksLister(Checks):
    """ A Checks instance only capable of get_checks. """
    def __init__(self):
        self.sources = None
        Checks.__init__(self, None, None)

# vim: set expandtab: ts=4:sw=4:
