#!/usr/bin/env python
#coding:utf-8
import os, sys, time, re, json, socket

import tutils

def test(tm):
    time.sleep(tm)
    return tm

res = tutils.multijobs(test, ((60,), (120,), (150,)), 3)
print res
