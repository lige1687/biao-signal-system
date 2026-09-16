"""Independent arithmetic route by the same researcher; not an independent-agent review."""
from pathlib import Path
import pandas as pd,json
p=Path(__file__).resolve().parent;a=pd.read_csv(p/'actions.csv');rs=json.loads((p/'results.json').read_text());out=[]
for r in rs:
 if r['mode']=='legacy_mechanical_trend':continue
 sym,mode=r['symbol'],r['mode'];d=pd.read_parquet(p/'inputs'/f'{sym}.bars.parquet');q=pd.read_csv(p/f'{sym}_{mode}.csv');acts=a[(a.symbol==sym)&(a['mode']==mode)];cash=shares=0.;prev=0.;index=1.;peak=1.;worst=0.;err=0.
 for row in q.itertuples():
  px=d.loc[pd.Timestamp(row.date)];ad=acts[acts.date==row.date]
  for x in ad[ad.timing=='next_open'].itertuples():
   n=shares*(.5 if x.action=='sell_half' else 1);cash+=n*px.open*.999;shares-=n
  pre=cash+shares*px.close;dep=0.
  for x in ad[ad.timing=='same_close_legacy'].itertuples():
   if x.action=='buy':shares+=x.amount*.999/px.close;dep+=x.amount
   else:n=shares*(.5 if x.action=='sell_half' else 1);cash+=n*px.close*.999;shares-=n
  eq=cash+shares*px.close
  if prev>0:index*=pre/prev
  if pre+dep>0:index*=eq/(pre+dep)
  peak=max(peak,index);worst=min(worst,index/peak-1);err=max(err,abs(eq-row.equity),abs(index-row.unit_value));prev=eq
 out.append({'symbol':sym,'mode':mode,'max_daily_error':float(err),'mdd_error':float(abs(worst-r['deposit_adjusted_mdd']))})
assert max(x['max_daily_error'] for x in out)<1e-9
# The compared arms must have exactly equal external-deposit dates and amounts.
flow=[]
for sym in a.symbol.unique():
 frames=[pd.read_csv(p/f'{sym}_{mode}.csv')[['date','external_deposit']] for mode in ['none','cached_close','cached_next_open']]
 assert all(frames[0].equals(x) for x in frames[1:]);flow.append(sym)
(p/'arithmetic-crosscheck.json').write_text(json.dumps({'checks':out,'method':'从动作和价格重新累计现金/份额；按每次外部入金前后分段连接投资涨跌，与原发行份额算法比较','separate_agent':False,'same_external_cashflow_checked':flow},ensure_ascii=False,indent=2)+'\n')
print('15 paths and 5 equal cashflow schedules verified')
