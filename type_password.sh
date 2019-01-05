#!/bin/sh

type_password() {
    local user=$1
    local pass=""
    local pass2="-"
    while [ "$pass" != "$pass2" ]; do
        echo -n "${user}'s password: "; stty -echo; read pass; stty echo; echo
        echo -n 'Retype password: '; stty -echo; read pass2; stty echo; echo
        if [ "$pass" != "$pass2" ]; then
            echo 'Sorry, passwords do not match.'
            continue
        fi  
        if [ -z "$pass" ]; then
            echo 'Sorry, passwords cannot be empty.'
            pass2="-"
        fi  
    done
    echo $pass
}

type_password root
