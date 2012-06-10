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


VERBOSITY = 2

Mock.init()

misc = unittest.TestLoader().loadTestsFromTestCase(TestMisc)
unittest.TextTestRunner(verbosity=VERBOSITY).run(misc)

bugzilla = unittest.TestLoader().loadTestsFromTestCase(TestBugzilla)
unittest.TextTestRunner(verbosity=VERBOSITY).run(bugzilla)

checks = unittest.TestLoader().loadTestsFromTestCase(TestChecks)
unittest.TextTestRunner(verbosity=VERBOSITY).run(checks)

r_checks = unittest.TestLoader().loadTestsFromTestCase(TestRChecks)
unittest.TextTestRunner(verbosity=VERBOSITY).run(r_checks)
