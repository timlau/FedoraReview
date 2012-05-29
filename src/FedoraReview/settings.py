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

from review_error import FedoraReviewError

SYS_PLUGIN_DIR = "/usr/share/fedora-review/plugins:%s"
MY_PLUGIN_DIR  = "~/.config/fedora-review/plugins"

PARSER_SECTION = 'review'

LOG_ROOT = 'FedoraReview'


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
        'workdir':      '.',
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
        self.log = self.get_logger()

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

    def init(self):
        ''' Delayed setup, to be called when sys.argv is ok...'''

        def _check_mock_grp():
            try:
                mock_gid = grp.getgrnam('mock')[2]
                if not mock_gid in os.getgroups():
                    raise ConfigError( 'Not in mock group, see manpage')
            except:
                raise ConfigError('No mock group - mock not installed?')

        if hasattr(self, 'init_done'):
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
                    help='Operate on local files <name>.spec &'
                         ' <name>*.src.rpm located in work dir.')
        modes.add_argument('-u', '--url', default = None, dest='url',
                    metavar='<url>',
                     help='Operate on another bugzilla, using complete'
                          ' url to bug page.')
        modes.add_argument('-d','--display-checks', default = False,
                    action='store_true',dest='list_checks',
                    help='List all available checks.')
        modes.add_argument('-V', '--version', default = False,
                    action='store_true',
                    help='Display version information and exit.')
        optional.add_argument('-c','--cache', action='store_true', dest='cache',
                    help = 'Do not redownload files from bugzilla,'
                           ' use the ones in the cache.')
        optional.add_argument('-g','--grab', default = False,
                    action='store_true',dest='grab',
                    help='Display urls and exit')
        optional.add_argument('-h','--help', action='help',
                    help = 'Display this help message')
        optional.add_argument('-m','--mock-config', metavar='<config>',
                    default = 'fedora-rawhide-i386', dest='mock_config',
                    help='Configuration to use for the mock build,'
                             ' defaults to fedora-rawhide-i686.')
        optional.add_argument('--no-report',  action='store_true',
                    dest='noreport',
                    help='Do not make a review report.')
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
        optional.add_argument('-s', '--single',
                    default='', dest='single',
                    metavar='<test>',
                    help='Single test to run, as named by --display-checks.')
        optional.add_argument('-v', '--verbose',  action='store_true',
                    help='Show more output.', default=False, dest='verbose')
        optional.add_argument('-x', '--exclude',
                    default='', dest='exclude',
                    metavar='"test,..."',
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
        args = parser.parse_args()
        self.do_logger_setup(logging.DEBUG if args.verbose else None)
        _check_mock_grp()
        args.workdir = os.getcwd()
        self.add_args(args)
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
        logging.DEBUG. If None, respects FR_LOGLEVEL environment
        variable, defaulting to logging.INFO.
        '''
        msg = None
        if not lvl:
            if 'FR_LOGLEVEL' in os.environ:
                try:
                    lvl = eval('logging.' +
                               os.environ['FR_LOGLEVEL'].upper())
                except:
                    msg = "Cannot set loglevel from FR_LOGLEVEL"
                    lvl = logging.INFO
            else:
                lvl = logging.INFO
        logger = logging.getLogger(LOG_ROOT)
        logger.setLevel(lvl)
        formatter = logging.Formatter('%(message)s', "%H:%M:%S")
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        handler.propagate = False
        if hasattr(self, '_log_handler'):
            logger.removeHandler(self._log_handler)
        self._log_handler = handler
        logger.addHandler(handler)
        if msg:
            self.log.warning(msg)
        return handler

    def get_logger(self):
        return logging.getLogger(LOG_ROOT)

Settings = _Settings()


# vim: set expandtab: ts=4:sw=4:
