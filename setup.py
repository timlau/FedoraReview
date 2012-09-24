#!/usr/bin/env python
"""
Setup script
"""
import os
import sys
pkg_dir = os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])),
                       'src')
sys.path.insert(0, pkg_dir)


from distutils.core import setup
from src.FedoraReview import __version__


setup(
    name = 'fedora-review',
    description = 'Tools to help review packages for inclusion in Fedora',
    data_files = [('/usr/share/man/man1/', [ 'fedora-review.1', 'fedora-create-review.1' ] ) ],
    version = __version__,
    license = 'GPLv2+',
    download_url = 'https://fedorahosted.org/releases/F/e/FedoraReview/',
    url = 'https://fedorahosted.org/FedoraReview/',
    package_dir = {'FedoraReview': 'src/FedoraReview',
                   'plugins':'plugins'},
    packages = ['FedoraReview','plugins'],
    package_data = { '': ['*.tmpl','version']},
    scripts = ["src/fedora-review", "src/fedora-create-review",
        "koji-download-scratch"],
    maintainer  = 'fedora-review maintainers',
    maintainer_email = 'fedorareview@lists.fedorahosted.org'
)
