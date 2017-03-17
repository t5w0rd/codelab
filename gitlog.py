#!/usr/bin/env python

import sys
import os

fn = sys.argv[1]
fn2 = sys.argv[2]

f = open(fn, 'r')
f2 = open(fn2, 'w')

lines = f.readlines()
for line in lines:
    if line[:4] != '    ':
        continue

    fixline = line[4:]
    if fixline[:12] == 'Merge branch':
        continue

    if fixline[:10] == 'Conflicts:':
        continue
    
    if fixline[:21] == 'Merge remote-tracking':
        continue

    if fixline[:1] == '\t':
        continue

    if fixline[:1] == '\n':
        continue

    f2.write(fixline)

f.close()
f2.close()

