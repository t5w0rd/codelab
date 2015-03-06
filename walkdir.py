#!/usr/bin/env python

import os

def walkdir(top, onWalk, followlinks = False):
    for path, dirs, files in os.walk(top, followlinks = followlinks):
        for d in dirs:
            onWalk(path, d, True)
        for f in files:
            onWalk(path, f, False)

def what(parent, child, isDir):
    print os.path.abspath('%s/%s' % (parent, child))

def main():
    import sys
    walkdir(sys.argv[1], what)

if __name__ == '__main__':
    main()
