#!/usr/bin/env python

import tutils

tutils.ptyPipe('M', 'tsM', host='0.0.0.0', port=3888, rhost='0.0.0.0', rport=3889)

