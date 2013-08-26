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

""" Functions to create the xml report. """


import xml.etree.ElementTree as ET
import xml.dom.minidom

from version import __version__, BUILD_FULL


def write_xml_report(spec, results):
    ''' Create the firehose-compatible xml report, see
        https://github.com/fedora-static-analysis/firehose/
    '''

    def create_xmltree(spec):
        ''' Create the basic xml report complete with <metadata>. '''
        root = ET.Element('analysis')
        metadata = ET.SubElement(root, 'metadata')
        ET.SubElement(metadata,
                      'generator',
                      {'name': 'fedora-review',
                       'version': __version__,
                       'build': BUILD_FULL})
        sut = ET.SubElement(metadata, 'sut')
        nvr = {'name': spec.name,
               'version': spec.version,
               'release': spec.release}
        ET.SubElement(sut, 'source-rpm', nvr)
        ET.SubElement(root, 'results')
        return root

    def add_xml_result(root, result):
        ''' Add a failed result to the xml report as a <result> tag. '''
        results = root.find('results')
        xml_result = ET.SubElement(results,
                                    'issue',
                                    {'test-id': result.check.name})
        message = ET.SubElement(xml_result, 'message')
        message.text = result.text
        if result.output_extra:
            notes = ET.SubElement(xml_result, 'notes')
            notes.text = result.output_extra
        return root

    root = create_xmltree(spec)
    for result in results:
        if result.check.is_failed:
            root = add_xml_result(root, result)
    dom = xml.dom.minidom.parseString(ET.tostring(root))
    with open('report.xml', 'w') as f:
        f.write(dom.toprettyxml(indent='    '))
