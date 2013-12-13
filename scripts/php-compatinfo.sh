#!/bin/bash
# @group: PHP
# @text: Run phpci static analyze on all php files.
# @type: EXTRA

[ -d BUILD ] ||  exit $FR_NOT_APPLICABLE

rpm -q php-bartlett-PHP-CompatInfo &> /dev/null || {
    errmsg="phpcompatinfo not found. Install php-bartlett-PHP-CompatInfo"
    errmsg="$errmsg package to get a more comprehensive php review."
    echo "$errmsg"
    exit $FR_FAIL
}

cp  /etc/pear/PHP_CompatInfo/phpcompatinfo.xml.dist phpcompatinfo.xml
sed -i '/consoleProgress/s/true/false/' phpcompatinfo.xml
phpcompatinfo --configuration=phpcompatinfo.xml print \
    --recursive --report full --report-file $PWD/phpci.log \
    $PWD/BUILD/*
echo "phpci static analyze results in $PWD/phpci.log"
exit $FR_PASS
