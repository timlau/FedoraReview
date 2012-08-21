#!/usr/bin/env python
#
# Create the file version if it does not exist.
# In any case, exec this file, providing symbols defined
# there on module level.

import logging
import os.path
import os
import socket
import sys

from subprocess import check_output
from review_error import FedoraReviewError

class VersionError(FedoraReviewError):
    pass

def _init():
    try:
        bytes = check_output(['git', 'log', '--pretty=format:%h %ci', '-1'])
    except:
        raise VersionError("No version file and git not available.")
    line = bytes.decode('utf-8')
    words = line.split()
    commit = words.pop(0)
    date = words.pop(0)
    time = ' '.join(words)
    try:
        with open('version.tmpl') as f:
           template=f.read()
    except:
        raise VersionError('Cannot read version.tmpl')

    template = template.replace('@date@', date)
    template = template.replace('@time@', time)
    template = template.replace('@commit@', commit)
    template = template.replace('@host@', socket.gethostname())
    try:
        with open('version', 'w') as f:
            f.write(template)
    except:
        raise VersionError('Cannot write to version file')


old_wd = os.getcwd()
here = os.path.dirname(os.path.realpath(__file__))
os.chdir(here)
version_path = os.path.join(here, 'version')
if not os.path.exists(version_path):
    _init()
with open(version_path) as f:
    version_script = f.read()
exec( version_script )
os.chdir(old_wd)

# vim: set expandtab: ts=4:sw=4;

