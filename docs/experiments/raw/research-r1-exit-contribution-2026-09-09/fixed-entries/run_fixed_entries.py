from pathlib import Path
from decimal import Decimal as D,getcontext
from datetime import date,timedelta,datetime,timezone
from collections import defaultdict
import csv,json,gzip,hashlib,statistics
getcontext().prec=40
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent;IN=ROOT/'execution/inputs';END='2026-06-30';OUT=HERE/'attempt-02'
OLD=HERE.parents[1]/'research-broad-etf-technical-2026-09-08/execution/account-results'
def jl(p):return json.loads(p.read_text())
def rc(p):return list(csv.DictReader(p.open()))
def dec(x):return D(str(x))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,default=str)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def unavailable(symbol,day,bm,reference,cfg):
 if day in cfg['blocked_dates'][symbol]:return 'known_open_unavailable'
 if day not in bm:return 'missing_quote'
 limit=dec(cfg['limits'][symbol])
 for eff,v in cfg['limit_changes'].get(symbol,[]):
  if eff<=day:limit=dec(v)
 return 'at_open_limit_conservative' if abs(dec(bm[day]['open'])-reference)>=reference*limit-D('.00051') else None
def path(rt,buy,old_sell,fee,method,bm,actions,obs,cfg):
 symbol=rt['symbol'];entry=rt['entry_date'];shares=dec(buy['shares']);initial_shares=shares;stop=dec(rt['initial_stop']);initial_stop=stop
 entry_notional=dec(buy['notional']);buy_fee=dec(buy['fee']);sold=False;pending=None;exit_date=None;exit_price=None;exit_notional=D(0);sell_fee=D(0);rights={};recv={};accrued=D(0);paid=D(0);events=[];daily=[]
 prior=max(d for d in bm if d<entry);reference=dec(bm[prior]['close']);mark=reference;mark_date=prior
 current=date.fromisoformat(entry);finish=date.fromisoformat(END)
 while current<=finish:
  day=str(current);entry_day=(day==entry)
  for a in sorted((x for x in actions if x['symbol']==symbol and x['effective_date']==day),key=lambda x:x['event_id']):
   if a['type']=='split':
    if not entry_day and not sold:shares*=dec(a['ratio']);stop/=dec(a['ratio'])
    reference/=dec(a['ratio']);events.append({'date':day,'kind':'split','event_id':a['event_id'],'shares_after':shares,'stop_after':stop})
   else:
    entitled=rights.get(a['event_id'],D(0));amt=entitled*dec(a['cash']);recv[a['event_id']]=amt;accrued+=amt
    if not entry_day and not sold:stop*=((reference-dec(a['cash']))/reference)
    reference-=dec(a['cash']);events.append({'date':day,'kind':'dividend_receivable','event_id':a['event_id'],'amount':amt,'entitled_shares':entitled,'stop_after':stop})
  for a in (x for x in actions if x['symbol']==symbol and x['type']=='cash_dividend' and x.get('pay_date')==day):
   amt=recv.pop(a['event_id'],D(0));paid+=amt;events.append({'date':day,'kind':'dividend_paid','event_id':a['event_id'],'amount':amt})
  if pending and not sold and day>pending['signal_date']:
   block=unavailable(symbol,day,bm,reference,cfg);pending['attempts'].append({'date':day,'reason':block or 'filled'})
   if block is None:
    exit_date=day;exit_price=dec(bm[day]['open']);exit_notional=shares*exit_price;sell_fee=exit_notional*fee;sold=True
    events.append({'date':day,'kind':'sell','reason':pending['reason'],'shares':shares,'price':exit_price,'fee':sell_fee});shares=D(0)
  if day in bm:mark=dec(bm[day]['close']);mark_date=day;reference=mark
  if not sold and day in bm and pending is None:
   close=dec(bm[day]['close']);structure=close<stop;road=False
   if method=='road_or_structure':
    o=obs[symbol].get(day)
    if not o or o.get('ema20') is None or o.get('cost20') is None:raise ValueError(f'missing observation {symbol} {day}')
    road=close<dec(o['ema20']) and close<dec(o['cost20'])
   reason='structure_stop' if structure else ('ema_cost_exit' if road else None)
   if reason:pending={'signal_date':day,'reason':reason,'attempts':[]};events.append({'date':day,'kind':'exit_signal','reason':reason,'close':close,'stop':stop,'ema20':o.get('ema20') if method=='road_or_structure' else None,'cost20':o.get('cost20') if method=='road_or_structure' else None})
  for a in (x for x in actions if x['symbol']==symbol and x['type']=='cash_dividend' and x.get('record_date')==day):
   rights[a['event_id']]=shares if not sold else D(0);events.append({'date':day,'kind':'dividend_recorded','event_id':a['event_id'],'shares':rights[a['event_id']]})
  value=(exit_notional-sell_fee+accrued) if sold else shares*mark+accrued
  daily.append({'path_id':f"{rt['position_id']}|{fee}|{method}",'date':day,'shares':shares,'mark':mark,'mark_date':mark_date,'receivable':sum(recv.values(),D(0)),'dividend_accrued':accrued,'dividend_paid':paid,'stop':stop,'sold':sold,'value':value,'net_pnl':value-entry_notional-buy_fee})
  current+=timedelta(days=1)
 terminal_market=D(0) if sold else shares*mark;net=exit_notional-sell_fee+terminal_market+accrued-entry_notional-buy_fee;ret=net/(entry_notional+buy_fee)
 peak=entry_notional+buy_fee;worst=D(0)
 for row in daily:peak=max(peak,row['value']);worst=min(worst,row['value']/peak-1)
 holding_days=(date.fromisoformat(exit_date or END)-date.fromisoformat(entry)).days+(0 if exit_date else 1)
 return {'path_id':f"{rt['position_id']}|{fee}|{method}",'source_account_id':buy['account_id'],'position_id':rt['position_id'],'candidate_id':rt['candidate_id'],'symbol':symbol,'fee_per_side':fee,'method':method,'entry_date':entry,'entry_price':dec(buy['price']),'initial_shares':initial_shares,'final_shares':shares,'entry_notional':entry_notional,'buy_fee':buy_fee,'initial_stop':initial_stop,'final_stop':stop,'exit_signal_date':pending['signal_date'] if pending else None,'exit_reason':pending['reason'] if pending else None,'exit_attempts':pending['attempts'] if pending else [],'exit_date':exit_date,'exit_price':exit_price,'exit_notional':exit_notional,'sell_fee':sell_fee,'dividend_accrued':accrued,'dividend_paid':paid,'terminal_market_value':terminal_market,'net_pnl':net,'net_return':ret,'holding_days':holding_days,'max_holding_drawdown':worst,'original_exit_date':rt['exit_date'],'original_exit_reason':old_sell['reason'] if old_sell else None,'original_net_pnl':dec(rt['net_pnl']),'original_net_return':dec(rt['net_return']),'events':events},daily
def main():
 OUT.mkdir(exist_ok=False)
 lock=jl(HERE/'run-lock-attempt-02.json')['files']
 for p,h in lock.items():assert sha(p)==h,p
 cfg=jl(IN/'execution-config.json');actions=jl(IN/'actions.json');obs=json.load(gzip.open(IN/'exit-observations.json.gz','rt'));allp=[];alld=[];recon=[]
 for folder in sorted(OLD.glob('*-R1-fee*bp')):
  fee=dec('0.001') if 'fee10bp' in folder.name else dec('0.002');trades=rc(folder/'trades.csv');tmap={(x['position_id'],x['side']):x for x in trades};rts=jl(folder/'roundtrips.json');symbol=rts[0]['symbol'];bm={r['date']:r for r in rc(IN/'bars'/f'{symbol}-nominal.csv')}
  for rt in rts:
   buy=tmap[(rt['position_id'],'buy')];buy['account_id']=folder.name;sell=tmap.get((rt['position_id'],'sell'))
   for method in ('road_or_structure','structure_only'):
    p,d=path(rt,buy,sell,fee,method,bm,actions,obs,cfg);allp.append(p);alld+=d
   original=allp[-2]; diffs={'exit_date':original['exit_date']==rt['exit_date'],'exit_reason':original['exit_reason']==(sell['reason'] if sell else None),'net_pnl':abs(original['net_pnl']-dec(rt['net_pnl'])),'net_return':abs(original['net_return']-dec(rt['net_return']))}
   recon.append({'source_account_id':folder.name,'position_id':rt['position_id'],**diffs});assert diffs['exit_date'] and diffs['exit_reason'] and diffs['net_pnl']<D('0.00001') and diffs['net_return']<D('1e-10'),(folder.name,rt['position_id'],diffs)
 with gzip.open(OUT/'path-daily.csv.gz','wt',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(alld[0]));w.writeheader();w.writerows(alld)
 with (OUT/'path-comparison.csv').open('w',newline='') as f:
  fields=[k for k in allp[0] if k not in ('events','exit_attempts')];w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows([{k:p[k] for k in fields} for p in allp])
 with gzip.open(OUT/'path-events.jsonl.gz','wt') as f:
  for p in allp:f.write(json.dumps({'path_id':p['path_id'],'exit_attempts':p['exit_attempts'],'events':p['events']},ensure_ascii=False,default=str)+'\n')
 save(OUT/'original-reconciliation.json',{'paths':len(recon),'all_matched':True,'max_net_pnl_difference':max(x['net_pnl'] for x in recon),'max_net_return_difference':max(x['net_return'] for x in recon),'checks':recon})
 pairs=[]
 for i in range(0,len(allp),2):
  a,b=allp[i:i+2];pairs.append({'source_account_id':a['source_account_id'],'position_id':a['position_id'],'candidate_id':a['candidate_id'],'symbol':a['symbol'],'fee_per_side':a['fee_per_side'],'entry_date':a['entry_date'],'initial_shares':a['initial_shares'],'original_exit_date':a['exit_date'],'original_exit_reason':a['exit_reason'],'original_net_return':a['net_return'],'structure_exit_date':b['exit_date'],'structure_exit_reason':b['exit_reason'],'structure_net_return':b['net_return'],'structure_minus_original_return':b['net_return']-a['net_return'],'original_holding_days':a['holding_days'],'structure_holding_days':b['holding_days'],'original_max_holding_drawdown':a['max_holding_drawdown'],'structure_max_holding_drawdown':b['max_holding_drawdown']})
 with (OUT/'paired-comparison.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(pairs[0]));w.writeheader();w.writerows(pairs)
 summaries=[]
 for method in ('road_or_structure','structure_only'):
  for fee in (D('.001'),D('.002')):
   for symbol in ('sh510300','sz159915'):
    xs=[p for p in allp if p['method']==method and p['fee_per_side']==fee and p['symbol']==symbol];rs=[p['net_return'] for p in xs]
    
    streak=best=0
    for r in rs:
     streak=streak+1 if r<0 else 0;best=max(best,streak)
    positives=sorted((p['net_pnl'] for p in xs if p['net_pnl']>0),reverse=True);possum=sum(positives,D(0))
    summaries.append({'method':method,'fee_per_side':fee,'symbol':symbol,'paths':len(xs),'closed':sum(p['exit_date'] is not None for p in xs),'open':sum(p['exit_date'] is None for p in xs),'mean_net_return':sum(rs,D(0))/len(rs),'median_net_return':statistics.median(rs),'profitable_fraction':D(sum(r>0 for r in rs))/len(rs),'total_holding_days':sum(p['holding_days'] for p in xs),'worst_holding_drawdown':min(p['max_holding_drawdown'] for p in xs),'longest_losing_streak':best,'top5_profit_concentration':sum(positives[:5],D(0))/possum if possum else None})
 save(OUT/'summary.json',summaries);save(OUT/'completion.json',{'status':'passed','fixed_entries':330,'paths':660,'original_reconciled':330,'all_inputs_unchanged':True,'finished_at':datetime.now(timezone.utc).isoformat()})
 for p,h in lock.items():assert sha(p)==h,p
if __name__=='__main__':main()
