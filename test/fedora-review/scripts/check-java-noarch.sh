#!/bin/sh
# @group: Java
# @name: unittest-test1
# @deprecates: CheckNoArch
# @text: Package has BuildArch: noarch (if possible)
egrep -q -i '^ *BuildArch: *noarch *$' srpm-unpacked/$FR_NAME.spec
case $? in
   0) exit $FR_PASS;;
   *) exit $FR_FAIL;;
esac
