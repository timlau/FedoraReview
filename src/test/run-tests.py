#!/usr/bin/env python
#
# Run all tests, python version
#
# Occasionally, mock is locked in a bad state, making tests
# fail.  To recover:
#
#     # rm -rf /var/lib/mock/*
#     $ mock --init
#
# To filter output when running as normal:
#     $ export REVIEW_LOGLEVEL=warning
#     $ ./run-tests.py
#
# To display lot's of data when hunting down bugs:
#     $ export REVIEW_LOGLEVEL=debug
#     $ ./run-tests.py
#
# Running a single test file:
#     $ python -m unittest test_misc
#
# Running a single test case:
#     $ python -m unittest test_misc.TestMisc.test_sources

import sys
import os.path
sys.path.insert(0,os.path.abspath('../'))

import unittest

from FedoraReview  import Mock

from test_misc     import TestMisc
from test_bugzilla import TestBugzilla
from test_checks   import TestChecks
from test_R_checks import TestRChecks
from test_options  import TestOptions
from test_util     import TestUtil


VERBOSITY = 2

Mock.init()

for t in 'Misc', 'Bugzilla', 'Checks', 'RChecks', 'Options', 'Util':
   test = eval( 'unittest.TestLoader().loadTestsFromTestCase(Test%s)' % t)
   unittest.TextTestRunner(verbosity=VERBOSITY).run(test)
