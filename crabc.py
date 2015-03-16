#!/usr/bin/env python

import os
import sys
import zipfile
import shutil


def decode(data, name):
    primes = (0x2717, 0x2719, 0x2735, 0x2737, 0x274d, 0x2753)

    out = list(data)

    data_size = len(data)
    name_size = len(name)

    prime = 0
    for i in primes:
        if data_size % i:
            prime = i
            break

    name_index = 0
    for i in xrange(data_size):
        index = prime * i

        r2 = ord(data[i])
        r3 = ord(name[name_index])

        A = (0L << 32) + index
        B = (0L << 32) + data_size

        mod = A % B

        pos = mod & 0xFFFFFFFF

        out[pos] = chr(r2 ^ r3)

        name_index = (name_index + 1) % name_size

    return ''.join(out)

def unzip(path):
    title = os.path.splitext(os.path.splitext(os.path.basename(path))[0])[0]
    password = 'cocos2d: ERROR: Invalid filename %s' % (title)
    f = zipfile.ZipFile(path)
    name = f.filelist[0].filename
    data = f.read(name, password)
    f.close()
    return data

def shell(cmd):
    pipe = os.popen(cmd)
    out = pipe.read()
    pipe.close()
    return out

def main():
    LUA_SIG = '\x1b\x4c\x75\x61'

    inroot = os.path.abspath(sys.argv[1])
    outroot = os.path.abspath(sys.argv[2])
    luadec = os.path.abspath(sys.argv[3])

    if not os.path.exists(outroot):
        os.makedirs(outroot)

    for path, dirs, files in os.walk(inroot):
        for fn in files:
            fullname = path + os.path.sep + fn
            basename = os.path.basename(fullname)
            zipname = fullname.replace(inroot, outroot, 1) + '.zip'
            zippath = os.path.dirname(zipname)
            luacname = zippath + os.path.sep + os.path.splitext(basename)[0] + '.luac'
            luaname = zippath + os.path.sep + os.path.splitext(basename)[0] + '.lua'
            txtname = zippath + os.path.sep + os.path.splitext(basename)[0] + '.txt'

            print '=> %s ...' % (luacname)
            
            f = open(fullname, 'rb')
            data = f.read()
            f.close()

            data2 = decode(data, basename)
            
            if not os.path.exists(zippath):
                os.makedirs(zippath)
            
            f = open(zipname, 'wb')
            f.write(data2)
            f.close()

            data3 = unzip(zipname)

            if data3[:4] == LUA_SIG:
                f = open(luacname, 'wb')
                f.write(data3)
                f.close()
                
                cmd = '%s %s>%s && rm %s' % (luadec, luacname, luaname, luacname)
                shell(cmd)

            else:
                f = open(txtname, 'wb')
                f.write(data3)
                f.close()

            os.remove(zipname)


if __name__ == '__main__':
    main()
