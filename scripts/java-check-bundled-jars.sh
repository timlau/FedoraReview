#!/bin/bash
# @deprecates: CheckBundledJars
# @group: Java
# @type: MUST
# @url:http://fedoraproject.org/wiki/Packaging:Java#Pre-built_JAR_files_.2F_Other_bundled_software'
# @text: Bundled jar/class files should be removed before build

cd BUILD &>/dev/null || {
    echo "Can't find any BUILD directory (--prebuilt option?)"
    exit $FR_PENDING
}
jars="$( find . -name \*.jar -o -name \*.class )"
test -z "$jars" && exit $FR_PASS
echo "Jar files in source (see attachment)"
echo  "$jars" | attach 8 "Jar and class files in source"
exit $FR_FAIL
