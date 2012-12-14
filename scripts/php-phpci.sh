#!/bin/bash
# @group: PHP
# @text: Run phpci static analyze on all php files.
# @type: EXTRA

rpm -q php-bartlett-PHP-CompatInfo &> /dev/null || {
    echo "Cannot find phpci, install php-bartlett-PHP-CompatInfo"
    exit $FR_FAIL
}

cp  /etc/pear/PHP_CompatInfo/phpcompatinfo.xml.dist phpcompatinfo.xml
sed -i '/consoleProgress/s/true/false/' phpcompatinfo.xml
phpci --configuration=phpcompatinfo.xml print \
    --recursive --report full --report-file $PWD/phpci.log \
    $PWD/BUILD/*
echo "phpci static analyze results in $PWD/phpci.log"
exit $FR_PASS
