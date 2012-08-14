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
This module contains automatic test for Fedora Packaging guidelines
'''

import inspect
import fnmatch
import re
import StringIO

from textwrap import TextWrapper

from helpers import Helpers
from settings import Settings
from mock import Mock
from review_error import FedoraReviewError

TEST_STATES = {'pending': '[ ]', 'pass': '[x]', 'fail': '[!]', 'na': '[-]'}
DEFAULT_API_VERSION = '0.1'

class AbstractRegistry(object):
    """ 
    The overall interface for a plugin module is that it must 
    contain a class Registry. This has a single function register()
    which return a list of checks defined by the module.
    """

    def register(self, plugin, checks):
        """
        Return list of checks in current module
        Parameters:
           plugin: loaded module object
           checks: Checks instance used when initiating check
                   object
        Returns:   CheckDict instance.
          
        """
        raise FedoraReviewError('Abstract register() called')
        

class RegistryBase(AbstractRegistry):
    """
    Register all classes containing 'Check' and not ending with 'Base'
    """

    def register(self, plugin, checks):
        tests = []
        id_and_classes = inspect.getmembers(plugin, inspect.isclass)
        for c in id_and_classes:
            if not 'Check' in c[0]:
                continue
            if c[0].endswith('Base'):
                continue
            obj = (c[1])(checks)
            tests.append(obj)
        return tests


class AbstractCheck(object):
    """
    The basic interface for a test (a. k a. check).

    Properties:
      - name: unique string
      - text: free format user info on test, one line.
      - description: longer, multiline free format text info.
      - type: 'MUST'|'SHOULD'|'EXTRA'|'UNDEFINED'
      - url: Usually guidelines url, possibly None.
      - defined_in: filename (complete path).
      - group: 'Generic', 'C/C++', 'php' ...
      - implementation: 'json'|'python'|'undefined'
      - version version of api, defaults to 0.1
      - deprecates: list of  tests replaced (should not run) by this test.
      - needs: List of tests which should run before this test. 
      - result: doesn't exist if test hasn't run. Else  TestResult or None.
      - checklist: the CheckDict instance this check is part of.
   
    Methods:
      - run(): run the test, sets result. The result is None if
        the test is not applicable. Otherwise, it's a TestResult
        reflecting either "pass","fail" or "na"

    Equality:
      - tests are considered equal if they have the same name.
    """

    def __init__(self, defined_in):
        self.defined_in = defined_in
        self._name = 'undefined'
        self.url = None
        self.text = None
        self.description = None
        self.type = 'UNDEFINED'
        self.group = 'Undefined'
        self.implementation = 'undefined'
        self.version = '0.1'
        self.deprecates = []
        self.needs = []
 

    name = property(lambda self: self._name,
                    lambda self,n: setattr(self, '_name', n))

    def __eq__(self, other):
       return self.name.__eq__(other)

    def __ne__(self, other):
       return self.name.__ne__(other)

    def __hash__(self):
        return self.name.__hash__()


class CheckDict(dict):
    """
    A Dictionary of AbstractCheck, maintaining checkdict property. 
    """

    def __init__(self, *args, **kwargs):
        self.update(*args, **kwargs)

    def __setitem__(self, key, value):
        value.checkdict = self
        dict.__setitem__(self, key, value)

    def update(self, *args, **kwargs):
        if len(args) > 1:
            raise TypeError("update: at most 1 arguments, got %d" % 
                            len(args))
        other = dict(*args, **kwargs)
        for key in other.iterkeys():
            self[key] = other[key]

    def add(self, check):
        self[check.name] = check

    def extend(self, checks):
        for c in checks:
            self.add(c)

    def set_single_check(self, check_name):
        c = self[check_name]
        self.clear()
        self[check_name] = c


class CheckBase(AbstractCheck, Helpers):
    """ Base class for native, python plugins in checks directory. """

    deprecates = []
    header = 'Generic'

    def __init__(self, base, sourcefile):
        Helpers.__init__(self)
        AbstractCheck.__init__(self, sourcefile)
        self.base = base
        self.spec = base.spec
        self.srpm = base.srpm
        self.sources = base.sources
        self.state = None
        self.output_extra = None
        self.attachments = []
        
    name = property(lambda self: self.__class__.__name__)

    def run(self):
        if self.is_applicable():
            self.run_if_applicable()
        else:
            self.set_passed('not_applicable')

    def run_if_applicable(self):
        ''' By default, a manual test returning 'inconclusive'.'''
        self.set_passed('inconclusive')

    def set_passed(self, result, output_extra=None, attachments=[]):
        '''
        Set if the test is passed, failed or N/A
        and set optional extra output to be shown in repost
        '''

        if result == 'not_applicable':
            self.result = None
            return
        if result == None or result == 'na':
            self.state = 'na'
        elif result == True or result == 'pass':
            self.state = 'pass'
        elif result == 'inconclusive' or result == 'pending':
            self.state = 'pending'
        else:
            self.state = 'fail'
        if output_extra:
            self.output_extra = output_extra
        if attachments != []:
            self.attachments = attachments
        r = TestResult(self.name, self.url, self.group,
                       self.deprecates, self.text, self.type,
                       self.state, self.output_extra, self.attachments)
        self.result = r

    def is_applicable(self):
        '''
        check if this test is applicable
        overload in child class if needed
        '''
        return True

    def sources_have_files(self, pattern):
        ''' Check if rpms has file matching a pattern'''
        sources_files = self.sources.get_files_sources()
        for source in sources_files:
            if fnmatch.fnmatch(source, pattern):
                return True
        return False

    def has_files(self, pattern):
        ''' Check if rpms has file matching a pattern'''
        rpm_files = self.srpm.get_files_rpms()
        for rpm in rpm_files:
            for fn in rpm_files[rpm]:
                if fnmatch.fnmatch(fn, pattern):
                    return True
        return False

    def has_files_re(self, pattern_re):
        ''' Check if rpms has file matching a pattern'''
        fn_pat = re.compile(pattern_re)
        rpm_files = self.srpm.get_files_rpms()
        #print rpm_files, pattern_re
        for rpm in rpm_files:
            for fn in rpm_files[rpm]:
                if fn_pat.search(fn):
                    return True
        return False

    def get_files_by_pattern(self, pattern):
        result = {}
        rpm_files = self.srpm.get_files_rpms()
        for rpm in rpm_files:
            result[rpm] = []
            for fn in rpm_files[rpm]:
                if fnmatch.fnmatch(fn, pattern):
                    result[rpm].append(fn)
        return result


class LangCheckBase(CheckBase):
    """ Base class for language specific class. """
    header = 'Language'

    def is_applicable(self):
        """ By default, language specific check are disabled. """
        return False


class TestResult(object):

    def __init__(self, name, url, group, deprecates, text, check_type,
                 result, output_extra, attachments=[]):
        self.name = name
        self.url = url
        self.group = group
        self.deprecates = deprecates
        self.text = re.sub("\s+", " ", text) if text else ''
        self.type = check_type
        self.result = result
        self.output_extra = output_extra
        self.attachments = attachments
        if self.output_extra:
            self.output_extra = re.sub("\s+", " ", self.output_extra)
        self.wrapper = TextWrapper(width=78, subsequent_indent=" " * 5,
                                   break_long_words=False, )

    def get_text(self):
        strbuf = StringIO.StringIO()
        main_lines = self.wrapper.wrap("%s: %s" % (TEST_STATES[self.result],
                                                   self.text))
        strbuf.write("%s" % '\n'.join(main_lines))
        if self.output_extra and self.output_extra != "":
            strbuf.write("\n")
            extra_lines = self.wrapper.wrap("     Note: %s" %
                                            self.output_extra)
            strbuf.write('\n'.join(extra_lines))

        return strbuf.getvalue()


class Attachment(object):
    """ Text written after the test lines. """

    def __init__(self, header, text, order_hint=10):
        """
        Setup an attachment. Args:
         -  header: short header, < 40 char.
         -  text: printed as-is.
         -  order_hint: Sorting hint, lower hint goes first.
                0 <= order_hint <= 10
        """

        self.header = header
        self.text = text
        self.order_hint = order_hint

    def __str__(self):
        s = self.header + '\n'
        s +=  '-' * len(self.header) + '\n'
        s +=  self.text
        return s

    def __cmp__(self, other):
        if not hasattr(other, 'order_hint'):
            return NotImplemented
        if self.order_hint < other.order_hint:
            return -1
        if self.order_hint > other.order_hint:
            return 1
        return 0


# vim: set expandtab: ts=4:sw=4:
