#!/usr/bin/env python

import sys
import tutils


try:
    host = sys.argv[1]
    port = sys.argv[2]
    rhost = sys.argv[3]
    rport = sys.argv[4]
except:
    print 'Usage:\n  %s <pHost> <pPort> <rHost> <rPort>' % (sys.argv[0],)
    sys.exit(1)

tutils.daemonize()
tutils.ptyPipe('M', 'tsM', host=host, port=port, rhost=host, rport=port)

