#!/usr/bin/env python

def multijobs(target, argslist, workers=None):
    if not workers:
        workers = multiprocessing.cpu_count()
    workers = min(len(argslist), workers)
    msgq = multiprocessing.Queue()

    # target wapper
    def worker(target, args):
        res = target(*args)
        pid = os.getpid()
        msgq.put((pid, res))

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
