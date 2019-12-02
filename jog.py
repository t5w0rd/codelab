#!/usr/bin/env python
# -*- coding: utf-8 -*-

CC_RED_BEGIN = '\033[0;31m'
CC_WHITE_BEGIN = '\033[0;37m'
CC_GREEN_BEGIN = '\033[0;32m'
CC_END = '\033[0m'

COLOR_UNSET = 'UNSET'
COLOR_RED = 'RED'
COLOR_WHITE = 'WHITE'
COLOR_GREEN = 'GREEN'

COLOR_SET = (COLOR_RED, COLOR_WHITE, COLOR_GREEN)

color_text = {
    COLOR_RED: CC_RED_BEGIN + 'R' + CC_END,
    COLOR_WHITE: CC_WHITE_BEGIN + 'W' + CC_END,
    COLOR_GREEN: CC_GREEN_BEGIN + 'G' + CC_END,
}

class Stat:
    def __init__(self):
        self.total = 0
        self.colors = {COLOR_RED: 0, COLOR_WHITE: 0, COLOR_GREEN: 0}

    def add(self, color):
        self.total += 1
        self.colors[color] += 1

    def output(self):
        if self.total == 0:
            print('\tN/A')
            return

        res = sorted(self.colors.items(), key=lambda item:item[1], reverse=True)
        for color, count in res:
            if count == 0:
                continue
            print('\t%s:\t%.0f%%' % (color_text[color], count * 100.0 / self.total))


def island_invalid(compass, island1, island2, island3):
    if compass is COLOR_UNSET:
        return False

    stat = Stat()
    stat.add(island1)
    stat.add(island2)
    stat.add(island3)

    if compass is COLOR_RED:
        return stat.colors[COLOR_GREEN] >= stat.colors[COLOR_RED]

    if compass is COLOR_WHITE:
        return stat.colors[COLOR_GREEN] != stat.colors[COLOR_RED]

    if compass is COLOR_GREEN:
        return stat.colors[COLOR_GREEN] <= stat.colors[COLOR_RED]


class Game:
    def __init__(self):
        self._cur_compass = COLOR_UNSET
        self._his1_compass = COLOR_UNSET
        self._his2_compass = COLOR_UNSET
        self._his1_island = COLOR_UNSET
        self._his2_island = COLOR_UNSET

    def reset(self):
        self._cur_compass = COLOR_UNSET
        self._his1_compass = COLOR_UNSET
        self._his2_compass = COLOR_UNSET
        self._his1_island = COLOR_UNSET
        self._his2_island = COLOR_UNSET


    def set_cur_compass(self, color):
        self._cur_compass = color

    def set_cur_island(self, color):
        self._his2_compass = self._his1_compass
        self._his1_compass = self._cur_compass
        self._his2_island = self._his1_island
        self._his1_island = color

    def guess_island(self):
        cur_stat = Stat()
        next1_stat = Stat()
        next2_stat = Stat()

        for cur in COLOR_SET:
            if island_invalid(self._his2_compass, self._his2_island, self._his1_island, cur):
                continue

            for next1 in COLOR_SET:
                if island_invalid(self._his1_compass, self._his1_island, cur, next1):
                    continue

                for next2 in COLOR_SET:
                    if island_invalid(self._cur_compass, cur, next1, next2):
                        continue

                    cur_stat.add(cur)
                    next1_stat.add(next1)
                    next2_stat.add(next2)

        print('')
        print('')
        print('next2:')
        next2_stat.output()
        print('next1:')
        next1_stat.output()
        print('cur:')
        cur_stat.output()


if __name__ == '__main__':
    import sys
    g = Game()
    while True:
        ln = sys.stdin.readline()
        if len(ln) == 0:
            break

        ln = ln.strip()
        if ln == '0':
            g.reset()
        elif ln == '1':
            g.set_cur_compass(COLOR_RED)
        elif ln == '2':
            g.set_cur_compass(COLOR_WHITE)
        elif ln == '3':
            g.set_cur_compass(COLOR_GREEN)
        elif ln == '4':
            g.set_cur_island(COLOR_RED)
        elif ln == '5':
            g.set_cur_island(COLOR_WHITE)
        elif ln == '6':
            g.set_cur_island(COLOR_GREEN)
        else:
            continue

        g.guess_island()

