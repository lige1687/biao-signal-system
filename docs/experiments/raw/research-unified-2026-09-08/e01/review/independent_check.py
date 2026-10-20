"""Independent E01 arithmetic review. No research engine imported or executed."""
from pathlib import Path
import json,hashlib,calendar
import numpy as np
import pandas as pd
P=Path(__file__).resolve().parents[1];R=P/'review'
def read(s):return pd.read_parquet(P/'inputs/cache'/f'{s}.parquet')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
sources=[p for p in P.rglob('*') if p.is_file() and 'review' not in p.relative_to(P).parts];before={str(p.relative_to(P)):digest(p) for p in sources}
old=json.loads((P/'inputs/legacy_results.json').read_text());breadth=read('breadth_cn_all');cache={};paired=[];errors=[]
for group,ss in old['trades'].items():
 if not group.endswith('|Xtarget'):continue
 kind=group.split('|')[0]
 for sym,trades in ss.items():
  if sym not in cache:
   d=read(sym).join(breadth[['b200']],how='inner').sort_index();d=d[d.b200.notna()];ma=d.close.rolling(200).mean();hi=d.close.rolling(500,min_periods=100).max();d=d[ma.notna()&hi.notna()];cache[sym]=d
  d=cache[sym];week={}
  for i,t in enumerate(d.index):week[t.isocalendar()[:2]]=i
  for t in trades:
   e=d.index.get_loc(t['entry_date']);buys=[i+1 for i in week.values() if e<i+1<=e+252]
   # Budget-normalized sum of acquired units; no AST reuse of original study.
   spent=sum(1/len(buys) for _ in buys)
   for fee in [10,20]:
    f=fee/10000;qty=sum((1-f)/len(buys)/float(d.open.iloc[i]) for i in buys)
    out=[]
    for lag in [0,1]:
     candidate=next((i for i in range(e+253,min(e+756,len(d))) if qty*float(d.close.iloc[i-lag])/spent-1>=.30),None)
     forced=candidate is None;i=min(e+756,len(d)-1) if forced else candidate
     out.append({'exit':str(d.index[i].date()),'ret':qty*float(d.open.iloc[i])*(1-f)/spent-1,'forced':forced,'holding':(i-e)/21})
    a,b=out
    if fee==10:
     if not(a['exit']==t['exit_date'] and a['forced']==t['forced'] and abs(a['ret']-t['ret'])<1e-12 and abs(a['holding']-t['hold_months'])<1e-12):errors.append({'type':'baseline','symbol':sym,'entry':t['entry_date']})
    paired.append({'key':f'{sym}|{kind}|{t["entry_date"]}','fee_bps':fee,'legacy_ret':a['ret'],'causal_ret':b['ret'],'legacy_exit':a['exit'],'causal_exit':b['exit'],'delta':b['ret']-a['ret']})
actual=pd.read_csv(P/'paired-differences.csv').set_index(['key','fee_bps']);max_pair_error=0
for x in paired:
 row=actual.loc[(x['key'],x['fee_bps'])]
 for k in ['legacy_ret','causal_ret','delta']:max_pair_error=max(max_pair_error,abs(float(row[k])-x[k]))
 for k in ['legacy_exit','causal_exit']:
  if row[k]!=x[k]:errors.append({'type':'paired_date','key':x['key'],'field':k})
acts=pd.read_csv(P/'account-actions.csv');plans=pd.read_csv(P/'account-plans.csv');evs=pd.read_csv(P/'account-events.csv');summaries=json.loads((P/'account-summary.json').read_text());allchecks=[]
for sm in summaries:
 case=sm['case'];sym,kind,fee_label=case.split('|');f=sm['fee_bps']/10000;d=read(sym);idx=d.index;day=pd.read_csv(P/'daily'/f'{case.replace("|","_")}.csv.gz');ca=acts[acts.case==case];cp=plans[plans.case==case].sort_values('plan');ce=evs[evs.case==case]
 bydate={date:g for date,g in ca.groupby('date',sort=False)};cash=1.;qty=0.;paid=0.;maxeq=0.;last_exit=None;seen_buy_plans=set();mapping={int(r.plan):r for r in cp.itertuples()}
 for row in cp.itertuples():
  if last_exit and pd.Timestamp(row.trigger)<=pd.Timestamp(last_exit)+pd.Timedelta(hours=9,minutes=30):errors.append({'type':'overlapping_plan','case':case,'plan':row.plan})
  last_exit=row.exit_date if pd.notna(row.exit_date) else None
  pa=ca[ca.plan==row.plan];purchases=pa[pa.action=='buy']
  if len(purchases)>52 or abs(purchases.amount.sum()-row.invested)>1e-10 or len(purchases)!=row.buy_count:errors.append({'type':'plan_buys','case':case,'plan':row.plan})
  if purchases.amount.max()>row.budget/52+1e-12:errors.append({'type':'installment_cap','case':case,'plan':row.plan})
 # Event acceptance checked against actual previously accepted lifecycle at decision time.
 for event in ce.itertuples():
  ts=pd.Timestamp(event.decision_at);occupied=any(pd.Timestamp(q.trigger)<ts and (pd.isna(q.exit_date) or pd.Timestamp(q.exit_date)+pd.Timedelta(hours=9,minutes=30)>ts) for q in cp.itertuples())
  if (event.status=='rejected_capital_occupied')!=occupied and event.status!='unexecuted_no_next_quote':errors.append({'type':'event_occupancy','case':case,'event':event.event_id})
 for row in day.itertuples():
  for a in bydate.get(row.date, pd.DataFrame()).itertuples():
   i=idx.get_loc(a.date);p=mapping[int(a.plan)];scheduled=pd.Timestamp(a.available_at);execution=pd.Timestamp(a.date)+pd.Timedelta(hours=9,minutes=30)
   if not scheduled<execution or abs(a.price-float(d.open.iloc[i]))>1e-10:errors.append({'type':'action_timing_price','case':case,'date':a.date})
   if abs(a.fee-a.amount*f)>1e-10:errors.append({'type':'fee','case':case,'date':a.date})
   if a.action=='buy':
    if not(p.e<i<=p.e+252) or not scheduled>pd.Timestamp(p.trigger) or scheduled.weekday()!=6 or scheduled.hour!=23 or scheduled.minute!=59:errors.append({'type':'weekly_schedule','case':case,'date':a.date})
    first=int(idx.searchsorted(scheduled,side='right'))
    if first!=i:errors.append({'type':'not_first_quote','case':case,'date':a.date})
    if abs(a.units*a.price-(a.amount-a.fee))>1e-10:errors.append({'type':'buy_quantity','case':case,'date':a.date})
    # Original available budget: all prior sold capital, no credit or external inflow.
    if a.plan not in seen_buy_plans and abs(cash-p.budget)>1e-10:errors.append({'type':'new_budget','case':case,'plan':a.plan})
    cash-=a.amount;qty+=a.units;seen_buy_plans.add(a.plan)
   else:
    if i<=p.e+252 or abs(a.units-qty)>1e-10 or abs(a.amount-a.price*qty)>1e-10:errors.append({'type':'sell','case':case,'date':a.date})
    if a.reason=='target30' and qty*float(d.close.iloc[i-1])/p.invested-1<.3-1e-12:errors.append({'type':'target_uses_previous_close','case':case,'date':a.date})
    if a.reason=='deadline' and i<p.e+756:errors.append({'type':'early_deadline','case':case,'date':a.date})
    cash+=a.amount-a.fee;qty-=a.units
   paid+=a.fee
  reconstructed=cash+qty*float(d.loc[pd.Timestamp(row.date),'close']);maxeq=max(maxeq,abs(reconstructed-row.equity),abs(cash-row.cash),abs(qty-row.units),abs(paid-row.cumulative_fees))
  if cash< -1e-10:errors.append({'type':'negative_cash','case':case,'date':row.date})
 if abs(day.external_inflow.sum()-1)>1e-12 or abs(day.external_outflow.sum())>1e-12:errors.append({'type':'external_funding','case':case})
 if abs(reconstructed-sm['final_wealth'])>1e-10:errors.append({'type':'final','case':case})
 allchecks.append({'case':case,'daily_rows':len(day),'actions':len(ca),'plans':len(cp),'max_cash_equity_quantity_fee_error':maxeq})
sub=[x for x in paired if x['fee_bps']==10]
result={'baseline_count':len(sub),'paired_all_fees_count':len(paired),'baseline_all_fields_match':not any(x['type']=='baseline' for x in errors),'changed_exit_count':sum(x['legacy_exit']!=x['causal_exit'] for x in sub),'mean_delta':sum(x['delta'] for x in sub)/len(sub),'max_pair_return_error':max_pair_error,'account_paths':len(allchecks),'accounts':allchecks,'errors':errors,'source_files_unchanged':all(digest(P/k)==v for k,v in before.items()),'source_sha256':before}
(R/'independent-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');pd.DataFrame(paired).to_csv(R/'independent-paired.csv',index=False)
print(json.dumps({k:v for k,v in result.items() if k not in ['accounts','source_sha256']},ensure_ascii=False,indent=2));print('max_account_error',max(x['max_cash_equity_quantity_fee_error'] for x in allchecks))
