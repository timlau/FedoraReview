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

TEST_STATES = {'pending': '[ ]', 'pass': '[x]', 'fail': '[!]', 'na': '[-]'}


class CheckBase(Helpers):

    deprecates = []

    def __init__(self, base):
        Helpers.__init__(self)
        self.base = base
        self.spec = base.spec
        self.srpm = base.srpm
        self.sources = base.sources
        self.url = None
        self.text = None
        self.description = None
        self.state = 'pending'
        self.type = 'MUST'
        self.result = None
        self.output_extra = None
        self.attachments = []

    def __eq__(self, other):
       return self.__class__.__name__.__eq__(other)

    def __ne__(self, other):
       return self.__class__.__name__.__ne__(other)

    def __hash__(self):
        return self.__class__.__name__.__hash__()

    def run_on_applicable(self):
        self.set_passed('inconclusive')

    def run(self):
        ''' By default, a manual test returning 'inconclusive'.'''
        if self.is_applicable():
             self.run_on_applicable()
        else:
             self.set_passed('not_applicable')

    def set_passed(self, result, output_extra=None):
        '''
        Set if the test is passed, failed or N/A
        and set optional extra output to be shown in repost
        '''
        if result == 'not_applicable':
            self.state = 'not_applicable'
        elif result == None or result == 'na':
            self.state = 'na'
        elif result == True or result == 'pass':
            self.state = 'pass'
        elif result == False or result == 'fail':
            self.state = 'fail'
        elif result == 'inconclusive' or result == 'pending':
            self.state = 'pending'
        else:
            self.state = 'fail'
        self.output_extra = output_extra


    name = property(lambda self: self.__class__.__name__)

    def get_result(self):
        '''
        Get the test report result for this test
        '''
        ret = TestResult(self.__class__.__name__, self.url, self.__class__.header,
                          self.__class__.deprecates, self.text, self.type,
                          self.state, self.output_extra, self.attachments)
        return ret

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
