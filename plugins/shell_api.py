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
Plugin module acting as an interface between, simple, shell-based plugins
and the regular python plugins.
'''

import os
import os.path
import re

from glob import glob
from subprocess import Popen, PIPE

from FedoraReview import AbstractRegistry, GenericCheck
from FedoraReview import ReviewDirs, Settings, XdgDirs


ENVIRON_TEMPLATE = """
FR_SETTINGS_generator
export FR_REVIEWDIR='@review_dir@'

export FR_NAME='@name@'
export FR_VERSION='@version@'
export FR_RELEASE='@release@'
export FR_GROUP='@group@'
export FR_LICENSE='@license@'
export FR_URL='@url@'

FR_SOURCE_generator
FR_PATCH_generator

export FR_PREP=@prep@
export FR_BUILD=@build@
export FR_INSTALL=@install@
export FR_PRE=@pre@
export FR_POST=@post@
export FR_PREUN=@preun@
export FR_POSTUN=@postun@
export FR_POSTTRANS=@posttrans@

FR_FILES_generator
FR_DESCRIPTION_generator
FR_PACKAGE_generator

export FR_FILES FR_DESCRIPTION FR_PACKAGE

export FR_PASS=80
export FR_FAIL=81
export FR_PENDING=82
export FR_NOT_APPLICABLE=83


function get_used_rpms()
# returns (stdout) list of used rpms if found, else returns 1
{
    cd $FR_REVIEWDIR
    if test  "${FR_SETTINGS[prebuilt]}" = True
    then
        files=( $(ls ../*.rpm 2>/dev/null | grep -v .src.rpm) ) \
               || files=( '@@' )
    else
        files=( $(ls results/*.rpm 2>/dev/null | grep -v .src.rpm) ) \
               || files=( '@@' )
    fi
    test -e ${files[0]} || return 1
    echo "${files[@]}"
    cd $OLDPWD
}

function unpack_rpms()
# Unpack all non-src rpms in results into rpms-unpacked, one dir per rpm.
{
    [ -d rpms-unpacked ] && return 0
    rpms=( $( get_used_rpms ) ) || return 1
    mkdir rpms-unpacked
    cd rpms-unpacked
    retval=0
    for rpm_path in ${rpms[@]};  do
        rpm=$( basename $rpm_path)
        mkdir $rpm
        cd $rpm
        rpm2cpio ../../$rpm_path | cpio -id &>/dev/null
        cd ..
    done
    cd ..
}

function unpack_sources()
# Unpack sources in upstream into upstream-unpacked
# Ignores (reuses) already unpacked items.
{
    sources=( $(cd upstream; ls) ) || sources=(  )
    if [[ ${#sources[@]} -eq 0 || ! -e "upstream/${sources[0]}" ]]; then
       return $FR_NOT_APPLICABLE
    fi
    for source in "${sources[@]}"; do
        mkdir upstream-unpacked/$source 2>/dev/null || continue
        rpmdev-extract -qfC  upstream-unpacked/$source upstream/$source || \
           cp upstream/$source upstream-unpacked/$source
    done
}


export -f unpack_rpms get_used_rpms unpack_sources

"""

ENV_PATH = 'review-env.sh'

_TAGS= ['name', 'version', 'release', 'group', 'license', 'url']
_SECTIONS = [ 'prep', 'build', 'install', 'pre', 'post',
             'preun', 'postun', 'posttrans']

_PASS = 80
_FAIL = 81
_PENDING = 82
_NOT_APPLICABLE = 83


class Registry(AbstractRegistry):

    def _create_env(self, spec, srpm):

        def quote(s):
            return s.replace("'", "'\\''")

        def settings_generator():
            body='declare -A FR_SETTINGS \n'
            for key in Settings.__dict__.iterkeys():
                if key.startswith('_'):
                    continue
                value = Settings.__dict__[key]
                if not value:
                    value=''
                body += 'FR_SETTINGS[%s]="%s"\n' %  (key, value)
            return body

        def source_generator():
            body = ''
            sources = spec.get_sources()
            for tag, path in sources.iteritems():
                body += 'export ' + tag + '="' + path + '"\n'
            return body

        def patch_generator():
            body = ''
            patches = spec.get_sources('Patch')
            for tag, path in patches.iteritems():
                body += 'export ' + tag + '="' + path + '"\n'
            return body

        def files_generator():
            body = 'declare -A FR_FILES\n'
            files = spec.get_section('%files')
            for section, lines in files.iteritems():
               item = ''
               for line in lines:
                    item += quote(line) + '\n'
               body += """FR_FILES[%s]='%s'\n""" % (section, item)
            return body

        def description_generator():
            body = 'declare -A FR_DESCRIPTION\n'
            descriptions = spec.get_section('%description')
            for section, lines in descriptions.iteritems():
               item = ''
               for line in lines:
                    item += quote(line) + '\n'
               body += """FR_DESCRIPTION[%s]='%s'\n""" % (section, item)
            return body

        def package_generator():
            body = 'declare -A FR_PACKAGE\n'
            packages = spec.get_section('%package')
            for section, lines in packages.iteritems():
               item = ''
               for line in lines:
                    item += quote(line) + '\n'
               body += """FR_PACKAGE[%s]='%s'\n""" % (section, item)
            return body

        env = ENVIRON_TEMPLATE
        env = env.replace('FR_SETTINGS_generator', settings_generator())
        env = env.replace('@review_dir@', ReviewDirs.root)
        for tag in _TAGS:
            try:
                value = spec.get_from_spec(tag.upper())
                env = env.replace('@' + tag  + '@', value)
            except:
                self.log.debug('Cannot get value for: ' + tag)
                env = env.replace('@' + tag  + '@','""')
        env = env.replace('FR_SOURCE_generator', source_generator())
        env = env.replace('FR_PATCH_generator', patch_generator())
        for s in _SECTIONS:
            body = ''
            section = '%' + s.strip()
            try:
                lines = spec.get_section(section)[section]
            except:
                lines = []
            for line in lines:
                body += quote(line) + '\n'
            body = "'" + body + "'"
            if len(body) <  5:
                body = ''
            env = env.replace('@' + s + '@', body)
        env = env.replace('FR_FILES_generator', files_generator())
        env = env.replace('FR_PACKAGE_generator', package_generator())
        env = env.replace('FR_DESCRIPTION_generator',
                          description_generator())
        with open(ENV_PATH, 'w') as f:
             f.write(env)

    def __init__(self, base):
        AbstractRegistry.__init__(self, base)
        self.groups = base.groups

    def _get_plugin_dirs(self):
        plugindir = os.path.dirname(__file__)
        plugindir = os.path.join(plugindir, '../scripts')
        plugindir = os.path.normpath(plugindir)
        path = plugindir + ':' + os.path.join(XdgDirs.app_datadir,
                                              'scripts')
        return path.split(':')

    def register(self, plugin):
        self.log = Settings.get_logger()
        dirs = self._get_plugin_dirs()
        checks = []
        if not Settings.list_checks:
            self._create_env(self.checks.spec, self.checks.srpm)
        for dir in dirs:
            dir = os.path.expanduser(dir)
            for f in glob(os.path.join(dir, '*.sh')):
                checks.append(ShellCheck(self.checks, f))
        return checks

class ShellCheck(GenericCheck):
    """ A single test  defined by a shell plugin. """
    DEFAULT_GROUP = 'Generic'
    DEFAULT_TYPE  = 'MUST'

    def __init__(self, checks, path):
        for tag in _TAGS:
           try:
               setattr(self, tag, tag + ' : undefined')
           except:
               pass
        GenericCheck.__init__(self, checks, path)
        self.implementation='shell'
        self.groups = checks.groups
        self.log = Settings.get_logger()
        self._parse(path)

    def _find_value(self, line, key):
        key = '@' + key + ':'
        if key in line:
            return re.sub('.*' + key, '', line).strip()
        return None

    def _parse_attributes(self, lines):
        self.type = self.DEFAULT_TYPE
        self.group = self.DEFAULT_GROUP
        self.text = ''
        for line in lines:
            for attr in ['group', 'url', 'type']:
                value = self._find_value(line, attr)
                if value:
                    setattr(self, attr, value)
            text = self._find_value(line, 'text')
            if text:
                if self.text:
                   self.text += ' '
                self.text +=  text
            list = self._find_value(line, 'deprecates')
            if list:
                self.deprecates = list.replace(',', ' ').split()
            list = self._find_value(line, 'needs')
            if list:
                self.needs = list.replace(',', ' ').split()

    def _parse(self, path):
        """
        Parse registration info for plugin with just one test, like:
        @name: test-name
        @group: java # generic, C/C++ etc
        @type: MUST|SHOULD|EXTRA
        @text :"User info, visible in listings"
        @test: "More text, appended to previous, w blank separator"
        @url: Guidelines URL, optional
        @deprecates: test1, test2, ...
        @needs: test4, test5, ...
        """

        with open(path) as f:
            lines = f.readlines()
        for line in lines:
            name = self._find_value(line, 'name')
            if name:
                break
        if not name:
            name = os.path.splitext(os.path.basename(path))[0]
        self._name = name
        self._parse_attributes(lines)

    def _do_run(self, cmd):
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        try:
            stdout,stderr = p.communicate()
        except:
            self.log.warning("Cannot execute " + cmd)
            self.log.debug("Cannot execute " + cmd, exc_info=True)
            return -1, None, None
        stdout = None if stdout == '' else stdout
        stderr = None if stderr == '' else stderr
        return p.returncode, stdout, stderr

    name = property(lambda self: self._name)

    def run(self):
        if hasattr(self, 'result'):
             return
        if not self.group in self.groups:
            self.set_passed("pending", "test run failed: illegal group")
            self.log.warning('Illegal group %s in %s' %
                                   (self.group, self.defined_in))
            return
        if not self.groups[self.group].is_applicable():
            self.set_passed('not_applicable')
            return
        cmd = 'source ./review-env.sh; ' + self.defined_in
        retval, stdout, stderr = self._do_run(cmd)
        if retval == -1:
            self.set_passed("pending",
                            "Cannot execute shell command" + cmd)
        elif retval == _PASS and not stderr:
            self.set_passed("pass", stdout)
        elif retval == _FAIL and not stderr:
            self.set_passed("fail", stdout)
        elif retval == _PENDING and not stderr:
            self.set_passed('pending', stdout)
        elif retval == _NOT_APPLICABLE and not stderr:
            self.set_passed('not_applicable', stdout)
        else:
            self.log.warning(
                'Illegal return from %s, code %d, output: %s' %
                     (self.defined_in, retval,
                     'stdout:' + str(stdout) + ' stderr:' + str(stderr)))
            self.set_passed('pending', 'Test run failed')

# vim: set expandtab: ts=4:sw=4:
