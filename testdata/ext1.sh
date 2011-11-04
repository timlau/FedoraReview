#!/bin/sh

while read;do
    if [ "$REPLY" == "" ];then
        break
    fi
done

echo '{"supported_api":1,
"command":"results",
"checks":[
    {
    "name":"ExtShellTest",
    "url":"http://nonsensical.url",
    "group":"Shell",
    "deprecates":[],
    "text":"Verify external plugins work OK",
    "type":"MUST",
    "result":"fail",
    "extra_output":"Ext plugins work!"
    }
]
}'
