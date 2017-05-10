#!/usr/bin/env python

import sys
import os
import tutils


try:
    host = sys.argv[1]
    port = int(sys.argv[2])
    rhost = sys.argv[3]
    rport = int(sys.argv[4])
except:
    print 'Usage:\n  %s <pHost> <pPort> <rHost> <rPort>' % (sys.argv[0],)
    sys.exit(1)

tutils.daemonize()
if 'HOME' in os.environ:
    os.chdir(os.environ['HOME'])
tutils.ptyPipe('M', 'tsM', host=host, port=port, rhost=rhost, rport=rport)

