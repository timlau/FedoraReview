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
Spec file management.
'''

import re
import rpm

from settings import Settings


def _lines_in_string(s, raw):
    ''' Return either plain s (raw) or stripped, non-empty item list. '''
    if raw:
        return s
    return [l.strip() for l in s.split('\n') if l]


class SpecFile(object):
    '''
    Wrapper class for getting information from a .spec file.'
    All get_* methods operates on the python binding to the spec,
    whereas the find_* methods works on the raw lines of spec data.
    Properties:
       - filename: spec path
       - lines: all lines in spec, raw data.
       - spec: rpm python spec object.
    '''
    # pylint: disable=W0212

    def __init__(self, filename):
        self.log = Settings.get_logger()
        self.filename = filename
        self.lines = []
        self._get_lines(filename)

        self.spec = rpm.TransactionSet().parseSpec(self.filename)
        self.name_vers_rel = [self.expand_tag(rpm.RPMTAG_NAME),
                              self.expand_tag(rpm.RPMTAG_VERSION),
                              self.expand_tag(rpm.RPMTAG_RELEASE)]
        pkg_list = [p.header[rpm.RPMTAG_NAME] for p in self.spec.packages]
        pkg_list = [p for p in pkg_list if self.get_files(p) != None]
        self._packages = pkg_list

    name = property(lambda self: self.name_vers_rel[0])
    version = property(lambda self: self.name_vers_rel[1])
    release = property(lambda self: self.name_vers_rel[2])

    def _get_lines(self, filename):
        ''' Read line from specfile, fold \ continuation lines. '''
        with open(filename, "r") as f:
            lines = f.readlines()
        last = None
        for line in lines:
            line = line.strip()
            if last:
                self.lines[last] += line
            else:
                self.lines.append(line)
            if line.endswith('\\'):
                last = len(self.lines) - 1
                self.lines[last] = self.lines[last][:-1]
            else:
                last = None

    def _get_pkg_by_name(self, pkg_name):
        '''
        Return package with given name. pgk_name == None
        -> base package, not existing name -> KeyError
        '''
        if not pkg_name:
            return self.spec.packages[0]
        for p in self.spec.packages:
            if p.header[rpm.RPMTAG_NAME] == pkg_name:
                return p
        raise KeyError(pkg_name + ': no such package')

    def _get_sources(self, _type='Source'):
        ''' Get SourceX/PatchX lines with macros resolved '''
        result = {}
        for (url, num, flags) in self.spec.sources:
            # rpmspec.h, rpm.org ticket #123
            srctype = "Source" if flags & 1 else "Patch"
            if _type != srctype:
                continue
            tag = srctype + str(num)
            result[tag] = self.spec.sourceHeader.format(url)
        return result

    def _parse_files_pkg_name(self, line):
        ''' Figure out the package name in a %files line. '''
        tokens = line.split()
        assert tokens.pop(0) == '%files'
        while tokens:
            token = tokens.pop(0)
            if len(tokens) == 0:
                return self.base_package + '-' + token
            elif token == '-n':
                return tokens.pop(0)
            elif token == '-f':
                tokens.pop(0)
        self.log.warning("Cannot parse %files line: " + line)

    def _parse_files(self, pkg_name):
        ''' Parse and return the %files section for pkg_name.
            Return [] for empty file list, None for no matching %files.
        '''
        if not pkg_name:
            pkg_name = self.name
        lines = None
        for line in [l.strip() for l in self.lines]:
            if lines == None:
                if line.startswith('%files'):
                    if self._parse_files_pkg_name(line) == pkg_name:
                        lines = []
                continue
            line = rpm.expandMacro(line)
            if line.startswith('%'):
                token = re.split('\s|\(', line)[0]
                if not token in ['%ghost', '%doc', '%docdir',
                '%verify', '%attr', '%config', '%dir', '%defattr']:
                    break
                else:
                    lines.append(line)
            elif line:
                lines.append(line)
        return lines

    @property
    def base_package(self):
        ''' Base package name, normally %{name} unless -n is used. '''
        return  self.spec.packages[0].header[rpm.RPMTAG_NAME]

    @property
    def sources_by_tag(self):
        ''' Return dict of source_url[tag]. '''
        return self._get_sources('Source')

    @property
    def patches_by_tag(self):
        ''' Return dict of patch_url[tag]. '''
        return self._get_sources('Patch')

    def expand_tag(self, tag, pkg_name=None):
        '''
        Return value of given tag in the spec file, or None. Parameters:
          - tag: tag as listed by rpm --querytags, case-insensitive or
            a  constant like rpm.RPMTAG_NAME.
          - package: A subpackage, as listed by get_packages(), defaults
            to the  base package.
        '''
        if not pkg_name:
            header = self.spec.sourceHeader
        else:
            header = self._get_pkg_by_name(pkg_name).header
        try:
            return header[tag]
        except ValueError:
            return None
        except rpm._rpm.error:
            return None

    @property
    def packages(self):
        ''' Return list of package names built by this spec. '''
        return self._packages

    @property
    def build_requires(self):
        ''' Return the list of build requirements. '''
        return self.spec.sourceHeader[rpm.RPMTAG_REQUIRES]

    def get_requires(self, pkg_name=None):
        ''' Return list of requirements i. e., Requires: '''
        package = self._get_pkg_by_name(pkg_name)
        return package.header[rpm.RPMTAG_REQUIRES]

    def get_files(self, pkg_name=None):
        ''' Return %files section for base or specified package.
            Returns [] for empty section, None for not found.
        '''
        try:
            files = self._get_pkg_by_name(pkg_name).fileList
            return \
                [l for l in [f.strip() for f in files.split('\n')] if l]
        except AttributeError:
            # No fileList attribute...
            # https://bugzilla.redhat.com/show_bug.cgi?id=857653
            return self._parse_files(pkg_name)

    def get_section(self, section, raw=False):
        '''
        Get a section in the spec file ex. %install, %clean etc. If
        raw is True, returns single string verbatim from spec.
        Otherwise returns list of stripped and non-empty lines.
        '''
        if section.startswith('%'):
            section = section[1:]
        try:
            section = getattr(self.spec, section)
        except AttributeError:
            return None
        return _lines_in_string(section, raw)

    def find(self, regex, flags=re.IGNORECASE):
        '''
        Return first raw line in spec matching regex or None.
          - regex: compiled regex or string.
          - flags: used when regex is a string to control search.
        '''
        if isinstance(regex, str):
            regex = re.compile(regex, flags)
        for line in self.lines:
            if regex.search(line):
                return line.strip()
        return None

    def find_all(self, regex, skip_changelog=False):
        ''' Return list of all raw lines in spec matching regex or []. '''
        if isinstance(regex, str):
            regex = re.compile(regex, re.IGNORECASE)
        result = []
        for line in self.lines:
            if skip_changelog:
                if line.lower().strip().startswith('%changelog'):
                    break
            if regex.search(line):
                result.append(line.strip())
        return result

# vim: set expandtab: ts=4:sw=4:
