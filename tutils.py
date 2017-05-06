#!/usr/bin/env python
#coding=utf-8

import os
import sys
import socket
import tty
import pty
import select


__all__ = ['Net',]

STDIN_FILENO = sys.stdin.fileno()
STDOUT_FILENO = sys.stdout.fileno()
STDERR_FILENO = sys.stderr.fileno()


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
        self._lstn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        self._lstn.bind((host, port))
        self._lstn.listen(1)
        if self._tcp:
            self._tcp.close()
        self._tcp, addr = self._lstn.accept()
        self._lstn.close()
        self._lstn = None

        return addr

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

        ret = ''
        while len(ret) < size or not size:
            try:
                s = self._tcp.recv(0xffff)
                if not s:
                    break

                ret += s

            except socket.timeout:
                break

        self._tcp.settimeout(None)
        return ret

    def connect(self, host, port, lhost = '0.0.0.0', lport = 0):
        '''connect remote host'''
        if self._tcp:
            self._tcp.close()
        
        self._tcp = socket.socket(type=socket.SOCK_STREAM)
        self._tcp.bind((lhost, lport))
        self._tcp.connect((host, port))

    def close(self):
        '''close the tcp socket'''
        self._tcp.close()
        self._tcp = None
        
    def rpty(self, cmd):
        '''remote execute, I/O from tcp'''
        tcp_fd = self._tcp.fileno()

        pid, master_fd = pty.fork()
        if pid == 0:
            if type(cmd) == str:
                cmd = cmd.split()
            os.execvp(cmd[0], cmd)

        try:
            _swap(read_fd=master_fd, write_fd=master_fd, read2_fd=tcp_fd, write2_fd=tcp_fd)
        except (IOError, OSError):
            pass

        #s.wait()
        os.close(master_fd)

    def lpty(self):
        '''I/O from tcp'''
        tcp_fd = self._tcp.fileno()
        restore = 0
        try:
            mode = tty.tcgetattr(STDIN_FILENO)
            tty.setraw(STDIN_FILENO)
            restore = 1
        except tty.error:    # This is the same as termios.error
            pass
        
        try:
            _swap(read_fd=tcp_fd, write_fd=tcp_fd)
        except (IOError, OSError):
            pass
        finally:
            if restore:
                tty.tcsetattr(STDIN_FILENO, tty.TCSAFLUSH, mode)
        

def _write(fd, data):
    """Write all the data to a descriptor."""
    while data != '':
        n = os.write(fd, data)
        data = data[n:]

def _read(fd):
    """Default read function."""
    return os.read(fd, 1024)

def _swap(read_fd, write_fd, read2_fd=STDIN_FILENO, write2_fd=STDOUT_FILENO, read_func=_read, write_func=_write, read2_func=_read, write2_func=_write):
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
                break
                #fds.remove(read_fd)
            else:
                write2_func(write2_fd, data)

        if read2_fd in rfds:
            data = read2_func(read2_fd)
            if not data:
                break
                #fds.remove(read2_fd)
            else:
                write_func(write_fd, data)


_net = Net()

def net():
    return _net


