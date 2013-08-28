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

import subprocess
import xml.etree.ElementTree as ET
import xml.dom.minidom

from glob import glob

from version import __version__, BUILD_FULL

_HEADER = """
This is a review *template*. Besides handling the [ ]-marked tests you are
also supposed to fix the template before pasting into bugzilla:
- Add issues you find to the list of issues on top. If there isn't such
  a list, create one.
- Add your own remarks to the template checks.
- Add new lines marked [!] or [?] when you discover new things not
  listed by fedora-review.
- Change or remove any text in the template which is plain wrong. In this
  case you could also file a bug against fedora-review
- Remove the "[ ] Manual check required", you will not have any such lines
  in what you paste.
- Remove attachments which you deem not really useful (the rpmlint
  ones are mandatory, though)
- Remove this text



Package Review
==============

Legend:
[x] = Pass, [!] = Fail, [-] = Not applicable, [?] = Not evaluated
[ ] = Manual review needed

"""


def _write_section(results, output):
    ''' Print a {SHOULD,MUST, EXTRA} section. '''

    def hdr(group):
        ''' Return header this test is printed under. '''
        if '.' in group:
            return group.split('.')[0]
        return group

    def result_key(result):
        ''' Return key used to sort results. '''
        if result.check.is_failed:
            return '0' + str(result.check.sort_key)
        elif result.check.is_pending:
            return '1' + str(result.check.sort_key)
        elif result.check.is_passed:
            return '2' + str(result.check.sort_key)
        else:
            return '3' + str(result.check.sort_key)

    groups = list(set([hdr(test.group) for test in results]))
    for group in sorted(groups):
        res = filter(lambda t: hdr(t.group) == group, results)
        if not res:
            continue
        res = sorted(res, key=result_key)
        output.write('\n' + group + ':\n')
        for r in res:
            output.write(r.get_text() + '\n')


def _get_specfile():
    ' Return a (specfile, sha224sum) tuple. '
    spec = glob('srpm-unpacked/*.spec')
    if len(spec) != 1:
        return '?', '?'
    path = spec[0].strip()
    cs = subprocess.check_output(['sha224sum', path]).split()[0]
    path = path.rsplit('/', 1)[1]
    return path, cs


def write_template(output, results, issues, attachments):
    ''' Print  review template results on output. '''

    def dump_local_repo():
        ''' print info on --local-repo rpms used. '''
        repodir = Settings.repo
        if not repodir.startswith('/'):
            repodir = os.path.join(ReviewDirs.startdir, repodir)
        rpms = glob(os.path.join(repodir, '*.rpm'))
        output.write("\nBuilt with local dependencies:\n")
        for rpm in rpms:
            output.write("    " + rpm + '\n')

    output.write(_HEADER)

    if issues:
        output.write("\nIssues:\n=======\n")
        for fail in issues:
            fail.set_leader('- ')
            fail.set_indent(2)
            output.write(fail.get_text() + "\n")
        results = [r for r in results if not r in issues]

    output.write("\n\n===== MUST items =====\n")
    musts = filter(lambda r: r.type == 'MUST', results)
    _write_section(musts, output)

    output.write("\n===== SHOULD items =====\n")
    shoulds = filter(lambda r: r.type == 'SHOULD', results)
    _write_section(shoulds, output)

    output.write("\n===== EXTRA items =====\n")
    extras = filter(lambda r: r.type == 'EXTRA', results)
    _write_section(extras, output)

    for a in sorted(attachments):
        output.write('\n\n')
        output.write(a.__str__())

    if Settings.repo:
        dump_local_repo()


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
        path, cs = _get_specfile()
        file_ = ET.SubElement(metadata, 'file', {'given-path': path})
        ET.SubElement(file_, 'hash', {'alg': 'sha224', 'hexdigest': cs})
        sut = ET.SubElement(metadata, 'sut')
        nvr = {'name': spec.name,
               'version': spec.version,
               'release': spec.release}
        ET.SubElement(sut, 'source-rpm', nvr)
        ET.SubElement(root, 'results')
        return root

    def add_xml_result(root, result):
        ''' Add a failed result to the xml report as a <result> tag. '''
        path = root.find('metadata/file').attrib['given-path']
        results = root.find('results')
        issue = ET.SubElement(results,
                              'issue',
                              {'test-id': result.name,
                               'severity': result.type})
        message = ET.SubElement(issue, 'message')
        message.text = result.text
        location = ET.SubElement(issue, 'location')
        ET.SubElement(location, 'file', {'given-path': path})
        if result.output_extra:
            ET.SubElement(issue, 'notes').text = result.output_extra
        return root

    root = create_xmltree(spec)
    for result in results:
        if result.is_failed:
            root = add_xml_result(root, result)
    dom = xml.dom.minidom.parseString(ET.tostring(root))
    with open('report.xml', 'w') as f:
        f.write(dom.toprettyxml(indent='    '))
