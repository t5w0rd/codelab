#!/usr/bin/env python

import socket
import struct


def ip_ntoa(n):
    '''ip_ntoa(0xc0a8158c) -> '192.168.21.140' '''
    return socket.inet_ntoa(struct.pack('>I', n))


def ip_aton(a):
    '''ip_aton('192.168.21.140') -> 0xc0a8158c '''
    return struct.unpack('>I', socket.inet_aton(a))[0] & 0xffffffff



def mask_cton(c):
    '''mask_cton(21) -> 0xfffff800 '''
    return (0xffffffff << (32 - c)) & 0xffffffff


def mask_ntoc(n):
    '''mask_ntoc(0xfffff800) -> 21 '''
    for c in range(32, 0, -1):
        if mk % (1 << (33 - (c))):
            return c
    return 0


def getnetbynm(ipn, maskn):
    return ipn & maskn & 0xffffffff


def getnetbyam(ip, mask):
    '''getnetbyam('192.168.21.140', '255.255.248.0') -> '192.168.16.0' '''
    return ip_ntoa(getnetbynm(ip_aton(ip), ip_aton(mask)))


def getbcbynm(ipn, maskn):
    return (getnetbynm(ipn, maskn) | (~maskn) & 0xffffffff)


def getbcbyam(ip, mask):
    '''getbcbyam('192.168.21.140', '255.255.248.0') -> '192.168.23.255' '''
    return ip_ntoa(getbcbynm(ip_aton(ip), ip_aton(mask)))


def getipsbynm(ipn, maskn):
    return (getnetbynm(ipn, maskn) | i for i in range(1, (~maskn) & 0xffffffff))


def getipsbyam(ip, mask):
    '''getipsbyam('192.168.21.140', '255.255.248.0') -> ['192.168.16.1', ..., '192.168.23.254'] '''
    return [ip_ntoa(a) for a in getipsbynm(ip_aton(ip), ip_aton(mask))]

