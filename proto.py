#!/usr/bin/env python

import struct
import re
import string


class Variable:
    def __init__(self, vtype, name, value = None, upvalue = None):
        self.type = vtype
        self.name = name
        self.value = value
        self.upvalue = upvalue


    def __getitem__(self, fname):
        '''var[fname]'''
        item = self.item(fname)
        return item and item.value


    def __setitem__(self, fname, value):
        '''var[fname] = value'''
        item = self.item(fname)
        if item:
            item.value = value
        

    def item(self, fname):
        if not fname in self.value:
            print repr(self.value)
            return None
        
        if self.value[fname] == None:
            typestr = self.type.fmap[fname]
            vtype = self.type.scope.parseType(typestr, self)
            newvar = vtype.allocVar(fname)
            newvar.upvalue = self
            self.value[fname] = newvar

        return self.value[fname]


    def isComplex(self):
        return isinstance(self.value, dict)


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
        if self.isComplex():
            res = addln(res, '\'%s\': {' % (self.name), level)
            first = True
            vtype = self.type
            for name in vtype.fseq:
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


    def parseLValue(self, expr):
        flist = expr.split('.')
        if len(flist) == 0 or len(flist[0]) == 0 or len(flist[-1]) == 0:
            return None

        scope = self
        while scope != None:
            # check f1.f2.f3 in scope
            check = True
            lvar = scope
            for name in flist:
                if lvar.isComplex() and name in lvar.value:
                    lvar = lvar.value[name]
                else:
                    check = False
                    break
            if check:
                return lvar

            scope = scope.upvalue

        return None


    def parseRValue(self, expr):
        # 0 / 128 / 0667 / 0o667 / 0x5dfe / 0b1101 / 'as\ndf' / "ABd\x3fdi\t"
        val = Variable.toValue(expr)
        if val != None:
            return val

        # datalen / hdr2.data.len
        lvar = self.parseLValue(expr)
        if lvar != None:
            return lvar.value  # return r-value
        
        return None


    @staticmethod
    def toValue(s):
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
                return eval(s)

        return None


class Type:
    def __init__(self, scope, name):
        self.scope = scope
        self.name = name


    def allocVar(self, name):
        fakename = name.replace('_', 'a')
        if not fakename[0].isalpha() or not fakename.isalnum():
            return None

        print 'DBG | alloc var(%s:%s)' % (name, self.name)
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
        if length == None:
            Basic.__init__(self, scope, 'string()', '')
        else:
            Basic.__init__(self, scope, 'string(%d)' % (length), '%ds' % (length))


class Struct(Type):
    def __init__(self, scope, name, proto):
        '''proto: ((fname, typestr), (fname, typestr), ...)'''
        Type.__init__(self, scope, name)

        fseq = [fname for fname, typestr in proto]  # member sequence
        fmap = dict(proto)  # member name-typestr map

        self.fseq = fseq
        self.fmap = fmap


    def encode(self, var, level = 0):
        print '    ' * level + '%s %s = %s' % (self.name, var.name, '{')
        data = str()
        for fname in self.fseq:
            ftype = self.scope.parseType(self.fmap[fname], var)
            fvar = var.value[fname]
            res = ftype.encode(fvar, level = level + 1)
            if res == None:
                #print 'ERR | encode:' + fname
                return None
            else:
                data += res
        print '    ' * level + '}'
        return data


    def decode(self, var, data, level = 0):
        pos = 0
        for fname in self.fseq:
            ftype = self.scope.parseType(self.fmap[fname], var)
            if var.value[fname] == None:
                var.value[fname] = ftype.allocVar(fname)
            fvar = var.value[fname]
            size = ftype.calcsize(fvar)
            ftype.decode(fvar, data[pos: pos + size], level = level + 1)
            pos += size


    def calcsize(self, var):
        size = 0
        for fname in self.fseq:
            ftype = self.scope.parseType(self.fmap[fname], var)
            fvar = var.value[fname]
            res = ftype.calcsize(fvar)
            size += res
        return size


    def allocVar(self, name):
        newvar = Type.allocVar(self, name)
        if newvar == None:
            return None

        fvmap = dict()
        for fname in self.fseq:
            fvmap[fname] = None
        
        newvar.value = fvmap
        return newvar


class Scope(Variable):
    def __init__(self, name):
        Variable.__init__(self, None, name, value = dict(), upvalue = None)
        self.tmap = {
            'uint8': Basic(self, 'uint8', 'B'),
            'uint16': Basic(self, 'uint16', 'H'),
            'uint32': Basic(self, 'uint32', 'I'),
            'uint64': Basic(self, 'uint64', 'Q')}
    

    def getVar(self, name):
        if name in self.value:
            return self.value[name]
        return None


    def getType(self, typestr):
        return self.parseType(typestr, self)


    def defType(self, name, proto):
        newtype = Struct(self, name, proto)
        self.tmap[name] = newtype
        return newtype


    def defVar(self, name, typestr):
        vtype = self.parseType(typestr, self)
        if vtype == None:
            return None

        newvar = vtype.allocVar(name)
        if newvar == None:
            return None

        newvar.upvalue = self
        self.value[name] = newvar
        return newvar


    def parseType(self, typestr, var):
        # vtype(expr)
        expr = reBetweenBrackets.findall(typestr)
        if len(expr) > 0:
            val = var.parseRValue(expr[0])
            if isinstance(val, dict):  # struct value
                return None
            
            vtype = typestr[:typestr.find('(', 1)]

            if vtype in ('string'):
                if isinstance(val, int) or val == None:
                    return String(self, val)
                else:
                    return None

            if val == None:
                return None

            typestr = vtype + '(' + repr(val) + ')'

            if typestr in self.tmap:
                return self.tmap[typestr]
            else:
                typestr = vtype + '()'

        if typestr in self.tmap:
            return self.tmap[typestr]

        #print 'ERR | typestr(%s)' % (typestr)
        return None


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
        self.scope = Scope('GLOBAL')


class MyParser(Parser):
    def __init__(self):
        Parser.__init__(self)
        self.state = State({'idle'}, 'idle')
        self.keywords = {}


    def parseLine(self, line):
        # TYPE = field1:type1 + field2:type2(334)
        # var:TYPE
        # var.field = 3
        # pkg.var = var
        #orgline = line
        words = reMyParserParseLine.findall(line)
        print 'DBG | ' + repr(words)
        while len(words) > 0:
            word = words.pop(0)  # pop first word
            if word in self.keywords:  # keyword
                self.error(SyntaxError, '')
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
                            ftypestr = words.pop(0)  # pop field typestr
                            proto.append((fname, ftypestr))
                        
                        if len(proto) == 0 or len(words) > 0:  # failed
                            self.error(SyntaxError, 'invalid syntax: %s' % (line))
                            return

                        self.scope.defType(tname, proto)
                        print 'DBG | define type(%s) succ' % (tname)

                    elif words[0] == ':':  # var:TYPE
                        vname = word  # var name
                        words.pop(0)  # pop :
                        if (len(words) != 1):  # failed
                            self.error(SyntaxError, 'invalid syntax: %s' % (line))
                            return

                        vtypestr = words.pop(0)  # pop type name
                        var = self.scope.defVar(vname, vtypestr)
                        if var == None:  # failed
                            self.error(NameError, 'type(%s) is not defined or cannot be parsed: %s' % (vtypestr, line))
                            return

                        print 'DBG | define var(%s:%s) succ' % (vname, var.type.name)
                            
                    elif words[0] == '=': # var = value
                        # hdr.len = 5
                        # hdr = pkg.hdr
                        if len(words) != 2:  # failed
                            self.error(SyntaxError, 'invalid syntax: %s' % (line))
                            return

                        lexpr = word  # l-value
                        words.pop(0)  # pop =
                        rexpr = words.pop(0)  # pop r-value

                        flist = lexpr.split('.')
                        fvar = self.scope
                        for fname in flist:
                            fvar = fvar.item(fname)
                            if fvar == None:
                                self.error(NameError, 'unresolved var(%s): %s' % (lexpr, line))
                                return
                        #print lexpr + ' = ' + repr(self.scope.parseRValue(rexpr))
                        fvar.value = self.scope.parseRValue(rexpr)
                        
                        #lvar = self.scope.parseLValue(lexpr)
                        #rvalue = self.scope.parse
                        #print lexpr + ' = ' + rexpr
                        #print repr(self.scope.parseLValue(lexpr))
                        #print repr(self.scope.parseRValue(rexpr))
                        pass

                    else:  # unsupported syntax
                        self.error(SyntaxError, 'unsupported syntax: %s' % (line))
                        return

                else:  # var / func(g(55))
                    self.error(SyntaxError, 'unsupported syntax: %s' % (line))
                    return

    def error(self, e, msg):
        raise e, msg
        
        
reBetweenBrackets = re.compile(r'\((.*)\)')
reMyParserParseLine = re.compile(r'\'.*\'|".*"|[+=:]|[\w_.()]+')

p = MyParser()
scope = p.scope

p.parseLine(r'HDR = len:uint16 + result:uint8')
p.parseLine(r'BODY(0) = data:string(hdr.len) + crc:string(4)')
p.parseLine(r'BODY(1) = msg:string(10)')
p.parseLine(r'PKG = flag:uint8 + hdr:HDR + body:BODY(hdr.result)')
p.parseLine(r'pkg: PKG')
p.parseLine(r'pkg.flag = "a\x32sdf"')
p.parseLine(r'encode(pkg)')

'''
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

'''
