"""Final read-only checks, then new immutable manifest; never overwrite a prior seal."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,gzip,re
P=Path(__file__).resolve().parent;ROOT=P.parents[3]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def check_files(files,base):
 for f,h in files.items():assert sha(base/f)==h,str(base/f)
 return len(files)
def main():
 assert not (P/'final-manifest.json').exists()
 old=[]
 for batch in ['fourth','fifth','sixth','seventh','eighth','ninth','tenth','eleventh']:
  f=P.parent/f'research-{batch}-2026-09-08/final-manifest.json';doc=read(f);n=check_files(doc['files'],ROOT);old.append(dict(batch=batch,files=n,manifest_sha256=sha(f)))
 seals=[]
 for rel in ['independent-review/first-review-seal.json','independent-review/precision-addendum/precision-review-seal.json']:
  f=P/rel;n=check_files(read(f)['files'],f.parent);seals.append(dict(seal=rel,files=n,sha256=sha(f)))
 locks=[]
 for rel in ['adapter/run-lock.json','adapter/candidate-review-lock.json','account-results/run-lock.json','precision-fix/candidate-lock.json','precision-account-results/run-lock.json']:
  f=P/rel;n=check_files(read(f)['files'],Path('/'));locks.append(dict(lock=rel,files=n))
 for name in ['results','order-results','source-results','summary-results','revision-difference-results']:
  assert read(P/f'independent-review/precision-addendum/{name}.json')['status']=='passed',name
 results=read(P/'precision-account-results/summary.json');assert len(results)==12 and sum(m['buys'] for m in results)==36 and sum(m['sells'] for m in results)==29
 assert sum(m['signal_accepted'] for m in results)==127
 assert {m['config_id'] for m in results if m['buys']==0}=={'A120J','C3','D','REF_BREAKOUT'}
 for m in results:
  trips=read(P/'precision-account-results'/m['config_id']/'roundtrips.json')
  assert abs(sum(t['net_pnl'] for t in trips)-m['net_gain'])<1e-6
  if m['config_id'] in {'A20E','A20J'}:assert abs(sum(t['net_pnl'] for t in trips if not t['closed'])-234138.8031)<1e-6
  if m['config_id']=='C1':assert len([t for t in trips if t['closed'] and t['net_pnl']<0])==15
 assert read(P/'precision-fix/comparison.json')['exact_file_count']==51
 with gzip.open(P/'precision-fix/candidates.json.gz','rt') as f:cs=json.load(f)
 assert len(cs)==2633 and len({c['candidate_id'] for c in cs})==2633
 package=P/'research-package';original=P.parent/'research-eleventh-2026-09-08/research-package'
 for f in package.rglob('*'):
  if f.is_file():assert sha(f)==sha(original/f.relative_to(package))
 assert not list(P.rglob('__pycache__'))
 report=ROOT/'docs/experiments/acd-limited-account-comparison-2026-09-08.md'
 assert '## 一句话结论（大白话）' in report.read_text() and '## ARCHIVE' in report.read_text()
 registry=read(ROOT/'docs/experiments/registry.json');entry=registry['entries'][str(report.relative_to(ROOT))];assert entry['category'] in registry['categories'] and entry['verdict']=='mixed'
 learning=[ROOT/f'docs/literature-learning/account-comparison-lessons-2026-09-08.{e}' for e in ['md','json']]
 assert len(read(learning[1])['entries'])==2
 for f in [report,learning[0]]:
  for target in re.findall(r'\]\(([^)]+)\)',f.read_text()):
   if not target.startswith(('https:','http:','#')):assert (f.parent/target.split('#')[0]).exists(),target
 before=read(P/'okr-before.json');after=read(P/'okr-after.json')
 bi={g['id']:g for g in before['items']};ai={g['id']:g for g in after['items']}
 assert set(bi)==set(ai)
 assert all(bi[k]==ai[k] for k in bi if k!='K-baseline')
 k=ai['K-baseline'];assert k['version']==10 and k['status']=='in_progress' and sum(bool(m['done']) for m in k['milestones'])==3
 record=dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),old_seals=old,independent_seals=seals,input_locks=locks,configs=12,buys=36,sells=29,candidates=2633,signal_accepted=127,exact_original_corrected_financial_files=51,registered=True,source_package_unchanged=True,learning_entries=2,okr_prior_approved_update_only=True)
 save(P/'root-verification.json',record)
 files=[f for f in P.rglob('*') if f.is_file()]+[report]+learning
 save(P/'final-manifest.json',dict(sealed_at_utc=datetime.now(timezone.utc).isoformat(),scope='twelfth limited accounts, original failure and isolated precision correction, two independent snapshots, report and learning; shared INDEX/registry/live OKR excluded',files={str(f.relative_to(ROOT)):sha(f) for f in sorted(files)}))
 check_files(read(P/'final-manifest.json')['files'],ROOT)
 print(json.dumps(dict(status='passed',sealed_files=len(files),manifest_sha256=sha(P/'final-manifest.json'),old_seals_verified=old),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
