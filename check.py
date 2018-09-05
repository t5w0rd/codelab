#!/usr/bin/env python
#coding:utf-8

import socket
import time
import json
import redis

class BaseChecker:
    #override
    def __init__(self, params):
        pass

    def check(self):
        return 'UNKNOWN'


class TCPChecker(BaseChecker):
    addr = None

    def __init__(self, params):
        BaseChecker.__init__(self, params)
        self.addr = params.split(':')

    #override
    def check(self):
        ret = 'DOWN'
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            conn.connect(self.addr)
            ret = 'OK'
        except:
            pass
        finally:
            conn.close()

        return ret        


CheckerMap = {
    "tcp": TCPChecker
}


CheckList = [
    {
        "id": "001",
        "key": "check_001",
        "name": "McVillage Server",
        "type": "tcp",
        "params": "10.0.0.112:25566"
    }, {
        "id": "002",
        "key": "check_002",
        "name": "TwiForest Server",
        "type": "tcp",
        "params": "10.0.0.112:25565"
    }
]

class Check:
    def start(self):
        cache = redis.StrictRedis()
        #mkey = [item["key"] for item in CheckList]
        #res = redis.mget(mkey)
        tosets = {}
        for item in CheckList:
            key = item["key"]
            typ = item["type"]
            params = item["params"]
            checkerClass = CheckerMap[typ]
            checker = checkerClass(params)
            status = checker.check()

            toset = {
                "id": item["id"],
                "key": key,
                "name": item["name"],
                "type": typ,
                "params": params,
                "status": status,
                "last_check": time.time()
            }
            tosets[key] = json.dumps(toset)

        print(tosets)
        cache.mset(tosets)

svc = Check()
svc.start()
