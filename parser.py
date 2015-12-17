#!/usr/bin/env python

def splitWithPairs(s, seps, pairDict):
    '''s: string
    seps: ',' or ',;'
    pairDict: {'()':3, '[]':3, '""':4}

    '''
    # '(x, y), (z, "(dd", aa)'
    push = {pair[0]: (pair[1], level) for pair, level in pairDict.iteritems()}
    pop = {pair[1]: pair[0] for pair in pairDict.iterkeys()}
    
    res = list()
    stack = list()
    start = 0
    end = 0
    for c in s:
        empty = (len(stack) == 0)
        if empty and (c in seps):
            res.append(s[start: end])
            start = end + 1
        elif (c in pop) and (not empty) and (c == push[stack[-1]][0]):
            stack.pop()
       	elif (c in push) and (empty or (push[c][1] >= push[stack[-1]][1])):
            stack.append(c)
        end += 1

    res.append(s[start: end])
    return res


s = '(x, y), (z, "(dd", aa)'
s = 'mul(ipFixed.ipHdrLen,4),calcsize(ipFixed)'
p = {'()': 2, '[]': 1, '""': 4, "''": 4}

l = splitWithPairs(s, ',', p)
print l
