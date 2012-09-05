#!/bin/bash
# @deprecates: CheckBundledJars
# @group: Java
# @type: MUST
# @url:http://fedoraproject.org/wiki/Packaging:Java#Pre-built_JAR_files_.2F_Other_bundled_software'
# @text: Bundled jar/class files should be removed before build

cd BUILD
jars="$( find . -name \*.jar -o -name \*.class )"
test -z "$jars" && exit $FR_PASS
count=$( echo $jars | wc -w)
cd ..
if (( ${#jars} < 100 )); then
    echo "$count jar or class files(s) in source (see attachment)"
    echo  "$jars" | attach 8 "Jar and class files in source"
else
    echo "$count jar or class(s) file in source, see file bundled-jars.txt"
    for jar in $jars; do
        echo $jar
    done > 'bundled-jars.txt'
fi
exit $FR_FAIL
