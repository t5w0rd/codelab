#!/usr/bin/env python

import sys
import tutils


try:
    host = sys.argv[1]
    port = int(sys.argv[2])
except:
    print 'Usage:\n  %s <rHost> <rPort>' % (sys.argv[0],)
    sys.exit(1)

tutils.ptyPipe('S', 'tS', host=host, port=port)
