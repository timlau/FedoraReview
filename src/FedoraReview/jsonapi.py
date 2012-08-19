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
# (C) 2011 - Stanislav Ochotnicky <sochotnicky@redhat.com>

'''
JSON API for FedoraReview plugins
'''
import re
import subprocess
from json import JSONEncoder, JSONDecoder

from helpers import Helpers
from check_base import TestResult, AbstractCheck, GenericCheck
from mock import Mock
from review_error import FedoraReviewError

class ERR_CODE(object):
    ERR_NO_COMMAND = 1


class PluginParseError(FedoraReviewError):
    pass


class JSONAPI(object):
    """Base class for all JSON plugin communication"""
    supported_api = 1


class SetupPlugin(JSONAPI):
    """First-contact API with plugin"""
    def __init__(self, spec, srpm, sources):
        self.pkgname = spec.name
        self.version = spec.version
        self.release = spec.release
        self.srpm = srpm.filename
        self.spec = {"path": spec.filename,
                     "text": spec.get_expanded()}
        self.rpms = []
        for rpm in srpm.get_files_rpms().keys():
            self.rpms.append(rpm)
        self.rpmlint = "\n".join(srpm.rpmlint_output)
        self.build_dir = Mock.get_builddir()


class GetSectionReply(JSONAPI):
    """Reply to get_section JSON command"""
    def __init__(self, section_text):
        self.text = section_text


class ErrorReply(JSONAPI):
    """Reply used when we encounter error in processing the request

    This is usually caused by unknown call or other error
    """
    def __init__(self, error_text, code):
        self.error = error_text
        self.code = code


class PluginResponse(JSONAPI):
    """Class for plugin responses"""
    command = None

class JSON_check(GenericCheck):
    """ A single test in the list of tests defined by a plugin. """

    def __init__(self, name, checks, plugin):
        GenericCheck.__init__(self, checks, plugin.plugin_path)
        self.plugin = plugin
        self.implementation='json'
        self._name = name

    name = property(lambda self: self._name)

    def run(self):
        if not hasattr( self.plugin, 'results'):
           self.plugin.run()
        self.result = self.plugin.get_result_by_name(self.name)
        
     
class PluginTestParser(object):
    """
    Parse registration info for plugin with just one test, like:
    @name: test-name
    @group: java # generic, C/C++ etc
    @type: MUST|SHOULD|EXTRA     
    @text :"User info, visible in listings"
    @url: Guidelines URL, optional
    @deprecates: test1, test2, ...
    @needs: test4, test5, ...
    """

    def find_value(self, line, name, key):
        if name:
           key = name + '.' + key
        key = '@' + key + ':'
        if key in line:
            return re.sub('.*' + key, '', line).strip()
        return None

    def parse_attributes(self, check, lines, name = None):
        for line in lines:
            for attr in ['group', 'url', 'text', 'type']:
                value = self.find_value(line, name, attr)
                if value:
                    setattr(check, attr, value)
            list = self.find_value(line, name, 'deprecates')
            if list:
                check.deprecates = list.replace(',', ' ').split()
            list = self.find_value(line, name, 'needs')
            if list:
                check.needs = list.replace(',', ' ').split()
 
    def parse(self, plugin, checks ):
        """ Parse a path, return a JSON_check object. """

        with open(plugin.plugin_path) as f:
            lines = f.readlines()
        for line in lines:
            name = self.find_value(line, None, 'name')
            if name:
                break
        if not name:
            name = os.path.basename(plugin_path)
        test = JSON_check(name, checks, plugin)
        self.parse_attributes(test, lines)
        return test


class PluginTestsParser(PluginTestParser):
    """
    Parse comments for a plugin with more than one test. Format:
    @tests: test1,test2 ...
    @test1.text: user info, one short line.
    @test1.group: Generic
    @test1.type:  MUST
    @test1.url: http://somewhere...
    @test1.deprecates: test1, test2
    @test1.needs: test4,test5
    @test2.text: user info, one short line.
    @test2.group: Generic
    @test2.type:  MUST
    @test2.url: http://somewhere...
    @test2.deprecates: test1, test2
    @test2.needs: test4,test5
    """

    def parse(self, plugin, checks):
        """
        Return a list of JSON_check corresponding to comments.
        """
        with open(plugin.plugin_path) as f:
            lines = f.readlines()
        tests = []
        name_lines = filter(lambda l: '@names:' in l, lines)
        if name_lines == []:
            raise PluginParseError("Cannot find '@names:'")
        name_line = name_lines[0]
        name_line = re.sub('.*@names:', '', name_line)
        for name in name_line.replace(',', ' ').split():
             test = JSON_check(name, checks, plugin)
             tests.append(test)
             self.parse_attributes(test, lines, name)
        return tests


class JSONPlugin(Helpers):
    """Plugin for communicating with external review checks using JSON"""

    def __init__(self, checks, plugin_path):
        Helpers.__init__(self)
        self.plugin_path = plugin_path
        self.version = None
        self.checks = checks
        self.spec = checks.spec
        self.srpm = checks.srpm
        self.sources = checks.sources
        self.encoder = ReviewJSONEncoder()
        self.decoder = JSONDecoder()
        self.plug_in = None
        self.plug_out = None
        self.plug_err = None
        self.tests = []
        self.results = []

    def register(self):
        try:
            self.tests = PluginTestsParser().parse(self, self.checks)
        except PluginParseError:
            try:
                self.tests = [PluginTestParser().parse(self, self.checks)]
            except:
                self.log.warning("Can't parse test metadata in " + 
                                  self.plugin_path)
        return self.tests

    def run(self):
        """Run the plugin to produce results"""
        plugin_proc = subprocess.Popen(self.plugin_path,
                                       bufsize=-1,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       stdin=subprocess.PIPE)
        self.plug_in = plugin_proc.stdin
        self.plug_out = plugin_proc.stdout
        self.plug_err = plugin_proc.stderr

        setup = SetupPlugin(self.spec, self.srpm, self.sources)
        try:
            self.__send_obj(setup)

            final_data = ""
            while True:
                data = plugin_proc.stdout.readline()
                if data == "":
                    break
                final_data = final_data + data
                obj = self.__get_class_from_json(final_data)
                if obj:
                    self.__handle_reply(obj)
                    final_data = ""
        except IOError, e:
            self.__error("Error communicating")
            self.__error(e)

        errout = self.plug_err.read()
        while errout != "":
            self.__error(errout)
            errout = self.plug_err.read()


    def get_results(self):
        """ Returns list of TestResult"""

        return self.results

    def get_result_by_name(self, name):
        found = filter(lambda r: r.name == name, self.results)
        assert(len(found) < 2)
        return None if found == [] else found[0]

    def __get_class_from_json(self, text):
        """Convert JSON reply to simple Python object

        returns None if JSON cannot be decoded
        """
        ret = None
        try:
            json_obj = self.decoder.decode(text)
            ret = PluginResponse()
            for key in json_obj.keys():
                setattr(ret, key, json_obj[key])
            if not hasattr(ret, "command"):
                self.__error("plugin returned JSON object without 'command' ")
                # Reply has to have this
                return None
        except ValueError:
            # ret is set to None
            pass
        return ret

    def __handle_reply(self, reply):
        """Handle incomming commands and results"""

        class JSON_TestResult(TestResult):

            def __init__(self, map_):
                 self.name = map_['name']
                 self.text = map_['text']
                 self.url = map_['url']
                 self.type = map_['type']
                 self.deprecates = map_['deprecates']
                 self.result = map_['result']
                 self.group = 'json'
                 extra = None
                 if "output_extra" in map_:
                     extra  =  map_['output_extra']
                 TestResult.__init__(self, self, map_['result'], extra, [])

        if reply.command == "results":
            self.__debug("Processing results")
            if hasattr(reply, "version"):
                self.version = reply.version

            for result in reply.checks:
                self.results.append(JSON_TestResult(result))
        elif reply.command == "get_section":
            self.__debug("get_section call")
            sec_name = "%%%s" % reply.section
            gs_ret = self.spec.get_section(sec_name)
            if sec_name not in gs_ret:
                section_text = ""
                self.log.debug("Plugin %s asked for non-existent"
                               "section %s" % (self.plugin_path,
                                               sec_name))
            else:
                section_text = "\n".join(gs_ret[sec_name])
            msg = GetSectionReply(section_text)
            self.__send_obj(msg)
        else:
            msg = "unrecognized message command %s"  % reply.command
            self.__error(msg)
            self.__send_obj(ErrorReply(msg, ERR_CODE.ERR_NO_COMMAND))

    def __send_obj(self, obj):
        """Send JSONAPI subclass to JSON plugin"""
        self.plug_in.write(self.encoder.encode(obj))
        self.plug_in.write("\n\n")
        self.plug_in.flush()

    def __debug(self, msg):
        self.log.debug("Plugin %s: %s" % (self.plugin_path,msg))

    def __error(self, msg):
        self.log.error("Plugin %s: %s" % (self.plugin_path,msg))

class ReviewJSONEncoder(JSONEncoder):
    """Custom JSON encoder for JSONAPI subclasses"""
    IGNORED = ['__module__', '__dict__', '__doc__', '__init__', '__weakref__',
             '__slots__']

    def default(self, encclass):
        if not isinstance(encclass, JSONAPI):
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
            if rem in ret:
                ret.pop(rem)

        return ret

# vim: set expandtab: ts=4:sw=4:

