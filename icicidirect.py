import requests
import argparse
from logging import critical as log
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

    def wait_for_buy_button(self):
        self.wait.until(lambda d: d.find_element_by_xpath(
            "//input[@type='button' and @value='Buy']"))

    def wait_for_place_another_order_button(self):
        self.wait.until(lambda d: d.find_element_by_xpath(
            "//input[@type='button' and @value='Place another order']"))

    def buy(self, stock_code, quantity):
        self.driver.get(self.cashbuy_url)
        self.byxpath("//label[@for='rdonse']").click()
        self.byxpath("//label[@for='rdomarket']").click()
        self.byid('stcode').send_keys(stock_code)
        self.byid('FML_QTY').send_keys(quantity)
        self.byxpath("//input[@type='button' and @value='Buy']").click()


def main():
    r = requests.get('https://magicray.github.io/magicrank.json', verify=False)
    r = r.json()
    data = r['data']
    stock_codes = r['symbol']

    buy_list = [(s['rank'], s) for s in data if s['rank'] <= ARGS.count]
    buy_list = [s for _, s in buy_list]

    if ARGS.amount > 0:
        icici = ICICIDirect()

    for s in buy_list:
        qty = int((ARGS.amount/ARGS.count)/s['cmp_rs'])
        code = stock_codes[s['name'].replace('.', '')]
        log((s['rank'], s['name'], code, s['cmp_rs'], qty))

        if qty > 0:
            # icici.wait_for_page(icici.orderbook_url)
            icici.wait_for_buy_button()
            icici.buy(code, qty)
            icici.wait_for_place_another_order_button()

    # if ARGS.amount > 0:
    #     icici.wait_for_page(icici.orderbook_url)


if __name__ == '__main__':
    ARGS = argparse.ArgumentParser()

    ARGS.add_argument('--count', dest='count', type=int, default=50)
    ARGS.add_argument('--amount', dest='amount', type=int, default=0)
    ARGS = ARGS.parse_args()
    main()
