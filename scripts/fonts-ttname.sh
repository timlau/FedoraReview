#!/bin/bash
# @group: fonts
# @text: Run ttname on all fonts in package.
# @type: EXTRA

msg="package to make a comprehensive font review."

rpm -q ttname &> /dev/null || {
    echo "Cannot find ttname command, install ttname $msg"
    exit $FR_FAIL
}
if unpack_rpms; then
    for font in $(find rpms-unpacked -name \*.ttf); do
        echo "----> ${font#.*/}"
        ttname $font
        echo
    done &> ttname.log
else
    echo "Cannot unpack rpms!" >&2
    exit $FR_FAIL
fi

echo "ttname analyze results in fonts/ttname.log."
exit $FR_PASS
