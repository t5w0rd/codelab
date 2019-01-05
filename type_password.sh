#!/bin/sh

type_password() {
    local _user=$1
    local _pass=""
    local _pass2="-"
    while [ "$_pass" != "$_pass2" ]; do
        echo -n "$_user's password: "; stty -echo; read _pass; stty echo; echo
        echo -n 'Retype password: '; stty -echo; read _pass2; stty echo; echo
        if [ "$_pass" != "$_pass2" ]; then
            echo 'Sorry, passwords do not match.'
            continue
        fi  
        if [ -z "$_pass" ]; then
            echo 'Sorry, passwords cannot be empty.'
            _pass2="-"
        fi  
    done
    eval $2=$_pass
}

type_password root pass
echo "pass: $pass"
