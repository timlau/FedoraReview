#!/bin/bash
# @group: fonts
# @text: Run repo-font-audit on all fonts in package.
# @type: EXTRA

msg="package to make a comprehensive font review."

rpm -q fontpackages-tools &> /dev/null || {
    msg="Cannot find repo-font-audit, install fontpackages-tools $msg"
    exit $FR_FAIL
}
rpm -q createrepo &> /dev/null || {
    msg="Cannot find createrepo, install createrepo $msg"
    exit $FR_FAIL
}

export TERM=${TERM:-dumb}
[ -d fonts ] || mkdir fonts
cd fonts

createrepo $FR_REVIEWDIR/results >repo-font-audit.log
repo-font-audit results file:///$FR_REVIEWDIR/results \
    >>repo-font-audit.log || {
        echo "Cannot run repo-font-audit"
        exit $FR_FAIL
}
for archive in repo-font-audit*xz; do
    tar xJf $archive && rm $archive || :
done

echo "repo-font-audit analyze results in $PWD/repo-font-audit* files"
exit $FR_PASS
