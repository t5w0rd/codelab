#!/usr/bin/env python
#coding=utf-8
import socket
import select
import sys

to_addr = ('build.cthuwork.com', 25565)  #目标服务器地址
#to_addr = ('120.55.166.86', 25565)  #目标服务器地址
class Proxy:
    def __init__(self, addr):
        self.proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.proxy.bind(addr)
        self.proxy.listen(10)
        self.inputs = [self.proxy]
        self.route = {}

    def serve_forever(self):
        print '等待客户端连接...'
        while 1:
            readable, _, _ = select.select(self.inputs, [], [])
            for self.sock in readable:
                if self.sock == self.proxy:
                    self.on_join()
                else:
                    data = self.sock.recv(8192)
                    if not data:
                        self.on_quit()
                    else:
                        if(data.find("WDL|CONTROL") != -1):
                            data=data.replace("WDL|CONTROL", "HRO|HERO123")
                            print "修改:CONTROL"
                        if(data.find("WDL|INIT") != -1):
                            data=data.replace("WDL|INIT", "HRO|HERO")
                            print "修改:INIT"
                        if(data.find("WDL|REQUEST") != -1):
                            data=data.replace("WDL|REQUEST", "HRO|HERO123")
                            print "修改:REQUEST"
                        self.route[self.sock].send(data)

    def on_join(self):
        client, addr = self.proxy.accept()
        print addr, 'connect'
        forward = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        forward.connect(to_addr)
        self.inputs += [client, forward]
        self.route[client] = forward
        self.route[forward] = client

    def on_quit(self):
        for s in self.sock, self.route[self.sock]:
            self.inputs.remove(s)
            del self.route[s]
            s.close()

if __name__ == '__main__':
    try:
        Proxy(('', 25565)).serve_forever()  #本地监听端口
    except KeyboardInterrupt:
        sys.exit(1)
