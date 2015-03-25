#!/usr/bin/env python
#
#  proto - Encode or decode data by proto expression.
#  Created by 5w0rd 2015.
#  Email: lightning_0721@163.com
#
#

import struct
import re


class Variable:
    def __init__(self, vtype, name, value = None, upvalue = None):
        self.type = vtype
        self.name = name
        self.value = value
        self.upvalue = upvalue


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
        return self.type.encode(self)


    def decode(self, data):
        return self.type.decode(self, data)


    def calcsize(self):
        return self.type.calcsize(self)


    def dump(self, short = True):
        return self.type.dump(self, short = short)


    def todict(self, transform = False, _d = None):
        '''transform: transform value
        _d: scope, donot use it'''
        val = None
        if self.isStruct():  # struct var
            val = dict()
            for name in self.type.fseq:
                fvar = self.value[name]
                if not fvar == None:
                    fvar.todict(transform = transform, _d = val)
                else:
                    val = None
        elif self.isArray():  # array var
            val = list()
            for ivar in self.value:
                if not ivar == None:
                    ivar.todict(transform = transform, _d = val)
                else:
                    val = None
        else:  # base var
            val = self.value
            if val != None and transform:
                val = self.type.transform(val)

        if _d == None:
            _d = dict()

        if isinstance(_d, dict):
            _d[self.name] = val
        elif isinstance(_d, list):
            _d.append(val)
        
        return _d


class Type:
    def __init__(self, scope, name, defval = None):
        self.scope = scope
        self.name = name
        self.defval = defval
        #print 'D|newType(%s)' % (name)


    def allocVar(self, name):
        if isinstance(name, str):
            fakename = name.replace('_', 'a')
            if not fakename[0].isalpha() or not fakename.isalnum():
                return None
        elif isinstance(name, int):  # elements of array
            name = '[' + str(name) + ']'
        else:  # failed
            return None

        #print 'D|alloc var(%s:%s)' % (name, self.name)
        return Variable(self, name, value = self.defval)


    def encode(self, var, level = 0):
        pass


    def decode(self, var, data, level = 0):
        pass


    def calcsize(self, var):
        pass
    

    def transform(self, val):
        return val


    def dump(self, var, short = True, level = 0):
        res = '    ' * level + '%s %s = %s' % (self.name, var.name, repr(self.transform(var.value)))
        return res


class Basic(Type):
    def __init__(self, scope, name, packfmt, defval = None):
        Type.__init__(self, scope, name, defval = defval)
        self.packfmt = packfmt


    def encode(self, var, level = 0):
        #print 'E| ' + '    ' * level + '%s %s = %s' % (self.name, var.name, repr(self.transform(var.value)))
        return struct.pack(self.packfmt, var.value)


    def decode(self, var, data, level = 0):
        var.value = struct.unpack_from(self.packfmt, data)[0]
        #print 'D| ' + '    ' * level + '%s %s = %s' % (self.name, var.name, repr(self.transform(var.value)))
        return self.calcsize(var)


    def calcsize(self, var):
        return struct.calcsize(self.packfmt)


class String(Type):
    def __init__(self, scope, size, encoding = None, defval = ''):
        name = 'string('
        packfmt = ''
        if size != None:
            name += str(size)
        if encoding != None:
            name += ',' + repr(encoding)
        name += ')'
        Type.__init__(self, scope, name, defval = defval)
        self.size = size
        self.encoding = encoding


    def encode(self, var, level = 0):
        packfmt = self.__packfmt(var)
        #print 'E| ' + '    ' * level + '%s %s = %s' % (self.name, var.name, repr(self.transform(var.value[:int(packfmt[:-1])])))
        return struct.pack(packfmt, var.value)


    def decode(self, var, data, level = 0):
        packfmt = self.__packfmt(var)
        var.value = struct.unpack_from(packfmt, data)[0]
        #print 'D| ' + '    ' * level + '%s %s = %s' % (self.name, var.name, repr(self.transform(var.value[:int(packfmt[:-1])])))
        return self.calcsize(var)


    def calcsize(self, var):
        return struct.calcsize(self.__packfmt(var))


    def __packfmt(self, var):
        if self.size == None:
            return str(len(var.value)) + 's'
        return str(self.size) + 's'

    
    def transform(self, val):
        if self.encoding != None:
            return val.encode(self.encoding)
        return val


    def dump(self, var, short = True, level = 0):
        packfmt = self.__packfmt(var)
        val = self.transform(var.value[:int(packfmt[:-1])])
        if short and len(val) > 24:
            val = val[:20] + '...'
        res = '    ' * level + '%s %s = %s' % (self.name, var.name, repr(val))
        return res


class Bits(Type):
    class BitsSize:
        def __init__(self, wide):
            self.wide = wide


    def __init__(self, scope, wide, defval = 0):
        Type.__init__(self, scope, 'bits(' + str(wide) + ')', defval = defval)
        self.wide = wide


    def encode(self, var, level = 0):
        #print 'E| ' + '    ' * level + '%s %s = %s' % (self.name, var.name, repr(self.transform(var.value)))
        return Bits.BitsSize(self.wide)


    def decode(self, var, data, level = 0):
        #print 'D| ' + '    ' * level + '%s %s = %s' % (self.name, var.name, repr(self.transform(var.value)))
        return Bits.BitsSize(self.wide)


    def calcsize(self, var):
        return Bits.BitsSize(self.wide)


    @staticmethod
    def encodebits(bitpack):
        bytelist = list()
        bytenum = Bits.calcsizebits(len(bitpack))
        bitpack += '0' * (bytenum * 8)
        return struct.pack(str(bytenum) + 'B', *[int(bitpack[i * 8:i * 8 + 8], 2) for i in range(bytenum)])


    @staticmethod
    def decodebits(bitpack, data):
        wide = 0
        for var in bitpack:
            wide += var.type.wide
        bytenum = Bits.calcsizebits(wide)
        data = data[:bytenum]
        binpack = [bin(ord(b))[2:] for b in data]
        binpack = ''.join(['0' * (8 - len(b)) + b for b in binpack])
        pos = 0
        for var in bitpack:
            wide = var.type.wide
            var.value = int(binpack[pos:pos + wide], 2)
            pos += wide
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
        if var == None:
            return None

        fvmap = dict()
        for fname in self.fseq:
            fvmap[fname] = None
        
        var.value = fvmap
        return var


    def encode(self, var, level = 0):
        #print 'E| ' + '    ' * level + '%s %s = {' % (self.name, var.name)
        data = str()
        bitpack = str()
        bitflag = False
        for fname in self.fseq:
            ftype = self.scope.getType(self.ftypeexpr[fname], var)
            fvar = var.value[fname]
            if fvar == None:  # try to use defval
                fvar = ftype.allocVar(fname)
            res = ftype.encode(fvar, level = level + 1)
            if res == None:  # failed
                #print 'ERR | encode:' + fname
                return None

            if isinstance(res, Bits.BitsSize):  # bits
                if not bitflag:  # begin pack bits
                    bitflag = True
                    bitpack = str()
                #val = (~(0xffffffff << fvar.type.wide)) & 0xffffffff & fvar.value  # ignore out of range bits
                wide = res.wide
                s = bin(fvar.value)[2:][-wide:][:wide]
                s = '0' * (wide - len(s)) + s
                bitpack += s
            else:
                if bitflag:  # end pack bits
                    bitflag = False
                    data += Bits.encodebits(bitpack)
                data += res
        if bitflag:  # end pack bits
            bitflag = False
            data += Bits.encodebits(bitpack)
        #print 'E| ' + '    ' * level + '}'
        return data


    def decode(self, var, data, level = 0):
        #print 'D| ' + '    ' * level + '%s %s = {' % (self.name, var.name)
        pos = 0
        bitpack = list()
        bitflag = False
        for fname in self.fseq:
            #print '###', self.ftypeexpr[fname]
            ftype = self.scope.getType(self.ftypeexpr[fname], var)
            #print '@@', var.name, var.value, fname, ftype.name
            fvar = ftype.allocVar(fname)
            fvar.upvalue = var
            var.value[fname] = fvar
            res = ftype.decode(fvar, data[pos:], level = level + 1)
            if isinstance(res, Bits.BitsSize):  # bits
                if not bitflag:  # begin pack bits var
                    bitflag = True
                    bitpack = list()
                bitpack.append(fvar)
            else:
                if bitflag:  # end pack bits var
                    bitflag = False
                    pos += Bits.decodebits(bitpack, data[pos:])
                pos += res
        if bitflag:  # end pack bits
            bitflag = False
            pos += Bits.decodebits(bitpack, data[pos:])
        #print 'D| ' + '    ' * level + '}'
        return pos


    def calcsize(self, var):
        size = 0
        bitpack = 0
        bitflag = False
        for fname in self.fseq:
            ftype = self.scope.getType(self.ftypeexpr[fname], var)
            fvar = var.value[fname]
            if fvar == None:
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


    def dump(self, var, short = True, level = 0):
        res = '    ' * level + '%s %s = {' % (self.name, var.name)
        size = len(res)
        for fname in self.fseq:
            ftype = self.scope.getType(self.ftypeexpr[fname], var)
            fvar = var.value[fname]
            if fvar != None:
                res += '\n' + ftype.dump(fvar, short = short, level = level + 1)
        if len(res) == size:
            res += '}'
        else:
            res += '\n' + '    ' * level + '}'
        return res


class Array(Type):
    def __init__(self, scope, itype, size):
        '''typeexpr: BODY(hdr.result)'''
        Type.__init__(self, scope, '%s[%d]' % (itype.name, size))
        self.itype = itype
        self.size = size


    def allocVar(self, name):
        var = Type.allocVar(self, name)
        if var == None:
            return None

        var.value = [None] * self.size
        return var


    def encode(self, var, level = 0):
        #print 'E| ' + '    ' * level + '%s %s = [' % (self.name, var.name)
        data = str()
        for index in range(self.size):
            ivar = var.value[index]
            if ivar == None:  # try to use defval
                ivar = self.itype.allocVar(index)
            res = self.itype.encode(ivar, level = level + 1)
            if res == None:
                #print 'ERR | encode:' + fname
                return None
            else:
                data += res
        #print 'E| ' + '    ' * level + ']'
        return data


    def decode(self, var, data, level = 0):
        #print 'D| ' + '    ' * level + '%s %s = [' % (self.name, var.name)
        pos = 0
        for index in range(self.size):
            ivar = self.itype.allocVar(index)
            ivar.upvalue = var
            var.value[index] = ivar
            pos += self.itype.decode(ivar, data[pos:], level = level + 1)
        #print 'D| ' + '    ' * level + ']'
        return pos


    def calcsize(self, var):
        total = 0
        for index in range(self.size):
            ivar = var.value[index]
            total += self.itype.calcsize(ivar)
        return total
    
    
    def dump(self, var, short = True, level = 0):
        res = '    ' * level + '%s %s = [' % (self.name, var.name)
        size = len(res)
        count = 0
        for index in range(self.size):
            ivar = var.value[index]
            if ivar != None:
                if short:
                    count += 1
                    if count > 5:
                        res += '\n' + '    ' * (level + 1) + '...'
                        break
                res += '\n' + self.itype.dump(ivar, short = short, level = level + 1)
        if len(res) == size:
            res += ']'
        else:
            res += '\n' + '    ' * level + ']'
        return res


class IPv4(Type):
    def __init__(self, scope, defval = '0.0.0.0'):
        Type.__init__(self, scope, 'IPv4', defval = defval)


    def encode(self, var, level = 0):
        #print 'E| ' + '    ' * level + '%s %s = %s' % (self.name, var.name, self.transform(var.value))
        return struct.pack('4B', *[int(b) for b in var.value.split('.')])


    def decode(self, var, data, level = 0):
        var.value = '.'.join([str(b) for b in struct.unpack_from('4B', data)])
        #print 'D| ' + '    ' * level + '%s %s = %s' % (self.name, var.name, self.transform(var.value))
        return 4


    def calcsize(self, var):
        return 4


    def dump(self, var, short = True, level = 0):
        res = '    ' * level + '%s %s = %s' % (self.name, var.name, self.transform(var.value))
        return res


class MAC(Type):
    def __init__(self, scope, defval = '00:00:00:00:00:00'):
        Type.__init__(self, scope, 'MAC', defval = defval)


    def encode(self, var, level = 0):
        #print 'E| ' + '    ' * level + '%s %s = %s' % (self.name, var.name, self.transform(var.value))
        return struct.pack('6B', *[int(b, 16) for b in var.value.split(':')])


    def decode(self, var, data, level = 0):
        var.value = ':'.join([b.encode('hex') for b in data[:6]])
        #print 'D| ' + '    ' * level + '%s %s = %s' % (self.name, var.name, self.transform(var.value))
        return 6


    def calcsize(self, var):
        return 6


    def dump(self, var, short = True, level = 0):
        res = '    ' * level + '%s %s = %s' % (self.name, var.name, self.transform(var.value))
        return res
        
    
class Scope(Variable):
    def __init__(self, name, parser):
        Variable.__init__(self, None, name, value = dict(), upvalue = None)
        self.parser = parser
        self.tmap = {
            'uint8': Basic(self, 'uint8', 'B', defval = 0),
            'uint16': Basic(self, 'uint16', 'H', defval = 0),
            'uint32': Basic(self, 'uint32', 'I', defval = 0),
            'uint64': Basic(self, 'uint64', 'Q', defval = 0L),
            'int8': Basic(self, 'int8', 'b', defval = 0),
            'int16': Basic(self, 'int16', 'h', defval = 0),
            'int32': Basic(self, 'int32', 'i', defval = 0),
            'int64': Basic(self, 'int64', 'q', defval = 0L),
            'uint16@': Basic(self, 'uint16@', '>H', defval = 0),
            'uint32@': Basic(self, 'uint32@', '>I', defval = 0),
            'uint64@': Basic(self, 'uint64@', '>Q', defval = 0L),
            'int16@': Basic(self, 'int16@', '>h', defval = 0),
            'int32@': Basic(self, 'int32@', '>i', defval = 0),
            'int64@': Basic(self, 'int64@', '>q', defval = 0L),
            'IPv4': IPv4(self),
            'MAC': MAC(self)
        }


    def getVar(self, name):
        if name in self.value:
            return self.value[name]
        return None


    def getType(self, typeexpr, varscope):
        return self.parser.parseType(typeexpr, varscope, 'Scope.getType(%s, %s)' % (repr(typeexpr), varscope.name))
        #try:
        #    return self.parser.parseType(typeexpr, varscope, '')
        #except:
        #    return None


    def getValue(self, expr, varscope):
        return self.parser.parseRValue(expr, varscope, 'Scope.getValue(%s, %s)' % (repr(expr), varscope.name))


    def defType(self, name, proto):
        newtype = Struct(self, name, proto)
        self.tmap[name] = newtype
        return newtype


    def defVar(self, name, typeexpr):
        vtype = self.getType(typeexpr, self)
        if vtype == None:
            return None

        var = vtype.allocVar(name)
        if var == None:
            return None

        var.upvalue = self
        self.value[name] = var
        return var


class State:
    def __init__(self, states, init):
        '''states: {state1, state2, ...}'''
        assert(not None in states and init in states)
        self.states = states
        self.state = init
        self.stack = list()


    def set(self, state):
        '''replace cur state with new state'''
        assert(state in self.states)
        self.state = state


    def get(self):
        assert(self.state != None)
        return self.state


    def push(self, state):
        '''push cur state and set to new state'''
        assert(self.state != None and state in self.states)
        self.stack.append(self.state)
        self.state = state


    def pop(self):
        '''pop state from stack and replace cur state'''
        assert(len(self.stack) > 0)
        self.state = self.stack.pop()


class Parser:
    def __init__(self):
        self.scope = Scope('GLOBAL', self)


    #def getType(self, name):
    #    return self.parseType(self, typeexpr, self.scope, 'Parser.getType(self, %s)' % (repr(name)))


    def getVar(self, expr):
        '''return the Variable instance as a l-value, expr: x or xx.yy.zz'''
        return self.parseLValue(expr, self.scope, 'Parser.getLValue(self, %s)' % (repr(expr)))


    def getValue(self, expr):
        '''return the value of Variable instance as r-value, expr: x or xx.yy.zz'''
        return self.parseRValue(expr, self.scope, 'Parser.getRValue(self, %s)' % (repr(expr)))


    def error(self, e, msg):
        raise e, msg


    def parseLValue(self, expr, varscope, line = ''):
        pass


    def parseRValue(self, expr, varscope, line = ''):
        pass


    def parseType(self, typeexpr, varscope, line = ''):
        pass


class EqParser(Parser):
    '''EqParser'''
    
    reBetweenBrackets = re.compile(r'\((.*)\)')
    reBetweenSqrBrackets = re.compile(r'\[(.*)\]')
    reEval = re.compile(r'${(.*)}')
    reParseLine = re.compile(r'".*"|[+=:#]|[\w_(){}\[\]$.\',@]+')
    spSplitFuncParams = {'()': 2, '[]': 1, '""': 4, "''": 4}


    def __init__(self):
        Parser.__init__(self)
        self.state = State({'idle'}, 'idle')
        self.keywords = {}
        self.funcions = {
            'add': ('RR', lambda x, y: x + y),
            'sub': ('RR', lambda x, y: x - y),
            'mul': ('RR', lambda x, y: x * y),
            'div': ('RR', lambda x, y: x / y),
            'mod': ('RR', lambda x, y: x % y),
            'print': ('R*', EqParser.func_print),
            'encode': ('L', lambda lvar: lvar.encode()),
            'decode': ('LR', lambda lvar, rdata: lvar.decode(rdata)),
            'calcsize': ('L', lambda lvar: lvar.calcsize()),
            'dump': ('L', lambda lvar: lvar.dump())
        }
        self.pylocals = None


    def execText(self, text, pylocals = None):
        lines = text.splitlines()
        for line in lines:
            self.execLine(line, pylocals = pylocals)


    def execLine(self, line, pylocals = None):
        self.pylocals = pylocals

        words = EqParser.reParseLine.findall(EqParser.wipeChars(line, ' \t\n\r', '\'\"'))
        if len(words) == 0 or words[0] == '#':
            return

        #print 'D|' + repr(words)
        while len(words) > 0:
            word = words.pop(0)  # pop first word
            if word in self.keywords:  # keyword
                self.error(NameError, 'keyword(%s) is not implemented: ' % (repr(word), line))
                return
            else:  # not a keyword
                if len(words) > 0: # normal statement
                    if words[0] == '=' and len(words) >= 3 and words[2] == ':':  # TYPE = field1:type1 ...
                        tname = word  # type
                        proto = list()
                        while len(words) >= 4:
                            words.pop(0)  # pop = or +
                            fname = words.pop(0)  # pop field name
                            words.pop(0)  #pop :
                            ftypeexpr = words.pop(0)  # pop field typeexpr
                            proto.append((fname, ftypeexpr))
                        
                        if len(proto) == 0 or len(words) > 0:  # failed
                            self.error(SyntaxError, 'invalid syntax: %s' % (repr(line)))
                            return

                        exprs = EqParser.reBetweenBrackets.findall(tname)
                        if len(exprs) == 1:  # func(...)
                            tname = tname[:tname.find('(', 1)]
                            if tname[0] == '(':  # failed
                                self.error(SyntaxError, 'invalid syntax: %s' % (repr(line)))
                                return

                            val = self.parseRValue(exprs[0], self.scope, line)
                            if val != None:  # TYPE(expr)
                                tname += '(' + repr(val) + ')'
                            else:  # TYPE()
                                tname += '()'

                        self.scope.defType(tname, proto)
                        #print 'D|define type(%s) succ' % (tname)

                    elif words[0] == ':':  # var:TYPE
                        vname = word  # var name
                        words.pop(0)  # pop :
                        if len(words) < 1:  # failed
                            self.error(SyntaxError, 'invalid syntax: %s' % (repr(line)))
                            return

                        vtypeexpr = words.pop(0)  # pop type name
                        var = self.scope.defVar(vname, vtypeexpr)
                        if var == None:  # failed
                            self.error(NameError, 'type(%s) is not defined or cannot be parsed: %s' % (repr(vtypeexpr), repr(line)))
                            return

                        if len(words) > 0:  # var:TYPE = r-value
                            if len(words) != 2 or words[0] != '=':  # failed
                                self.error(SyntaxError, 'invalid syntax: %s' % (repr(line)))
                                return

                            words.pop(0)  # pop =
                            rexpr = words.pop(0)  # pop r-value
                            var.value = self.parseRValue(rexpr, self.scope, line = line)
                        #print 'D|define var(%s:%s) succ' % (vname, var.type.name)
                            
                    elif words[0] == '=': # var = value
                        # hdr.len = 5
                        # hdr = pkg.hdr
                        if len(words) != 2:  # failed
                            self.error(SyntaxError, 'invalid syntax: %s' % (repr(line)))
                            return

                        lexpr = word  # l-value
                        words.pop(0)  # pop =
                        rexpr = words.pop(0)  # pop r-value

                        fvar = self.parseLValue(lexpr, self.scope, autoalloc = True, line = line)
                        fvar.value = self.parseRValue(rexpr, self.scope, line = line)
                    else:  # unsupported syntax
                        self.error(SyntaxError, 'unsupported syntax: %s' % (repr(line)))
                        return

                else:  # var / func(33)
                    expr = word  # expr
                    plists = EqParser.reBetweenBrackets.findall(expr)
                    if len(plists) == 1:  # func(...)
                        fname = expr[:expr.find('(', 1)]
                        if fname[0] == '(':  # failed
                            self.error(SyntaxError, 'invalid syntax: %s' % (repr(line)))
                            return

                        self.parseFunc(fname, plists[0], self.scope, line = line)
                    else:  # var
                        self.error(SyntaxError, 'unsupported syntax: %s' % (repr(line)))
                        return


    def autoAlloc(self, upvar, name, line = ''):
        if upvar.isStruct():
            vtype = self.parseType(upvar.type.ftypeexpr[name], upvar, line = line)
        elif upvar.isArray():
            vtype = upvar.type.itype
        else:
            vtype = None
            self.error(ValueError, 'invalied upvalue(%s): %s' % (upvar.name, line))
            return None
        var = vtype.allocVar(name)
        var.upvalue = upvar
        upvar.value[name] = var
        return var


    def parseLValue(self, expr, varscope, autoalloc = False, line = ''):
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

                indexexprs = EqParser.reBetweenSqrBrackets.findall(name)
                if len(indexexprs) == 1:  # like .l2[r1.r2]
                    name = name[:name.find('[', 1)]
                    if name[0] == '[':  # failed
                        self.error(SyntaxError, 'invalid syntax: %s' % (repr(line)))
                        return
                if not name in lvar.value:
                    check = False
                    break

                lname = name
                lupvar = lvar
                lvar = lvar.value[name]

                if lvar == None and autoalloc:
                    lvar = self.autoAlloc(lupvar, lname, line = line)

                if len(indexexprs) == 1:  # like .l2[r1.r2]
                    index = self.parseRValue(indexexprs[0], varscope, line = line)
                    if index >= len(lvar.value):
                        check = False
                        break

                    lname = index
                    lupvar = lvar
                    lvar = lvar.value[index]

                    if lvar == None and autoalloc:
                        lvar = self.autoAlloc(lupvar, lname, line = line)

            if check:
                return lvar

            svar = svar.upvalue

        return None


    def parseRValue(self, expr, varscope, line = ''):
        if expr == '':
            #self.error(ValueError, 'nothing to parse: %s' % (repr(line)))
            return None

        # 0 / 128 / 0667 / 0o667 / 0x5dfe / 0b1101 / 'as\ndf' / "ABd\x3fdi\t"
        val = self.toValue(expr)
        if val != None:
            return val

        # ${x + 2}
        if expr[:2] == '${' and expr[-1] == '}':
            try:
                return eval(expr[2:-1], globals(), self.pylocals)
            except Exception, msg:
                self.error(ValueError, 'eval(%s) failed, %s: %s' % (repr(expr[2:-1]), msg, repr(line)))
                return None

        # func(...)
        plists = EqParser.reBetweenBrackets.findall(expr)
        if len(plists) == 1:  # = func(...)
            fname = expr[:expr.find('(', 1)]
            if fname[0] == '(':  # failed
                self.error(SyntaxError, 'invalid syntax: %s' % (repr(line)))
                return
            return self.parseFunc(fname, plists[0], varscope, line = line)

        # datalen / hdr2.data.len
        lvar = self.parseLValue(expr, varscope, line = line)
        if lvar != None:
            return lvar.value  # return r-value

        self.error(ValueError, 'r-value(%s) cannot be parsed: %s' % (repr(expr), repr(line)))
        return None


    def parseFunc(self, fname, paramexprs, varscope, line = ''):
        if not fname in self.funcions:  # function not defined
            self.error(NameError, 'function(%s) is not defined: %s' % (repr(fname), repr(line)))
            return None

        fparamlr, func = self.funcions[fname]
        #paramlist = paramexprs.split(',')  # !!!! '(x, y), z' -> '(x' + 'y)' + 'z'
        paramlist = EqParser.splitWithPairs(paramexprs, ',', EqParser.spSplitFuncParams)
        #print 'D|parseFunc(%s)|paramList|' % (fname), repr(paramexprs), '->', paramlist
        vals = list()
        if fparamlr[-1] != '*':  # use MIN(paramlist.size, fparamlr.size)
            paramlist = paramlist[:len(fparamlr)]

        lrlock = None
        for index, paramexpr in enumerate(paramlist):
            lr = None

            if lrlock == None:
                lr = fparamlr[index]
                if lr == '*':
                    lrlock = fparamlr[index - 1]
                    lr = lrlock
            else:
                lr = lrlock

            val = None
            if lr == 'L':  # function accept a l-value
                val = self.parseLValue(paramexpr, varscope, line = line)
            elif lr == 'R':  # function accept a r-value
                val = self.parseRValue(paramexpr, varscope, line = line)
            else:  # unsupported function proto
                self.error(SyntaxError, 'unsupported function proto(%s): %s' % (repr(fparamlr), repr(line)))
                return None

            if val == None:  # failed
                self.error(ValueError, 'invalid value: %s' % (repr(line)))
                return None

            vals.append(val)

            #print 'D|parseFunc(%s)|succ' % (fname)
        return func(*vals)


    def parseType(self, typeexpr, varscope, line = ''):
        '''for example, typeexpr: BODY(hdr.result), varscope: pkg
        PKG = hdr:HDR + body:BODY(hdr.result)
        hdr is in pkg, so the varscope is pkg'''
        # vtype[expr] / vtype(expr2)[expr1]
        exprs = EqParser.reBetweenSqrBrackets.findall(typeexpr)
        if len(exprs) == 1:
            vtype = typeexpr[:typeexpr.find('[', 1)]
            if vtype[0] == '[':
                self.error(SyntaxError, 'invalid syntax: %s' % (repr(line)))
                return None

            vtype = self.parseType(vtype, varscope, line = line)

            val = self.parseRValue(exprs[0], varscope, line = line)
            if isinstance(val, int):
                return Array(self.scope, vtype, val)
            else:
                self.error(ValueError, 'value(%s) is not an integer: %s' % (repr(exprs[0]), repr(line)))
                return None

        # vtype(expr)
        exprs = EqParser.reBetweenBrackets.findall(typeexpr)
        if len(exprs) == 1:
            vtype = typeexpr[:typeexpr.find('(', 1)]
            if vtype[0] == '(':
                self.error(SyntaxError, 'invalid syntax: %s' % (repr(line)))
                return None

            
            if vtype in ('string', 'bits'):
                #paramexprs = exprs[0].split(',')  # !!!! '(x, y), z' -> '(x' + 'y)' + 'z'
                paramexprs = EqParser.splitWithPairs(exprs[0], ',', EqParser.spSplitFuncParams)
                vals = [self.parseRValue(paramexpr, varscope, line = line) for paramexpr in paramexprs]
                
                if vtype == 'string':
                    if not isinstance(vals[0], int) and exprs[0] != '':
                        self.error(ValueError, 'size value(%s) is not an integer: %s' % (repr(paramexprs[0]), repr(line)))
                        return None

                    if len(vals) >= 2 and vals[1] != None and not isinstance(vals[1], str):
                        self.error(ValueError, 'codec value(%s) is not a string: %s' % (repr(paramexprs[1]), repr(line)))
                        return None
                    
                    return String(self.scope, vals[0], encoding = (len(vals) >= 2 and vals[1]) or None)
                elif vtype == 'bits':
                    if not isinstance(vals[0], int) and exprs[0] != '':
                        self.error(ValueError, 'size value(%s) is not an integer: %s' % (repr(paramexprs[0]), repr(line)))
                        return None
                    return Bits(self.scope, vals[0])

            val = self.parseRValue(exprs[0], varscope, line = line)
            if isinstance(val, dict) or isinstance(val, list):  # struct value, or array value
                self.error(ValueError, 'invalid value(%s): %s' % (repr(exprs[0]), repr(line)))
                return None

            if val == None:
                self.error(ValueError, 'value(%s) cannot be parsed: %s' % (repr(exprs[0]), repr(line)))
                return None

            typeexpr = vtype + '(' + repr(val) + ')'

            if typeexpr in self.scope.tmap:
                return self.scope.tmap[typeexpr]
            else:
                typeexpr = vtype + '()'

        if typeexpr in self.scope.tmap:
            return self.scope.tmap[typeexpr]

        #print 'ERR | typeexpr(%s)' % (typeexpr)
        self.error(NameError, 'type(%s) is not defined or cannot be parsed: %s' % (repr(typeexpr), repr(line)))
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
                return eval(s, globals(), self.pylocals)

        return None


    @staticmethod
    def wipeChars(s, chars, bchars):
        lst = list()
        sep = None
        for c in s:
            if sep == None and c in bchars:  # ' or "
                sep = c
                lst.append(c)
                continue

            if sep != None or not c in chars:
                lst.append(c)

            if c == sep:
                sep = None
                
        return ''.join(lst)


    @staticmethod
    def splitWithPairs(s, seps, pairDict):
        '''s: string
        seps: ',' or ',;'
        pairDict: {'()': 2, '[]': 1, '""': 4, "''": 4}

        '''
        # '(x, y), (z, "(dd", aa)'
        push = {pair[0]: (pair[1], level) for pair, level in pairDict.iteritems()}
        pop = {pair[1]: pair[0] for pair in pairDict.iterkeys()}
        
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


    @staticmethod
    def func_print(*rvals):
        for rval in rvals:
            print rval,
        print
    

def main():
    p = EqParser()
    scope = p.scope

    p.execLine(r'HDR = len:uint16 + result:uint8')
    p.execLine(r'BODY(0) = data:string(hdr.len) + ip:IPv4 + mac:MAC')
    p.execLine(r'BODY(1) = msg:string(10)')
    p.execLine(r'PKG = flag:uint8 + hdr:HDR + body:BODY(hdr.result) + resv:uint8[5]')
    p.execLine(r'pkg: PKG')
    p.execLine(r'pkg.flag = ${max(123, 222)}')
    p.execLine(r'hdr: HDR')
    p.execLine(r'hdr.len = 6')
    p.execLine(r'hdr.result = 0')
    p.execLine(r'pkg.hdr = hdr')
    p.execLine(r'pkg.body.data = "what is your name?"')
    p.execLine(r'pkg.body.ip = "192.168.1.1"')
    p.execLine(r'pkg.body.mac = "aa:bb:cc:ee:ff:11"')
    p.execLine(r'pkg.resv[0] = 2')
    p.execLine(r'print(dump(pkg))')
#p.execLine(r's = dump(pkg)')
    p.execLine(r's:string() = encode(pkg)')
#p.execLine(r'print(s)')
    p.execLine(r'pkg2: PKG')
    p.execLine(r'decode(pkg2,s)')
    p.execLine(r's = dump(pkg2)')
    p.execLine(r'print(s, 5454)')
#p.execLine(r's = dump(s)')
#p.execLine(r'print(s)')
    text = r'''
    PNG_CHUNK = Length:uint32@ + Type:string(4) + Data:PNG_DATA(Type) + CRC:string(4, 'hex')
    PNG_DATA('IHDR') = Width:uint32@ + Height:uint32@ + BitDepth:uint8 + ColorType:uint8 + CompressionMethod:uint8 + FilterMethod:uint8 + InterlaceMethod:uint8
    PNG_DATA() = data:string(Length, 'base64')
    PNG = sig:string(8, 'base64') + chunks:PNG_CHUNK[1]

    png:PNG
    chunk:PNG_CHUNK

    arr:int32[4]
#arr[2] = 1
#arr[0] = 5
    print(dump(arr))

    arr:string()[3]
    arr[0] = ${hex(18)}
    arr[2] = "gogogo~~!!!"
    print(dump(arr))
    print(encode(arr))
    '''
    p.execText(text)

    f = open('test.png', 'rb')
    data = f.read()
    f.close()

    png = p.getVar('png')
    png.decode(data)

    d = png.todict(transform = True)
    print png.dump()

    import json
    s = json.dumps(d)

    f = open('res.txt', 'w')
    f.write(s)
    f.close()

    import socket
    import sys
    import time
    import dpkt

    text = r'''
    ETH_TYPE_ARP:uint16 = ${dpkt.ethernet.ETH_TYPE_ARP}
    ETH_TYPE_IP:uint16 = ${dpkt.ethernet.ETH_TYPE_IP}
    
    ETH = ethHdr:ETH_HDR + ethBody:ETH_BODY(ethHdr.type)
    
    ETH_HDR = dst:MAC + src:MAC + type:uint16@
    
    ETH_BODY(ETH_TYPE_ARP) = arp:ARP
    ETH_BODY(ETH_TYPE_IP) = ip:IP
    ETH_BODY() = unknown:string(0)


        ARP = hardType:uint16@ + protoType:uint16@ + hardLen:uint8 + protoLen:uint8 + opType:uint16@ + srcMac:MAC + srcIp:IPv4 + dstMac:MAC + dstIp:IPv4


        IP_PROTO_TCP:uint8 = ${dpkt.ip.IP_PROTO_TCP}
        IP_PROTO_UDP:uint8 = ${dpkt.ip.IP_PROTO_UDP}

        IP = ipHdr:IP_HDR + ipBody:IP_BODY(ipHdr.ipFixed.proto)
    
            IP_HDR = ipFixed:IP_HDR_FIXED + ipOpts:IP_HDR_OPTS
                IP_HDR_FIXED = ver:bits(4) + ipHdrLen:bits(4) + diffServ:uint8 + ipLength:uint16@ + flags:uint16@ + mf:bits(1) + df:bits(1) + rf:bits(1) + frag:bits(13) + ttl:uint8 + proto:uint8 + checkSum:uint16@ + srcIp:IPv4 + dst:IPv4
                IP_HDR_OPTS = options:string(sub(mul(ipFixed.ipHdrLen, 4), calcsize(ipFixed)), 'hex')
    
            IP_BODY(IP_PROTO_TCP) = tcp:TCP
            IP_BODY(IP_PROTO_UDP) = udp:UDP
            IP_BODY() = unknown:string(sub(ipHdr.ipFixed.ipLength, calcsize(ipHdr)), 'hex')


                TCP = tcpHdr:TCP_HDR + tcpBody:TCP_BODY

                    TCP_HDR = tcpFixed:TCP_HDR_FIXED + tcpOpts:TCP_HDR_OPTS
                        TCP_HDR_FIXED = srcPort:uint16@ + dstPort:uint16@ + seq:uint32@ + ack:uint32@ + tcpHdrLen:bits(4) + resv:bits(6) + urgf:bits(1) + ackf:bits(1) + pshf:bits(1) + rstf:bits(1) + synf:bits(1) + finf:bits(1) + win:uint16@ + checkSum:uint16@ + urgent:uint16@
                        TCP_HDR_OPTS = options:string(sub(mul(tcpFixed.tcpHdrLen, 4), calcsize(tcpFixed)), 'hex')

                    TCP_BODY = data:string(sub(sub(ipHdr.ipFixed.ipLength, calcsize(ipHdr)), calcsize(tcpHdr)), 'hex')


                UDP = udpHdr:UDP_HDR + udpBody:UDP_BODY

                    UDP_HDR = srcPort:uint16@ + dstPort:uint16@ + udpLength:uint16@ + checksum:uint16@

                    UDP_BODY = data:string(sub(udpHdr.udpLength, calcsize(udpHdr)), 'hex')


    eth:ETH
    '''

    p.execText(text, locals())
    eth = p.getVar('eth')

    ifname = len(sys.argv) > 1 and sys.argv[1]

    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3))
    if ifname:
        s.bind((ifname, dpkt.ethernet.ETH_TYPE_IP))

    f = open('res2.txt', 'w')
    try:
        while True:
            data, addr = s.recvfrom(65535)
            #p.execLine(r'decode(eth, ${data})', locals())
            eth.decode(data)
            if eth['ethHdr']['type'].value in (dpkt.ethernet.ETH_TYPE_ARP, dpkt.ethernet.ETH_TYPE_IP):
                #ss = json.dumps(eth.todict(transform = True))
                #f.write(ss)
                print eth.dump()
    except Exception, msg:
        print msg

    f.close()
    s.close()


if __name__ == '__main__':
    main()

