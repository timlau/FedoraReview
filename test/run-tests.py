#!/usr/bin/env python
#
# Run all tests, python version
#
# See: README.test for howto
#
# pylint: disable=C0103,W0611

''' Run tests wrapper module. '''

import os
import sys
import unittest2 as unittest

import srcpath                                   # pylint: disable=W0611
from FedoraReview import Mock

from test_misc     import TestMisc
from test_bugzilla import TestBugzilla
from test_checks   import TestChecks
from test_R_checks import TestRChecks
from test_options  import TestOptions
from test_dist     import TestDist
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

export PATH=/bin:/usr/bin:/sbin:/usr/sbin
Mock.init()

testFail = 0
for t in 'Misc', 'Bugzilla', 'Ext', 'Options', 'Checks', 'RChecks', \
         'Regressions', 'Dist':
    test = eval('unittest.TestLoader().loadTestsFromTestCase(Test%s)' % t)
    result = unittest.TextTestRunner(verbosity=VERBOSITY).run(test)
    testFail = testFail + len(result.errors) + len(result.failures)

sys.exit(testFail)
