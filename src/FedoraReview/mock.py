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
Tools for helping Fedora package reviewers
'''

import logging
import os
import os.path

from glob import glob
from urlparse import urlparse
from subprocess import call, Popen, PIPE, STDOUT

from settings import Settings
from helpers import Helpers


_RPMLINT_SCRIPT="""
mock  @config@ --shell << 'EOF'
echo 'rpmlint:'
rpmlint @rpm_names@
echo 'rpmlint-done:'
EOF
"""

class _Mock(Helpers):
    """ Some basic operations on the mock chroot env, a singleton. """

    def __init__(self):
        Helpers.__init__(self)

        ''' Read mock configuration to get mock root. '''
        config_opts= {}
        with open('/etc/mock/default.cfg') as f:
            config = f.read()
        exec config
        self.mock_root = config_opts['root']

    def _get_dir(self, subdir=None):
        if Settings.mock_config:
            p = os.path.join( '/var/lib/mock', Settings.mock_config )
        else:
            p = os.path.join( '/var/lib/mock', self.mock_root )
        p = os.path.join(p, subdir) if subdir else p
        if not os.path.exists(p):
            os.makedirs(p)
        return p

    def get_resultdir(self):
        return self._get_dir('result')

    def get_builddir(self, subdir=None):
        """ Return the directory which corresponds to %_topdir inside
        mock. Optional subdir argument is added to returned path.
        """
        p = self._get_dir('root/builddir/build')
        return os.path.join(p, subdir) if subdir else p

    """  The directory where mock leaves built rpms and logs """
    resultdir=property(get_resultdir)

    """ Mock's %_topdir seen from the outside. """
    topdir = property(lambda self: get_builddir(self))

    def install(self, rpm_files):
        """
        Run  'mock install' on a list of files, return None if
        OK, else the stdout+stderr
        """
        cmd = ["mock", "install"]
        if Settings.mock_config:
             cmd.extend(['-r', Settings.mock_config])
        cmd.extend(rpm_files)
        self.log.debug('Command: ' + ' '.join(cmd))
        try:
            p = Popen(cmd, stdout=PIPE, stderr=STDOUT)
            output, error = p.communicate()
            if Settings.verbose:
                txt = "Install output: "
                txt += output if output else ''
                txt += error if error else ''
                print txt
        except OSError as e:
            if Settings.verbose:
                txt = "Install output: "
                txt += output if output else ''
                txt += error if error else ''
                print txt
            return output[0]
        if p.returncode != 0:
            logging.warning("Install command returned error code %i",
                            p.returncode)
        return None if p.returncode == 0 else output

    def _run(self, script):
        """ Run a script,  return (ok, output). """
        try:
            p = Popen(script, stdout=PIPE, stderr=STDOUT, shell=True)
            output, error = p.communicate()
        except OSError as e:
            return False, e.strerror
        return True, output

    def rpmlint_rpms(self, rpms):
        """ Install and run rpmlint on  packages,
        Requires packages already installed.
        Return (True,  text) or (False, error_string)"""

        error =  self.install(['rpmlint'])
        if error:
            return False, error

        script = _RPMLINT_SCRIPT
        basenames = [ os.path.basename(r) for r in rpms]
        names = [r.rsplit('-', 2)[0] for r in basenames]
        rpm_names = ' '.join(list(set(names)))
      
        config = ''
        if Settings.mock_config:
            config = '-r ' + Settings.mock_config 
        script = script.replace('@config@', config)
        script = script.replace('@rpm_names@', rpm_names)
        ok, output = self._run(script)
        self.log.debug( "Script output: " + output)

        if not ok:
            return False, output + '\n'

        ok, err_msg = self.check_rpmlint_errors(output)
        if err_msg:
            return False, err_msg

        lines = output.split('\n')
        l = ''
        while not l.startswith('rpmlint:') and len(lines) > 0:
            l = lines.pop(0)
        text = ''
        for l in lines:
            if l.startswith('<mock-'):
                l=l[l.find('#'):]
            if l.startswith('rpmlint-done:'):
                break
            text += l + '\n'
        return ok, text

    def have_cache_for(self, name):
        ''' return true if there is at least one srpm and one rpm in
        resultdir, prefixed with the given name
        '''
        path = self.get_resultdir()
        if len(glob(os.path.join(path, name + '*.src.rpm'))) == 0:
             return False
        return len(glob(os.path.join(path, name +'*.rpm'))) >= 2

    def builddir_cleanup(self):
        ''' Remove broken symlinks left by mock command. '''
        paths = glob(os.path.join(self.get_builddir('BUILD'), '*'))
        for p in paths:
           try:
              os.stat(p)
           except:
              try:
                  os.lstat(p)
                  os.unlink(p)
              except:
                   pass


Mock = _Mock()

# vim: set expandtab: ts=4:sw=4:
