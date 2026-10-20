"""Identity and summary checks using independently reconstructed balances, no engine import."""
from pathlib import Path
from decimal import Decimal as D
from datetime import date
from collections import Counter
from bisect import bisect_right
import csv,json
P=Path(__file__).resolve().parent;S=P/'accepted'
def rows(p):return list(csv.DictReader(p.open()))
def js(p):return json.loads(p.read_text())
params=js(S/'product-qualification/execution-parameters.json')
dates=sorted({r['date'] for s in params['symbols'] for r in rows(S/'product-qualification/bars-helper-native'/f'{s}-nominal.csv')})
summaries={x['config_id']:x for x in js(S/'account-results/summary.json')};output=[]
for cfg in ['R0','R1']:
 folder=S/'account-results'/cfg;trades=rows(folder/'trades.csv');orders=js(folder/'orders.json');trips=js(folder/'roundtrips.json');daily=rows(P/'reconciliation'/cfg/'daily-independent.csv')
 tb={t['order_id']:t for t in trades};ob={o['order_id']:o for o in orders}
 assert len(tb)==len(trades) and len(ob)==len(orders) and set(tb)<=set(ob)
 for o in orders:
  if o['side']=='buy':
   i=bisect_right(dates,o['signal_date']);assert o['planned_date']==(dates[i] if i<len(dates) else None)
   assert len(o['attempts'])<=1
  if o['status']=='filled':
   assert o['order_id'] in tb;t=tb[o['order_id']]
   assert t['side']==o['side'] and t['symbol']==o['symbol']
   filled=[a for a in o['attempts'] if a['reason']=='filled'];assert len(filled)==1 and filled[0]['date']==t['date'] and o['attempts'][-1]['date']==t['date']
   if o['side']=='buy':assert t['date']==o['planned_date']
  else:assert o['order_id'] not in tb
 peak=D(daily[0]['nav']);anchor=daily[0]['date'];under=False;episode=None;longest=0;longstart=None;longend=None;recovered=None
 for r in daily:
  n=D(r['nav']);today=r['date']
  if n>=peak-D('1e-25'):
   if under:
    duration=(date.fromisoformat(today)-date.fromisoformat(episode)).days
    if duration>longest:longest=duration;longstart=episode;longend=today;recovered=True
   peak=max(peak,n);anchor=today;under=False;episode=None
  else:
   if not under:episode=anchor;under=True
   duration=(date.fromisoformat(today)-date.fromisoformat(episode)).days
   if duration>=longest:longest=duration;longstart=episode;longend=today;recovered=False
 rep=summaries[cfg];tol=D('.00001');last=daily[-1]
 for field,value in {'last_equity':D(last['equity']),'net_gain':D(last['equity'])-D(last['total_funding']),'fees':D(last['fees']),'max_drawdown':-min(D(r['drawdown']) for r in daily)}.items():assert abs(D(str(rep[field]))-value)<tol,(cfg,field)
 assert rep['buys']==sum(t['side']=='buy' for t in trades)
 assert longest==rep['longest_drawdown_days'] and under==rep['unrecovered_at_end'],(cfg,'recovery timing')
 sells={t['position_id']:t['date'] for t in trades if t['side']=='sell'}
 post=[e for e in js(folder/'events.json') if e['kind']=='dividend_receivable' and e.get('position_id') in sells and sells[e['position_id']]<e['date'] and e['amount']>0]
 output.append(dict(config=cfg,orders=len(orders),order_statuses=dict(Counter(o['status'] for o in orders)),trades=len(trades),open_positions=sum(not t['closed'] for t in trips),post_sale_receivable_actual_events=len(post),last_receivable=last['receivable'],longest_drawdown_days=longest,longest_start=longstart,longest_end=longend,longest_recovered=recovered,unrecovered_at_end=under,last_equal_or_higher_peak=anchor))
(P/'summary-and-orders-checks.json').write_text(json.dumps({'status':'passed','results':output},ensure_ascii=False,indent=2)+'\n')
print(json.dumps(output,ensure_ascii=False))
