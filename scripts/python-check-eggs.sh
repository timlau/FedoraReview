#!/bin/bash
# @group: Python
# @url: http://fedoraproject.org/wiki/Packaging:Python#Packaging_eggs_and_setuptools_concerns
# @text: Binary eggs must be removed in %prep

cd BUILD/*
eggs=$( find . -name \*.egg)
if [ -n "$eggs" ]; then
    echo "Binary egg files not removed in %prep: $eggs"
    exit $FR_FAIL
else
    exit $FR_PASS
fi
