#!/usr/bin/env python
#
#  proto - Encode or decode data by proto expression.
#  Created by 5w0rd 2015.
#  Email: lightning_0721@163.com
#
#

import ctypes
import re
import struct
import codecs

__all__ = ["EqParser", ]


class Variable:
    def __init__(self, vtype, name, value=None, upvalue=None):
        self.type = vtype
        self.name = name
        self.value = value
        self.upvalue = upvalue
        self._offset = 0  # after decode, _offset will be set

    def __str__(self):
        return '%s(%s:%s = %r)' % (self.__class__, self.name, self.type.name, self.value)

    __repr__ = __str__

    def __getitem__(self, k):
        '''var[k]'''
        return self.value[k].value

    def __setitem__(self, k, value):
        '''var[k] = value'''
        self.value[k].value = value

    def isStruct(self):
        return isinstance(self.value, dict)

    def isArray(self):
        return isinstance(self.value, list)

    def setValue(self, value):
        self.value = value

    def getValue(self):
        return self.value

    def setUpValue(self, upvalue):
        self.upvalue = upvalue

    def getUpValue(self):
        return self.upvalue

    def encode(self):
        parser = self.type._scope._parser
        parser.refValCache()
        parser._onceoffset = 0
        data = self.type.encode(self)
        parser.unrefValCache()
        return data

    def decode(self, data):
        parser = self.type._scope._parser
        parser.refValCache()
        parser._oncesize = len(data)
        parser._onceoffset = 0
        size = self.type.decode(self, data)
        parser.unrefValCache()
        # parser._oncesize = 0
        return size

    def calcsize(self):
        parser = self.type._scope._parser
        parser.refValCache()
        size = self.type.calcsize(self)
        parser.unrefValCache()
        return size

    def dump(self, mode='str', **params):
        parser = self.type._scope._parser
        parser._onceoffset = 0
        return self.type.dump(self, mode=mode, **params)


class Type:
    def __init__(self, scope, name, defval=None):
        self._scope = scope
        self.name = name
        self._defval = defval
        # print('D|newType(%s)' % (name))

    def __str__(self):
        return '%s(%s)' % (self.__class__, self.name)

    __repr__ = __str__

    def allocVar(self, name):
        if isinstance(name, str):
            fakename = name.replace('_', 'a')
            if not fakename[0].isalpha() or not fakename.isalnum():
                return None
        elif isinstance(name, int):  # elements of array
            name = '[' + str(name) + ']'
        else:  # failed
            return None

        # print('D|alloc var(%s:%s)' % (name, self.name))
        return Variable(self, name, value=self._defval)

    def parser(self):
        return self._scope._parser

    def encode(self, var, level=0):
        pass

    def decode(self, var, buf, level=0):
        pass

    def calcsize(self, var):
        pass

    def transform(self, val):
        return val

    def dump(self, var, mode='str', **params):
        if mode == 'str':
            return self.dumpstr(var, **params)
        elif mode == 'dict':
            params['data'] = dict()
            return self.dumpdict(var, **params)
        else:
            return None

    def dumpstr(self, var, short=True, level=0):
        res = '%08x  %s' % (var._offset, '    ' * level) + '%s %s = %r' % (
        self.name, var.name, self.transform(var.value))
        return res

    def dumpdictset(self, data, name, val):
        if isinstance(data, dict):
            data[name] = val
        elif isinstance(data, list):
            data.append(val)

        return data

    def dumpdict(self, var, data=None, transform=False):
        val = var.value
        if val != None and transform:
            val = self.transform(val)

        return self.dumpdictset(data, var.name, val)


class Basic(Type):
    def __init__(self, scope, name, packfmt, defval=None):
        Type.__init__(self, scope, name, defval=defval)
        self.packfmt = packfmt

    def encode(self, var, level=0):
        var._offset = self.parser()._onceoffset
        # print('E| ' + '    ' * level + '%s %s = %r' % (self.name, var.name, self.transform(var.value)))
        ret = struct.pack(self.packfmt, var.value)
        self.parser()._onceoffset += len(ret)
        return ret

    def decode(self, var, buf, level=0):
        offset = self.parser()._onceoffset
        var._offset = offset
        var.value, = struct.unpack_from(self.packfmt, buf, offset)
        # print('D| ' + '    ' * level + '%s %s = %r' % (self.name, var.name, self.transform(var.value)))
        ret = self.calcsize(var)
        self.parser()._onceoffset = offset + ret
        return ret

    def calcsize(self, var):
        return struct.calcsize(self.packfmt)


class String(Type):
    def __init__(self, scope, size, encoding=None, defval=''):
        name = 'string('
        packfmt = ''
        if size != None:
            name += str(size)
        if encoding != None:
            name += ',' + repr(encoding)
        name += ')'
        Type.__init__(self, scope, name, defval=defval)
        self.size = size
        self.encoding = encoding

    def encode(self, var, level=0):
        var._offset = self.parser()._onceoffset
        packfmt = self._packfmt(var)
        # print('E| ' + '    ' * level + '%s %s = %r' % (self.name, var.name, self.transform(var.value[:int(packfmt[:-1])])))
        ret = struct.pack(packfmt, var.value)
        self.parser()._onceoffset += len(ret)
        return ret

    def decode(self, var, buf, level=0):
        offset = self.parser()._onceoffset
        var._offset = offset
        packfmt = self._packfmt(var)
        try:
            var.value, = struct.unpack_from(packfmt, buf, offset)
        except Exception as msg:
            raise Exception("%s packfmt(%r)" % (msg, packfmt))

        # print('D| ' + '    ' * level + '%s %s = %r' % (self.name, var.name, self.transform(var.value[:int(packfmt[:-1])])))
        ret = self.calcsize(var)
        self.parser()._onceoffset = offset + ret
        return ret

    def calcsize(self, var):
        return struct.calcsize(self._packfmt(var))

    def _packfmt(self, var):
        if self.size is None:
            return str(len(var.value)) + 's'
        return str(self.size) + 's'

    def transform(self, val):
        if self.encoding != None:
            # return val.decode(self.encoding)
            return codecs.encode(val, self.encoding).decode('utf-8')
            # return base64.b64decode(val).decode('utf-8')
        return val

    def dumpstr(self, var, short=True, level=0):
        packfmt = self._packfmt(var)
        val = self.transform(var.value[:int(packfmt[:-1])])
        if short and len(val) > 24:
            val = val[:20] + '...'
        res = '%08x  %s' % (var._offset, '    ' * level) + '%s %s = %r' % (self.name, var.name, val)
        return res


class Bits(Type):
    class BitsSize:
        def __init__(self, wide):
            self.wide = wide

    def __init__(self, scope, wide, defval=0):
        Type.__init__(self, scope, 'bits(' + str(wide) + ')', defval=defval)
        self.wide = wide

    def encode(self, var, level=0):
        var._offset = self.parser()._onceoffset
        # print('E| ' + '    ' * level + '%s %s = %r' % (self.name, var.name, self.transform(var.value)))
        return Bits.BitsSize(self.wide)

    def decode(self, var, buf, level=0):
        offset = self.parser()._onceoffset
        var._offset = offset
        # print('D| ' + '    ' * level + '%s %s = %r' % (self.name, var.name, self.transform(var.value)))
        return Bits.BitsSize(self.wide)

    def calcsize(self, var):
        return Bits.BitsSize(self.wide)

    def dumpstr(self, var, short=True, level=0):
        if var._offset >= 0:
            return Type.dumpstr(self, var, short=short, level=level)
        res = ' +%d bits  %s' % (-var._offset, '    ' * level) + '%s %s = %r' % (
        self.name, var.name, self.transform(var.value))
        return res

    @staticmethod
    def encodebits(bitpack):
        parser = None
        ret = str()
        binpack = str()
        pos = 0
        for var in bitpack:
            if parser is None:
                parser = var.type.parser()
            off = pos % 8
            if off > 0:
                var._offset = -off
            else:
                var._offset += pos / 8
            wide = var.type.wide
            pos += wide
            # var.value = (~(0xffffffff << wide)) & 0xffffffff & var.value  # ignore out of range bits
            s = bin(var.value)[2:][-wide:]
            s = '0' * (wide - len(s)) + s
            binpack += s

        bytelist = list()
        bytenum = Bits.calcsizebits(len(binpack))
        binpack += '0' * (bytenum * 8)
        ret = struct.pack(str(bytenum) + 'B', *[int(binpack[i * 8:i * 8 + 8], 2) for i in xrange(bytenum)])
        parser._onceoffset += len(ret)
        return ret

    @staticmethod
    def decodebits(bitpack, buf):
        parser = None
        wide = 0
        for var in bitpack:
            if parser is None:
                parser = var.type.parser()
            wide += var.type.wide
        offset = parser._onceoffset
        bytenum = Bits.calcsizebits(wide)
        buf = buf[offset:offset + bytenum]
        binpack = [bin(ord(b))[2:] for b in buf]
        binpack = ''.join(['0' * (8 - len(b)) + b for b in binpack])
        pos = 0
        for var in bitpack:
            off = pos % 8
            if off > 0:
                var._offset = -off
            else:
                var._offset += pos / 8
            wide = var.type.wide
            var.value = int(binpack[pos:pos + wide], 2)
            pos += wide

        parser._onceoffset = offset + bytenum
        return bytenum

    @staticmethod
    def calcsizebits(bitpack):
        return (bitpack + 7) / 8


class Struct(Type):
    def __init__(self, scope, name, proto):
        '''proto: ((fname, typeexpr), (fname, typeexpr), ...)'''
        Type.__init__(self, scope, name)

        self.fseq = [fname for fname, typeexpr in proto]  # member sequence
        self.ftypeexpr = dict(proto)  # member name-typeexpr map

    def allocVar(self, name):
        var = Type.allocVar(self, name)
        if var is None:
            return None

        fvmap = dict()
        for fname in self.fseq:
            fvmap[fname] = None

        var.value = fvmap
        return var

    def encode(self, var, level=0):
        var._offset = self.parser()._onceoffset
        # print('E| ' + '    ' * level + '%s %s = {' % (self.name, var.name))
        ret = str()
        bitpack = None
        bitflag = False
        for fname in self.fseq:
            fvar = var.value[fname]
            if fvar is None:  # try to use defval
                ftype = self._scope.getType(self.ftypeexpr[fname], var)
                fvar = ftype.allocVar(fname)
            else:
                ftype = fvar.type
            
            if isinstance(ftype, Bits):
                ftype.encode(fvar, level=level + 1)
                if not bitflag:  # begin pack bits
                    bitflag = True
                    bitpack = list()
                bitpack.append(fvar)
            else:
                if bitflag:  # end pack bits var
                    bitflag = False
                    ret += Bits.encodebits(bitpack)
                ret += ftype.encode(fvar, level=level + 1)
        if bitflag:  # end pack bits
            bitflag = False
            ret += Bits.encodebits(bitpack)
        # print('E| ' + '    ' * level + '}')
        return ret

    def decode(self, var, buf, level=0):
        var._offset = self.parser()._onceoffset
        # print('D| ' + '    ' * level + '%s %s = {' % (self.name, var.name))
        if type(buf) == str:
            buf = ctypes.create_string_buffer(init=buf, size=len(buf))
        pos = 0
        bitpack = None
        bitflag = False
        for fname in self.fseq:
            # print('###', self.ftypeexpr[fname])
            ftype = self._scope.getType(self.ftypeexpr[fname], var)
            # print('@@ %d\t%s\t%s\t%s' % (self.parser()._onceoffset, var.name, fname, ftype.name))
            fvar = ftype.allocVar(fname)
            fvar.upvalue = var
            var.value[fname] = fvar
            if isinstance(ftype, Bits):
                ftype.decode(fvar, buf, level=level + 1)
                if not bitflag:  # begin pack bits var
                    bitflag = True
                    bitpack = list()
                bitpack.append(fvar)
            else:
                if bitflag:  # end pack bits var
                    bitflag = False
                    pos += Bits.decodebits(bitpack, buf)
                pos += ftype.decode(fvar, buf, level=level + 1)
        if bitflag:  # end pack bits
            bitflag = False
            pos += Bits.decodebits(bitpack, buf)
        # print('D| ' + '    ' * level + '}')
        return pos

    def calcsize(self, var):
        size = 0
        bitpack = 0
        bitflag = False
        for fname in self.fseq:
            ftype = self._scope.getType(self.ftypeexpr[fname], var)
            fvar = var.value[fname]
            if fvar is None:
                fvar = ftype.allocVar(fname)
            res = ftype.calcsize(fvar)
            if isinstance(res, Bits.BitsSize):  # bits
                if not bitflag:  # begin pack bits
                    bitflag = True
                    bitpack = 0
                bitpack += res.wide
            else:
                if bitflag:  # end pack bits
                    bitflag = False
                    size += Bits.calcsizebits(bitpack)
                size += res
        if bitflag:  # end pack bits
            bitflag = False
            size += Bits.calcsizebits(bitpack)
        return size

    def dumpstr(self, var, short=True, level=0):
        res = '%08x  %s' % (var._offset, '    ' * level) + '%s %s = {' % (self.name, var.name)
        size = len(res)
        for fname in self.fseq:
            fvar = var.value[fname]
            if fvar != None:
                # ftype = self._scope.getType(self.ftypeexpr[fname], var)
                ftype = fvar.type
                res += '\n' + ftype.dumpstr(fvar, short=short, level=level + 1)
        if len(res) == size:
            res += '-' * 8 + '  ' + '}'
        else:
            res += '\n' + '-' * 8 + '  ' + '    ' * level + '}'
        return res

    def dumpdict(self, var, data=None, transform=False):
        val = dict()
        for fname in self.fseq:
            fvar = var.value[fname]
            if not fvar is None:
                # ftype = self._scope.getType(self.ftypeexpr[fname], var)
                ftype = fvar.type
                ftype.dumpdict(fvar, data=val, transform=transform)
            else:
                val = None
        return self.dumpdictset(data, var.name, val)


class Array(Type):
    def __init__(self, scope, itype, size, datasize=False):
        '''typeexpr: BODY(hdr.result)'''
        if not datasize:
            Type.__init__(self, scope, '%s[%d]' % (itype.name, size))
        else:
            Type.__init__(self, scope, '%s[<%d>]' % (itype.name, size))
        self.itype = itype
        self.usedatasize = datasize  # size is dynamic
        if not self.usedatasize:
            self.size = size
            self.datasize = None
        else:
            self.size = None
            self.datasize = size

    def allocVar(self, name):
        var = Type.allocVar(self, name)
        if var is None:
            return None

        if self.usedatasize:
            var.value = list()
        else:
            var.value = [None] * self.size
        return var

    def encode(self, var, level=0):
        var._offset = self.parser()._onceoffset
        # print('E| ' + '    ' * level + '%s %s = [' % (self.name, var.name))
        ret = str()
        for index in range(self.size):
            ivar = var.value[index]
            if ivar is None:  # try to use defval
                ivar = self.itype.allocVar(index)
            ret += self.itype.encode(ivar, level=level + 1)
        # print('E| ' + '    ' * level + ']')
        return ret

    def decode(self, var, buf, level=0):
        offset = self.parser()._onceoffset
        var._offset = offset
        # print('D| ' + '    ' * level + '%s %s = [' % (self.name, var.name))
        if type(buf) == str:
            buf = ctypes.create_string_buffer(init=buf, size=len(buf))
        pos = 0
        index = 0
        while (not self.usedatasize and index < self.size) or (self.usedatasize and pos < self.datasize):
            # for index in range(self.size):
            ivar = self.itype.allocVar(index)
            ivar.upvalue = var
            if self.usedatasize:
                var.value.append(ivar)
            else:
                var.value[index] = ivar
            pos += self.itype.decode(ivar, buf, level=level + 1)
            index += 1
        if self.usedatasize:
            self.__init__(self._scope, self.itype, index, datasize=False)
        # print('D| ' + '    ' * level + ']')
        return pos

    def calcsize(self, var):
        total = 0
        for index in range(self.size):
            ivar = var.value[index]
            total += self.itype.calcsize(ivar)
        return total

    def dumpstr(self, var, short=True, level=0):
        res = '%08x  %s' % (var._offset, '    ' * level) + '%s %s = [' % (self.name, var.name)
        size = len(res)
        count = 0
        for index in range(self.size):
            ivar = var.value[index]
            if ivar != None:
                if short:
                    count += 1
                    if count > 5:
                        res += '\n' + '-' * 8 + '  ' + '    ' * (level + 1) + '...'
                        break
                res += '\n' + self.itype.dumpstr(ivar, short=short, level=level + 1)
        if len(res) == size:
            res += '-' * 8 + '  ' + ']'
        else:
            res += '\n' + '-' * 8 + '  ' + '    ' * level + ']'
        return res

    def dumpdict(self, var, data=None, transform=False):
        val = list()
        for ivar in var.value:
            if not ivar is None:
                ivar.type.dumpdict(ivar, data=val, transform=transform)
            else:
                val = None
        return self.dumpdictset(data, var.name, val)


class IPv4(Type):
    def __init__(self, scope, defval='0.0.0.0'):
        Type.__init__(self, scope, 'IPv4', defval=defval)

    def encode(self, var, level=0):
        var._offset = self.parser()._onceoffset
        # print('E| ' + '    ' * level + '%s %s = %s' % (self.name, var.name, self.transform(var.value)))
        ret = struct.pack('4B', *[int(b) for b in var.value.split('.')])
        self.parser()._onceoffset += len(ret)
        return ret

    def decode(self, var, buf, level=0):
        offset = self.parser()._onceoffset
        var._offset = offset
        var.value = '.'.join([str(b) for b in struct.unpack_from('4B', buf, offset)])
        # print('D| ' + '    ' * level + '%s %s = %s' % (self.name, var.name, self.transform(var.value)))

        self.parser()._onceoffset = offset + 4
        return 4

    def calcsize(self, var):
        return 4

    def dumpstr(self, var, short=True, level=0):
        res = '%08x  %s' % (var._offset, '    ' * level) + '%s %s = %s' % (
            self.name, var.name, self.transform(var.value))
        return res


class MAC(Type):
    def __init__(self, scope, defval='00:00:00:00:00:00'):
        Type.__init__(self, scope, 'MAC', defval=defval)

    def encode(self, var, level=0):
        var._offset = self.parser()._onceoffset
        # print('E| ' + '    ' * level + '%s %s = %s' % (self.name, var.name, self.transform(var.value)))
        ret = struct.pack('6B', *[int(b, 16) for b in var.value.split(':')])
        self.parser()._onceoffset += len(ret)
        return ret

    def decode(self, var, buf, offset=0, level=0):
        offset = self.parser()._onceoffset
        var._offset = offset
        var.value = ':'.join([b.encode('hex') for b in buf[offset:offset + 6]])
        # print('D| ' + '    ' * level + '%s %s = %s' % (self.name, var.name, self.transform(var.value)))
        self.parser()._onceoffset = offset + 6
        return 6

    def calcsize(self, var):
        return 6

    def dumpstr(self, var, short=True, level=0):
        res = '%08x  %s' % (var._offset, '    ' * level) + '%s %s = %s' % (
            self.name, var.name, self.transform(var.value))
        return res


class Scope(Variable):
    def __init__(self, name, parser):
        Variable.__init__(self, None, name, value=dict(), upvalue=None)
        self._parser = parser

        # types with no params
        self._tmap = {
            'uint8': Basic(self, 'uint8', 'B', defval=None),
            'uint16': Basic(self, 'uint16', 'H', defval=None),
            'uint32': Basic(self, 'uint32', 'I', defval=None),
            'uint64': Basic(self, 'uint64', 'Q', defval=None),
            'int8': Basic(self, 'int8', 'b', defval=None),
            'int16': Basic(self, 'int16', 'h', defval=None),
            'int32': Basic(self, 'int32', 'i', defval=None),
            'int64': Basic(self, 'int64', 'q', defval=None),
            'uint16@': Basic(self, 'uint16@', '!H', defval=None),
            'uint32@': Basic(self, 'uint32@', '!I', defval=None),
            'uint64@': Basic(self, 'uint64@', '!Q', defval=None),
            'int16@': Basic(self, 'int16@', '!h', defval=None),
            'int32@': Basic(self, 'int32@', '!i', defval=None),
            'int64@': Basic(self, 'int64@', '!q', defval=None),
            'IPv4': IPv4(self),
            'MAC': MAC(self)
        }

        # types with params
        self._tpmap = {
            'string': String,
            'bits': Bits
        }

    def getVar(self, name):
        if name in self.value:
            return self.value[name]
        return None

    def getType(self, typeexpr, varscope):
        return self._parser._parseType(typeexpr, varscope, 'Scope.getType(%r, %s)' % (typeexpr, varscope.name))
        # try:
        #    return self._parser._parseType(typeexpr, varscope, '')
        # except:
        #    return None

    # def getValue(self, expr, varscope):
    #    return self._parser._parseRValue(expr, varscope, line='Scope.getValue(%r, %s)' % (expr, varscope.name))


    # def setValue(self, expr, varscope, value):
    #    var = self._parser._parseLValue(expr, varscope, autoalloc=True, line='Scope.getValue(%r, %s)' % (expr, varscope.name))
    #    var.value = value


    def defType(self, name, proto):
        newtype = Struct(self, name, proto)
        self._tmap[name] = newtype
        return newtype

    def defVar(self, name, typeexpr):
        vtype = self.getType(typeexpr, self)
        if vtype is None:
            return None

        var = vtype.allocVar(name)
        if var is None:
            return None

        var.upvalue = self
        self.value[name] = var
        return var


class State:
    def __init__(self, states, init):
        '''states: {state1, state2, ...}'''
        assert (not None in states and init in states)
        self._states = states
        self._state = init
        self.stack = list()

    def set(self, state):
        '''replace cur state with new state'''
        assert (state in self._states)
        self._state = state

    def get(self):
        assert (self._state != None)
        return self._state

    def push(self, state):
        '''push cur state and set to new state'''
        assert (self._state != None and state in self._states)
        self.stack.append(self._state)
        self._state = state

    def pop(self):
        '''pop state from stack and replace cur state'''
        assert (len(self.stack) > 0)
        self._state = self.stack.pop()


class Parser:
    def __init__(self):
        self._scope = Scope('GLOBAL', self)

    # def getType(self, name):
    #    return self._parseType(self, typeexpr, self._scope, 'Parser.getType(self, %r)' % (name,))


    def getVar(self, expr):
        '''return the Variable instance as a l-value, expr: x or xx.yy.zz'''
        return self._parseLValue(expr, self._scope, 'Parser.getLValue(self, %r)' % (expr,))

    def getValue(self, expr):
        '''return the value of Variable instance as r-value, expr: x or xx.yy.zz'''
        return self._parseRValue(expr, self._scope, 'Parser.getValue(self, %r)' % (expr))

    def setValue(self, expr, value):
        '''set l-value = value'''
        var = self._parseLValue(expr, self._scope, autoalloc=True,
                                line='Parser.setValue(self, %r, %r)' % (expr, value))
        var.value = value

    def error(self, e, msg):
        raise e(msg)

    def _parseLValue(self, expr, varscope, line=''):
        pass

    def _parseRValue(self, expr, varscope, line=''):
        pass

    def _parseType(self, typeexpr, varscope, line=''):
        pass


class EqParser(Parser):
    '''EqParser'''

    _reBetweenBrackets = re.compile(r'\((.*)\)')
    # _reBetweenSqrBrackets = re.compile(r'\[(<.*>)\]')
    _reBetweenSqrBrackets = re.compile(r'\[(.*)\]')
    # _reEval = re.compile(r'${(.*)}')
    _reParseLine = re.compile(r'".*"|[+=:#]|[\w_<>(){}\[\]$.\',@]+')
    _spSplitFuncParams = {'()': 2, '[]': 1, '""': 4, "''": 4}

    def __init__(self):
        Parser.__init__(self)
        self._state = State({'idle'}, 'idle')
        self._keywords = {}
        self._functions = {
            'add': ('RR', lambda self, x, y: x + y),
            'sub': ('RR', lambda self, x, y: x - y),
            'mul': ('RR', lambda self, x, y: x * y),
            'div': ('RR', lambda self, x, y: x / y),
            'mod': ('RR', lambda self, x, y: x % y),
            'print': ('R*', EqParser._func_print),
            'encode': ('L', lambda self, lvar: lvar.encode()),
            'decode': ('LR', lambda self, lvar, rdata: lvar.decode(rdata)),
            'calcsize': ('L', lambda self, lvar: lvar.calcsize()),
            'dump': ('L', lambda self, lvar: lvar.dump()),
            'total': ('', lambda self: self._oncesize),  # decode(data), total data size
            'offset': ('', lambda self: self._onceoffset),  # cur decode offset
            'import': ('R*', EqParser._func_import),
        }
        self._pylocals = None
        self._valcache = None
        self._oncesize = 0  # use for decoding once
        self._onceoffset = 0  # use for decoding once

    def definedTypes(self):
        return sorted(self._scope._tmap.keys() + self._scope._tpmap.keys())

    def definedFunctions(self):
        return ['%s(%s)' % (func, info[0]) for func, info in sorted(self._functions.items(), key=lambda x: x[0])]

    def execute(self, text, pylocals=None):
        '''if you want to use the var in python, you should let: pylocals=locals() or pylocals=globals()'''
        self._pylocals = pylocals
        self.refValCache()
        lines = text.splitlines()
        for line in lines:
            self._executeLine(line)
        self.unrefValCache()

    def _executeLine(self, line):
        '''execute line'''
        words = EqParser._reParseLine.findall(EqParser._wipeChars(line, ' \t\n\r', '\'\"'))
        if len(words) == 0 or words[0] == '#':
            return

        # print('D|' + repr(words))
        while len(words) > 0:
            word = words.pop(0)  # pop first word
            if word in self._keywords:  # keyword
                self.error(NameError, 'keyword(%r) is not implemented: %r' % (word, line))
                return
            else:  # not a keyword
                if len(words) > 0:  # normal statement
                    if words[0] == '=' and len(words) >= 3 and words[2] == ':':  # TYPE = field1:type1 ...
                        tname = word  # type
                        proto = list()
                        while len(words) >= 4:
                            words.pop(0)  # pop = or +
                            fname = words.pop(0)  # pop field name
                            words.pop(0)  # pop :
                            ftypeexpr = words.pop(0)  # pop field typeexpr
                            proto.append((fname, ftypeexpr))

                        if len(proto) == 0 or len(words) > 0:  # failed
                            self.error(SyntaxError, 'invalid syntax: %r' % (line,))
                            return

                        exprs = EqParser._reBetweenBrackets.findall(tname)
                        if len(exprs) == 1:  # func(...)
                            tname = tname[:tname.find('(', 1)]
                            if tname[0] == '(':  # failed
                                self.error(SyntaxError, 'invalid syntax: %r' % (line,))
                                return

                            val = self._parseRValue(exprs[0], self._scope, line)
                            if val != None:  # TYPE(expr)
                                tname += '(' + repr(val) + ')'
                            else:  # TYPE()
                                tname += '()'

                        self._scope.defType(tname, proto)
                        # print('D|define type(%s) succ' % (tname))

                    elif words[0] == ':':  # var:TYPE
                        vname = word  # var name
                        words.pop(0)  # pop :
                        if len(words) < 1:  # failed
                            self.error(SyntaxError, 'invalid syntax: %r' % (line,))
                            return

                        vtypeexpr = words.pop(0)  # pop type name
                        var = self._scope.defVar(vname, vtypeexpr)
                        if var is None:  # failed
                            self.error(NameError,
                                       '%s:%s, type(%r) is not defined or cannot be parsed or invalid: %r' % (
                                       vname, vtypeexpr, vtypeexpr, line))
                            return

                        if len(words) > 0:  # var:TYPE = r-value
                            if len(words) != 2 or words[0] != '=':  # failed
                                self.error(SyntaxError, 'invalid syntax: %r' % (line,))
                                return

                            words.pop(0)  # pop =
                            rexpr = words.pop(0)  # pop r-value
                            var.value = self._parseRValue(rexpr, self._scope, line=line)
                            # print('D|define var(%s:%s) succ' % (vname, var.type.name))

                    elif words[0] == '=':  # var = value
                        # hdr.len = 5
                        # hdr = pkg.hdr
                        if len(words) != 2:  # failed
                            self.error(SyntaxError, 'invalid syntax: %r' % (line,))
                            return

                        lexpr = word  # l-value
                        words.pop(0)  # pop =
                        rexpr = words.pop(0)  # pop r-value

                        fvar = self._parseLValue(lexpr, self._scope, autoalloc=True, line=line)
                        fvar.value = self._parseRValue(rexpr, self._scope, line=line)
                    else:  # unsupported syntax
                        self.error(SyntaxError, 'unsupported syntax: %r' % (line,))
                        return

                else:  # var / func(33)
                    expr = word  # expr
                    plists = EqParser._reBetweenBrackets.findall(expr)
                    if len(plists) == 1:  # func(...)
                        fname = expr[:expr.find('(', 1)]
                        if fname[0] == '(':  # failed
                            self.error(SyntaxError, 'invalid syntax: %r' % (line,))
                            return

                        self._parseFunc(fname, plists[0], self._scope, line=line)
                    else:  # var
                        self.error(SyntaxError, 'unsupported syntax(lonely): %r' % (line,))
                        return

    def _autoAlloc(self, upvar, name, line=''):
        if upvar.isStruct():
            vtype = self._parseType(upvar.type.ftypeexpr[name], upvar, line=line)
        elif upvar.isArray():
            vtype = upvar.type.itype
        else:
            vtype = None
            self.error(ValueError, 'invalied upvalue(%r): %r' % (upvar.name, line))
            return None
        var = vtype.allocVar(name)
        var.upvalue = upvar
        upvar.value[name] = var
        return var

    def refValCache(self):
        if self._valcache is None:
            self._valcache = {'ref': 1}
            # print('D|valcache|init')
        else:
            self._valcache['ref'] += 1
        return self._valcache

    def unrefValCache(self):
        assert (self._valcache != None)
        self._valcache['ref'] -= 1
        if self._valcache['ref'] == 0:
            self._valcache = None
            # print('D|valcache|clear')

    def _setCacheVal(self, expr, varscope, val):
        if self._valcache is None:
            return val
        key = str(id(varscope)) + '.' + expr
        self._valcache[key] = val
        return val

    def _getCacheVal(self, expr, varscope):
        if self._valcache is None:
            return None

        if expr.rfind(')') >= 0:
            return None

        key = str(id(varscope)) + '.' + expr
        if not key in self._valcache:
            return None
        # print('C|expr: %s.%s = %s' % (varscope.name, expr, self._valcache[key]))
        return self._valcache[key]

    def _parseLValue(self, expr, varscope, autoalloc=False, line=''):
        flist = expr.split('.')
        if len(flist) == 0 or flist[0] == '' or flist[-1] == '':
            return None

        svar = varscope
        while svar != None:
            # check l1.l2[r1.r2].l3 in varscope
            check = True
            lvar = svar
            lname = None
            lupvar = None
            for name in flist:
                if not lvar.isStruct():
                    check = False
                    break

                indexexprs = EqParser._reBetweenSqrBrackets.findall(name)
                if len(indexexprs) == 1:  # like .l2[r1.r2]
                    name = name[:name.find('[', 1)]
                    if name[0] == '[':  # failed
                        self.error(SyntaxError, 'invalid syntax: %r' % (line,))
                        return
                if not name in lvar.value:
                    check = False
                    break

                lname = name
                lupvar = lvar
                lvar = lvar.value[name]

                if lvar is None and autoalloc:
                    lvar = self._autoAlloc(lupvar, lname, line=line)

                if len(indexexprs) == 1:  # like .l2[r1.r2]
                    index = self._parseRValue(indexexprs[0], varscope, line=line)
                    if index >= len(lvar.value):
                        check = False
                        break

                    lname = index
                    lupvar = lvar
                    lvar = lvar.value[index]

                    if lvar is None and autoalloc:
                        lvar = self._autoAlloc(lupvar, lname, line=line)

            if check:
                return lvar

            svar = svar.upvalue

        self.error(NameError, 'l-value(%r) cannot be parsed: %r' % (expr, line))
        return None

    def _parseRValue(self, expr, varscope, line=''):
        cacheval = self._getCacheVal(expr, varscope)
        if cacheval:
            # print('D|valcache|hit|%s in %s' % (expr, varscope.name))
            return cacheval

        if expr == '':
            # self.error(ValueError, 'nothing to parse: %r' % (line,))
            return None

        # 0 / 128 / 0667 / 0o667 / 0x5dfe / 0b1101 / 'as\ndf' / "ABd\x3fdi\t"
        val = self.toValue(expr)
        if val != None:
            return self._setCacheVal(expr, varscope, val)

        # ${x + 2}
        if expr[:2] == '${' and expr[-1] == '}':
            try:
                return eval(expr[2:-1], globals(), self._pylocals)
            except Exception as msg:
                self.error(ValueError, 'eval(%r) failed, %s: %r' % (expr[2:-1], msg, line))
                return None

        # func(...)
        plists = EqParser._reBetweenBrackets.findall(expr)
        if len(plists) == 1:  # = func(...)
            fname = expr[:expr.find('(', 1)]
            if fname[0] == '(':  # failed
                self.error(SyntaxError, 'invalid syntax: %r' % (line))
                return None
            return self._setCacheVal(expr, varscope, self._parseFunc(fname, plists[0], varscope, line=line))

        # datalen / hdr2.data.len
        lvar = self._parseLValue(expr, varscope, autoalloc=True, line=line)
        if lvar != None:
            return self._setCacheVal(expr, varscope, lvar.value)  # return r-value

        self.error(ValueError, 'r-value(%r) cannot be parsed: %r' % (expr, line))
        return None

    def _parseFunc(self, fname, paramexprs, varscope, line=''):
        if not fname in self._functions:  # function not defined
            self.error(NameError, 'function(%r) is not defined: %r' % (fname, line))
            return None

        fparamlr, func = self._functions[fname]
        paramlist = EqParser._splitWithPairs(paramexprs, ',', EqParser._spSplitFuncParams)
        # print('D|_parseFunc(%r)|paramList|' % (fname), paramexprs, '->', paramlist)
        vals = list()
        if paramexprs != '':
            if fparamlr[-1] != '*':  # use MIN(paramlist.size, fparamlr.size)
                paramlist = paramlist[:len(fparamlr)]

            lrlock = None
            for index, paramexpr in enumerate(paramlist):
                lr = None

                if lrlock is None:
                    lr = fparamlr[index]
                    if lr == '*':
                        lrlock = fparamlr[index - 1]
                        lr = lrlock
                else:
                    lr = lrlock

                val = None
                if lr == 'L':  # function accept a l-value
                    val = self._parseLValue(paramexpr, varscope, line=line)
                elif lr == 'R':  # function accept a r-value
                    val = self._parseRValue(paramexpr, varscope, line=line)
                else:  # unsupported function proto
                    self.error(SyntaxError, 'unsupported function proto(%r): %r' % (fparamlr, line))
                    return None

                if val is None:  # failed
                    self.error(ValueError, 'invalid value: %r' % (line,))
                    return None
                vals.append(val)
        # print('D|_parseFunc(%r)|succ %r' % (fname, res))
        res = func(self, *vals)
        return res

    def _parseType(self, typeexpr, varscope, line=''):
        '''for example, typeexpr: BODY(hdr.result), varscope: pkg
        PKG = hdr:HDR + body:BODY(hdr.result)
        hdr is in pkg, so the varscope is pkg'''
        # vtype[expr] / vtype(expr2)[expr1]
        exprs = EqParser._reBetweenSqrBrackets.findall(typeexpr)
        if len(exprs) == 1:
            vtype = typeexpr[:typeexpr.find('[', 1)]
            if vtype[0] == '[':
                self.error(SyntaxError, 'invalid syntax: %r' % (line,))
                return None

            vtype = self._parseType(vtype, varscope, line=line)

            # what in [], <3312> / 3312
            usedatasize = exprs[0][0] == '<' and exprs[0][-1] == '>'
            if usedatasize:
                val = self._parseRValue(exprs[0][1:-1], varscope, line=line)
            else:
                val = self._parseRValue(exprs[0], varscope, line=line)
            if isinstance(val, int):
                return Array(self._scope, vtype, val, usedatasize)
            else:
                self.error(ValueError, 'value(%r) is not an integer: %rr' % (exprs[0], line))
                return None

        # vtype(expr)
        exprs = EqParser._reBetweenBrackets.findall(typeexpr)
        if len(exprs) == 1:
            vtype = typeexpr[:typeexpr.find('(', 1)]
            if vtype[0] == '(':
                self.error(SyntaxError, 'invalid syntax: %r' % (line,))
                return None

            if vtype in self._scope._tpmap:
                # paramexprs = exprs[0].split(',')  # !!!! '(x, y), z' -> '(x' + 'y)' + 'z'
                paramexprs = EqParser._splitWithPairs(exprs[0], ',', EqParser._spSplitFuncParams)
                vals = [self._parseRValue(paramexpr, varscope, line=line) for paramexpr in paramexprs]

                if vtype == 'string':
                    if not isinstance(vals[0], int) and exprs[0] != '':
                        self.error(ValueError,
                                   '%s, size value(%s=%r) is not an integer: %r' % (
                                   typeexpr, paramexprs[0], vals[0], line))
                        return None

                    if len(vals) >= 2 and vals[1] != None and not isinstance(vals[1], str):
                        self.error(ValueError,
                                   'codec value(%r) is not a string: %r' % (paramexprs[1], line))
                        return None

                    return self._scope._tpmap[vtype](self._scope, vals[0],
                                                     encoding=(len(vals) >= 2 and vals[1]) or None)  # return String obj
                elif vtype == 'bits':
                    if not isinstance(vals[0], int) and exprs[0] != '':
                        self.error(ValueError,
                                   '%s, size value(%s=%r) is not an integer: %r' % (
                                   typeexpr, paramexprs[0], vals[0], line))
                        return None
                    return self._scope._tpmap[vtype](self._scope, vals[0])  # return Bits obj

            val = self._parseRValue(exprs[0], varscope, line=line)
            if isinstance(val, dict) or isinstance(val, list):  # struct value, or array value
                self.error(ValueError, 'invalid value(%s=%r): %r' % (exprs[0], val, line))
                return None

            if val is None:
                self.error(ValueError, 'value(%s) cannot be parsed: %r' % (exprs[0], line))
                return None

            typeexpr = vtype + '(' + repr(val) + ')'

            if typeexpr in self._scope._tmap:
                return self._scope._tmap[typeexpr]
            else:
                typeexpr = vtype + '()'

        if typeexpr in self._scope._tmap:
            return self._scope._tmap[typeexpr]

        # print('ERR | typeexpr(%s)' % (typeexpr))
        self.error(NameError, 'type(%r) is not defined or cannot be parsed: %r' % (typeexpr, line))
        return None

    def toValue(self, s):
        # 0 / 128 / 0667 / 0o667 / 0x5dfe / 0b1101
        base = 10
        prefix = s[:2]
        if s.isdigit():
            if s[0] == '0':
                base = 8
            else:
                base = 10
        elif prefix == '0x':
            base = 16
        elif prefix == '0b':
            base = 2
        elif prefix == '0o':
            base = 8
        try:
            return int(s, base)
        except:
            # 'adff' / "fapsdf"
            if (s[0] == '\'' or s[0] == '\"') and s[0] == s[-1]:
                return eval(s, globals(), self._pylocals)  # 'abc' / "abc" -> 'abc'

        return None

    @staticmethod
    def _wipeChars(s, chars, bchars):
        lst = list()
        sep = None
        for c in s:
            if sep is None and c in bchars:  # ' or "
                sep = c
                lst.append(c)
                continue

            if sep != None or not c in chars:
                lst.append(c)

            if c == sep:
                sep = None

        return ''.join(lst)

    @staticmethod
    def _splitWithPairs(s, seps, pairDict):
        '''s: string
        seps: ',' or ',;'
        pairDict: {'()': 2, '[]': 1, '""': 4, "''": 4}

        '''
        # '(x, y), (z, "(dd", aa)'
        push = {pair[0]: (pair[1], level) for pair, level in pairDict.items()}
        pop = {pair[1]: pair[0] for pair in pairDict.keys()}

        res = list()
        stack = list()
        start = 0
        end = 0
        for c in s:
            empty = (len(stack) == 0)
            if empty and (c in seps):
                res.append(s[start: end])
                start = end + 1
            elif (c in pop) and (not empty) and (c == push[stack[-1]][0]):
                stack.pop()
            elif (c in push) and (empty or (push[c][1] >= push[stack[-1]][1])):
                stack.append(c)
            end += 1

        res.append(s[start: end])
        return res

    def _func_print(self, *rvals):
        for rval in rvals:
            print(rval, end=' ')
        print()

    def _func_import(self, *rfiles):
        for rfile in rfiles:
            with open(rfile, 'r') as fp:
                self.execute(fp.read(), pylocals=self._pylocals)


def main():
    p = EqParser()
    scope = p._scope

    text = r'''
    PNG_CHUNK = Length:uint32@ + Type:string(4) + Data:PNG_DATA(Type) + CRC:string(4, 'hex')
    PNG_DATA('IHDR') = Width:uint32@ + Height:uint32@ + BitDepth:uint8 + ColorType:uint8 + CompressionMethod:uint8 + FilterMethod:uint8 + InterlaceMethod:uint8
    PNG_DATA() = data:string(Length, 'base64')
    PNG = sig:string(8, 'base64') + chunks:PNG_CHUNK[<sub(total(), calcsize(sig))>]

    png:PNG
    '''
    p.execute(text)

    with open('test.png', 'rb') as fp:
        data = fp.read()

    png = p.getVar('png')
    p.refValCache()
    png.decode(data)
    print(png.dump())
    p.unrefValCache()
    exit(0)

    import json
    d = png.dump(mode='dict', transform=True)
    s = json.dumps(d)
    # print(s)

    import socket
    import sys
    import dpkt

    text = r'''
    import('eth.proto')
    eth:ETH
    '''

    def getData():
        useSock = 'AF_PACKET' in dir(socket)
        data = None
        if useSock:
            with open('eth.cap', 'wb') as fp:
                sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3))
                ifname = len(sys.argv) > 1 and sys.argv[1]
                if ifname:
                    sock.bind((ifname, 0))
                try:
                    while True:
                        data, addr = sock.recvfrom(0xFFFF)
                        # proto, = struct.unpack('!H', data[12:14])
                        # fp.write(struct.pack('I', len(data)))
                        # fp.write(data)
                        yield data
                except KeyboardInterrupt as msg:
                    print('KeyboardInterrupt', msg)

            sock.close()
        else:
            with open('eth.cap', 'rb') as fp:
                try:
                    while True:
                        data = fp.read(4)
                        if data == '':
                            data = None
                            break
                        data, = fp.read(struct.unpack('I', data))
                        if data == '':
                            data = None
                            break
                        yield data
                except KeyboardInterrupt as msg:
                    print('KeyboardInterrupt', msg)

        yield data

    def xcall(func, *l, **d):
        try:
            return func(*l, **d)
        except Exception as msg:
            print('Exception:', msg)
            return None

    p.execute(text, pylocals=locals())
    eth = p.getVar('eth')

    with open('rec.txt', 'w') as fp:
        devinfos = dict()
        for data in getData():
            if data is None:
                break

            # xcall(eth.decode, data)
            eth.decode(data)

            proto = p.getValue('eth.ethHdr.type')
            # if proto != dpkt.ethernet.ETH_TYPE_IP:
            # print(hex(proto))
            if proto in (dpkt.ethernet.ETH_TYPE_ARP, dpkt.ethernet.ETH_TYPE_IP):
                print(eth.dump())
                if proto == dpkt.ethernet.ETH_TYPE_ARP:
                    srcIp = p.getValue('eth.ethBody.arp.srcIp')
                    # print(eth.dump(), len(data))
                    if not srcIp in devinfos:
                        srcMac = p.getValue('eth.ethBody.arp.srcMac')
                        devinfos[srcIp] = {'mac': srcMac}
                        # print(eth.dump())
                        print('new %s %s' % (srcMac, srcIp))
                elif proto == dpkt.ethernet.ETH_TYPE_IP:
                    srcIp = p.getValue('eth.ethBody.ip.ipHdr.ipFixed.srcIp')
                    ipProto = p.getValue('eth.ethBody.ip.ipHdr.ipFixed.proto')
                    if not srcIp in (
                            '45.77.23.212', '192.168.50.179', '192.168.50.238', '127.0.0.1', '10.8.73.67', '10.8.73.92',
                            '192.168.1.101'):
                        print(ipProto, srcIp)
                        if ipProto == dpkt.ip.IP_PROTO_TCP:
                            tcpData = p.getValue('eth.ethBody.ip.ipBody.tcp.tcpBody.data')
                            print(tcpData)
                            fp.write(tcpData + '\n\n')
                            fp.flush()


if __name__ == '__main__':
    main()
