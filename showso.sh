#!/bin/sh
test() {
    ldd $1 | while read l; do
        so=`echo $l | awk -F ' => ' '{print $1}'`
        so2=`echo $l | awk -F ' => ' '{print $2}' | awk '{print $1}'`
        if [[ $so2 == /* ]]; then
            echo $so2
            test $so2
        else
            if [[ $so == /* ]]; then
                so1=`echo $so | awk '{print $1}'`
                echo $so1
                #test $so1
            else
                echo $so
            fi
        fi
    done
}
test $1|sort -u
