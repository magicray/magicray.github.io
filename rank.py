import re
import bs4
import math
import json
import time
import argparse
import requests
from logging import critical as log

value_screen = ('903587/value', '18y63mipg9g6ygbhwyigxse1olb4r61i')
growth_screen = ('879125/growth', 'fheukf655ba57h3ixd7j3j2l6ph0k2bx')
quality_screen = ('878969/quality', 'qpgob75yjt4dd6jn1zwkgr14yswmxuwk')


def download(screen, sessionid):
    url = 'https://www.screener.in/screens/{}/?include_old=yes&page='
    url = url.format(screen).lower()

    rows = list()
    headers = list()
    s_no_max = 0
    for i in range(1000):
        r = requests.get(url + str(i+1), headers={
            'accept-encoding': 'gzip',
            'cookie': 'sessionid={};'.format(sessionid)})

        assert(200 == r.status_code)
        log('downloaded {}'.format(url + str(i+1)))

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
            if row and row[0].strip():
                s_no = int(row[0].strip('.'))
                if s_no > s_no_max:
                    rows.append(row)
                    s_no_max = s_no
                else:
                    flag = False
                    break

        if flag is False and rows:
            break

        # To avoid flooding the server with requests and getting thrown out
        time.sleep(1)

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
    # OPM > 0 AND
    # Return on equity > 0 AND
    # Return on assets > 0 AND
    # Return on invested capital > 0 AND
    # Return on capital employed > 0 AND
    #
    # Sales growth > 0 AND
    # Profit growth > 0 AND
    # Operating profit growth > 0 AND
    #
    # Earnings yield > 0 AND
    # Price to Sales > 0 AND
    # Price to Earning > 0 AND
    # Price to book value > 0 AND
    #
    # EPS > 0 AND
    # EBIT > 0 AND
    # Net profit > 0 AND
    # Profit after tax > 0 AND
    # Operating profit > 0 AND
    #
    # EBIT latest quarter > 0 AND
    # EBIT preceding quarter > 0 AND
    # Operating profit latest quarter > 0 AND
    # Operating profit preceding quarter > 0 AND
    # Operating profit 2quarters back > 0 AND
    # Operating profit 3quarters back > 0 AND
    #
    # Sales > Net profit AND
    # Sales > Operating profit AND
    #
    # Current ratio > 1 AND
    # Net worth > 0 AND
    # Book value > 0 AND
    # Total Assets > 0

    filename = 'universe.json'
    try:
        data = json.load(open(filename))
        assert(data['timestamp'] > time.time() - 86400)
    except Exception:
        data = dict()
        for screen, sessionid in (value_screen, growth_screen, quality_screen):
            for key, value in download(screen, sessionid).items():
                if key in data:
                    data[key].update(value)
                else:
                    data[key] = value

        data = dict(timestamp=int(time.time()), data=data)
        with open(filename, 'w') as fd:
            json.dump(data, fd)

    tmp = dict()
    for k, v in data['data'].items():
        v.pop('5yrs_return', None)

        if all('' != y for y in v.values()):
            tmp[k] = v
            v['p_o'] = v['mar_cap_rs_cr'] / v['op_12m_rs_cr']
        else:
            log('incomplete data : %s', k)

    if not args.top:
        args.top = int(len(tmp)/2)

    if not args.count:
        args.count = args.top

    # Statistics is likely to work more reliable for bigger companies,
    # pick biggest args.top stocks by market cap
    mcap = rank('op_12m_rs_cr', tmp)
    #mcap = rank('mar_cap_rs_cr', tmp)
    final_rank = [(mcap[name], name) for name in mcap]
    biggest = set([name for rank, name in sorted(final_rank)[:args.top]])
    data = {k: v for k, v in tmp.items() if k in biggest}
    assert(len(data) == args.top)

    t = time.time()
    log('columns(%d) rows(%d) msec(%d)',
        len(data[list(data.keys())[0]]), len(data), (time.time()-t)*1000)

    columns = ('roce', 'roe',
               # 'qtr_sales_var', 'qtr_profit_var',
               'earnings_yield', 'p_e',
               'mar_cap_rs_cr', 'cmp_rs')

    # Rank on Profitability
    roe = rank('roe', data)
    roe_3yr = rank('roe_3yr', data)
    roe_5yr = rank('roe_5yr', data)
    roce = rank('roce', data)
    roce_3yr = rank('roce_3yr', data)
    roce_5yr = rank('roce_5yr', data)
    roic = rank('roic', data)
    opm = rank('opm', data)
    opm_5yr = rank('5yr_opm', data)
    roa = rank('roa_12m', data)
    roa_3yr = rank('roa_3yr', data)
    roa_5yr = rank('roa_5yr', data)

    # Rank on Growth
    sales_growth = rank('sales_growth', data)
    sales_growth_3yr = rank('sales_var_3yrs', data)
    sales_growth_5yr = rank('sales_var_5yrs', data)
    sales_growth_yoy = rank('qtr_sales_var', data)
    profit_growth = rank('profit_growth', data)
    profit_growth_3yr = rank('profit_var_3yrs', data)
    profit_growth_5yr = rank('profit_var_5yrs', data)
    profit_growth_yoy = rank('qtr_profit_var', data)
    op_profit_growth = rank('opert_prft_gwth', data)

    # Rank on Valuation
    pe = rank('p_e', data, False)
    ps = rank('cmp_sales', data, False)
    pb = rank('cmp_bv', data, False)
    po = rank('p_o', data, False)
    e_yield = rank('earnings_yield', data)

    # Rank on Stability
    sales = rank('sales_rs_cr', data)
    np = rank('np_12m_rs_cr', data)
    op = rank('op_12m_rs_cr', data)
    debteq = rank('debt_eq', data, False)

    stats = {f: median(f, data) for f in columns}

    final_rank = [(
        # Quality
        (roce[name] + roe[name] + opm[name] + roa[name] +
         roce_3yr[name] + roe_3yr[name] + roa_3yr[name] +
         roce_5yr[name] + roe_5yr[name] + opm_5yr[name] + roa_5yr[name] +
         roic[name]) / 12 +

        # Growth
        (sales_growth[name] + profit_growth[name] +
         sales_growth_3yr[name] + profit_growth_3yr[name] +
         sales_growth_5yr[name] + profit_growth_5yr[name] +
         sales_growth_yoy[name] + profit_growth_yoy[name] +
         op_profit_growth[name]) / 9 +

        # Value
        (pe[name] + pb[name] + ps[name] + po[name] + e_yield[name]) / 5 +

        # Stability
        (sales[name] + np[name] + op[name] + debteq[name]) / 4,

        name) for name in roe]

    def print_header():
        headers = '{:16s}' + '{:>8s}' * 9
        print(headers.format(time.strftime('%Y-%m-%d'),
                             'ROCE', 'ROE',
                             'SALES', 'PROFIT',
                             'YIELD', 'P/E',
                             'MCAP', 'CMP', 'QTY'))

    print_header()
    for i, f in enumerate(('Max', 'Median')):
        print(('%s\t\t' + '%8.2f' * 4 + '%8d%8d') % (
            f,
            stats['roce'][i],
            stats['roe'][i],
            # stats['qtr_sales_var'][i],
            # stats['qtr_profit_var'][i],
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

    per_stock = args.amount / args.count
    count = 0
    stock_list = list()
    for n, (_, name) in enumerate(sorted(final_rank)[start:start+args.count]):
        v = data[name]
        v['name'] = name
        v['rank'] = count+1
        stock_list.append(v)

        qty = 0
        available = per_stock if args.amount > per_stock else args.amount
        qty = math.ceil(available / v['cmp_rs'])

        if qty*v['cmp_rs'] > max(available, args.amount):
            qty -= 1

        if args.amount and qty < 1:
            break

        args.amount -= qty*v['cmp_rs']

        print(('%-16s' + '%8.2f' * 4 + '%8d%8d%8d') % (
            name, v['roce'], v['roe'],
            # v['qtr_sales_var'], v['qtr_profit_var'],
            v['earnings_yield'], v['p_e'],
            v['mar_cap_rs_cr'], v['cmp_rs'],
            qty))

        count += 1

        for k in columns:
            avg[k] += v[k]
        avg['count'] += 1

    for k in columns:
        avg[k] /= avg['count']

    with open('magicrank.json') as fd:
        prev = json.load(fd)

    prev_names = set([s['name'] for s in prev['data'] if s['rank'] <= len(prev['data'])/2])
    stock_names = set([s['name'] for s in stock_list if s['rank'] <= args.top/2])
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
                symbol=prev['symbol'],
                sold={k: v for k, v in sold.items() if v+86400*90 > ts},
                url='https://www.screener.in/screens/290555/universe/'),
            fd, sort_keys=True, indent=4)

    print('-' * 88)
    print_header()
    print(('%-16s' + '%8.2f' * 4 + '%8d%8d') % (
        'Average', avg['roce'], avg['roe'],
        # avg['qtr_sales_var'], avg['qtr_profit_var'],
        avg['earnings_yield'], avg['p_e'],
        avg['mar_cap_rs_cr'], avg['cmp_rs']))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--amount', dest='amount', type=int, default=0)
    parser.add_argument('--count', dest='count', type=float)
    parser.add_argument('--top', dest='top', type=int, default=500)
    portfolio(parser.parse_args())


if __name__ == '__main__':
    main()
