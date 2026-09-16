"""Finite, offline E01 audit. No production imports, writes or network calls."""
from pathlib import Path
import ast, json, hashlib, datetime, gzip, io
import numpy as np
import pandas as pd
P=Path(__file__).resolve().parent
SYMS=['SH000001','SZ399001','000300','000015','399006','510500','512100','588000']
KINDS=['deep20','bottom','lowtier','base']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,x):
 (P/name).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False,default=str)+'\n')
def csv(name,rows):
 d=pd.DataFrame(rows);b=d.to_csv(index=False,float_format='%.17g').encode()
 if name.endswith('.gz'):b=gzip.compress(b,mtime=0)
 (P/name).write_bytes(b)
def load_bars(s):return pd.read_parquet(P/'inputs/cache'/f'{s}.parquet')
def breadth(_='cn_all'):return pd.read_parquet(P/'inputs/cache/breadth_cn_all.parquet')[["b20","b50","b200","ad","ad20"]]
def align(a,b):return a.join(b,how='inner').sort_index()
def legacy_functions(fee):
 ns=dict(np=np,pd=pd,FEE=fee,ACCUM=252,MAX_HOLD=504,COOLDOWN=126,load_index_bars=load_bars,load_breadth=breadth,align_index_breadth=align)
 t=ast.parse((P/'inputs/legacy_study.py').read_text());t.body=[q for q in t.body if isinstance(q,ast.FunctionDef) and q.name in ['build_states','entry_events','run_trade']];exec(compile(t,'frozen_legacy_functions','exec'),ns)
 fn=ast.parse((P/'inputs/legacy_study.py').read_text());fn=next(q for q in fn.body if isinstance(q,ast.FunctionDef) and q.name=='run_trade');fn.name='causal_run_trade'
 class Lag(ast.NodeTransformer):
  def visit_Subscript(self,n):
   n=self.generic_visit(n)
   if isinstance(n.value,ast.Name) and n.value.id=='closes' and isinstance(n.slice,ast.Name) and n.slice.id=='j':n.slice=ast.BinOp(left=ast.Name(id='j',ctx=ast.Load()),op=ast.Sub(),right=ast.Constant(1))
   return n
 fn=Lag().visit(fn);exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'single_causality_change','exec'),ns);return ns

def paired():
 old=json.loads((P/'inputs/legacy_results.json').read_text());rows=[];pairs=[];mismatches=[]
 for fee in [10.,20.]:
  ns=legacy_functions(fee)
  for s in SYMS:
   df=ns['build_states'](s)
   for k in KINDS:
    for t in old['trades'][k+'|Xtarget'].get(s,[]):
     key=f"{s}|{k}|{t['entry_date']}";e=df.index.get_loc(pd.Timestamp(t['entry_date']))
     a=ns['run_trade'](df,e,'Xtarget');b=ns['causal_run_trade'](df,e,'Xtarget')
     if fee==10 and (a['exit_date']!=t['exit_date'] or abs(a['ret']-t['ret'])>1e-10):mismatches.append(dict(key=key,archive=t,rerun=a))
     for label,v in [('legacy',a),('causal',b)]:rows.append(dict(key=key,symbol=s,entry_kind=k,fee_bps=fee,variant=label,**v))
     pairs.append(dict(key=key,symbol=s,entry_kind=k,fee_bps=fee,legacy_ret=a['ret'],causal_ret=b['ret'],delta=b['ret']-a['ret'],legacy_exit=a['exit_date'],causal_exit=b['exit_date'],date_changed=a['exit_date']!=b['exit_date'],legacy_forced=a['forced'],causal_forced=b['forced']))
 csv('paired-trades.csv',rows);csv('paired-differences.csv',pairs);save('baseline-mismatches.json',mismatches)
 assert len(rows)==584 and len(pairs)==292
 if mismatches:raise RuntimeError('Legacy baseline not closed. No candidate verdict permitted.')
 summaries=[]
 for fee in [10.,20.]:
  for s in ['ALL']+SYMS:
   a=[x for x in pairs if x['fee_bps']==fee and (s=='ALL' or x['symbol']==s)];d=np.array([x['delta'] for x in a]);summaries.append(dict(symbol=s,fee_bps=fee,n=len(a),changed=sum(x['date_changed'] for x in a),mean_delta=float(d.mean()),median_delta=float(np.median(d)),min_delta=float(d.min()),max_delta=float(d.max()),positive=int((d>1e-12).sum()),negative=int((d< -1e-12).sum()),zero=int((abs(d)<=1e-12).sum())))
 save('paired-summary.json',summaries);return summaries

def full_frame(s):
 d=load_bars(s).join(breadth(),how='left');end=min(d.index.max(),breadth().b200.last_valid_index());d=d.loc[:end].copy();c=d.close
 ma=c.rolling(200,min_periods=200).mean();high=c.rolling(500,min_periods=100).max();high=high.where(c.isna().rolling(500,min_periods=1).sum()==0)
 d['gap']=c/ma-1;d['dd']=c/high-1
 valid=d[['gap','dd','b200']].notna().all(axis=1);start=int(np.flatnonzero(valid)[0]);return d,start

def events_for(d,start,k):
 idx=d.index
 if k=='base':
  ev=[];last=-10**9
  ends=pd.date_range(idx[start].to_period('M').start_time,idx[-1]+pd.offsets.MonthEnd(0),freq='ME')
  for day in ends:
   ts=day+pd.Timedelta(hours=23,minutes=59)
   if ts>idx[-1]+pd.Timedelta(hours=16):continue
   e=int(idx.searchsorted(ts,side='right')-1)
   if e>=start and e-last>=126:ev.append(dict(e=e,decision_at=ts));last=e
  return ev
 if k=='deep20':valid=d.gap.notna();flag=d.gap<=-.2
 elif k=='bottom':valid=d[['gap','dd','b200']].notna().all(axis=1);flag=(d.b200<43.3)&(d.dd<=-.15)&(d.gap<0)
 else:valid=d.b200.notna();flag=d.b200<43.3
 ev=[];last=-10**9
 for e in range(max(1,start),len(d)):
  if valid.iloc[e] and valid.iloc[e-1] and flag.iloc[e] and not flag.iloc[e-1] and e-last>=126:ev.append(dict(e=e,decision_at=idx[e]+pd.Timedelta(hours=16)));last=e
 return ev

def risk_stats(eq,dates):
 v=np.asarray(eq);draw=v/np.maximum.accumulate(v)-1;under=draw< -1e-12;max_wait=cur=0
 for b in under:cur=cur+1 if b else 0;max_wait=max(max_wait,cur)
 return dict(max_drawdown=float(draw.min()),longest_below_peak_quote_days=max_wait,below_peak_at_end=bool(under[-1]),worst_below_initial=float((v-1).min()))

def account(d,start,events,fee,case):
 idx=d.index;n=len(d);opens=d.open.to_numpy();closes=d.close.to_numpy();f=fee*1e-4
 # Civil schedules are known without reading subsequent prices. Missing exchange calendar is explicitly a proxy.
 weeks={}
 for sun in pd.date_range(idx[start].normalize()-pd.Timedelta(days=7),idx[-1],freq='W-SUN'):
  ts=sun+pd.Timedelta(hours=23,minutes=59);j=int(idx.searchsorted(ts,side='right'))
  if j<n:weeks.setdefault(j,[]).append(ts)
 incoming={};event_rows=[]
 for no,e in enumerate(events):
  e={**e,'event_id':f'{case}|event{no:04d}'};j=int(idx.searchsorted(e['decision_at'],side='right'));incoming.setdefault(j,[]).append(e)
 cash=1.;units=0.;active=None;paid=0.;realized=0.;daily=[];trades=[];actions=[];peak=1.;plan_no=0
 def close_plan(i,reason):
  nonlocal cash,units,paid,active,realized
  val=units*opens[i];cost=val*f;cash+=val-cost;paid+=cost;realized+=val-cost-active['invested'];actions.append(dict(case=case,date=str(idx[i].date()),action='sell',amount=val,fee=cost,units=units,price=opens[i],plan=active['id'],reason=reason,available_at=str(active['pending_exit'][1])))
  trades.append(dict(case=case,plan=active['id'],trigger=str(active['decision_at']),e=active['e'],exit_date=str(idx[i].date()),reason=reason,budget=active['budget'],invested=active['invested'],buy_count=active['buys'],terminal_wealth=cash,plan_return=cash/active['budget']-1,holding_quote_days=i-active['e'],status='closed'))
  units=0.;active=None
 for i in range(start,n):
  # These decisions arrived before this open, while previous holdings were still held.
  for ev in incoming.get(i,[]):
   row=dict(case=case,event_id=ev['event_id'],decision_at=str(ev['decision_at']),quote_date=str(idx[ev['e']].date()),first_possible_open=str(idx[i].date()))
   if active is not None:row['status']='rejected_capital_occupied'
   elif cash<=1e-14:row['status']='rejected_no_capital'
   else:
    plan_no+=1;active=dict(id=plan_no,e=ev['e'],decision_at=ev['decision_at'],budget=cash,invested=0.,buys=0,pending_buys=[],pending_exit=None);row['status']='accepted'
   event_rows.append(row)
  sold=False
  if active and i>active['e']+252:
   expired=i>=active['e']+756
   hit=active['invested']>0 and np.isfinite(closes[i-1]) and units*closes[i-1]/active['invested']-1>=.30
   if active['pending_exit'] is None and (expired or hit):
    active['pending_exit']=('deadline' if expired else 'target30',idx[i-1]+pd.Timedelta(hours=16))
   if active['pending_exit'] is not None and np.isfinite(opens[i]) and opens[i]>0:
    close_plan(i,active['pending_exit'][0]);sold=True
  if active and not sold and active['e']<i<=active['e']+252:
   active['pending_buys'].extend(ts for ts in weeks.get(i,[]) if ts>active['decision_at'])
   due=list(active['pending_buys']) if np.isfinite(opens[i]) and opens[i]>0 else []
   for ts in due:
    if active['buys']>=52:break
    active['pending_buys'].remove(ts)
    amt=min(active['budget']/52,cash);qty=amt*(1-f)/opens[i];units+=qty;cash-=amt;paid+=amt*f;active['invested']+=amt;active['buys']+=1
    actions.append(dict(case=case,date=str(idx[i].date()),action='buy',amount=amt,fee=amt*f,units=qty,price=opens[i],plan=active['id'],reason='weekly_schedule',available_at=str(ts)))
  value=units*closes[i];eq=cash+value;unrealized=value-(active['invested'] if active else 0.)
  assert cash>=-1e-12 and abs(eq-(1+realized+unrealized))<1e-10
  daily.append(dict(date=str(idx[i].date()),cash=cash,units=units,close=closes[i],holdings=value,equity=eq,external_inflow=1. if i==start else 0.,external_outflow=0.,cumulative_fees=paid,realized=realized,unrealized=unrealized,active_plan=active['id'] if active else 0))
 for ev in incoming.get(n,[]):event_rows.append(dict(case=case,event_id=ev['event_id'],decision_at=str(ev['decision_at']),quote_date=str(idx[ev['e']].date()),first_possible_open=None,status='unexecuted_no_next_quote'))
 if active:trades.append(dict(case=case,plan=active['id'],trigger=str(active['decision_at']),e=active['e'],exit_date=None,reason='open_at_cutoff',budget=active['budget'],invested=active['invested'],buy_count=active['buys'],terminal_wealth=daily[-1]['equity'],plan_return=daily[-1]['equity']/active['budget']-1,holding_quote_days=n-1-active['e'],status='open'))
 closed=[x for x in trades if x['status']=='closed'];rets=np.array([x['plan_return'] for x in closed]);eq=[x['equity'] for x in daily]
 summary=dict(case=case,fee_bps=fee,start=str(idx[start].date()),end=str(idx[-1].date()),events=len(events),accepted=sum(x['status']=='accepted' for x in event_rows),rejected_occupied=sum(x['status']=='rejected_capital_occupied' for x in event_rows),unexecuted_no_next_quote=sum(x['status']=='unexecuted_no_next_quote' for x in event_rows),closed_plans=len(closed),open_plans=sum(x['status']=='open' for x in trades),final_wealth=eq[-1],ending_cash=cash,ending_holdings=units*closes[-1],net_liquidation_estimate=cash+units*closes[-1]*(1-f),external_total=1.,total_fees=paid,mean_cash_fraction=float(np.mean([x['cash']/x['equity'] for x in daily])),mean_closed_return=float(rets.mean()) if len(rets) else None,median_closed_return=float(np.median(rets)) if len(rets) else None,min_closed_return=float(rets.min()) if len(rets) else None,closed_win_fraction=float((rets>0).mean()) if len(rets) else None,mean_closed_holding=float(np.mean([x['holding_quote_days'] for x in closed])) if closed else None,**risk_stats(eq,idx[start:]))
 return summary,daily,trades,event_rows,actions

def synthetic():
 idx=pd.bdate_range('2020-01-01',periods=900);d=pd.DataFrame({'open':1.,'close':1.},index=idx);ev=[dict(e=0,decision_at=idx[0]+pd.Timedelta(hours=16)),dict(e=126,decision_at=idx[126]+pd.Timedelta(hours=16))];s,days,tr,ers,ac=account(d,0,ev,0.,'synthetic')
 assert abs(s['final_wealth']-1)<1e-10 and s['rejected_occupied']==1 and s['accepted']==1
 flows=sum(r['external_inflow'] for r in days)-sum(r['external_outflow'] for r in days);assert abs(flows-1)<1e-10 and any(x['action']=='sell' for x in ac)
 return {'flat_zero_fee':{'passed':True,'final':s['final_wealth']},'internal_sale_not_external_flow':{'passed':True,'net_external':flows},'overlap_no_extra_budget':{'passed':True,'rejected':s['rejected_occupied'],'min_cash':min(r['cash'] for r in days)}}

def main():
 before={str(f):sha(f) for f in (P/'inputs').rglob('*') if f.is_file()};start=datetime.datetime.now(datetime.timezone.utc).isoformat()
 syn=synthetic();save('synthetic-checks.json',syn);ps=paired()
 frames={s:full_frame(s) for s in SYMS};events={(s,k):events_for(d,i,k) for s,(d,i) in frames.items() for k in KINDS}
 save('frozen-events.json',[{'symbol':s,'kind':k,'events':es} for (s,k),es in events.items()]);save('events-freeze.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sha256':sha(P/'frozen-events.json'),'before_account_results':True})
 summaries=[];alltr=[];aller=[];allactions=[];dailyout=P/'daily';dailyout.mkdir(exist_ok=True)
 for s,(d,i) in frames.items():
  for k in KINDS:
   for fee in [10.,20.]:
    case=f'{s}|{k}|fee{int(fee)}';smy,days,tr,ers,acts=account(d,i,events[s,k],fee,case);summaries.append(smy);alltr+=tr;aller+=ers;allactions+=acts;csv('daily/'+case.replace('|','_')+'.csv.gz',days)
 csv('account-plans.csv',alltr);csv('account-events.csv',aller);csv('account-actions.csv',allactions);save('account-summary.json',summaries)
 assert len(summaries)==64 and all(sha(Path(f))==v for f,v in before.items())
 save('run-manifest.json',{'started_at':start,'completed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'script_sha256':sha(Path(__file__)),'inputs':before,'all_inputs_unchanged':True,'outcomes':{'paired_rows':584,'account_paths':64,'plans':len(alltr),'actions':len(allactions)},'execution_clarifications_sha256':sha(P/'execution-clarifications.md'),'limitations':['quoted dates are not exchange calendars','historical proxy audit, not tradable performance','no independent future events','new portfolio paths have no matched baseline claim']})
 print(json.dumps({'paired':ps[:1],'account_paths':len(summaries),'plans':len(alltr),'synthetic':syn},ensure_ascii=False))
if __name__=='__main__':main()
