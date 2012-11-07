#!/usr/bin/env python
"""
Setup script
"""
import os
import sys
MAIN_DIR = os.path.dirname(os.path.realpath(sys.argv[0]))
PKG_DIR = os.path.join(MAIN_DIR, 'src')
sys.path.insert(0, PKG_DIR)

from distutils.core import setup
from src.FedoraReview import __version__


def list_files_in_dir(dir_, extension):
    ''' Return recursive listing of all regular files under dir. '''
    file_list = []
    for filename in os.listdir(os.path.join(MAIN_DIR, dir_)):
        if filename.endswith(extension):
            file_list.append(os.path.join(dir_, filename))
    return file_list


setup(
    name = 'fedora-review',
    description = 'Tools to help review packages for inclusion in Fedora',
    data_files = [('/usr/share/man/man1/',
                      ['fedora-review.1', 'fedora-create-review.1']),
                  ('/usr/share/fedora-review/scripts',
                      list_files_in_dir('scripts', '.sh')),
                  ('/usr/share/fedora-review/plugins',
                      list_files_in_dir('plugins', '.py')),
        ],
    version = __version__,
    license = 'GPLv2+',
    download_url = 'https://fedorahosted.org/releases/F/e/FedoraReview/',
    url = 'https://fedorahosted.org/FedoraReview/',
    package_dir = {'FedoraReview': 'src/FedoraReview'},
    packages = ['FedoraReview'],
    package_data = {'': ['*.tmpl', 'version']},
    scripts = ["src/fedora-review", "src/fedora-create-review",
        "koji-download-scratch"],
    maintainer  = 'fedora-review maintainers',
    maintainer_email = 'fedorareview@lists.fedorahosted.org'
)
