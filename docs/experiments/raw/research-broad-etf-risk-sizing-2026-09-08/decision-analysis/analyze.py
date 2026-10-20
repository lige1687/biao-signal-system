"""Descriptive paired account comparison. No parameter fitting or strategy simulation."""
from pathlib import Path
import csv,json,hashlib,math
from datetime import datetime,timezone
B=Path(__file__).resolve().parents[1]
R=B.parents[3]
OLD=R/'docs/experiments/raw/research-broad-etf-technical-2026-09-08/execution/account-results'
NEW=B/'execution/account-results'
HERE=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text())
rows=lambda p:list(csv.DictReader(p.open()))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,d):
 (HERE/name).write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def main():
 assert not (HERE/'results.json').exists(),'Do not overwrite prior analysis'
 inputs=[Path(__file__).resolve(),OLD/'summary.json',NEW/'summary.json']
 for root,method in [(OLD,'R1'),(NEW,'R1-risk1')]:
  for s in ['sh510300','sz159915']:
   for tag in ['10','20']:
    inputs += [root/f'{s}-{method}-fee{tag}bp'/f for f in ['daily.csv','trades.csv','roundtrips.json','orders.json']]
 locked={str(p):sha(p) for p in inputs}
 save('input-lock.json',{'at_utc':datetime.now(timezone.utc).isoformat(),'files':locked})
 profiles=[];annual=[];positions=[];comparisons=[]
 summaries={d['account_id']:d for rt in [OLD,NEW] for d in read(rt/'summary.json')}
 for root,method in [(OLD,'R1'),(NEW,'R1-risk1')]:
  for s in ['sh510300','sz159915']:
   for tag in ['10','20']:
    aid=f'{s}-{method}-fee{tag}bp';folder=root/aid;fee=int(tag)/10000
    ds=rows(folder/'daily.csv');ts=rows(folder/'trades.csv');ps=read(folder/'roundtrips.json');os=read(folder/'orders.json');buy=[t for t in ts if t['side']=='buy'];by_date={d['date']:d for d in ds}
    es=[float(d['equity']) for d in ds];peak=100000.;draw=0.;expo=[];year_data={};last=100000.
    for d,e in zip(ds,es):
     assert abs(e-float(d['cash'])-float(d['assets'])-float(d['receivable']))<1e-5
     assert float(d['deposit'])==0 and float(d['total_funding'])==100000
     peak=max(peak,e);draw=max(draw,1-e/peak);expo.append(float(d['assets'])/e)
     y=d['date'][:4]
     if y not in year_data:year_data[y]={'start':last,'end':e,'peak':last,'drawdown':0}
     q=year_data[y];q['end']=e;q['peak']=max(q['peak'],e);q['drawdown']=max(q['drawdown'],1-e/q['peak']);last=e
    for y,d in year_data.items():annual.append({'account_id':aid,'symbol':s,'method':method,'fee':fee,'year':y,'start_equity':d['start'],'end_equity':d['end'],'net_gain':d['end']-d['start'],'return':d['end']/d['start']-1,'max_decline':d['drawdown']})
    bs={t['position_id']:t for t in buy};risk_caps=0;cash_caps=0;ties=0
    for p in ps:
     t=bs[p['position_id']];prev=float(t['previous_product_equity']);qty=float(t['shares']);ep=float(t['price']);stop=float(t['stop']);risk=qty*(ep-stop)
     assert prev>0 and risk>0
     cap=math.floor(prev*.01/(ep-stop)/100+1e-12)*100
     beforecash=float(by_date[t['date']]['cash'])+float(t['notional'])+float(t['fee'])
     cashcap=math.floor(max(0,beforecash)/(ep*(1+fee))/100)*100
     if method=='R1-risk1':
      assert abs(qty-min(cap,cashcap))<1e-6,(aid,t['date'],qty,cap,cashcap)
      if cap<cashcap:risk_caps+=1
      elif cashcap<cap:cash_caps+=1
      else:ties+=1
     positions.append({'account_id':aid,'method':method,'candidate_id':p['candidate_id'],'entry_date':p['entry_date'],'exit_date':p['exit_date'],'closed':p['closed'],'previous_equity':prev,'shares':qty,'initial_price_distance':ep-stop,'initial_planned_risk':risk,'initial_risk_fraction':risk/prev,'cash_cap_shares':cashcap,'risk_one_percent_cap_shares':cap,'net_pnl':p['net_pnl'],'loss_over_one_percent_equity':bool(p['closed'] and -p['net_pnl']>prev*.01+1e-5),'pnl_to_entry_equity':p['net_pnl']/prev})
    pp=[p for p in positions if p['account_id']==aid];closed=[p for p in pp if p['closed']]
    closed_pnl=sum(p['net_pnl'] for p in closed);open_pnl=sum(p['net_pnl'] for p in pp if not p['closed'])
    assert abs(closed_pnl+open_pnl-(es[-1]-100000))<1e-5
    m=summaries[aid]
    for key,val in [('last_equity',es[-1]),('max_drawdown',draw),('mean_exposure',sum(expo)/len(expo)),('fees',sum(float(t['fee']) for t in ts))]:assert abs(m[key]-val)<1e-5,(aid,key)
    buy_ids=[(t['candidate_id'],t['date']) for t in buy];sale_ids=[(bs[t['position_id']]['candidate_id'],t['date'],t['reason']) for t in ts if t['side']=='sell']
    profiles.append({'account_id':aid,'symbol':s,'method':method,'fee':fee,'days':len(ds),'last_equity':es[-1],'net_gain':es[-1]-100000,'max_decline':draw,'mean_exposure':sum(expo)/len(expo),'cash_only_days':sum(float(d['assets'])==0 for d in ds),'fees':m['fees'],'buys':len(buy),'sells':len(ts)-len(buy),'orders':len(os),'positions':len(ps),'closed_pnl':closed_pnl,'open_pnl':open_pnl,'closed_positions':len(closed),'open_positions':len(pp)-len(closed),'risk_cap_smaller_buys':risk_caps,'cash_cap_smaller_buys':cash_caps,'equal_caps_buys':ties,'losses_over_one_percent':sum(p['loss_over_one_percent_equity'] for p in pp),'worst_completed_loss_fraction':min([p['pnl_to_entry_equity'] for p in closed]+[0]),'buy_id_dates':buy_ids,'sale_id_dates_reasons':sale_ids,'money_drawdown_exposure_fees_positions_checks':True})
 lookup={(p['symbol'],p['fee'],p['method']):p for p in profiles}
 for s in ['sh510300','sz159915']:
  for f in [.001,.002]:
   old=lookup[s,f,'R1'];new=lookup[s,f,'R1-risk1']
   comparisons.append({'symbol':s,'fee':f,'new_minus_old_ending_equity':new['last_equity']-old['last_equity'],'new_minus_old_max_decline':new['max_decline']-old['max_decline'],'same_buy_ids_and_dates':old['buy_id_dates']==new['buy_id_dates'],'same_sale_ids_dates_reasons':old['sale_id_dates_reasons']==new['sale_id_dates_reasons'],'new_only_buys':[x for x in new['buy_id_dates'] if x not in old['buy_id_dates']],'old_only_buys':[x for x in old['buy_id_dates'] if x not in new['buy_id_dates']],'new_wealth_not_lower_and_decline_not_higher':new['last_equity']>=old['last_equity']-1e-5 and new['max_decline']<=old['max_decline']+1e-12})
 assert all(sha(Path(p))==h for p,h in locked.items())
 save('results.json',{'profiles':profiles,'comparisons':comparisons,'all_new_wealth_not_lower_and_decline_not_higher':all(c['new_wealth_not_lower_and_decline_not_higher'] for c in comparisons),'scope':'Same signals and exit policy, only order sizing changes. No fixed-fraction investment control. Known-history descriptive comparison.'})
 save('annual.json',annual);save('position-risk.json',positions)
 print(json.dumps({'profiles':len(profiles),'new_accounts':4,'annual_rows':len(annual),'comparisons':comparisons},ensure_ascii=False))
if __name__=='__main__':main()
