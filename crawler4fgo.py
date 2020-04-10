#!/usr/bin/env python
#coding:utf-8

import requests
from lxml import etree
import os
from collections.abc import Iterator


wiki_url_base = r'https://fgo.wiki'


def get_full_url(relative_path):
    return wiki_url_base + relative_path


def try_xpath(html, xpath_fmt, *args):
    res = html.xpath(xpath_fmt.format(*args))
    if len(res) is 0:
        return None
    return res[0]


servant_page_url_fmt = get_full_url(r'/w/{name_link}')

servant_card_names = ['初始状态', '灵基再临I', '灵基再临Ⅲ', '灵基再临Ⅳ', '愚人节', '初始状态～灵基再临Ⅲ', '初始状态~灵基再临Ⅲ', '普通', '灵衣']
# servant_card_names = ['初始状态～灵基再临Ⅲ', '初始状态~灵基再临Ⅲ', '普通']

servant_card_page_xpath_fmt = r'//div[@title="{}"]/p/a/@href'


def parser_function(data, *args):
    """
    解析器定义模板
    yield next_url, next_parser, next_args
    or
    return next_url, next_parser, next_args
    or
    nothing to return
    :param data:
    :param args:
    :return: next_url, next_parser, next_args
    """
    pass


def parse_servants_svt(data):
    """
    解析英灵图鉴中的csv数据
    :param data:
    :return:
    """
    pass


def load_csv_file(data, path):
    """
    加载csv文件
    :param data:
    :param path:
    :return:
    """
    with open(path, 'r') as fp:
        return None, parse_servants_data, (fp.read(),)


def parse_servants_data(data, servants_data):
    """
    解析所有从者数据
    :param data:
    :param servants_data:
    :return:
    """
    lns = servants_data.splitlines()
    titles = lns[0].split(',')
    for ln in lns[1:]:
        fields = ln.split(',')
        servant = {titles[i]: item for i, item in enumerate(fields)}
        next_url = servant_page_url_fmt.format_map(servant)
        yield next_url, parse_servant_page, (servant,)


def parse_servant_page(data, servant):
    """
    解析从者页
    :param data:
    :param servant:
    :return:
    """
    html = etree.HTML(data)
    for card_name in servant_card_names:
        href = try_xpath(html, servant_card_page_xpath_fmt, card_name)
        if href is not None:
            yield get_full_url(href), parse_servant_card_page, (servant, card_name)


servant_card_image_xpath_fmt = r'//div[@class="fullImageLink"]/a/@href'


def parse_servant_card_page(data, servant, card_name):
    """
    解析从者卡面页
    :param data:
    :param servant:
    :param card_name:
    :return:
    """
    html = etree.HTML(data)
    href = try_xpath(html, servant_card_image_xpath_fmt)
    if href is not None:
        yield get_full_url(href), save_servant_card_image, (servant, card_name)


save_base = r'crawler4fgo'


def save_servant_card_image(data, servant, card_name):
    """
    保存从者图片
    :param data:
    :param servant:
    :param card_name:
    :return:
    """
    path = save_base + r'/{name_link}'.format_map(servant)
    os.makedirs(path, mode=0o755, exist_ok=True)

    file_name = r'{}/{}.png'.format(path, card_name)
    print('保存[{}]'.format(file_name))
    with open(file_name, 'wb') as fp:
        fp.write(data)


def invoke_parser(url, parser, args, add_parse_item):
    def next_invoke(cur_result):
        if isinstance(cur_result, tuple) and len(cur_result) == 3:
            next_url, next_parser, next_args = cur_result
            print('新增解析项[{}]'.format(next_parser.__name__))
            add_parse_item(next_url, next_parser, next_args)
        elif cur_result is None:
            pass
        else:
            print('解析器返回结果格式错误[{}]'.format(parser.__name__))

    data = None
    if url is not None:
        print('获取[{}]'.format(url))
        with requests.get(url) as rsp:
            data = rsp.content

    print('调用解析器[{}]'.format(parser.__name__))
    res = parser(data, *args)
    if isinstance(res, Iterator):
        for each in res:
            next_invoke(each)
    else:
        next_invoke(res)


def simple_add_parse_item(url, parser, args):
    invoke_parser(url, parser, args, simple_add_parse_item)



import multiprocessing
import multiprocessing.pool
from typing import Optional
import threading


mgr = None
pool = None
q = None


def multi_parse_add(url, parser, args):
    global q
    q.put((url, parser, args))


def multi_worker(q):
    while True:
        item = q.get()
        url, parser, args = item
        invoke_parser(url, parser, args, multi_parse_add)


def start_multi_crawler(workers=4):
    global mgr, pool, q
    mgr = multiprocessing.Manager()
    q = mgr.Queue()
    pool = multiprocessing.Pool(workers)
    res = pool.starmap_async(multi_worker, [(q,)] * workers)
    multi_parse_add(None, load_csv_file, ('fgo_csv.txt',))
    res.get()


if __name__ == '__main__':
    #simple_add_parse_item(None, load_csv_file, ('fgo_csv.txt',))
    start_multi_crawler(8)
