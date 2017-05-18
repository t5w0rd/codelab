#!/usr/bin/env python
#coding=utf-8

import os
import sys
import socket
import tty
import pty
import select
import time
import fcntl
import termios
import array
import json
import logging
import multiprocessing
import re


__all__ = ['XNet', 'net', 'daemonize']


class Net:
    _lstn = None
    _tcp, _addr = None, None
    _udp = None  #socket.socket(type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP)

    def __init__(self):
        pass

    def listen(self, host, port):
        '''return the address of the connection.'''
        self._lstn = socket.socket(type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
        self._lstn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, 'SO_REUSEPORT'):
            self._lstn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        self._lstn.bind((host, port))
        self._lstn.listen(1)
        if self._tcp:
            self._tcp.close()
        self._tcp, self._addr = self._lstn.accept()
        self._lstn.close()
        self._lstn = None

    def attach(self, tcp, addr=None):
        if self._tcp:
            self._tcp.close()
        self._tcp, self._addr = tcp, addr

    def send(self, s):
        '''send a string or iterable strings; return the number of bytes sent.'''
        c = 0
        if isinstance(s, str):
            self._tcp.sendall(s)
            c += len(s)
        elif hasattr(s, '__iter__'):
            c = 0
            for seg in s:
                n = self.send(seg)
                c += n

        return c

    def recv(self, size=None, timeout=None):
        if size == None and timeout == None:
            return self._tcp.recv(0xffff)

        self._tcp.settimeout(timeout)
        ret = ''
        while ret == '' or size == None or len(ret) < size:
            if not size:
                n = 0xffff
            else:
                n = size - len(ret)

            try:
                s = self._tcp.recv(n)
            except socket.timeout:
                break

            if not s:
                break
            
            ret += s

        self._tcp.settimeout(None)
        return ret

    def connect(self, host, port, lhost = '0.0.0.0', lport = 0):
        '''connect remote host'''
        
        tcp = socket.socket(type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
        tcp.bind((lhost, lport))
        if self._tcp:
            self._tcp.close()
        self._tcp, self._addr = tcp, (host, port)
        self._tcp.connect((host, port))

    def close(self):
        '''close the tcp socket'''
        self._tcp.close()
        self._tcp, self._addr = None, None

    def fileno(self):
        return self._tcp.fileno()

    def addr(self):
        return self._addr
        
    def bindu(self, host, port):
        if self._udp:
            self._udp.close()
        self._udp = socket.socket(type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP)
        self._udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, 'SO_REUSEPORT'):
            self._udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self._udp.bind((host, port))

    def sendto(self, s, host=None, port=None):
        if host == None or port == None:
            host, port = self._addru
        else:
            self._addru = host, port
        return self._udp.sendto(s, self._addru)

    def recvfrom(self, size=None, timeout=None):
        self._udp.settimeout(timeout)
        try:
            ret, self._addru = self._udp.recvfrom(size or 0xffff)
        except:
            ret = ''
        self._udp.settimeout(None)
        return ret

    def closeu(self):
        self._udp.close()
        self._udp, self._addru = None, None

    def addru(self):
        return self._addru

    def rpty(self, cmd, close_wait=0):
        '''remote execute, I/O from tcp.
        when the connection closed, what child for close_wait seconds. -1: wait until child exits.'''
        tcp_fd = self._tcp.fileno()

        pid, master_fd = pty.fork()
        if pid == pty.CHILD:
            if type(cmd)== str:
                cmd = cmd.split()
            os.execvp(cmd[0], cmd)

        buf = array.array('H', [25, 80, 0, 0])
        try:
            fcntl.ioctl(pty.STDOUT_FILENO, termios.TIOCGWINSZ, buf, True)
        except Exception:
            pass
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, buf)

        try:
            _copyLoop(read_fd=master_fd, write_fd=master_fd, read2_fd=tcp_fd, write2_fd=tcp_fd)
        except (IOError, OSError):
            #print '$copy loop error'
            pass
        if close_wait >= 0:
            time.sleep(close_wait)
            os.kill(pid, 9)
        os.wait()
        os.close(master_fd)

    def lpty(self, eof_break=True):
        '''I/O from tcp.
        eof_break: True, when reached stdin eof, the copy loop will be break.'''
        tcp_fd = self._tcp.fileno()
        restore = 0
        try:
            mode = tty.tcgetattr(pty.STDIN_FILENO)
            tty.setraw(pty.STDIN_FILENO)
            restore = 1
        except tty.error:    # This is the same as termios.error
            pass
        
        try:
            _copyLoop(read_fd=tcp_fd, write_fd=tcp_fd, eof2_break=eof_break)
        except (IOError, OSError):
            #print '$copy loop error'
            pass
        finally:
            if restore:
                tty.tcsetattr(pty.STDIN_FILENO, tty.TCSAFLUSH, mode)
        

def _write(fd, data):
    """Write all the data to a descriptor."""
    while data != '':
        n = os.write(fd, data)
        data = data[n:]

def _read(fd):
    """Default read function."""
    return os.read(fd, 1024)

def _copyLoop(read_fd, write_fd, read2_fd=pty.STDIN_FILENO, write2_fd=pty.STDOUT_FILENO, read_func=_read, write_func=_write, read2_func=_read, write2_func=_write, eof_break=True, eof2_break=True):
    """Parent copy data loop.
    Copies
            read_fd -> write2_fd   (read_func, write2_func)
            read2_fd -> write_fd    (read2_func, write_func)"""
    fds = [read_fd, read2_fd]
    while True:
        rfds, wfds, xfds = select.select(fds, [], [])
        if read_fd in rfds:
            data = read_func(read_fd)
            if not data:  # Reached EOF.
                #print '#read_eof'
                if eof_break:
                    #os.fsync(write2_fd)
                    break
                else:
                    fds.remove(read_fd)
            else:
                #print 'master@', data
                write2_func(write2_fd, data)

        if read2_fd in rfds:
            data = read2_func(read2_fd)
            if not data:
                #print '#read2_eof'
                if eof2_break:
                    #os.fsync(write_fd)
                    break
                else:
                    fds.remove(read2_fd)
            else:
                write_func(write_fd, data)


def _rpty(net):
    #print 'remote connection: %s:%d' % net.addr()
    net.rpty('bash')

def _lpty(net):
    net.lpty()

class XNet(Net):
    def __init__(self):
        Net.__init__(self)

    def posivePtyServer(self, host, port, handler=_rpty):
        '''socket <-> pty'''
        while True:
            self.listen(host, port)
            handler(self)
            self.close()

    def posivePtyClient(self, host, port, handler=_lpty):
        '''stdio <-> socket'''
        self.connect(host, port)
        handler(self)
        self.close()

    def reversePtyServer(self, host, port, interval=1, handler=_rpty):
        '''socket <-> pty'''
        while True:
            try:
                self.connect(host, port)
                handler(self)
                self.close()
            except socket.error, e:
                #print e
                pass

            time.sleep(interval)

    def reversePtyClient(self, host, port, handler=_lpty):
        '''stdio <-> socket'''
        self.listen(host, port)
        handler(self)
        self.close()

    def udpNatTrv(self, key, host, port):
        #addr = self._udp.getsockname()
        '''
        a->M  A
        b->M  B

        b->A  drop
        b->M  M->A
        a->B  ok
        '''
        # a->M or b->M
        cmd = 'udpNatTrv'
        data = {'cmd':cmd, 'key':key}
        data = json.dumps(data)
        _log.info('send(%s)|key(%s),server(%s:%d)', cmd, key, host, port)
        self.sendto(data, host, port)

        # (M)->a or (M)->b
        data = self.recvfrom()
        data = json.loads(data)
        cmd = data['cmd']
        assert(cmd == 'udpNatTrv')

        host, port = self.addru()
        addr = tuple(data['addr'])
        _log.info('recv(%s)|key(%s),server(%s:%d),peer(%s:%d)', cmd, key, host, port, *addr)
        if data['next'] == 'send':
            # B
            # b->A may be drop
            while True:
                cmd = 'udpNatTrv_drop'
                data = {'cmd':cmd}
                data = json.dumps(data)
                _log.info('send(%s)|key(%s),peer(%s:%d)', cmd, key, *addr)
                self.sendto(data, *addr)

                try:
                    data = self.recvfrom(timeout=1)
                    print '@@', self.addru(), data
                except Exception:
                    pass
                except KeyboardInterrupt:
                    break

                break
                

            # b->M (M->a)
            cmd = 'udpNatTrv_ready'
            data = {'cmd':cmd, 'key':key}
            data = json.dumps(data)
            _log.info('send(%s)|key(%s),server(%s:%d)', cmd, key, host, port)
            self.sendto(data, host, port)
            
            # (a)->B
            data = self.recvfrom()
            data = json.loads(data)
            cmd = data['cmd']
            assert(cmd == 'udpNatTrv_ready' and self.addru() == addr)
            _log.info('recv(%s)|key(%s),peer(%s:%d)', cmd, key, *addr)
            _log.info('success|key(%s),peer(%s:%d)', key, *addr)

        else:
            # A
            # (M)->a (or b->a may be drop)
            while True:
                break

                cmd = 'udpNatTrv_drop'
                data = {'cmd':cmd}
                data = json.dumps(data)
                _log.info('send(%s)|key(%s),peer(%s:%d)', cmd, key, *addr)
                self.sendto(data, *addr)

                try:
                    data = self.recvfrom(timeout=1)
                    print '@@', self.addru(), data
                except Exception:
                    pass

            data = self.recvfrom()
            data = json.loads(data)
            cmd = data['cmd']
            if cmd == 'udpNatTrv_drop':
                assert(self.addru() == addr)
                _log.info('recv(%s)|key(%s),peer(%s:%d)', cmd, key, *addr)
                data = self.recvfrom()
                data = json.loads(data)
                cmd = data['cmd']
            assert(cmd == 'udpNatTrv_ready' and self.addru() == (host, port))
            _log.info('recv(%s)|key(%s),server(%s:%d)', cmd, key, host, port)

            # a->B  ok
            cmd = 'udpNatTrv_ready'
            data = {'cmd':cmd}
            data = json.dumps(data)
            _log.info('send(%s)|key(%s),peer(%s:%d)', cmd, key, *addr)
            self.sendto(data, *addr)
            _log.info('success|key(%s),peer(%s:%d)', key, *addr)


    def udpNatTrvServer(self, host, port):
        keyAddr = dict()
        self.bindu(host, port)
        while True:
            data = self.recvfrom()
            data = json.loads(data)
            cmd = data['cmd']
            if cmd == 'udpNatTrv':
                key = data['key']
                if not key in keyAddr or keyAddr[key] == self.addru():
                    # host A
                    _log.info('recv(%s)|key(%s),host A(%s:%d)', cmd, key, *self.addru())
                    keyAddr[key] = self.addru()
                else:
                    # host B
                    # M->b
                    _log.info('recv(%s)|key(%s),host B(%s:%d)', cmd, key, *self.addru())
                    cmd = 'udpNatTrv'
                    data = {'cmd':cmd, 'addr':keyAddr[key], 'next': 'send'}
                    data = json.dumps(data)
                    _log.info('send(%s)|key(%s),host B(%s:%d)', cmd, key, *self.addru())
                    self.sendto(data)

                    # M->a
                    data = {'cmd':cmd, 'addr':self.addru(), 'next': 'recv'}
                    data = json.dumps(data)
                    _log.info('send(%s)|key(%s),host A(%s:%d)', cmd, key, *keyAddr[key])
                    self.sendto(data, *keyAddr[key])

            elif cmd == 'udpNatTrv_ready':
                # host B
                key = data['key']
                _log.info('recv(%s)|key(%s),host B(%s:%d)', cmd, key, *self.addru())

                # (b)->M
                # M->a
                cmd = 'udpNatTrv_ready'
                data = {'cmd':cmd}
                data = json.dumps(data)
                _log.info('send(%s)|key(%s),host A(%s:%d)', cmd, key, *keyAddr[key])
                self.sendto(data, *keyAddr.pop(key))


def ptyPipe(who, env, **args):
    '''who:
    M: middle host with public ip;
    s: source host with internal ip;
    t: target host with internal ip;

    relationship:
    s!t: s and t cannot access each other;
    t>s: s can access t, but t cannot;
    M=s: M and s can access each other;

    env:
    stM or tsM: s!t s>M t>M
    sMt: s!t s>M M=t
    '''

    if env == 'stM' or env == 'tsM':
        if who == 'M':
            ps_host = args['host']  # positive server listen host
            ps_port = args['port']  # positive server listen port
            rs_host = args['rhost']  # reverse server host
            rs_port = args['rport']  # reverse server port
            
            def psHandler(ps_net):
                def rcHandler(rc_net):
                    _copyLoop(read_fd=ps_net.fileno(), write_fd=ps_net.fileno(), read2_fd=rc_net.fileno(), write2_fd=rc_net.fileno())
                
                rc_net = XNet() # reverse client
                rc_net.reversePtyClient(rs_host, rs_port, handler=rcHandler)
            
            ps_net = XNet() # positive server
            ps_net.posivePtyServer(ps_host, ps_port, handler=psHandler)

        elif who == 's':
            ps_host = args['host']  # positive server listen host
            ps_port = args['port']  # positive server listen port

            pc_net = XNet()
            pc_net.posivePtyClient(ps_host, ps_port)
            
        elif who == 't':
            rs_host = args['host']  # reverse server host
            rs_port = args['port']  # reverse server port
            cmd = args['cmd']
    
            def rsHandler(rs_net):
                #print 'remote connection: %s:%d' % rs_net.addr()
                rs_net.rpty(cmd)

            rs_net = XNet()
            rs_net.reversePtyServer(rs_host, rs_port, handler=rsHandler)
            
    elif env == 'sMt':
        pass
    elif env == 'tS':
        if who == 'S':
            rs_host = args['host']  # reverse server host
            rs_port = args['port']  # reverse server port

            rc_net = XNet()
            rc_net.reversePtyClient(rs_host, rs_port)
        elif who == 't':
            rs_host = args['host']  # reverse server host
            rs_port = args['port']  # reverse server port
            cmd = args['cmd']
            
            def rsHandler(rs_net):
                #print 'remote connection: %s:%d' % rs_net.addr()
                rs_net.rpty(cmd)

            rs_net = XNet()
            rs_net.reversePtyServer(rs_host, rs_port, handler=rsHandler)
    else:
        pass


_net = XNet()
def net():
    return _net

def daemonize(stdin='/dev/null', stdout='/dev/null', stderr='/dev/null', keepwd=False):
    """
    do the UNIX double-fork magic, see Stevens' "Advanced 
    Programming in the UNIX Environment" for details (ISBN 0201563177)
    http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
    """
    try: 
        pid = os.fork()
        if pid > 0:
            # exit first parent
            sys.exit(0)
    except OSError, e: 
        sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
        sys.exit(1)

    # decouple from parent environment
    if not keepwd:
        os.chdir("/")
    os.setsid()
    os.umask(0)

    # do second fork
    try: 
        pid = os.fork()
        if pid > 0:
            # exit from second parent
            sys.exit(0)
    except OSError, e: 
        sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
        sys.exit(1)

    # redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()
    si = file(stdin, 'r')
    so = file(stdout, 'a+')
    se = file(stderr, 'a+', 0)
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())
    
def multijobs(target, args, workers=None):
    if not workers:
        workers = multiprocessing.cpu_count()
    jobs = len(args)
    workers = min(jobs, workers)
    pool = multiprocessing.Pool(processes=workers)
    ret = pool.map(target, args)
    pool.close()
    pool.join()
    return ret

import SocketServer
import slde
import proto

class _TcpServerHandler(SocketServer.BaseRequestHandler):
    def __init__(self, req, addr, server):
        self.msgq = server.manager.Queue()
        self.buf = slde.SldeBuf()

        SocketServer.BaseRequestHandler.__init__(self, req, addr, server)
        

    def setup(self):
        #self.server.msgq.put({'cmd': 'add', 'req': self})
        self.server.reqs[self.client_address] = time.time()

    def handle(self):
        print self.client_address

        left = self.buf.headerSize
        while left:
            data = self.request.recv(left)
            left = self.buf.write(data)

        if left != None:
            pr = proto.EqParser()
            pr.execute('''
            SLDE = stx:uint8 + length:uint16@ + data:string(length, 'hex') + etx:uint8
            data:SLDE
            ''')
            pdata = pr.getVar('data')
            data = self.buf.decode()
            data = json.loads(data)
            cmd = data['cmd']
            if cmd == 'list':
                rsp = {'cmd': cmd, 'clients': list()}
                for addr, info in self.server.reqs.items():
                    rsp['clients'].append(addr)
                self.response(rsp)

            
    def finish(self):
        #self.server.msgq.put({'cmd': 'del', 'req': self})
        print 'req cost:', time.time() - self.server.reqs.pop(self.client_address)

    def encode(self, data):
        self.buf.clear()
        data = json.dumps(data)
        return self.buf.encode(data)

    def response(self, data):
        data = self.encode(data)
        self.request.sendall(data);
        

class _ForkingTCPServer(SocketServer.ForkingTCPServer):
    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
        self.manager = multiprocessing.Manager()
        self.msgq = self.manager.Queue()
        self.reqs = self.manager.dict()
        SocketServer.ForkingTCPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate=bind_and_activate)

    def serve_forever(self, poll_interval=0.5):
        proc = multiprocessing.Process(target=self.procMsgHanler)
        proc.start()

        SocketServer.ForkingTCPServer.serve_forever(self, poll_interval=poll_interval)

        proc.join()

    def procMsgHanler(self):
        while True:
            msg = self.msgq.get()
            cmd = msg['cmd']
            req = msg['req']
            if cmd == 'add':
                self.reqs[req] = time.time()
            elif cmd == 'del':
                info = self.reqs.pop(req)
                print 'proc req cost:', time.time() - info
            elif cmd == 'list':
                s = ''
                for r, info in self.reqs.iteritems():
                    s += '%s:%d\n' % r.client_address
                print s
                #req.msgq.put(s)

        
def tcpServer(host, port, maxconn=10):
    _ForkingTCPServer.allow_reuse_address = True
    _ForkingTCPServer.timeout = 5
    server = _ForkingTCPServer((host, port), _TcpServerHandler)
    server.serve_forever()


def initLogger():
    log = logging.getLogger('tutils')
    log.setLevel(logging.DEBUG)
    fmt = logging.Formatter(r'[%(levelname)s %(asctime)s %(filename)s:%(lineno)d] %(message)s')

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    sh.setLevel(logging.INFO)
    #sh.setLevel(logging.DEBUG)
    log.addHandler(sh)

    #fh = logging.FileHandler('%s/log-%s.log' % (workspace, subname))
    #fh.setFormatter(fmt)
    #fh.setLevel(logging.INFO)
    #log.addHandler(fh)
    return log

_log = initLogger()

if __name__ == '__main__':
    tcpServer('localhost', 2889)
