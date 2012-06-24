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

'''
Tools for helping Fedora package reviewers
'''

import argparse
import grp
import logging
import os.path
import re
import sys

from review_error import FedoraReviewError, CleanExitError

SYS_PLUGIN_DIR = "/usr/share/fedora-review/plugins:%s"
MY_PLUGIN_DIR  = "~/.config/fedora-review/plugins"

PARSER_SECTION = 'review'

LOG_ROOT = 'FedoraReview'

# REVIEW_LOGFILE is intentionally hidden from UI and manpage...
SESSION_LOG = os.environ['REVIEW_LOGFILE'] \
                  if 'REVIEW_LOGFILE' in os.environ \
              else os.path.expanduser('~/.cache/fedora-review.log')


class ConfigError(FedoraReviewError):
    def __init__(self, what):
        FedoraReviewError.__init__(self, 'Configuration error: ' + what)


class _Settings(object):
    """
    FedoraReview singleton Config Setting based on command line options.
    All config values are accessed as attributes.
    """

    defaults = {
        'ext_dirs':     ':'.join([os.path.expanduser(MY_PLUGIN_DIR),
                                                     SYS_PLUGIN_DIR]),
        'bz_url':       'https://bugzilla.redhat.com',
        'user':         None,
        'verbose':      False
    }

    def __init__(self):
        '''Constructor of the Settings object.
        This instanciate the Settings object and load into the _dict
        attributes the default configuration which each available option.
        '''
        for key,value in self.defaults.iteritems():
            setattr(self, key, value)
        self._dict = self.defaults

    def __getitem__(self, key):
        hash = self._get_hash(key)
        if not hash:
            raise KeyError(key)
        return self._dict.get(hash)

    def _populate(self):
        '''Set option values from a INI file section.

        :arg parser: ConfigParser instance (or subclass)
        :arg section: INI file section to read use.
        '''
        if self.parser.has_section(PARSER_SECTION):
            opts = set(self.parser.options(PARSER_SECTION))
        else:
            opts = set()

        for name in self._dict.iterkeys():
            value = None
            if name in opts:
                value = self.parser.get(PARSER_SECTION, name)
                setattr(self, name, value)
                self.parser.set(PARSER_SECTION, name, value)
            else:
                self.parser.set(PARSER_SECTION, name, self._dict[name])

    def init(self, force=False):
        ''' Delayed setup, to be called when sys.argv is ok...'''

        def _check_mock_grp():
            try:
                mock_gid = grp.getgrnam('mock')[2]
                if not mock_gid in os.getgroups():
                    raise ConfigError( 'Not in mock group, see manpage')
            except:
                raise ConfigError('No mock group - mock not installed?')

        if hasattr(self, 'init_done') and not force:
             return

        self.do_logger_setup()
        parser = argparse.ArgumentParser(
                    description='Review a package using Fedora Guidelines',
                    add_help=False)

        mode =  parser.add_argument_group('Operation mode - one is required')
        modes =  mode.add_mutually_exclusive_group(required=True)
        optional =  parser.add_argument_group('General options')
        bz_only = parser.add_argument_group(
                     'Only to be used with bugzilla.redhat.com i. e., --bug')
        modes.add_argument('-b', '--bug', metavar='<bug>',
                    help='Operate on fedora bugzilla using its bug number.')
        modes.add_argument('-n', '--name', metavar='<name>',
                    help='Use local files <name>.spec and'
                         ' <name>*.src.rpm in current dir.')
        modes.add_argument('-u', '--url', default = None, dest='url',
                    metavar='<url>',
                     help='Use another bugzilla, using complete'
                          ' url to bug page.')
        modes.add_argument('-d','--display-checks', default = False,
                    action='store_true',dest='list_checks',
                    help='List all available checks.')
        modes.add_argument('-V', '--version', default = False,
                    action='store_true',
                    help='Display version information and exit.')
        modes.add_argument('-h','--help', action='help',
                    help = 'Display this help message')
        optional.add_argument('-c','--cache', action='store_true', dest='cache',
                    help = 'Do not redownload files from bugzilla,'
                           ' use the ones in the cache.')
        optional.add_argument('-m','--mock-config', metavar='<config>',
                    dest='mock_config',
                    help='Configuration to use for the mock build,'
                         " defaults to 'root' defined in" 
                         ' /etc/mock/default.cfg')
        optional.add_argument('--no-report',  action='store_true',
                    help='Do not print review report.')
        optional.add_argument('--no-build', action='store_true',
                    dest='nobuild',
                    help = 'Do not rebuild the srpm, use currently'
                           ' built in mock.')
        optional.add_argument('-o','--mock-options', metavar='<mock options>',
                    default = '--no-cleanup-after', dest='mock_options',
                    help='Options to specify to mock for the build,'
                         ' defaults to --no-cleanup-after')
        optional.add_argument('-p', '--prebuilt',  action='store_true',
                    dest='prebuilt', help='When using -n <name>, use'
                    ' prebuilt rpms in current directory.')
        optional.add_argument('-s', '--single', metavar='<test>',
                    help='Single test to run, as named by --display-checks.')
        optional.add_argument('-r', '--rpm-spec', action='store_true',
                    dest='rpm_spec', default=False, 
                    help='Take spec file from srpm instead of separate url.')
        optional.add_argument('-v', '--verbose',  action='store_true',
                    help='Show more output.', default=False, dest='verbose')
        optional.add_argument('-x', '--exclude',
                    dest='exclude', metavar='"test,..."',
                    help='Comma-separated list of tests to exclude.')
        bz_only.add_argument('-a','--assign', action='store_true',
                    help = 'Assign the bug and set review flags')
        bz_only.add_argument('-l', '--login', action='store_true',
                    default=False,
                    help='Login into Fedora Bugzilla before starting')
        bz_only.add_argument('--other-bz', default=None,
                    metavar='<bugzilla url>', dest='other_bz',
                    help='Alternative bugzilla URL')
        bz_only.add_argument('-i','--user', dest='user',
                    metavar="<user id>",
                    help = 'The bugzilla user Id')

        try:
            args = parser.parse_args()
        except:
            raise CleanExitError('Exit from argparse')

        self.add_args(args)
        self.do_logger_setup(logging.DEBUG if args.verbose else None)
        _check_mock_grp()
        # resultdir as present in mock_options, possibly null
        self.resultdir = None
        if self.mock_options:
            rx=re.compile('--resultdir=([^ ]+)')
            m = rx.search(self.mock_options)
            self.resultdir = m.groups()[0] if m else None
            if not 'no-cleanup-after' in self.mock_options:
                self.mock_options += ' --no-cleanup-after'
      
        self.init_done = True

    def add_args(self, args):
        """ Load all command line options in args. """
        dict = vars(args)
        for key, value in dict.iteritems():
            setattr(self, key, value)

    @property
    def current_bz_url(self):
        return  self.other_bz if self.other_bz else self.bz_url

    def dump(self):
        self.log.debug("Active settings after processing options")
        for k,v in vars(self).iteritems():
             if k in [ '_dict', 'mock_config_options','log' ]:
                 continue
             try:
                 self.log.debug("    " + k + ": " + v.__str__())
             except:
                 pass

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
                except:
                    msg = "Cannot set loglevel from REVIEW_LOGLEVEL"
                    lvl = logging.INFO
            else:
                lvl = logging.INFO

        if not hasattr(self, '_log_config_done'):
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
        # define a Handler which writes INFO messages or higher to the sys.stderr
        console = logging.StreamHandler()
        console.setLevel(lvl)
        formatter = logging.Formatter('%(message)s', "%H:%M:%S")
        console.setFormatter(formatter)
        if hasattr(self, '_con_handler'):
            self.log.removeHandler(self._con_handler)
        self.log.addHandler(console)
        self._con_handler = console

        if msg:
            self.log.warning(msg)
        return True

    def get_logger(self):
        if not hasattr(self, 'log'):
            self.do_logger_setup()
        return self.log

Settings = _Settings()

# vim: set expandtab: ts=4:sw=4:
