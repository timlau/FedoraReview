#!/bin/bash
# @group: Perl
# @url: http://fedoraproject.org/wiki/Packaging:Perl
# @text: CPAN urls should be non-versioned.

if [[ "${FR_URL^^}" ==  *CPAN* ]]; then
    exit $FR_PENDING
else
    exit $FR_NOT_APPLICABLE
fi
