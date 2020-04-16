#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import requests
import json
from fake_useragent import UserAgent
import pickle
import sys
import os


import hmac
import hashlib
import base64
import urllib.parse


notify_url = r'https://oapi.dingtalk.com/robot/send?access_token=759196110b9d292f2826d8474ee73f040cc4d5508e29aa19e21185491e7a626c'
secret = r'SEC3b634b66a28f2ec828956364cc6a49b70260adce3c09e163aca57f6501ac83ed'


def notify(data):
    timestamp = int(round(time.time() * 1000))
    secret_enc = secret.encode()
    string_to_sign = '{}\n{}'.format(timestamp, secret)
    string_to_sign_enc = string_to_sign.encode()
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    url = '{}&timestamp={}&sign={}'.format(notify_url, timestamp, sign)
    try:
        return requests.post(url, json=data).status_code == 200
    except:
        return False


class Seller:
    island_list_url = r'http://ttc.21hz.top/turniptrade/island/list/{}'
    seller_init_url = r'http://ttc.21hz.top/turniptrade/seller/init'
    seller_join_url = r'http://ttc.21hz.top/turniptrade/seller/{}/join'
    seller_status_url = r'http://ttc.21hz.top/turniptrade/seller/{}/status'
    seller_extend_url = r'http://ttc.21hz.top/turniptrade/seller/{}/extend'
    seller_quit_url = r'http://ttc.21hz.top/turniptrade/seller/{}/quit'
    
    def __init__(self):
        self._headers = {
            'User-Agent': UserAgent().chrome,
            'Origin': r'http://dodopass.21hz.top',
            'Referer': r'http://dodopass.21hz.top/trade/seller.html'
        }
        self._sess = requests.Session()
        self._sess.headers.update(self._headers)
        self.name = None
        self.seller_id = None

    def island_list(self, page):
        rsp = self._sess.get(Seller.island_list_url.format(page), headers=self._headers)
        assert rsp.status_code == 200, rsp.status_code
        rsp = rsp.json()
        code = rsp['status']
        msg = rsp['msg']
        lst = rsp['list']

        islands = { island['island_id']: {
            'name': island['name'],
            'price': island['price'],
            'remark': island['remark'],
            'seller_count': island['seller_count'],
            'max_seller': island['max_seller'],
            'queue_length': island['queue_length']
        } for island in lst }

        return code, msg, islands

    def seller_init(self, name):
        rsp = self._sess.get(Seller.seller_init_url, headers=self._headers)
        assert rsp.status_code == 200, rsp.status_code
        rsp = rsp.json()
        code = rsp['status']
        msg = rsp['msg']
        seller_id = rsp['seller_id']

        self.name = name
        self.seller_id = seller_id

        return code, msg, seller_id

    def seller_join(self, island_id):
        data = {
            'name': self.name,
            'island': island_id
        }
        rsp = self._sess.post(Seller.seller_join_url.format(self.seller_id), json=data, headers=self._headers)
        assert rsp.status_code == 200, rsp.status_code
        rsp = rsp.json()
        code = rsp['status']
        msg = rsp['msg']

        return code, msg

    def seller_status(self):
        rsp = self._sess.get(Seller.seller_status_url.format(self.seller_id), headers=self._headers)
        assert rsp.status_code == 200, rsp.status_code
        rsp = rsp.json()
        code = rsp['status']
        msg = rsp['msg']
        island = rsp['island']

        return code, msg, island

    def seller_extend(self):
        data = {}
        rsp = self._sess.post(Seller.seller_extend_url.format(self.seller_id), json=data, headers=self._headers)
        assert rsp.status_code == 200, rsp.status_code
        rsp = rsp.json()
        code = rsp['status']
        msg = rsp['msg']

        return code, msg

    def seller_quit(self):
        data = {
            'name': self.name
        }
        rsp = self._sess.post(Seller.seller_quit_url.format(self.seller_id), headers=self._headers)
        assert rsp.status_code == 200, rsp.status_code
        rsp = rsp.json()
        code = rsp['status']
        msg = rsp['msg']

        return code, msg

    def dump(self, fname):
        with open(fname, 'wb') as fp:
            pickle.dump(self, fp)
            return fname
        return None

    @staticmethod
    def load(fname):
        with open(fname, 'rb') as  fp:
            return pickle.load(fp)


def load_history():
    global history
    try:
        with open('islands.history', 'rb') as  fp:
            history = pickle.load(fp)
    except:
        history = set()


def dump_history():
    with open('islands.history', 'wb') as  fp:
        global history
        pickle.dump(history, fp)


def single_seller_robot(name, strategy):
    global history
    load_history()

    seller = Seller()
    
    state = 'init'
    while True:
        try:
            if state == 'init':
                print('创建临时卖家<{}>...'.format(name), end='')
                code, msg, seller_id = seller.seller_init(name)
                print('[{}] {} ID:{}\n'.format(code, msg, seller_id))
                state = 'pick'

            elif state == 'pick':
                page = 1
                print('获取第{}页岛列表...'.format(page), end='')
                code, msg, islands = seller.island_list(page)
                print('[{}] {} 岛数量:{}\n'.format(code, msg, len(islands)))
                island_id = strategy(islands)
                if island_id is not None:
                    history.add(island_id)
                    island = islands[island_id]
                    print('<{}>加入<{}>岛的等候队伍...'.format(name, island['name']), end='')
                    code, msg = seller.seller_join(island_id)
                    print('[{}] {}\n'.format(code, msg))
                    if code == 0:
                        # 可以登岛
                        fname = '{}_queue.seller'.format(seller.seller_id)
                        seller.dump(fname)
                        state = 'status'
                    elif code == 1:
                        # 开始排队
                        fname = '{}_queue.seller'.format(seller.seller_id)
                        seller.dump(fname)
                        state = 'status'
                    elif code == 9:
                        # 已在队列中
                        state = 'status'
                    else:
                        print('未识别:{} {} {}\n'.format(state, code, msg))
                else:
                    print('没有满足条件的岛', end='\r')
                    time.sleep(1)

            elif state == 'status':
                code, msg, island = seller.seller_status()
                if code == 0:
                    # 不在队伍中
                    print('闲置中\n')
                    state = 'pick'
                elif code == 1:
                    # 排到队首
                    print('\n可以登岛\n')
                    src = '{}_queue.seller'.format(seller.seller_id)
                    dst = '{}_enter.seller'.format(seller.seller_id)
                    try:
                        os.rename(src, dst)
                    except:
                        pass

                    dump_history()
                    
                    cmd = '{} {}'.format(sys.argv[0], dst)
                    text = '岛:{name} 价格:{price} 密码:{password}\n备注:{remark}\n取消:{cmd}'.format(cmd=cmd, **island)
                    print(text)
                    data = {
                        'msgtype': 'text',
                        'text': {
                            'content': text
                        }, 
                    }
                    notify(data)
                    print('进入续期循环\n')
                    state = 'extend'
                elif code == 2:
                    # 排队中
                    print('{name} 价格:{price} 排队:{queue_pos}/{queue_length}'.format(**island), end='\r')
                    time.sleep(5)
                else:
                    print('未识别:{} {} {}'.format(state, code, msg))
                
            elif state == 'extend':
                time.sleep(10)
                code, msg = seller.seller_extend()
                #print('[{}] {}'.format(code, msg))
                if code == 0:
                    pass
                else:
                    state = 'status'
            else:
                break
        except Exception as e:
            print(e)
            raise e

        time.sleep(1)


class SellerState:
    def __init__(self, seller):
        self.seller = seller
        self.state = 'status'

    def check_state(self):
        try:
            if self.state == 'status':
                code, msg, island = self.seller.seller_status()
                if code == 0:
                    # 不在队伍中
                    print('闲置中\n')
                    self.state = 'pick'
                elif code == 1:
                    # 排到队首
                    print('\n可以登岛\n')
                    src = '{}_queue.seller'.format(self.seller.seller_id)
                    dst = '{}_enter.seller'.format(self.seller.seller_id)
                    try:
                        os.rename(src, dst)
                    except:
                        pass
                    
                    cmd = '{} {}'.format(sys.argv[0], dst)
                    text = '岛:{name} 价格:{price} 密码:{password}\n备注:{remark}\n取消:{cmd}'.format(cmd=cmd, **island)
                    print(text)
                    data = {
                        'msgtype': 'text',
                        'text': {
                            'content': text
                        }, 
                    }
                    notify(data)
                    print('进入续期循环\n')
                    self.state = 'extend'
                elif code == 2:
                    # 排队中
                    print('{name} 价格:{price} 排队:{queue_pos}/{queue_length}'.format(**island))
                else:
                    print('未识别:{} {} {}'.format(self.state, code, msg))
                
            elif self.state == 'extend':
                code = 0  #code, msg = self.seller.seller_extend()
                #print('[{}] {}'.format(code, msg))

                if code == 0:
                    pass
                else:
                    self.state = 'status'
            else:
                return
        except Exception as e:
            print(e)
            raise e

        return self.state


def multi_seller_robot(name, strategy, max_sellers):
    robot_seller = Seller()
    sellers = {}  # island_id -> SellerState
    history = {}

    state = 'pick'
    while True:
        try:
            if state == 'pick':
                page = 1
                print('获取第{}页岛列表...'.format(page), end='')
                code, msg, islands = robot_seller.island_list(page)
                print('[{}] {} 岛数量:{}\n'.format(code, msg, len(islands)))
                island_id_list = strategy(islands)
                for island_id in island_id_list:
                    if (len(sellers) >= max_sellers) or (island_id in history):
                        continue

                    seller = Seller()
                    print('创建临时卖家<{}>...'.format(name), end='')
                    code, msg, seller_id = seller.seller_init(name)
                    print('[{}] {} ID:{}\n'.format(code, msg, seller_id))

                    island = islands[island_id]
                    print('<{}>加入<{}>岛的等候队伍...'.format(name, island['name']), end='')
                    code, msg = seller.seller_join(island_id)
                    print('[{}] {}\n'.format(code, msg))
                    if code == 0:
                        # 可以登岛
                        fname = '{}_queue.seller'.format(seller.seller_id)
                        seller.dump(fname)
                        sellers[island_id] = SellerState(seller)
                        history[island_id] = sellers[island_id]
                        #state = 'status'
                    elif code == 1:
                        # 开始排队
                        fname = '{}_queue.seller'.format(seller.seller_id)
                        seller.dump(fname)
                        sellers[island_id] = SellerState(seller)
                        history[island_id] = sellers[island_id]
                        #state = 'status'
                    elif code == 9:
                        # 已在队列中
                        sellers[island_id] = SellerState(seller)
                        history[island_id] = sellers[island_id]
                        #state = 'status'
                    else:
                        print('未识别:{} {} {}\n'.format(state, code, msg))
                else:
                    print('没有满足条件的岛', end='\r')
                    #time.sleep(1)
            else:
                print('错误的状态:{}'.format(state))
                break
        except Exception as e:
            print(e)
            #raise e

        time.sleep(10)

        todel = []
        for island_id, seller_state in sellers.items():
            seller_state = seller_state.check_state()
            if seller_state == 'extend':
                todel.append(island_id)

        for island_id in todel:
            del sellers[island_id]


def test_strategy(islands):
    global history
    sorted_islands = sorted(islands.items(), key=lambda item:item[1]['queue_length'])
    for island_id, island in sorted_islands:
        if island_id in history:
            continue

        name = island['name']
        price = island['price']
        remark = island['remark']
        seller_count = island['seller_count']
        max_seller = island['max_seller']
        queue_length = island['queue_length']
        #if remark.find('妹妹') >= 0:
        if price <= 300:
            return island_id

    return None


def test_multi_strategy(islands):
    sorted_islands = sorted(islands.items(), key=lambda item:item[1]['queue_length'])
    ret = []
    for island_id, island in sorted_islands:
        name = island['name']
        price = island['price']
        remark = island['remark']
        seller_count = island['seller_count']
        max_seller = island['max_seller']
        queue_length = island['queue_length']
        #if price >= 450:
        if remark.find('妹妹') >= 0:
            ret.append(island_id)

    return ret


def seller_quit(fname):
    seller = Seller.load(fname)
    seller.seller_quit()
    os.unlink(fname)


def main():
    if len(sys.argv) == 1:
        single_seller_robot('Alicia', test_strategy)
        #multi_seller_robot('t5w0rd', test_multi_strategy, 1)
    elif len(sys.argv) == 2:
        seller_quit(sys.argv[1])
        # quit all
        # ls *.seller|xargs -i{} python3 dodopass.py {}


if __name__ == '__main__':
    main()

