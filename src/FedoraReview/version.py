#!/usr/bin/env python
#
'''
Create the file version if it does not exist.
In any case, exec this file, providing symbols defined
there on module level, redefining he 'unknown' defaults.
'''

import os.path
import os
import socket

try:
    from subprocess import check_output
except ImportError:
    from FedoraReview.el_compat import check_output

from review_error import ReviewError

__version__ = 'Unknown'
BUILD_FULL = 'Unknown (no version file nor git info)'
BUILD_DATE = "Unknown"
BUILD_ID = "Unknown"


class VersionError(ReviewError):
    ''' If we cannot deduce the version. '''
    pass


def _setup():
    ''' Setup  the 'version' file from version.tmpl. '''
    try:
        octets = check_output(['git', 'log', '--pretty=format:%h %ci', '-1'])
    except:
        raise VersionError("No version file and git not available.")
    line = octets.decode('utf-8')
    words = line.split()
    commit = words.pop(0)
    date = words.pop(0)
    time = ' '.join(words)
    try:
        with open('version.tmpl') as f:
            template = f.read()
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


def _init():
    ''' Possibly create version file, read and export it. '''
    old_wd = os.getcwd()
    here = os.path.dirname(os.path.realpath(__file__))
    os.chdir(here)
    version_path = os.path.join(here, 'version')
    if not os.path.exists(version_path):
        _setup()
    with open(version_path) as f:
        version_script = f.read()
    os.chdir(old_wd)
    return version_script


exec(_init())                                    # pylint: disable=W0122

# vim: set expandtab: ts=4:sw=4;
