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
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


"""
This program aims to provide a simple way to create review-request on
the Red Hat's bugzilla for Fedora products.

The idea is:
- from a spec and srpm
  - start a koji scratch build
  - if build worked
    - upload to fedorapeople.org
    - create the bugzilla ticket
    - Add the koji build in the bugzilla as a link
  - otherwise:
    - warn user
"""

import argparse
import ConfigParser
import fedora_cert
import getpass
import logging
import os
import rpm
import subprocess
import sys
from xmlrpclib import Fault
from bugzilla.rhbugzilla import RHBugzilla3
from subprocess import Popen


SETTINGS_FILE = os.path.join(os.environ['HOME'], '.config',
                    'fedora-create-review')

BUG_COMMENT = """
Spec URL: %s
SRPM URL: %s

Description:
%s
"""

# Initial simple logging stuff
logging.basicConfig()
LOG = logging.getLogger("fedora-create-review")
if '--debug' in sys.argv:
    LOG.setLevel(logging.DEBUG)


class FedoraCreateReviewError(Exception):
    """ Generic Exception class used for the exception thrown in this
    project. """
    pass


class Settings(object):
    """ gitsync Settings """
    # upload target
    upload_target = 'fedorapeople.org:public_html/'

    def __init__(self):
        """Constructor of the Settings object.
        This instanciate the Settings object and load into the _dict
        attributes the default configuration which each available option.
        """
        self._dict = {'upload_target': self.upload_target,
                     }
        self.load_config(SETTINGS_FILE, 'fedora-create-review')

    def load_config(self, configfile, sec):
        """Load the configuration in memory.

        :arg configfile, name of the configuration file loaded.
        :arg sec, section of the configuration retrieved.
        """
        parser = ConfigParser.ConfigParser()
        configfile = os.path.join(os.environ['HOME'], configfile)
        isNew = self.create_conf(configfile)
        parser.read(configfile)
        if not parser.has_section(sec):
            parser.add_section(sec)
        self.populate(parser, sec)
        if isNew:
            self.save_config(configfile, parser)

    def create_conf(self, configfile):
        """Check if the provided configuration file exists, generate the
        folder if it does not and return True or False according to the
        initial check.

        :arg configfile, name of the configuration file looked for.
        """
        if not os.path.exists(configfile):
            dn = os.path.dirname(configfile)
            if not os.path.exists(dn):
                os.makedirs(dn)
            return True
        return False

    def save_config(self, configfile, parser):
        """Save the configuration into the specified file.

        :arg configfile, name of the file in which to write the configuration
        :arg parser, ConfigParser object containing the configuration to
        write down.
        """
        with open(configfile, 'w') as conf:
            parser.write(conf)

    def __getitem__(self, key):
        hash = self._get_hash(key)
        if not hash:
            raise KeyError(key)
        return self._dict.get(hash)

    def populate(self, parser, section):
        """Set option values from a INI file section.

        :arg parser: ConfigParser instance (or subclass)
        :arg section: INI file section to read use.
        """
        if parser.has_section(section):
            opts = set(parser.options(section))
        else:
            opts = set()

        for name in self._dict.iterkeys():
            value = None
            if name in opts:
                value = parser.get(section, name)
                setattr(self, name, value)
                parser.set(section, name, value)
            else:
                parser.set(section, name, self._dict[name])


class ReviewRequest(object):
    """ Review Request class, used to be able to keep some information
    within the class.
    """

    def __init__(self):
        """ Constructor. """
        self.settings = Settings()
        self.info = {}
        self.log = LOG
        self.specfile = ''
        self.spec = ''
        self.srpmfile = ''

    def add_comment_build(self, output_build, bug):
        """ Retrieve the link to the koji build from the output of the
        koji command and add a comment with this link on the review
        request.
        """
        print 'Adding comment about the koji build'
        url = None
        for line in output_build.split('\n'):
            if 'Task info' in line:
                url = line.split('Task info:')[1]
        comment = "This package built on koji: %s" % url
        bug.addcomment(comment)

    def create_review_request(self, rename_request):
        """ Create the review request on the bugzilla. """
        print 'Creating review'
        review_type = 'Review Request'
        if rename_request:
            review_type = 'Rename Request'
        data = {
            'product': 'Fedora',
            'component': 'Package Review',
            'version': 'rawhide',
            'short_desc': '%s: %s - %s' % (review_type, self.info['name'],
                    self.info['summary']),
            'comment': BUG_COMMENT % (self.info['specurl'],
                    self.info['srpmurl'], self.info['description']),
            'rep_platform': 'Unspecified',
            'bug_severity': 'unspecified',
            'op_sys': 'Unspecified',
            'bug_file_loc': '',
            'priority': 'unspecified',
            }
        if rename_request:
            data['comment'] = data['comment'] + \
            '\n\n This is a Rename request for the former package \'%s\'' % rename_request
        self.log.debug("bz.createbug(%s)", data)
        try:
            bug = self.bzclient.createbug(**data)
            bug.refresh()
        except Fault, ex:
            print ex
            self.login_bz()
            return self.create_review_request(rename_request)
        return bug

    def do_scratch_build(self, target='rawhide'):
        """ Starts a scratch build on koji. """
        print 'Starting scratch build'
        cmd = ['koji', 'build', '--scratch', target, self.srpmfile]
        self.log.debug(cmd)
        try:
            proc = Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = proc.communicate()[0]
        except OSError, err:
            print "OSError : %s" % str(err)
        return (output, proc.returncode)

    def fill_urls(self):
        """ Fill the spec and src.rpm urls into the info table using the
        info in the settings.
        """
        try:
            fasusername = fedora_cert.read_user_cert()
        except:
            self.log.debug('Could not read Fedora cert, using login name')
            fasusername = raw_input('FAS username: ')
        complement_url = self.settings.upload_target.split('public_html/')[1]
        url = 'http://%s.fedorapeople.org/%s/' % (fasusername, complement_url)
        self.info['specurl'] = url + self.specfile.rsplit('/', 1)[1]
        self.info['srpmurl'] = url + self.srpmfile.rsplit('/', 1)[1]

    def find_existing_reviews(self):
        """ Return information about the review request(s) sumitted
        for a given package.

        This function queries the Fedora/RedHat's bugzilla to find the review
        or reviews submitted for a given package.
        It prints out the bug number, the assignee, the summary and the
        resolution of each bug found.

        :arg packagename the name of the package to search for
        """
        bugbz = self.bzclient.query(
                {#'bug_status': ['CLOSED'],
                 'short_desc': "Request: {0} -.*".format(self.info['name']),
                 'short_desc_type': 'regexp',
                 'component': 'Package Review'})

        if bugbz:
            print 'Reviews for a package of the same name have been found:'
        for bug in bugbz:
            print ' ', bug, '-', bug.resolution
            print "\t",bug.url

        if bugbz:
            usr_inp = raw_input( 'Do you want to proceed anyway? [Y/N]')
            if usr_inp.lower() == ''  or usr_inp.lower().startswith('n'):
                raise FedoraCreateReviewError()

    def login_bz(self):
        """ Login into the bugzilla. """
        username = raw_input('Bugzilla username: ')
        self.bzclient.login(user=username,
                            password=getpass.getpass())

    def main(self):
        """ The main function."""
        parser = setup_parser()
        args = parser.parse_args()
        if not args.test:
            bzurl = 'https://bugzilla.redhat.com'
        else:
            bzurl = 'https://partner-bugzilla.redhat.com'

        self.bzclient = RHBugzilla3(url="%s/xmlrpc.cgi" % bzurl)
        self.srpmfile = os.path.expanduser(args.srpmfile)
        self.specfile = os.path.expanduser(args.specfile)
        self.spec = rpm.spec(self.specfile)
        if not args.no_build:
            (output_build, returncode) = self.do_scratch_build(
                target=args.koji_target)
            if returncode != 0:
                raise FedoraCreateReviewError(
                    'Something happened while trying to build this package on koji: \n %s' % output_build)
        self.info['summary'] = self.retrieve_summary()
        self.info['description'] = self.retrieve_description()
        self.info['name'] = self.retrieve_name()
        self.find_existing_reviews()
        (output_upload, returncode) = self.upload_files()
        if returncode != 0:
            raise FedoraCreateReviewError(
                    'Something happened while uploading the files:\n %s' % output_upload)
        self.fill_urls()
        bug = self.create_review_request(args.rename_request)
        if not args.no_build:
            self.add_comment_build(output_build, bug)
        print 'Review created at: %s/show_bug.cgi?id=%s' % (bzurl,
                                                            bug.id)
        print bug

    def retrieve_description(self):
        """ Retrieve the description tag from a spec file. """
        description = self.spec.packages[0].header[1005]
        self.log.debug('Description: %s' % description)
        return description

    def retrieve_name(self):
        """ Retrieve the name tag from a spec file. """
        name = self.spec.packages[0].header[1000]
        self.log.debug('Name: %s' % name)
        return name

    def retrieve_summary(self):
        """ Retrieve the summary tag from a spec file. """
        summary = self.spec.packages[0].header[1004]
        self.log.debug('Summary: %s' % summary)
        return summary

    def upload_files(self):
        """ Upload the spec file and the src.rpm files into
        fedorapeople.org."""
        print 'Uploading files into fedorapeople'
        self.log.debug('Target: %s' % self.settings.upload_target)
        cmd = ['scp', self.specfile, self.srpmfile,
            self.settings.upload_target]
        self.log.debug(cmd)
        try:
            proc = Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = proc.communicate()[0]
        except OSError, err:
            print "OSError : %s" % str(err)
        return (output, proc.returncode)


def setup_parser():
    """
    Set the command line arguments.
    """
    parser = argparse.ArgumentParser(
        prog="fedora-create-review")
    # General connection options
    parser.add_argument('specfile',
                help='Path to the spec file')
    parser.add_argument('srpmfile',
                help='Path to the src.rpm file')
    parser.add_argument('--user', dest='username',
                help='FAS username')
    parser.add_argument('--rename-request', default=False,
                help='Former name of the package.')
    parser.add_argument('--koji-target', default='rawhide',
                help='Target for the koji scratch build (default: rawhide)')
    parser.add_argument('--test', default=False, action='store_true',
                help='Run on a test bugzilla instance')
    parser.add_argument('--no-scratch-build', dest='no_build',
                action='store_true',
                help='Do not run the koji scratch build')
    parser.add_argument('--debug', action='store_true',
                help='Outputs bunches of debugging info')
    return parser

if __name__ == '__main__':
    try:
        ReviewRequest().main()
    except Exception, error:
        print error
