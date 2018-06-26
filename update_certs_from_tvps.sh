#!/bin/sh
scp -P56022 t5w0rd@tvps.tutils.com:~/certs/letsencrypt.tgz /tmp
tar xf /tmp/letsencrypt.tgz -C/etc
rm /tmp/letsencrypt.tgz
service nginx reload
