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
            vtype = self.type.scope.getType(typestr, self)
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


class Type:
    def __init__(self, scope, name):
        self.scope = scope
        self.name = name


    def allocVar(self, name):
        fakename = name.replace('_', 'a')
        if not fakename[0].isalpha() or not fakename.isalnum():
            return None

        #print 'DBG | alloc var(%s:%s)' % (name, self.name)
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
        print '    ' * level + '%s %s = %s' % (self.name, var.name, repr(var.value))


    def calcsize(self, var):
        return struct.calcsize(self.packstr)


class String(Basic):
    def __init__(self, scope, length):
        if length == None:
            Basic.__init__(self, scope, 'string()', '')
        else:
            Basic.__init__(self, scope, 'string(%d)' % (length), '%ds' % (length))


    def encode(self, var, level = 0):
        packstr = self.__packstr(var)
        print '    ' * level + '%s %s = %s' % (self.name, var.name, repr(var.value[:int(packstr[:-1])]))
        return struct.pack(packstr, var.value)


    def decode(self, var, data, level = 0):
        packstr = self.__packstr(var)
        var.value = struct.unpack_from(packstr, data)[0]
        print '    ' * level + '%s %s = %s' % (self.name, var.name, repr(var.value[:int(packstr[:-1])]))


    def calcsize(self, var):
        return struct.calcsize(self.__packstr(var))


    def __packstr(self, var):
        if self.packstr == '':
            return '%ds' % (len(var.value))
        return self.packstr


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
            ftype = self.scope.getType(self.fmap[fname], var)
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
        print '    ' * level + '%s %s = %s' % (self.name, var.name, '{')
        pos = 0
        for fname in self.fseq:
            ftype = self.scope.getType(self.fmap[fname], var)
            fvar = var.value[fname]
            if fvar == None:
                fvar = ftype.allocVar(fname)
                fvar.upvalue = var
                var.value[fname] = fvar
            ftype.decode(fvar, data[pos:], level = level + 1)
            size = ftype.calcsize(fvar)
            pos += size
        print '    ' * level + '}'


    def calcsize(self, var):
        size = 0
        for fname in self.fseq:
            ftype = self.scope.getType(self.fmap[fname], var)
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
    def __init__(self, name, parser):
        Variable.__init__(self, None, name, value = dict(), upvalue = None)
        self.parser = parser
        self.tmap = {
            'uint8': Basic(self, 'uint8', 'B'),
            'uint16': Basic(self, 'uint16', '>H'),
            'uint32': Basic(self, 'uint32', '>I'),
            'uint64': Basic(self, 'uint64', '>Q')}


    def getVar(self, name):
        if name in self.value:
            return self.value[name]
        return None


    def getType(self, typestr, varscope):
        return self.parser.parseType(typestr, varscope, '')
        #try:
        #    return self.parser.parseType(typestr, varscope, '')
        #except:
        #    return None


    def defType(self, name, proto):
        newtype = Struct(self, name, proto)
        self.tmap[name] = newtype
        return newtype


    def defVar(self, name, typestr):
        vtype = self.getType(typestr, self)
        if vtype == None:
            return None

        newvar = vtype.allocVar(name)
        if newvar == None:
            return None

        newvar.upvalue = self
        self.value[name] = newvar
        return newvar


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
    #    return self.parseType(self, typestr, self.scope, 'Parser.getType(self, %s)' % (repr(name)))


    def getVar(self, expr):
        '''return the Variable instance as a l-value, expr: x or xx.yy.zz'''
        return self.parseLValue(expr, self.scope, 'Parser.getLValue(self, %s)' % (repr(expr)))


    def getValue(self, expr):
        '''return the value of Variable instance as r-value, expr: x or xx.yy.zz'''
        return self.parseRValue(expr, self.scope, 'Parser.getRValue(self, %s)' % (repr(expr)))


    def error(self, e, msg):
        raise e, msg


    def parseLValue(self, expr, varscope, line):
        pass


    def parseRValue(self, expr, varscope, line):
        pass


    def parseType(self, typestr, varscope, line):
        pass


class MyParser(Parser):
    def __init__(self):
        Parser.__init__(self)
        self.state = State({'idle'}, 'idle')
        self.keywords = {}
        self.funcions = {
            'print': ('R*', MyParser.func_print),
            'encode': ('L', MyParser.func_encode),
            'decode': ('LR', MyParser.func_decode),
            'dump': ('L', MyParser.func_dump)
        }


    def parseText(self, text):
        lines = text.splitlines()
        for line in lines:
            self.parseLine(line)


    def parseLine(self, line):
        words = reMyParserParseLine.findall(MyParser.wipeChars(line, ' \t\n\r', '\'\"'))
        if len(words) == 0:
            return

        #print 'DBG | ' + repr(words)
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
                            self.error(SyntaxError, 'invalid syntax: %s' % (repr(line)))
                            return

                        self.scope.defType(tname, proto)
                        #print 'DBG | define type(%s) succ' % (tname)

                    elif words[0] == ':':  # var:TYPE
                        vname = word  # var name
                        words.pop(0)  # pop :
                        if len(words) < 1:  # failed
                            self.error(SyntaxError, 'invalid syntax: %s' % (repr(line)))
                            return

                        vtypestr = words.pop(0)  # pop type name
                        var = self.scope.defVar(vname, vtypestr)
                        if var == None:  # failed
                            self.error(NameError, 'type(%s) is not defined or cannot be parsed: %s' % (repr(vtypestr), repr(line)))
                            return

                        if len(words) > 0:  # var:TYPE = r-value
                            if len(words) != 2 or words[0] != '=':  # failed
                                self.error(SyntaxError, 'invalid syntax: %s' % (repr(line)))
                                return

                            words.pop(0)  # pop =
                            rexpr = words.pop(0)  # pop r-value
                            var.value = self.parseRValue(rexpr, self.scope, line)
                        #print 'DBG | define var(%s:%s) succ' % (vname, var.type.name)
                            
                    elif words[0] == '=': # var = value
                        # hdr.len = 5
                        # hdr = pkg.hdr
                        if len(words) != 2:  # failed
                            self.error(SyntaxError, 'invalid syntax: %s' % (repr(line)))
                            return

                        lexpr = word  # l-value
                        words.pop(0)  # pop =
                        rexpr = words.pop(0)  # pop r-value

                        flist = lexpr.split('.')
                        fvar = self.scope
                        for fname in flist:
                            fvar = fvar.item(fname)
                            if fvar == None:
                                self.error(NameError, 'l-value(%s) cannot be parsed: %s' % (repr(lexpr), repr(line)))
                                return

                        fvar.value = self.parseRValue(rexpr, self.scope, line)
                    else:  # unsupported syntax
                        self.error(SyntaxError, 'unsupported syntax: %s' % (repr(line)))
                        return

                else:  # var / func(33)
                    expr = word  # expr
                    plists = reBetweenBrackets.findall(expr)
                    if len(plists) == 1:  # func(...)
                        fname = expr[:expr.find('(', 1)]
                        if fname[0] == '(':  # failed
                            self.error(SyntaxError, 'invalid syntax: %s' % (repr(line)))
                            return

                        self.parseFunc(fname, plists[0], line)
                    else:  # var
                        self.error(SyntaxError, 'unsupported syntax: %s' % (repr(line)))
                        return


    def parseLValue(self, expr, varscope, line):
        flist = expr.split('.')
        if len(flist) == 0 or flist[0] == '' or flist[-1] == '':
            return None

        while varscope != None:
            # check f1.f2.f3 in varscope
            check = True
            lvar = varscope
            for name in flist:
                if lvar.isComplex() and name in lvar.value:
                    lvar = lvar.value[name]
                else:
                    check = False
                    break
            if check:
                return lvar

            varscope = varscope.upvalue

        return None


    def parseRValue(self, expr, varscope, line):
        if expr == '':
            #self.error(ValueError, 'nothing to parse: %s' % (repr(line)))
            return None

        # 0 / 128 / 0667 / 0o667 / 0x5dfe / 0b1101 / 'as\ndf' / "ABd\x3fdi\t"
        val = MyParser.toValue(expr)
        if val != None:
            return val

        # ${x + 2}
        if expr[:2] == '${' and expr[-1] == '}':
            try:
                return eval(expr[2:-1])
            except Exception, msg:
                self.error(ValueError, 'eval failed, %s: %s' % (msg, repr(line)))
                return None

        # func(...)
        plists = reBetweenBrackets.findall(expr)
        if len(plists) == 1:  # = func(...)
            fname = expr[:expr.find('(', 1)]
            if fname[0] == '(':  # failed
                self.error(SyntaxError, 'invalid syntax: %s' % (repr(line)))
                return
            return self.parseFunc(fname, plists[0], line)

        # datalen / hdr2.data.len
        lvar = self.parseLValue(expr, varscope, line)
        if lvar != None:
            return lvar.value  # return r-value

        self.error(ValueError, 'r-value(%s) cannot be parsed: %s' % (repr(expr), repr(line)))
        return None


    def parseFunc(self, fname, paramstrs, line):
        if not fname in self.funcions:  # function not defined
            self.error(NameError, 'function(%s) is not defined: %s' % (repr(fname), repr(line)))
            return None

        fparamlr, func = self.funcions[fname]
        paramlist = paramstrs.split(',')
        vals = list()
        if fparamlr[-1] != '*':  # use MIN(paramlist.size, fparamlr.size)
            paramlist = paramlist[:len(fparamlr)]

        lrlock = None
        for index, paramstr in enumerate(paramlist):
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
                val = self.parseLValue(paramstr, self.scope, line)
            elif lr == 'R':  # function accept a r-value
                val = self.parseRValue(paramstr, self.scope, line)
            else:  # unsupported function proto
                self.error(SyntaxError, 'unsupported function proto(%s): %s' % (repr(fparamlr), repr(line)))
                return None

            if val == None:  # failed
                self.error(ValueError, 'invalid value: %s' % (repr(line)))
                return None

            vals.append(val)
        return func(*vals)


    def parseType(self, typestr, varscope, line):
        '''typestr: BODY(hdr.result), varscope: pkg
        PKG = hdr:HDR + body:BODY(hdr.result)
        hdr is in pkg, so the varscope is pkg'''
        # vtype(expr)
        exprs = reBetweenBrackets.findall(typestr)
        if len(exprs) == 1:
            val = self.parseRValue(exprs[0], varscope, line)
            if isinstance(val, dict):  # struct value
                self.error(ValueError, 'invalid value(%s): %s' % (repr(exprs[0]), repr(line)))
                return None
            
            vtype = typestr[:typestr.find('(', 1)]
            if vtype in ('string'):
                if isinstance(val, int) or exprs[0] == '':
                    return String(self.scope, val)
                else:
                    self.error(ValueError, 'value(%s) is not a integer: %s' % (repr(exprs[0]), repr(line)))
                    return None

            if val == None:
                self.error(ValueError, 'value(%s) is empty: %s' % (repr(exprs[0]), repr(line)))
                return None

            typestr = vtype + '(' + repr(val) + ')'

            if typestr in self.scope.tmap:
                return self.scope.tmap[typestr]
            else:
                typestr = vtype + '()'

        if typestr in self.scope.tmap:
            return self.scope.tmap[typestr]

        #print 'ERR | typestr(%s)' % (typestr)
        self.error(NameError, 'type(%s) is not defined or cannot be parsed: %s' % (repr(typestr), repr(line)))
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


    @staticmethod
    def func_print(*rvals):
        for rval in rvals:
            print rval,
        print


    @staticmethod
    def func_encode(lvar):
        return lvar.encode()


    @staticmethod
    def func_decode(lvar, rdata):
        lvar.decode(rdata)


    @staticmethod
    def func_dump(lvar):
        return lvar.dump()
        
        
reBetweenBrackets = re.compile(r'\((.*)\)')
reEval = re.compile(r'${(.*)}')
#reMyParserParseLine = re.compile(r'\'.*\'|".*"|[+=:]|[\w_.(),]+')
reMyParserParseLine = re.compile(r'".*"|[+=:]|[\w_.(){}$,\']+')

p = MyParser()
scope = p.scope

p.parseLine(r'HDR = len:uint16 + result:uint8')
p.parseLine(r'BODY(0) = data:string(hdr.len) + crc:string(4)')
p.parseLine(r'BODY(1) = msg:string(10)')
p.parseLine(r'PKG = flag:uint8 + hdr:HDR + body:BODY(hdr.result)')
p.parseLine(r'pkg: PKG')
p.parseLine(r'pkg.flag = ${max(123, 222)}')
p.parseLine(r'hdr: HDR')
p.parseLine(r'hdr.len = 6')
p.parseLine(r'hdr.result = 0')
p.parseLine(r'pkg.hdr = hdr')
p.parseLine(r'pkg.body.data = "what is your name?"')
p.parseLine(r'pkg.body.crc = "\xAA\xBB\xCC\xDD"')
p.parseLine(r's:string() = encode(pkg)')
#p.parseLine(r's = dump(pkg)')
#p.parseLine(r's = encode(pkg)')
p.parseLine(r'print(s)')
p.parseLine(r'pkg2: PKG')
p.parseLine(r'decode(pkg2,s)')
p.parseLine(r's = dump(pkg2)')
p.parseLine(r'print(s, 5454)')
#p.parseLine(r's = dump(s)')
#p.parseLine(r'print(s)')

text = r'''
PNG_CHUNK = Length:uint32 + Type:string(4) + Data:PNG_DATA(Type) + CRC:uint32
PNG_DATA('IHDR') = Width:uint32 + Height:uint32 + BitDepth:uint8 + ColorType:uint8 + CompressionMethod:uint8 + FilterMethod:uint8 + InterlaceMethod:uint8
PNG_DATA() = data:string(Length)
PNG = sig:string(8) + chunk1:PNG_CHUNK

png:PNG
chunk:PNG_CHUNK
'''
p.parseText(text)

f = open('test.png', 'rb')
data = f.read()
f.close()

png = p.getVar('png')
png.decode(data)

print png.dump()
