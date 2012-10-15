#!/usr/bin/env python
"""
Setup script
"""
import os
import sys
main_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
pkg_dir = os.path.join(main_dir, 'src')
sys.path.insert(0, pkg_dir)


from distutils.core import setup
from src.FedoraReview import __version__


def list_files_in_dir(dir, extension):
    file_list = []
    for filename in os.listdir(os.path.join(main_dir, dir)):
        if filename.endswith(extension):
            file_list.append(os.path.join(dir, filename))
    return file_list

def list_datafiles():
    filelist = [('/usr/share/man/man1/',
                    [ 'fedora-review.1', 'fedora-create-review.1' ] ),
                ('/usr/share/fedora-review/scripts',
                    list_files_in_dir('scripts', '.sh')),
                ('/usr/share/fedora-review/plugins',
                    list_files_in_dir('plugins', '.py'))]
    for root, dirs, files in os.walk('test'):
        filelist.append((os.path.join('/usr/share/fedora-review', root),
                             [os.path.join(root, f) for f  in files]))
    return filelist

setup(
    name = 'fedora-review',
    description = 'Tools to help review packages for inclusion in Fedora',
    data_files = list_datafiles(),
    version = __version__,
    license = 'GPLv2+',
    download_url = 'https://fedorahosted.org/releases/F/e/FedoraReview/',
    url = 'https://fedorahosted.org/FedoraReview/',
    package_dir = {'FedoraReview': 'src/FedoraReview'},
    packages = ['FedoraReview'],
    package_data = { '': ['*.tmpl','version']},
    scripts = ["src/fedora-review", "src/fedora-create-review",
        "koji-download-scratch"],
    maintainer  = 'fedora-review maintainers',
    maintainer_email = 'fedorareview@lists.fedorahosted.org'
)
