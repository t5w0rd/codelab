#!/usr/bin/env python

import sys

CC_RED_BEGIN = '\033[0;31m'
CC_GREEN_BEGIN = '\033[0;32m'
CC_YELLOW_BEGIN = '\033[0;33m'
CC_BLUE_BEGIN = '\033[0;34m'
CC_END = '\033[0m'

def createMap(width, height):
    ret = []
    for ln in xrange(height):
        ret.append([0] * width)
    return ret

def printNode(node):
    s = '%02X' % (node)
    if node == 1:
        s = CC_RED_BEGIN + s + CC_END
    elif node == 2:
        s = CC_GREEN_BEGIN + s + CC_END
    elif node == 3:
        s = CC_YELLOW_BEGIN + s + CC_END
    elif node == 4:
        s = CC_BLUE_BEGIN + s + CC_END
    sys.stdout.write(s)

def printSpace():
    sys.stdout.write(' ')

def printLf():
    sys.stdout.write('\n')

def printMap(mp):
    for ln in mp:
        for node in ln:
            printNode(node)
            printSpace()
        printLf()
    sys.stdout.flush()

def getHeight(mp):
    return len(mp)

def getWidth(mp):
    return len(mp[0])

def setNode(mp, x, y, v):
    mp[y][x] = v



def astar(mp, start, end):
    openNodes = dict()
    closeNodes = set()
    openNodes[start] = {'f': 0}
    minFNode = None
    for openNode, info in openNodes.iteritems():
        if not minFNode:
            minFNode = openNode
        else:
            curF = info['f']
            if curF < openNodes[minFNode]:
                minF = curF

    while True:



def main():
    mp = createMap(7, 5)
    mp[1][3] = 4
    mp[2][3] = 4
    mp[3][3] = 4
    printMap(mp)

if __name__ == '__main__':
    main()

