#!/usr/bin/env python

class Holding:
    _total = 0.0
    _num = 0.0

    def __init__(self):
        self.reset()

    def reset(self):
        self._num = 0.0
        self._total = 0.0

    def buy(self, points, value, append=0.0):
        num = value * 1.0 / points
        self._num += num
        self._total += value + append

    def sell(self, points, value, append=0.0):
        num = value * 1.0 / points
        if self._num < num:
            raise ValueError('sell too much (%f/%f)' % (num, self._num))
        self._num -= num
        self._total -= value-append

    def sellall(self, points, append=0.0):
        value = self._num * points
        self._num = 0.0
        self._total -= value-append
        return self._total

    def pl(self, points):
        return self._num * points - self._total

    def holdingcost(self):
        return self._total / self._num
