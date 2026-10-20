"""Read complete account paths; no strategy, parameters, source prices or account mutations."""
from pathlib import Path
import json,csv,hashlib,calendar,datetime
P=Path(__file__).resolve().parent; B=P.parent
OLD=B.parent/'research-broad-etf-cash-2026-09-08/first12/account-results'
NEW=B/'execution/account-results'
def read(p):return json.loads(p.read_text())
def rows(p):
 with p.open() as f:return list(csv.DictReader(f))
def save(n,v):(P/n).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def metrics(ds,initial):
 peak=initial;dd=0
 for d in ds:
  v=float(d['equity']);peak=max(peak,v);dd=min(dd,v/peak-1)
 return {'return':float(ds[-1]['equity'])/initial-1,'max_drawdown':dd,'ending_equity':float(ds[-1]['equity'])}
def main():
 assert not (P/'results.json').exists(),'Preserve earlier analysis'
 summaries=read(NEW/'summary.json');assert len(summaries)==8
 sources=[Path(__file__),B/'protocol.md',NEW/'summary.json'];profiles=[];annual=[];rolling=[];segments=[];checks=[]
 for s in summaries:
  sid=s['account_id'];nf=NEW/sid
  # Financial primary baseline is original three-tier for both candidates.
  fee=format(s['fee_per_side'],'.3f');of=OLD/f"{s['symbol']}-breadth_three_tier-fee{fee}"
  hf=OLD/f"{s['symbol']}-hold-fee{fee}"
  ds=rows(nf/'daily.csv');od=rows(of/'daily.csv');hs=read(hf/'summary.json');os=read(of/'summary.json')
  assert [x['date'] for x in ds]==[x['date'] for x in od]
  ts=rows(nf/'trades.csv'); fees=sum(float(x['fee']) for x in ts if x.get('fee'))
  mm=metrics(ds,100000);assert abs(mm['max_drawdown']-s['max_drawdown'])<1e-10
  assert abs(float(ds[-1]['equity'])-s['final_equity'])<1e-6 and abs(fees-s['fees'])<1e-6
  mean_new=sum(float(x['invested_weight']) for x in ds)/len(ds);mean_old=sum(float(x['invested_weight']) for x in od)/len(od)
  profiles.append({**s,'baseline_equity':os['final_equity'],'baseline_max_drawdown':os['max_drawdown'],'extra_wealth':s['final_equity']-os['final_equity'],'drawdown_difference_pp':100*(s['max_drawdown']-os['max_drawdown']),'extra_fees':s['fees']-os['fees'],'mean_invested_fraction':mean_new,'baseline_mean_invested_fraction':mean_old,'hold_equity':hs['final_equity'],'hold_max_drawdown':hs['max_drawdown'],'historical_joint_improvement':s['final_equity']>=os['final_equity'] and s['max_drawdown']>=os['max_drawdown']})
  yr=rows(nf/'yearly.csv');oy={x['period']:x for x in rows(of/'yearly.csv')};hy={x['period']:x for x in rows(hf/'yearly.csv')}
  assert abs(sum(float(x['change']) for x in yr)-s['net_gain'])<1e-6
  for y in yr:
   yy=y['period'];annual.append({'account_id':sid,'year':yy,'new_return':float(y['return']),'baseline_return':float(oy[yy]['return']),'hold_return':float(hy[yy]['return']),'new_minus_baseline_pp':100*(float(y['return'])-float(oy[yy]['return']))})
  month_ends=[]
  for i,d in enumerate(ds):
   dt=datetime.date.fromisoformat(d['date'])
   if dt.day==calendar.monthrange(dt.year,dt.month)[1]:month_ends.append(i)
  # 36 complete calendar months; include prior month-end start wealth, Jan2015 starts 100000.
  for j in range(35,len(month_ends)):
   a=month_ends[j-36]+1 if j>=36 else 0;b=month_ends[j]+1
   n0=float(ds[a-1]['equity']) if a else 100000;o0=float(od[a-1]['equity']) if a else 100000
   n=metrics(ds[a:b],n0);o=metrics(od[a:b],o0)
   rolling.append({'account_id':sid,'start':ds[a]['date'],'end':ds[b-1]['date'],'new_return':n['return'],'baseline_return':o['return'],'difference_pp':100*(n['return']-o['return']),'new_max_drawdown':n['max_drawdown'],'baseline_max_drawdown':o['max_drawdown']})
  for lo,hi in [('2015-01-01','2019-12-31'),('2020-01-01','2026-06-30')]:
   ids=[i for i,d in enumerate(ds) if lo<=d['date']<=hi];a=ids[0];b=ids[-1]+1
   n=metrics(ds[a:b],float(ds[a-1]['equity']) if a else 100000);o=metrics(od[a:b],float(od[a-1]['equity']) if a else 100000)
   segments.append({'account_id':sid,'start':lo,'end':hi,'new':n,'baseline':o})
  checks.append({'account_id':sid,'daily_rows':len(ds),'trade_rows':len(ts),'fees_endpoint_drawdown_annual_checked':True})
  sources += [nf/n for n in ['daily.csv','trades.csv','yearly.csv','summary.json']]+[of/n for n in ['daily.csv','yearly.csv','summary.json']]+[hf/n for n in ['yearly.csv','summary.json']]
 rolling_summary=[]
 for s in summaries:
  rr=[r for r in rolling if r['account_id']==s['account_id']]
  rolling_summary.append({'account_id':s['account_id'],'windows':len(rr),'windows_ahead':sum(r['difference_pp']>0 for r in rr),'windows_behind':sum(r['difference_pp']<0 for r in rr),'worst':min(rr,key=lambda r:r['difference_pp']),'best':max(rr,key=lambda r:r['difference_pp']),'overlapping_not_independent':True})
 save('results.json',{'profiles':profiles,'rolling_summary':rolling_summary,'segments':segments,'checks':checks,'joint_improvement_all_four_by_method':{m:all(x['historical_joint_improvement'] for x in profiles if x['method']==m) for m in {x['method'] for x in profiles}},'limitations':['Known historical paths; not future validation.','Rolling windows overlap and reuse full-account paths; not independent restarted accounts.','Higher participation is not proof of signal predictive improvement.']})
 save('annual.json',annual);save('rolling-36-months.json',rolling)
 save('input-lock.json',{'files':{str(p):digest(p) for p in sorted(set(sources))}})
 print(json.dumps(profiles,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
