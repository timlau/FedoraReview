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

'''  EL6+ compatibility layer '''

import sys

if sys.version < '2.7':
    def check_output(*popenargs, **kwargs):
        """Run command with arguments and return its output as a byte
        string.  Backported from Python 2.7.
        See https://gist.github.com/1027906
        """
        import subprocess
        process = subprocess.Popen(stdout=subprocess.PIPE,
                                   *popenargs,
                                   **kwargs)
        output = process.communicate()[0]
        retcode = process.poll()
        if retcode:
            cmd = kwargs.get("args")
            if cmd is None:
                cmd = popenargs[0]
            error = subprocess.CalledProcessError(retcode, cmd)
            error.output = output
            raise error
        return output
else:
    from subprocess import check_output

# vim: set expandtab: ts=4:sw=4:
