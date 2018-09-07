#!/usr/bin/env python3
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
        addr = params.split(':')
        addr[1] = int(addr[1])
        self.addr = tuple(addr)

    #override
    def check(self):
        ret = 'DOWN'
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.settimeout(5)
        try:
            conn.connect(self.addr)
            ret = 'OK'
        except Exception as e:
            #print(e)
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
        "params": "10.0.0.112:25565"
    }, {
        "id": "002",
        "key": "check_002",
        "name": "TwiForest Server",
        "type": "tcp",
        "params": "10.0.0.112:25566"
    }, {
        "id": "003",
        "key": "check_003",
        "name": "Ubuntu SSH Server",
        "type": "tcp",
        "params": "10.0.0.226:56022"
    }
]

class Check:
    def start(self):
        cache = redis.StrictRedis()
        keys = []
        tosets = {}
        for item in CheckList:
            key = item["key"]
            name = item["name"]
            typ = item["type"]
            params = item["params"]
            checkerClass = CheckerMap[typ]
            checker = checkerClass(params)
            print("checking "+name+"... ", end="", flush=True)
            status = checker.check()
            print(status)

            toset = {
                "id": item["id"],
                "key": key,
                "name": name,
                "type": typ,
                "params": params,
                "status": status,
                "last_check": time.time()
            }
            keys.append(key)
            tosets[key] = json.dumps(toset)

        tosets["check_list"] = ','.join(keys)
        cache.mset(tosets)
        

svc = Check()
svc.start()
