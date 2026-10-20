"""Read-only independent Decimal reconstruction of three base ledgers.
Does not call simulate or inspect candidate rules to generate any new strategy.
"""
from pathlib import Path
from decimal import Decimal as D,getcontext
from datetime import date,timedelta
from collections import defaultdict
import csv,json,hashlib
getcontext().prec=40
ROOT=Path(__file__).resolve().parent; RAW=ROOT.parent
def csvread(p):
    with p.open() as f:return list(csv.DictReader(f))
primary=[e for e in json.loads((RAW/'events/510300/events.json').read_text())['events'] if '2023-01-01'<=e['record_date']<='2025-12-31']
summary=json.loads((ROOT/'summary.json').read_text());results=[];files=[]
for arm in ('quarterly','hold','single'):
    p=ROOT/'results'/('base-'+arm)
    daily=csvread(p/'daily.csv');trades=csvread(p/'trades.csv');flows=csvread(p/'flows.csv')
    syms=[x[6:] for x in daily[0] if x.startswith('units_')]
    prices={s:{r['date']:r for r in csvread(RAW/'prices'/(s+'-nominal.csv'))} for s in syms}
    for fn in ('daily.csv','trades.csv','flows.csv','events.json'):files.append({'path':str(p/fn),'sha256':hashlib.sha256((p/fn).read_bytes()).hexdigest()})
    ts=defaultdict(list);fs={x['date']:D(x['amount']) for x in flows}
    for t in trades:ts[t['date']].append(t)
    expected_flows={};day=date(2023,1,1)
    while day<=date(2025,12,31):
        if day.weekday()==0:expected_flows[day.isoformat()]=D(1000)
        day+=timedelta(days=1)
    assert fs==expected_flows and len(fs)==len(flows)==157
    units={s:D(0) for s in syms};marks={s:D(prices[s][max(d for d in prices[s] if d<'2023-01-01')]['close']) for s in syms}
    cash=D(0);ar={};rights={};equity=D(0);nav=D(1);account_units=D(0);funding=D(0);fees=D(0);paid=D(0);divdetails=[]
    maxcash=maxeq=maxnav=D(0);peak=D(1);worst=D(0);pnl={s:D(0) for s in syms}
    for row in daily:
        d=row['date'];oldunits=units.copy();oldmarks=marks.copy()
        for e in primary:
            if e['ex_date']==d:
                amt=rights[e['event_id']]*D(e['cash_per_share_decimal']);ar[e['event_id']]=amt
                marks['sh510300']-=D(e['cash_per_share_decimal']);pnl['sh510300']+=amt
            if e['pay_date']==d:
                amt=ar.pop(e['event_id']);cash+=amt;paid+=amt
                divdetails.append({'record_date':e['record_date'],'registered_shares':str(rights[e['event_id']]),'per_share':e['cash_per_share_decimal'],'paid_date':d,'amount':str(amt)})
        flow=fs.get(d,D(0));funding+=flow;cash+=flow
        if flow:account_units+=flow/nav
        sides=defaultdict(set)
        for t in ts[d]:
            s=t['symbol'];qty=D(t['shares']);px=D(t['price']);fee=D(t['fee']);side=t['side'];sign=1 if side=='buy' else -1
            assert px==D(prices[s][d]['open'])
            assert qty>0 and qty%100==0 and abs(fee-qty*px*D('.001'))<D('1e-10')
            assert abs(D(t['notional'])-qty*px)<D('1e-9')
            if side=='sell':assert qty<=oldunits[s]
            units[s]+=sign*qty;cash-=sign*qty*px+fee;fees+=fee
            assert units[s]>=0 and cash>=D('-1e-8')
            sides[s].add(side)
        assert all(len(x)<=1 for x in sides.values())
        for e in primary:
            if e['record_date']==d:rights[e['event_id']]=units['sh510300']
        for s in syms:
            if d in prices[s]:marks[s]=D(prices[s][d]['close'])
            pnl[s]+=oldunits[s]*(marks[s]-oldmarks[s])
        for t in ts[d]:
            s=t['symbol'];sign=1 if t['side']=='buy' else -1
            pnl[s]+=sign*D(t['shares'])*(marks[s]-D(t['price']))-D(t['fee'])
        equity=cash+sum(units[s]*marks[s] for s in syms)+sum(ar.values())
        if account_units:nav=equity/account_units
        peak=max(peak,nav);worst=max(worst,1-nav/peak)
        maxcash=max(maxcash,abs(cash-D(row['cash'])));maxeq=max(maxeq,abs(equity-D(row['equity'])));maxnav=max(maxnav,abs(nav-D(row['nav'])))
        assert abs(sum(ar.values())-D(row['receivable']))<D('1e-8')
        for s in syms:assert units[s]==D(row['units_'+s]) and marks[s]==D(row['mark_'+s])
    assert maxcash<D('1e-7') and maxeq<D('1e-7') and maxnav<D('1e-10')
    assert abs(sum(pnl.values())-(equity-funding))<D('1e-20')
    sr=next(s for s in summary if s['scenario']=='base' and s['arm']==arm)
    for key,val in [('final_equity',equity),('fees',fees),('dividends_received',paid),('max_drawdown',worst)]:assert abs(D(str(sr[key]))-val)<D('1e-7')
    results.append({'arm':arm,'days':len(daily),'trades':len(trades),'contributed':str(funding),'final_equity':str(equity),'final_cash':str(cash),'fees':str(fees),'dividends':str(paid),'max_drawdown':str(worst),'max_daily_cash_error':str(maxcash),'max_daily_equity_error':str(maxeq),'max_daily_nav_error':str(maxnav),'pnl_by_symbol':{s:str(v) for s,v in pnl.items()},'dividend_reconstruction':divdetails})
a,b=results[:2]
delta={'final_equity':str(D(a['final_equity'])-D(b['final_equity'])),'fees':str(D(a['fees'])-D(b['fees'])),'dividends':str(D(a['dividends'])-D(b['dividends'])),'max_drawdown':str(D(a['max_drawdown'])-D(b['max_drawdown'])),'pnl_by_symbol':{s:str(D(a['pnl_by_symbol'][s])-D(b['pnl_by_symbol'][s])) for s in a['pnl_by_symbol']}}
out={'results':results,'quarterly_minus_hold':delta,'input_hashes':files,'method':'Independent Decimal reconstruction from trade/flow CSV, primary dividends, and source nominal closes; engine not imported.'}
(ROOT/'reviewer-real-ledgers.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'results':[{k:v for k,v in r.items() if k not in ('pnl_by_symbol','dividend_reconstruction')} for r in results],'quarterly_minus_hold':delta},ensure_ascii=False,indent=2))
