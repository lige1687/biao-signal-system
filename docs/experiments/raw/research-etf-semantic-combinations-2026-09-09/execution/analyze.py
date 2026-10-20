from pathlib import Path
from datetime import date
import csv,json,statistics
H=Path(__file__).resolve().parent;A=H/'attempt-01';END='2026-06-30'
def read(p):return json.loads(Path(p).read_text())
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def invested(folder,meta):
 d=list(csv.DictReader((folder/'daily.csv').open()));ps=read(folder/'roundtrips.json');ev=read(folder/'events.json');entries={p['entry_date']:p for p in ps};div={};ac={p['position_id']:0. for p in ps}
 for e in ev:
  if e['kind']=='dividend_receivable' and e.get('position_id'):div.setdefault(e['date'],[]).append(e)
 base=nav=peak=1.;draw=0.;active=None;stats=[];ys={};ye={};last=1.;holding=0
 for row in d:
  day=row['date'];ys.setdefault(day[:4],last)
  for e in div.get(day,[]):ac[e['position_id']]+=float(e['amount'])
  if day in entries:active=entries[day];active['_peak']=1.;active['_draw']=0.;active['_days']=0
  if active:
   p=active;cap=p['entry_notional']+p['buy_fee'];closed=p['closed'] and day==p['exit_date'];val=(p['exit_notional']-p['sell_fee'] if closed else float(row['assets']))+ac[p['position_id']];factor=val/cap;nav=base*factor;p['_peak']=max(p['_peak'],factor);p['_draw']=max(p['_draw'],1-factor/p['_peak'])
   if not closed:p['_days']+=1;holding+=1
   if closed:base=nav;active=None
  else:nav=base
  peak=max(peak,nav);draw=max(draw,1-nav/peak);ye[day[:4]]=nav;last=nav
 span=(date.fromisoformat(d[-1]['date'])-date.fromisoformat(d[0]['date'])).days;closed=[p for p in ps if p['closed']];r=[p['net_return'] for p in closed]
 profile={**meta,'unit_final':nav,'calendar_annualized':nav**(365.25/span)-1,'maximum_decline':draw,'positions':len(ps),'closed':len(closed),'open':len(ps)-len(closed),'closed_mean':statistics.mean(r) if r else None,'closed_median':statistics.median(r) if r else None,'closed_win_fraction':sum(x>0 for x in r)/len(r) if r else None,'holding_days':holding,'worst_position_decline':max((p['_draw'] for p in ps),default=None)}
 annual=[{**meta,'year':y,'unit_return':ye[y]/ys[y]-1} for y in ys]
 return profile,annual
def main():
 profiles=[];annual=[];periods=[];accounts=read(A/'summary.json')
 for m in accounts:
  aid=m['account_id'];folder=A/'accounts'/aid;p,a=invested(folder,{k:m[k] for k in ('account_id','symbol','group','exit','fee')});profiles.append(p);annual+=a
  rows=list(csv.DictReader((folder/'daily.csv').open()))
  for label,lo,hi in [('2015-2019','2015-01-01','2019-12-31'),('2020-2026H1','2020-01-01',END)]:
   g=[r for r in rows if lo<=r['date']<=hi];before=100000. if lo.startswith('2015') else float([r for r in rows if r['date']<lo][-1]['equity']);periods.append({'account_id':aid,'period':label,'return':float(g[-1]['equity'])/before-1})
 save(H/'invested-results.json',profiles);save(H/'invested-annual.json',annual);save(H/'fixed-periods.json',periods)
if __name__=='__main__':main()
