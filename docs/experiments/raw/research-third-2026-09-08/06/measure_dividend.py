"""One known dividend event: valuation audit, not a strategy return test."""
from pathlib import Path
import json,hashlib
import pandas as pd
P=Path(__file__).resolve().parent
def bars(path):
 rows=json.loads(path.read_text())['data']['sh510300']['day']
 return pd.DataFrame([x[:6] for x in rows],columns=['date','open','close','high','low','volume']).set_index('date').astype(float)
def ledger(prices,dividend,ex_date,pay_date,split_date=None,split_ratio=1):
 units=1.;cash=0.;receivable=0.;entitlement=0.;rows=[];initial=float(prices.iloc[0])
 for date,price in prices.items():
  if date==split_date:units*=split_ratio
  if date==ex_date:entitlement=units*dividend;receivable+=entitlement
  if date==pay_date:cash+=entitlement;receivable-=entitlement
  equity=units*price+cash+receivable
  rows.append(dict(date=date,units=units,nominal_close=price,cash=cash,dividend_receivable=receivable,equity=equity,normalized_wealth=equity/initial,external_flow=initial if not rows else 0.))
 return pd.DataFrame(rows).set_index('date')
test=ledger(pd.Series([10.,9.,9.],index=['a','b','c']),1.,'b','c');assert test.equity.tolist()==[10.,10.,10.] and test.cash.tolist()==[0.,0.,1.] and test.dividend_receivable.tolist()==[0.,1.,0.] and test.external_flow.sum()==10
split=ledger(pd.Series([10.,2.],index=['a','b']),0.,None,None,'b',5);assert split.equity.tolist()==[10.,10.] and split.units.tolist()==[1.,5.]
prices=bars(P/'510300-nominal-2025.json').close;qfq=pd.read_csv(P/'sh510300-qfq.csv',index_col=0).close.reindex(prices.index)
d=ledger(prices,.088,'2025-06-18','2025-06-27');d['qfq_normalized']=qfq/qfq.iloc[0];d['nominal_only_normalized']=prices/prices.iloc[0];d.to_csv(P/'dividend-daily-ledger.csv',float_format='%.17g')
ratios=[]
for date in ['2025-06-17','2025-06-18','2025-06-26','2025-06-27','2025-06-30']:
 row=d.loc[date];ratios.append(dict(date=date,nominal_price=float(prices.loc[date]),qfq_price=float(qfq.loc[date]),raw_minus_qfq=float(prices.loc[date]-qfq.loc[date]),cash=float(row.cash),receivable=float(row.dividend_receivable),normalized_wealth=float(row.normalized_wealth)))
old=bars(P/'510300-nominal-2013.json').close;adj=pd.read_csv(P/'sh510300-qfq.csv',index_col=0).close.reindex(old.index)
result=dict(window=[d.index.min(),d.index.max()],initial_nominal_wealth=float(prices.iloc[0]),nominal_plus_cash_return=float(d.normalized_wealth.iloc[-1]-1),qfq_ratio_return=float(d.qfq_normalized.iloc[-1]-1),nominal_price_only_return=float(d.nominal_only_normalized.iloc[-1]-1),qfq_minus_actual_percentage_points=float((d.qfq_normalized.iloc[-1]-d.normalized_wealth.iloc[-1])*100),rows=ratios,synthetic_checks={'dividend_is_not_external_deposit':True,'receivable_not_spendable_until_pay_date':True,'split_conserves_wealth':True},nominal_2013_min_raw_minus_qfq=float((old-adj).min()),nominal_2013_max_raw_minus_qfq=float((old-adj).max()),protocol_sha256=hashlib.sha256((P/'measurement-protocol.json').read_bytes()).hexdigest(),scope='Known fixed holding; no trading performance claim or full-history dividend verification.')
(P/'dividend-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
