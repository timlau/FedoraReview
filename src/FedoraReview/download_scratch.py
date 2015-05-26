# See: https://bugzilla.redhat.com/show_bug.cgi?id=675140#c1
# From: http://people.redhat.com/mikeb/scripts/download-scratch.py

''' Download a scrath build from koji. '''

import os
import sys
import koji
import urlgrabber
import urlgrabber.progress
import optparse

BASEURL = 'http://kojipkgs.fedoraproject.org/work/'
HUBURL = 'http://koji.fedoraproject.org/kojihub'


def _do_download(task, session, opts):
    ''' Perform download of a single task. '''

    if opts.arches:
        print 'Downloading %s rpms from task %i: %s' \
            % (', '.join(opts.arches), task['id'], koji.taskLabel(task))
    else:
        print 'Downloading rpms from task %i: %s' \
            % (task['id'], koji.taskLabel(task))
    base_path = koji.pathinfo.taskrelpath(task['id'])
    output = session.listTaskOutput(task['id'])
    prog_meter = urlgrabber.progress.TextMeter()
    if output == []:
        print "This build is empty, no files to download"
        sys.exit(1)
    for filename in output:
        if opts.nologs and filename.endswith('log'):
            continue
        elif filename.endswith('.rpm'):
            if opts.arches:
                arch = filename.rsplit('.', 3)[2]
                if arch not in opts.arches:
                    continue
            if 'debuginfo' in filename and opts.nodebug:
                continue
        what = opts.baseurl + base_path + '/' + filename
        urlgrabber.grabber.urlgrab(what, progress_obj=prog_meter)


def _download_scratch_rpms(parser, task_ids, opts):
    ''' Given build id, tasks and CLI options download build results
    to current dir. '''

    if not os.access(os.getcwd(), os.R_OK | os.W_OK | os.X_OK):
        raise IOError("Insufficient permissons for current directory."
                      " Aborting download")
    session = koji.ClientSession(opts.huburl)
    for task_id in task_ids:
        task = session.getTaskInfo(task_id, request=True)
        if not task:
            parser.error('Invalid task ID: %i' % task_id)
        elif task['state'] in (koji.TASK_STATES['FREE'],
                               koji.TASK_STATES['OPEN']):
            parser.error('Task %i has not completed' % task['id'])
        elif task['state'] != koji.TASK_STATES['CLOSED']:
            parser.error('Task %i did not complete successfully' % task['id'])

        if task['method'] == 'build':
            print 'Getting rpms from children of task %i: %s' \
                % (task['id'], koji.taskLabel(task))
            task_opts = {'parent': task_id,
                         'method': 'buildArch',
                         'state': [koji.TASK_STATES['CLOSED']],
                         'decode': True}
            tasks = session.listTasks(opts=task_opts)
        elif task['method'] == 'buildArch':
            tasks = [task]
        else:
            parser.error('Task %i is not a build or buildArch task'
                         % task['id'])
        for task in tasks:
            _do_download(task, session, opts)


def main():
    ''' Main public entry. '''

    usage = 'usage: %prog [options] task-ID [task-ID...]'
    parser = optparse.OptionParser(usage=usage)
    parser.add_option(
        '--arch', action='append', dest='arches', metavar='ARCH', default=[],
        help='Only download packages of the given arch '
        '(may be specified multiple times)')
    parser.add_option(
        '--huburl', '-u', default=HUBURL,
        help='URL of Koji hub (default: %default)')
    parser.add_option(
        '--baseurl', '-b', default=BASEURL,
        help='Base URL for downloading RPMs  (default: %default)')
    parser.add_option('--nologs', '-l', action='store_true',
                      help='Do not download build logs')
    parser.add_option('--nodebug', '-d', action='store_true',
                      help='Do not download debuginfo packages')

    opts, args = parser.parse_args()
    if not args:
        parser.error('At least one task ID must be specified')
    for task_id in args:
        if not task_id.isdigit():
            parser.error('%s is not an integer task ID' % task_id)

    _download_scratch_rpms(parser, [int(tid) for tid in args], opts)


if __name__ == '__main__':
    main()


# vim: set expandtab ts=4 sw=4:
