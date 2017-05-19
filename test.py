#!/usr/bin/env python
#coding:utf-8
import os, sys, time, re, json, socket

import tutils
import proto

p = proto.EqParser()
p.execute('''
import('elf.proto')
elf:ELF64
phdr:ELF64_PHDR
print(calcsize(phdr))
''')

with file('/bin/ls', 'rb') as fp:
    data = fp.read()

elf = p.getVar('elf')
elf.decode(data)
print elf.dump()

