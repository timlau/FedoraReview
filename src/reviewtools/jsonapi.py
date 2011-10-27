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
# (C) 2011 - Stanislav Ochotnicky <sochotnicky@redhat.com>

'''
JSON API for FedoraReview plugins
'''
import subprocess
from json import JSONEncoder, JSONDecoder

from reviewtools import Helpers

class JSONAPI(object):
    supported_api = 1

class SetupPlugin(JSONAPI):
    """First-contact API with plugin"""
    def __init__(self, spec, srpm, sources):
        self.pkgname = spec.name
        self.version = spec.version
        self.release = spec.release
        self.srpm = {"path":srpm.filename,
                     "tree":None}
        self.spec = {"path":spec.filename,
                     "text":None}
        self.rpms = []
        for rpm in srpm.get_files_rpms().keys():
            self.rpms.append({"path":rpm,
                              "tree":None})
        self.rpmlint = "\n".join(srpm.rpmlint_output)


class JSONPlugin(Helpers):

    def __init__(self, base, plugin_path):
        Helpers.__init__(self)
        self.plugin_path = plugin_path
        self.spec = base.spec
        self.srpm = base.srpm
        self.sources = base.sources
        self.encoder = ReviewJSONEncoder()

    def run(self):
        # /bin/cat will be normally self.plugin_path
        plugin_proc = subprocess.Popen("/bin/cat",
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       stdin=subprocess.PIPE)

        setup = SetupPlugin(self.spec, self.srpm, self.sources)
        plugin_proc.stdin.write(self.encoder.encode(setup))
        print self.encoder.encode(setup)
        # plugin_proc.stdout.read()
        # decode later


class ReviewJSONEncoder(JSONEncoder):
    ''' a custom JSON encoder for JSONAPI subclasses '''
    IGNORED=['__module__', '__dict__', '__doc__', '__init__','__weakref__']

    def default(self, encclass):
        if not isinstance (encclass, JSONAPI):
            print 'You cannot use the ReviewJSONEmcoder for a non-JSONAPI object.'
            return
        ret = {}
        # get things from base classes
        for base in encclass.__class__.__bases__:
            for item in base.__dict__:
                ret[item] = base.__dict__[item]

        # get things defined in class
        for item in encclass.__class__.__dict__:
            ret[item] = encclass.__class__.__dict__[item]

        # instance variables
        for item in encclass.__dict__:
             ret[item] = encclass.__dict__[item]

        for rem in self.IGNORED:
            if ret.has_key(rem):
               ret.pop(rem)

        return ret

