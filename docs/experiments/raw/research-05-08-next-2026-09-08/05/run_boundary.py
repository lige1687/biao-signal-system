"""Offline reporting-only successor to frozen E01. No production writes."""
from pathlib import Path
import importlib.util, inspect, json, hashlib
import numpy as np
import pandas as pd
P=Path(__file__).resolve().parent
OLD=P.parents[1]/'research-unified-2026-09-08/e01'
spec=importlib.util.spec_from_file_location('frozen_e01',P.parent/'inputs/prior/e01.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.P=OLD
protocol='''Frozen boundary check: reporting only; budgets, thresholds, prices and execution unchanged. Log expired pending buys after 252 quote days; log pending buys cancelled at 52 buys; log pending buys/exits at cutoff. A zero-position expiry is recorded as a cash-only plan expiry, not an economic sale. Invalid closes remain a hard failure; no invented marks. Compare all five original outputs for 64 frozen accounts; synthetic cases use hand-known actions and dates. No parameter search.'''
(P/'protocol.txt').write_text(protocol)
src=inspect.getsource(m.account)
src=src.replace('idx=d.index;n=len(d);','diagnostics=[]\n idx=d.index;n=len(d);',1)
src=src.replace("val=units*opens[i];", "\n  if units==0:diagnostics.append(dict(plan=active['id'],date=str(idx[i].date()),status='cash_only_plan_expired',pending_reason=reason))\n  val=units*opens[i];",1)
src=src.replace("expired=i>=active['e']+756", "\n   for ts in active['pending_buys']:diagnostics.append(dict(plan=active['id'],date=str(idx[i].date()),scheduled_at=str(ts),status='cancelled_accumulation_ended'))\n   active['pending_buys']=[]\n   expired=i>=active['e']+756",1)
src=src.replace("if active['buys']>=52:break", "if active['buys']>=52:\n     for pending in active['pending_buys']:diagnostics.append(dict(plan=active['id'],date=str(idx[i].date()),scheduled_at=str(pending),status='cancelled_buy_cap'))\n     active['pending_buys']=[]\n     break",1)
src=src.replace("due=list(active['pending_buys'])", "if active['buys']>=52:\n    for pending in active['pending_buys']:diagnostics.append(dict(plan=active['id'],date=str(idx[i].date()),scheduled_at=str(pending),status='cancelled_buy_cap'))\n    active['pending_buys']=[]\n   due=list(active['pending_buys'])",1)
src=src.replace("if active:trades.append", "if active:\n  for ts in active['pending_buys']:diagnostics.append(dict(plan=active['id'],date=str(idx[-1].date()),scheduled_at=str(ts),status='unexecuted_buy_at_cutoff'))\n  if active['pending_exit'] is not None:diagnostics.append(dict(plan=active['id'],date=str(idx[-1].date()),status='unexecuted_exit_at_cutoff',reason=active['pending_exit'][0],available_at=str(active['pending_exit'][1])))\n if active:trades.append",1)
src=src.replace('return summary,daily,trades,event_rows,actions','return summary,daily,trades,event_rows,actions,diagnostics')
(P/'account_reporting_v3.py').write_text(src)
ns=dict(m.__dict__);exec(compile(src,'account_reporting_v3.py','exec'),ns);fn=ns['account']
checks=[]
def run(n,missing=(),events=None):
 idx=pd.bdate_range('2020-01-01',periods=n);d=pd.DataFrame({'open':1.,'close':1.},index=idx)
 for lo,hi in missing:d.iloc[lo:hi,d.columns.get_loc('open')]=np.nan
 ev=events if events is not None else [dict(e=0,decision_at=idx[0]+pd.Timedelta(hours=16))]
 return d,fn(d,0,ev,0.,'synthetic')
d,r=run(260,[(240,253)])
assert any(x['status']=='cancelled_accumulation_ended' for x in r[5])
assert not any(x['action']=='buy' and x['date']>str(d.index[252].date()) for x in r[4])
checks.append('pending buy cancelled after accumulation; no late purchase')
d,r=run(8,[(3,8)]);assert any(x['status']=='unexecuted_buy_at_cutoff' for x in r[5]);checks.append('cutoff preserves unexecuted buy evidence')
d,r=run(758,[(756,758)]);assert any(x['status']=='unexecuted_exit_at_cutoff' for x in r[5]);assert not any(x['action']=='sell' for x in r[4]);checks.append('missing deadline open does not create sale')
d,r=run(760,[(756,758)]);sales=[x for x in r[4] if x['action']=='sell'];assert len(sales)==1 and sales[0]['date']==str(d.index[758].date());checks.append('pending sale executes at first available open')
d,r=run(760,[(0,756)]);assert r[0]['final_wealth']==1 and any(x['status']=='cash_only_plan_expired' for x in r[5]);checks.append('zero holdings expire as cash-only plan, with legacy zero-value action retained for comparability')
d,r=run(8);e=[dict(e=7,decision_at=d.index[7]+pd.Timedelta(hours=16))];r=fn(d,0,e,0.,'last');assert r[0]['unexecuted_no_next_quote']==1 and len(r[4])==0;checks.append('last-close decision cannot execute within cutoff')
idx=pd.date_range('2020-01-01',periods=850,freq='7D');d=pd.DataFrame({'open':1.,'close':1.},index=idx);r=fn(d,0,[dict(e=0,decision_at=idx[0]+pd.Timedelta(hours=16))],0.,'cap');assert len([x for x in r[4] if x['action']=='buy'])==52 and any(x['status']=='cancelled_buy_cap' for x in r[5]);checks.append('52-purchase cap reports remaining schedules as cancelled')
idx=pd.date_range('2020-01-01',periods=55,freq='7D');d=pd.DataFrame({'open':1.,'close':1.},index=idx);d.iloc[53:,0]=np.nan;r=fn(d,0,[dict(e=0,decision_at=idx[0]+pd.Timedelta(hours=16))],0.,'cap_missing_open');assert len(r[5])==2 and [x['date'] for x in r[5]]==[str(idx[i].date()) for i in [53,54]] and all(x['status']=='cancelled_buy_cap' for x in r[5]);checks.append('cap cancels on both exact schedule dates even with missing opens')
comp=[];diagnostics=[]
for s in m.SYMS:
 d,start=m.full_frame(s)
 for k in m.KINDS:
  ev=m.events_for(d,start,k)
  for fee in [10.,20.]:
   case=f'{s}|{k}|fee{int(fee)}';old=m.account(d,start,ev,fee,case);new=fn(d,start,ev,fee,case)
   assert old==new[:5],case
   comp.append(dict(case=case,all_five_outputs_identical=True));diagnostics.extend(dict(case=case,**x) for x in new[5])
out=dict(synthetic_checks=checks,accounts_checked=len(comp),all_original_outputs_identical=True,diagnostic_rows=len(diagnostics),status_counts=pd.Series([x['status'] for x in diagnostics]).value_counts().to_dict(),protocol_sha256=hashlib.sha256(protocol.encode()).hexdigest())
(P/'results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));(P/'comparisons.json').write_text(json.dumps(comp,indent=2));(P/'pending-arrangements.json').write_text(json.dumps(diagnostics,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
