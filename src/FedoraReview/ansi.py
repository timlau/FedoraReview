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
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

''' ANSI colored terminal output support '''
# pylint: disable=W1401

BLACK   = "\033[1;30m"
RED     = "\033[1;31m"
GREEN   = "\033[1;32m"
YELLOW  = "\033[1;33m"
BLUE    = "\033[1;34m"
MAGENTA = "\033[1;35m"
CYAN    = "\033[1;36m"
WHITE   = "\033[1;37m"
RESET   = "\033[0m"


def black(s):
    ''' Return s with optional ansi chars to print in black. '''
    return BLACK + s + RESET


def green(s):
    ''' Return s with optional ansi chars to print in green. '''
    return GREEN + s + RESET


def yellow(s):
    ''' Return s with optional ansi chars to print in yellow. '''
    return YELLOW + s + RESET


def blue(s):
    ''' Return s with optional ansi chars to print in blue. '''
    return BLUE + s + RESET


def magenta(s):
    ''' Return s with optional ansi chars to print in magenta. '''
    return MAGENTA + s + RESET


def red(s):
    ''' Return s with optional ansi chars to print in red. '''
    return RED + s + RESET


def cyan(s):
    ''' Return s with optional ansi chars to print in cyan. '''
    return CYAN + s + RESET


def white(s):
    ''' Return s with optional ansi chars to print in white. '''
    return WHITE + s + RESET
