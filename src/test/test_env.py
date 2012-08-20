#!/usr/bin/python -tt
#-*- coding: utf-8 -*-

#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
# (C) 2011 - Tim Lauridsen <timlau@fedoraproject.org>
'''
Unit tests for bugzilla bug handling
'''
import os.path
import os
import subprocess

from urllib import urlopen

no_net = None

try:
    urlopen('http://bugzilla.redhat.com')
    no_net  = False
except:
    no_net = True

def check_python_test():
    # re-recreate a cached build for python-test in python-test.repo
    if not os.path.exists('python-test.repo/python-test'):
        print "\nInitiating python-test.repo/python-test"
        os.chdir('python-test.repo')
        subprocess.check_call(
                     '../../fedora-review --no-build -rpcn python-test',
                     shell=True)
        os.chdir('..')
