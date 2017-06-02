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
import ctypes
import struct
import tempfile
import pickle
import urlparse
import collections
import errno
import base64
import zlib

import traceback


__all__ = ['net', 'XNet', 'tcpPtyIO', 'tcpRawStdIO', 'tcpMapProxy', 'tcpMapAgent', 'daemonize', 'multijobs', 'initLogger', 'StopWatch', 'SldeBuf', 'writeAttachData', 'readAttachData', 'shell']


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

    def rmap(self):
        tcpMapAgent(self._tcp)

    def lmap(self, mapping):
        tcpMapProxy(self._tcp, mapping)

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

def _rmap(net, **args):
    net.rmap()

def _lmap(net, **args):
    mapping = args['mapping']
    net.lmap(mapping)

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
# CMD_ALIVE:uint8 = 0
# CMD_CONNECT:uint8 = 1
# CMD_DATA:uint8 = 2
# CMD_CLOSE:uint8 = 3
# DATA(CMD_CONNECT) = host:IPv4 + port:uint16@
# DATA(CMD_DATA) = length:uint16@ + data:string(length)
# DATA() = none:string(0)

CMD_ALIVE = 0
CMD_CONNECT = 1
CMD_DATA = 2
CMD_CLOSE = 3
ALIVE_INTERVAL = 30
HOST_HTTP_PROXY = '{http}'

def _packAlive():
    return struct.pack('!IB', 0, CMD_ALIVE)

def _packConnect(sid, addr):
    host, port = addr
    lenHost = len(host)
    return struct.pack('!IBH%usH' % (lenHost,), sid, CMD_CONNECT, lenHost, host, port)

def _unpackConnect(buf, pos):
    lenHost, = struct.unpack_from('!H', buf, pos)
    pos += struct.calcsize('!H')
    host, port = struct.unpack_from('!%usH' % (lenHost,), buf, pos)
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

def tcpMapProxy(tcp, mapping):
    '''mapping: [((lhost, lport), (rhost, rport)), ...]'''
    _log.info('tcp port proxy start')
    return _tcpAddressMapping(tcp, True, mapping)

def tcpMapAgent(tcp):
    _log.info('tcp port agent start')
    return _tcpAddressMapping(tcp, False, None)

def _tcpAddressMapping(tcp, isproxy, mapping):
    rfds = [tcp,]
    wfds = []
    lstnMap = {}
    conn2sidMap = {}
    sid2connMap = {}
    connPendMap = {}  # sid: (sid, raddr, queue, tmConn)
    #tcpSndQueue = collections.deque()
    #tcpSndPend = False
    sndBuf = SldeBuf()
    rcvBuf = SldeBuf()
    toRecv = rcvBuf.headerSize

    tcp.settimeout(5)
    def clearAndExit():
        tcp.close()
        if isproxy:
            for lstn in lstnMap.iterkeys():
                lstn.close()

        for conn in connPendMap.iterkeys():
            conn.close()

        for conn in conn2sidMap.iterkeys():
            conn.close()
        _log.info('%s|exit', who)
    '''
    def tcpSend(data):
        if tcpSndPend:
            tcpSndQueue.append(data)
            return
        try:
            tcp.sendall(data)
            while len(tcpSndQueue):
                data = tcpSndQueue[0]
                tcp.sendall(data)
                tcpSndQueue.popleft()
            tcpSndPend = False
        except socket.error, e:
            assert(e.errno == errno.EAGAIN)
            tcpSndPend = True
            tcpSndQueue.append(data)
            wfds.append(tcp)
    '''
    def sendall(sock, data):
        try:
            sock.sendall(data)
            return 0
        except socket.error, e:
            if sock is tcp:
                raise e
            else:
                sid = conn2sidMap[sock]
                if e.errno == errno.EPIPE:
                    rfds.remove(sock)
                    conn2sidMap.pop(sock)
                    sid2connMap.pop(sid)
                    sock.close()
                elif e.errno is None:
                    # timed out
                    _log.error('%s|sid->%u|send data timeout', who, sid)
                    pass
                else:
                    raise e
            return e.errno

    if isproxy:
        assert(mapping)
        who = 'proxy'
        mapping = list(mapping)
        sidgen = 1
        for laddr, raddr in mapping:
            lstn = socket.socket(type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
            lstn.settimeout(5)
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
                _log.error('%s|listen failed: %s', who, msg)
                lstn.close()
                clearAndExit()
                return
    else:
        who = 'agent'

    now = time.time()
    tmAlive = now  # the time of last recv CMD_ALIVE
    tmSndAlive = now  # the time of last send CMD_ALIVE
    while True:
        rlist, wlist, _ = select.select(rfds, wfds, [], 1)
        now = time.time()
        for wfd in wlist:
            if wfd in connPendMap:
                # remove conn pending info
                sid, raddr, queue, tmConn = connPendMap.pop(wfd)
                wfds.remove(wfd)
                
                # connect again for check nonblock connect result
                res = wfd.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                if res == 0:
                    # connect succ, append conn info, and send data from queue
                    wfd.settimeout(5)
                    _log.info('%s|sid->%u|connect(nonblocking) %s:%u successfully, send data from queue|queue->%u', who, sid, raddr[0], raddr[1], len(queue))
                    rfds.append(wfd)
                    conn2sidMap[wfd] = sid

                    while len(queue):
                        data = queue.popleft()
                        res = sendall(wfd, data)
                else:
                    _log.error('%s|sid->%u|connect(nonblocking) failed: %s(%d), tell remote peer to close connection', who, sid, os.strerror(res), res)
                    wfd.close()
                    sid2connMap.pop(sid)

                    # tell peer
                    sndBuf.clear()
                    buf = sndBuf.encode(_packClose(sid))
                    res = sendall(tcp, buf)
            elif wfd == tcp or wfd in conn2sidMap:
                pass

        closedFds = set()
        for rfd in rlist:
            if rfd in closedFds:
                # closed
                continue

            if rfd == tcp:
                # from remote agent, proto buf
                try:
                    s = tcp.recv(toRecv)
                except socket.error:
                    s = None
                if not s:
                    # remote connection is closed, clear
                    _log.info('%s|remote peer closed', who)
                    clearAndExit()
                    return

                left = rcvBuf.write(s)
                if left is None:
                    # wrong data
                    _log.error('%s|bad data from remote peer', who)
                    rcvBuf.clear()

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

                    if cmd == CMD_ALIVE:
                        tmAlive = now
                        _log.info('%s|remote peer is alive', who)
                    elif cmd == CMD_CONNECT:
                        # cmd connect
                        assert(not isproxy)
                        assert(sid not in sid2connMap)
                        raddr = _unpackConnect(buf, pos)
                        _log.info('%s|sid->%u|cmd->connect %s:%u', who, sid, raddr[0], raddr[1])
                        
                        # create a new connection
                        conn = socket.socket(type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
                        try:
                            conn.settimeout(0)
                            res = conn.connect_ex(raddr)
                            assert(res == errno.EINPROGRESS)

                            # nonblocking IO: append conn pending info
                            wfds.append(conn)
                            connPendMap[conn] = (sid, raddr, collections.deque(), now)
                            sid2connMap[sid] = conn

                            # blocking IO: append conn info
                            #rfds.append(conn)
                            #conn2sidMap[conn] = sid
                            #sid2connMap[sid] = conn
                        except socket.error, msg:
                            raise socket.error(msg)
                            # blocking IO: connect failed
                            #_log.error('%s|sid->%u|connect failed: %s, tell remote peer to close connection', who, sid, msg)
                            #conn.close()
                            # tell peer
                            #sndBuf.clear()
                            #buf = sndBuf.encode(_packClose(sid))
                            #res = sendall(tcp, buf)

                    elif cmd == CMD_DATA and sid in sid2connMap:
                        # cmd send data
                        _log.info('%s|sid->%u|cmd->send data to connection', who, sid)
                        conn = sid2connMap[sid]
                        length, data = _unpackData(buf, pos)
                        assert(len(data) == length)
                        if conn in connPendMap:
                            # connect is pending
                            _, _, queue, _ = connPendMap[conn]
                            queue.append(data)
                        else:
                            res = sendall(conn, data)

                    elif cmd == CMD_CLOSE and sid in sid2connMap:
                        # cmd close, remove conn info
                        _log.info('%s|sid->%u|cmd->close connection', who, sid)
                        conn = sid2connMap[sid]
                        conn.close()
                        sid2connMap.pop(sid)
                        if conn in connPendMap:
                            # connect is pending
                            wfds.remove(conn)
                            connPendMap.pop(conn)
                        else:
                            rfds.remove(conn)
                            closedFds.add(conn)
                            conn2sidMap.pop(conn)

            elif rfd in conn2sidMap:
                # connection socket can be read
                sid = conn2sidMap[rfd]
                try:
                    s = rfd.recv(0xffff)
                except socket.error:
                    s = None
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
                    res = sendall(tcp, buf)
                else:
                    # tell peer
                    _log.info('%s|sid->%u|receive data from connection, tell remote peer to send data to connection', who, sid)
                    sndBuf.clear()
                    buf = sndBuf.encode(_packData(sid, s))
                    res = sendall(tcp, buf)
            
            elif rfd in lstnMap:
                # new connection
                assert(isproxy)
                rhost, rport = lstnMap[rfd]
                conn, addr = rfd.accept()
                conn.settimeout(5)
                sid = sidgen
                sidgen += 1

                isHttpProxy = rhost == HOST_HTTP_PROXY
                method = None
                
                if isHttpProxy:
                    # http proxy connection, recv http header, get host name and fix http header
                    try:
                        httpHeader = conn.recv(0xffff)
                        # get host name and fix http header
                        httpHeaderLines = httpHeader.splitlines(True)
                        httpHeader = ''
                        for index, line in enumerate(httpHeaderLines):
                            proxyConnection = False
                            if index == 0:
                                # parse host and port from url
                                res = line.split()
                                method = res[0]
                                if method == 'CONNECT':
                                    raddr = res[1]
                                    res = raddr.split(':')
                                    rhost = res[0]
                                    rport = len(res) >= 2 and int(res[1]) or 443
                                    #break
                                else:
                                    url = res[1]
                                    res = urlparse.urlsplit(url)
                                    rhost = res.hostname or rhost
                                    rport = res.port or 80
                            if rhost == HOST_HTTP_PROXY and line.find('Host: ') == 0:
                                # host
                                raddr = line[len('Host: '):].rstrip()
                                res = raddr.split(':')
                                rhost = res[0]
                                rport = len(res) == 2 and int(res[1]) or 80
                            elif line.find('Proxy-Connection: ') == 0:
                                # Proxy-Connection skip
                                proxyConnection = True
                                #httpHeaderLines[index] = line.replace('Proxy-Connection: ', 'Connection: ', 1)
                            if not proxyConnection:
                                httpHeader += line
                        assert(rhost != HOST_HTTP_PROXY and rport != 0)
                        _log.info('%s|sid->%u|new http proxy connection, tell remote peer to request %s:%u', who, sid, rhost, rport)
                    except socket.error, e:
                        _log.error('%s|sid->%u|new http proxy connection, recv http header failed: %s, may be droped by fire wall', who, sid, e)
                        conn.close()
                        conn = None
                    except AssertionError:
                        _log.error('%s|sid->%u|new http proxy connection, parse host failed', who, sid)
                        conn.close()
                        conn = None
                else:
                    # normal connection
                    _log.info('%s|sid->%u|new connection, tell remote peer to connect %s:%u', who, sid, rhost, rport)

                if conn:
                    # append conn info
                    rfds.append(conn)
                    conn2sidMap[conn] = sid
                    sid2connMap[sid] = conn

                    # tell peer
                    sndBuf.clear()
                    buf = sndBuf.encode(_packConnect(sid, (rhost, rport)))
                    res = sendall(tcp, buf)

                    if isHttpProxy:
                        #print httpHeader
                        if method == 'CONNECT':
                            # send conn established
                            data = 'HTTP/1.1 200 Connection Established\r\nProxy-Agent: tutils/1.0\r\n\r\n'
                            res = sendall(conn, data)

                        else:
                            # tell peer
                            sndBuf.clear()
                            buf = sndBuf.encode(_packData(sid, httpHeader))
                            res = sendall(tcp, buf)
            else:
                raise Exception('unknown socket')
            
        # timeout
        tmSndAliveDelta = now - tmSndAlive
        if tmSndAliveDelta >= ALIVE_INTERVAL:
            # tell peer
            sndBuf.clear()
            buf = sndBuf.encode(_packAlive())
            res = sendall(tcp, buf)
            tmSndAlive = now

        tmAliveDelta = now - tmAlive
        if tmAliveDelta > ALIVE_INTERVAL * 2:
            _log.error('%s|remote is not alive' % who)
            clearAndExit()
            return

class XNet(Net):
    def __init__(self):
        Net.__init__(self)

    def positiveServer(self, host, port, handler=_rpty, loop=True, **args):
        '''socket <-> pty'''
        while True:
            self.listen(host, port)
            handler(self, **args)
            self.close()

            if not loop:
                break

    def positiveClient(self, host, port, handler=_lpty, loop=False, interval=1, **args):
        '''stdio <-> socket'''
        while True:
            try:
                self.connect(host, port)
                handler(self, **args)
                self.close()
            except socket.error, e:
                #print e
                pass
            
            if not loop:
                break

            time.sleep(interval)

    def reverseServer(self, host, port, handler=_rpty, loop=True, interval=1, **args):
        '''socket <-> pty'''
        while True:
            try:
                self.connect(host, port)
                handler(self, **args)
                self.close()
            except socket.error, e:
                #print e
                pass

            if not loop:
                break

            time.sleep(interval)

    def reverseClient(self, host, port, handler=_lpty, loop=False, **args):
        '''stdio <-> socket'''
        while True:
            self.listen(host, port)
            handler(self, **args)
            self.close()

            if not loop:
                break

    def positiveServerThenPositiveClient(self, host, port, rhost, rport, loop=True, **args):
        def psHandler(ps_net):
            def rcHandler(rc_net):
                _copyLoop(read_fd=ps_net.fileno(), write_fd=ps_net.fileno(), read2_fd=rc_net.fileno(), write2_fd=rc_net.fileno())
            
            rc_net = XNet()  # reverse client
            rc_net.reverseClient(rhost, rport, handler=rcHandler, loop=loop)
            del rc_net
        
        self.positiveServer(host, port, handler=psHandler, loop=loop)

    def positiveServerThenReverseClient(self, host, port, rhost, rport, loop=True, **args):
        def psHandler(ps_net):
            def pcHandler(pc_net):
                _copyLoop(read_fd=ps_net.fileno(), write_fd=ps_net.fileno(), read2_fd=pc_net.fileno(), write2_fd=pc_net.fileno())
            
            pc_net = XNet()  # reverse client
            pc_net.positiveClient(rhost, rport, handler=pcHandler, loop=loop)
            del pc_net
        
        self.positiveServer(host, port, handler=psHandler, loop=loop)
    
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

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(stdin, 'r')
        so = file(stdout, 'a+')
        se = file(stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())
    except OSError, e: 
        sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
        sys.exit(1)

            
def hideArgvs(stdin='/dev/null', stdout='/dev/null', stderr='/dev/null', keepwd=False):
    """
    do the UNIX double-fork magic, see Stevens' "Advanced 
    Programming in the UNIX Environment" for details (ISBN 0201563177)
    http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
    """

    me = os.path.abspath(sys.argv[0])
    try:
        pid = os.fork()
        if pid > 0:
            # exit first parent
            os._exit(0)
    except OSError, e: 
        sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
        os._exit(1)

    # decouple from parent environment
    if not keepwd:
        os.chdir("/")
    os.setsid()
    os.umask(0)

    # do second fork
    try: 
        env = dict(os.environ)
        fd, env['tmpfile'] = tempfile.mkstemp()
        sys_argv = list(sys.argv)
        if '-H' in sys_argv:
            sys_argv.remove('-H')
        if '-hide' in sys_argv:
            sys_argv.remove('--hide')
        sys_argv = pickle.dumps(sys_argv)
        os.write(fd, sys_argv)
        os.close(fd)

        pid = os.fork()
        if pid > 0:
            # exit from second parent
            os._exit(0)

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(stdin, 'r')
        so = file(stdout, 'a+')
        se = file(stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())
        os.execve(me, (me,), env)
        os._exit(0)
    except OSError, e: 
        sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
        os._exit(1)

def checkHideArgvs():
    if 'tmpfile' not in os.environ:
        return

    tmpfile = os.environ['tmpfile']
    fp = file(tmpfile, 'rb')
    sys_argv = pickle.load(fp)
    fp.close()
    os.remove(tmpfile)
    sys.argv = sys_argv

def multijobs(target, argslist, workers=None):
    if not workers:
        workers = multiprocessing.cpu_count()
    workers = min(len(argslist), workers)
    msgq = multiprocessing.Queue()

    # target wapper
    def worker(target, args):
        res = target(*args)
        pid = os.getpid()
        msgq.put((pid, res))

    # add proc to waiting
    waiting = collections.deque()
    for args in argslist:
        args_wapper = [target, args]
        proc = multiprocessing.Process(target=worker, args=args_wapper)
        waiting.append(proc)

    seq = []
    running = set()
    results = {}
    dataNum = 1
    while True:
        # move proc from waiting to running
        for i in xrange(max(0, min(len(waiting), workers - len(running)))):
            proc = waiting.popleft()
            running.add(proc)
            proc.start()
            seq.append(proc.pid)

        if len(running) == 0:
            break

        # if len(running) > 0, wait for blocking msgq.get() instead of time.sleep()
        for i in xrange(dataNum):
            pid, res = msgq.get()
            results[pid] = res
        dataNum = 0

        # check proc is alive or not
        dead = []
        for proc in running:
            if not proc.is_alive():
                dead.append(proc)
                
        # remove dead proc from running
        for proc in dead:
            running.remove(proc)
            proc.join()
            dataNum += 1

    # put msgq data left to results map
    while not msgq.empty():
        pid, res = msgq.get()
        results[pid] = res
    msgq.close()

    # collect retults of child proc
    ret = []
    for pid in seq:
        ret.append(results[pid])

    return ret

def writeAttachData(fn, header, text, end_offset=-1024):
    with file(fn, 'rb+') as fp:
        fp.seek(0, os.SEEK_END)
        size = fp.tell()
        off = max(-size, min(0, end_offset))
        fp.seek(off, os.SEEK_END)
        s = fp.read()
        pos = s.find(header)
        if pos >= 0:
            fp.seek(off + pos, os.SEEK_END)

        fp.write(header)
        fp.write(text)
        fp.truncate()

def readAttachData(fn, header, end_offset=-1024):
    with file(fn, 'rb') as fp:
        fp.seek(0, os.SEEK_END)
        size = fp.tell()
        off = max(-size, min(0, end_offset))
        fp.seek(off, os.SEEK_END)
        s = fp.read()
        pos = s.find(header)
        if pos >= 0:
            return s[pos + len(header):]

    return None

def shell(cmd):
    with os.popen(cmd) as pipe:
        return pipe.read()

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
LENGTH_SIZE = 4
HEADER_SIZE = LENGTH_SIZE + 1

class SldeBuf:
    '''slde = stx:uint8 + length:uint16@ + data:string(length) + etx:uint8'''
    headerSize = HEADER_SIZE

    def __init__(self, bufsize=0x100000):
        self.writebuf = ctypes.create_string_buffer(bufsize)
        self.clear()

    def clear(self):
        self.pos = None
        self.length = None

    def write(self, buf):
        '''write headerSize bytes for first, return next bytes to write.if return None, failed.'''
        n = len(buf)
        if self.pos is None:
            self.pos = 0

        ctypes.memmove(ctypes.addressof(self.writebuf) + self.pos, buf, n)
        self.pos += n

        if self.pos < self.headerSize:
            return self.headerSize - self.pos

        stx, length = struct.unpack_from('!BI', self.writebuf, 0)
        if stx != STX:
            return None

        self.length = length
        left = self.headerSize - self.pos + length + 1
        if left > 0:
            return left
        
        # write finished
        magic, = struct.unpack_from('B', self.writebuf, self.headerSize + self.length)
        if magic != ETX:
            return None

        self.pos = None
        return 0

    def decode(self):
        '''when'''
        if self.pos == None:
            ret = ctypes.string_at(ctypes.addressof(self.writebuf) + self.headerSize, self.length)  #.decode('base64')
            ret = zlib.decompress(ret)
            #print `ret`
            return base64.decodestring(ret)

    def encode(self, data):
        #data = data.encode('base64')
        data = base64.encodestring(data)
        data = zlib.compress(data)
        encodebuf = ctypes.create_string_buffer(len(data) + self.headerSize + 1)
        struct.pack_into('!BI%usB' % (len(data),), encodebuf, 0, STX, len(data), data, ETX)
        return encodebuf

try:
    import paramiko
except:
    pass

def _sshExecWorker(host, port, user, passwd, cmd):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=user, password=passwd)
    stdin, stdout, stderr = ssh.exec_command(cmd)
    ret = stdout.read(), stderr.read()
    ssh.close()
    return ret

def encode(s):
    return zlib.compress(base64.encodestring(s))

def decode(s):
    return base64.decodestring(zlib.decompress(s))

AD_HEADER = '\xfa\x05\xa1\x9c\x2f\xed\x50\x3e'

'''\
usage:
    ./tutils.py genargvs file_name argvs...
    ./tutils.py file_name
    ./tutils.py genargvs {self} argvs...
    ./tutils.py

bash_mfrjobd=`ps aux|grep mfrjobd|grep -v grep|awk '{print $2}'`
if [ -z "$bash_mfrjobd" ]; then
    mfrjobd
fi
'''
if __name__ == '__main__':
    me = os.path.abspath(sys.argv[0])
    if not os.path.exists(me):
        res = shell('which %s' % (sys.argv[0],)).rstrip()
        if os.path.exists(res):
            me = res

    if len(sys.argv) == 1:
        attachData = readAttachData(me, AD_HEADER)
        if attachData is not None:
            sys.argv.append('{self}')

    if len(sys.argv) >= 2 and sys.argv[1] not in ('pty', 'map', 'sshexec'):
        if sys.argv[1] == 'genargvs' and len(sys.argv) > 3:
            # generate argvs file
            s = pickle.dumps(sys.argv[3:])
            s = encode(s)
            if sys.argv[2] == '{self}':
                fn = me
                writeAttachData(fn, AD_HEADER, s)
            else:
                fn = sys.argv[2]
                with file(fn, 'wb') as fp:
                    fp.write(s)
            sys.exit(0)
        
        if sys.argv[1] == '{self}' and attachData is not None or os.path.exists(sys.argv[1]):
            # load argvs file
            if sys.argv[1] == '{self}':
                keep = True
                s = attachData
            else:
                fn = sys.argv[1]
                keep = len(sys.argv) == 3 and sys.argv[2] == 'keep'
                with file(fn, 'rb') as fp:
                    s = fp.read()
                if not keep:
                    os.remove(fn)

            s = decode(s)
            sys_argv = pickle.loads(s)
            sys_argv.insert(0, sys.argv[0])
            sys.argv = sys_argv


    import optparse

    op = optparse.OptionParser()
    op.set_usage('%prog <FUNCTION> [options]\n  FUNCTION\tsub function to use (pty/map/sshexec/genargvs)')
    #op = optparse.OptionGroup(op, 'pty pipe')
    #op.add_option('-e', '--env', action='store', dest='env', type=str, help='Environment, must be set (tsM/sMt/tS/sT)')
    #op.add_option('-w', '--who', action='store', dest='who', type=str, help='Who, must be set (s/S/t/T/M)')
    op.add_option('-t', '--type', action='store', dest='type', type=str, help='type, positive or reverse, client or server, must be set (pc/ps/rc/rs/pspc/psrc)')
    op.add_option('-l', '--local', action='store', dest='laddr', type=str, help='Address of local host, like 0.0.0.0:1234')
    op.add_option('-r', '--remote', action='store', dest='raddr', type=str, help='Address of remote host, like 192.168.1.101:1234')
    op.add_option('-c', '--command', action='store', dest='cmd', type=str, help='Command to be run, when connect')
    op.add_option('-m', '--mapping', action='store', dest='mapping', type=str, help='Address mapping pairs, like "0.0.0.0:10022,localhost:22,,localhost:8080,{http}"')
    op.add_option('-d', '--daemon', action='store_true', dest='daemon', default=False, help='Run as a daemon process')
    #op.add_option('-H', '--hide', action='store_true', dest='hide_argvs', default=False, help='Hide runtime argvs')
    op.add_option('-L', '--loop', action='store_true', dest='loop', default=False, help='Client or server will loop forever')
    op.add_option('-u', '--user', action='store', dest='user', help='Username')
    op.add_option('-p', '--passwd', action='store', dest='passwd', help='Password')
    op.add_option('-a', '--address-list', action='store', dest='raddrs', type=str, help='Remote address list, like "111.2.3.4:22,222.3.4.5:22"')

    #op.add_option_group(opg)

    (opts, args) = op.parse_args()
    if len(args) < 1:
        op.print_help()
        sys.exit(1)
    
    function = args[0]
    cmd = opts.cmd
    daemon = opts.daemon
    #hide_argvs = opts.hide_argvs
    loop = opts.loop
    passwd = opts.passwd
    user = opts.user
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

    if opts.mapping:
        mapping = []
        for pair in opts.mapping.split(',,'):
            laddr, raddr = pair.split(',')
            _host, _port = laddr.split(':')
            _port = int(_port)
            res = raddr.split(':')
            if len(res) == 2:
                _rhost, _rport = res
                _rport = int(_rport)
            elif len(res) == 1 and res[0] == HOST_HTTP_PROXY:
                _rhost, = res
                _rport = 0
            else:
                assert(False)
            mapping.append(((_host, _port), (_rhost, _rport)))
    else:
        mapping = None

    if opts.raddrs:
        raddrs = []
        for raddr in opts.raddrs.split(','):
            _host, _port = raddr.split(':')
            _port = int(_port)
            raddrs.append((_host, _port))
    else:
        raddrs = None
    
    #if hide_argvs:
    #    # hide runtime command line argvs and daemonize
    #    hideArgvs()
    if daemon:
        daemonize()


    if 'HOME' in os.environ:
        os.chdir(os.environ['HOME'])

    try:
        if function == 'pty':
            assert(cstype)
            assert(not ((cstype == 'ps' or cstype == 'rs') and not cmd))
            assert(not ((cstype == 'pc' or cstype == 'rs' or cstype == 'pspc' or cstype == 'psrc') and not opts.raddr))
            assert(not ((cstype == 'ps' or cstype == 'rc' or cstype == 'pspc' or cstype == 'psrc') and not opts.laddr))

            if cstype == 'pc':
                _net.positiveClient(rhost, rport, loop=loop)
            elif cstype == 'ps':
                _net.positiveServer(host, port, loop=loop, cmd=cmd)
            elif cstype == 'rc':
                _net.reverseClient(host, port, loop=loop)
            elif cstype == 'rs':
                _net.reverseServer(rhost, rport, loop=loop, cmd=cmd)
            elif cstype == 'pspc':
                _net.positiveServerThenPositiveClient(host, port, rhost, rport, loop=loop)
            elif cstype == 'psrc':
                _net.positiveServerThenReverseClient(host, port, rhost, rport, loop=loop)

        elif function == 'map':
            assert(cstype)
            assert(not ((cstype == 'pc' or cstype == 'rc') and not mapping))
            assert(not ((cstype == 'pc' or cstype == 'rs' or cstype == 'pspc' or cstype == 'psrc') and not opts.raddr))
            assert(not ((cstype == 'ps' or cstype == 'rc' or cstype == 'pspc' or cstype == 'psrc') and not opts.laddr))

            if cstype == 'pc':
                _net.positiveClient(rhost, rport, handler=_lmap, loop=loop, mapping=mapping)
            elif cstype == 'ps':
                _net.positiveServer(host, port, handler=_rmap, loop=loop)
            elif cstype == 'rc':
                _net.reverseClient(host, port, handler=_lmap, loop=loop, mapping=mapping)
            elif cstype == 'rs':
                _net.reverseServer(rhost, rport, handler=_rmap, loop=loop)
            elif cstype == 'pspc':
                _net.positiveServerThenPositiveClient(host, port, rhost, rport, loop=loop)
            elif cstype == 'psrc':
                _net.positiveServerThenReverseClient(host, port, rhost, rport, loop=loop)

        elif function == 'sshexec':
            assert(paramiko)
            assert(raddrs)
            assert(user and passwd)
            argslist = []
            for host, port in raddrs:
                argslist.append((host, port, user, passwd, cmd))
            res = multijobs(_sshExecWorker, argslist, workers=len(argslist))
            for out, err in res:
                sys.stdout.write(out)
                if err:
                    sys.stdout.write(err)
            sys.stdout.flush()
        else:
            assert(not 'unsupported FUNCTION')

    except AssertionError:
        traceback.print_exc()
        op.print_help()
        sys.exit(1)

