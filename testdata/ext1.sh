#!/bin/sh

while read;do
    if [ "$REPLY" == "" ];then
        break
    fi
done

echo '{"supported_api":1,
    "command":"get_section",
    "section":"build"
}'

while read;do
    if [ "$REPLY" == "" ];then
        break
    fi
    echo $REPLY > /tmp/get_section
done

echo '{"supported_api":1,
"command":"results",
"checks":[
    {
    "name":"ExtShellTest",
    "url":"http://nonsensical.url",
    "group":"Java",
    "deprecates":[],
    "text":"Verify external plugins work OK",
    "type":"MUST",
    "result":"fail",
    "output_extra":"Ext plugins work!"
    }
]
}'
