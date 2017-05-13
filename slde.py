#!/usr/bin/env python

import struct
import ctypes
import socket


STX = 2
ETX = 3
LENGTH_SIZE = 2
HEADER_SIZE = LENGTH_SIZE + 1


class slde:
    '''slde = stx:uint8 + length:uint16@ + data:string(length) + etx:uint8'''
    def __init__(self):
        self.pos = None

    def write(self, buf):
        if self.pos == None and len(buf) == HEADER_SIZE:
            stx, length = struct.unpack('!BH', buf)
            if stx == STX and length <= 0xffff:
                self.length = length
                left = length + 1
                self.buf = ctypes.create_string_buffer(left)
                self.pos = 0
                return left
        else:
            ctypes.memmove(ctypes.addressof(self.buf) + self.pos, buf, len(buf))
            self.pos += len(buf)
            left = self.length - self.pos + 1
            if left > 0:
                return left
            elif left == 0:
                magic, = struct.unpack_from('B', self.buf, self.length)
                if magic == ETX:
                    self.buf = ctypes.string_at(self.buf, self.length)
                    self.pos = None
                    return 0
        return None

    def data(self):
        if self.pos == None and self.buf != None:
            return self.buf


if __name__ == '__main__':
    import proto
    rsp = slde()
    towrite = ('\x02\x00\x0a', 'abc', '1234', '\xaa\xbb', '\x0d\x03')
    for w in towrite:
        left = rsp.write(w)
        print left, 'left'
    data = rsp.data()
    p = proto.EqParser()
    p.execute('''
    SLDE = stx:uint8 + length:uint16@ + data:string(length, 'hex') + etx:uint8
    data:SLDE
    ''')
    pdata = p.getVar('data')
    pdata.decode(''.join(towrite))
    print pdata.dump()

