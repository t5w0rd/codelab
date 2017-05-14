#!/usr/bin/env python

import struct
import ctypes
import socket


STX = 2
ETX = 3
LENGTH_SIZE = 2
HEADER_SIZE = LENGTH_SIZE + 1


class SldeBuf:
    '''slde = stx:uint8 + length:uint16@ + data:string(length) + etx:uint8'''
    headerSize = HEADER_SIZE

    def __init__(self):
        self.clear()

    def clear(self):
        self.pos = None
        self.writebuf = None

    def write(self, buf):
        '''write headerSize bytes for first, return next bytes to write.if return None, failed.'''
        if self.pos == None and len(buf) >= self.headerSize:
            stx, length = struct.unpack_from('!BH', buf)
            if stx == STX and length <= 0xffff:
                self.length = length
                left = length + 1
                self.writebuf = ctypes.create_string_buffer(self.headerSize + left)
                ctypes.memmove(self.writebuf, buf, self.headerSize)
                self.pos = self.headerSize
                more = len(buf) - self.headerSize
                if more > 0:
                    buf = buf[more:]
                else:
                    return left
            else:
                return None
        
        left = self.length - self.pos - len(buf) + self.headerSize + 1
        if left < 0:
            # beyond the length
            return None

        ctypes.memmove(ctypes.addressof(self.writebuf) + self.pos, buf, len(buf))
        self.pos += len(buf)
        if left > 0:
            return left

        # write finished.
        magic, = struct.unpack_from('B', self.writebuf, self.headerSize + self.length)
        if magic == ETX:
            self.pos = None
            return 0

        return None

    def decode(self):
        '''when'''
        if self.pos == None and self.writebuf != None:
            return ctypes.string_at(ctypes.addressof(self.writebuf) + self.headerSize, self.length)

    def encode(self, data):
        if len(data) <= 0xffff:
            encodebuf = ctypes.create_string_buffer(len(data) + self.headerSize + 1)
            struct.pack_into('!BH%dsB' % (len(data),), encodebuf, 0, STX, len(data), data, ETX)
            return encodebuf.raw



if __name__ == '__main__':
    import proto
    rsp = SldeBuf()
    data = rsp.encode('\x55\xaa\xbb\xcc\x44')
    p = proto.EqParser()
    p.execute('''
    SLDE = stx:uint8 + length:uint16@ + data:string(length, 'hex') + etx:uint8
    data:SLDE
    ''')
    pdata = p.getVar('data')
    pdata.decode(data)
    print pdata.dump()

    rsp.clear()
    rsp.write('\x02\x00\x05')
    rsp.write('abc12\x03')
    print rsp.decode()

