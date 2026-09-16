"""Link user-facing comparison rows to independently checked source/orders and fixed paths."""
from verify_accounts import *

def run():
 root=SNAP/'execution/account-results';candidates=jload(root/'S/candidates.json');cmap={c['candidate_id']:c for c in candidates};orders={}
 for variant in ('S','T'):
  orders[variant]={o['candidate_id']:o for cfg in CONFIGS for o in jload(root/variant/cfg/'orders.json') if o['side']=='buy'}
 rows=readcsv(root/'candidate-outcomes.csv');assert len(rows)==1008
 seen=set()
 for r in rows:
  variant=r['method'];cid=r['candidate_id'];key=(variant,cid);assert key not in seen;seen.add(key);c=cmap[cid];o=orders[variant][cid]
  for field in ('config_id','symbol','signal_date'):assert r[field]==c[field]
  assert r['signal_accepted']==str(c['signal_accepted']) and r['signal_reject_reason']==(c['signal_reject_reason'] or '')
  assert r['status']==o['status'] and r['order_reason']==o['reason'] and r['position_id']==(o.get('position_id') or '')
 wide=readcsv(root/'candidate-status-comparison.csv');assert len(wide)==504 and {r['candidate_id'] for r in wide}==set(cmap)
 changes=[]
 for r in wide:
  cid=r['candidate_id'];c=cmap[cid]
  for field in ('config_id','symbol','signal_date'):assert r[field]==c[field]
  for variant in ('S','T'):
   o=orders[variant][cid]
   for f,k in [('status','status'),('order_reason','reason'),('position_id','position_id')]:assert r[f+'_'+variant]==(o.get(k) or '')
  sb=orders['S'][cid]['status']=='filled';tb=orders['T'][cid]['status']=='filled'
  changes.append(dict(config=c['config_id'],candidate_id=cid,symbol=c['symbol'],signal_date=c['signal_date'],S_bought=sb,T_bought=tb,entry_change='both' if sb and tb else 'new_T' if tb else 'lost_T' if sb else 'neither'))
 fixed={(r['config'],r['position_id'],r['variant']):r for r in jload(REVIEW/'fixed-paths-independent.json')}
 pairs=readcsv(SNAP/'execution/fixed-17-comparison.csv');assert len(pairs)==17
 for p in pairs:
  cfg=p['config_id'];pid=p['position_id'];s=fixed[(cfg,pid,'S')];t=fixed[(cfg,pid,'T')]
  for method,r in [('S',s),('T',t)]:
   assert p[method+'_exit_signal_date']==(r['first_exit_signal'] or '') and p[method+'_exit_date']==(r['exit_date'] or '') and p[method+'_exit_reason']==(r['exit_reason'] or '')
   assert abs(num(p[method+'_net_pnl'])-num(r['net_pnl']))<TOL
  assert abs(num(p['T_minus_S'])-(num(t['net_pnl'])-num(s['net_pnl'])))<TOL
 writecsv(REVIEW/'candidate-entry-comparison-independent.csv',changes)
 save(REVIEW/'comparison-table-results.json',dict(status='passed',candidate_outcomes=len(rows),candidate_paired_statuses=len(wide),fixed_comparison_rows=len(pairs),both_entries=sum(r['entry_change']=='both' for r in changes),new_T_entries=sum(r['entry_change']=='new_T' for r in changes),lost_T_entries=sum(r['entry_change']=='lost_T' for r in changes)))
 print(json.dumps(jload(REVIEW/'comparison-table-results.json')))
if __name__=='__main__':run()
