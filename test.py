#!/usr/bin/env python
#coding:utf-8
import os, sys, time, re, json, socket

import tutils
import proto

MAGIC='\n\n# IKJBGAD&ADE\n\n'
import os, sys
def attachData(fn, header, text, end_offset=-100):
    with file(fn, 'rb+') as fp:
        fp.seek(0, os.SEEK_END)
        size = fp.tell()
        off = max(-size, min(0, end_offset))
        fp.seek(off, os.SEEK_END)
        s = fp.read()
        pos = s.find(MAGIC)
        if pos >= 0:
            fp.seek(off + pos, os.SEEK_END)

        fp.write(header)
        fp.write(text)
        fp.truncate()

print os.path.abspath(sys.argv[0])

# IKJBGAD&ADE

#1234jkjjkj lkjadsf
