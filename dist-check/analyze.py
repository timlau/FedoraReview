#!/usr/bin/env python

'''
analyze [report-name [arg]]

Expects a list of report.xml files created by fedora-review on stdin,
prints a report. Valid report names:

    stats:  Number of failed tests in the reports.
    legend: Prints explanation for each test.
    srpms:  Prints failing srpms for a given test.
    tests:  Prints failing tests for a given srpm.
    srpms-full:
            As srpms, also prints notes about the tests.
    tests-full:
            As tests, also prints notes about the tests.
    mktree: Create a tree with reports on packages and issues.

Examples:

    find . -name report.xml | ./analyze stats
    find . -name report.xml | ./analyze srpms CheckAddMavenDepmap

[report name] defaults to 'stats'.
'''

# pylint: disable=W0621,C0103

import sqlite3
import os
import os.path
import sys
import xml.etree.ElementTree as ET

from textwrap import TextWrapper


def db_init():
    ''' Create an in-memory db with all tables in place. '''
    conn = sqlite3.connect(':memory:')
    c = conn.cursor()
    c.execute('create table issues (id text, srpm text, notes text)')
    c.execute('create table tests'
              ' (id text primary key, message text, type text)')
    conn.commit()
    return conn


def db_insert(conn, tree):
    ''' Insert issues and tests from the parsed xml into db. '''
    srpm = tree.find('metadata/sut/source-rpm').attrib['name']
    c = conn.cursor()
    for issue in tree.findall('results/issue'):
        name = issue.attrib['test-id']
        try:
            type_ = issue.attrib['severity']
        except KeyError:
            type_ = 'UNKNOWN'
        message = issue.find('message').text
        node = issue.find('notes')
        notes = node.text.strip() if node is not None else ''
        c.execute('insert into issues  values (?,?,?)',
                      (name, srpm, notes))
        c.execute('replace into tests values(?,?,?)',
                      (name, message, type_))
    conn.commit()


def get_xmltree(path):
    ''' Return parsed xml dom. '''
    return ET.ElementTree(file=path)


def get_test_description(conn, test, prefix=''):
    ''' Return description for a test, possibly prefixed with MUST/SHOULD.
    '''
    res = conn.execute(
        'select message,type from tests where id="%s"' % test)
    text_type = res.fetchone()
    line = prefix
    line += text_type[1].strip() + ': ' if text_type[1] else ''
    line += text_type[0].strip()
    return line


def get_wrapper(indent='    '):
    ''' Return a TextWrapper with a uniform indent. '''
    return TextWrapper(initial_indent=indent, subsequent_indent=indent)


def print_stats(conn):
    ''' Print summary of failed tests. '''
    wrapper = get_wrapper()
    c = conn.cursor()
    names = c.execute('select id from issues')
    results = []
    for name in list(set(names)):
        size = c.execute('select count() from issues where id="%s"' % name[0])
        results.append([name[0], size.fetchone()[0]])
    for r in sorted(results, key=lambda r: r[1], reverse=True):
        print r[1], r[0]
        line = get_test_description(c, r[0])
        for l in wrapper.wrap(line):
            print l


def print_legend(conn):
    ''' Print explanation for each test. '''
    c = conn.cursor()
    for row in c.execute('select * from tests order by id'):
        print row[0].strip(), ': ', row[1].strip()


def print_srpms(conn, test, f, comments=False):
    ''' Print srpms failing given a test. '''
    c = conn.cursor()
    if comments:
        line = get_test_description(c, test)
        wrapper = get_wrapper('    -- ')
        for l in wrapper.wrap(line):
            f.write(l + '\n')

    wrapper = get_wrapper()
    sql = 'select srpm, notes from issues' \
          ' where id="%s" order by srpm' % test
    for row in c.execute(sql):
        f.write(row[0].strip() + '\n')
        if comments and row[1].strip():
            for row in wrapper.wrap(row[1].strip()):
                f.write(row + '\n')


def print_tests(conn, srpm, f, comments=False):
    ''' Print failed tests for a given srpm. '''
    c = conn.cursor()
    c_ = conn.cursor()
    notes_wrapper = get_wrapper()
    comments_wrapper_ = get_wrapper("    -- ")
    sql = 'select id, notes from issues  where srpm="%s" order by id' % srpm
    for row in c.execute(sql):
        f.write(row[0].strip() + '\n')
        if comments:
            line = get_test_description(c_, row[0].strip())
            for l in comments_wrapper_.wrap(line):
                f.write(l + '\n')
            for row in notes_wrapper.wrap(row[1].strip()):
                f.write(row + '\n')


def make_tree(conn):
    ''' Create a tree with reports by issue and by package. '''
    if os.path.exists('tree'):
        print "tree exists, please move out of way"
        sys.exit(1)
    os.makedirs("tree/issues")
    os.makedirs("tree/packages")
    os.makedirs("tree/all-packages")
    c = conn.cursor()
    for row in c.execute("select distinct srpm from issues"):
        srpm = row[0].strip()
        letterdir = "tree/packages/" + srpm[0]
        if not os.path.exists(letterdir):
            os.mkdir(letterdir)
        with open('%s/%s' % (letterdir, srpm), 'w') as f:
            f.write('----- Failed tests for %s ----\n\n' % srpm)
            print_tests(conn, srpm, f, True)
        relpath = "../packages/" + srpm[0] + "/" + srpm
        os.symlink(relpath, "tree/all-packages/" + srpm)
    for row in c.execute("select id from tests"):
        issue = row[0].strip()
        with open('tree/issues/' + issue, 'w') as f:
            f.write('----- Packages failing test %s ----\n\n' % issue)
            print_srpms(conn, issue, f, True)


report = 'stats' if len(sys.argv) < 2 else sys.argv[1]
if report == '-h' or report == '--help':
    print sys.modules[__name__].__doc__
    sys.exit(0)

conn = db_init()
for path in sys.stdin:
    db_insert(conn, get_xmltree(path.strip()))

if report == 'stats':
    print_stats(conn)
elif report == 'legend':
    print_legend(conn)
elif report == 'mktree':
    make_tree(conn)
elif report == 'srpms' or report == 'srpms-full':
    if len(sys.argv) != 3:
        print "I need a test argument..."
        sys.exit(1)
    print_srpms(conn, sys.argv[2], sys.stdout, report == 'srpms-full')
elif report == 'tests' or report == 'tests-full':
    if len(sys.argv) != 3:
        print "I need a srpm argument..."
        sys.exit(1)
    print_tests(conn, sys.argv[2], sys.stdout, report == 'tests-full')
else:
    print sys.modules[__name__].__doc__
    sys.exit(1)
sys.exit(0)
