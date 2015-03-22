#!/usr/bin/env python

import os


def shell(cmd):
    pipe = os.popen(cmd)
    out = pipe.read()
    pipe.close()
    return out

