#!/usr/bin/env python
#coding:utf-8
import os, sys, time, re, json, socket

import tutils

host = sys.argv[1]
port = int(sys.argv[2])

net = tutils.net()
net.connect(host, port)

data = 'GET /app/v1/market/stock_rank?mt=hs&rt=7&num=2 HTTP/1.1\r\nHost: 139.196.228.231:18888\r\nAccept: */*\r\nContent-type: application/json;charset=UTF-8\r\n\r\n'
net.send(data)

data = net.recv()
print data

net.close()
