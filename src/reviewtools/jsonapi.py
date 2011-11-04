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
import select
from json import JSONEncoder, JSONDecoder

from reviewtools import Helpers, TestResult

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
                     "text":spec.get_expanded()}
        self.rpms = []
        for rpm in srpm.get_files_rpms().keys():
            self.rpms.append({"path":rpm,
                              "tree":None})
        self.rpmlint = "\n".join(srpm.rpmlint_output)
        self.build_dir = srpm.get_build_dir()

class PluginResponse(JSONAPI):
    command = None

class JSONPlugin(Helpers):
    """Plugin for communicating with external review checks using JSON"""

    def __init__(self, base, plugin_path):
        Helpers.__init__(self)
        self.plugin_path = plugin_path
        self.spec = base.spec
        self.srpm = base.srpm
        self.sources = base.sources
        self.encoder = ReviewJSONEncoder()
        self.decoder = JSONDecoder()
        self.results = []

    def run(self):
        # /bin/cat will be normally self.plugin_path
        plugin_proc = subprocess.Popen(self.plugin_path,
                                       bufsize = -1,
                                       stdout = subprocess.PIPE,
                                       stderr = subprocess.PIPE,
                                       stdin = subprocess.PIPE)

        setup = SetupPlugin(self.spec, self.srpm, self.sources)
        plugin_proc.stdin.write(self.encoder.encode(setup))
        plugin_proc.stdin.write("\n\n")
        plugin_proc.stdin.flush()

        final_data = ""
        while True:
            rlist, wlist, xlist = select.select([plugin_proc.stdout], [], [])
            json_obj = None
            if plugin_proc.stdout in rlist:
                data = plugin_proc.stdout.read(10)
                if data == "":
                    break
                final_data = final_data + data
                obj = self.__get_class_from_json(final_data)
                if obj:
                    self.__handle_reply(obj)
                    final_data = ""
                    break


    def get_results(self):
        return self.results

    def __get_class_from_json(self, text):
        ret = None
        try:
            json_obj = self.decoder.decode(text)
            ret = PluginResponse()
            for key in json_obj.keys():
                setattr(ret, key, json_obj[key])
            if not hasattr(ret, "command"):
                # Reply has have this
                return None
        except ValueError, e:
            # ret is set to None
            pass
        return ret

    def __handle_reply(self, reply):
        if reply.command == "results":
            for result in reply.checks:
                extra = None
                if result.has_key("output_extra"):
                    extra = result["output_extra"]
                self.results.append(TestResult(result["name"], result["url"],
                                               result["group"], result["deprecates"],
                                               result["text"], result["type"], result["result"],
                                               extra))



class ReviewJSONEncoder(JSONEncoder):
    ''' a custom JSON encoder for JSONAPI subclasses '''
    IGNORED=['__module__', '__dict__', '__doc__', '__init__', '__weakref__',
             '__slots__']

    def default(self, encclass):
        if not isinstance (encclass, JSONAPI):
            print 'You cannot use the ReviewJSONEmcoder for a non-JSONAPI object.'
            return
        ret = {}
        # get things from base classes
        for base in encclass.__class__.__bases__:
            if hasattr(base, "__dict__"):
                for item in base.__dict__:
                    ret[item] = base.__dict__[item]

        # get things defined in class
        for item in encclass.__class__.__dict__:
            ret[item] = encclass.__class__.__dict__[item]

        # instance variables
        if hasattr(encclass, "__dict__"):
            for item in encclass.__dict__:
                ret[item] = encclass.__dict__[item]

        # slot variables
        if hasattr(encclass, "__slots__"):
            for item in encclass.__slots__:
                ret[item] = getattr(encclass, item)

        for rem in self.IGNORED:
            if ret.has_key(rem):
               ret.pop(rem)

        return ret

