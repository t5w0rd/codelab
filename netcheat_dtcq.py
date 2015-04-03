#!/usr/bin/env python

from netfw import *
import json


fhdr = 'POST /apimob/login'
jskw = 'Content-Disposition: form-data; name="ticket"\r\n\r\n'
conlen = 'Content-Length: '
def loginhook(data, fromaddr, toaddr, fromissrc):
    tmp = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
    tmp.connect(('127.0.0.1', 8888))
    tmp.send(data)
    tmp.close()

    if data[:len(fhdr)] != fhdr:
        return data
    '''
    start, end = 0
    while True:
        end = data.find('\r\n', start)
        if end < 0:
            break
        start = end + 1
    '''
    begin = data.find(jskw) + len(jskw)
    jd = data[begin:]
    end = begin + jd.find('\r\n')
    #print data
    
    jd = data[begin:end]
    jd = json.loads(jd)
    begins = data[:begin]
    ends = data[end:]
    jd['ticket_sign'] = 'b77beb77ea2e622fc0be94a57621a896'
    jd['ticket_sdata']['data']['username'] = 'sw0rd00'
    jd['ticket_sdata']['data']['password'] = 'lSFmABADXFg5FtVAU9EgQt+F39k7HQJGax09b/uCFr/aObFwrtfSFZKfaS1XVlF3WmYmRoC8TaX+\n1/fuDJyax2C390jrrJZiCBeTjYTglzTnDBCn/tM+wj4P+9je/bnA53NHcqWAA4z/ID77n5U40EHQ\nRHyEMjgxBS14cLkVd44=\n'

    #print json.dumps(jd)

    data2 = begins + json.dumps(jd, sort_keys=True).replace(': ', ':').replace(', ', ',').replace(r'/', r'\/') + ends
    delta = len(data2) - len(data)
    
    cl = data.find(conlen) + len(conlen)
    cls = data[cl:data[cl:].find('\r\n') + cl]
    #print '@@@', len(data[cl + 5:])
    cls2 = str(int(cls) + delta)
    finds = conlen + cls
    replaces = conlen + cls2
    data2 = data2.replace(finds, replaces, 1)
    print data2


    cl = data2.find(conlen) + len(conlen)
    #print '@@@', len(data2[cl + 5:])

    #lines = data.splitlines()
    #print lines
        
    return data2


daddr_login = ('115.28.253.93', 80)
#daddr_login = ('127.0.0.1', 8888)
fwp = FwTcpPort()
fwp.register('0.0.0.0', daddr_login, hook = loginhook)
fwp.start(('0.0.0.0', 2888), reuseaddr = True)

