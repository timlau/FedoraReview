#!/bin/bash
# @group: Generic
# @name: generic-srv-opt
# @url: http://fedoraproject.org/wiki/Packaging/Guidelines#PackageDocumentation
# @text: Packages must not store files under /srv, /opt or /usr/local
# @type: MUST

if unpack_rpms; then
    declare -A sizes
    cd rpms-unpacked
    for rpm in *; do
        [ -d "$rpm/opt" ] && opt_rpms=( $rpm ${opt_rpms[@]} )
        [ -d "$rpm/srv" ] && srv_rpms=( $rpm ${srv_rpms[@]} )
        [ -d "$rpm/usr/local" ] && local_rpms=( $rpm ${local_rpms[@]} )
    done

    test -z "${opt_rpms[*]}${srv_rpms[*]}${local_rpms[*]}" && \
        exit $FR_PASS

    echo "Rpm(s) have files under /srv, /opt or /usr/local:"
    for rpm in ${opt_rpms[@]};   do echo "    /opt       $rpm"; done
    for rpm in ${srv_rpms[@]};   do echo "    /srv       $rpm"; done
    for rpm in ${local_rpms[@]}; do echo "    /usr/local $rpm"; done
    exit $FR_FAIL
else
    echo "Cannot unpack rpms (using --prebuilt?)"
    exit $FR_PENDING
fi
