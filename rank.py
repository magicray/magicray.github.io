import re
import bs4
import json
import time
import requests
from logging import critical as log


SCREENER = """
Return on equity > 0 AND
Return on capital employed > 0 AND

Sales growth > 0 AND
Profit growth > 0 AND
Operating profit growth > 0 AND

Earnings yield > 0 AND
Price to Earning  > 0 AND

Sales > Operating profit  AND
Operating profit > Net profit  AND
Net profit > 0 AND

Last result date > 202508
"""


#growth_screen = ('879125/growth', 'chrdjfpkcw07dhqo4nwfh0yd7g191lxl')
#quality_screen = ('878969/quality', '7ntrq89s65vvh06jwgewobakgkgr4gvz')
universe_screen = ('290555/universe', 'b97f2yuxhodlbbjxgzrcgx5cziq5wpu9')


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

        assert (200 == r.status_code)
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
    for i, (_, name) in enumerate(data):
        rank[name] = i

    return rank


def main():
    filename = 'universe.json'
    try:
        data = json.load(open(filename))
        assert (data['timestamp'] > time.time() - 86400)
    except Exception:
        data = dict()
        #for screen, sessionid in (growth_screen, quality_screen, universe_screen):
        for screen, sessionid in [universe_screen]:
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
        try:
            assert (all('' != y for y in v.values()))

            tmp[k] = v
        except Exception:
            log('incomplete data : name(%s)', k)
            log(json.dumps({x: y for x, y in v.items() if '' == y}, indent=4))

    data = tmp

    # Rank on Size - More is better
    np = rank('np_12m_rs_cr', data)           # More net profit is better
    op = rank('op_12m_rs_cr', data)           # More operting profit is better
    sales = rank('sales_rs_cr', data)         # More sales is better
    size_rank = [(np[name] + op[name] + sales[name],
                  name) for name in sales]

    # Divide into two halvs based upon the above factors to discard the tiny companies.
    # We will take only the upper half ranked by profit and sales
    count = min(200, int(len(size_rank)/2))
    biggest_stocks = set([name for _, name in sorted(size_rank)[:count]])
    data = {k: v for k, v in data.items() if k in biggest_stocks}

    assert(len(data) == 200)

    # Rank on Quality - More is better unless specified
    roe = rank('roe', data)
    roce = rank('roce', data)

    # Rank on Growth - More is better
    sales_growth = rank('sales_growth', data)
    profit_growth = rank('profit_growth', data)
    op_profit_growth = rank('opert_prft_gwth', data)

    # Rank on Valuation
    pe = rank('p_e', data, False)
    earnings_yield = rank('earnings_yield', data)

    # Ranking weightage - 33% Quality - 33% Growth - 33% Valuation
    final_rank = [(
        # Quality
        (roe[name] + roce[name]) / 2 +

        # Growth
        (sales_growth[name] + profit_growth[name] +
         op_profit_growth[name]) / 3 +

        # Value
        (pe[name] + earnings_yield[name]) / 2,

        name) for name in roe]

    count = 0
    stock_list = list()
    for n, (_, name) in enumerate(sorted(final_rank)):
        v = data[name]
        count = count+1
        v['name'] = name
        v['rank'] = count
        stock_list.append(v)

    with open('magicrank.json') as fd:
        prev = json.load(fd)

    prev_names = set([s['name'] for s in prev['data'] if s['rank'] <= len(prev['data'])//2])
    stock_names = set([s['name'] for s in stock_list if s['rank'] <= len(stock_list)//2])
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
                sold={k: v for k, v in sold.items() if v+86400*90 > ts},
                url='https://www.screener.in/screens/290555/universe/'),
            fd, sort_keys=True, indent=4)


if __name__ == '__main__':
    main()
