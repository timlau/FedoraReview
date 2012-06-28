#!/usr/bin/python
#
# See: https://bugzilla.redhat.com/show_bug.cgi?id=675140#c1
# From: http://people.redhat.com/mikeb/scripts/download-scratch.py

import sys
import koji
import urlgrabber
import urlgrabber.progress
import optparse

BASEURL = 'http://kojipkgs.fedoraproject.org/work/'

usage = 'usage: %prog [options] task-ID [task-ID...]'
parser = optparse.OptionParser(usage=usage)
parser.add_option('--arch', action='append', dest='arches', metavar='ARCH', default=[],
                  help='Only download packages of the given arch (may be specified multiple times)')

opts, args = parser.parse_args()
if not args:
    parser.error('At least one task ID must be specified')

session = koji.ClientSession('http://koji.fedoraproject.org/kojihub')

for task_id in args:
    if not task_id.isdigit():
        parser.error('%s is not an integer task ID' % task_id)

    task_id = int(task_id)
    task = session.getTaskInfo(task_id, request=True)
    if not task:
        parser.error('Invalid task ID: %i' % task_id)
    elif task['state'] in (koji.TASK_STATES['FREE'], koji.TASK_STATES['OPEN']):
        parser.error('Task %i has not completed' % task['id'])
    elif task['state'] != koji.TASK_STATES['CLOSED']:
        parser.error('Task %i did not complete successfully' % task['id'])

    if task['method'] == 'build':
        print 'Getting rpms from children of task %i: %s' % (task['id'], koji.taskLabel(task))
        tasks = session.listTasks(opts={'parent': task_id, 'method': 'buildArch', 'state': [koji.TASK_STATES['CLOSED']],
                                        'decode': True})
    elif task['method'] == 'buildArch':
        tasks = [task]
    else:
        parser.error('Task %i is not a build or buildArch task' % task['id'])

    prog_meter = urlgrabber.progress.TextMeter()

    for task in tasks:
        if opts.arches:
            print 'Downloading %s rpms from task %i: %s' % (', '.join(opts.arches), task['id'], koji.taskLabel(task))
        else:
            print 'Downloading rpms from task %i: %s' % (task['id'], koji.taskLabel(task))

        base_path = koji.pathinfo.taskrelpath(task['id'])
        output = session.listTaskOutput(task['id'])
        for filename in output:
            download = False
            if opts.arches:
                for arch in opts.arches:
                    if filename.endswith('.%s.rpm' % arch):
                        download = True
                        break
            else:
                if filename.endswith('.rpm'):
                    download = True
            if download:
                urlgrabber.grabber.urlgrab(BASEURL + base_path + '/' + filename,
                                           progress_obj=prog_meter)
