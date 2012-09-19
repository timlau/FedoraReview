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
Binary rpm file management.
'''

import os
import rpm

from mock import Mock
from settings import Settings


class RpmFile(object):
    '''
    Wrapper class for getting information from a binary RPM file
    '''
    # pylint: disable=W0212

    def __init__(self, pkg_name, version, release):
        ''' Create a RPM wrapper given a package name. '''
        self.log = Settings.get_logger()
        self._inited = False
        self.name = pkg_name
        self.version = version
        self.release = release
        self.filename = None
        self.header = None

    def init(self):
        ''' Lazy init, we have no rpms until they are built. '''
        if self._inited:
            return
        self.filename = Mock.get_package_rpm_path(self.name, self)
        fd = os.open(self.filename, os.O_RDONLY)
        self.header = rpm.TransactionSet().hdrFromFdno(fd)
        os.close(fd)
        self._inited = True

    def _scriptlet(self, prog_tag, script_tag):
        ''' Return inline -p script, script or None. '''
        self.init()
        prog = self.header[prog_tag]
        script = self.header[script_tag]
        if prog and script:
            return prog + script
        if prog:
            return prog
        return script

    @property
    def posttrans(self):
        ''' Return postTrans scriptlet. '''
        return self._scriptlet(rpm.RPMTAG_POSTTRANSPROG,
                               rpm.RPMTAG_POSTTRANS)

    @property
    def pretrans(self):
        ''' Return preTrans scriptlet. '''
        return self._scriptlet(rpm.RPMTAG_PRETRANSPROG,
                               rpm.RPMTAG_PRETRANS)

    @property
    def postun(self):
        ''' Return postUn scriptlet. '''
        return self._scriptlet(rpm.RPMTAG_POSTUNPROG,
                               rpm.RPMTAG_POSTUN)

    @property
    def preun(self):
        ''' Return preUn scriptlet. '''
        return self._scriptlet(rpm.RPMTAG_PREUNPROG,
                               rpm.RPMTAG_PREUN)

    @property
    def post(self):
        ''' Return post scriptlet. '''
        return self._scriptlet(rpm.RPMTAG_POSTINPROG,
                               rpm.RPMTAG_POSTIN)

    @property
    def pre(self):
        ''' Return pre scriptlet. '''
        return self._scriptlet(rpm.RPMTAG_PREINPROG,
                               rpm.RPMTAG_PREIN)

    def filelist(self):
        ''' List of files in this rpm (expanded). '''
        self.init()
        return self.header[rpm.RPMTAG_FILENAMES]

    @property
    def requires(self):
        ''' List of requires, also auto-generated for rpm. '''
        self.init()
        return self.header[rpm.RPMTAG_REQUIRES]

    @property
    def provides(self):
        ''' List of provides, also auto-generated for rpm. '''
        self.init()
        return self.header[rpm.RPMTAG_PROVIDES]


# vim: set expandtab: ts=4:sw=4:
