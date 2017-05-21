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

TESTB = c1:uint8 + b1:bits(2) + b2:bits(3) + b3:bits(2) + b4:bits(1) + c2:uint8
test:TESTB
test.c1 = 1
test.b1 = 1
test.b2 = 0
test.b3 = 0
test.b4 = 1
test.c2 = 2
''')

p.execute('''
#import('slde.proto')
SLDE = stx:uint8 + length:uint16@ + data:string(length) + etx:uint8
slde:SLDE
slde.stx = 0x02
slde.etx = 0x03
data:string() = "hello"
slde.length = calcsize(data)
slde.data = data
encode(slde)
ss:string() = "test string"
import('png.proto')
png:PNG
''')

v = p.getVar('png')
with file('test.png', 'rb') as fp:
    data = fp.read()
v.decode(data)

v = p.getVar('png')
#v.encode()
print len(v.encode())
print v.dump()