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
# To disable slow tests:
#     $ export REVIEW_FAST_TEST=1
#     $ ./run-tests.py
#
# Running a single test file:
#     $ python -m unittest test_misc
#
# Running a single test case:
#     $ python -m unittest test_misc.TestMisc.test_sources

import sys
import os.path
os.chdir(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0,os.path.abspath('../'))

import unittest

from FedoraReview  import Mock

from test_misc     import TestMisc
from test_bugzilla import TestBugzilla
from test_checks   import TestChecks
from test_R_checks import TestRChecks
from test_options  import TestOptions
from test_ext      import TestExt
from test_regressions import TestRegressions

VERBOSITY = 2

import fr_testcase

if fr_testcase.NO_NET:
    print "Warning:  No network available, only some tests run"
if not 'REVIEW_LOGLEVEL' in os.environ:
    print "Warning:  REVIEW_LOGLEVEL not set, lot's of output ahead."
if fr_testcase.FAST_TEST:
    print "Warning: slow tests skipped"


Mock.init()

testFail = 0
for t in 'Misc', 'Bugzilla', 'Ext', 'Options','Checks', 'RChecks',\
         'Regressions':
   test = eval( 'unittest.TestLoader().loadTestsFromTestCase(Test%s)' % t)
   result = unittest.TextTestRunner(verbosity=VERBOSITY).run(test)
   testFail = testFail + len(result.errors) + len(result.failures)

sys.exit(testFail)
