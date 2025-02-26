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

    stock_count = min(50, len(data)//2)
    buy_list = [(s['rank'], s) for s in data if s['rank'] < stock_count]
    buy_list = [s for _, s in sorted(buy_list)]
    buy_set = set([stock_codes[b['name'].replace('.', '')] for b in buy_list])

    sell_start_index = len(data) // 2
    hold_list = [(s['rank'], s) for s in data if s['rank'] < sell_start_index]
    hold_list = [s for _, s in sorted(hold_list)]
    hold_set = set([stock_codes[s['name'].replace('.', '')] for s in hold_list])

    existing_set = set(portfolio.keys())
    print('Sell : {}'.format(sorted(existing_set - hold_set)))

    minimum_value = ARGS.amount / stock_count
    low_threshold = 1.0
    high_threshold = 1.0

    for b in buy_list:
        symbol = stock_codes[b['name'].replace('.', '')]
        existing_value = portfolio.pop(symbol, 0)
        if minimum_value * low_threshold > existing_value:
            buy_qty = int((minimum_value * high_threshold - existing_value) / b['cmp_rs'])
            buy_value = int(buy_qty * b['cmp_rs'])

            print('{:>7d} {:>6d} {:>7d} {:>9d}\t{}\t{}'.format(
                int(existing_value), buy_qty, int(b['cmp_rs']),
                buy_value, symbol, b['name']))


if __name__ == '__main__':
    ARGS = argparse.ArgumentParser()
    ARGS.add_argument('portfolio', help='Portfolio file from icicidirect')
    ARGS.add_argument('amount', type=float, help='Amount in crores')
    ARGS = ARGS.parse_args()
    ARGS.amount *= 10000000
    main()
