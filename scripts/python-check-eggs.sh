#!/bin/bash
# @group: Python
# @url: http://fedoraproject.org/wiki/Packaging:Python#Packaging_eggs_and_setuptools_concerns
# @text: Binary eggs must be removed in %prep

if [ ! -d BUILD/${FR_NAME}-*  ]; then
    echo "Cannot find sources under BUILD (using prebuilt sources?)"
    exit $FR_PENDING
fi

cd BUILD/${FR_NAME}-*
eggs=$( find . -name \*.egg)
if [ -n "$eggs" ]; then
    echo "Binary egg files not removed in %prep: $eggs"
    exit $FR_FAIL
else
    exit $FR_PASS
fi
