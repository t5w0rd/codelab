#!/usr/bin/env python
#coding:utf-8
import os, sys, time, re, json, socket

import tutils
n = tutils.net()
n.bindu('0.0.0.0', 0)
n.udpNatTrv('abc123', 'localhost', 2888)
n.closeu()
