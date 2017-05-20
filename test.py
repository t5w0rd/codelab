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

TEST = c1:uint8 + b1:bits(2) + b2:bits(3) + b3:bits(2) + b4:bits(1) + c2:uint8
test:TEST
test.c1 = 1
test.b1 = 1
test.b2 = 0
test.b3 = 0
test.b4 = 1
test.c2 = 2
''')

with file('/bin/ls', 'rb') as fp:
    data = fp.read()

elf = p.getVar('elf')
elf.decode(data)
#print elf.dump()

test = p.getVar('test')

#test.decode('a\x40c')
test.decode(test.encode())
print `test.encode()`
print test.dump()
