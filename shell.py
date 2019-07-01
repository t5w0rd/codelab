#!/usr/bin/env python

__all__ = ['shell']

import os

def shell(cmd):
    with os.popen(cmd) as pipe:
        out = pipe.read()
        return out

