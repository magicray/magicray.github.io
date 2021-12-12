import time
import json
import requests
import argparse
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait


class ICICIDirect():
    def __init__(self):
        url = 'https://secure.icicidirect.com'
        self.cashbuy_url = url + '/trading/equity/cashbuy'
        self.orderbook_url = url + '/trading/equity/orderbook'

        self.driver = webdriver.Chrome()
        self.driver.get(url + '/customer/login')
        self.wait = WebDriverWait(self.driver, 1000)
        # self.e('txtuid').send_keys('<username>')
        # self.e('txtPass').send_keys('<password>')
        # self.e('txtDOB').send_keys('<ddmmyyyy>')
        # self.e('btnlogin').click()

    def byid(self, elem_id):
        return self.driver.find_element_by_id(elem_id)

    def byxpath(self, selector):
        return self.driver.find_element_by_xpath(selector)

    def wait_for_page(self, url):
        self.wait.until(lambda d: d.current_url == url)

    def buy(self, stock_code, quantity):
        self.driver.get(self.cashbuy_url)
        self.byxpath("//label[@for='rdonse']").click()
        self.byxpath("//label[@for='rdomarket']").click()
        self.byid('stcode').send_keys(stock_code)
        self.byid('FML_QTY').send_keys(quantity)


def main():
    r = requests.get('https://magicray.github.io/map.json', verify=False)
    stock_codes = r.json()

    r = requests.get('https://magicray.github.io/magicrank.json', verify=False)
    buy_list = [(s['rank'],s) for s in r.json()['data'] if s['rank'] < 101]
    buy_list = [s for _, s in buy_list]
    icici = ICICIDirect()

    for s in buy_list:
        qty = int((ARGS.amount/100)/s['cmp_rs'])

        if qty < 1:
            continue

        code = stock_codes.get(s['name'], 'Not Found')
        print((s['rank'], s['name'], code, s['cmp_rs'], qty))
        icici.wait_for_page(icici.orderbook_url)
        icici.buy(code, qty)


if __name__ == '__main__':
    ARGS = argparse.ArgumentParser()

    ARGS.add_argument('--amount', dest='amount', type=int, default=0)
    ARGS = ARGS.parse_args()
    main()
