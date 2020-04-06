#!/usr/bin/env python
# -*- coding: utf-8 -*-

import selenium.webdriver
import time
import requests
import hmac
import hashlib
import base64
import urllib.parse


notify_url = r'https://oapi.dingtalk.com/robot/send?access_token=924087974c083883dce8820b58ffacd95570fe53c55aabb002ec60d14b278460'
secret = r'SECd00250727f2cd97d897b3387fe2aeedd2354a85e8ebed1cf32ac49cf6d141e45'
username = r'username'
password = r'password'

url = r'https://bbs.nga.cn/thread.php?stid=21103085'
tfmt = r'%y-%m-%d %H:%M'


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


def chrome():
    opt = selenium.webdriver.ChromeOptions()
    c = selenium.webdriver.Chrome(options=opt)
    return c


def login(c):
    c.get(url)
    state = 'init'

    while True:
        print('state:', state)
        if state == 'init':
            try:
                login = c.find_element_by_xpath(r'//div[@id="mainmenu"]//a[contains(text(),"登录")]')
                login.click()
                state = 'input'
            except:
                pass

        elif state == 'input':
            try:
                iframe = c.find_element_by_xpath(r'//div[@id="commonuiwindow"]//iframe')
                c.switch_to.frame(iframe)
                iframe = c.find_element_by_xpath(r'//iframe[@id="iff"]')
                c.switch_to.frame(iframe)
                
                name = c.find_element_by_xpath(r'//input[@id="name"]')
                name.click()
                name.send_keys(username)
                
                passwd = c.find_element_by_xpath(r'//input[@id="password"]')
                passwd.click()
                passwd.send_keys(password)
                
                submit = c.find_element_by_xpath(r'//a[text()="登 录"]')
                submit.click()
                
                state = 'vcode'
            except:
                c.switch_to.default_content()

        elif state == 'vcode':
            try:
                vcode = c.find_element_by_xpath(r'//input[contains(@placeholder,"输入图形验证码")]')
                vcode.click()
                state = 'manual'
            except:
                pass

        elif state == 'manual':
            try:
                alert = c.switch_to.alert
                text = alert.text
                alert.accept()
                if text.find('登录成功') < 0:
                    submit = c.find_element_by_xpath(r'//a[text()="登 录"]')
                    submit.click()
                    raise Exception()

                c.switch_to.default_content()
                state = 'done'
            except:
                pass
        else:
            break

        time.sleep(1)


def monitor(c):
    cache = set()
    first = True

    while True:
        c.get(url)
        time.sleep(20)

        try:
            tbl = c.find_element_by_xpath(r'//table[contains(@class, "forumbox")]')
        except:
            continue

        datas = []
        trs = tbl.find_elements_by_xpath(r'tbody/tr')
        for tr in trs:
            td2 = tr.find_element_by_xpath(r'td[@class="c2"]')
            a = td2.find_element_by_xpath(r'a')
            title = a.text
            href = a.get_attribute('href')

            td3 = tr.find_element_by_xpath(r'td[@class="c3"]')
            span = td3.find_element_by_xpath(r'span')
            date = span.get_attribute('title')

            text = '{} {}'.format(date, title)

            if href in cache:
                continue

            data = {
                'msgtype': 'link',
                'link': {
                    'text': text,
                    'title': title,
                    'picUrl': 'https://img4.nga.178.com/proxy/cache_attach/ficon/710u.png',
                    'messageUrl': href
                }
            }

            if first or notify(data):
                cache.add(href)

        first = False


def main():
    c = chrome()
    #login(c)
    monitor(c)


if __name__ == '__main__':
    main()
