"""Final verification and immutable archive, without rerunning sealed experiments."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,csv,re
P=Path(__file__).resolve().parent;ROOT=P.parents[3];REV=P/'independent-review'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def check(files,base):
 for name,value in files.items():assert sha(base/name)==(value['sha256'] if isinstance(value,dict) else value),str(base/name)
 return len(files)
def main():
 assert not (P/'final-manifest.json').exists()
 old=[]
 for b in ['fourth','fifth','sixth','seventh','eighth','ninth','tenth','eleventh','twelfth']:
  f=P.parent/f'research-{b}-2026-09-08/final-manifest.json';n=check(read(f)['files'],ROOT);old.append(dict(batch=b,files=n,manifest_sha256=sha(f)))
 nreview=check(read(REV/'final-manifest.json')['files'],REV)
 for rel in ['initial-lock.json','execution/run-lock.json']:check(read(P/rel)['files'],Path('/'))
 accepted=read(REV/'accepted-inputs.json')['files'];changes=read(REV/'source-integrity-final.json')['changes'];exceptions={c['source']:c for c in changes};nsame=0
 for rec in accepted:
  assert sha(REV/'accepted'/rec['file'])==rec['sha256']
  f=Path(rec['source'])
  if str(f) in exceptions:
   c=exceptions[str(f)];assert not f.exists()
   if c['change']=='log_renamed_identical_bytes':assert sha(ROOT/c['current_source'])==rec['sha256']
   else:assert c['change']=='removed_generated_cache_accepted_copy_preserved'
  else:assert sha(f)==rec['sha256'];nsame+=1
 assert nsame==221 and len(accepted)==224 and len(changes)==3
 v=read(REV/'summary.json');assert v['numeric_review']=='passed' and v['source_integrity']=='changed_log_path_and_removed_caches'
 for meth in ['S','T']:
  for name in ['results','order-results','source-results','summary-results']:assert read(REV/meth/f'{name}.json')['status']=='passed'
 assert v['trades']==90 and v['calendar_account_days']==50388 and v['comparison_tables']['new_T_entries']==14
 assert read(REV/'fixed-path-results.json')['status']=='passed' and read(REV/'observation-results.json')['differences']==0
 results=read(P/'execution/account-results/summary.json');assert len(results)==12
 lookup={(r['method'],r['config_id']):r for r in results}
 configs=read(P/'configurations.json');prior=P.parent/'research-twelfth-2026-09-08/precision-account-results'
 for c in configs:
  cfg=c['id'];s,t=lookup['S',cfg],lookup['T',cfg]
  assert s['total_funding']==t['total_funding']==600000
  for name in ['daily.csv','trades.csv','orders.json','events.json','roundtrips.json']:
   assert sha(P/'execution/account-results/S'/cfg/name)==sha(prior/cfg/name)
   if cfg not in {'A20E','A20J'}:assert sha(P/'execution/account-results/S'/cfg/name)==sha(P/'execution/account-results/T'/cfg/name)
  if cfg in {'A20E','A20J'}:
   assert abs((t['last_equity']-s['last_equity'])-(-184600.7905))<1e-6
   assert t['buys']==s['buys']+7 and t['open_positions']==0
 for method in ['S','T']:
  candidates=read(P/'execution/account-results'/method/'candidates.json');assert len(candidates)==504 and len({c['candidate_id'] for c in candidates})==504
 with (P/'execution/fixed-17-comparison.csv').open() as f:paired=list(csv.DictReader(f))
 assert len(paired)==17 and sum(r['S_exit_date']!=r['T_exit_date'] for r in paired)==8
 tests=(P/'supplemental-tests/root-tests.txt').read_text();assert '7 passed' in tests
 report=ROOT/'docs/experiments/a-road-exit-account-comparison-2026-09-08.md';learning=[ROOT/f'docs/literature-learning/exit-and-reentry-lessons-2026-09-08.{e}' for e in ['md','json']]
 assert '## 一句话结论（大白话）' in report.read_text() and '## ARCHIVE' in report.read_text()
 reg=read(ROOT/'docs/experiments/registry.json');entry=reg['entries'][str(report.relative_to(ROOT))];assert entry['category'] in reg['categories'] and entry['verdict']=='mixed'
 for f in [report,learning[0]]:
  for target in re.findall(r'\]\(([^)]+)\)',f.read_text()):
   if not target.startswith(('http:','https:','#')):assert (f.parent/target.split('#')[0]).exists(),target
 seed=read(learning[1]);assert len(seed['entries'])==1 and len(seed['reading_updates'])==1
 source=read(P/'paper-methods/source.json');assert sha(P/'paper-methods/kaminski-lo-2014.pdf')==source['pdf_sha256'] and source['pages']==21
 assert not list(P.rglob('__pycache__'))
 save(P/'root-verification.json',dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),old_seals=old,independent_sealed_files=nreview,independent_manifest_sha256=sha(REV/'final-manifest.json'),numeric_review='passed',accepted_224_all_unchanged=True,original_sources_unchanged=221,explicit_source_path_exceptions=changes,baseline_identical_tables=30,unchanged_four_config_tables=20,tests_passed=7,configs=12,original_fixed_entries=17,registered=True,paper_pages=21,learning_entries=1,reading_updates=1,okr_updated=False))
 files=sorted([f for f in P.rglob('*') if f.is_file()]+[report]+learning)
 save(P/'final-manifest.json',dict(sealed_at_utc=datetime.now(timezone.utc).isoformat(),scope='thirteenth isolated A exit research and independent evidence, failures, primary paper, main report and learning; shared registry/INDEX/live OKR excluded',files={str(f.relative_to(ROOT)):sha(f) for f in files}))
 check(read(P/'final-manifest.json')['files'],ROOT)
 print(json.dumps(dict(status='passed',sealed_files=len(files),manifest_sha256=sha(P/'final-manifest.json'),old_batches_verified=len(old),independent_sealed_files=nreview,source_path_exceptions=3,financial_discrepancies=0),indent=2))
if __name__=='__main__':main()
