#!/bin/bash
# @group: Generic
# @url: http://fedoraproject.org/wiki/Packaging:ReviewGuidelines#Package_Review_Guidelines
# @text: Large data in /usr/share should live in a noarch subpackage
# @text: if package is arched.
# @type: EXTRA


min=1000000
max=10000000
datadir='usr/share'

if unpack_rpms; then
    declare -A sizes
    sum=0
    cd rpms-unpacked
    noarchs="$( ls -d *noarch.rpm  2>/dev/null || echo '' )"
    if [ "$noarchs" = "$( ls -d *rpm )" ]; then
        exit $FR_NOT_APPLICABLE
    fi
    for rpm in *; do
        [[ "$rpm" == *noarch.rpm ]]  && continue
        [ -d "$rpm/$datadir" ] || continue
        sizes[$rpm]=$( tar -c $rpm/$datadir | wc -c )
        sum=$((sum + ${sizes[$rpm]}))
    done

    test $sum -lt $min && exit $FR_PASS
    echo "Arch-ed rpms have a total of $sum bytes in /usr/share"
    for rpm in ${!sizes[@]}; do
        [ ${sizes[$rpm]} -gt $max ] && \
            msg=$( printf "$msg, %s:%s" $rpm "${sizes[$rpm]}" )
    done
    msg=${msg#, }
    [ -n "$msg" ] && echo $msg
    test $sum -lt $max && exit $FR_PENDING
    exit $FR_FAIL
else
    exit $FR_PENDING
fi
