#!/bin/bash
# @deprecates: CheckLargeDocs
# @group: Generic
# @name: unittest-test2
# @url: http://fedoraproject.org/wiki/Packaging/Guidelines#PackageDocumentation
# @text: Large documentation must go in a -doc subpackage.


min=10000
max=1000000
docdir='./usr/share/doc'

if unpack_rpms; then
    [ $(ls rpms-unpacked | wc -l) = '0' ] && return FR_PASS
    size=$(for rpm in rpms-unpacked/*; do
               (cd $rpm; test -d $docdir && tar c ./usr/share/doc)
           done | wc -c)
    count=$(for rpm in rpms-unpacked/*; do
               (cd $rpm; test -d $docdir && find $docdir -type f)
            done | wc -l)

    echo "Documentation size is $size bytes in $count files."
    test $size -lt $min && exit $FR_PASS
    test $size -gt $max && exit $FR_FAIL
fi
exit $FR_PENDING
