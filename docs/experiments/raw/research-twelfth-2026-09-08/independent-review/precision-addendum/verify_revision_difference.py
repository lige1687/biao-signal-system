"""Independent original/revised evidence comparison; never runs either account engine."""
from verify_accounts import *
from collections import Counter

def run_difference():
 original=BASE.parent/'accepted';revised=BASE/'accepted'
 protected=jload(BASE.parent/'first-review-seal.json')
 assert all(sha(BASE.parent/p)==h for p,h in protected['files'].items()),'Original sealed review changed'
 cfgs=jload(revised/'configurations.json');assert [c['id'] for c in cfgs]==CONFIGS
 financial=[Path(cfg)/f for cfg in CONFIGS for f in ['daily.csv','trades.csv','events.json','roundtrips.json']]
 financial += [Path(f) for f in ['annual-contributions.csv','product-contributions.csv','a-first-touch-contributions.csv']]
 financial_checks=[]
 for rel in financial:
  a=original/'account-results'/rel;b=revised/'account-results'/rel
  assert a.read_bytes()==b.read_bytes(),('Economic output changed',str(rel))
  financial_checks.append(dict(file=str(rel),sha256=sha(a),bytes=a.stat().st_size))
 old={c['candidate_id']:c for c in jload(original/'account-results/candidates.json')};new={c['candidate_id']:c for c in jload(revised/'account-results/candidates.json')};assert set(old)==set(new)
 changes=[];accepted_changed=[]
 for cid,c in old.items():
  n=new[cid];fields={k for k in set(c)|set(n) if c.get(k)!=n.get(k)}
  assert fields<={'signal_rr','signal_accepted','signal_reject_reason'}
  if cid.startswith('REF_'):assert not fields
  if fields:changes.append(dict(candidate_id=cid,fields=sorted(fields)))
  if 'signal_accepted' in fields:
   assert c['signal_accepted'] is False and n['signal_accepted'] is True and n['signal_reject_reason'] is None and num(n['signal_rr'])==3
   accepted_changed.append(cid)
 assert len(accepted_changed)==2
 orderchanges=[];decision_changes=[];rr_fields=Counter();maxrr=ZERO
 for cfg in CONFIGS:
  ao=jload(original/'account-results'/cfg/'orders.json');bo=jload(revised/'account-results'/cfg/'orders.json')
  assert [o['order_id'] for o in ao]==[o['order_id'] for o in bo]
  for a,b in zip(ao,bo):
   changed={k for k in set(a)|set(b) if a.get(k)!=b.get(k)}
   assert changed<={'signal_rr','signal_accepted','signal_reject_reason','signal_rr_recomputed','open_rr','attempts','candidate_metadata','reason','resolved_date'},(cfg,a['order_id'],changed)
   if changed:orderchanges.append(dict(config=cfg,order_id=a['order_id'],candidate_id=a.get('candidate_id'),fields=sorted(changed)))
   if a['reason']!=b['reason']:
    assert a['candidate_id'] in accepted_changed and a['reason']=='signal_reward_risk_below_3' and b['reason']=='nonpositive_open_risk'
    assert a['status']==b['status']=='rejected' and not a['attempts'] and len(b['attempts'])==1
    decision_changes.append(dict(candidate_id=a['candidate_id'],original_reason=a['reason'],revised_reason=b['reason'],original_resolved_date=a['resolved_date'],revised_resolved_date=b['resolved_date'],revised_attempt=b['attempts'][0]))
   else:
    assert len(a['attempts'])==len(b['attempts'])
    for x,y in zip(a['attempts'],b['attempts']):
     different={k for k in set(x)|set(y) if x.get(k)!=y.get(k)}
     assert different<={'open_rr'}
     if different:diff=abs(num(x['open_rr'])-num(y['open_rr']));assert diff<D('1e-10');maxrr=max(maxrr,diff)
   for f in ['signal_rr','signal_rr_recomputed','open_rr']:
    if a.get(f) is not None and b.get(f) is not None:
     diff=abs(num(a[f])-num(b[f]));assert diff<D('1e-10');maxrr=max(maxrr,diff)
   rr_fields.update(changed)
 assert len(decision_changes)==2
 for entry in jload(BASE/'accepted-inputs.json')['files']:assert sha(Path(entry['source']))==entry['sha256'] and sha(revised/entry['file'])==entry['sha256']
 save(BASE/'revision-difference-results.json',dict(status='passed',original_review_files_unchanged=len(protected['files']),revised_input_files_unchanged=len(jload(BASE/'accepted-inputs.json')['files']),financial_files_byte_identical=financial_checks,candidates=len(old),candidate_field_changes=len(changes),changed_candidate_field_counts=dict(Counter(f for c in changes for f in c['fields'])),candidate_acceptance_changes=accepted_changed,order_records_with_field_changes=len(orderchanges),order_changed_field_counts=dict(rr_fields),actual_decision_changes=decision_changes,max_changed_rr_field_difference=maxrr))
 save(BASE/'candidate-field-changes.json',changes);save(BASE/'order-field-changes.json',orderchanges)
 print('Original review protected; 51 financial files identical; two rejection stages changed, no economic changes.')

if __name__=='__main__':run_difference()
