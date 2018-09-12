#!/usr/bin/env python
#coding:utf-8

import selenium.webdriver
import sys
import time
import math
import random

def find_element_by_xpath(browser, xpath, timeout=-1):
    tag = None
    while tag is None:
        try:
            tag = browser.find_element_by_xpath(xpath)
            if not tag.is_displayed():
                tag = None
                raise Exception('tag is not visible')

        except:
            if timeout == 0:
                return tag
            timeout -= 1
            time.sleep(1)

    time.sleep(0.1)
    return tag

def register(user, passwd, headless=True):
    url = 'https://login.youyu.hk/login/#!/register?type=mobile'

    opt = selenium.webdriver.ChromeOptions()
    #opt.add_argument('--proxy-server=10.0.0.226:53128')
    opt.add_argument('--proxy-server=tvpsx.tutils.com:53128')
    if headless:
        opt.set_headless()
    b = selenium.webdriver.Chrome(options=opt)

    b.get(url)

    ipt = find_element_by_xpath(b, '//input[@name="Reg-phone"]')
    ipt.send_keys(user)

    ipt = find_element_by_xpath(b, '//div[@class="password"]/input')
    ipt.send_keys(passwd)

    ipt = find_element_by_xpath(b, '//input[@class="btn wm-btn"]')
    ipt.click()
    
    sys.stdout.write('输入%s的验证码: ' % (user,))
    sys.stdout.flush()
    code = sys.stdin.readline().strip()
    ipt = find_element_by_xpath(b, '//input[@name="Reg-phonecode"]')
    ipt.send_keys(code)

    btn = find_element_by_xpath(b, u'//button[@class="btn-register wm-btn"]')
    btn.click()

    p = find_element_by_xpath(b, u'//div[@class="title"]/p[contains(text(), "注册成功")]')

    b.close()
    b.quit()

def guess(user, passwd, up=True, headless=True):
    url = 'https://m.youyu.cn/c/acts/prediction/?mid=CA001025#/'

    opt = selenium.webdriver.ChromeOptions()
    #opt.add_argument('--proxy-server=10.0.0.226:53128')
    opt.add_argument('--proxy-server=tvpsx.tutils.com:53128')
    if headless:
        opt.set_headless()
    b = selenium.webdriver.Chrome(options=opt)

    b.get(url)

    btn = find_element_by_xpath(b, '//button[@class="btn_join"]')
    btn.click()

    ipt = find_element_by_xpath(b, '//input[@class="longer"]')
    ipt.send_keys(user)

    ipt = find_element_by_xpath(b, '//input[@class="login_password"]')
    ipt.send_keys(passwd)

    btn = find_element_by_xpath(b, '//div[@class="btn"]/button')
    btn.click()

    btn = find_element_by_xpath(b, '//button[@class="btn_join"]')
    btn.click()
    
    div = find_element_by_xpath(b, u'//div[contains(text(), "等待开奖中")]', timeout=3)
    if div:
        b.close()
        b.quit()
        return
    
    div = find_element_by_xpath(b, u'//div[@class="wechat_code"]', timeout=0)
    if div:
        print '%s: %s' % (user, div.text)
        b.close()
        b.quit()
        return

    btn = find_element_by_xpath(b, '//button[@class="'+('goup bounceLeft' if up else 'godown bounceRight')+'"]')
    #time.sleep(1)
    btn.click()
    print '%s: %s' % (user, 'up' if up else 'down')

    #div = find_element_by_xpath(b, u'//div[contains(text(), "等待开奖中")]')
    time.sleep(3)

    b.close()
    b.quit()

def batch(index=0):
    pairs = [

        ['13074626489', 'test1234'],
        ['15726693988', 'xiang755896'],
        ['13366034990', 'xiang755896'],
        ['13552218637', '0208suixin'],
        ['13998192096', 'wb8131790'],
        ['17640199716', 'wb8131790'],
        ['16619970443', 'wyy970327'],
        ['13263516535', 'wyy970327'],

        ['13217816405', 'test1234'],
        ['13942418454', 'Reotest1234'],
        ['18501115839', 'test1234'],
        ['13941420885', 'test1234'],
        ['17501078790', 'test1234'],
        ['17610352168', '2857922521lhy'],
        ['13842445375', '2857922521lhy']
    ]
    
    res = (random.random()<0.5)
    for user, passwd in pairs:
        if index == 0:
            guess(user, passwd, res, False)
            res = not res
        else:
            index -= 1

batch()
