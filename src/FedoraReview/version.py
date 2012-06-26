#!/usr/bin/env python
#
# Create the file version if it does not exist.
# In any case, exec this file, providing symbols defined
# there on module level + the 'version' variable,
# the first part (no git commit) of the version

import os
import os.path

from review_error import FedoraReviewError

VERSION_PATTERN = '[0-9]+\.[0-9]+[.][0-9]'

class VersionError(FedoraReviewError):
    pass

def _init(where):
    from subprocess import check_output

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
        with open(os.path.join(where, 'version.tmpl')) as f:
           template=f.read()
    except:
        raise VersionError('Cannot read version.tmpl')

    template = template.replace('@date@', date)
    template = template.replace('@time@', time)
    template = template.replace('@commit@', commit)
    try:
        with open(os.path.join(where, 'version'), 'w') as f:
            f.write(template)
    except: 
        raise VersionError('Cannot write to version file')


here = os.path.dirname(os.path.realpath(__file__))
version_path = os.path.join(here, 'version')
if not os.path.exists(version_path):
    _init(here)
with open(version_path) as f:
    version_script = f.read()
exec( version_script )

if not 'build_version' in globals():
    import re
    build_version = re.match(VERSION_PATTERN, __version__).group(0)

# vim: set expandtab: ts=4:sw=4;

