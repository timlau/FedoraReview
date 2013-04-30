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
# (C) 2011 - Tim Lauridsen <timlau@fedoraproject.org>

''' Tools for helping Fedora package reviewers '''

# pylint: disable=R0924

import argparse
import grp
import logging
import errno
import os
import os.path
import re
import sys

import ansi
from review_error import ReviewError
from xdg_dirs import XdgDirs

PARSER_SECTION = 'review'

SESSION_LOG = os.path.join(XdgDirs.cachedir, 'fedora-review.log')


def _check_mock_grp():
    ''' Raise ReviewError unless mock installation is OK. '''

    mock_msg = \
        'No mock group - mock not installed or mock not in effective' \
        'groups. Try running  "newgrp" or logging out from all your local ' \
        'sessions and logging back in. Or disable test using ' \
        'REVIEW_NO_MOCKGROUP_CHECK, see manpage'

    if 'REVIEW_NO_MOCKGROUP_CHECK' in os.environ:
        return
    mock_gid = grp.getgrnam('mock')[2]
    if not mock_gid in os.getgroups():
        raise ReviewError(mock_msg)


def _add_modes(modes):
    ''' Add all mode arguments to the option parser group modes. '''
    modes.add_argument('-b', '--bug', metavar='<bug>',
                       help='Operate on fedora bugzilla using its bug number.')
    modes.add_argument('-n', '--name', metavar='<name>',
                       help='Use local files <name>.spec and <name>*.src.rpm'
                       ' in current dir or, when using --rpm-spec, use'
                       ' <name> as path to srpm.')
    modes.add_argument('-u', '--url', default = None, dest='url',
                       metavar='<url>',
                       help='Use another bugzilla, using complete'
                       ' url to bug page.')
    modes.add_argument('-d', '--display-checks', default = False,
                       action='store_true', dest='list_checks',
                       help='List all available checks.')
    modes.add_argument('-f', '--display-flags', default = False,
                       action='store_true', dest='list_flags',
                       help='List all available flags.')
    modes.add_argument('-V', '--version', default = False,
                       action='store_true',
                       help='Display version information and exit.')
    modes.add_argument('-h', '--help', action='help',
                       help = 'Display this help message')


def _add_optionals(optional):
    ''' Add all optional arguments to option parser group optionals. '''

    optional.add_argument('-B', '--no-colors', action='store_false',
                          help='No colors in output',
                          default=True, dest='use_colors')
    optional.add_argument('-c', '--cache', action='store_true',
                          dest='cache',
                          help = 'Do not redownload files from bugzilla,'
                          ' use the ones in the cache.')
    optional.add_argument('-D', '--define', metavar='<flag>',
                          action='append', dest='flags', default=[],
                          help = 'Define a flag like --define EPEL5 or '
                          ' -D EPEL5=1')
    optional.add_argument('-L', '--local-repo', metavar='<rpm directory>',
                          dest='repo',
                          help = 'directory with rpms to install together with'
                          ' reviewed package during build and install phases.')
    optional.add_argument('-m', '--mock-config', metavar='<config>',
                          dest='mock_config',
                          help='Configuration to use for the mock build,'
                          " defaults to 'default' i. e.,"
                          ' /etc/mock/default.cfg')
    optional.add_argument('--no-report', action='store_true',
                          help='Do not print review report.')
    optional.add_argument('--no-build', action='store_true',
                          dest='nobuild',
                          help = 'Do not rebuild or install the srpm, use last'
                          ' built one in mock. Implies --cache')
    optional.add_argument('-o', '--mock-options', metavar='<mock options>',
                          default = '--no-cleanup-after --no-clean',
                          dest='mock_options',
                          help='Options to specify to mock for the build,'
                          ' defaults to --no-cleanup-after --no-clean')
    optional.add_argument('--other-bz', default=None,
                          metavar='<bugzilla url>', dest='other_bz',
                          help='Alternative bugzilla URL')
    optional.add_argument('-p', '--prebuilt', action='store_true',
                          dest='prebuilt', default = False,
                          help='When using -n <name>, use'
                              ' prebuilt rpms in current directory.')
    optional.add_argument('-s', '--single', metavar='<test>',
                          help='Single test to run, as named by '
                          '--display-checks.')
    optional.add_argument('-r', '--rpm-spec', action='store_true',
                          dest='rpm_spec', default=False,
                          help='Take spec file from srpm instead of separate'
                          'url.')
    optional.add_argument('-v', '--verbose', action='store_true',
                          help='Show more output.', default=False,
                          dest='verbose')
    optional.add_argument('-x', '--exclude',
                          dest='exclude', metavar='"test,..."',
                          help='Comma-separated list of tests to exclude.')
    optional.add_argument('-k', '--checksum', dest='checksum',
                          default='sha256',
                          choices=['md5', 'sha1', 'sha224', 'sha256',
                                   'sha384', 'sha512'],
                          help='Algorithm used for checksum')


def _make_log_dir():
    ''' Create the log dir, unless it's already there. '''
    try:
        os.makedirs(os.path.dirname(SESSION_LOG))
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            pass
        else:
            raise ReviewError('Cannot create log directory: ' +
                              SESSION_LOG)


class ColoredFormatter(logging.Formatter):
    ''' Formatter usable for colorizing terminal output acccording to presets
    '''

    COLORS = {
        'WARNING': ansi.blue,
        'CRITICAL': ansi.red,
        'ERROR': ansi.red
    }

    def __init__(self, fmt=None, datefmt=None, use_color=True):
        logging.Formatter.__init__(self, fmt, datefmt)
        self.use_color = use_color and ansi.color_supported()

    def format(self, record):
        lname = record.levelname
        ret = logging.Formatter.format(self, record)
        if not ret.startswith(lname):
            ret = lname + ': ' + ret
        if self.use_color and lname in self.COLORS:
            ret = self.COLORS[lname](ret)
        return ret


class _Settings(object):                         # pylint: disable=R0902,R0924
    """
    FedoraReview singleton Config Setting based on command line options.
    All config values are accessed as attributes.
    """

    BZ_OPTS_MESSAGE = """
    The options --assign, --login and --user has been removed from
    fedora-review in favor of using the bugzilla tool instead. See
    fedora-review(1), section ASSIGN AND LOGIN and bugzilla(1).
    """

    class SettingsError(ReviewError):
        ''' Illegal options from user. '''
        def __init__(self):
            ReviewError.__init__(self, 'Bad options!!', 2, True)

    defaults = {
        'bz_url': 'https://bugzilla.redhat.com',
    }

    def __init__(self):
        '''Constructor of the Settings object.
        This instanciate the Settings object and load into the _dict
        attributes the default configuration which each available option.
        '''
        for key, value in self.defaults.iteritems():
            setattr(self, key, value)
        self._dict = self.defaults
        self.log = None
        self._con_handler = None
        self._log_config_done = None
        self.cache = None
        self.resultdir = None
        self.init_done = None
        self.uniqueext = None
        self.configdir = None
        self.log_level = None
        self.verbose = False
        self.name = None
        self.use_colors = False
        self.session_log = SESSION_LOG

    def __getitem__(self, key):
        my_key = self._get_hash(key)
        if not my_key:
            raise KeyError(key)
        return self._dict.get(my_key)

    def _fix_mock_options(self):
        '''
        Update resultdir, uniqueext and configdir from mock_options.
        '''
        self.resultdir = None
        self.uniqueext = None
        self.configdir = None
        if not self.mock_options:
            return
        m = re.search('--uniqueext=([^ ]+)', self.mock_options)
        self.uniqueext = '-' + m.groups()[0] if m else None
        m = re.search('--resultdir=([^ ]+)', self.mock_options)
        self.resultdir = m.groups()[0] if m else None
        m = re.search('--configdir=([^ ]+)', self.mock_options)
        self.configdir = m.groups()[0] if m else None
        if not 'no-cleanup-after' in self.mock_options:
            self.mock_options += ' --no-cleanup-after'
        if not 'no-cleanup-after' in self.mock_options:
            self.mock_options += ' --no-cleanup-after'
        if not re.search('clean($|[ ])', self.mock_options):
            self.mock_options += ' --no-clean'

    def init(self, force=False):
        ''' Delayed setup, to be called when sys.argv is ok...'''

        if self.init_done and not force:
            return

        self.do_logger_setup()
        for opt in ['--assign', '--login', '--user', '-a', '-i', '-l']:
            if opt in sys.argv:
                print self.BZ_OPTS_MESSAGE
                self.init_done = True
                raise self.SettingsError()
        parser = argparse.ArgumentParser(
            description='Review a package using Fedora Guidelines',
            add_help=False)

        mode = parser.add_argument_group('Operation mode - one is required')
        modes = mode.add_mutually_exclusive_group(required=True)
        optionals = parser.add_argument_group('General options')
        _add_modes(modes)
        _add_optionals(optionals)
        try:
            args = parser.parse_args()
        except:
            raise self.SettingsError()

        self.add_args(args)
        self.do_logger_setup(logging.DEBUG if args.verbose else None)
        if self.nobuild:
            self.cache = True
        if not self.prebuilt:
            _check_mock_grp()
        self._fix_mock_options()
        self.init_done = True

    def add_args(self, args):
        """ Load all command line options in args. """
        var_dict = vars(args)
        for key, value in var_dict.iteritems():
            setattr(self, key, value)

    @property
    def current_bz_url(self):
        ''' Effective value of --bz-url, not empty. '''
        return self.other_bz if self.other_bz else self.bz_url

    def dump(self):
        ''' Debug output of all settings. '''
        if not self.log:
            return
        self.log.debug("Active settings after processing options")
        for k, v in vars(self).iteritems():
            if k in ['_dict', 'mock_config_options', 'log']:
                continue
            try:
                self.log.debug("    " + k + ": " + v.__str__())
            except AttributeError:
                self.log.debug("    " + k + ": not printable")

    def do_logger_setup(self, lvl=None):
        ''' Setup Python logging. lvl is a logging.* thing like
        logging.DEBUG. If None, respects REVIEW_LOGLEVEL environment
        variable, defaulting to logging.INFO.
        '''
        msg = None
        if not lvl:
            if 'REVIEW_LOGLEVEL' in os.environ:
                try:
                    lvl = eval('logging.' +
                               os.environ['REVIEW_LOGLEVEL'].upper())
                except (ValueError, SyntaxError):
                    msg = "Cannot set loglevel from REVIEW_LOGLEVEL"
                    lvl = logging.INFO
            else:
                lvl = logging.INFO

        if not self._log_config_done:
            _make_log_dir()
            logging.basicConfig(level=logging.DEBUG,
                                format='%(asctime)s %(name)-12s'
                                       ' %(levelname)-8s %(message)s',
                                datefmt='%m-%d %H:%M',
                                filename= SESSION_LOG,
                                filemode='w')
        self._log_config_done = True

        self.log_level = lvl
        if lvl == logging.DEBUG:
            self.verbose = True
        self.log = logging.getLogger('')
        # define a Handler which writes INFO  or higher to sys.stderr
        console = logging.StreamHandler()
        console.setLevel(lvl)
        formatter = ColoredFormatter('%(message)s',
                                     "%H:%M:%S", self.use_colors)
        console.setFormatter(formatter)
        if self._con_handler:
            self.log.removeHandler(self._con_handler)
        self.log.addHandler(console)
        self._con_handler = console

        if msg:
            self.log.warning(msg)
        return True

    def get_logger(self):
        ''' Return the application logger instance. '''
        if not self.log:
            self.do_logger_setup()
        return self.log


Settings = _Settings()

# vim: set expandtab ts=4 sw=4:
