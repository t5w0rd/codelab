#!/usr/bin/env python

import struct
import re


class Var:
    def __init__(self, value, upvalue):
        self.data = [value, upvalue]


    def __getitem__(self, mname):
        if self.data[0] == None:
            newvar = Var(None, self)
            self.data[0] = {mname: newvar}
            return newvar
        elif not mname in self.data[0]:
            #return None
            newvar = Var(None, self)
            self.data[0][mname] = newvar
            return newvar

        return self.data[0][mname]
    

    def __setitem__(self, mname, value):
        if self.data[0] == None:
            self.data[0] = {mname: Var(value, self)}
        elif not mname in self.data[0]:
            self.data[0][mname] = Var(value, self)
        else:
            self.data[0][mname].setValue(value)


    def setValue(self, value):
        self.data[0] = value


    def getValue(self):
        return self.data[0]


    def setUpValue(self, upvalue):
        return self.data[1]


    def getUpValue(self):
        return self.data[1]
    

    def parseValue(self, exprstr):
        # 0 / 121
        if exprstr.isdigit():
            return int(exprstr)

        # 0x1f / 0xE0
        if exprstr[:2] == '0x':
            return int(exprstr, 16)

        # datalen / hdr2.data.len
        mlist = exprstr.split('.')
        if len(mlist) > 0 and len(mlist[0]) > 0 and len(mlist[-1]) > 0:
            svar = self
            while svar != None:
                check = True
                mvar = svar
                for m in mlist:  # hdr2, data, len
                    mvl = mvar.getValue()
                    if isinstance(mvl, dict) and m in mvl:
                        mvar = mvl[m]
                    else:
                        check = False
                        break;
                if check:
                    return mvar.getValue()

                svar = svar.getUpValue()
            
            return None

        return None


reBetweenBrackets = re.compile('\((.*)\)')

class Type:
    def __init__(self, scope):
        self.scope = scope

    def newVar(self, value, upvalue):
        pass

    def encode(self, var):
        pass


class Simple(Type):
    def __init__(self, scope, packstr):
        Type.__init__(self, scope)
        
        self.packstr = packstr


    def encode(self, var):
        print 'MSG | encode: ' + self.packstr, var.getValue()
        return struct.pack(self.packstr, var.getValue())


    def newVar(self, value, upvalue):
        return [value, upvalue]


class String(Type):
    def __init__(self, scope, length):
        Type.__init__(self, scope)
        
        self.length = length


    def encode(self, var):
        print 'MSG | encode: ' + str(self.length) + 's', var.getValue()
        return struct.pack(str(self.length) + 's', var.getValue())


class Struct(Type):
    def __init__(self, scope, proto): 
        Type.__init__(self, scope)
        
        proto = proto.replace(' ', '')
        minfos = proto.split(',')

        mseq = list()  # member sequence
        mmap = dict()  # member mmap
        for minfo in minfos:
            mname, mtypestr = minfo.split(':', 1)
            mseq.append(mname)
            mmap[mname] = mtypestr
            
        self.mseq = mseq
        self.mmap = mmap


    def encode(self, var):
        data = str()
        for mname in self.mseq:
            mtype = self.parseType(self.mmap[mname], var)
            mvar = var.getValue()[mname]
            res = mtype.encode(mvar)
            print 'MSG | encode: ' + mname
            if res == None:
                print 'ERR | encode:' + mname
                return None
            else:
                data = data + res

        return data

    def parseType(self, typestr, var):
        # ttt(expr)
        expr = reBetweenBrackets.findall(typestr)
        if len(expr) > 0:
            expr = var.parseValue(expr[0])
            ttt = typestr[:typestr.find('(', 1)]

            if ttt in ('s'):
                return String(scope, expr)
            
            typestr = ttt + '(' + str(expr) + ')'
        
        # ttt
        if typestr in self.scope:
            return self.scope[typestr]
        
        return None


    
'''
HDR = datalen:I, result:I

SP(0) = data:s(datalen)
SP() = err:I, msglen:I, msg:s(msglen)

PKT = hdr:HDR, SP(hdr.result)
SimpleVar = [321, None]
StructVar = [{mname: var, ...}, <table>]

Var[0]  # value
Var[1]  # upvalue pointer


'''
scope = dict()
scope['B'] = Simple(scope, 'B')
scope['H'] = Simple(scope, 'H')
scope['I'] = Simple(scope, 'I')
scope['Q'] = Simple(scope, 'Q')

scope['HDR'] = Struct(scope, 'len:I, result:B')
scope['BODY(0)'] = Struct(scope, 'data:s(hdr.len), crc:s(4)')
scope['BODY()'] = Struct(scope, 'msg:s(10)')
scope['PKG'] = Struct(scope, 'hdr:HDR, body:BODY(hdr.result)')
t = scope['PKG']

#pkg2 = Var(None, None)
#hdr = Var({'len': Var(4, hdr), 'result': Var(0, hdr)}, pkg2)
#body = Var({'data': Var('AB', body)}, pkg2)
#pkg2.setValue({'hdr':hdr, 'body':body})

pkg2 = Var(None, None)
hdr = pkg2['hdr']
hdr['len'] = 5
hdr['result'] = 0

body = pkg2['body']
body['data'] = 'AB'
body['crc'] = 'abcd'

#pkg2['body'] = body



t.encode(pkg2)



#scope['BODY(0)'] = Struct(scope, 'data:s(hdr2.datalen)')
#scope['BODY()'] = Struct(scope, 'err:I, msglen:I, msg:s(msglen)')

#scope['PKT'] = Struct(scope, 'hdr:HDR, hdr2:HDR, body:BODY(hdr.result)')


'''
mname = 'hdr'
mtype = parse('HDR'): ->scope['HDR']
mvar = var['hdr']
mtype.encode(mvar)

...

mname = 'body'
mtype = parse('BODY(hrd.result)', var): res = var.parse('hdr.result'); scope['BODY(%s)' % (res)]
mvar = var['body']
mtype.encode(mvar)

    mname = 'data'
    mtype = parse('s(hdr2.datalen)', var): res = var.parse('hdr2.datalen'); s(res); String(int(res))
    mvar = var['data']
    mtype.encode(mvar)

[{'body': [{'data': ['AB', [...]]}, [...]],
  'hdr': [{'len': [4, [{'len': 4, 'result': 0}, [...]]],
    'result': [0, [{'len': 4, 'result': 0}, [...]]]},
   [...]]},
 None]

PKG pkg
pkg.hdr.len = 4
pkg.hdr.result = 0
pkg.body.data = 'AB'

pkg = scope['PKG'].newVar(None)
pkg.set('hdr.len', 4)
pkg.set('hdr.result', 0)
pkg.set('body.data', 'AB')

'''

