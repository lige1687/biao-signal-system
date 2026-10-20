"""Independent synthetic checks; no historical candidate results or production imports."""
from pathlib import Path
from datetime import date,timedelta
import importlib.util,hashlib,json,math,random

ROOT=Path(__file__).resolve().parent
src=ROOT/'cash_engine.py';before=hashlib.sha256(src.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('reviewed_engine',src)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def panel(end='2023-04-03'):
    p={s:{} for s in ('x','y')};day=date(2022,12,31)
    while day<=date.fromisoformat(end):
        d=day.isoformat()
        for s in p:p[s][d]={'open':10.,'close':10.}
        if d=='2023-03-31':p['x'][d]['close']=20.
        if d>'2023-03-31':p['x'][d]={'open':20.,'close':20.}
        day+=timedelta(days=1)
    return p

def sim(p,ev=(),end='2023-04-01',quarter=True,fee=0,rate=0):
    return m.simulate(p,list(ev),start='2023-01-01',end=end,weekly=2000,fee=fee,cash_rate=rate,rebalance=quarter,limits={s:10 for s in p})

checks=[]
def ok(name,detail):checks.append({'name':name,'passed':True,'detail':detail})

# Hand-calculated: thirteen 2000 deposits, x/y each 1300 shares before quarter.
p=panel()
for d in p['x']:
    if d>='2023-04-01':p['x'][d]={'open':18.,'close':18.}
ev=[dict(event_id='d',symbol='x',type='cash_dividend',record_date='2023-03-31',ex_date='2023-04-01',pay_date='2023-04-02',cash_per_share=2.)]
r=sim(p,ev);a=r['daily'][-1]
assert (a['units_x'],a['units_y'],a['cash'],a['receivable'],a['equity'])==(1000,1800,400.,2600.,39000.)
ok('quarter_and_ex_date','Hand expected: x=1000, y=1800, cash=400, receivable=2600, equity=39000.')
r=sim(p,ev,end='2023-04-02');a=r['daily'][-1]
paid=[e for e in r['events'] if e['kind']=='dividend_paid'][0]
assert paid['amount']==2600 and a['equity']==39000 and a['receivable']==0
assert a['units_x']==1100 and a['units_y']==1800 and a['cash_x']==1000 and a['cash_y']==200
ok('pay_after_quarter_sale_and_cash_ownership','Payment uses registered 1300 shares, not current 1000; buys only originating x with dividend.')

p=panel()
for d in p['x']:
    if d>='2023-04-01':p['x'][d]={'open':4.,'close':4.}
r=sim(p,[dict(event_id='s',symbol='x',type='split',ex_date='2023-04-01',ratio=5)])
a=r['daily'][-1]
assert (a['units_x'],a['units_y'],a['cash'],a['equity'])==(4800,1900,800.,39000.)
ok('quarter_and_split','Hand expected x=4800, y=1900, cash=800, equity=39000; no fivefold phantom wealth.')

# Deterministic arbitrary synthetic paths. Independent close-to-close wealth bridge.
rng=random.Random(6807);p={s:{} for s in ('x','y')};day=date(2022,12,31);old={'x':10.,'y':15.}
while day<=date(2023,7,5):
    for s in p:
        op=old[s]*(1+rng.uniform(-.035,.035));cl=op*(1+rng.uniform(-.035,.035))
        p[s][day.isoformat()]={'open':op,'close':cl};old[s]=cl
    day+=timedelta(days=1)
ev=[dict(event_id='d',symbol='x',type='cash_dividend',record_date='2023-03-31',ex_date='2023-04-01',pay_date='2023-04-06',cash_per_share=.4)]
for quarter in (False,True):
    r=sim(p,ev,end='2023-07-05',quarter=quarter,fee=.001,rate=.02)
    prior=None;max_res=0.;min_cash=1e9
    for row in r['daily']:
        d=row['date'];ts=[t for t in r['trades'] if t['date']==d]
        flow=sum(f['amount'] for f in r['flows'] if f['date']==d)
        div=sum(e['amount'] for e in r['events'] if e['date']==d and e['kind']=='dividend_receivable')
        market=sum((prior['units_'+s] if prior else 0)*(row['mark_'+s]-(prior['mark_'+s] if prior else p[s]['2022-12-31']['close'])) for s in p)
        trading=sum((1 if t['side']=='buy' else -1)*t['shares']*(row['mark_'+t['symbol']]-t['price'])-t['fee'] for t in ts)
        expect=(prior['equity'] if prior else 0)+flow+market+trading+div+row['interest']
        res=abs(row['equity']-expect);max_res=max(res,max_res);assert res<1e-7
        if prior and prior['equity']>0:
            assert abs(row['nav']/prior['nav']-row['equity']/(prior['equity']+flow))<1e-12
        for s in p:
            sides={t['side'] for t in ts if t['symbol']==s};assert len(sides)<=1
            sold=sum(t['shares'] for t in ts if t['symbol']==s and t['side']=='sell')
            assert sold <= (prior['units_'+s] if prior else 0)
            min_cash=min(min_cash,row['cash_'+s]);assert row['cash_'+s]>=-1e-7
        prior=row
    ok('daily_independent_wealth_bridge_'+str(quarter),{'days':len(r['daily']),'max_error':max_res,'min_cash':min_cash,'same_day_opposite_trades':0,'nav_cashflow_bridge':'passed'})

# Future closes cannot affect earlier orders or earlier ledger.
a=sim(p,end='2023-07-05');q={s:{d:v.copy() for d,v in rows.items()} for s,rows in p.items()}
q['x']['2023-04-01']['close']*=1.9
b=sim(q,end='2023-07-05')
assert [t for t in a['trades'] if t['date']<='2023-04-01']==[t for t in b['trades'] if t['date']<='2023-04-01']
assert [d for d in a['daily'] if d['date']<'2023-04-01']==[d for d in b['daily'] if d['date']<'2023-04-01']
ok('same_day_close_and_future_orders','Changing quarter execution day close leaves same open orders and all prior daily ledgers unchanged.')

# Defensive-input probe, separate from pass checks: caller must reject invalid closes.
bad=panel();bad['x']['2023-01-02']['close']=float('nan')
try:
    out=sim(bad,end='2023-01-02',quarter=False)
    bad_probe={'engine_rejected':False,'nav_is_finite':math.isfinite(out['daily'][-1]['nav'])}
except (ValueError,AssertionError) as ex:bad_probe={'engine_rejected':True,'error':str(ex)}
after=hashlib.sha256(src.read_bytes()).hexdigest();assert before==after
result={'engine_sha256':before,'checks':checks,'bad_close_probe':bad_probe,'historical_candidates_executed':False}
(ROOT/'reviewer-checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
