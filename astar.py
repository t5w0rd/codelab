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
    width = getWidth(mp)
    height = getHeight(mp)

    def getH(node, end):
        return (abs(node[0] - end[0]) + abs(node[1] - end[1])) * 10

    openNodes = dict()
    closeNodes = dict()

    openNodes[start] = {'parent': None, 'g': 0, 'h': getH(start, end)}
    openNodes[start]['f'] = openNodes[start]['g'] + openNodes[start]['h']

    while (not end in closeNodes) and len(openNodes) > 0:
        minFNode = None
        minFNodeInfo = None
        for openNode, openNodeInfo in openNodes.iteritems():
            if not minFNode:
                minFNode = openNode
                minFNodeInfo = openNodeInfo
            else:
                if openNodeInfo['f'] < openNodes[minFNode]['f']:
                    minFNode = openNode
                    minFNodeInfo = openNodeInfo

        closeNodes[minFNode] = openNodes.pop(minFNode)

        nextNodes = {
            (minFNode[0] - 1, minFNode[1] - 1): 14,
            (minFNode[0] - 1, minFNode[1]): 10,
            (minFNode[0] - 1, minFNode[1] + 1): 14,
            (minFNode[0], minFNode[1] - 1): 10,
            (minFNode[0], minFNode[1] + 1): 10,
            (minFNode[0] + 1, minFNode[1] - 1): 14,
            (minFNode[0] + 1, minFNode[1]): 10,
            (minFNode[0] + 1, minFNode[1] + 1): 14}

        for nextNode, incG in nextNodes.iteritems():
            if nextNode[0] < 0 or nextNode[0] >= height or nextNode[1] < 0 or nextNode[1] >= width:
                continue

            if mp[minFNode[0]][nextNode[1]] == 4 or mp[nextNode[0]][minFNode[1]] == 4 or mp[nextNode[0]][
                nextNode[1]] == 4 or nextNode in closeNodes:
                continue

            nextNodeG = minFNodeInfo['g'] + incG
            if not nextNode in openNodes:
                nextNodeInfo = {'parent': minFNode}
                nextNodeInfo['g'] = nextNodeG
                nextNodeInfo['h'] = getH(nextNode, end)
                nextNodeInfo['f'] = nextNodeInfo['g'] + nextNodeInfo['h']
                openNodes[nextNode] = nextNodeInfo
            else:
                nextNodeInfo = openNodes[nextNode]
                if nextNodeG < nextNodeInfo['g']:
                    nextNodeInfo['parent'] = minFNode
                    nextNodeInfo['g'] = nextNodeG
                    nextNodeInfo['f'] = nextNodeInfo['g'] + nextNodeInfo['h']

    return closeNodes


def main():
    mp = createMap(20, 20)
    mp[1][3] = 4
    mp[2][3] = 4
    mp[3][3] = 4
    mp[12][15] = 4
    mp[12][14] = 4
    mp[12][13] = 4
    mp[11][13] = 4
    mp[10][13] = 4
    mp[13][12] = 4
    mp[14][11] = 4
    mp[15][10] = 4
    mp[9][13] = 4
    mp[8][13] = 4
    mp[7][13] = 4
    mp[6][13] = 4
    mp[8][5] = 4
    mp[8][6] = 4
    mp[8][7] = 4
    mp[8][4] = 4
    mp[8][3] = 4
    mp[9][7] = 4
    mp[15][8] = 4
    mp[15][7] = 4
    mp[15][6] = 4
    mp[12][7] = 4
    mp[12][8] = 4
    mp[12][9] = 4
    mp[12][10] = 4
    mp[5][10] = 4
    mp[5][9] = 4
    mp[5][8] = 4
    mp[5][7] = 4
    mp[4][7] = 4
    mp[3][7] = 4
    mp[2][7] = 4
    # printMap(mp)
    start = (0, 0)
    end = (17, 17)
    closeNodes = astar(mp, start, end)
    if end in closeNodes:
        curNode = end
        while curNode:
            curNodeInfo = closeNodes[curNode]
            mp[curNode[0]][curNode[1]] = 3
            curNode = curNodeInfo['parent']
    printMap(mp)


if __name__ == '__main__':
    main()
