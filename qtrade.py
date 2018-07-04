#!/usr/bin/env python
#coding:utf-8

import math
import requests
import datetime
import time
import pickle

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
        return text

class DingTalk:
    url = None

    def __init__(self, url):
        self.url = url

    def msg(self, msg):
        payload = {
            "msgtype": "text",
            "text": {
                "content": msg+"\n@15652234096"
            },
            "at": {
                "atMobiles": [
                    "15652234096"
                ], 
                "isAtAll": False
            }
        }
        requests.post(self.url, json=payload)


class Trade:
    def step(self, *prices):
        pass

# =1331  4
# <1331 1000  3
# <1210 1000  2
# <1100 1000  1
# <1000 
# 900 1000    -1
# 3000, 100, 200, 0.50, 150   (1+per)^n=max/min 200-100
class LevelTrade(Trade):
    holding = None
    _min_price = 0.0
    _max_price = 0.0
    _level_chg = 0.0
    _max_level = 0.0
    _level = None
    _budget = 0.0
    _budget_per_level = 0.0
    _budget_max_used = 0.0
    mode = 0
    messager = None

    def __init__(self, holding, budget, min_price, max_price, level_chg, mode=0):
        self.holding = holding
        self._budget = budget
        self._min_price = min_price
        self._max_price = max_price
        self._level_chg = level_chg
        self._max_level = self.calc_level(max_price)
        self._budget_per_level = 1.0 * self._budget / (self._max_level - 1)
        self.mode = mode

    def calc_level(self, price):
        level = int(round(math.log(1.0*price/self._min_price, 1.0+self._level_chg)+1, 5))
        return level

    def calc_num(self, level, price):
        if self.mode == 1:
            num = round(1.0*self._budget_per_level/self._min_price/100) * 100
        elif self.mode == 2:
            num = round(1.0*self._budget_per_level/(self._min_price+self._max_price)*2/100) * 100
        elif self.mode == 3:
            num = round(1.0*self._budget_per_level/self._max_price/100) * 100
        else:
            num = round(1.0*self._budget_per_level*level/price/100) * 100
        return num

    def step(self, *prices):
        ret = False
        for price in prices:
            level = self.calc_level(price)
            if self._level is None:
                dt = level - self._max_level
            else:
                dt = level - self._level

            if dt > 0:
                # sell
                num = self.calc_num(dt, price)
                if num>0 and self.holding.num>0:
                    if num > self.holding.num:
                        num = self.holding.num
                    cost = self.holding.sell(num, price)
                    self._level = level
                    ret = True
                    if self.messager:
                        self.messager.msg('%s\nSELL %d at %.3f, %s' % (self.holding.name, num, price, ('%.2f' if cost<0 else '+%.2f') % (cost,)))
            elif dt < 0:
                # buy
                num = self.calc_num(-dt, price)
                if num > 0:
                    cost = self.holding.buy(num, price)
                    self._level = level
                    if self.holding.cost > self._budget_max_used:
                        self._budget_max_used = self.holding.cost
                    ret = True
                    if self.messager:
                        self.messager.msg('%s\nBUY %d at %.3f, %s' % (self.holding.name, num, price, ('%.2f' if -cost<0 else '+%.2f') % (-cost,)))
        return ret
            
    def step_by_kline(self, kline):
        if not kline.data:
            return
        prices = [item['1'] for item in kline.data]
        return self.step(*prices)

    def reset(self, reset_holding=False):
        self._level = self.calc_level(self._max_price)
        self._budget_max_used = 0.0
        if reset_holding:
            self.holding.reset()

    def print_detail(self, price):
        text = self.holding.print_detail(price)
        u = self._budget_max_used * 100.0 / self._budget
        final = self._budget + self.holding.float_profit(price)
        pl = (final - self._budget) * 100.0 / self._budget
        free = self._budget - self.holding.cost
        free_rate = free * 100.0 / self._budget
        text = '''%s\nBudget: %.2f
Max Used: %.2f(%.2f%%)
Final: %.2f(%s%.2f%%)
Free: %.2f(%.2f%%)''' % (
        text,
        self._budget,
        self._budget_max_used,
        u,
        final,
        '+' if pl>0 else '',
        pl,
        free,
        free_rate)
        if self.messager:
            self.messager.msg(text)
        print text
        return text

class KLine:
    symbol = ""
    data = None
    low = None  # 最低价
    high = None  # 最高价
    avg = None  # 平均价
    cur = None  # 最新价
    hv = None  # 历史波动率
    date = None

    def __init__(self, symbol):
        self.symbol = symbol

    def update(self, start=None, end=None):
        market = self.symbol[:2]
        symbol_raw = self.symbol[2:]
        url = r'https://market.youyu.cn/app/v3/quote/user/query/stockdetail?marketcode=%s&stockcode=%s&graph_tab_index=2&k_not_refresh=0&stock_type=010104&klinenum=100' % (market, symbol_raw)
        try:
            res = requests.get(url).json()
        except Exception, e:
            return False
        if not 'data' in res or not 'graph_tab_data' in res['data'] or not res['data']['graph_tab_data'] or not 'all_data' in res['data']['graph_tab_data'][0]:
            return False
        k = res['data']['graph_tab_data'][0]['all_data']
        self.data = []
        self.low = None
        self.high = None
        self.cur = k[0]['1']
        self.date = k[0]['44']
        self.avg = 0.0
        last_p = None
        v_rate = []
        v_rate_avg = 0.0
        for i in reversed(k):
            date = i['44']
            if (start is None or date>=start) and (end is None or date<=end):
                self.data.append(i)
                price = i['1']
                self.avg += price
                if not last_p is None:
                    rate = math.log(price/last_p)
                    v_rate.append(rate)
                    v_rate_avg += rate
                last_p = price
                if self.low is None or i['5']<self.low:
                    self.low = i['5']
                if self.high is None or i['4']>self.high:
                    self.high = i['4']
        self.avg /= len(self.data)
        v_rate_avg /= len(v_rate)
        self.hv = 0.0
        for rate in v_rate:
            self.hv += (rate - v_rate_avg) ** 2.0
        self.hv = (self.hv / len(v_rate)) ** 0.5

        return True
    
def get_kline(symbol, start=None, end=None):
    k = KLine(symbol)
    k.update(start, end)
    return k

class Robot:
    symbol = ""
    holding = None
    trade = None
    kline = None
    messager = None

    def __init__(self, symbol, budget, low, high, chg):
        self.symbol = symbol
        self.holding = Holding(symbol)
        self.trade = LevelTrade(self.holding, budget, low, high, chg)
        self.kline = KLine(symbol)

    def _update_kline(self):
        end = datetime.datetime.now()
        start = end - datetime.timedelta(days=7)
        return self.kline.update(start.strftime('%Y%m%d'), end.strftime('%Y%m%d'))

    def save(self, file_name=None):
        if not file_name:
            file_name = self.symbol+'.rob'
        with open(file_name, 'wb') as fp:
            pickle.dump(self, fp)

    def start(self, sleep=10, begin=None):
        self.trade.messager = self.messager
        while True:
            now = time.time()
            if self._update_kline():
                if not begin or self.kline.date>=begin:
                    if self.trade.step(self.kline.cur):
                        self.save()
                        self.trade.print_detail(self.kline.cur)
            time.sleep(sleep)

def load_robot(file_name):
    with open(file_name, 'rb') as fp:
        return pickle.load(fp)
    return None

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
    k = get_kline(symbol)
    if not k:
        print >>sys.stderr, 'Wrong symbol(%s)' % (symbol,)
        sys.exit(1)
    start = k.data[0]['44']
    end = k.data[len(k.data)-1]['44']
    h = Holding(symbol)
    h.charge_rate = charge_rate
    h.min_charge = charge_min
    tr = LevelTrade(h, 10000000, k.low, k.high, 0.02, mode)
    tr.step_by_kline(k)
    print 'Date: %s -> %s\nPrice Range: %.3f ~ %.3f (%.2f%%)\nAvange Price: %.3f\nHistory Volatility: %.2f%%\n' % (start, end, k.low, k.high, (k.high-k.low)*100.0/k.low, k.avg, k.hv*100.0)
    print 'Now:'
    tr.print_detail(k.cur)
    print '\n[At Avange Price(%.3f)]:' % (k.avg,)
    tr.step(k.avg)
    tr.print_detail(k.avg)
