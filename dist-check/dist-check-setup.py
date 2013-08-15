#!/usr/bin/env python
#
# Create one subdirectory per fedora package usable as input for dist-check-run
# This is damned slow (1-2 hours for me), mostly sitting in repoquery. Needs
# some configuration.
#
# The complete output isn't that big (~100MB).
#
# pylint: disable=C0103,C0111,W1201,W0702,W0621

import multiprocessing
import os
import os.path
import shutil
import subprocess
import urllib

from BeautifulSoup import BeautifulSoup

ARCH = subprocess.check_output(['uname', '-i']).strip()

YUM_CMD = "yum --disablerepo=* --enablerepo=fedora* --releasever=rawhide"
BASE_URL = 'https://dl.fedoraproject.org/pub' \
                '/fedora/linux/development/rawhide/%s/os/Packages' % ARCH
REPOQUERY_CMD = "repoquery --disablerepo=* --enablerepo=fedora*" \
                    " --releasever=rawhide --archlist=%s" % ARCH


def find_subdirs(url):
    """ Locate subdir links in url) """
    tmpfile = urllib.urlretrieve(url)[0]
    soup = BeautifulSoup(open(tmpfile))
    links = soup.findAll('a')
    hrefs = map(lambda l: l['href'], links)
    found = []
    for href in hrefs:
        href = href.encode('ascii', 'ignore')
        if len(href) == 2 and href.endswith('/'):
            found.append(os.path.join(url, href[0]))
    return found


def find_rpmlinks(url):
    """ Locate rpm links in url """
    tmpfile = urllib.urlretrieve(url)[0]
    soup = BeautifulSoup(open(tmpfile))
    links = soup.findAll('a')
    hrefs = map(lambda l: l['href'], links)
    found = []
    for href in hrefs:
        href = href.encode('ascii', 'ignore')
        if href.endswith('rpm'):
            found.append(os.path.join(url, href))
    return found


def repoquery(pkg):
    ''' Find source rpm for a package using repoquery (slow!). '''
    cmd = REPOQUERY_CMD + " -C + -q --qf %{sourcerpm} " + pkg
    s = subprocess.check_output(cmd.split()).strip()
    if '\n' in s:
        cmd += '.' + ARCH
        s = subprocess.check_output(cmd.split()).strip()
    return s


def link2pkg(url):
    ''' Dig out package name from link. '''
    return url.rsplit('/', 1)[1].rsplit('-', 2)[0]


def add_pkg(pkg):
    ''' Add a pkg, possibly creating dir and srpm pkg ref. '''
    srpm = repoquery("-q --qf %{sourcerpm} " + pkg).strip()
    src_pkg = srpm.rsplit('-', 2)[0] if srpm else pkg
    if not os.path.exists(src_pkg):
        tmpdir = '%s.tmp.%d' % (src_pkg, os.getpid())
        os.mkdir(tmpdir)
        with open(tmpdir + '/srpm.url', 'w') as f:
            f.close()
        try:
            os.rename(tmpdir, src_pkg)
        except OSError:
            # This is a race condition: another thread might
            # have created the same dir. If so, just drop our stuff.
            shutil.rmtree(tmpdir)
    with open('%s/%s.url' % (src_pkg, pkg), 'w') as f:
        f.close()


cmd = YUM_CMD + " makecache"
subprocess.check_call(cmd.split())

pool = multiprocessing.Pool(8)
for d in find_subdirs(BASE_URL):
    for link in find_rpmlinks(d):
        pkg = link2pkg(link)
        pool.apply_async(add_pkg, (pkg,))
pool.close()
pool.join()
