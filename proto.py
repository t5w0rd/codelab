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
    		vtype = self.type.parseType(typestr, self)
    		newvar = vtype.create(mname)
    		newvar.setUpValue(self)
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
    def __init__(self, scope, name):
        self.scope = scope
        self.name = name

    def create(self, name):
        return Variable(self, name)

    def encode(self, var, level = 0):
        pass


class Basic(Type):
    def __init__(self, scope, name, packstr):
        Type.__init__(self, scope, name)
        
        self.packstr = packstr


    def encode(self, var, level = 0):
        print '    ' * level + '%s %s = %s' % (self.name, var.name, str(var.getValue()))
        return struct.pack(self.packstr, var.getValue())


class String(Type):
    def __init__(self, scope, length):
        Type.__init__(self, scope, 'string')
        
        self.length = length


    def encode(self, var, level = 0):
        print '    ' * level + '%s(%d) %s = %s' % (self.name, self.length, var.name, repr(var.getValue()))
        return struct.pack(str(self.length) + 's', var.getValue())


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
            mtype = self.parseType(self.mmap[mname], var)
            mvar = var.getValue()[mname]
            res = mtype.encode(mvar, level = level + 1)
            if res == None:
                #print 'ERR | encode:' + mname
                return None
            else:
                data = data + res
        print '    ' * level + '}'
        return data


    def create(self, name):
        newvar = Type.create(self, name)
        mvmap = dict()
        for mname in self.mseq:
            mvmap[mname] = None

        newvar.setValue(mvmap)
        return newvar


    def parseType(self, typestr, var):
        # vtype(expr)
        expr = reBetweenBrackets.findall(typestr)
        if len(expr) > 0:
            expr = var.parseValue(expr[0])
            vtype = typestr[:typestr.find('(', 1)]

            if vtype in ('string'):
                return String(scope, expr)
            
            typestr = vtype + '(' + str(expr) + ')'
        
        # vtype
        if typestr in self.scope.tmap:
            return self.scope.tmap[typestr]
        
        print 'ERR | typestr(%s)' % (typestr)
        return None


def wipechars(s, chars):
	lst = list()
	for c in s:
		if not c in chars:
			lst.append(c)

	return ''.join(lst)


class Scope:
	def __init__(self):
		self.tmap = {
    		'uint8': Basic(self, 'uint8', 'B'),
    		'uint16': Basic(self, 'uint16', 'H'),
    		'uint32': Basic(self, 'uint32', 'I'),
    		'uint64': Basic(self, 'uint64', 'Q')
        }
		self.vmap = dict()


	def defType(self, name, protostr):
		protostr = wipechars(protostr, ' \t\r\n')
		proto = [p.split(':', 1) for p in protostr.split(',')]
		newtype = Struct(self, name, proto)
		self.tmap[name] = newtype
		return newtype


	def defVariable(self, name, vtype):
		newvar = self.tmap[vtype].create(name)
		self.vmap[name] = newvar
		return newvar


scope = Scope()

scope.defType('HDR', 'len:uint16, result:uint8')
scope.defType('BODY(0)', 'data:string(hdr.len), crc:string(4)')
scope.defType('BODY(1)', 'msg:string(10)')
scope.defType('PKG', 'hdr:HDR, body:BODY(hdr.result)')
pkg = scope.defVariable('pkg', 'PKG')

hdr = pkg['hdr']
hdr['len'] = 5
hdr['result'] = 1

body = pkg['body']
body['msg'] = 'asdf'
#body['data'] = 'AB'
#body['crc'] = 'abcd'

#pkg2['body'] = body



print repr(pkg.encode())



#scope['BODY(0)'] = Struct(scope, 'data:s(hdr2.datalen)')
#scope['BODY()'] = Struct(scope, 'err:I, msglen:I, msg:s(msglen)')

#scope['PKT'] = Struct(scope, 'hdr:HDR, hdr2:HDR, body:BODY(hdr.result)')

