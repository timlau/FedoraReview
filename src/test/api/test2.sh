#!/bin/sh
#    @names: ExtShellTest2, ExtShellTest3
#    @ExtShellTest2.group: Generic
#    @ExtShellTest2.type: EXTRA     
#    @ExtShellTest2.text: A second check solely for test purposes.
#    $url: Guidelines URL, optional
#    @ExtShellTest3.group: Generic
#    @ExtShellTest3.type: EXTRA     
#    @ExtShellTest3.text: A third check solely for test purposes.
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
    "name":"ExtShellTest2",
    "url":"http://nonsensical2.url",
    "group":"Java",
    "deprecates":[],
    "text":"Verify external plugins work OK (#2)",
    "type":"MUST",
    "result":"fail",
    "output_extra":"Ext plugins work! (#2)"
    }
    {
    "name":"ExtShellTest3",
    "url":"http://nonsensical3.url",
    "group":"Perl",
    "deprecates":[],
    "text":"Verify external plugins work OK (#3)",
    "type":"MUST",
    "result":"fail",
    "output_extra":"Ext plugins work! (#3)"
    }



]
}'
