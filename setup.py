#!/usr/bin/env python
"""
Setup script
"""

from distutils.core import setup


setup(
    name = 'FedoraReview',
    description = 'Tools to help review packages for inclusion in Fedora',
    description_long = '',
    data_files = [('/usr/share/man/man1/', [ 'fedora-review.1' ] ) ],
    version = '0.1.0',
    license = 'GPLv2+',
    download_url = 'https://fedorahosted.org/releases/F/e/FedoraReview/',
    url = 'https://fedorahosted.org/FedoraReview/',
    package_dir = {'FedoraReview': 'src/FedoraReview'},
    packages = ['FedoraReview', 'FedoraReview.checks'],
    scripts=["src/fedora-review"],
    )
