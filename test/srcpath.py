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
#    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#    MA 02110-1301 USA.
#
# pylint: disable=C0103,R0904,R0913
''' Insert path to package into sys.path. '''

import os
import sys

from distutils.sysconfig import get_python_lib

if os.path.exists('../src'):
    SRC_PATH = os.path.abspath('../src')
    REVIEW_PATH = os.path.abspath('../src/fedora-review')
    PLUGIN_PATH = os.path.abspath('..')
else:
    SRC_PATH = os.path.join(get_python_lib(), 'FedoraReview')
    PLUGIN_PATH = SRC_PATH
    REVIEW_PATH = '/usr/bin/fedora-review'
assert os.path.exists(SRC_PATH), "Can't find src path"
sys.path.insert(0, SRC_PATH)

# vim: set expandtab ts=4 sw=4:
