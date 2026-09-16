from pathlib import Path
from decimal import Decimal as D,getcontext
from collections import defaultdict
import csv,json
getcontext().prec=40
HERE=Path(__file__).resolve().parent;OUT=HERE.parent/'execution/attempt-01';MAIN=HERE.parent/'execution/invested-results.json';TOL=D('0.0000000001')
def rc(p):return list(csv.DictReader(p.open()))
def jl(p):return json.loads(p.read_text())
def dec(x):return D(str(x))
def dd(vals):
 peak=vals[0];worst=D(0)
 for v in vals:peak=max(peak,v);worst=min(worst,v/peak-1)
 return worst
def one(folder):
 daily=rc(folder/'daily.csv');trips=jl(folder/'roundtrips.json');events=jl(folder/'events.json');sym=folder.name.split('-')[0]
 ent={p['entry_date']:p for p in trips};active=None;base=D(1);curve=[];holds=0;position_dd=[];points=[];accrued=defaultdict(lambda:D(0));byday=defaultdict(list)
 for e in events:
  if e['kind']=='dividend_receivable' and e.get('position_id'):byday[e['date']].append(e)
 for r in daily:
  day=r['date']
  for e in byday[day]:accrued[e['position_id']]+=dec(e['amount'])
  if day in ent:active=ent[day];points=[D(1)]
  if active:
   den=dec(active['entry_notional'])+dec(active['buy_fee']);pid=active['position_id']
   if active['exit_date']==day:
    ratio=(dec(active['exit_notional'])-dec(active['sell_fee'])+accrued[pid])/den;v=base*ratio;points.append(ratio);position_dd.append(dd(points));base=v;active=None
   else:
    ratio=(dec(r['units_'+sym])*dec(r['mark_'+sym])+accrued[pid])/den;v=base*ratio;points.append(ratio);holds+=1
  else:v=base
  curve.append(v)
 if active:position_dd.append(dd(points));base=curve[-1]
 return {'account_id':folder.name,'unit_final':curve[-1],'maximum_decline':-dd([D(1)]+curve),'holding_days':holds,'worst_position_decline':-min(position_dd,default=D(0)),'positions':len(trips),'closed':sum(p['closed'] for p in trips),'open':sum(not p['closed'] for p in trips)}
def main():
 independent=[one(p) for p in sorted((OUT/'accounts').iterdir())];reported={x['account_id']:x for x in jl(MAIN)};diff=[]
 for x in independent:
  r=reported[x['account_id']]
  for k in ('unit_final','maximum_decline','holding_days','worst_position_decline','positions','closed','open'):
   d=abs(dec(r[k])-dec(x[k]));diff.append({'account_id':x['account_id'],'field':k,'reported':r[k],'independent':x[k],'difference':d});assert d<TOL,(x['account_id'],k,d)
 (HERE/'invested-curve-comparison.json').write_text(json.dumps({'status':'passed','accounts':32,'fields':len(diff),'maximum_difference':str(max(x['difference'] for x in diff)),'checks':diff},ensure_ascii=False,indent=2,default=str)+'\n')
 print(json.dumps({'status':'passed','accounts':32,'fields':len(diff),'maximum_difference':str(max(x['difference'] for x in diff))}))
if __name__=='__main__':main()
