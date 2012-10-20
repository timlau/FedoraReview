#!/bin/bash
# @group: Generic
# @type: MUST
# @url:http://flags.com
# @text: Flags should work OK
# !!register flag <name>  <doc>
# @register-flag: EPEL6  Enable EPEL6 checking
# @register-flag: EPEL7  Enable EPEL7 checking
# @set-flag: EPEL7 7
if [ -n  "${FR_FLAGS[EPEL5]}" ]; then
    echo "flags:  ${FR_FLAGS['EPEL5']}  ${FR_FLAGS['EPEL6']}"
    exit $FR_PASS
else
    echo EPEL5 flag is not set
    exit $FR_FAIL
fi

