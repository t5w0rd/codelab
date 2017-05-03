#!/bin/sh

if [ $# -lt 1 ]; then
    echo "usage: $0 <HOST> [USER]"
    exit 0
fi

HOST_NAME=$1
USER_NAME=$2
KEY_NAME=id_rsa
KEY_FILE=~/.ssh/${KEY_NAME}

if [ -z "${USER_NAME}" ]; then
    USER_NAME=$USER
fi

if [ ! -f "${KEY_FILE}" -o ! -f "${KEY_FILE}.pub" ]; then
    ssh-keygen -t rsa -f ${KEY_FILE} -P ''
fi

ssh-keygen -R ${HOST_NAME}
scp ${KEY_FILE} ${KEY_FILE}.pub ${USER_NAME}@${HOST_NAME}:/tmp/
ssh ${USER_NAME}@${HOST_NAME} "if [ ! -d .ssh ]; then mkdir .ssh && chmod 700 .ssh; fi; cat /tmp/${KEY_NAME}.pub>>.ssh/authorized_keys && chmod 600 .ssh/authorized_keys; rm /tmp/${KEY_NAME}.pub"

