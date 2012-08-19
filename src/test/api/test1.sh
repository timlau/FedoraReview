#!/bin/sh
#    @name: test1
#    @group: Generic
#    @type: EXTRA     
#    @text: A check solely for test purposes.
#    $url: Guidelines URL, optional
#    $deprecates: test1, test2, ...
#    $needs: test4, test5, ...

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
    #echo $REPLY > /tmp/get_section
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
