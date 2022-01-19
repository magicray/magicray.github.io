import re
import bs4
import math
import json
import time
import argparse
import requests
from logging import critical as log


def download(screen):
    url = 'https://www.screener.in/screens/{}/?include_old=yes&page='
    url = url.format(screen).lower()

    rows = list()
    headers = list()
    s_no_max = 0
    for i in range(1000):
        r = requests.get(url + str(i+1))

        if 200 != r.status_code:
            break

        page = bs4.BeautifulSoup(r.content, 'lxml')

        for h in page.select('th a'):
            title = re.sub(r'\W+', '_', h.text).strip('_').lower()

            if title not in headers:
                headers.append(title)

        flag = False
        for r in page.select('tr'):
            row = list()
            for c in r.children:
                if 'td' == c.name:
                    row.append(c.text.strip())
                    flag = True
            if row:
                s_no = int(row[0].strip('.'))
                if s_no > s_no_max:
                    rows.append(row)
                    s_no_max = s_no
                else:
                    flag = False
                    break

        if flag is False and rows:
            break

    result = dict()
    for row in rows:
        d = result.setdefault(row[1], dict())
        for i in range(len(headers)-2):
            try:
                d[headers[i+2]] = float(row[i+2])
            except Exception:
                d[headers[i+2]] = row[i+2]

    return result


def rank(field, data, descending=True):
    data = sorted([(v[field], k) for k, v in data.items()], reverse=descending)

    rank = dict()
    for i, (ebit, name) in enumerate(data):
        rank[name] = i

    return rank


def median(field, data):
    val = sorted([v[field] for k, v in data.items()])
    return val[-1], val[len(val)//2], val[0]


def portfolio(args):
    # Earnings yield > 0 AND
    # Price to Earning > 0 AND
    # Return on equity > 0 AND
    # Return on capital employed > 0 AND
    # YOY Quarterly sales growth > 0 AND
    # YOY Quarterly profit growth  > 0 AND

    # NPM latest quarter > 0 AND
    # OPM latest quarter > 0 AND
    # GPM latest quarter > 0 AND
    # Market Capitalization > 1000

    filename = 'investible.json'
    try:
        data = json.load(open(filename))
        assert(data['timestamp'] > time.time() - 86400)
    except Exception:
        log('downloading data')
        data = dict(timestamp=int(time.time()), data=download(args.screen))
        with open(filename, 'w') as fd:
            json.dump(data, fd)

    tmp = dict()
    for k, v in data['data'].items():
        if v['qtr_profit_var'] == '' or v['qtr_sales_var'] == '':
            continue

        if all('' != y for y in v.values()):
            tmp[k] = v

        v['value'] = max(v['earnings_yield'], 100/v['p_e'])
        v['profit'] = max(v['roce'], v['roe'])
        v['growth'] = min(v['qtr_profit_var'], v['qtr_sales_var'])

    mcaps = sorted([v['mar_cap_rs_cr'] for v in tmp.values()], reverse=True)
    threshold = mcaps[min(args.top, len(mcaps)-1)]
    data = {k: v for k, v in tmp.items() if v['mar_cap_rs_cr'] > threshold}
    assert(len(data) == args.top)

    t = time.time()
    log('columns(%d) rows(%d) msec(%d)',
        len(data[list(data.keys())[0]]), len(data), (time.time()-t)*1000)

    columns = ('roce', 'roe',
               'qtr_sales_var', 'qtr_profit_var',
               'earnings_yield', 'p_e',
               'mar_cap_rs_cr', 'cmp_rs')

    # roe = rank('roe', data)
    # roce = rank('roce', data)
    # pe = rank('p_e', data, False)
    # e_yield = rank('earnings_yield', data)
    profit = rank('profit', data)
    growth = rank('growth', data)
    value = rank('value', data)

    stats = {f: median(f, data) for f in columns}

    final_rank = [(
        # roce[name] + roe[name] +   # Quality
        # 2*growth[name] +           # Growth
        # pe[name] + e_yield[name],  # Value
        profit[name] + growth[name] + value[name],
        name) for name in profit]

    def print_header():
        headers = '{:16s}' + '{:>8s}' * 9
        print(headers.format(time.strftime('%Y-%m-%d'),
                             'ROCE', 'ROE',
                             'SALES', 'PROFIT',
                             'YIELD', 'P/E',
                             'MCAP', 'CMP', 'QTY'))

    print_header()
    for i, f in enumerate(('Max', 'Median')):
        print(('%s\t\t' + '%8.2f' * 6 + '%8d%8d') % (
            f,
            stats['roce'][i],
            stats['roe'][i],
            min(999, stats['qtr_sales_var'][i]),
            min(999, stats['qtr_profit_var'][i]),
            stats['earnings_yield'][i],
            stats['p_e'][i],
            stats['mar_cap_rs_cr'][i],
            stats['cmp_rs'][i]))
    print('-' * 88)

    avg = {k: 0 for k in columns}
    avg['count'] = 0

    if int(args.count) != args.count:
        args.count = args.count * len(final_rank)

    args.count = int(args.count)

    start = 0
    args.count = args.count if args.count else len(final_rank)
    if args.count < 0:
        args.count *= -1
        start = len(final_rank) - args.count

    mcap_count = {k: 0 for k in [mcaps[min(i, len(mcaps)-1)]
                                 for i in range(99, len(mcaps)+100, 100)]}
    per_stock = args.amount / args.count
    count = 0
    stock_list = list()
    for n, (_, name) in enumerate(sorted(final_rank)[start:start+args.count]):
        v = data[name]
        v['name'] = name
        v['rank'] = count+1
        v['qtr_profit_var'] = min(999, v['qtr_profit_var'])
        stock_list.append(v)

        qty = 0
        available = per_stock if args.amount > per_stock else args.amount
        qty = math.ceil(available / v['cmp_rs'])

        if qty*v['cmp_rs'] > max(available, args.amount):
            qty -= 1

        if args.amount and qty < 1:
            break

        args.amount -= qty*v['cmp_rs']

        print(('%-16s' + '%8.2f' * 6 + '%8d%8d%8d') % (
            name, v['roce'], v['roe'],
            v['qtr_sales_var'], v['qtr_profit_var'],
            v['earnings_yield'], v['p_e'],
            v['mar_cap_rs_cr'], v['cmp_rs'],
            qty))

        count += 1
        for k in mcap_count:
            if v['mar_cap_rs_cr'] >= k:
                mcap_count[k] += 1

        for k in columns:
            avg[k] += v[k]
        avg['count'] += 1

    for k in columns:
        avg[k] /= avg['count']

    with open('magicrank.json') as fd:
        prev = json.load(fd)

    prev_names = set([s['name'] for s in prev['data'] if s['rank'] <= args.hold])
    stock_names = set([s['name'] for s in stock_list if s['rank'] <= args.hold])
    with open('magicrank.json', 'w') as fd:
        ts = int(time.time())
        sold = prev.get('sold', {})
        sold.update({s: ts for s in set(prev_names) - set(stock_names)})
        for s in list(sold.keys()):
            if s in stock_names:
                sold.pop(s)
        json.dump(dict(
                data=stock_list,
                date=int(time.time()),
                symbol=prev['symbols'],
                sold={k: v for k, v in sold.items() if v+86400*90 > ts},
                url='https://www.screener.in/screens/' + args.screen),
            fd, sort_keys=True, indent=4)

    print('-' * 88)
    print_header()
    print(('%-16s' + '%8.2f' * 6 + '%8d%8d') % (
        'Average', avg['roce'], avg['roe'],
        avg['qtr_sales_var'], avg['qtr_profit_var'],
        avg['earnings_yield'], avg['p_e'],
        avg['mar_cap_rs_cr'], avg['cmp_rs']))

    prev = 0
    for i, k in enumerate(sorted(mcap_count, reverse=True)):
        if mcap_count[k] - prev:
            log('top(%d) mcap(%d) count(%d) total(%d)',
                min((i+1)*100, len(mcaps)-1, args.top), k,
                mcap_count[k]-prev, mcap_count[k])
        prev = mcap_count[k]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--screen', dest='screen', default='290555/Investable')
    parser.add_argument('--amount', dest='amount', type=int, default=0)
    parser.add_argument('--count', dest='count', type=float, default=200)
    parser.add_argument('--hold', dest='hold', type=int, default=100)
    parser.add_argument('--top', dest='top', type=int, default=200)
    portfolio(parser.parse_args())


if __name__ == '__main__':
    main()
