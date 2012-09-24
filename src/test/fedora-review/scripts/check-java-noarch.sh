#!/bin/sh
# @group: Java
# @name: unittest-test1
# @deprecates: CheckNoArch
# @text: Package has BuildArch: noarch (if possible)
test is_applicable 'java' || exit $FR_NOT_APPLICABLE
egrep -q -i '^ *BuildArch: *noarch *$' srpm-unpacked/$name.spec 
case $? in
   0) exit $FR_PASS;;
   *) exit $FR_FAIL;;
esac
