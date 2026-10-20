from pathlib import Path
import csv,json,math
from cash_engine import simulate
P=Path(__file__).resolve().parent;OLD=P.parent.parent/'research-fourth-2026-09-08'

def read(p):
 with p.open() as f:return list(csv.DictReader(f))
prices={s:{r['date']:{k:float(r[k]) for k in ['open','close']} for r in read(OLD/'prices'/f'{s}-nominal.csv')} for s in ['sh510300','sz159915','sh518880','sh513100']}
events=[dict(e,symbol='sh510300') for e in json.loads((OLD/'events/510300/events.json').read_text())['events'] if '2023-01-01'<=e['record_date']<='2025-12-31']
checks=[]
for x in json.loads((OLD/'study/summary.json').read_text()):
 subset={s:q for s,q in prices.items() if x['arm']!='single' or s=='sh510300'}
 r=simulate(subset,events,start='2023-01-01',end='2025-12-31',weekly=x['weekly'],fee=x['fee'],cash_rate=x['cash_rate'],rebalance=x['arm']=='quarterly',limits={s:.1 for s in subset},limit_changes={'sz159915':[('2020-08-24',.2)]},blocked_dates={'sz159915':['2021-02-08','2021-02-09'],'sh513100':['2022-01-13']})
 original=read(OLD/'study/results'/f"{x['scenario']}-{x['arm']}"/'daily.csv')
 assert len(original)==len(r['daily'])
 for a,b in zip(original,r['daily']):
  for k in ['equity','cash','receivable','nav']:assert abs(float(a[k])-b[k])<1e-9
 trades=read(OLD/'study/results'/f"{x['scenario']}-{x['arm']}"/'trades.csv')
 assert len(trades)==len(r['trades'])
 for a,b in zip(trades,r['trades']):
  assert a['date']==b['date'] and a['symbol']==b['symbol'] and a['side']==b['side']
  assert float(a['shares'])==b['shares'] and float(a['price'])==b['price']
 checks.append({'scenario':x['scenario'],'arm':x['arm'],'daily_values_unchanged':True,'all_trades_unchanged':True})
(P/'old-results-invariance.json').write_text(json.dumps(checks,indent=2));print('All 12 old accounts and trades unchanged')
