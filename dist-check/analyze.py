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
            As srpms, also prints notes about the tests
    tests-full:
            As tests, also prints notes about the tests
    mktree: Create a tree with reports on packagea and issues.

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
    c.execute('create table tests (id text primary key, message text)')
    conn.commit()
    return conn


def db_insert(conn, tree):
    ''' Insert issues and tests from the parsed xml into db. '''
    srpm = tree.find('metadata/sut/source-rpm').attrib['name']
    c = conn.cursor()
    for issue in tree.findall('results/issue'):
        name = issue.attrib['test-id']
        message = issue.find('message').text
        notes = issue.find('notes')
        notes = notes.text if notes is not None else ''
        c.execute('insert into issues  values (?,?,?)',
                   (name, srpm, notes))
        c.execute('replace into tests values(?,?)', (name, message))
    conn.commit()


def get_xmltree(path):
    ''' Return parsed xml dom. '''
    return ET.ElementTree(file=path)


def print_stats(conn):
    ''' Print summary of failed tests. '''
    wrapper = TextWrapper(initial_indent="    -- ",
                          subsequent_indent="    -- ")
    c = conn.cursor()
    names = c.execute('select id from issues')
    results = []
    for name in list(set(names)):
        size = c.execute('select count() from issues where id="%s"' % name[0])
        results.append([name[0], size.fetchone()[0]])
    for r in sorted(results, key=lambda r: r[1], reverse=True):
        print r[1], r[0]
        text = c.execute('select message from tests where id="%s"' % r[0])
        for l in wrapper.wrap(text.fetchone()[0].strip()):
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
        sql = 'select message from tests where id="%s"' % test
        c.execute(sql)
        message = c.fetchone()
        f.write(test + ': ' + message[0].strip() + '\n')
    wrapper = TextWrapper(initial_indent="    ")
    wrapper.subsequent_indent = "    "
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
    wrapper = TextWrapper(initial_indent="    ", subsequent_indent="    ")
    wrapper_ = TextWrapper(initial_indent="    -- ",
                           subsequent_indent="    -- ")
    sql = 'select id, notes from issues  where srpm="%s" order by id' % srpm
    for row in c.execute(sql):
        f.write(row[0].strip() + '\n')
        if comments:
            sql = 'select message from tests where id="%s"' % row[0].strip()
            c_.execute(sql)
            for line in wrapper_.wrap(c_.fetchone()[0].strip()):
                f.write(line + '\n')
            for row in wrapper.wrap(row[1].strip()):
                f.write(row + '\n')


def make_tree(conn):
    ''' Create a tree with reports by issue and by package. '''
    if os.path.exists('tree'):
        print "tree exists, please move out of way"
        sys.exit(1)
    os.makedirs("tree/issues")
    os.makedirs("tree/packages")
    sql = "select distinct srpm from issues"
    c = conn.cursor()
    for row in c.execute(sql):
        srpm = row[0].strip()
        with open('tree/packages/' + srpm, 'w') as f:
            f.write('----- Failed tests for %s ----\n\n-' % srpm)
            print_tests(conn, srpm, f, True)
    sql = "select id from tests"
    c = conn.cursor()
    for row in c.execute(sql):
        issue = row[0].strip()
        with open('tree/issues/' + issue, 'w') as f:
            f.write('----- Packages failing test %s ----\n\n-' % issue)
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
