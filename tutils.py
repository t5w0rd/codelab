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
        self._lstn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        self._lstn.bind((host, port))
        self._lstn.listen(1)
        if self._tcp:
            self._tcp.close()
        self._tcp, self._addr = self._lstn.accept()
        self._lstn.close()
        self._lstn = None

    def send(self, s):
        '''send a string or iterable strings; return the number of bytes sent.'''
        c = 0
        if isinstance(s, str):
            m = len(s)
            while c < m:
                n = self._tcp.send(s[c:])
                c += n
        elif hasattr(s, '__iter__'):
            c = 0
            for seg in s:
                n = self.send(seg)
                c += n

        return c

    def recv(self, size=None, timeout=None):
        '''return bytes received.'''
        self._tcp.settimeout(timeout)

        ret = None
        while size == None or ret == None or len(ret)< size:
            if size and size > 0:
                if ret == None:
                    n = size
                else:
                    n = size - len(ret)
            else:
                n = 0xffff

            try:
                s = self._tcp.recv(size and (size - len(ret))or 0xffff)
            except socket.timeout:
                break

            if not s:
                break
            
            if not ret:
                ret = s
            else:
                ret += s

        self._tcp.settimeout(None)
        return ret

    def connect(self, host, port, lhost = '0.0.0.0', lport = 0):
        '''connect remote host'''
        
        tcp = socket.socket(type=socket.SOCK_STREAM)
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
        #fcntl.ioctl(pty.STDOUT_FILENO, termios.TIOCGWINSZ, buf, True)
        #print '@@', buf
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, buf)

        try:
            _swap(read_fd=master_fd, write_fd=master_fd, read2_fd=tcp_fd, write2_fd=tcp_fd)
        except (IOError, OSError):
            #print '$swap error'
            pass
        if close_wait >= 0:
            time.sleep(close_wait)
            os.kill(pid, 9)
        os.wait()
        os.close(master_fd)

    def lpty(self, eof_break=True):
        '''I/O from tcp.
        eof_break: True, when reached stdin eof, the swap loop will be break.'''
        tcp_fd = self._tcp.fileno()
        restore = 0
        try:
            mode = tty.tcgetattr(pty.STDIN_FILENO)
            tty.setraw(pty.STDIN_FILENO)
            restore = 1
        except tty.error:    # This is the same as termios.error
            pass
        
        try:
            _swap(read_fd=tcp_fd, write_fd=tcp_fd, eof2_break=eof_break)
        except (IOError, OSError):
            #print '$swap error'
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

def _swap(read_fd, write_fd, read2_fd=pty.STDIN_FILENO, write2_fd=pty.STDOUT_FILENO, read_func=_read, write_func=_write, read2_func=_read, write2_func=_write, eof_break=True, eof2_break=True):
    """Parent swap data loop.
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

    def pServer(self, host, port, handler=_rpty):
        '''socket <-> pty'''
        while True:
            self.listen(host, port)
            handler(self)
            self.close()

    def pClient(self, host, port, handler=_lpty):
        '''stdio <-> socket'''
        self.connect(host, port)
        handler(self)
        self.close()

    def rServer(self, host, port, interval=1, handler=_rpty):
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

    def rClient(self, host, port, handler=_lpty):
        '''stdio <-> socket'''
        self.listen(host, port)
        handler(self)
        self.close()


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
                    _swap(read_fd=ps_net.fileno(), write_fd=ps_net.fileno(), read2_fd=rc_net.fileno(), write2_fd=rc_net.fileno())
                
                rc_net = XNet() # reverse client
                rc_net.rClient(rs_host, rs_port, handler=rcHandler)
            
            ps_net = XNet() # positive server
            ps_net.pServer(ps_host, ps_port, handler=psHandler)

        elif who == 's':
            ps_host = args['host']  # positive server listen host
            ps_port = args['port']  # positive server listen port

            pc_net = XNet()
            pc_net.pClient(ps_host, ps_port)
            
        elif who == 't':
            rs_host = args['host']  # reverse server host
            rs_port = args['port']  # reverse server port
            cmd = args['cmd']
    
            def rsHandler(rs_net):
                #print 'remote connection: %s:%d' % rs_net.addr()
                rs_net.rpty(cmd)

            rs_net = XNet()
            rs_net.rServer(rs_host, rs_port, handler=rsHandler)
            
    elif env == 'sMt':
        pass
    elif env == 'tS':
        if who == 'S':
            rs_host = args['host']  # reverse server host
            rs_port = args['port']  # reverse server port

            rc_net = XNet()
            rc_net.rClient(rs_host, rs_port)
        elif who == 't':
            rs_host = args['host']  # reverse server host
            rs_port = args['port']  # reverse server port
            cmd = args['cmd']
            
            def rsHandler(rs_net):
                #print 'remote connection: %s:%d' % rs_net.addr()
                rs_net.rpty(cmd)

            rs_net = XNet()
            rs_net.rServer(rs_host, rs_port, handler=rsHandler)
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
