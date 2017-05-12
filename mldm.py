#!/usr/bin/env python

import struct
import ctypes


MAGIC = '\x28\x88'
LENGTH_SIZE = 2

class mldm:
    def __init__(self):
        self.pos = 0
        pass

    def headerSize(self):
        return len(MAGIC) + 2

    def write(self, buf):
        if not self.pos:
            magic, length = struct.unpack('2sH', buf)
            if magic == MAGIC and length <= 0xffff:
                self.length = length
                left = len(MAGIC) + length
                self.buf = ctypes.create_string_buffer(left)
                return left
        else:
            ctypes.memmove(ctypes.addressof(self.buf) + self.pos, buf, len(buf)
            self.pos += len(buf)
            return len(MAGIC) + self.length - self.pos

        return None


