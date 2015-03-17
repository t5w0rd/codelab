#!/usr/bin/env python

#hardtype2 + prototype2 + hardaddrlen1 + protoaddrlen1 + optype2 + srcmac6 + srcip4 + dstmac6 + dstip4

png_sig = '\x89\x50\x4e\x47\x0d\x0a\x1a\x0a'

#png_chunk = datalen:4 + type:4 + data:datalen vh+ crc:4

chunk = Chunk('png_chunk')
chunk.setProto('datalen:I, type:I, data:ihdr, crc:4')
chunk.setProto('datalen:I, type:I, data:s:datalen, crc:4')


proto = chunk.proto.replace(' ', '')
lst = proto.split(',')
vmap = dict()
vseq = list()
for v in lst:
    (name, type) = v.lsplit(':', 1)
    vseq.append(name)
    vmap[name] = [type, None]


chunk.setData('type', '12')
raw = chunk.pack(type = 12, data = data, datalen = len(data), crc = 1341234)

chunk.unpack2(raw)
(('datalen', 13), ('type', 12), ('data', 'asdasdf'), ('crc', 1341234))
chunk.unpack(raw)
{'datalen': 13, 'type': 12, ...}


ihdr = Chunk('ihdr')
ihdr.setProto('width:4, height:4, bitdepth:1, colortype:1...')

