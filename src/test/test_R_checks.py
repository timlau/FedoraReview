#!/usr/bin/python -tt
#-*- coding: UTF-8 -*-

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
#    Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
'''
Unit checks for automatic test of fedora R review guidelines
'''


import sys
import os.path
sys.path.insert(0,os.path.abspath('../'))

import os
import shutil
import unittest


from FedoraReview import Settings, Checks, ReviewDirs, NameBug
from FedoraReview.checks import R

from test_env import no_net


class TestRChecks(unittest.TestCase):

    def setUp(self):
        self.startdir = os.getcwd()
        sys.argv = ['fedora-review','-rpn','R-Rdummypkg']
        os.chdir('test-R')
        if os.path.exists('R-Rdummypkg'):
             shutil.rmtree('R-Rdummypkg')
        Settings.init(True)
        self.log = Settings.get_logger()
        ReviewDirs.reset(os.getcwd())

    @unittest.skipIf(no_net, 'No network available')
    def test_all_checks(self):
        ''' Run all automated review checks'''
        self.bug = NameBug('R-Rdummypkg')
        self.bug.find_urls()
        self.bug.download_files()
        checks = Checks(self.bug.spec_file, self.bug.srpm_file)
        checks.run_checks(writedown=False)
        for check in checks.get_checks().itervalues():
            if hasattr(check, 'result'):
                if not(check.group == 'Generic' or check.group == 'R'):
                    continue
                result = check.result
                if not result:
                    continue
                self.assertTrue(result.result in ['pass', 'pending', 'fail']) 
        os.chdir('..')
        ReviewDirs.reset(self.startdir)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRChecks)
    unittest.TextTestRunner(verbosity=2).run(suite)
