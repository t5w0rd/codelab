#!/usr/bin/env python

import os
from collections import deque

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
        yield top, dirs, nondirs
        
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

    lst = deque()
    if isdir(top):
        top = abspath(top)
        lst.append(top)

    while len(lst):
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
        yield top, dirs, nondirs
        
        for name in dirs:
            path = '%s/%s' % (top, name)
            if not islink(path) or followlinks:
                lst.append(path)
        
def walkdir(top, onWalk, mode='dfs', followlinks=False):
    '''mode: 'dfs' or 'bfs'.
    onWalk(parent, child, isDir)'''
    walk = (mode == 'dfs' and _walk_dfs) or _walk_bfs
    for path, dirs, files in walk(top, followlinks=followlinks):
        for d in dirs:
            onWalk(path, d, True)
        for f in files:
            onWalk(path, f, False)
        
def walkdir(top, onWalk, mode='dfs', followlinks=False):
    '''mode: 'dfs' or 'bfs'.
    onWalk(parent, child, isDir)'''
    walk = (mode == 'dfs' and _walk_dfs) or _walk_bfs
    for path, dirs, files in walk(top, followlinks=followlinks):
        for d in dirs:
            onWalk(path, d, True)
        for f in files:
            onWalk(path, f, False)

def what(parent, child, isDir):
    #print os.path.abspath('%s/%s' % (parent, child))
    print '%s/%s' % (parent, child)
    #print '%s' % (parent,)

def main():
    import sys
    walkdir(sys.argv[1], what)

if __name__ == '__main__':
    main()
