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
Tools for helping Fedora package reviewers
'''

import argparse
import sys

from reviewtools.bugz import ReviewBug
from reviewtools.misc import Checks

class ReviewHelper:


    
    def __init__(self):
        self.bug = None
        self.checks = None
        self.args = self.get_args()
        self.verbose = False

    def get_args(self):
        parser = argparse.ArgumentParser(description='Review a Fedora Package')
        parser.add_argument('-b','--bug', metavar='[bug]', required=True,
                   help='the bug number contain the package review')
        parser.add_argument('-w','--workdir', default='~/.reviewhelper/', metavar='[dir]',
                            help='Work directory (default = ~/.reviewhelper)')       
        parser.add_argument('-o', '--output', type=argparse.FileType('w'), default='-',
                            metavar='[file]',
                            help="output file for review report (default = stdout)") 
        parser.add_argument('--assign', action='store_true',
                            help = 'Assign the bug and set review flags')        
        parser.add_argument('-u','--user', metavar='[userid]', 
                   help='The Fedora Bugzilla userid')
        parser.add_argument('-p','--password', metavar='[password]', 
                   help='The Fedora Bugzilla password')
        parser.add_argument('-v','--verbose',  action='store_true',
                            help='Show more output')
        parser.add_argument('--no-report',  action='store_true', dest='noreport', 
                            help='Dont make a review report')
        args = parser.parse_args()
        return args
    
    def download_sources(self):
        self.checks.source.set_work_dir(self.args.workdir)
        sources = self.checks.spec.get_sources()
        if sources:
            for tag in sources:
                if tag.startswith('Source'):
                    self.verbose_message("Downloading (%s): %s" % (tag,sources[tag]))
                    self.checks.source.get_source(sources[tag])
            return True
        else:
            return False
        
    def do_report(self):
        ''' Create a review report'''
        print('Getting .spec and .srpm Urls from bug report : %s' % self.args.bug)
        # get urls
        rc = self.bug.find_urls()
        if not rc:
            print('Cant find any .spec and .srpm URLs in bugreport')
            sys.exit(1)
        self.verbose_message("  --> Spec url : %s" % self.bug.spec_url)
        self.verbose_message("  --> SRPM url : %s" % self.bug.srpm_url)
        # get the spec and SRPM file 
        print('Downloading .spec and .srpm files')
        rc = self.bug.download_files()
        if not rc:
            print('Cant download .spec and .srpm')
            sys.exit(1)
        self.verbose_message("  --> Spec file : %s" % self.bug.spec_file)
        self.verbose_message("  --> SRPM file : %s" % self.bug.srpm_file)
        self.checks = Checks(self.bug.spec_file, self.bug.srpm_file)
        # get upstream sources
        rc = self.download_sources()
        if not rc:
            print('Cant download upstream sources')
            sys.exit(1)
        print('Running check and generate report\n')
        self.checks.run_checks(output=self.args.output)
            
    def do_assign(self):
        ''' assign bug'''
        if self.args.user and self.args.password:
            print ("Assigning bug to user")
            self.bug.assign_bug()
        else:
            print('You need to add bugzilla userid/password (-u/-p) to assign bug')
                
    def verbose_message(self, msg):
        if self.verbose:
            print msg

    def run(self):
        print self.args
        self.verbose = self.args.verbose
        if self.args.bug:
            # get the bug
            print ("Proccessing review bug : %s" % self.args.bug )
            if self.args.user and self.args.password:
                self.bug = ReviewBug(self.args.bug, user = self.args.user, password= self.args.password)
            else:
                self.bug = ReviewBug(self.args.bug)
            self.bug.set_work_dir(self.args.workdir)
            self.verbose_message("  --> Working dir : %s" % self.bug.work_dir)
            if self.args.assign:
                self.do_assign()
            if not self.args.noreport:                        
                self.do_report()

if __name__ == "__main__":
    review = ReviewHelper()
    review.run()


