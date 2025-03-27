#!/usr/bin/env python
# -*- coding: utf-8 -*-

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from typing import Iterable
import time
from urllib.parse import urljoin
import requests
from PIL import Image
from io import BytesIO


def get_ui(driver: webdriver.Edge):
    txt = driver.find_element(By.ID, "chat-input")
    r1 = driver.find_element(By.XPATH, "//*[contains(text(), '深度思考')]")
    search = driver.find_element(By.XPATH, "//*[contains(text(), '联网搜索')]")
    send = driver.find_element(By.CLASS_NAME, 'f6d670')
    # txt.send_keys()
    # send.click()
    return txt, r1, search, send

def wait_login(driver: webdriver.Edge):
    txt = driver.find_elements(By.ID, "chat-input")
    while len(txt) == 0:
        time.sleep(0.5)
        txt = driver.find_elements(By.ID, "chat-input")

def wait_generating(driver: webdriver.Edge):
    
    time.sleep(0.5)
    send = driver.find_elements(By.CLASS_NAME, 'f6d670')
    while len(send) == 0 or send[0].get_attribute('aria-disabled') == 'false':
        send = driver.find_elements(By.CLASS_NAME, 'f6d670')
        time.sleep(0.5)

def get_last_assistant(driver: webdriver.Edge) -> str:
    lst = driver.find_elements(By.XPATH, "//div[@class='ds-markdown ds-markdown--block']")
    return lst[-1].text

def chat(driver: webdriver.Edge, message: str, stream: bool) -> Iterable:
    count = len(driver.find_elements(By.XPATH, "//div[@class='ds-markdown ds-markdown--block']"))
    
    input = driver.find_element(By.ID, "chat-input")
    input.send_keys(message)
    send = driver.find_element(By.CLASS_NAME, 'f6d670')
    send.click()
    
    # 等待输出
    while len(driver.find_elements(By.XPATH, "//div[@class='ds-markdown ds-markdown--block']")) == count:
        time.sleep(0.5)
    
    if stream:
        txt = ''
        send = driver.find_elements(By.CLASS_NAME, 'f6d670')
        while len(send) == 0 or send[0].get_attribute('aria-disabled') == 'false':
            time.sleep(0.1)
            send = driver.find_elements(By.CLASS_NAME, 'f6d670')
            new_txt = get_last_assistant(driver)
            delta = len(new_txt) - len(txt)
            if delta > 0:
                txt = new_txt
                yield txt[-delta:]
        
        new_txt = get_last_assistant(driver)
        delta = len(new_txt) - len(txt)
        if delta > 0:
            txt = new_txt
            yield txt[-delta:]
    else:
        send = driver.find_elements(By.CLASS_NAME, 'f6d670')
        while len(send) == 0 or send[0].get_attribute('aria-disabled') == 'false':
            send = driver.find_elements(By.CLASS_NAME, 'f6d670')
            time.sleep(0.5)
        yield get_last_assistant(driver)


def show_qrcode(driver: webdriver.Edge):
    img = driver.find_element(By.CSS_SELECTOR, '.js_qrcode_img.web_qrcode_img')
    img_url = urljoin(url, img.get_attribute('src'))
    response = requests.get(img_url)
    # 将图片内容加载到PIL图像对象中
    image = Image.open(BytesIO(response.content))

    image = image.convert("1")  # 1-bit pixels, black and white, stored with one pixel per byte

    # 调整图像大小
    width, height = image.size
    image = image.resize((int(width * 0.1), int(height * 0.1)))

    # 遍历像素，打印到终端
    for y in range(image.height):
        line = ""
        for x in range(image.width):
            # 获取像素值，0 是黑色，255 是白色
            pixel = image.getpixel((x, y))
            if pixel == 0:
                line += "  "  # 白色部分留空
            else:
                line += "██"  # 黑色部分用字符填充
                
        print(line)


if __name__ == '__main__':
    opts = Options()
    opts.add_argument("--headless")  # 启用无头模式
    opts.add_argument("--disable-gpu")  # 禁用 GPU 加速（某些系统需要）

    driver = webdriver.Edge(options=opts)

    url = 'https://open.weixin.qq.com/connect/qrconnect?appid=wx932d4fdaf46d5611&scope=snsapi_login&redirect_uri=https%3A%2F%2Fchat.deepseek.com%2Fapi%2Fv0%2Fusers%2Foauth%2Fwechat%2Fcallback&state=&login_type=jssdk&self_redirect=false&styletype=&sizetype=&bgcolor=&rst=&stylelite=1'
    # url = 'https://chat.deepseek.com/'
    driver.get(url)
    
    show_qrcode(driver)
    
    wait_login(driver)
    
    while True:
        message = input('User: ').strip()
        while len(message) == 0:
            message = input('User: ').strip()
        
        print('Assistant: ', end='', flush=True)
        for txt in chat(driver, message, stream=True):
            print(txt, end='', flush=True)
        print()
