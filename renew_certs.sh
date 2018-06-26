#!/bin/sh
CFG=/etc/nginx/sites-enabled
cd $CFG
TMP=$(mktemp -d)
ls -Idefault . |xargs -i mv {} $TMP/
service nginx reload
certbot certonly --webroot -w /var/www/default -d www.tutils.com -d bbs.tutils.com -d bbs-m.tutils.com -d bbs-app.tutils.com -d blog.tutils.com -d git.tutils.com -d test.tutils.com -d tools.tutils.com -d vpn.tutils.com -d mail.tutils.com -d dl.tutils.com -d lab.tutils.com -d tlab.tutils.com -d dnf.tutils.com -d dnfx.tutils.com -d tvps.tutils.com -d tvpsx.tutils.com -d proxy.tutils.com -d dev.tutils.com -d ad.tutils.com -d app.tutils.com -d pay.tutils.com -d code.tutils.com -d game.tutils.com -d play.tutils.com -d img.tutils.com
mv $TMP/* $CFG
service nginx reload
rmdir $TMP
cd /etc
tar czf ~/certs/letsencrypt.tgz letsencrypt
