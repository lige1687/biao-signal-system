from pathlib import Path
import gzip,json,csv,hashlib
from collections import Counter
P=Path(__file__).resolve().parent;O=P.parent/'research-tenth-2026-09-08'
def read(p):return json.loads(p.read_text())
def load(p):return json.loads(gzip.decompress(p.read_bytes()))
def key(r):return (r['module'],r['event']['symbol'],r['basis_epoch_start'],r['basis_epoch_end'],r['event']['event_id'])
oldrows=load(O/'history-diagnostic/raw-events.json.gz');newrows=load(P/'history-diagnostic/raw-events.json.gz')
old={key(r):r for r in oldrows};new={key(r):r for r in newrows};assert len(old)==len(oldrows) and len(new)==len(newrows)
diffs=[];summary=[]
for module in ['A','C','D']:
 left={k for k in old if k[0]==module};right={k for k in new if k[0]==module}
 removed=sorted(left-right);added=sorted(right-left);changed=sorted(k for k in left&right if old[k]!=new[k])
 for kind,keys in [('removed',removed),('added',added),('changed',changed)]:
  for k in keys:diffs.append(dict(module=module,kind=kind,before=old.get(k),after=new.get(k)))
 summary.append(dict(module=module,old_events=len(left),new_events=len(right),removed=len(removed),added=len(added),changed=len(changed),removed_confirmed=sum('confirmed' in old[k]['event']['evidence'].get('sub_rule','') for k in removed),added_confirmed=sum('confirmed' in new[k]['event']['evidence'].get('sub_rule','') for k in added)))
# Confirm four historical IDs now persist; preserve and explain any cross-version field changes.
prior=load(O/'history-diagnostic/differences.json.gz');restored=[]
for row in prior:
 if row['kind']!='removed_after_future':continue
 match=[r for r in newrows if r['event']['event_id']==row['event_id'] and r['basis_epoch_start']==row['epoch_start'] and r['basis_epoch_end']==row['epoch_end']]
 assert len(match)==1,row
 actual=match[0]['event']; prior_event=row['before']
 expected=json.loads(json.dumps(prior_event))
 changes=[]
 if row['symbol']=='sh513100':
  expected['evidence']['a3_structure_id']='strict_bottom:2015-12-30'
  changes=[dict(field='evidence.a3_structure_id',before=prior_event['evidence']['a3_structure_id'],after=expected['evidence']['a3_structure_id'],reason='separate raw-history reconstruction proves first publication on Dec30; old Dec31 source date was already rewritten')]
 assert actual==expected,row
 restored.append(dict(symbol=row['symbol'],cutoff=row['cutoff'],event_id=row['event_id'],event_preserved=True,full_fields_equal_old_prefix=actual==prior_event,cross_version_changes=changes))
assert len(restored)==4
out=dict(modules=summary,restored_confirmations=restored,meaning='old implementation versus repaired implementation differences; distinct from fixed-history consistency; events are not eligible or independent trades')
(P/'old-new-event-comparison.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
with gzip.open(P/'old-new-event-differences.json.gz','wt') as f:json.dump(diffs,f,ensure_ascii=False)
print(json.dumps(out,ensure_ascii=False))
