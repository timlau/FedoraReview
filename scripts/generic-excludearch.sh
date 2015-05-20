#!/bin/bash
# vim: set expandtab ts=4 sw=4:
#
# @group: Generic
# @type: MUST
# @deprecates: CheckExcludeArch
# @url:https://fedoraproject.org/wiki/Architectures#ExcludeArch_.26_ExclusiveArch
# @text: Package is not known to require an ExcludeArch tag.
# @register-flag: EXARCH Enable ExcludeArch dependency checking (slow)


declare -A srpm_by_pkg
MSG="INFO: ExclusiveArch dependency checking disabled, enable with EXARCH flag"

function get_spec()
# Get spec file for a given package
{
    if [ -z "${srpm_by_pkg[$1]}" ]; then
        srpm=$( dnf repoquery -C --qf '%{SOURCERPM}' $1 )
        srpm="${srpm%-*}"
        srpm="${srpm%-*}"
        srpm_by_pkg[$1]="$srpm"
    fi
    pkg="${srpm_by_pkg[$1]}"
    [ -f $pkg.spec ] && return
    rm -rf $pkg
    if git clone -q git://pkgs.fedoraproject.org/$pkg.git &>/dev/null; then
        mv $pkg/$pkg.spec . && rm -rf $pkg && return
    else
        yumdownloader -q --source $pkg >/dev/null || {
            echo "WARNING: Cannot get spec for $pkg"
            return
        }
        rpm2cpio *src.rpm | cpio --quiet -id $pkg.spec  \
             && rm *.src.rpm && return
    fi
    echo "WARNING: error unpacking $pkg spec"
    return 1
}

function resolve()
# Return yet not retrieved direct dependencies of packages in $@
{
    for dep in $@; do
        [ -f $dep.spec ] || deps="$deps $dep"
    done
    [ -z "$deps" ] && return
    deps=$(dnf repoquery -C --requires --resolve $deps)
    for dep in $deps; do
        pkg=${dep%-*}
        pkg=${pkg%-*}
        pkgs="$pkgs $pkg"
    done
    echo $pkgs | sort | uniq
}


if [ -z "${FR_FLAGS[EXARCH]}" ]; then
    echo "$MSG" >> .log
    exit $FR_PENDING
fi

[ -d dependencies ] || mkdir dependencies
cd dependencies

for pkg in $(resolve $FR_NAME); do
    get_spec $pkg
done

excludes=$( grep -il ExcludeArch *.spec 2>/dev/null | awk '{printf "%s ",$1}' ||: )
spec_count=$(ls *.spec 2>/dev/null| wc -l)
if [ -z "$excludes" ]; then
    echo "$spec_count specfiles, no ExcludeArch: found"
else
    echo "$spec_count specfiles, ExcludeArch: found"
    echo $excludes
fi
exit $FR_PENDING

