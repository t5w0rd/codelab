#!/usr/bin/env python
#coding:utf-8

import selenium.webdriver
import sys
import time

def find_element_by_xpath(browser, xpath):
    tag = None
    while tag is None:
        try:
            tag = browser.find_element_by_xpath(xpath)
            if not tag.is_displayed():
                tag = None
                raise Exception('tag is not visible')

        except:
            time.sleep(1)

    time.sleep(0.1)
    return tag

def register(user, passwd, headless=True):
    url = 'https://login-stage.youyu.hk/login/#!/register?type=mobile'

    opt = selenium.webdriver.ChromeOptions()
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
    url = 'https://m-stage.youyu.cn/c/acts/prediction/?mid=CA001025#/'

    opt = selenium.webdriver.ChromeOptions()
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

    btn = find_element_by_xpath(b, '//button[@class="'+('goup bounceLeft' if up else 'godown bounceRight')+'"]')
    btn.click()

    #b.close()
    #b.quit()

