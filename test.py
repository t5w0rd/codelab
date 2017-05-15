#!/usr/bin/env python
#coding:utf-8
import os, sys, time, re, json, socket

import tutils

host = sys.argv[1]
port = int(sys.argv[2])
n = tutils.net()

if len(sys.argv) == 4:
    n.udpNatTrvServer(host, port)
else:
    n.bindu('0.0.0.0', 2889)
    n.udpNatTrv('abc123', host, port)
    n.closeu()
