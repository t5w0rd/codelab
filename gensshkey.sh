#!/bin/sh

if [ $# -lt 3 ] ; then
    echo "usage: $0 <USER> <HOST> <FILE>"
    exit 0
fi

username=$1
hostname=$2
keyname=$3

#client: ssh1, server: ssh1
ssh-keygen -f ~/.ssh/$keyname
scp ~/.ssh/$keyname.pub $username@$hostname:
ssh $username@$hostname "mkdir .ssh && chmod 755 .ssh; cat $keyname.pub>>.ssh/authorized_keys && chmod 600 .ssh/authorized_keys; rm $keyname.pub"
ssh-add ~/.ssh/$keyname

