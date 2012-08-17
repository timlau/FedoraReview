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

import re
import fnmatch
import StringIO

from textwrap import TextWrapper

from helpers import Helpers
from settings import Settings
from mock import Mock


class AbstractCallError(Exception):
    pass


class AbstractCheck(object):
    """
    The basic interface for a test (a. k a. check) as seen from
    the outside.

    Class attributes:
      - version version of api, defaults to 0.1
      - group: 'Generic', 'C/C++', 'PHP': name of the registry
                which instantiated this check.
      - implementation: 'json'|'python'|'shell', defaults to 
        'python'.

    Properties:
      - name: Unique string.
      - defined_in: Filename (complete path).
      - deprecates: List of  tests replaced (should not run) by this
        test  if the test is applicable.
      - needs: List of tests which should run before this test.
      - result: Undefined until run(), None if test is not
        applicable, else TestResult.

    Methods:
      - run(): Run the test, sets result

    Equality:
      - Tests are considered equal if they have the same name.
    """

    version        = '0.1'
    implementation = 'python'

    def __init__(self, defined_in):
        self.defined_in = defined_in
        self.deprecates = []
        self.needs = []
        self._name = 'Undefined'

    name = property(lambda self: self._name,
                    lambda self,n: setattr(self, '_name', n))

    def __eq__(self, other):
       return self.name.__eq__(other)

    def __ne__(self, other):
       return self.name.__ne__(other)

    def __hash__(self):
        return self.name.__hash__()

    def __str__(self):
        return self.name

    def run(self):
        raise AbstractCallError('AbstractCheck')

class GenericCheck(AbstractCheck):
    """
    Common interface inherited by all Check implementations.

    Properties:
      - text: free format user info on test, one line.
      - description: longer, multiline free format text info.
      - type: 'MUST'|'SHOULD'|'EXTRA'|'UNDEFINED', defaults to
        'MUST'
      - url: Usually guidelines url, possibly None.
      - checks: Checks instance which created this check.
    """

    def __init__(self, checks, defined_in):
        AbstractCheck.__init__(self, defined_in)
        self.checks = checks
        self.url = '(this test has no URL)'
        self.text = 'No description'
        self.description = 'This test has no description'
        self.type = 'MUST'
        self.needs = ['CheckBuildCompleted']

    spec = property(lambda self: self.checks.spec)
    srpm = property(lambda self: self.checks.srpm)
    sources = property(lambda self: self.checks.sources)
    name = property(lambda self: self.__class__.__name__)

    def set_passed(self, result, output_extra=None, attachments=[]):
        '''
        Set if the test is passed, failed or N/A
        and set optional extra output to be shown in repost
        '''
        if result == 'not_applicable':
            self.result = None
            return
        if result == None or result == 'na':
            state = 'na'
        elif result == True or result == 'pass':
            state = 'pass'
        elif result == False or result == 'fail':
            state = 'fail'
        elif result == 'inconclusive' or result == 'pending':
            state = 'pending'
        else:
            state = 'fail'
        r = TestResult(self, state, output_extra, attachments)
        self.result = r

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
        for rpm in rpm_files:
            for fn in rpm_files[rpm]:
                if fn_pat.search(fn):
                    return True
        return False


class CheckBase(GenericCheck, Helpers):
    """ Base class for "regular" python checks. """

    def __init__(self, checks, defined_in):
        Helpers.__init__(self)
        GenericCheck.__init__(self, checks, defined_in)

    def is_applicable(self):
        '''
        check if this test is applicable
        overload in child class if needed
        '''
        return True

    def run_if_applicable(self):
        self.set_passed('inconclusive')

    def run(self):
        ''' By default, a manual test returning 'inconclusive'.'''
        if self.is_applicable():
             self.run_if_applicable()
        else:
             self.set_passed('not_applicable')

    def get_files_by_pattern(self, pattern):
        result = {}
        rpm_files = self.srpm.get_files_rpms()
        for rpm in rpm_files:
            result[rpm] = []
            for fn in rpm_files[rpm]:
                if fnmatch.fnmatch(fn, pattern):
                    result[rpm].append(fn)
        return result

    group = property(lambda self: self.registry.group)


class LangCheckBase(CheckBase):
    """ Base class for language specific class. """

    def is_applicable(self):
        """ By default, language specific check are disabled. """
        return False


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


class TestResult(object):
    TEST_STATES = {
         'pending': '[ ]', 'pass': '[x]', 'fail': '[!]', 'na': '[-]'}

    def __init__(self, check, result, output_extra, attachments=[]):
        self.name = check.name
        self.url = check.url
        self.group = check.group
        self.deprecates = check.deprecates
        self.text = re.sub("\s+", " ", check.text) if check.text else ''
        self.type = check.type
        self.result = result
        self.output_extra = output_extra
        self.attachments = attachments
        if self.output_extra:
            self.output_extra = re.sub("\s+", " ", self.output_extra)
        self.wrapper = TextWrapper(width=78, subsequent_indent=" " * 5,
                                   break_long_words=False, )

    def get_text(self):
        strbuf = StringIO.StringIO()
        main_lines = self.wrapper.wrap(
            "%s: %s" % (self.TEST_STATES[self.result], self.text))
        strbuf.write("%s" % '\n'.join(main_lines))
        if self.output_extra and self.output_extra != "":
            strbuf.write("\n")
            extra_lines = self.wrapper.wrap("     Note: %s" %
                                            self.output_extra)
            strbuf.write('\n'.join(extra_lines))

        return strbuf.getvalue()

    def __str__(self):
        self.get_text()


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
