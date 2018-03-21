#!/usr/bin/env python

__all__ = ['shell']

import os

def shell(cmd):
    pipe = os.popen(cmd)
    out = pipe.read()
    pipe.close()
    return out

