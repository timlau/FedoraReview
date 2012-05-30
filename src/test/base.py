#!/usr/bin/python -tt
#-*- coding: UTF-8 -*-

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
Common code and vars used by unit tests
'''
import os

BASE_URL = 'https://fedorahosted.org/releases/F/e/FedoraReview/'

TEST_BUG = '672280'
TEST_SPEC = BASE_URL + 'python-test.spec'
TEST_SRPM = BASE_URL + 'python-test-1.0-1.fc16.src.rpm'
TEST_SRC = BASE_URL + 'python-test-1.0.tar.gz'
TEST_WORK_DIR = os.path.abspath('test-work/')+'/'

R_TEST_SRPM = BASE_URL + 'R-Rdummypkg-1.0-1.fc16.src.rpm'
R_TEST_SPEC = BASE_URL + 'R-Rdummypkg.spec'
R_TEST_SRC = BASE_URL + 'Rdummypkg_1.0.tar.gz'
