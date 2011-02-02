#!/usr/bin/python -tt
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

TEST_BUG=672280
TEST_SPEC='http://timlau.fedorapeople.org/files/test/review-test/python-test.spec'
TEST_SRPM='http://timlau.fedorapeople.org/files/test/review-test/python-test-1.0-1.fc14.src.rpm'
TEST_SRC='http://timlau.fedorapeople.org/files/test/review-test/python-test-1.0.tar.gz'
TEST_WORK_DIR = os.path.abspath('test-work/')+'/'
