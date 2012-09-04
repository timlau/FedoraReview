#!/bin/bash
# @deprecates: CheckBundledJars
# @group: Java
# @type: MUST
# @url:http://fedoraproject.org/wiki/Packaging:Java#Pre-built_JAR_files_.2F_Other_bundled_software'
# @text: Bundled jar/class files should be removed before build

if [ ! -d BUILD/${FR_NAME}-*  ]; then
    echo "Cannot find sources under BUILD (using prebuilt sources?)"
    exit $FR_PENDING
fi

cd "BUILD/${FR_NAME}-*"
jars=$( find . -name \*.jar -o -name \*.class)

test -z "$jars" && exit $FR_PASS
echo "Jar/class files in source: $jars"
exit $FR_FAIL
