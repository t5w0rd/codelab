#!/bin/sh

findelf() {
    files=`find $1 -type f`
    for f in $files; do
        if [[ `file $f|grep 'ELF'` != "" ]]; then
            echo $f
        fi
    done
}

findelf $1
