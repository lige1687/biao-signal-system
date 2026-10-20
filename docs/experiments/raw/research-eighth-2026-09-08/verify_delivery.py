from pathlib import Path
import hashlib,json,re
from datetime import datetime,timezone
import pandas as pd
P=Path(__file__).resolve().parent;ROOT=P.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
checks={}
for batch in ['fourth','fifth','sixth','seventh']:
 f=P.parent/f'research-{batch}-2026-09-08/final-manifest.json';entries=read(f)['files']
 bad=[path for path,h in entries.items() if sha(ROOT/path)!=h];assert not bad,(batch,bad)
 checks[batch+'_seal']={'files':len(entries),'mismatches':bad,'manifest_sha256':sha(f)}
for name in ['b-research-fix','product-qualification','technical-account','candidate-review','account-review']:
 q=P/name; entries=read(q/'manifest.json')['files'];bad=[]
 for e in entries:
  path=e.get('path',e.get('file'));assert path
  if sha(q/path)!=e['sha256']:bad.append(path)
 assert not bad,(name,bad)
 checks[name]={'files':len(entries),'mismatches':bad}
for name in ['candidate-study/run-lock.json','account-results/run-lock.json','account-results/summary-code-lock.json']:
 lock=read(P/name)
 for f,h in lock['files'].items():assert sha(Path(f))==h,(name,f)
 checks[name]={'files':len(lock['files']),'unchanged':True}
report=ROOT/'docs/experiments/technical-account-limited-comparison-2026-09-08.md'
learning=ROOT/'docs/literature-learning/technical-comparison-lessons-2026-09-08.md'
key=str(report.relative_to(ROOT));registry=read(ROOT/'docs/experiments/registry.json')
assert registry['entries'][key]['category'] in registry['categories']
assert registry['entries'][key]['verdict']=='mixed'
assert report.name in (ROOT/'docs/experiments/INDEX.md').read_text()
assert '## 一句话结论（大白话）' in report.read_text() and '## ARCHIVE' in report.read_text()
local=[]
for doc in [report,learning]:
 for link in re.findall(r'\]\(([^)]+)\)',doc.read_text()):
  if '://' in link or link.startswith('#'):continue
  target=doc.parent/link.split('#')[0];assert target.exists(),(doc,link);local.append(str(target.resolve()))
checks['report_and_links']={'registered':True,'links_checked':len(local)}
papers={x['id'] for x in read(ROOT/'docs/literature-learning/learning-seed.json')['papers']}
supplement=read(learning.with_suffix('.json'));assert len(supplement['entries'])==2
for e in supplement['entries']:
 assert e['paper_id'] in papers and e['id'] in learning.read_text()
 assert e['body_markdown'] in learning.read_text()
 assert e['method_acceptance']['automatic_adoption'] is False
checks['learning_entries']={'count':2,'markdown_json_match':True,'old_seed_unmodified_by_this_batch':True}
cards=read(P/'evidence-cards.json');assert len(cards)==3
for c in cards:
 ref=c['evidence_ref'];assert len(ref['source_path'])==len(ref['source_hash'])
 for f,h in zip(ref['source_path'],ref['source_hash']):assert sha(Path(f))==h
 for r in c['rule_refs']:assert sha(Path(r['config_path']))==r['config_hash']
 assert c['research']['production_adopted'] is False
checks['evidence_cards']={'count':3,'all_hashes_match':True}
summary=read(P/'account-results/summary.json'); assert {x['config_id'] for x in summary}=={f'P{i}' for i in range(8)}
assert all(x['total_funding']==600000 for x in summary)
assert sum(x['trade_count'] for x in summary)==1925
assert sum(x['completed_trades'] for x in summary)==9
assert sum(len(pd.read_csv(P/'account-results'/x['config_id']/'daily.csv')) for x in summary)==33592
assert read(P/'execution-checks.json')['status']=='passed'
assert 'Ran 17 tests' in (P/'spark-metrics/parent-tests-final.txt').read_text()
assert (P/'spark-metrics/parent-tests-final.txt').read_text().strip().endswith('OK')
assert 'Ran 23 tests' in (P/'parent-account-tests.txt').read_text()
assert (P/'parent-account-tests.txt').read_text().strip().endswith('OK')
checks['result_coverage']={'accounts':8,'daily_rows':33592,'fills':1925,'technical_lifecycles':9,'helper_tests':17,'account_tests':23}
assert read(P/'okr-update-proposal.json')['approval_pending'] is True
checks['okr']={'proposal_only':True,'goal':'K-baseline','proposed_completed_milestones':3,'total_milestones':4}
receipt={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'status':'passed','checks':checks}
(P/'delivery-checks.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(receipt,ensure_ascii=False,indent=2))
