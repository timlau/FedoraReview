import os
import sys

if os.path.exists('../src'):
    srcpath = '../src'
elif os.path.exists('../../../lib/python2.7/site-packages/FedoraReview/src'):
    srcpath = '../../../lib/python2.7/site-packages/FedoraReview/src'
else:
    assert False, "Can't find src path"
sys.path.insert(0,os.path.abspath(srcpath))
