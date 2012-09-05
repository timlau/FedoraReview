#!/bin/bash
# @group: Generic
# @url:http://attachments.org
# @text: Attachments should work properly

echo 'attachment 1'  | attach 8 'Heading 1'
echo 'attachment 2'  | attach 9 'Heading 2'
echo 'Created two attachments'
exit $FR_PASS
