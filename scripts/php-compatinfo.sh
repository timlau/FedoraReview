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

LOG=$PWD/phpci.log

if [ -x /usr/share/php-bartlett-PHP-CompatInfo/fedora-review-check ]
then
  # Version > 4
  /usr/share/php-bartlett-PHP-CompatInfo/fedora-review-check $LOG $PWD/BUILD/*

elif [ -f /etc/phpcompatinfo.json ]
then
  # Version > 3
  cd BUILD/*
  phpcompatinfo \
     --no-ansi --no-interaction \
     analyser:run . \
     Extension Class Constant Function Interface Namespace Trait \
     >$LOG
  cd ../..

else
  # Older versions
  cp  /etc/pear/PHP_CompatInfo/phpcompatinfo.xml.dist phpcompatinfo.xml
  sed -i '/consoleProgress/s/true/false/' phpcompatinfo.xml
  phpcompatinfo --configuration=phpcompatinfo.xml print \
    --recursive --report full --report-file $LOG \
    $PWD/BUILD/*
fi

echo -e "$(phpcompatinfo --version) static analyze\nresults in $LOG"
exit $FR_PASS
