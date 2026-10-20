from pathlib import Path
from decimal import Decimal as D,getcontext,ROUND_FLOOR
from datetime import date
import csv,json,gzip,hashlib,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent;EX=ROOT/'execution';OUT=EX/'attempt-01';IN=EX/'inputs';getcontext().prec=40
sys.path.insert(0,str(HERE));from prior_evidence import build_prior_evidence
def jl(p):return json.loads(p.read_text())
def rc(p):return list(csv.DictReader(p.open()))
def dec(x):return D(str(x))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,default=str)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 cond=jl(EX/'conditions.json')['rows'];cm={x['candidate_id']:x for x in cond};assert len(cm)==84
 with gzip.open(IN/'source-candidates/precision-candidates.json.gz','rt') as f:source=[x for x in json.load(f) if x['config_id']=='C1' and x['symbol'] in ('sh510300','sz159915')]
 sm={x['candidate_id']:x for x in source};assert set(cm)==set(sm)
 membership=[];time_issues=[]
 for cid,x in cm.items():
  s=sm[cid];ev=s['metadata']['source_event']['evidence'];p=dec(x['close'])>=dec(x['sma20']) and abs(dec(x['l1'])-dec(x['sma20']))<=dec(x['atr20'])
  q=bool(ev['dual_ma_bull_state']);groups=['G0']+(['GP'] if p else [])+(['GQ'] if q else [])+(['GPQ'] if p and q else [])
  assert p==x['position_p'] and q==x['direction_q'];assert groups==[g for g in ('G0','GP','GQ','GPQ') if x['group_membership'][g]]
  assert x['reclaim_date']==x['signal_date']==s['signal_date'];assert s['config_id']=='C1';assert x['l2']==x['stop']==s['stop'];assert x['target']==s['target']
  for k in ('l1_confirmed_available_date','breakdown_date','reclaim_date','target_confirmed_at','basis_as_of'):
   if x.get(k) and x[k]>x['signal_date']:time_issues.append({'candidate_id':cid,'field':k,'value':x[k],'signal_date':x['signal_date']})
  membership.append({'candidate_id':cid,'symbol':x['symbol'],'signal_date':x['signal_date'],'P':p,'Q':q,'groups':groups,'p_distance':abs(dec(x['l1'])-dec(x['sma20'])),'atr20':dec(x['atr20']),'target_confirmed_at':x['target_confirmed_at']})
 assert not time_issues
 counts={g:sum(g in x['groups'] for x in membership) for g in ('G0','GP','GQ','GPQ')};assert counts=={'G0':84,'GP':12,'GQ':5,'GPQ':5}
 fixed=jl(OUT/'fixed-summary.json');bars={s:[r['date'] for r in rc(IN/'bars'/f'{s}-nominal.csv')] for s in ('sh510300','sz159915')};opps=[];maturity_checks=[]
 for f in fixed:
  folder=OUT/'fixed-opportunities'/f['path_id'];trips=jl(folder/'roundtrips.json');daily={r['date']:r for r in rc(folder/'daily.csv')};events=jl(folder/'events.json');rt=trips[0] if trips else None
  entered=bool(rt);entry=rt['entry_date'] if rt else None;maturity=None;ret60=None;hold60=None
  if entered:
   after=[d for d in bars[f['symbol']] if d>entry]
   if len(after)>=60:
    maturity=after[59];cut=min([d for d in [rt['exit_date'],maturity] if d is not None]);hold60=(date.fromisoformat(cut)-date.fromisoformat(entry)).days
    if rt['exit_date'] is not None and rt['exit_date']<=maturity:ret60=dec(rt['net_return'])
    else:
     pid=rt['position_id'];accrued=sum((dec(e['amount']) for e in events if e['kind']=='dividend_receivable' and e.get('position_id')==pid and e['date']<=maturity),D(0));row=daily[maturity];value=dec(row['units_'+f['symbol']])*dec(row['mark_'+f['symbol']])+accrued;den=dec(rt['entry_notional'])+dec(rt['buy_fee']);ret60=value/den-1
    maturity_checks.append({'path_id':f['path_id'],'entry_date':entry,'maturity_quote_date':maturity,'holding_days_at_60':hold60,'return_at_60':ret60,'used_actual_exit':bool(rt['exit_date'] and rt['exit_date']<=maturity)})
  holding=(date.fromisoformat(rt['exit_date'] or '2026-06-30')-date.fromisoformat(entry)).days+(0 if rt and rt['exit_date'] else 1) if entered else 0
  for group in f['groups']:
   opps.append({'candidate_id':f['candidate_id'],'symbol':f['symbol'],'group':group,'variant':f['exit_variant'],'fee':str(f['fee']),'signal_date':f['signal_date'],'entered':entered,'entry_date':entry,'exit_date':rt['exit_date'] if rt else None,'net_return':rt['net_return'] if rt else None,'maturity_quote_date':maturity,'return_at_60':ret60,'holding_days':holding,'holding_days_at_60':hold60})
 decisions=[{'candidate_id':x['candidate_id'],'symbol':x['symbol'],'signal_date':x['signal_date']} for x in cond]
 evidence=build_prior_evidence(opps,decisions,groups=['G0','GP','GQ','GPQ'],variants=['E0','E1'],fees=['0.001','0.002'],min_distinct=30);assert len(evidence)==1344
 for x in evidence:
  assert x['maximum_completed_known_date'] is None or x['maximum_completed_known_date']<x['decision_date'];assert x['maximum_maturity_quote_date'] is None or x['maximum_maturity_quote_date']<x['decision_date'];assert x['target_candidate_id'] not in x['completed_candidate_ids']+x['mature_candidate_ids']+x['unresolved_candidate_ids']
 # Full-account entry audit and independently normalized invested-capital curve from roundtrips/daily.
 account_checks=[];curves=[];buy_count=0;exit_sample=[]
 for folder in sorted((OUT/'accounts').iterdir()):
  aid=folder.name;parts=aid.split('-');sym,group,variant=parts[:3];fee=D('.001') if 'fee10bp' in aid else D('.002');orders=jl(folder/'orders.json');trips=jl(folder/'roundtrips.json');daily=rc(folder/'daily.csv');daily_map={r['date']:r for r in daily};events=jl(folder/'events.json');allowed={x['candidate_id'] for x in membership if x['symbol']==sym and group in x['groups']}
  buys=[o for o in orders if o['side']=='buy'];assert {o['candidate_id'] for o in buys}==allowed
  filled=[o for o in buys if o['status']=='filled'];buy_count+=len(filled)
  for o in filled:
   c=sm[o['candidate_id']];assert o['signal_date']==c['signal_date'];assert o['resolved_date']>o['signal_date'];px=dec(o['price']);stop=dec(o['stop']);risk=dec(o['attempts'][0]['previous_product_equity'])*D('.01');q=(risk/(px-stop)/100).to_integral_value(rounding=ROUND_FLOOR)*100;prior=(date.fromisoformat(o['resolved_date'])-__import__('datetime').timedelta(days=1)).isoformat();opening_cash=dec(daily_map[prior]['cash_'+sym]);opening_cash+=sum((dec(e['amount']) for e in events if e['kind']=='dividend_paid' and e['date']==o['resolved_date'] and e.get('symbol')==sym),D(0));cashq=(opening_cash/(px*(1+fee))/100).to_integral_value(rounding=ROUND_FLOOR)*100;assert dec(o['shares'])==min(q,cashq)
  curve=D(1);worst=D(0);peak=D(1)
  for rt in trips:
   factor=1+dec(rt['net_return']);curve*=factor;peak=max(peak,curve);worst=min(worst,curve/peak-1)
  curves.append({'account_id':aid,'positions':len(trips),'ending_unit_factor_product':curve,'rough_trade_endpoint_drawdown':worst})
  sells=[o for o in orders if o['side']=='sell'];
  for o in sells[:1]:exit_sample.append({'account_id':aid,'reason':o['reason'],'signal_date':o['signal_date'],'resolved_date':o.get('resolved_date'),'strictly_later':o.get('resolved_date') is None or o['resolved_date']>o['signal_date']})
  account_checks.append({'account_id':aid,'candidate_orders':len(buys),'filled_buys':len(filled),'positions':len(trips),'candidate_membership_exact':True})
 save(HERE/'membership-independent.json',{'counts':counts,'rows':membership,'time_issues':time_issues});save(HERE/'maturity-60-independent.json',maturity_checks);save(HERE/'prior-evidence-1344.json',evidence);save(HERE/'account-entry-checks.json',account_checks);save(HERE/'invested-curve-key-results.json',curves);save(HERE/'exit-samples.json',exit_sample)
 result={'status':'passed','c1_candidates':84,'qualified_fixed_candidates':len({x['candidate_id'] for x in fixed}),'fixed_paths':len(fixed),'fixed_paths_entered':sum(x['entered'] for x in fixed),'membership_counts':counts,'prior_evidence_rows':len(evidence),'maturity_paths':len(maturity_checks),'accounts':len(account_checks),'filled_account_buys':buy_count,'time_issues':len(time_issues),'exit_samples':len(exit_sample)};save(HERE/'actual-results.json',result);print(json.dumps(result))
 lock=jl(HERE/'actual-input-result-lock.json')['files'];bad=[p for p,h in lock.items() if sha(p)!=h];assert not bad,bad
if __name__=='__main__':main()
