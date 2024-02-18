import re
import bs4
import json
import time
import requests
from logging import critical as log

value_screen = ('903587/value', 'ernlkdkijyag0d048e3ouem8774k5vyp')
growth_screen = ('879125/growth', '8cmbf0oxunegvesbax08io8ob855d5ov')
quality_screen = ('878969/quality', '08rubasshjfkuozbrtj9a0tp36qm3rgy')
stability_screen = ('1078958/stability', 'b8tc69wcvriqifuaajep1wk22pqbyjfh')
universe_screen = ('290555/universe', '5ukjoyfkgfi7r7m119prdif7ym41uxmv')


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
    for i, (ebit, name) in enumerate(data):
        rank[name] = i

    return rank


def median(field, data):
    val = sorted([v[field] for k, v in data.items()])
    return val[-1], val[len(val)//2], val[0]


def main():
    filename = 'universe.json'
    try:
        data = json.load(open(filename))
        assert (data['timestamp'] > time.time() - 86400)
    except Exception:
        data = dict()
        for screen, sessionid in (value_screen, growth_screen, quality_screen, stability_screen):
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
            v['p_o'] = v['mar_cap_rs_cr'] / v['op_12m_rs_cr']  # Less is better Value

            v['debt_eq'] = v['debt_eq'] * 100                  # Less is better Quality
            if v['debt_eq'] > 0:
                v['int_ratio'] = 100 / v['int_coverage']       # Less is better Quality
            else:
                v['int_ratio'] = 0

            # Net Profit Margin - More is better Quality
            v['npm'] = (100 * v['np_12m_rs_cr']) / v['sales_rs_cr']

            # Divident yield over 5 years - More is better Quality
            v['div_yield'] = (100 * v['div_5yrs_rs_cr']) / v['mar_cap_rs_cr']

            # How much below 200 DMA - More is better Value
            v['oversold'] = (v['200_dma_rs'] * 100) / v['cmp_rs']

            # Operating Cashflow Yield - More is better Quality
            v['ocf_yield_3'] = (100 * v['cf_opr_3yrs_rs_cr']) / v['mar_cap_rs_cr']
            v['ocf_yield_5'] = (100 * v['cf_opr_5yrs_rs_cr']) / v['mar_cap_rs_cr']

            # Free Cashflow Yield - More is better Quality
            v['fcf_yield_3'] = (100 * v['free_cash_flow_3yrs_rs_cr']) / v['mar_cap_rs_cr']
            v['fcf_yield_5'] = (100 * v['free_cash_flow_5yrs_rs_cr']) / v['mar_cap_rs_cr']

            tmp[k] = v
        except Exception:
            log('incomplete data : name(%s)', k)
            log(json.dumps({x: y for x, y in v.items() if '' == y}, indent=4))

    data = tmp

    # t = time.time()
    # log('columns(%d) rows(%d) msec(%d)',
    #     len(data[list(data.keys())[0]]), len(data), (time.time()-t)*1000)

    # Rank on Size - More is better
    np = rank('np_12m_rs_cr', data)
    op = rank('op_12m_rs_cr', data)
    div = rank('div_5yrs_rs_cr', data)
    sales = rank('sales_rs_cr', data)
    ocf_3 = rank('cf_opr_3yrs_rs_cr', data)
    ocf_5 = rank('cf_opr_5yrs_rs_cr', data)
    fcf_3 = rank('free_cash_flow_3yrs_rs_cr', data)
    fcf_5 = rank('free_cash_flow_5yrs_rs_cr', data)
    zscore = rank('altman_z_scr', data)

    size_rank = [(sales[name] + np[name] + op[name] +
                  div[name] + ocf_5[name] + fcf_5[name] +
                  ocf_3[name] + fcf_3[name] + zscore[name],
                 name) for name in sales]

    # Divide into two halvs based upon the above factors to discard the tiny companies.
    # We will take only the upper half ranked by profit, dividend, sales and cashflow.
    count = int(len(size_rank)/2)
    biggest_stocks = set([name for _, name in sorted(size_rank)[:count]])
    data = {k: v for k, v in data.items() if k in biggest_stocks}

    # Rank on Quality - More is better unless specified
    roe = rank('roe', data)
    roe_3yr = rank('roe_3yr', data)
    roe_5yr = rank('roe_5yr', data)
    roce = rank('roce', data)
    roce_3yr = rank('roce_3yr', data)
    roce_5yr = rank('roce_5yr', data)
    roic = rank('roic', data)
    npm = rank('npm', data)
    opm = rank('opm', data)
    opm_5yr = rank('5yr_opm', data)
    roa = rank('roa_12m', data)
    roa_3yr = rank('roa_3yr', data)
    roa_5yr = rank('roa_5yr', data)
    debteq = rank('debt_eq', data, False)       # Less is better
    int_ratio = rank('int_ratio', data, False)  # Less is better
    pscore = rank('piotski_scr', data)

    # Rank on Growth - More is better
    sales_growth = rank('sales_growth', data)
    sales_growth_3yr = rank('sales_var_3yrs', data)
    sales_growth_5yr = rank('sales_var_5yrs', data)
    sales_growth_yoy = rank('qtr_sales_var', data)
    profit_growth = rank('profit_growth', data)
    profit_growth_3yr = rank('profit_var_3yrs', data)
    profit_growth_5yr = rank('profit_var_5yrs', data)
    profit_growth_yoy = rank('qtr_profit_var', data)
    op_profit_growth = rank('opert_prft_gwth', data)
    eps_growth_3yr = rank('eps_var_3yrs', data)
    eps_growth_5yr = rank('eps_var_5yrs', data)
    gfactor = rank('g_factor', data)

    # Rank on Valuation
    pe = rank('p_e', data, False)           # Less Price/Earnings is better
    ps = rank('cmp_sales', data, False)     # Less Price/Sales is better
    pb = rank('cmp_bv', data, False)        # Less Price/BookValue is better
    po = rank('p_o', data, False)           # Less Price/Operating Profit is better
    peg = rank('peg', data, False)          # Less PE/Growth is better
    e_yield = rank('earnings_yield', data)  # More Earnings Yield is better
    div_yield = rank('div_yield', data)     # More divident Yield is better
    ocf_yield_3 = rank('ocf_yield_3', data) # More Operating Cash Flow Yield is better
    ocf_yield_5 = rank('ocf_yield_5', data)
    fcf_yield_3 = rank('fcf_yield_3', data) # More Free Cash Flow Yield is better
    fcf_yield_5 = rank('fcf_yield_5', data)
    oversold = rank('oversold', data)               # Move oversold is cheaper
    overbought = rank('52w', data, False)           # Less is cheaper - Position in 52 week range
    return_3yrs = rank('3yrs_return', data, False)  # Less is cheaper
    return_5yrs = rank('5yrs_return', data, False)  # Less is cheaper

    # Ranking weightage - 25% Quality - 25% Growth - 50% Valuation
    final_rank = [(
        # Quality
        (roce[name] + roe[name] + npm[name] + opm[name] + roa[name] +
         roce_3yr[name] + roe_3yr[name] + roa_3yr[name] +
         roce_5yr[name] + roe_5yr[name] + opm_5yr[name] + roa_5yr[name] +
         roic[name] + debteq[name] + int_ratio[name] +
         pscore[name]) / 16 +

        # Growth
        (sales_growth[name] + profit_growth[name] +
         sales_growth_3yr[name] + profit_growth_3yr[name] +
         sales_growth_5yr[name] + profit_growth_5yr[name] +
         sales_growth_yoy[name] + profit_growth_yoy[name] +
         op_profit_growth[name] +
         eps_growth_3yr[name] + eps_growth_5yr[name] +
         gfactor[name]) / 12 +

        # Value
        (pe[name] + pb[name] + ps[name] + po[name] + peg[name] + e_yield[name] +
         div_yield[name] + ocf_yield_5[name] + fcf_yield_5[name] +
         ocf_yield_3[name] + fcf_yield_3[name] +
         return_3yrs[name] + return_5yrs[name] +
         overbought[name] + oversold[name])*2 / 15,

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

    prev_names = set([s['name'] for s in prev['data'] if s['rank'] <= len(prev['data'])/2])
    stock_names = set([s['name'] for s in stock_list if s['rank'] <= len(stock_list)/2])
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


if __name__ == '__main__':
    main()
