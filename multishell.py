#!/usr/bin/env python
#coding:utf-8
import sys
import os
import subprocess
import multiprocessing
import threading

__all__ = ['multishell',]

def usage():
    print 'Usage:'
    print '  %s <CHILD1> [CHILD2] ...' % (sys.argv[0])

color_format = '\033[%dm%%s\033[0m'  # fg:30-37, bg:40-47

def colorstr(s, color, bg=False):
    return (color_format % (30+(10 if bg else 0)+(color)%6+1)) % (s,)

def _read_output(q, sp):
    pid = os.getpid()
    def _read_stderr():
        while True:
            ln = sp.stderr.readline()
            if not ln:
                break
            q.put((pid, ln, True))

    while True:
        ln = sp.stdout.readline()
        if not ln:
            break
        q.put((pid, ln, False))

    t = threading.Thread(target=_read_stderr)
    t.start()
    t.join()
    q.put((0, pid, False))

def multishell(argvs_list, shell=False):
    q = multiprocessing.Queue()
    pmap = {}
    for i, argvs in enumerate(argvs_list):
        if shell:
            name = os.path.basename(argvs.split()[0])
        else:
            name = os.path.basename(argvs[0])
        sp = subprocess.Popen(argvs, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p = multiprocessing.Process(target=_read_output, args=(q, sp))
        p.start()
        pmap[p.pid] = {
            'obj': p,
            'prefix': '[%s] '%(name,),
            'color': i
        }

    alive = len(pmap)
    while True:
        pid, ln, bg = q.get()
        if pid == 0:
            alive = alive - 1
            if alive == 0:
                break
            continue

        info = pmap[pid]
        sys.stdout.write(colorstr(info['prefix']+ln, info['color'], bg))

    for info in pmap.itervalues():
        info['obj'].join()

    q.close()

if __name__ == '__main__':
    #multishell(('/usr/bin/uname', '/usr/bin/ssh --help'), shell=True)
    #multiexec((('/usr/bin/uname',), ('/usr/bin/uname',)))
    multishell(sys.argv[1:], shell=True)
