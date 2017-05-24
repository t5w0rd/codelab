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
import select
import ctypes
import struct

import traceback


__all__ = ['net', 'XNet', 'tcpPtyIO', 'tcpRawStdIO', 'daemonize', 'multijobs', 'initLogger', 'StopWatch', 'SldeBuf']


class Net:
    _lstn = None
    _tcp = None
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
        self._lstn.listen(5)
        if self._tcp:
            self._tcp.close()
        self._tcp, addr = self._lstn.accept()
        self._lstn.close()
        self._lstn = None

    def connect(self, host, port, lhost = '0.0.0.0', lport = 0):
        '''connect remote host'''
        
        tcp = socket.socket(type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
        tcp.bind((lhost, lport))
        if self._tcp:
            self._tcp.close()
        self._tcp = tcp
        self._tcp.connect((host, port))

    def tcp(self):
        return self._tcp

    def laddr(self):
        return self._tcp.getsockname()

    def raddr(self):
        return self._tcp.getpeername()

    def attach(self, tcp):
        if self._tcp:
            self._tcp.close()
        self._tcp = tcp

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
        ret = None
        while ret == '' or size == None or ret == None or len(ret) < size:
            n = (not size and 0xffff) or (size - (ret != None and len(ret) or 0))
            try:
                s = self._tcp.recv(n)
            except socket.timeout:
                break

            if not s:
                if ret == None:
                    ret = s
                break
            
            if ret == None:
                ret = s
            else:
                ret += s

        self._tcp.settimeout(None)
        return ret

    def close(self):
        '''close the tcp socket'''
        self._tcp.close()
        self._tcp = None

    def fileno(self):
        return self._tcp.fileno()

    def bindu(self, host, port):
        if self._udp:
            self._udp.close()
        self._udp = socket.socket(type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP)
        self._udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, 'SO_REUSEPORT'):
            self._udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self._udp.bind((host, port))

    def attachu(self, udp, addr=None):
        if self._udp:
            self._udp.close()
        self._udp, self._addru = udp, addr

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

    def udp(self):
        return self._udp

    def addru(self):
        return self._addru

    def sendf(self, fp, offset=None, size=None):
        if offset is not None:
            fp.seek(offset, os.SEEK_SET)

        sent = 0
        while size is None or sent < size:
            n = (size is not None and size - sent) or 512
            s = fp.read(n)
            if not s:
                break

            n_ = self._tcp.send(s)
            sent += n_
            if n_ != len(s):
                fp.seek(n_ - len(s), os.SEEK_CUR)

    def recvf(self, fp, size=None, timeout=None):
        '''if size is None, recv until empty data'''
        self._tcp.settimeout(timeout)
        recved = 0
        while size is None or recved < size:
            n = (size is not None and size - recved) or 0xffff
            s = self._tcp.recv(n)
            if not s:
                break

            n_ = fp.write(s)
            while n_ != len(s):
                s = s[n_:]
                n_ = fp.write(s)

        self._tcp.settimeout(timeout)

    def rpty(self, cmd, close_wait=0):
        tcpPtyIO(self._tcp, cmd, close_wait=close_wait)

    def lpty(self, eof_break=True):
        tcpRawStdIO(self._tcp, eof_break=eof_break)

    def rmapping(self):
        tcpMappingAgent(self._tcp)

    def lmapping(self, addr_pairs):
        tcpMappingProxy(self._tcp, addr_pairs)

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


def _rpty(net, **args):
    cmd = args['cmd']
    #print 'remote connection: %s:%d' % net.raddr()
    net.rpty(cmd)

def _lpty(net, **args):
    net.lpty()

def _rmapping(net, **args):
    net.rmapping()

def _lmapping(net, **args):
    addr_pairs = args['addr_pairs']
    net.lmapping(addr_pairs)

def tcpPtyIO(tcp, cmd, close_wait=0):
    '''remote execute, I/O from tcp.
    when the connection closed, what child for close_wait seconds. -1: wait until child exits.'''
    tcp_fd = tcp.fileno()

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

def tcpRawStdIO(tcp, eof_break=True):
    '''I/O from tcp.
    eof_break: True, when reached stdin eof, the copy loop will be break.'''
    tcp_fd = tcp.fileno()
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


# ADDR_MAPPING = sid:uint32@ + cmd:uint8 + data:DATA(cmd)
# CMD_CONNECT:uint8 = 1
# CMD_DATA:uint8 = 2
# CMD_CLOSE:uint8 = 3
# DATA(CMD_CONNECT) = host:IPv4 + port:uint16@
# DATA(CMD_DATA) = length:uint16@ + data:string(length)
# DATA() = none:string(0)

CMD_CONNECT = 1
CMD_DATA = 2
CMD_CLOSE = 3

def _packConnect(sid, addr):
    host, port = addr
    return struct.pack('!IB4sH', sid, CMD_CONNECT, socket.inet_aton(socket.gethostbyname(host)), port)

def _unpackConnect(buf, pos):
    n, port = struct.unpack_from('!4sH', buf, pos)
    host = socket.inet_ntoa(n)
    return host, port

def _packData(sid, data):
    return struct.pack('!IBH%us' % (len(data),), sid, CMD_DATA, len(data), data)

def _unpackData(buf, pos):
    length, = struct.unpack_from('!H', buf, pos)
    pos += struct.calcsize('!H')
    data, = struct.unpack_from('%us' % (length,), buf, pos)
    return length, data

def _packClose(sid):
    return struct.pack('!IB', sid, CMD_CLOSE)

def tcpMappingProxy(tcp, addr_pairs):
    '''addr_pairs: [((lhost, lport), (rhost, rport)), ...]'''
    _log.info('tcp port proxy start')
    return _tcpForwardPort(tcp, True, addr_pairs)

def tcpMappingAgent(tcp):
    _log.info('tcp port agent start')
    return _tcpForwardPort(tcp, False, None)

def _tcpForwardPort(tcp, isproxy, addr_pairs):
    rfds = [tcp,]
    lstnMap = {}
    conn2sidMap = {}
    sid2connMap = {}
    sndBuf = SldeBuf()
    rcvBuf = SldeBuf()
    toRecv = rcvBuf.headerSize

    if isproxy:
        assert(addr_pairs)
        who = 'proxy'
        addr_pairs = list(addr_pairs)
        sidgen = 1
        for laddr, raddr in addr_pairs:
            lstn = socket.socket(type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
            lstn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, 'SO_REUSEPORT'):
                lstn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            try:
                _log.info('%s|listen on %s:%u', who, laddr[0], laddr[1])
                lstn.bind(laddr)
                lstnMap[lstn] = raddr
                rfds.append(lstn)
                lstn.listen(5)
            except Exception, msg:
                _log.info('%s|listen failed: %s', who, msg)
                lstn.close()
                for lstn in lstnMap.iterkeys():
                    lstn.close()
                _log.info('%s|exit', who)
                return
    else:
        who = 'agent'

    while True:
        rlist, _, _ = select.select(rfds, [], [], 1)
        for rfd in rlist:
            if rfd == tcp:
                # from remote agent, proto buf
                s = tcp.recv(toRecv)
                if not s:
                    # remote connection is closed, clear
                    _log.info('%s|remote peer closed', who)
                    tcp.close()
                    if isproxy:
                        for lstn in lstnMap.iterkeys():
                            lstn.close()

                    for conn in conn2sidMap.iterkeys():
                        conn.close()

                    _log.info('%s|exit', who)
                    return

                left = rcvBuf.write(s)
                if left is None:
                    # wrong data
                    _log.error('%s|bad data from remote peer', who)

                elif left > 0:
                    # n bytes left
                    toRecv = left

                elif left == 0:
                    # complete proto buf
                    toRecv = rcvBuf.headerSize
                    buf = ctypes.create_string_buffer(rcvBuf.decode())
                    rcvBuf.clear()
                    _log.info('%s|receive a full proto buf from remote peer', who)

                    pos = 0
                    sid, cmd = struct.unpack_from('!IB', buf, pos)
                    pos += struct.calcsize('!IB')

                    if cmd == CMD_CONNECT:
                        # cmd connect
                        assert(not isproxy)
                        assert(sid not in sid2connMap)
                        raddr = _unpackConnect(buf, pos)
                        _log.info('%s|sid->%u|cmd->connect %s:%u', who, sid, raddr[0], raddr[1])
                        
                        # create a new connection
                        conn = socket.socket(type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
                        try:
                            conn.connect(raddr)
                            # append conn info
                            rfds.append(conn)
                            conn2sidMap[conn] = sid
                            sid2connMap[sid] = conn
                        except socket.error, msg:
                            _log.error('%s|connect failed: %s, tell remote peer to close connection', who, msg)
                            conn.close()
                            # tell peer
                            sndBuf.clear()
                            buf = sndBuf.encode(_packClose(sid))
                            tcp.sendall(buf)

                    elif cmd == CMD_DATA and sid in sid2connMap:
                        # cmd send data
                        _log.info('%s|sid->%u|cmd->send data to connection', who, sid)
                        conn = sid2connMap[sid]
                        length, data = _unpackData(buf, pos)
                        assert(len(data) == length)
                        conn.sendall(data)

                    elif cmd == CMD_CLOSE and sid in sid2connMap:
                        # cmd close, remove conn info
                        _log.info('%s|sid->%u|cmd->close connection', who, sid)
                        conn = sid2connMap[sid]
                        rfds.remove(conn)
                        conn2sidMap.pop(conn)
                        sid2connMap.pop(sid)
                        conn.close()

            elif rfd in conn2sidMap:
                # connection socket can be read
                sid = conn2sidMap[rfd]
                s = rfd.recv(0xffff)
                if not s:
                    # connection is closed
                    _log.info('%s|sid->%u|connection closed, tell remote peer to close connection', who, sid)
                    sid = conn2sidMap[rfd]
                    rfds.remove(rfd)
                    conn2sidMap.pop(rfd)
                    sid2connMap.pop(sid)
                    rfd.close()
                    # tell peer
                    sndBuf.clear()
                    buf = sndBuf.encode(_packClose(sid))
                    tcp.sendall(buf)
                else:
                    # tell peer
                    _log.info('%s|sid->%u|receive data from connection, tell remote peer to send data to connection', who, sid)
                    sndBuf.clear()
                    buf = sndBuf.encode(_packData(sid, s))
                    tcp.sendall(buf)
            
            elif rfd in lstnMap:
                # new connection
                assert(isproxy)
                conn, addr = rfd.accept()
                sid = sidgen
                sidgen += 1
                
                _log.info('%s|sid->%u|new connection, tell remote peer to connect %s:%u', who, sid, lstnMap[rfd][0], lstnMap[rfd][1])

                # append conn info
                rfds.append(conn)
                conn2sidMap[conn] = sid
                sid2connMap[sid] = conn

                # tell peer
                sndBuf.clear()
                buf = sndBuf.encode(_packConnect(sid, lstnMap[rfd]))
                tcp.sendall(buf)

            else:
                raise Exception('unknown socket')

class XNet(Net):
    def __init__(self):
        Net.__init__(self)

    def positiveServer(self, host, port, handler=_rpty, **args):
        '''socket <-> pty'''
        while True:
            self.listen(host, port)
            handler(self, **args)
            self.close()

    def positiveClient(self, host, port, handler=_lpty, **args):
        '''stdio <-> socket'''
        self.connect(host, port)
        handler(self, **args)
        self.close()

    def reverseServer(self, host, port, interval=1, handler=_rpty, **args):
        '''socket <-> pty'''
        while True:
            try:
                self.connect(host, port)
                handler(self, **args)
                self.close()
            except socket.error, e:
                #print e
                pass

            time.sleep(interval)

    def reverseClient(self, host, port, handler=_lpty, **args):
        '''stdio <-> socket'''
        self.listen(host, port)
        handler(self, **args)
        self.close()

    def positiveServerThenReverseClient(self, host, port, rhost, rport, **args):
        def psHandler(ps_net):
            def rcHandler(rc_net):
                _copyLoop(read_fd=ps_net.fileno(), write_fd=ps_net.fileno(), read2_fd=rc_net.fileno(), write2_fd=rc_net.fileno())
            
            rc_net = XNet()  # reverse client
            rc_net.reverseClient(rhost, rport, handler=rcHandler)
            del rc_net
        
        self.positiveServer(host, port, handler=psHandler)

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
        keyAddr = {}
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


def _ptyPipe_psrc(args):
    '''positive server <-> reverse client.'''
    ps_host = args['host']  # positive server listen host
    ps_port = args['port']  # positive server listen port
    rs_host = args['rhost']  # reverse server host
    rs_port = args['rport']  # reverse server port
    
    def psHandler(ps_net):
        def rcHandler(rc_net):
            _copyLoop(read_fd=ps_net.fileno(), write_fd=ps_net.fileno(), read2_fd=rc_net.fileno(), write2_fd=rc_net.fileno())
        
        rc_net = XNet()  # reverse client
        rc_net.reverseClient(rs_host, rs_port, handler=rcHandler)
    
    ps_net = XNet()  # positive server
    ps_net.positiveServer(ps_host, ps_port, handler=psHandler)
    del ps_net

def _ptyPipe_ps(args):
    '''positive server.'''
    ps_host = args['host']  # positive server listen host
    ps_port = args['port']  # positive server listen port
    cmd = args['cmd']
    
    def psHandler(ps_net):
        #print 'remote connection: %s:%d' % ps_net.raddr()
        ps_net.rpty(cmd)

    ps_net = XNet()
    ps_net.positiveServer(ps_host, ps_port, handler=psHandler)
    del ps_net

def _ptyPipe_pc(args):
    '''positive client.'''
    ps_host = args['rhost']  # positive server listen host
    ps_port = args['rport']  # positive server listen port

    pc_net = XNet()
    pc_net.positiveClient(ps_host, ps_port)
    del pc_net

def _ptyPipe_rs(args):
    '''reverse server.'''
    rs_host = args['rhost']  # reverse server host
    rs_port = args['rport']  # reverse server port
    cmd = args['cmd']

    def rsHandler(rs_net):
        #print 'remote connection: %s:%d' % rs_net.raddr()
        rs_net.rpty(cmd)

    rs_net = XNet()
    rs_net.reverseServer(rs_host, rs_port, handler=rsHandler)
    del rs_net

def _ptyPipe_rc(args):
    '''reverse client.'''
    rs_host = args['host']  # reverse server host
    rs_port = args['port']  # reverse server port

    rc_net = XNet()
    rc_net.reverseClient(rs_host, rs_port)
    del rc_net

def ptyPipe(env, who, **args):
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

    if env == 'tsM':
        if who == 's':
            _ptyPipe_pc(args)
        elif who == 'M':
            _ptyPipe_psrc(args)
        elif who == 't':
            _ptyPipe_rs(args)
    elif env == 'sMt':
        if who == 's':
            _ptyPipe_pc(args)
        elif who == 'M':
            raise Exception('Not supported')
        elif who == 't':
            _ptyPipe_ps(args)
    elif env == 'tS':
        if who == 'S':
            _ptyPipe_rc(args)
        elif who == 't':
            _ptyPipe_rs(args)
    elif env == 'sT':
        if who == 's':
            _ptyPipe_pc(args)
        elif who == 'T':
            _ptyPipe_ps(args)
    else:
        raise Exception('Not supported')

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

try:
    import SocketServer
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
                    rsp = {'cmd': cmd, 'clients': []}
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
            self.reqs = self.manager.dist()
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

except:
    pass


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

class StopWatch:
    def __init__(self, mode='reset'):
        self._tm = time.time()
        self._mode = mode
        self._logs = {}

    def tell(self):
        return time.time() - self._tm

    def peek(self):
        now = time.time()
        ret = now - self._tm
        self._tm = now
        return ret

    def log(self, key):
        if self._mode == 'reset':
            self._logs[key] = self.reset()
        else:
            self._logs[key] = self.peek()

    def logs(self):
        return self._logs


STX = 2
ETX = 3
LENGTH_SIZE = 2
HEADER_SIZE = LENGTH_SIZE + 1

class SldeBuf:
    '''slde = stx:uint8 + length:uint16@ + data:string(length) + etx:uint8'''
    headerSize = HEADER_SIZE

    def __init__(self):
        self.clear()

    def clear(self):
        self.pos = None
        self.writebuf = None

    def write(self, buf):
        '''write headerSize bytes for first, return next bytes to write.if return None, failed.'''
        if self.pos == None and len(buf) >= self.headerSize:
            stx, length = struct.unpack_from('!BH', buf)
            if stx == STX and length <= 0xffff:
                self.length = length
                left = length + 1
                self.writebuf = ctypes.create_string_buffer(self.headerSize + left)
                ctypes.memmove(self.writebuf, buf, self.headerSize)
                self.pos = self.headerSize
                more = len(buf) - self.headerSize
                if more > 0:
                    buf = buf[more:]
                else:
                    return left
            else:
                return None
        
        left = self.length - self.pos - len(buf) + self.headerSize + 1
        if left < 0:
            # beyond the length
            return None

        ctypes.memmove(ctypes.addressof(self.writebuf) + self.pos, buf, len(buf))
        self.pos += len(buf)
        if left > 0:
            return left

        # write finished.
        magic, = struct.unpack_from('B', self.writebuf, self.headerSize + self.length)
        if magic == ETX:
            self.pos = None
            return 0

        return None

    def decode(self):
        '''when'''
        if self.pos == None and self.writebuf != None:
            return ctypes.string_at(ctypes.addressof(self.writebuf) + self.headerSize, self.length)

    def encode(self, data):
        if len(data) <= 0xffff:
            encodebuf = ctypes.create_string_buffer(len(data) + self.headerSize + 1)
            struct.pack_into('!BH%dsB' % (len(data),), encodebuf, 0, STX, len(data), data, ETX)
            return encodebuf


if __name__ == '__main__':
    import optparse

    op = optparse.OptionParser()
    op.set_usage('%prog <FUNCTION> [options]\n  FUNCTION\tsub function to use (pty/port)')
    #op = optparse.OptionGroup(op, 'pty pipe')
    #op.add_option('-e', '--env', action='store', dest='env', type=str, help='Environment, must be set (tsM/sMt/tS/sT)')
    #op.add_option('-w', '--who', action='store', dest='who', type=str, help='Who, must be set (s/S/t/T/M)')
    op.add_option('-t', '--type', action='store', dest='type', type=str, help='type, positive or reverse, client or server, must be set (pc/ps/rc/rs/psrc)')
    op.add_option('-d', '--daemon', action='store_true', dest='daemon', default=False, help='Run as a daemon process')
    op.add_option('-l', '--local', action='store', dest='laddr', type=str, help='Address of local host, like 0.0.0.0:1234')
    op.add_option('-r', '--remote', action='store', dest='raddr', type=str, help='Address of remote host, like 192.168.1.101:1234')
    op.add_option('-c', '--command', action='store', dest='cmd', type=str, help='Command to be run, when connect')
    op.add_option('-p', '--address-pairs', action='store', dest='addr_pairs', type=str, help='forward port address pairs, like 0.0.0.0:10022,localhost:22;localhost:80,localhost:80')

    #op.add_option_group(opg)

    (opts, args) = op.parse_args()
    if len(sys.argv) < 2:
        op.print_help()
        sys.exit(1)
    
    function = sys.argv[1]
    cmd = opts.cmd
    daemon = opts.daemon
    cstype = opts.type

    if opts.laddr:
        host, port = opts.laddr.split(':')
        port = int(port)
    else:
        host, port = None, None

    if opts.raddr:
        rhost, rport = opts.raddr.split(':')
        rport = int(rport)
    else:
        rhost, rport = None, None

    if opts.addr_pairs:
        addr_pairs = []
        for pair in opts.addr_pairs.split(';'):
            laddr, raddr = pair.split(',')
            _host, _port = laddr.split(':')
            _port = int(_port)
            _rhost, _rport = raddr.split(':')
            _rport = int(_rport)
            addr_pairs.append(((_host, _port), (_rhost, _rport)))
    else:
        addr_pairs = None
    
    if daemon:
        daemonize()

    if 'HOME' in os.environ:
        os.chdir(os.environ['HOME'])

    try:
        if function == 'pty':
            assert(cstype)
            assert(not ((cstype == 'ps' or cstype == 'rs') and not cmd))
            assert(not ((cstype == 'pc' or cstype == 'rs' or cstype == 'psrc') and not opts.raddr))
            assert(not ((cstype == 'ps' or cstype == 'rc' or cstype == 'psrc') and not opts.laddr))

            if cstype == 'pc':
                _net.positiveClient(rhost, rport)
            elif cstype == 'ps':
                _net.positiveServer(host, port, cmd=cmd)
            elif cstype == 'rc':
                _net.reverseClient(host, port)
            elif cstype == 'rs':
                _net.reverseServer(rhost, rport, cmd=cmd)
            elif cstype == 'psrc':
                _net.positiveServerThenReverseClient(host, port, rhost, rport)

        elif function == 'port':
            assert(cstype)
            assert(not ((cstype == 'pc' or cstype == 'rc') and not addr_pairs))
            assert(not ((cstype == 'pc' or cstype == 'rs' or cstype == 'psrc') and not opts.raddr))
            assert(not ((cstype == 'ps' or cstype == 'rc' or cstype == 'psrc') and not opts.laddr))

            if cstype == 'pc':
                _net.positiveClient(rhost, rport, handler=_lmapping, addr_pairs=addr_pairs)
            elif cstype == 'ps':
                _net.positiveServer(host, port, handler=_rmapping)
            elif cstype == 'rc':
                _net.reverseClient(host, port, handler=_lmapping, addr_pairs=addr_pairs)
            elif cstype == 'rs':
                _net.reverseServer(rhost, rport, handler=_rmapping)
            elif cstype == 'psrc':
                _net.positiveServerThenReverseClient(host, port, rhost, rport)

    except AssertionError:
        traceback.print_exc()
        op.print_help()
        sys.exit(1)
