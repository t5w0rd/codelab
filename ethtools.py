#!/usr/bin/env python

import sys
import socket
import time


class EthRobot:
    def __init__(self, ifname):
        self.ifname = ifname
    

    def startSenderMode(self, interval, pktGenIter):
        sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3))
        if self.ifname:
            sock.bind((self.ifname, 0))

        for pkt in pktGenIter():
            sock.send(pkt)
            time.sleep(interval)

        sock.close()


    def startReceiverMode(self, parser):
        sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3))
        if self.ifname:
            sock.bind((self.ifname, 0))

        while True:
            pkt = sock.recv(0xffff)
            parser(pkt)
            
        sock.close()





def main():
    import dpkt
    import proto
    


if __name__ == '__main__':
    main()
