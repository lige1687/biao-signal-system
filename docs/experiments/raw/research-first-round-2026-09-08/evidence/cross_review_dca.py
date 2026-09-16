"""Independent arithmetic review; no import/call of DCA author's test or original engines."""
from pathlib import Path
import json,hashlib
import pandas as pd
import numpy as np
OUT=Path(__file__).resolve().parent;DCA=OUT.parent/'dca';CACHE=DCA/'snapshot/cache'
def bars(sym):
 x=pd.read_parquet(CACHE/f'{sym}.parquet');return x[~x.index.duplicated(keep='last')].sort_index()
p=bars('000300').join(bars('breadth_cn_all')[['b200']],how='inner').dropna(subset=['b200'])
m=p.close.rolling(200).mean();dd=p.close.rolling(500,min_periods=100).max();p=p[m.notna()&dd.notna()]
e=p.index.get_loc('2012-02-07');j=p.index.get_loc('2014-12-08')
# Build ISO-week final dates using plain dictionary replacement, no study helper.
w={}
for i,d in enumerate(p.index): w[d.isocalendar()[:2]]=i
purchase=[i+1 for i in w.values() if e<i+1<=e+252]
u=sum(.999/(len(purchase)*p.open.iloc[i]) for i in purchase)
r13={'entry':'2012-02-07','signal_date':'2014-12-08','purchase_count':len(purchase),'units':u,'previous_close':float(p.close.iloc[j-1]),'same_day_close':float(p.close.iloc[j]),'same_day_open':float(p.open.iloc[j]),'previous_close_return':u*p.close.iloc[j-1]-1,'same_day_close_return':u*p.close.iloc[j]-1,'old_proceeds_return':u*p.open.iloc[j]*.999-1,'next_open_return':u*p.open.iloc[j+1]*.999-1}
pr=pd.read_csv(DCA/'round13_000300_target_paired.csv');row=pr[(pr.entry_type=='deep20')&(pr.entry_date=='2012-02-07')].iloc[0]
assert abs(r13['old_proceeds_return']-row.archived_ret)<1e-12
assert r13['previous_close_return']<.30<=r13['same_day_close_return']
checks={}
for name in ['W5','long']:
 ledger=pd.read_csv(DCA/f'round18_{name}_daily_ledger.csv',parse_dates=['date']).set_index('date')
 syms=['000300','399006','518880','^IXIC'];op=np.column_stack([bars(s).open.reindex(ledger.index) for s in syms]);cl=np.column_stack([bars(s).close.reindex(ledger.index) for s in syms]);assert np.isfinite(op).all() and np.isfinite(cl).all()
 weekfinal={}
 for i,d in enumerate(ledger.index): weekfinal[d.isocalendar()[:2]]=i
 deposits=np.zeros(len(ledger));deposits[list(weekfinal.values())]=1/len(weekfinal)
 assert np.allclose(deposits,ledger.deposit,atol=1e-14)
 cash=0.;hold=[0.]*4;fundshares=0.;navs=[];equities=[]
 for i,d in enumerate(ledger.index):
  # Price existing fund shares at today's open, then issue shares for new money.
  pre=cash+sum(hold[k]*op[i,k] for k in range(4))
  if deposits[i]:
   unitprice=pre/fundshares if fundshares else 1.
   fundshares+=deposits[i]/unitprice;cash+=deposits[i]
  if i>0 and deposits[i-1]>0 and cash>0:
   for k in range(4): hold[k]+=(cash/4)*.999/op[i,k]
   cash=0.
  prev=ledger.index[i-1] if i else d
  if i and (d.year,(d.month-1)//3)!=(prev.year,(prev.month-1)//3):
   values=[hold[k]*op[i,k] for k in range(4)];total=sum(values);charge=sum(abs(v-total/4) for v in values)*.001
   hold=[(total-charge)/4/op[i,k] for k in range(4)]
  eq=cash+sum(hold[k]*cl[i,k] for k in range(4));equities.append(eq);navs.append(eq/fundshares if fundshares else 1.)
 eqa=np.array(equities);nv=np.array(navs);v=eqa[eqa>0]
 checks[name]={'independent_final':equities[-1],'ledger_final':float(ledger.equity.iloc[-1]),'max_equity_error':float(np.max(abs(eqa-ledger.equity))),'max_unit_nav_error':float(np.max(abs(nv-ledger.unit_nav))),'account_balance_drawdown':float(min(v/np.maximum.accumulate(v)-1)),'investment_unit_drawdown':float(min(nv/np.maximum.accumulate(nv)-1)),'final_cash':cash,'fundshares':fundshares,'final_unit_nav':navs[-1]}
 assert checks[name]['max_equity_error']<1e-12
 assert checks[name]['max_unit_nav_error']<1e-12
raw=json.loads((DCA/'snapshot/source/docs/experiments/raw/dca-complete-trades-2026-09-07/dca_complete_trades_results.json').read_text())
allrows=[];adj=[];allpairs=[]
for group,symdict in raw['trades'].items():
 for sym,ts in symdict.items():
  ts=sorted(ts,key=lambda t:t['entry_date']);allrows.extend((sym,t['entry_date'],group) for t in ts)
  for a,b in zip(ts,ts[1:]):
   if b['entry_date']<=a['exit_date']:adj.append((sym,a['entry_date'],b['entry_date'],group))
  for i,a in enumerate(ts):
   for b in ts[i+1:]:
    if b['entry_date']<=a['exit_date']:allpairs.append((sym,a['entry_date'],b['entry_date'],group))
counts={'all_configuration_rows':len(allrows),'unique_symbol_entry_dates':len(set((a,b) for a,b,c in allrows)),'consecutive_overlap_comparisons':len(adj),'unique_overlapping_entry_pairs_ignoring_method':len(set((a,b,c) for a,b,c,d in adj)),'all_overlap_pairs_within_method':len(allpairs)}
result={'round13':r13,'round18':checks,'counts':counts,'method':'Independent plain share issuance/valuation and arithmetic from frozen parquet and CSV; no original engines imported.'}
(OUT/'cross-review-dca-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
