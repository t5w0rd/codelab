#!/usr/bin/env python

import sys
import tutils


try:
    host = sys.argv[1]
    port = sys.argv[2]
    cmd = sys.argv[3]
except:
    print 'Usage:\n  %s <rHost> <rPort> <cmd>' % (sys.argv[0],)
    sys.exit(1)

tutils.daemonize()
tutils.ptyPipe('t', 'tsM', host=host, port=port, cmd=cmd)

