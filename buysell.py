import time
import csv
import requests
import argparse
from logging import critical as log

requests.packages.urllib3.disable_warnings()

def main():
    portfolio = dict()
    with open(ARGS.portfolio) as fd:
        csvreader = csv.reader(fd)
        headers = next(csvreader)
        for record in csvreader:
            d = dict(zip(headers, record))
            portfolio[d['Stock Symbol']] = float(d['Value At Market Price'])

    r = requests.get('https://magicray.github.io/magicrank.json', verify=False)
    r = r.json()
    data = r['data']
    stock_codes = r['symbol']

    buy_list = [(s['rank'], s) for s in data if s['rank'] <= len(data)/2]
    buy_list = [s for _, s in sorted(buy_list)]

    buy_set = set([stock_codes[b['name'].replace('.', '')] for b in buy_list])
    existing_set = set(portfolio.keys())
    print('Sell : {}'.format(sorted(existing_set - buy_set)))

    minimum_value = ARGS.amount / len(buy_list)

    for b in buy_list:
        symbol = stock_codes[b['name'].replace('.', '')]
        existing_value = portfolio.pop(symbol, 0)
        if minimum_value > existing_value:
            buy_qty = int((minimum_value - existing_value) / b['cmp_rs'])
            buy_value = int(buy_qty * b['cmp_rs'])

            print('{} \t{} \t{} \t{} \t{} \t{}'.format(
                int(existing_value), buy_qty, int(b['cmp_rs']),
                buy_value, symbol, b['name']))


if __name__ == '__main__':
    ARGS = argparse.ArgumentParser()
    ARGS.add_argument('--portfolio', dest='portfolio')
    ARGS.add_argument('--amount', dest='amount', type=int, default=0)
    ARGS = ARGS.parse_args()
    main()
