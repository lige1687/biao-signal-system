"""Supplemental identity/boundary checks on accepted outputs plus independent ledgers."""
from pathlib import Path
from decimal import Decimal as D,ROUND_FLOOR
from bisect import bisect_right
from collections import Counter
import csv,json,hashlib
P=Path(__file__).resolve().parent;S=P/'accepted'
def rows(p):return list(csv.DictReader(p.open()))
def js(p):return json.loads(p.read_text())
params=js(S/'product-qualification/execution-parameters.json');symbols=params['symbols'];dates=sorted({r['date'] for s in symbols for r in rows(S/'product-qualification/bars-helper-native'/f'{s}-nominal.csv')});summary=[];riskchecks=[]
for config in [f'P{i}' for i in range(8)]:
 folder=S/'account-results'/config;trades=rows(folder/'trades.csv');orders=js(folder/'orders.json');trips=js(folder/'roundtrips.json');daily={r['date']:r for r in rows(P/'reconciliation'/config/'daily-independent.csv')};tradeby={t['order_id']:t for t in trades};orderby={o['order_id']:o for o in orders}
 assert len(tradeby)==len(trades) and len(orderby)==len(orders)
 assert set(tradeby).issubset(orderby)
 for order in orders:
  if order['side']=='buy':
   planned=order['signal_date'] if config=='P6' else (dates[bisect_right(dates,order['signal_date'])] if bisect_right(dates,order['signal_date'])<len(dates) else None)
   assert order['planned_date']==planned
  if order['status']=='filled':
   assert order['order_id'] in tradeby;trade=tradeby[order['order_id']]
   assert trade['side']==order['side'] and trade['symbol']==order['symbol']
   filled=[a for a in order['attempts'] if a['reason']=='filled'];assert len(filled)==1 and filled[0]['date']==trade['date']
   assert order['attempts'][-1]['date']==trade['date']
   if order['side']=='buy':assert trade['date']==order['planned_date']
  else:assert order['order_id'] not in tradeby
  if order['side']=='buy' and config!='P6':assert len(order['attempts'])<=1
  if config=='P7' and order['side']=='buy':
   for attempt in order['attempts']:
    day=attempt['date'];previous=D(daily[day]['previous_equity_'+order['symbol']]);risk=previous*D('.01');assert abs(D(str(attempt['risk_budget']))-risk)<D('.00001')
    rec=dict(date=day,order_id=order['order_id'],previous_product_wealth=previous,risk_budget=risk,reason=attempt['reason'])
    if order['status']=='filled':
     trade=tradeby[order['order_id']];px=D(trade['price']);stop=D(trade['stop']);risk_shares=(risk/(px-stop)/100).to_integral_value(rounding=ROUND_FLOOR)*100;actual=D(trade['shares']);rec.update(actual_shares=actual,risk_only_shares=risk_shares,risk_limit_binding=(actual==risk_shares),actual_nominal_risk=actual*(px-stop));assert actual<=risk_shares
    riskchecks.append(rec)
 events=js(folder/'events.json');trade_by_pos={}
 for t in trades:
  if t['side']=='sell':trade_by_pos[t['position_id']]=t['date']
 post_sale_div=[e for e in events if e['kind']=='dividend_receivable' and e.get('position_id') in trade_by_pos and trade_by_pos[e['position_id']]<e['date'] and e['amount']>0]
 summary.append(dict(config=config,orders=len(orders),statuses=dict(Counter(o['status'] for o in orders)),trades=len(trades),open_trips=sum(not t['closed'] for t in trips),closed_trips=sum(t['closed'] for t in trips),post_sale_receivable_real_occurrences=len(post_sale_div)))
# Explicit real split/record event cases from reconstructed records.
daily6={r['date']:r for r in rows(P/'reconciliation/P6/daily-independent.csv')};before=daily6['2022-01-12'];after=daily6['2022-01-13'];assert D(after['units_sh513100'])==D(before['units_sh513100'])*5;assert D(after['mark_sh513100'])*5==D(before['mark_sh513100']);assert after['mark_date_sh513100']=='2022-01-12'
assert D(after['units_sh513100'])*D(after['mark_sh513100'])==D(before['units_sh513100'])*D(before['mark_sh513100'])
last=daily6['2026-06-30'];assert D(last['receivable'])==0
ends={c:js(S/'account-results'/c/'roundtrips.json') for c in [f'P{i}' for i in range(8)]}
assert all(not t['closed'] and t['exit_date'] is None and t['sell_fee']==0 for t in ends['P6'])
output=dict(status='passed',order_checks=summary,p7_budget_checks=riskchecks,split_without_quote=dict(date='2022-01-13',before_shares=before['units_sh513100'],after_shares=after['units_sh513100'],before_mark=before['mark_sh513100'],after_mark=after['mark_sh513100'],preserved_mark_date=after['mark_date_sh513100']),limits='No technical open positions or post-sale dividends occur in these real paths; those general code branches require separate synthetic tests and cannot be claimed proven here.')
(P/'order-boundary-checks.json').write_text(json.dumps(output,ensure_ascii=False,indent=2,default=str)+'\n');print(json.dumps({'status':'passed','orders':sum(x['orders'] for x in summary),'P7_attempts':len(riskchecks),'real_post_sale_dividend_cases':sum(x['post_sale_receivable_real_occurrences'] for x in summary)},ensure_ascii=False))
