#!/usr/bin/env python

__all__ = ['join', 'walkdir']

import os
from collections import deque

def join(parent, child):
    return '%s/%s' % (parent if parent != '/' else '', child)

def _walk_dfs(top, onerror=None, followlinks=False):
    isdir = os.path.isdir
    islink = os.path.islink
    listdir = os.listdir
    abspath = os.path.abspath
    error = os.error

    lst = list()
    if isdir(top):
        top = abspath(top)
        lst.append(top)

    while len(lst):
        top = lst.pop()
        try:
            names = listdir(top)
        except error, err:
            if onerror is not None:
                onerror(err)
            continue
        
        dirs, nondirs = [], []
        for name in names:
            path = '%s/%s' % (top, name)
            if isdir(path):
                dirs.append(name)
            else:
                nondirs.append(name)
        yield 0, top, dirs, nondirs
        
        for name in reversed(dirs):
            path = '%s/%s' % (top, name)
            if not islink(path) or followlinks:
                lst.append(path)

def _walk_bfs(top, onerror=None, followlinks=False):
    isdir = os.path.isdir
    islink = os.path.islink
    listdir = os.listdir
    abspath = os.path.abspath
    error = os.error
    deep = 0

    lst = deque()
    if isdir(top):
        top = abspath(top)
        lst.append(1)
        lst.append(top)

    while len(lst) > 1:
        top = lst.popleft()
        if type(top) == int:
            deep = top
            lst.append(deep + 1)
            top = lst.popleft()

        try:
            names = listdir(top)
        except error, err:
            if onerror is not None:
                onerror(err)
            continue
        
        dirs, nondirs = [], []
        for name in names:
            path = '%s/%s' % (top, name)
            if isdir(path):
                dirs.append(name)
            else:
                nondirs.append(name)
        yield deep, top, dirs, nondirs
        
        for name in dirs:
            path = '%s/%s' % (top, name)
            if not islink(path) or followlinks:
                lst.append(path)
        
def walkdir(top, onWalk, mode='dfs', followlinks=False, **kwargs):
    '''mode: 'dfs' or 'bfs'.
    onWalk like: func(parent, child, isDir, **kwargs)'''
    walk = (mode == 'dfs' and _walk_dfs) or _walk_bfs
    for deep, path, dirs, files in walk(top, followlinks=followlinks):
        for d in dirs:
            onWalk(path, d, True, **kwargs)
        for f in files:
            onWalk(path, f, False, **kwargs)
        
def what(parent, child, isDir, **kwargs):
    #print os.path.abspath('%s/%s' % (parent, child))
    print '%s/%s' % (parent, child)
    #print '%s' % (parent,)

def main():
    import sys
    walkdir(sys.argv[1], what)

if __name__ == '__main__':
    main()
