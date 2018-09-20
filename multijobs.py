#!/usr/bin/env python

import os
import multiprocessing
import collections

def multijobs(target, argslist, workers=None):
    if not workers:
        workers = multiprocessing.cpu_count()
    workers = min(len(argslist), workers)
    msgq = multiprocessing.Queue()

    # target wrapper
    def worker(target, args):
        try:
            pid = os.getpid()
            res = target(*args)
            msgq.put((pid, res))
        except Exception, e:
            msgq.put((pid, e))

    # add proc to waiting
    waiting = collections.deque()
    for args in argslist:
        args_wapper = (target, args)
        proc = multiprocessing.Process(target=worker, args=args_wapper)
        waiting.append(proc)

    seq = []
    running = set()
    results = {}
    dataNum = 1
    while True:
        # move proc from waiting to running
        for i in xrange(max(0, min(len(waiting), workers - len(running)))):
            proc = waiting.popleft()
            running.add(proc)
            proc.start()
            seq.append(proc.pid)

        if len(running) == 0:
            break

        # if len(running) > 0, wait for blocking msgq.get() instead of time.sleep()
        for i in xrange(dataNum):
            pid, res = msgq.get()
            results[pid] = res
        dataNum = 0

        # check proc is alive or not
        dead = []
        for proc in running:
            if not proc.is_alive():
                dead.append(proc)
                
        # remove dead proc from running
        for proc in dead:
            running.remove(proc)
            proc.join()
            dataNum += 1

    # put msgq data left to results map
    while not msgq.empty():
        pid, res = msgq.get()
        results[pid] = res
    msgq.close()

    # collect retults of child proc
    ret = []
    for pid in seq:
        ret.append(results[pid])

    return ret

def splitlist(lst, num):
    ret = []
    msz = len(lst)
    sz = max(1, int(round(len(lst) * 1.0 / num)))
    p = 0
    for i in xrange(num):
        p2 = p+sz if i!=num-1 else msz
        ret.append(lst[p:p2])
        p += sz
    return ret
