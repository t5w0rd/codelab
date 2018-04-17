#!/usr/bin/env python

#hardtype2 + prototype2 + hardaddrlen1 + protoaddrlen1 + optype2 + srcmac6 + srcip4 + dstmac6 + dstip4

png_sig = '\x89\x50\x4e\x47\x0d\x0a\x1a\x0a'

#png_chunk = datalen:4 + type:4 + data:datalen vh+ crc:4

chunk = Chunk('png_chunk')
chunk.setProto('datalen:I, type:I, data:ihdr, crc:4')
chunk.setProto('datalen:I, type:I, data:s:datalen, crc:4')

class Chunk:
    def __init__(self, proto):
        proto = proto.replace(' ', '')
        lst = proto.split(',')
        vseq = list()
        vmap = dict()
        for v in lst:
            (vname, vtype) = v.lsplit(':', 1)
            vseq.append(vname)
            vmap[vname] = [vtype, None]

        self.vseq = vseq
        self.vmap = vmap


raw = chunk.pack(type = 12, data = data, datalen = len(data), crc = 1341234)

chunk.unpack2(raw)
(('datalen', 13), ('type', 12), ('data', 'asdasdf'), ('crc', 1341234))
chunk.unpack(raw)
{'datalen': 13, 'type': 12, ...}


ihdr = Chunk('ihdr')
ihdr.setProto('width:4, height:4, bitdepth:1, colortype:1...')

