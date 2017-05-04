#!/usr/bin/env python

import os
import sys
import socket
import subprocess


class Net:
    __lstn = None
    __tcp = None
    __udp = None  #socket.socket(type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP)

    def __init__(self):
        pass

    def listen(self, host, port):
        '''return the address of the connection.'''
        self.__lstn = socket.socket(type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
        self.__lstn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__lstn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        self.__lstn.bind((host, port))
        self.__lstn.listen(1)
        if self.__tcp:
            self.__tcp.close()
        self.__tcp, addr = self.__lstn.accept()
        self.__lstn.close()
        self.__lstn = None

        return addr

    def send(self, s):
        '''send a string or iterable strings; return the number of bytes sent.'''
        c = 0
        if isinstance(s, str):
            m = len(s)
            while c < m:
                n = self.__tcp.send(s[c:])
                c += n
        elif hasattr(s, '__iter__'):
            c = 0
            for seg in s:
                n = self.send(seg)
                c += n

        return c

    def recv(self, size=None, timeout=None):
        '''return bytes received.'''
        self.__tcp.settimeout(timeout)

        ret = ''
        while len(ret) < size or not size:
            try:
                s = self.__tcp.recv(0xffff)
                if not s:
                    break

                ret += s

            except socket.timeout:
                break

        self.__tcp.settimeout(None)
        return ret

    def connect(self, host, port, lhost = '0.0.0.0', lport = 0):
        '''connect remote host'''
        if self.__tcp:
            self.__tcp.close()
        
        self.__tcp = socket.socket(type=socket.SOCK_STREAM)
        self.__tcp.bind((lhost, lport))
        self.__tcp.connect((host, port))

    def close(self):
        '''close the tcp socket'''
        self.__tcp.close()
        self.__tcp = None
        
    def redirect(self, cmd):
        child = subprocess.Popen(cmd, shell=False, stdin=self.__tcp, stdout=self.__tcp, stderr=self.__tcp)
        child.wait()

__net = Net()

def defaultNet():
    return __net


