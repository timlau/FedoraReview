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
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#    MA  02110-1301 USA.
#
# pylint: disable=C0103,R0904,R0913
''' Unit tests for creating dist '''

import os
import os.path
import sys
import unittest2 as unittest

from glob import glob
from subprocess import check_call

try:
    from subprocess import check_output
except ImportError:
    from FedoraReview.el_compat import check_output

from fr_testcase import FR_TestCase


def _proper_dist_os():
    ''' Return true if we can create a dist on this OS. '''
    uname_r = check_output(['uname', '-r']).decode('utf-8')
    if 'el6' in uname_r:
        return False
    return True


class TestDist(FR_TestCase):
    ''' Test creating installation artifacts. '''

    @unittest.skipIf(not _proper_dist_os(),
                     'Cannot make a dist (bad os)')
    def test_tarballs(self):
        ''' Test  make_release_script. '''
        os.chdir('..')
        check_call('./make_release -q >/dev/null', shell=True)
        self.assertEqual(len(glob('dist/*')), 3)
        lint = check_output(
                  'rpmlint -f test/rpmlint.conf dist/*spec dist/*rpm',
                  shell=True)
        self.assertIn('0 error', lint)
        self.assertIn('0 warning', lint)

    @staticmethod
    def dogfood():
        '''
        Run fedora-review on itself (not found by discover et. al.)
        '''
        os.chdir('..')
        check_call('./try-fedora-review -m fedora-17-i386' +
                       ' -o "--without tests"' +
                       ' -rn dist/fedora-review*.src.rpm',
                   shell=True)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        suite = unittest.TestSuite()
        for test in sys.argv[1:]:
            suite.addTest(TestDist(test))
    else:
        suite = unittest.TestLoader().loadTestsFromTestCase(TestDist)
    unittest.TextTestRunner(verbosity=2).run(suite)
