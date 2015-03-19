#!/usr/bin/env python

import struct
import re


class Variable:
    def __init__(self, vtype, name, value = None, upvalue = None):
        self.type = vtype
        self.name = name
        self.value = value
        self.upvalue = upvalue


    def __getitem__(self, mname):
        '''var[mname]'''
        if self.value[mname] == None:
            typestr = self.type.mmap[mname]
            vtype = self.type.scope.parseType(typestr, self)
            newvar = vtype.defVar(mname)
            newvar.upvalue = self
            self.value[mname] = newvar

        return self.value[mname]


    def __setitem__(self, mname, value):
        '''var[mname] = value'''

        self.__getitem__(mname).setValue(value)


    def setValue(self, value):
        self.value = value


    def getValue(self):
        return self.value


    def setUpValue(self, upvalue):
        self.upvalue = upvalue


    def getUpValue(self):
        return self.upvalue


    def encode(self):
        return self.type.encode(self)


    def decode(self, data):
        self.type.decode(self, data)


    def calcsize(self):
        return self.type.calcsize(self)


    def dump(self, level = 0):
        def addln(s, ln, level):
            if len(s) > 0:
                s += '\n'
            return s + '    ' * level + ln

        res = str()
        if isinstance(self.value, dict):
            res = addln(res, '\'%s\': {' % (self.name), level)
            first = True
            vtype = self.type
            for name in vtype.mseq:
                var = self.value[name]
                if not var == None:
                    s = var.dump(level = level + 1)
                    if first:
                        first = False
                    else:
                        res += ','

                    res = addln(res, s, 0)

            res = addln(res, '}', level)
        else:
            res = addln(res, '\'%s\': %s' % (self.name, repr(self.value)), level)
        
        return res


    def parseValue(self, exprstr):
        # 0 / 121
        if exprstr.isdigit():
            return int(exprstr)

        # 0x1f / 0xE0
        if exprstr[:2] == '0x':
            return int(exprstr, 16)

        # datalen / hdr2.data.len
        nlist = exprstr.split('.')
        if len(nlist) > 0 and len(nlist[0]) > 0 and len(nlist[-1]) > 0:
            svar = self
            while svar != None:
                check = True
                mvar = svar
                for name in nlist:  # hdr2, data, len
                    mvl = mvar.value
                    if isinstance(mvl, dict) and name in mvl:
                        mvar = mvl[name]  # mvar = mvar.value[name]
                    else:
                        check = False
                        break;
                if check:
                    return mvar.value

                svar = svar.upvalue

            return None

        return None


reBetweenBrackets = re.compile('\((.*)\)')

class Type:
    def __init__(self, scope, name):
        self.scope = scope
        self.name = name


    def defVar(self, name):
        return Variable(self, name)


    def encode(self, var, level = 0):
        pass


    def decode(self, var, data, level = 0):
        pass


    def calcsize(self, var):
        pass


class Basic(Type):
    def __init__(self, scope, name, packstr):
        Type.__init__(self, scope, name)

        self.packstr = packstr


    def encode(self, var, level = 0):
        print '    ' * level + '%s %s = %s' % (self.name, var.name, repr(var.value))
        return struct.pack(self.packstr, var.value)


    def decode(self, var, data, level = 0):
        var.value = struct.unpack_from(self.packstr, data)[0]


    def calcsize(self, var):
        return struct.calcsize(self.packstr)


class String(Basic):
    def __init__(self, scope, length):
        Basic.__init__(self, scope, 'string(%d)' % (length), '%ds' % (length))


class Struct(Type):
    def __init__(self, scope, name, proto):
        '''proto: ((mname, typestr), (mname, typestr), ...)'''
        Type.__init__(self, scope, name)

        mseq = [mname for mname, typestr in proto]  # member sequence
        mmap = dict(proto)  # member name-typestr map

        self.mseq = mseq
        self.mmap = mmap


    def encode(self, var, level = 0):
        print '    ' * level + '%s %s = %s' % (self.name, var.name, '{')
        data = str()
        for mname in self.mseq:
            mtype = self.scope.parseType(self.mmap[mname], var)
            mvar = var.value[mname]
            res = mtype.encode(mvar, level = level + 1)
            if res == None:
                #print 'ERR | encode:' + mname
                return None
            else:
                data += res
        print '    ' * level + '}'
        return data


    def decode(self, var, data, level = 0):
        pos = 0
        for mname in self.mseq:
            mtype = self.scope.parseType(self.mmap[mname], var)
            if var.value[mname] == None:
                var.value[mname] = mtype.defVar(mname)
            mvar = var.value[mname]
            size = mtype.calcsize(mvar)
            mtype.decode(mvar, data[pos: pos + size], level = level + 1)
            pos += size


    def calcsize(self, var):
        size = 0
        for mname in self.mseq:
            mtype = self.scope.parseType(self.mmap[mname], var)
            mvar = var.value[mname]
            res = mtype.calcsize(mvar)
            size += res
        return size


    def defVar(self, name):
        newvar = Type.defVar(self, name)
        mvmap = dict()
        for mname in self.mseq:
            mvmap[mname] = None

        newvar.setValue(mvmap)
        return newvar


    


class Scope(Variable):
    def __init__(self, name):
        Variable.__init__(self, None, name, value = dict(), upvalue = None)
        self.tmap = {
                'uint8': Basic(self, 'uint8', 'B'),
                'uint16': Basic(self, 'uint16', 'H'),
                'uint32': Basic(self, 'uint32', 'I'),
                'uint64': Basic(self, 'uint64', 'Q')
                }


    def defType(self, name, proto):
        newtype = Struct(self, name, proto)
        self.tmap[name] = newtype
        return newtype


    def defVar(self, name, typestr):
        vtype = self.parseType(typestr, self)
        newvar = vtype.defVar(name)
        newvar.upvalue = self
        self.value[name] = newvar
        return newvar


    def parseType(self, typestr, var):
        # vtype(expr)
        expr = reBetweenBrackets.findall(typestr)
        if len(expr) > 0:
            expr = var.parseValue(expr[0])
            vtype = typestr[:typestr.find('(', 1)]

            if vtype in ('string'):
                return String(self, expr)

            typestr = vtype + '(' + str(expr) + ')'

            if typestr in self.tmap:
                return self.tmap[typestr]
            else:
                typestr = vtype + '()'

        # vtype
        if typestr in self.tmap:
            return self.tmap[typestr]

        print '@ERR | typestr(%s)' % (typestr)
        return None



class Context:
    def __init__(self):
        self.scope = Scope('GLOBAL')


    def defType(self, name, protostr):
        proto = [p.split(':', 1) for p in protostr.split(',')]
        return self.scope.defType(name, proto)


    def parseLine(self, ln):
        '''proto HDR ='''
        ln = ln.strip(' \t\r\n')
        protostr = wipechars(ln, ' \t\r\n')


    def wipechars(s, chars):
        lst = list()
        for c in s:
            if not c in chars:
                lst.append(c)

        return ''.join(lst)

        
        
c = Context()
scope = c.scope

c.defType('HDR', 'len:uint16,result:uint8')
c.defType('BODY(0)', 'data:string(hdr.len),crc:string(4)')
c.defType('BODY(1)', 'msg:string(10)')
c.defType('PKG', 'hdr:HDR,body:BODY(hdr.result)')
pkg = scope.defVar('pkg', 'PKG')

hdr = scope.defVar('hdr', 'HDR')
hdr['len'] = 3
hdr['result'] = 0
body = scope.defVar('body', 'BODY(hdr.result)')
body['data'] = 'ABCDEFG'
body['crc'] = 'FFEEGG'
print body.encode()
print body.dump()

hdr = pkg['hdr']
hdr['len'] = 5
hdr['result'] = 1

body = pkg['body']
body['msg'] = 'asdf'
#body['data'] = 'AB'
#body['crc'] = 'abcd'

#pkg['body'] = body


data = pkg.encode()

pkg2 = scope.defVar('pkg2', 'PKG')

pkg2.decode(data)

data2 = pkg2.encode()

print repr(data2)

print pkg2.calcsize()
print pkg2.dump()

#scope['BODY(0)'] = Struct(scope, 'data:s(hdr2.datalen)')
#scope['BODY()'] = Struct(scope, 'err:I, msglen:I, msg:s(msglen)')

#scope['PKT'] = Struct(scope, 'hdr:HDR, hdr2:HDR, body:BODY(hdr.result)')


