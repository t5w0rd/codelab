#!/usr/bin/env python

import tutils

tutils.ptyPipe('t', 'tsM', host='45.77.23.212', port=3889, cmd='ssh dev@10.9.19.249 -p 22')
