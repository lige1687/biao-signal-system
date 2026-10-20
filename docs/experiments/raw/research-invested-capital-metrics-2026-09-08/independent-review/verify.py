from pathlib import Path
from decimal import Decimal as D, getcontext
from collections import defaultdict
import csv,json,hashlib
getcontext().prec=40
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[4]
TECH=REPO/'docs/experiments/raw/research-broad-etf-technical-2026-09-08/execution/account-results'
RISK=REPO/'docs/experiments/raw/research-broad-etf-risk-sizing-2026-09-08/execution/account-results'
OUT=HERE

def loadj(p): return json.loads(p.read_text())
def rows(p): return list(csv.DictReader(p.open()))
def dec(x): return D(str(x))
def dump(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2,default=str)+'\n')
def write(p,x):
 fields=list(dict.fromkeys(k for r in x for k in r)) if x else []
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(x)
def dd(vals):
 peak=vals[0];worst=D(0)
 for v in vals:
  peak=max(peak,v);worst=min(worst,v/peak-1)
 return worst

def account(folder,method):
 daily=rows(folder/'daily.csv'); trades=rows(folder/'trades.csv'); trips=loadj(folder/'roundtrips.json'); events=loadj(folder/'events.json')
 bydate={r['date']:r for r in daily}; tbypos=defaultdict(list)
 for t in trades:tbypos[t['position_id']].append(t)
 accrued=defaultdict(lambda:D(0)); accrue_by_day=defaultdict(list)
 for e in events:
  if e['kind']=='dividend_receivable' and e.get('position_id'):
   accrue_by_day[e['date']].append((e['position_id'],dec(e['amount'])))
 position={p['position_id']:p for p in trips}; entries={p['entry_date']:p for p in trips}; exits={p['exit_date']:p for p in trips if p['closed']}
 curve=D(1); active=None; dailyout=[]; factors=[]; hold_days=0; current_points=[]; trade_dd=[]
 for r in daily:
  day=r['date']
  for pid,amt in accrue_by_day[day]: accrued[pid]+=amt
  if day in entries:
   assert active is None
   active=entries[day];current_points=[D(1)]
  if active:
   pid=active['position_id']; denom=dec(active['entry_notional'])+dec(active['buy_fee'])
   if active.get('exit_date')==day:
    ratio=(dec(active['exit_notional'])-dec(active['sell_fee'])+accrued[pid])/denom
    point=curve*ratio;current_points.append(ratio)
    factors.append({'account_id':folder.name,'method':method,'position_id':pid,'candidate_id':active['candidate_id'],'entry_date':active['entry_date'],'exit_date':day,'closed':True,'factor':ratio,'net_return':ratio-1,'reported_net_return':dec(active['net_return']),'max_trade_drawdown':dd(current_points)})
    trade_dd.append(dd(current_points));curve=point;active=None
   else:
    qty=dec(r['units_'+active['symbol']]); value=qty*dec(r['mark_'+active['symbol']])+accrued[pid]
    ratio=value/denom;point=curve*ratio;current_points.append(ratio);hold_days+=1
  else: point=curve
  dailyout.append({'account_id':folder.name,'date':day,'unit_curve':point,'holding':bool(active)})
 if active:
  pid=active['position_id'];ratio=dailyout[-1]['unit_curve']/curve
  factors.append({'account_id':folder.name,'method':method,'position_id':pid,'candidate_id':active['candidate_id'],'entry_date':active['entry_date'],'exit_date':None,'closed':False,'factor':ratio,'net_return':ratio-1,'reported_net_return':dec(active['net_return']),'max_trade_drawdown':dd(current_points)})
  trade_dd.append(dd(current_points));curve=dailyout[-1]['unit_curve']
 years=(D(len(daily)-1)/D('365.25'))
 full_ann=curve**(D(1)/years)-1
 hold_ann=curve**(D('365.25')/D(hold_days))-1 if hold_days else None
 prod=D(1)
 for f in factors:prod*=f['factor']
 assert abs(prod-curve)<D('1e-20')
 assert max(abs(f['net_return']-f['reported_net_return']) for f in factors)<D('1e-10')
 return dailyout,factors,{'account_id':folder.name,'method':method,'ending_unit_curve':curve,'full_period_annualized':full_ann,'holding_days':hold_days,'holding_day_annualized':hold_ann,'max_continuous_drawdown':dd([D(1)]+[dec(x['unit_curve']) for x in dailyout]),'worst_single_trade_drawdown':min(trade_dd),'trades':len(factors),'closed':sum(f['closed'] for f in factors),'open':sum(not f['closed'] for f in factors)}

def run():
 all_daily=[];all_factors=[];summary=[]
 for base,method,pat in [(TECH,'R1-full-cash','*-R1-fee*bp'),(RISK,'R1-risk1','*-R1-risk1-fee*bp')]:
  for folder in sorted(base.glob(pat)):
   d,f,s=account(folder,method);all_daily+=d;all_factors+=f;summary.append(s)
 assert len(summary)==8
 fmap={(x['account_id'].split('-')[0],x['account_id'].split('fee')[-1],x['method']):x for x in all_factors}
 # Pair by symbol, fee and candidate identity/order rather than position IDs.
 pairs=[]
 for symbol in ('sh510300','sz159915'):
  for fee in ('10bp','20bp'):
   a=[x for x in all_factors if x['account_id']==f'{symbol}-R1-fee{fee}']
   b=[x for x in all_factors if x['account_id']==f'{symbol}-R1-risk1-fee{fee}']
   assert len(a)==len(b)
   for x,y in zip(a,b):
    same=(x['candidate_id'],x['entry_date'],x['exit_date'])==(y['candidate_id'],y['entry_date'],y['exit_date'])
    diff=abs(x['net_return']-y['net_return'])
    pairs.append({'symbol':symbol,'fee':fee,'candidate_id':x['candidate_id'],'same_identity_dates':same,'unit_return_difference':diff})
 assert all(x['same_identity_dates'] for x in pairs)
 assert max(x['unit_return_difference'] for x in pairs)<D('1e-10')
 write(OUT/'unit-curve-daily.csv',all_daily);write(OUT/'trade-factors.csv',all_factors);write(OUT/'paired-trade-checks.csv',pairs);write(OUT/'independent-summary.csv',summary)
 result={'status':'passed','paths':len(summary),'daily_rows':len(all_daily),'trade_factors':len(all_factors),'paired_trades':len(pairs),'all_pair_identity_dates_match':all(x['same_identity_dates'] for x in pairs),'max_pair_unit_return_difference':max(x['unit_return_difference'] for x in pairs),'max_reported_roundtrip_return_difference':max(abs(x['net_return']-x['reported_net_return']) for x in all_factors)}
 dump(OUT/'results.json',result);print(json.dumps(result,default=str))
if __name__=='__main__':run()
