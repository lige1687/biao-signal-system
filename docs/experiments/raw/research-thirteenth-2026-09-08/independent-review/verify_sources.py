"""New narrow source preservation audit: all 504 already-reviewed A records must be identical."""
from verify_accounts import *
import gzip
from collections import Counter

def run_sources():
 original=json.load(gzip.open(SNAP/'twelfth-candidates.json.gz','rt'))
 expected=[c for c in original if c['config_id'] in CONFIGS]
 assert len(expected)==504
 rows=jload(ACCOUNT/'candidates.json')
 # Original ordering is part of exact reuse; no recalculation of old source algorithm claimed.
 assert rows==expected,'Candidate missing, reordered or mutated'
 checks=[]
 for c in expected:
  cfg=c['config_id'];orders=jload(ACCOUNT/cfg/'orders.json')
  order=next(o for o in orders if o.get('candidate_id')==c['candidate_id'])
  assert order['candidate_metadata']==c
  checks.append(dict(config=cfg,candidate_id=c['candidate_id'],signal_date=c['signal_date'],signal_accepted=c['signal_accepted'],full_record_identical=True,order_metadata_identical=True))
 writecsv(BASE/'candidate-source-checks.csv',checks)
 save(BASE/'source-results.json',dict(status='passed',candidates=len(rows),per_config=dict(Counter(c['config_id'] for c in rows)),scope='Entire original A record including nested event/target/discipline data and all order metadata is identical to frozen twelfth precision source. Existing detector/target-selection validation is reused, not independently recreated in this batch.'))
 if VARIANT=='S':
  baseline=[]
  for cfg in CONFIGS:
   for f in ('daily.csv','trades.csv','orders.json','events.json','roundtrips.json'):
    old=SNAP/'twelfth-baseline'/cfg/f;new=ACCOUNT/cfg/f
    before=readcsv(old) if f.endswith('.csv') else jload(old)
    after=readcsv(new) if f.endswith('.csv') else jload(new)
    assert before==after,(cfg,f,'baseline table differs')
    baseline.append(dict(config=cfg,file=f,rows=len(before),old_sha256=sha(old),new_sha256=sha(new),exact_table_equal=True,byte_identical=sha(old)==sha(new)))
  writecsv(REVIEW/'baseline-table-checks.csv',baseline)
  save(REVIEW/'baseline-results.json',dict(status='passed',tables=len(baseline),all_exact_table_equal=True,all_byte_identical=all(x['byte_identical'] for x in baseline)))
 print('Full A source preservation passed:',len(rows))
if __name__=='__main__':run_sources()
