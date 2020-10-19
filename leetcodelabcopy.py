#!/usr/bin/env python

import selenium.webdriver
import json
import sys
import time


def load_lab(name):
    with open(name, 'r') as fp:
        return json.load(fp)


def add_fav(fav_name):
    fav = None
    while fav is None:
        time.sleep(0.1)
        try:
            fav = b.find_element_by_class_name('css-11hfr6f-Button')
        except:
            pass

    fav.click()
    pop = None
    while pop is None:
        time.sleep(0.1)
        try:
            pop = b.find_element_by_class_name('popper-container')
        except:
            pass
    btn = None
    while btn is None:
        time.sleep(0.1)
        try:
            btn = pop.find_element_by_xpath('//div[contains(text(), "{}")]'.format(fav_name))
        except:
            pass
    time.sleep(0.5)
    btn.click()
    time.sleep(0.1)


def gen_url(slug):
    return 'https://leetcode-cn.com/problems/{}/'.format(slug)


qs = load_lab(sys.argv[1])
opt = selenium.webdriver.ChromeOptions()
b = selenium.webdriver.Chrome(options=opt)
b.get('https://leetcode-cn.com/problems/two-sum/')

time.sleep(40)

for i, q in enumerate(qs):
    if i+1 <= 710:
        continue
    url = gen_url(q['titleSlug'])
    b.get(url)
    add_fav(sys.argv[2])
    print('{}/{}'.format(i+1, len(qs)))

