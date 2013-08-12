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
# (C) 2013 - Pavel Raiskup <praiskup@redhat.com>

''' Autotools SHOULD checks, default Generic group. '''

import textwrap
from subprocess import Popen, PIPE

from FedoraReview import CheckBase, RegistryBase, ReviewDirs


#########################################
## STILL COMMONLY USED OBSOLETE MACROS ##
##                                     ##
## Any suggestion for newer check here ##
## would be appreciated.               ##
#########################################

_OBS_M4S_AUTOMAKE = [
    'AM_CONFIG_HEADER',
    'AM_PROG_CC_STDC',
]

_OBS_M4S_LIBTOOL = [
    'AC_PROG_LIBTOOL',
    'AM_PROG_LIBTOOL',
]

_OBSOLETE_CHECKS = {
    'automake': _OBS_M4S_AUTOMAKE,
    'libtool': _OBS_M4S_LIBTOOL,
}


def _prepend_indent(text):
    ''' add the paragraph indentation '''
    lines = text.splitlines()
    return '\n'.join(map(lambda x: "  " + x if x != "" else "", lines))


class Registry(RegistryBase):
    ''' Module registration, register all checks. '''
    group = 'Generic.autotools'

    def is_applicable(self):
        return True


class AutotoolsCheckBase(CheckBase):
    ''' Base class for all Autotool-related tests. '''

    used_tools = None

    def __init__(self, checks):
        CheckBase.__init__(self, checks, __file__)

        # construct text wrapper
        self.wrapper = textwrap.TextWrapper(break_long_words=False,
                drop_whitespace=True, replace_whitespace=True,
                fix_sentence_endings=True)

    def text_wrap(self, text, width=76):
        ''' wrap the text on the specified character '''
        self.wrapper.width = width
        return self.wrapper.fill(text)

    def find_used_tools(self):
        ''' get the list of autotools relevant for this package '''

        def check_for(tool, packages):
            ''' helper - try all known package names for the tool '''
            for name in packages:
                if name in brequires:
                    self.used_tools.append(tool)
                    return

        brequires = self.spec.build_requires

        if self.used_tools is not None:
            return

        self.used_tools = []

        am_pkgs = ['automake', 'automake14', 'automake15', 'automake16',
                   'automake17']
        check_for('automake', am_pkgs)
        # Re-enable once some autoconf-related checkers are added
        # check_for('autoconf', ['autoconf', 'autoconf213'])
        check_for('libtool', ['libtool'])

        self.log.debug("autotools used: " + ' '.join(self.used_tools))


## CHECKERS ##

class CheckAutotoolsObsoletedMacros(AutotoolsCheckBase):
    ''' obsolete macros (shorthly m4s) checker '''

    warn_items = {}

    def __init__(self, base):
        AutotoolsCheckBase.__init__(self, base)

        # basic settings
        self.text = 'Package should not use obsolete m4 macros'
        self.automatic = True
        self.type = 'EXTRA'
        self.url = 'https://fedorahosted.org/FedoraReview/wiki/AutoTools'

    def get_trace_command(self):
        ''' construct the basic grep command '''
        trace_cmd = ["grep", "-E", "-n", "-o"]

        for tool in self.used_tools:
            if not tool in _OBSOLETE_CHECKS:
                # shouldn't be neccessary
                continue

            checks = _OBSOLETE_CHECKS[tool]
            for obs_m4 in checks:
                trace_cmd.append("-e")
                trace_cmd.append(obs_m4 + "[[:space:]]*$")
                trace_cmd.append("-e")
                trace_cmd.append(obs_m4 + r"\(")

        return trace_cmd

    def trace(self):
        ''' trace for obsoleted macros '''

        def shorter_configure(configure):
            ''' remove the workdir prefix from configure file '''
            prefix = ReviewDirs.root + "/BUILD"
            simple = configure
            if configure.startswith(prefix):
                simple = configure[len(prefix) + 1:]
            return simple

        # find traced files
        src = self.checks.buildsrc
        trace_files = src.find_all('*configure.ac') \
                    + src.find_all('*configure.in')

        # get the base tracing command (grep)
        trace_cmd = self.get_trace_command()

        # ---------------------------
        # search for obsoleted macros
        # ---------------------------
        for configure_ac in trace_files:
            cmd = trace_cmd + [configure_ac]

            try:
                self.log.debug("running: " + ' '.join(cmd))
                p = Popen(cmd, stdout=PIPE, stderr=PIPE)
                stdout, stderr = p.communicate()
            except IOError:
                self.set_passed(self.PENDING,
                        "error while tracing autoconf.ac")
                return

            if not p.returncode in [0, 1]:
                msg = "grep returns bad exit value %d: " % p.returncode \
                    + stderr
                self.set_passed(self.PENDING, msg)
                return

            m4_lines = stdout.splitlines(False)
            m4_lines = map(lambda x: x.strip('('), m4_lines)
            for m4_line in m4_lines:
                line, m4 = m4_line.split(':')

                if not m4 in self.warn_items:
                    self.warn_items[m4] = []

                self.warn_items[m4].append({
                    'file': shorter_configure(configure_ac),
                    'line': int(line),
                })

    def generate_pretty_output(self):
        '''
        take the results from self.warn_items and generate at pretty looking
        message
        '''

        output = ""

        for item in self.warn_items.keys():
            positions = self.warn_items[item]

            hit = item + " found in: "

            first = True
            for pos in positions:
                if first:
                    first = False
                else:
                    hit = hit + ', '
                hit = hit + pos['file'] + ':' + str(pos['line'])

            output = output + _prepend_indent(self.text_wrap(hit))
            output = output + "\n"

        return output

    def run(self):
        ''' standard entry point for each check '''
        self.set_passed(self.NA)

        self.find_used_tools()
        if not self.used_tools:
            return

        # trace for warnings
        self.trace()

        if not len(self.warn_items):
            self.set_passed(self.PASS)
            return

        msg = "Some obsoleted macros found, see the attachment."
        output = self.generate_pretty_output()
        attachment = self.Attachment("AutoTools: Obsoleted m4s found", output)
        self.set_passed(self.FAIL, msg, [attachment])
        return

# vim: set expandtab ts=4 sw=4 tw=79:
