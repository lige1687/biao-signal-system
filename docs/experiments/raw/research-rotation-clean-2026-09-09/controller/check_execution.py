from pathlib import Path
import importlib.util,json,pandas as pd,numpy as np
B=Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('independent_full',B/'full-review/verify_full.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
p,a=v.inputs();z=v.indicators(p,a);raw=p.set_index(['date','symbol']);zi=z.set_index(['date','symbol']);cfg=json.loads((B/'full-protocol.json').read_text());e=pd.read_csv(B/'full-execution/equity.csv',parse_dates=['date']);t=pd.read_csv(B/'full-execution/trades.csv',parse_dates=['date','signal_date'],dtype={'symbol':str});sig=pd.read_csv(B/'full-execution/signals.csv');fail=[];checked=0;expected_stop=0;overrides=0
for r in t.itertuples():
 checked+=1;k=(r.date,r.symbol)
 if k not in raw.index:fail.append(['missing quote',str(k)]);continue
 bar=raw.loc[k]
 if r.date<=r.signal_date or abs(r.price-bar.open)>1e-10 or bar.volume<=0 or abs(bar.high-bar.low)<1e-12:fail.append(['fill timing/price/volume',str(k)])
 if r.side=='buy' and r.reason!='monthly':fail.append(['nonmonthly buy',str(k)])
 if r.symbol=='512890' and str(r.date.date())=='2021-10-22':fail.append(['known halt',str(k)])
for k,g in t.groupby(['account_id','date','symbol']):
 if g.side.nunique()>1:fail.append(['same day two sides',str(k)])
for account,g in e.groupby('account_id'):
 if 'sma200' not in account:continue
 pool=account.split('-')[0];symbols=cfg['pools'][pool];union=sorted(p[(p.symbol.isin(symbols))&(p.date>=v.START)&(p.date<=v.END)].date.unique());nextday=dict(zip(union[:-1],union[1:]));gd=g.set_index('date');ss=sig[sig.account_id==account];actual={(r.decision_date,r.selected,r.eligible_date) for r in ss.itertuples() if r.trend_states=='daily_below_sma200'};expected=set();monthly=set(ss[ss.trend_states!='daily_below_sma200'].eligible_date)
 for row in g.itertuples():
  nd=nextday.get(row.date)
  if nd is None:continue
  for symbol in symbols:
   q=zi.loc[(row.date,symbol)] if (row.date,symbol) in zi.index else None
   if getattr(row,'units_'+symbol,0)>0 and q is not None and pd.notna(q.sma200) and q.idx<q.sma200:
    expected.add((str(row.date.date()),symbol,str(nd.date())))
    if str(nd.date()) in monthly:overrides+=1;continue
    if (nd,symbol) in raw.index and raw.loc[(nd,symbol)].volume>0 and raw.loc[(nd,symbol)].high!=raw.loc[(nd,symbol)].low:
     if gd.loc[nd,'units_'+symbol]>1e-9:fail.append(['did not fully exit next valid open',account,str(row.date.date()),symbol])
 expected_stop+=len(expected)
 if expected!=actual:fail.append(['daily signals mismatch',account,len(expected-actual),len(actual-expected)])
out={'status':'passed' if not fail else 'failed','trade_fills_checked':checked,'expected_daily_exit_signals':expected_stop,'month_boundary_final_target_overrides':overrides,'failures':fail,'independent_indicators':'full-review/verify_full.py; no call to execution indicator function','scope':'actual open fills, signal-before-fill, buy only monthly, no same-day roundtrip, full exit on next valid nonmonthly open, independently recomputed daily exit triggers'}
(B/'controller/execution-checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False,indent=2))
assert not fail
