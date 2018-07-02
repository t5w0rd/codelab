#!/usr/bin/env python


class Holding:
    cost = 0.0
    num = 0.0
    charge_rate = 0.0001
    min_charge = 0.1
    name = ""

    def __init__(self, name=""):
        self.reset()
        self.name = name

    def reset(self):
        self.num = 0.0
        self.cost = 0.0

    def buy(self, num, price):
        self.num += num
        cost = price * num
        cost += max(self.min_charge, cost*self.charge_rate)
        self.cost += cost
        print 'buy %d at %.3f, total -%.2f' % (num, price, cost)
        return cost

    def sell(self, num, price):
        if self.num < num:
            raise ValueError('sell too much (%g/%g)' % (num, self.num))
        self.num -= num
        cost = price * num
        cost -= max(self.min_charge, cost*self.charge_rate)
        self.cost -= cost
        print 'sell %d at %.3f total +%.2f' % (num, price, cost)
        return cost

    def sell_all(self, price):
        self.sell(self.num, price)

    def float_profit(self, price):
        return self.num * price - self.cost

    def unit_cost(self):
        if self.num == 0:
            return None
        return max(0, self.cost / self.num)

    def print_detail(self, price):
        pl = self.float_profit(price)
        uc = self.unit_cost()
        text = '''Name: %s
Current Price: %.3f
Unit Cost: %s
Open Interest: %d
Market Value: %.2f
Float Profit: %s%.2f%s''' % (
                self.name,
                price,
                '0.000' if uc is None else '%.3f' % (uc,),
                self.num,
                price*self.num,
                '+' if pl>0 else '',
                pl,
                '' if self.cost<=0 else ('(%s%%.2f%%%%)' % ('+' if pl>0 else '',)) % (pl*100.0/self.cost,))
        print text
# =1331  4
# <1331 1000  3
# <1210 1000  2
# <1100 1000  1
# <1000 
# 900 1000    -1
# 3000, 100, 200, 0.50, 150   (1+per)^n=max/min 200-100
import math
class LevelTrade:
    holding = None
    _min_price = 0.0
    _max_price = 0.0
    _level_chg = 0.0
    _max_level = 0.0
    _level = None
    _budget = 0.0
    _budget_per_level = 0.0
    _budget_max_used = 0.0
    _mode = 0

    def __init__(self, holding, budget, min_price, max_price, level_chg, mode=0):
        self.holding = holding
        self._budget = budget
        self._min_price = min_price
        self._max_price = max_price
        self._level_chg = level_chg
        self._max_level = self.calc_level(max_price)
        self._budget_per_level = 1.0 * self._budget / (self._max_level - 1)
        self._mode = mode

    def calc_level(self, price):
        level = int(round(math.log(1.0*price/self._min_price, 1.0+self._level_chg)+1, 5))
        return level

    def calc_num(self, level, price):
        if self._mode == 1:
            num = round(1.0*self._budget_per_level/self._min_price/100) * 100
        elif self._mode == 2:
            num = round(1.0*self._budget_per_level/(self._min_price+self._max_price)*2/100) * 100
        elif self._mode == 3:
            num = round(1.0*self._budget_per_level/self._max_price/100) * 100
        else:
            num = round(1.0*self._budget_per_level*level/price/100) * 100
        return num

    def step(self, *prices):
        for price in prices:
            level = self.calc_level(price)
            if self._level is None:
                dt = level - self._max_level
            else:
                dt = level - self._level

            if dt > 0:
                # sell
                num = self.calc_num(dt, price)
                if num > 0:
                    if num > self.holding.num:
                        self.holding.sell_all(price)
                    else:
                        self.holding.sell(num, price)
            elif dt < 0:
                # buy
                num = self.calc_num(-dt, price)
                if num > 0:
                    self.holding.buy(num, price)
                    if self.holding.cost > self._budget_max_used:
                        self._budget_max_used = self.holding.cost
            self._level = level

    def reset(self, reset_holding=False):
        self._level = self.calc_level(self._max_price)
        self._budget_max_used = 0.0
        if reset_holding:
            self.holding.reset()

    def print_detail(self, price):
        self.holding.print_detail(price)
        u = self._budget_max_used * 100.0 / self._budget
        final = self._budget + self.holding.float_profit(price)
        pl = (final - self._budget) * 100.0 / self._budget
        free = self._budget - self.holding.cost
        free_rate = free * 100.0 / self._budget
        text = '''Budget: %.2f
Max Used: %.2f(%.2f%%)
Final: %.2f(%s%.2f%%)
Free: %.2f(%.2f%%)''' % (
        self._budget,
        self._budget_max_used,
        u,
        final,
        '+' if pl>0 else '',
        pl,
        free,
        free_rate)
        print text

if __name__ == '__main__':
    import sys
    import requests
    if len(sys.argv) < 2:
        print 'Usage:\n  %s <stock_code> [mode:0|1|2|3] [charge_rate] [charge_min]' % (sys.argv[0],)
        sys.exit(1)
    symbol = sys.argv[1]
    mode = 0 if len(sys.argv)<3 else int(sys.argv[2])
    charge_rate = 0.0001 if len(sys.argv)<4 else float(sys.argv[3])
    charge_min = 0.1 if len(sys.argv)<4 else float(sys.argv[3])
    market = symbol[:2]
    symbol_raw = symbol[2:]
    url = r'https://market.youyu.cn/app/v3/quote/user/query/stockdetail?marketcode=%s&stockcode=%s&graph_tab_index=2&k_not_refresh=0&stock_type=010104&klinenum=100' % (market, symbol_raw)
    res = requests.get(url).json()
    if not 'graph_tab_data' in res['data']:
        print >>sys.stderr, 'Wrong symbol(%s)' % (symbol,)
        sys.exit(1)
    k = res['data']['graph_tab_data'][0]['all_data']
    start = k[len(k)-1]['44']
    end = k[0]['44']
    price = k[0]['1']
    max_price = None
    min_price = None
    for i in k:
        _max = i['4']
        _min = i['5']
        if max_price is None or _max>max_price:
            max_price = _max
        if min_price is None or _min<min_price:
            min_price = _min
    h = Holding(symbol)
    h.charge_rate = charge_rate
    h.min_charge = charge_min
    tr = LevelTrade(h, 10000000, min_price, max_price, 0.02, mode)
    avg = 0.0
    for i in reversed(k):
        p = i['1']
        avg += p
        tr.step(p)
    avg /= len(k)
    print 'Date: %s -> %s\nPrice Range: %.3f ~ %.3f (%.2f%%)\nAvange Price: %.3f\n' % (start, end, min_price, max_price, (max_price-min_price)*100.0/min_price, avg)
    print 'Now:'
    tr.print_detail(price)
    print '\n[At Avange Price(%.3f)]:' % (avg,)
    tr.step(avg)
    tr.print_detail(avg)
