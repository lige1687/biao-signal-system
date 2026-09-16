from pathlib import Path
from decimal import Decimal as D, ROUND_FLOOR, getcontext
from datetime import date,timedelta
from collections import defaultdict
import csv,json,hashlib,ast
getcontext().prec=40
HERE=Path(__file__).resolve().parent; ROOT=HERE.parent; IN=ROOT/'execution/inputs'; TOL=D('.00001')
def jl(p):return json.loads(p.read_text())
def rc(p):return list(csv.DictReader(p.open()))
def dec(x):return D(str(x))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,default=str)+'\n')
def wc(p,x):
 fields=list(dict.fromkeys(k for r in x for k in r)) if x else ['account_id']
 with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(x)
def lot(x):return (x/D(100)).to_integral_value(rounding=ROUND_FLOOR)*100
def simulate(symbol,fee,bars,actions,settings,start,end,aid):
 bm={r['date']:r for r in bars}; dates=sorted(bm); blocked=set(settings['blocked_dates'][symbol]); no_mark={r['date'] for r in jl(IN/'dated-restrictions.json') if r['symbol']==symbol and not r['close_mark_allowed']}
 run=[d for d in dates if start<=d<=end]; first=run[0]; prior=max(d for d in dates if d<start); ref=dec(bm[prior]['close']); mark=ref;markdate=prior
 cash=D(100000);recv=D(0);units=D(0);fees=D(0);divs=D(0);rights={};dues={};pending=None
 trades=[];reject=[];daily=[];events=[];day=date.fromisoformat(start); finish=date.fromisoformat(end)
 def block(ds,bar,reference):
  if ds in blocked:return 'known_open_unavailable'
  if bar is None:return 'missing_quote'
  limit=dec(settings['limits'][symbol])
  for eff,v in settings['limit_changes'].get(symbol,[]):
   if eff<=ds:limit=dec(v)
  return 'at_open_limit_conservative' if abs(dec(bar['open'])-reference)>=reference*limit-D('.00051') else None
 while day<=finish:
  ds=str(day);bar=bm.get(ds)
  if ds==first:pending={'signal_date':start,'reason':'initial_hold_allocation','sources':[]}
  # Effective actions change receivables/units and the prior reference before the open.
  effref=ref
  for a in sorted((x for x in actions if x['symbol']==symbol and x['effective_date']==ds),key=lambda x:x['event_id']):
   if a['type']=='cash_dividend':
    amt=rights.get(a['event_id'],D(0))*dec(a['cash']);dues[a['event_id']]=amt;recv+=amt;effref-=dec(a['cash']);events.append((ds,'receivable',a['event_id'],amt))
   else:
    units*=dec(a['ratio']);effref/=dec(a['ratio']);events.append((ds,'split',a['event_id'],units))
  paid=[]
  for a in (x for x in actions if x['symbol']==symbol and x['type']=='cash_dividend' and x.get('pay_date')==ds):
   amt=dues.pop(a['event_id'],D(0));recv-=amt;cash+=amt;divs+=amt;events.append((ds,'paid',a['event_id'],amt))
   if amt>0:paid.append({'event_id':a['event_id'],'pay_date':ds,'amount':str(amt)})
  if paid:
   if pending is None:pending={'signal_date':ds,'reason':'dividend_reinvestment','sources':paid}
   else:pending['sources']+=paid
  if pending is not None:
   reason=block(ds,bar,effref)
   if reason:reject.append({'account_id':aid,'date':ds,'signal_date':pending['signal_date'],'reason':reason})
   else:
    px=dec(bar['open']);q=lot(cash/(px*(1+fee)))
    if q<=0:
     reject.append({'account_id':aid,'date':ds,'signal_date':pending['signal_date'],'reason':'reinvestment_below_one_lot','payment_sources':pending['sources']});pending=None
    else:
     notional=q*px;cost=notional*fee;cash-=notional+cost;units+=q;fees+=cost
     trades.append({'account_id':aid,'date':ds,'signal_date':pending['signal_date'],'side':'buy','shares':q,'price':px,'notional':notional,'fee':cost,'reason':pending['reason'],'payment_sources':pending['sources'],'cash_after':cash,'units_after':units});pending=None
  if bar is not None and ds not in no_mark:mark=dec(bar['close']);markdate=ds;ref=mark
  else:ref=effref
  for a in (x for x in actions if x['symbol']==symbol and x['type']=='cash_dividend' and x.get('record_date')==ds):rights[a['event_id']]=units;events.append((ds,'record',a['event_id'],units))
  eq=cash+recv+units*mark
  daily.append({'account_id':aid,'date':ds,'cash':cash,'receivable':recv,'units':units,'mark':mark,'market_value':units*mark,'equity':eq,'invested_weight':units*mark/eq if eq else 0,'fees':fees,'dividends_received':divs,'mark_age_days':(day-date.fromisoformat(markdate)).days})
  day+=timedelta(days=1)
 if pending:reject.append({'account_id':aid,'date':end,'signal_date':pending['signal_date'],'reason':'pending_at_period_end'})
 return daily,trades,reject,events

def locate_results():
 for p in (ROOT/'execution/attempt-03',ROOT/'execution/account-results',ROOT/'execution/attempt-01'):
  if p.exists() and (p/'summary.json').exists():return p
 raise FileNotFoundError('execution results not ready')
def compare_rows(actual,expected,fields,context,diffs):
 assert len(actual)==len(expected),(context,len(actual),len(expected))
 for i,(a,e) in enumerate(zip(actual,expected)):
  for k in fields:
   if isinstance(e[k],D):
    d=abs(dec(a[k])-e[k]);
    if d>TOL:diffs.append({'context':context,'row':i,'field':k,'actual':a[k],'expected':e[k],'difference':d})
   elif e[k] is None and a[k]=='':continue
   elif str(a[k])!=str(e[k]):diffs.append({'context':context,'row':i,'field':k,'actual':a[k],'expected':e[k],'difference':'text'})
def periods(daily,trades,n):
 groups=defaultdict(list)
 for r in daily:groups[r['date'][:n]].append(r)
 out=[];prior=D(100000);prior_div=D(0)
 for key,rs in sorted(groups.items()):
  high=prior;worst=D(0)
  for r in rs:high=max(high,r['equity']);worst=min(worst,r['equity']/high-1)
  ts=[t for t in trades if t['date'].startswith(key)];end=rs[-1]
  out.append({'period':key,'start_equity':prior,'end_equity':end['equity'],'change':end['equity']-prior,'return':end['equity']/prior-1,'max_drawdown':worst,'buys':D(len(ts)),'sells':D(0),'fees':sum((t['fee'] for t in ts),D(0)),'dividends_received':end['dividends_received']-prior_div,'cash_only_days':D(sum(r['units']==0 for r in rs))})
  prior=end['equity'];prior_div=end['dividends_received']
 return out
def intervals(daily):
 rs=[{'date':'2014-12-31','equity':D(100000)}]+daily;peak=rs[0]['equity'];pi=0;active=None;out=[]
 for i,r in enumerate(rs):
  if r['equity']>=peak:
   if active:
    active['recovery_date']=r['date'];active['recovery_days']=D((date.fromisoformat(r['date'])-date.fromisoformat(active['start_date'])).days);out.append(active);active=None
   peak=r['equity'];pi=i
  else:
   x=r['equity']/peak-1
   if active is None:active={'start_date':rs[pi]['date'],'peak_equity':peak,'valley_date':r['date'],'valley_equity':r['equity'],'max_drawdown':x,'recovery_date':None,'recovery_days':None}
   elif x<active['max_drawdown']:active.update(valley_date=r['date'],valley_equity=r['equity'],max_drawdown=x)
 if active:out.append(active)
 return out
def run():
 out=locate_results();cfg=jl(ROOT/'execution/config.json');settings=jl(IN/'execution-parameters-source.json');actions=jl(IN/'actions.json');diffs=[];summ=[];all_daily=[];buychecks=[]
 for symbol in cfg['symbols']:
  bars=rc(IN/'bars'/f'{symbol}-nominal.csv')
  for fs in cfg['fees_per_side']:
   fee=dec(fs);aid=f'{symbol}-hold_dividend_reinvest-fee{fs}';folder=out/aid
   ed,et,er,ev=simulate(symbol,fee,bars,actions,settings,*cfg['research_window'],aid);ad=rc(folder/'daily.csv');at=rc(folder/'trades.csv');ar=jl(folder/'rejected.json')
   compare_rows(ad,ed,list(ed[0]),aid+' daily',diffs)
   # Core trade fields and exact payment provenance; extra presentation fields may differ.
   tf=['account_id','date','signal_date','side','shares','price','notional','fee','reason','cash_after','units_after']
   compare_rows(at,et,tf,aid+' trades',diffs)
   assert len(at)==len(et)
   for a,e in zip(at,et):
    actual_sources=ast.literal_eval(a['payment_sources']) if a.get('payment_sources') else []
    assert actual_sources==e['payment_sources'];buychecks.append({'account_id':aid,'date':e['date'],'reason':e['reason'],'shares':e['shares'],'fee':e['fee'],'payment_sources':json.dumps(e['payment_sources'],ensure_ascii=False)})
   # Every independently expected wait/failure reason must occur in order.
   assert [(x['date'],x['signal_date'],x['reason']) for x in ar]==[(x['date'],x['signal_date'],x['reason']) for x in er]
   for filename,expected in [('monthly.csv',periods(ed,et,7)),('yearly.csv',periods(ed,et,4)),('drawdown_recovery.csv',intervals(ed))]:
    actual=rc(folder/filename);compare_rows(actual,expected,list(expected[0]) if expected else [],aid+' '+filename,diffs)
   eq=ed[-1]['equity']; peak=D(100000);mdd=D(0)
   for x in ed:peak=max(peak,x['equity']);mdd=min(mdd,x['equity']/peak-1)
   rs=jl(folder/'summary.json');checks={'final_equity':eq,'net_gain':eq-D(100000),'final_cash':ed[-1]['cash'],'final_receivable':ed[-1]['receivable'],'final_units':ed[-1]['units'],'terminal_market_value':ed[-1]['market_value'],'fees':ed[-1]['fees'],'dividends_received':ed[-1]['dividends_received'],'buys':D(len(et)),'sells':D(0),'max_drawdown':mdd}
   md=D(0)
   for k,v in checks.items():md=max(md,abs(dec(rs[k])-v))
   if md>TOL:diffs.append({'context':aid+' summary','field':'max','difference':md})
   all_daily+=ed;summ.append({'account_id':aid,'days':len(ed),'buys':len(et),'reinvestment_buys':sum(x['reason']=='dividend_reinvestment' for x in et),'events':len(ev),'final_equity':eq,'max_drawdown':mdd,'max_summary_difference':md})
 wc(HERE/'daily-independent.csv',all_daily);wc(HERE/'buy-checks.csv',buychecks);wc(HERE/'field-differences.csv',diffs);save(HERE/'independent-summary.json',summ)
 result={'status':'passed' if not diffs else 'failed','accounts':len(summ),'daily_rows':len(all_daily),'buys':sum(x['buys'] for x in summ),'reinvestment_buys':sum(x['reinvestment_buys'] for x in summ),'field_differences':len(diffs)};save(HERE/'numeric-results.json',result);print(json.dumps(result))
 if diffs:raise SystemExit(1)
if __name__=='__main__':run()
