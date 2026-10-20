"""Independent mixed-defense order/state and accounting audit; no execution imports."""
from pathlib import Path
from collections import defaultdict
import pandas as pd,numpy as np,json,hashlib
B=Path(__file__).resolve().parents[1]; SRC=B.parent/'research-rotation-clean-2026-09-09'; D=SRC/'full-pool-preparation'; X=B/'execution'; O=B/'review'
PROTO=json.loads((B/'protocol.json').read_text()); SYMS=PROTO['symbols']

def load_index():
 p=pd.read_csv(D/'prices.csv',parse_dates=['date']);p.symbol=p.symbol.str[:6];p=p[p.symbol.isin(SYMS)].sort_values(['symbol','date'])
 acts=json.loads((D/'action-sources/normalized-actions.json').read_text())['events']; by=defaultdict(list)
 for a in acts:by[a['symbol']].append(a)
 out=[]
 for s,g in p.groupby('symbol'):
  level=1.;prev=None;pc=None;vals=[]
  for r in g.itertuples():
   if prev is not None:
    u=1.;cash=0.
    for a in sorted(by[s],key=lambda x:x.get('effective_date') or '9999'):
     ed=a.get('effective_date')
     if ed and prev.date()<pd.Timestamp(ed).date()<=r.date.date():
      if a['type']=='split':u*=float(a['split_ratio'])
      elif a['type']=='cash_dividend':cash+=u*float(a['cash_per_unit'])
    level*=((u*r.close+cash)/pc)
   vals.append(level);prev=r.date;pc=r.close
  z=pd.DataFrame({'date':g.date,'symbol':s,'idx':vals});z['sma200']=z.idx.rolling(200).mean();out.append(z)
 return p,pd.concat(out),acts

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 if not (X/'summary.json').exists():print('prepared');return
 p,idx,acts=load_index(); tr=pd.read_csv(X/'trades.csv');sig=pd.read_csv(X/'signals.csv'); orders=pd.read_csv(X/'orders.csv');eq=pd.read_csv(X/'equity.csv')
 fails=[];checks=defaultdict(int)
 # Old methods must reproduce prior full14 paths exactly on all financial fields.
 oldeq=pd.read_csv(SRC/'full-execution/equity.csv');oldt=pd.read_csv(SRC/'full-execution/trades.csv')
 refs={'no_exit_100':'momentum_top3','monthly_reentry_exit':'momentum_top3_sma200'}
 for method,old in refs.items():
  for fee in [.001,.002]:
   aid=f'{method}-fee{fee:.3f}';oid=f'full14-{old}-fee{fee:.3f}'
   a=eq[eq.account_id==aid].reset_index(drop=True);b=oldeq[oldeq.account_id==oid].reset_index(drop=True)
   cols=[c for c in b.columns if c!='account_id'];checks['old_daily']+=len(a)
   if len(a)!=len(b) or any(np.nanmax(np.abs(a[c]-b[c]))>1e-8 if np.issubdtype(a[c].dtype,np.number) else not a[c].equals(b[c]) for c in cols):fails.append({'type':'old_daily', 'method':method,'fee':fee})
   a=tr[tr.account_id==aid].reset_index(drop=True);b=oldt[oldt.account_id==oid].reset_index(drop=True);cols=['date','symbol','side','qty','price','notional','fee','reason','signal_date'];checks['old_trades']+=len(a)
   if len(a)!=len(b) or any(np.nanmax(np.abs(a[c]-b[c]))>1e-8 if np.issubdtype(a[c].dtype,np.number) else not a[c].equals(b[c]) for c in cols):fails.append({'type':'old_trades','method':method,'fee':fee})
 # 75% monthly signal weights and fills against frozen target values.
 for r in sig[sig.account_id.str.startswith('no_exit_75')].itertuples():
  if str(getattr(r,'trend_states',''))=='daily_below_sma200':continue
  w=json.loads(r.weights);checks['75_monthly_signals']+=1
  if abs(sum(w.values())-(1.0 if any(v>0 for v in w.values()) else 0))>1e-12:fails.append({'type':'75_weight','account':r.account_id,'date':r.decision_date})
 # Fast reentry provenance and budget. Execution must expose stop source/budget in orders/trades.
 im={(str(r.date.date()),r.symbol):(r.idx,r.sma200) for r in idx.itertuples()}; union=sorted(p.date.dt.strftime('%Y-%m-%d').unique())
 for aid,g in tr[tr.account_id.str.startswith('fast_reentry_exit')].groupby('account_id'):
  budgets={}; last_stop={}; month_epoch=None
  for r in g.itertuples():
   if r.reason=='monthly':
    if month_epoch!=r.date[:7]:budgets.clear();last_stop.clear();month_epoch=r.date[:7]
   elif r.side=='sell' and r.reason in ('stop','daily_sma200_exit'):
    budgets[str(r.symbol)]=r.notional-r.fee;last_stop[str(r.symbol)]=r.date;checks['fast_stops']+=1
   elif r.side=='buy' and r.reason in ('fast_reentry','reentry'):
    s=str(r.symbol);checks['fast_reentries']+=1
    if s not in budgets: continue
    if r.notional+r.fee>budgets[s]+1e-7:fails.append({'type':'budget_overspend','account':aid,'date':r.date,'symbol':s,'over':r.notional+r.fee-budgets[s]})
    prev=[d for d in union if last_stop[s]<d<r.date and (d,s) in im and pd.notna(im[(d,s)][1]) and im[(d,s)][0]>=im[(d,s)][1]]
    if not prev: pass
    elif not (prev[-1]<r.date):fails.append({'type':'same_day_information','account':aid,'date':r.date,'symbol':s})
    budgets.pop(s);last_stop.pop(s)
 # Independent bidirectional reentry-event completeness audit.
 rev=pd.read_csv(X/'reentry_events.csv')
 for aid,gg in rev.groupby('account_id'):
  triggers=gg[gg.event=='reentry_triggered']; fills=gg[gg.event=='reentry_filled']; stops=gg[gg.event=='stop_budget_created']; checks['reentry_event_stops']+=len(stops);checks['reentry_event_triggers']+=len(triggers);checks['reentry_event_fills']+=len(fills)
  for rr in triggers.itertuples():
   q=im.get((rr.recovery_signal_date,str(rr.symbol)))
   if not q or pd.isna(q[1]) or q[0]+1e-14<q[1]:fails.append({'type':'trigger_without_independent_recovery','account':aid,'date':rr.recovery_signal_date,'symbol':str(rr.symbol)})
   earlier=[d for d in union if str(rr.source_stop_date)<d<rr.recovery_signal_date and (d,str(rr.symbol)) in im and pd.notna(im[(d,str(rr.symbol))][1]) and im[(d,str(rr.symbol))][0]>=im[(d,str(rr.symbol))][1]]
   if earlier:fails.append({'type':'late_trigger','account':aid,'date':rr.recovery_signal_date,'earlier':earlier[0],'symbol':str(rr.symbol)})
  for rr in fills.itertuples():
   match=triggers[(triggers.symbol==rr.symbol)&(triggers.source_stop_date==rr.source_stop_date)&(triggers.recovery_signal_date==rr.recovery_signal_date)]
   if len(match)!=1:fails.append({'type':'fill_trigger_cardinality','account':aid,'date':rr.date,'symbol':str(rr.symbol)})
  # Every trigger must fill or be explicitly superseded at monthly execution.
  for rr in triggers.itertuples():
   filled=((fills.symbol==rr.symbol)&(fills.source_stop_date==rr.source_stop_date)&(fills.recovery_signal_date==rr.recovery_signal_date)).any()
   canceled=((gg.event=='monthly_cancel')&(gg.symbol==rr.symbol)&(gg.date>=rr.eligible_date)).any()
   if not filled and not canceled:fails.append({'type':'trigger_neither_filled_nor_monthly_canceled','account':aid,'date':rr.recovery_signal_date,'symbol':str(rr.symbol)})
 # 75% target dollars are applied at execution although signal weights retain sum one.
 oo=orders[(orders.account_id.str.startswith('no_exit_75'))&(orders['kind']=='monthly')]
 for (aid,sd,ed),gq in oo.groupby(['account_id','signal_date','eligible_date']):
  # use one terminal/completed row per symbol to avoid counting delay repeats
  lastq=gq.sort_values('date').groupby('symbol').tail(1); se=sig[(sig.account_id==aid)&(sig.decision_date==sd)]
  if len(se):
   expected=.75*float(se.opening_equity.iloc[0]); actual=float(lastq.target_value.sum()); checks['75_target_groups']+=1
   if abs(expected-actual)>1e-6:fails.append({'type':'75_target_value','account':aid,'date':ed,'diff':actual-expected})
 # independent ledger replay from actual fills/actions
 action_by=defaultdict(list)
 for a in acts:
  for k in ['record_date','effective_date','pay_date']:
   if a.get(k):action_by[a[k]].append((k,a))
 for aid,g in eq.groupby('account_id'):
  cash=1e6;rec=0.;units={s:0. for s in SYMS};ent={};dues={};last={};tg=tr[tr.account_id==aid];prices={(str(r.date.date()),r.symbol):r for r in p.itertuples()}
  for r in g.itertuples():
   for k,a in action_by.get(r.date,[]):
    s=a['symbol']
    if a['type']=='split' and k=='effective_date':units[s]*=float(a['split_ratio']);last[s]=last.get(s,0)/float(a['split_ratio'])
    elif a['type']=='cash_dividend' and k=='effective_date':amt=ent.get(a['event_id'],units[s])*float(a['cash_per_unit']);dues[a['event_id']]=amt;rec+=amt
    elif a['type']=='cash_dividend' and k=='pay_date':amt=dues.pop(a['event_id'],0);rec-=amt;cash+=amt
   for t in tg[tg.date==r.date].itertuples():
    if t.side=='buy':cash-=t.notional+t.fee;units[str(t.symbol)]+=t.qty
    else:cash+=t.notional-t.fee;units[str(t.symbol)]-=t.qty
   for k,a in action_by.get(r.date,[]):
    if a['type']=='cash_dividend' and k=='record_date':ent[a['event_id']]=units[a['symbol']]
   for s in SYMS:
    q=prices.get((r.date,s));
    if q:last[s]=q.close
   val=cash+rec+sum(units[s]*last.get(s,0) for s in SYMS);checks['ledger_rows']+=1
   if max(abs(val-r.equity),abs(cash-r.cash),abs(rec-r.receivable))>1e-7:fails.append({'type':'ledger','account':aid,'date':r.date,'diff':val-r.equity})
 result={'passed':not fails,'checks':checks,'failures':fails,'limits':['Fast-order validation checks budget and causal recovery from source prices; detailed queue cancellation also relies on execution orders evidence.','Historical comparison is descriptive and follows the fixed surviving-ETF pool.']};(O/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(result['passed'],dict(checks),len(fails))
if __name__=='__main__':main()
