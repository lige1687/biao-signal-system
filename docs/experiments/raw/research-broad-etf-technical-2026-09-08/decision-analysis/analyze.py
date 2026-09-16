"""Read all frozen accounts and expose actual participation, not risk-equal ranking."""
from pathlib import Path
import csv,json,hashlib,collections
P=Path(__file__).resolve().parent;OUT=P.parent/'execution/account-results'
def read(p):return json.loads(p.read_text())
def rows(p):
 with p.open() as f:return list(csv.DictReader(f))
def save(n,v):(P/n).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def main():
 assert not (P/'results.json').exists(),'Preserve prior analysis'
 ss=read(OUT/'summary.json');assert len(ss)==48
 profiles=[];annual=[];checks=[];inputs=[Path(__file__),OUT/'summary.json'];groups=collections.defaultdict(list)
 for s in ss:
  folder=OUT/s['account_id'];ds=rows(folder/'daily.csv');ts=rows(folder/'trades.csv');os=read(folder/'orders.json');rt=read(folder/'roundtrips.json');sym=s['symbol']
  peak=100000;dd=0;fees=0;av=0;cashdays=0
  for d in ds:
   eq=float(d['equity']);assert abs(eq-float(d['cash'])-float(d['assets'])-float(d['receivable']))<1e-6
   assert float(d['total_funding'])==100000 and float(d['deposit'])==0
   peak=max(peak,eq);dd=min(dd,eq/peak-1);av+=float(d['assets'])/eq;cashdays+=float(d['assets'])==0
  fees=sum(float(t['fee']) for t in ts);eq=float(ds[-1]['equity']);av/=len(ds)
  assert abs(eq-s['last_equity'])<1e-6 and abs(fees-s['fees'])<1e-6 and abs(-dd-s['max_drawdown'])<1e-10 and abs(av-s['mean_exposure'])<1e-10
  assert abs(sum(t['net_pnl'] for t in rt)-s['net_gain'])<1e-6
  buys=[o for o in os if o['side']=='buy'];assert len(buys)==s['raw_candidates']
  reasons=collections.Counter(o['reason'] for o in buys if o['status']=='rejected')
  closed=[t for t in rt if t['closed']];opened=[t for t in rt if not t['closed']]
  pr={**s,'max_decline_fraction':dd,'cash_only_days':cashdays,'source_signal_passes':s['signal_accepted'],'filled_buys':sum(o['status']=='filled' for o in buys),'buy_reject_reasons':dict(reasons),'closed_pnl_sum':sum(t['net_pnl'] for t in closed),'open_pnl_sum':sum(t['net_pnl'] for t in opened),'positive_closed':sum(t['net_pnl']>0 for t in closed),'largest_position_pnl':max((t['net_pnl'] for t in rt),default=None),'last_open_entries':[{'date':t['entry_date'],'net_pnl':t['net_pnl'],'market_value':t['market_value']} for t in opened]}
  profiles.append(pr)
  yy=collections.defaultdict(list)
  for d in ds:yy[d['date'][:4]].append(d)
  prior=100000
  for y,rr in sorted(yy.items()):
   end=float(rr[-1]['equity']);pk=prior;d0=0
   for d in rr:pk=max(pk,float(d['equity']));d0=min(d0,float(d['equity'])/pk-1)
   annual.append({'account_id':s['account_id'],'symbol':sym,'method':s['method'],'fee_per_side':s['fee_per_side'],'year':y,'start_equity':prior,'end_equity':end,'pnl':end-prior,'return':end/prior-1,'period_max_decline':d0});prior=end
  assert abs(sum(a['pnl'] for a in annual if a['account_id']==s['account_id'])-s['net_gain'])<1e-6
  econ=[{k:t.get(k) for k in ['date','side','shares','price','fee']} for t in ts]
  groups[(sym,s['fee_per_side'],json.dumps(econ,sort_keys=True))].append(s['method'])
  checks.append({'account_id':s['account_id'],'days':len(ds),'trades':len(ts),'orders':len(os),'positions':len(rt),'money_fee_drawdown_exposure_position_pnl_annual_match':True})
  inputs += [folder/(n+e) for n,e in [('daily','.csv'),('trades','.csv'),('orders','.json'),('roundtrips','.json')]]
 pairs=[{'symbol':k[0],'fee':k[1],'methods':v,'trade_count':len(json.loads(k[2]))} for k,v in groups.items() if len(v)>1]
 aggregate=[]
 for sym in ['sh510300','sz159915']:
  for fee in [.001,.002]:
   ps=[p for p in profiles if p['symbol']==sym and p['fee_per_side']==fee and not p['method'].startswith('R')]
   aggregate.append({'symbol':sym,'fee':fee,'technical_configs':len(ps),'no_fills':sum(p['buys']==0 for p in ps),'positive_ending':sum(p['net_gain']>0 for p in ps),'negative_ending':sum(p['net_gain']<0 for p in ps),'source_candidates':sum(p['raw_candidates'] for p in ps),'source_accepted':sum(p['signal_accepted'] for p in ps),'total_buys_across_distinct_accounts':sum(p['buys'] for p in ps),'warning':'Accounts share market/overlapping source events; counts are not independent strategy successes.'})
 save('results.json',{'profiles':profiles,'identical_trade_paths':pairs,'technical_activity':aggregate,'checks':checks});save('annual.json',annual)
 save('input-lock.json',{'files':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(set(inputs))}})
 print(json.dumps(aggregate,ensure_ascii=False,indent=2));print('48 account analysis complete')
if __name__=='__main__':main()
