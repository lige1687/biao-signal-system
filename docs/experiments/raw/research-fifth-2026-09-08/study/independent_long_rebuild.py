"""Independent Decimal reconstruction of three actual long-history ledgers.

Never imports the main engine or runner. Parses dividends anew from the original
PDFs, replays recorded trades, and verifies cash allocation and trade eligibility.
This checks accounting and timing; it is not a fresh strategy performance trial.
"""
from pathlib import Path
from decimal import Decimal as D, getcontext
from datetime import date, timedelta, datetime, timezone
from collections import defaultdict
import csv
import hashlib
import json
import math
import re
from pypdf import PdfReader

getcontext().prec = 42
ROOT = Path(__file__).resolve().parent
OLD = ROOT.parent.parent / 'research-fourth-2026-09-08'
START, END = '2013-07-30', '2026-06-30'
FEE = D('.001')
TOL = D('.000001')
hashes = {}


def fingerprint(p):
    hashes[str(p.resolve())] = hashlib.sha256(p.read_bytes()).hexdigest()


def read_csv(p):
    fingerprint(p)
    with p.open() as stream:
        return list(csv.DictReader(stream))


def pdf_text(p):
    fingerprint(p)
    return re.sub(r'\s+', '', ''.join(page.extract_text() for page in PdfReader(p).pages))


def parse_date(text, label):
    match = re.search(label + r'(\d{4})年(\d{1,2})月(\d{1,2})日', text)
    assert match, label
    return date(*map(int, match.groups())).isoformat()


# Original documents, rather than the runner's float event list, establish facts.
original_list = OLD / 'events/510300/events.json'
fingerprint(original_list)
metadata = json.loads(original_list.read_text())['events']
dividends = []
for item in metadata:
    p = OLD / 'events/510300' / item['source_file']
    text = pdf_text(p)
    assert '基金主代码510300' in text
    amount = re.search(r'本次分红方案[（(]单位[：:]元/10份基金份额[）)]([0-9.]+)', text)
    assert amount, p
    event = dict(event_id=item['event_id'], record_date=parse_date(text, '权益登记日'),
                 ex_date=parse_date(text, '除息日'), pay_date=parse_date(text, '现金红利发放日'),
                 per_share=D(amount.group(1))/10, source_file=str(p.resolve()))
    for key in ('record_date', 'ex_date', 'pay_date'):
        assert event[key] == item[key], (p, key)
    assert event['per_share'] == D(item['cash_per_share_decimal'])
    assert event['record_date'] < event['ex_date'] <= event['pay_date']
    dividends.append(event)
assert len(dividends) == 13

split_pdf = OLD / 'events/other/513100-official-split.pdf'
split_text = pdf_text(split_pdf)
assert '2022年1月13日' in split_text and '2022年1月14日' in split_text
assert '每1份基金份额拆分成5份' in split_text or '每1份基金份额拆成5份' in split_text
resume_text = pdf_text(OLD / 'events/other/159915-resume.pdf')
assert '2021年2月9日' in resume_text and ('10：30' in resume_text or '10:30' in resume_text)

calendar = []
day = date.fromisoformat(START)
while day <= date.fromisoformat(END):
    calendar.append(day.isoformat())
    day += timedelta(days=1)
expected_flows = {d: D(1000) for d in calendar if date.fromisoformat(d).weekday() == 0}
summary_path = ROOT / 'summary.json'
fingerprint(summary_path)
summary = json.loads(summary_path.read_text())
result = []

for arm in ('quarterly', 'hold', 'single'):
    folder = ROOT / 'results' / ('full-base-' + arm)
    daily = read_csv(folder / 'daily.csv')
    trades = read_csv(folder / 'trades.csv')
    flows = read_csv(folder / 'flows.csv')
    assert [x['date'] for x in daily] == calendar
    actual_flows = {x['date']: D(x['amount']) for x in flows}
    assert actual_flows == expected_flows and len(flows) == len(actual_flows)
    symbols = sorted(k.removeprefix('units_') for k in daily[0] if k.startswith('units_'))
    assert symbols == (['sh510300'] if arm == 'single' else ['sh510300', 'sh513100', 'sh518880', 'sz159915'])
    prices = {s: {x['date']: x for x in read_csv(OLD / 'prices' / (s + '-nominal.csv'))} for s in symbols}
    marks = {s: D(prices[s][max(d for d in prices[s] if d < START)]['close']) for s in symbols}
    mark_dates = {s: max(d for d in prices[s] if d < START) for s in symbols}
    by_day = defaultdict(list)
    for trade in trades:
        assert START <= trade['date'] <= END
        by_day[trade['date']].append(trade)
    shares = dict.fromkeys(symbols, D(0))
    cash = dict.fromkeys(symbols, D(0))
    rights, receivable = {}, {}
    funding = fee_sum = paid = account_units = D(0)
    nav = peak = D(1)
    worst = worst_principal = D(0)
    pending = False
    maxima = defaultdict(lambda: D(0))
    dividends_paid, splits, checks = [], [], defaultdict(int)
    rebuilt_nav = []

    for row in daily:
        d = row['date']
        if d[5:] in ('01-01', '04-01', '07-01', '10-01'):
            pending = arm == 'quarterly'
        if d == '2022-01-13' and 'sh513100' in shares:
            before = shares['sh513100'] * marks['sh513100']
            old_shares = shares['sh513100']
            shares['sh513100'] *= 5
            marks['sh513100'] /= 5
            assert shares['sh513100'] * marks['sh513100'] == before
            splits.append(dict(date=d,old_shares=str(old_shares),new_shares=str(shares['sh513100']),wealth_change_before_trading='0'))
        for event in dividends:
            key = event['event_id']
            if event['ex_date'] == d:
                assert key in rights
                receivable[key] = rights[key] * event['per_share']
                marks['sh510300'] -= event['per_share']
            if event['pay_date'] == d:
                amount = receivable.pop(key)
                cash['sh510300'] += amount
                paid += amount
                dividends_paid.append(dict(record_date=event['record_date'],shares=str(rights[key]),per_share=str(event['per_share']),payment_date=d,cash=str(amount)))
        flow = expected_flows.get(d, D(0))
        if flow:
            account_units += flow / nav
            funding += flow
            for s in symbols:
                cash[s] += flow / len(symbols)

        reference = marks.copy()
        allowed = {}
        for s in symbols:
            quote = prices[s].get(d)
            limit = D('.2') if s == 'sz159915' and d >= '2020-08-24' else D('.1')
            forbidden = (s == 'sz159915' and d in ('2021-02-08','2021-02-09')) or (s == 'sh513100' and d == '2022-01-13')
            allowed[s] = bool(quote) and not forbidden and abs(D(quote['open'])-reference[s]) < reference[s]*limit-D('.00051')
        rebalance_today = pending and all(allowed.values())
        if rebalance_today:
            common_cash = sum(cash.values())
            checks['rebalance_days'] += 1
        else:
            common_cash = None

        seen_buy = False
        for trade in by_day[d]:
            s, side = trade['symbol'], trade['side']
            qty, px = D(trade['shares']), D(trade['price'])
            assert side in ('buy','sell') and qty > 0 and qty % 100 == 0
            assert allowed[s], (arm,d,s,'ineligible trade')
            assert px == D(prices[s][d]['open'])
            notional = qty*px
            cost = notional*FEE
            assert abs(D(trade['notional'])-notional) < TOL
            assert abs(D(trade['fee'])-cost) < TOL
            if rebalance_today:
                assert trade['reason'] == 'quarterly_previous_close_target'
                if side == 'buy':
                    seen_buy = True
                else:
                    assert not seen_buy, 'A sell followed a buy in the redistribution.'
            else:
                assert side == 'buy' and trade['reason'] == 'cash_available'
            change = -notional-cost if side == 'buy' else notional-cost
            if side == 'sell':
                assert qty <= shares[s]
                shares[s] -= qty
            else:
                shares[s] += qty
            if rebalance_today:
                common_cash += change
                assert common_cash >= -TOL
            else:
                cash[s] += change
                assert cash[s] >= -TOL
            fee_sum += cost
            checks['trades_checked'] += 1
            if s == 'sz159915':
                checks['growth_trades_after_limit_change' if d >= '2020-08-24' else 'growth_trades_before_limit_change'] += 1
        if rebalance_today:
            cash = {s: common_cash/len(symbols) for s in symbols}
            pending = False

        for event in dividends:
            if event['record_date'] == d:
                rights[event['event_id']] = shares['sh510300']
                assert d in prices['sh510300'] or shares['sh510300'] == 0
        for s in symbols:
            if d in prices[s]:
                marks[s] = D(prices[s][d]['close'])
                mark_dates[s] = d
            assert shares[s] == D(row['units_'+s]), (arm,d,s,'shares')
            assert abs(marks[s]-D(row['mark_'+s])) < D('1e-12'), (arm,d,s,'mark')
            maxima['symbol_cash'] = max(maxima['symbol_cash'], abs(cash[s]-D(row['cash_'+s])))
        assert row['stale_symbols'] == ','.join(s for s in symbols if mark_dates[s] != d)
        assets = sum(shares[s]*marks[s] for s in symbols)
        cash_total, owed = sum(cash.values()), sum(receivable.values())
        equity = assets+cash_total+owed
        if account_units:
            nav = equity/account_units
        peak = max(peak,nav)
        worst = max(worst,1-nav/peak)
        if funding:
            worst_principal = max(worst_principal, 1-equity/funding)
        rebuilt_nav.append(nav)
        values = dict(cash=cash_total,assets=assets,receivable=owed,equity=equity,total_funding=funding,account_units=account_units,nav=nav,interest=D(0))
        for key, value in values.items():
            maxima[key] = max(maxima[key], abs(value-D(row[key])))
        assert all(v < TOL for k,v in maxima.items() if k != 'nav'), (arm,d,dict(maxima))
        assert maxima['nav'] < D('1e-10')

    # Solve terminal wealth from each independently reconstructed deposit date.
    # The unknown is continuous annual rate; the objective is monotone.
    elapsed = [(date.fromisoformat(END)-date.fromisoformat(d)).days/365.25 for d in expected_flows]
    low, high = -2.0, 2.0
    for _ in range(120):
        mid = (low+high)/2
        accumulated = sum(1000*math.exp(mid*t) for t in elapsed)
        if accumulated > float(equity):
            high = mid
        else:
            low = mid
    annual_return = math.expm1((low+high)/2)
    main = next(x for x in summary if x['window']=='full' and x['scenario']=='base' and x['arm']==arm)
    comparison = dict(final_equity=equity,final_cash=cash_total,final_holdings_value=assets,final_receivable=owed,contributed=funding,fees=fee_sum,dividends_received=paid,max_drawdown=worst,worst_loss_vs_contributions=worst_principal,hypothetical_net_liquidation=equity-assets*FEE)
    for key,value in comparison.items():
        assert abs(D(str(main[key]))-value) < TOL, (arm,key,value,main[key])
    assert abs(annual_return-main['cashflow_annual_return']) < 1e-10
    assert main['rebalance_count'] == checks['rebalance_days']
    assert int(main['contribution_count']) == len(expected_flows)
    result.append(dict(arm=arm,days=len(daily),trades=len(trades),contribution_count=len(expected_flows),**{k:str(v) for k,v in comparison.items()},cashflow_annual_return=annual_return,max_daily_errors={k:str(v) for k,v in maxima.items()},checks=dict(checks),split_reconstruction=splits,dividend_reconstruction=dividends_paid,all_checks_passed=True))

out = dict(checked_at=datetime.now(timezone.utc).isoformat(),window=[START,END],method='Independent Decimal reconstruction from nominal price CSV, original dividend PDFs, recorded trades, and an independently generated Monday funding calendar. Does not import simulate or runner.',boundaries=['Actual trades replayed; does not regenerate strategy target quantities from scratch.','Timing and lot/fee/cash eligibility checked for every recorded trade, including dated limits and special suspension.','Three longest base accounts only; other 18 trials not claimed independently rebuilt.','Dividend payment usable before opening and daily open execution remain study assumptions.'],results=result,source_dividends_reparsed=13,input_hashes=[dict(path=p,sha256=h) for p,h in sorted(hashes.items())])
(ROOT/'independent-long-ledgers.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps([{k:v for k,v in x.items() if k not in ('dividend_reconstruction','max_daily_errors','split_reconstruction')} for x in result],ensure_ascii=False,indent=2))
