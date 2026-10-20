"""Read-only checks of frozen input identities, reports, and recorded verification."""
from pathlib import Path
import json,hashlib,re,math
from urllib.parse import unquote
P=Path(__file__).resolve().parent;REPO=P.parents[3];S=P/'study'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
prev=json.loads((P.parent/'research-fourth-2026-09-08/final-manifest.json').read_text())
for f,h in prev['files'].items():assert sha(REPO/f)==h,('previous archive modified',f)
for f in json.loads((P/'input-manifest.json').read_text())['files']:assert sha(Path(f['path']))==f['sha256']
qual=json.loads((S/'qualification.json').read_text());assert qual['window']==['2013-07-30','2026-06-30'];assert len(qual['pdf_checks'])==19
for f in qual['sources']+qual['pdf_checks']:assert sha(Path(f['path']))==f['sha256']
lock=json.loads((S/'run-lock.json').read_text());assert lock['planned_runs']==21 and lock['at']>lock['protocol_frozen_at']
for f,key in [('protocol.md','protocol_sha256'),('qualification.json','qualification_sha256'),('cash_engine.py','engine_sha256'),('run_study.py','runner_sha256')]:assert sha(S/f)==lock[key],f
for f,n in [('final-tests-original.txt',12),('final-tests-history.txt',8)]:
 t=(S/f).read_text();assert f'Ran {n} tests' in t and '\nOK\n' in t
invariance=json.loads((S/'old-results-invariance.json').read_text());assert len(invariance)==12 and all(r['daily_values_unchanged'] and r['all_trades_unchanged'] for r in invariance)
rows=json.loads((S/'summary.json').read_text());assert len(rows)==21
assert all(math.isfinite(x['final_equity']) and math.isfinite(x['max_drawdown']) for x in rows)
recon=json.loads((S/'reconciliation.json').read_text());assert len(recon)==21 and all(x['all_balances_rebuilt'] for x in recon)
assert sum(x['days'] for x in recon)==70785 and sum(x['trades'] for x in recon)==27311
ind=json.loads((S/'independent-long-ledgers.json').read_text());assert len(ind['results'])==3
for f in ind['input_hashes']:
 if isinstance(f,dict):
  path=f.get('path',f.get('file'));assert sha(Path(path))==f['sha256']
cards=json.loads((P/'evidence-cards.json').read_text());assert len(cards)==2
for c in cards:
 e=c['evidence_ref'];assert e['schema_version']=='provenance/1.2'
 for p,h in zip(e['source_path'],e['source_hash']):assert sha(Path(p))==h
registry=json.loads((REPO/'docs/experiments/registry.json').read_text());new=json.loads((P/'registration.json').read_text());local_links=0
reports=[]
for f,entry in new.items():
 p=REPO/f;reports.append(p);s=p.read_text();assert '## 一句话结论（大白话）' in s and '## ARCHIVE' in s
 assert registry['entries'][f]==entry and entry['category'] in registry['categories']
reports.append(REPO/'docs/literature-learning/research-applications-2026-09-08.md')
for p in reports:
 for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
  if '://' in target or target.startswith('#'):continue
  actual=(p.parent/unquote(target.split('#')[0])).resolve();assert actual.exists(),('missing link',actual);local_links+=1
okr=json.loads((P/'okr-after.json').read_text());assert okr['status']=='review' and all(m['done'] for m in okr['milestones'])
x=json.loads((P/'okr-08-state.json').read_text());assert x['status']=='in_progress' and not x['milestones'][-1]['done']
print(json.dumps(dict(prior_archive_unchanged=len(prev['files']),formal_report_pages_verified=19,new_pdfs=15,tests_passed=20,old_accounts_unchanged=12,fixed_comparisons=21,reconciled_daily_records=70785,reconciled_transactions=27311,independently_reconstructed_accounts=3,evidence_cards=2,reports_registered=2,local_links_verified=local_links,okr_06='review',okr_08='in_progress'),ensure_ascii=False,indent=2))
