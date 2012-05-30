#!/bin/sh
# Run all tests
#
#
set -x
export REVIEW_LOGLEVEL=warning
python -m unittest -v test-misc.TestMisc
python -m unittest -v test-checks.TestChecks
python -m unittest -v test-bugzilla.TestBugzilla
python -m unittest -v test-R-checks.TestRChecks
