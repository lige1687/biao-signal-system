"""Exhaustive original/corrected comparisons, preserving every differing field."""
from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parent;BASE=P.parent
read=lambda p:json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def differences(a,b,path=''):
 if isinstance(a,dict) and isinstance(b,dict):
  return [d for k in sorted(set(a)|set(b)) for d in differences(a.get(k),b.get(k),path+'/'+k)]
 if isinstance(a,list) and isinstance(b,list):
  if len(a)!=len(b):return [dict(path=path,before=a,after=b)]
  return [d for i,(x,y) in enumerate(zip(a,b)) for d in differences(x,y,path+'/'+str(i))]
 return [] if a==b else [dict(path=path,before=a,after=b)]
def main():
 old=BASE/'account-results';new=BASE/'precision-account-results';equal=[];changes=[]
 for c in read(BASE/'configurations.json'):
  cfg=c['id']
  for name in ['daily.csv','trades.csv','events.json','roundtrips.json']:
   a=old/cfg/name;b=new/cfg/name;assert sha(a)==sha(b),(cfg,name);equal.append(str(Path(cfg)/name))
  a=read(old/cfg/'orders.json');b=read(new/cfg/'orders.json');assert len(a)==len(b)
  for x,y in zip(a,b):
   ds=differences(x,y)
   if ds:changes.append(dict(config_id=cfg,order_id=x['order_id'],candidate_id=x.get('candidate_id'),changes=ds))
 # Detailed ordering metadata may carry changed numeric display; economic paths allowed only for two known orders.
 expected={'A20E:first_ma_pullback:64e8c7322fdea81bccfdf858','A20J:first_ma_pullback:5dfc14dc6e284f6f8b6b9c36'}
 substantive=[]
 for row in changes:
  ds=[d for d in row['changes'] if d['path'].split('/')[-1] not in {'signal_rr','signal_rr_recomputed','open_rr'}]
  if ds:assert row['candidate_id'] in expected,(row,ds);substantive.append(dict(**{k:v for k,v in row.items() if k!='changes'},changes=ds))
 assert {r['candidate_id'] for r in substantive}==expected
 for name in ['annual-contributions.csv','product-contributions.csv','a-first-touch-contributions.csv']:
  assert sha(old/name)==sha(new/name),name;equal.append(name)
 sd=differences(read(old/'summary.json'),read(new/'summary.json'))
 assert all(d['path'].split('/')[2] in {'signal_accepted','rejection_reason_counts'} for d in sd),sd
 save(P/'order-field-differences.json',changes);save(P/'summary-differences.json',sd)
 save(P/'comparison.json',dict(status='passed',exact_files=equal,exact_file_count=len(equal),financial_results_unchanged=True,changed_order_records=len(changes),changed_rejection_paths=substantive,summary_changes=sd,original_completion_sha256=sha(old/'completion.json'),corrected_completion_sha256=sha(new/'completion.json')))
 print('Exact financial files:',len(equal),'changed order records:',len(changes),'changed rejection paths:',len(substantive))
if __name__=='__main__':main()
