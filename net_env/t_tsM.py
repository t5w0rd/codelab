#!/usr/bin/env python

import sys
import os
import tutils


try:
    host = sys.argv[1]
    port = int(sys.argv[2])
    cmd = sys.argv[3]
except:
    print 'Usage:\n  %s <rHost> <rPort> <cmd>' % (sys.argv[0],)
    sys.exit(1)

tutils.daemonize()
if 'HOME' in os.environ:
    os.chdir(os.environ['HOME'])
tutils.ptyPipe('t', 'tsM', host=host, port=port, cmd=cmd)

