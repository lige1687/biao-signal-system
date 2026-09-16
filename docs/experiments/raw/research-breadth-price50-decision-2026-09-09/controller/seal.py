from pathlib import Path
import json,hashlib,datetime
import pandas as pd
from lei_signal.research.definitions import load_registry,verify_sources
R=Path(__file__).resolve().parents[5];W=Path(__file__).resolve().parents[1];C=W/'controller';report=R/'docs/experiments/breadth-price50-decision-2026-09-09.md'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
r=load_registry();before=read(C/'registry-before.json');lock=read(C/'source-lock.json');summary=pd.read_csv(W/'execution/results/summary.csv');checks={
 'old_296_files_unchanged':all(sha(R/p)==h for p,h in lock['files'].items()),
 'protocol_unchanged':sha(W/'protocol.md')==lock['protocol_sha256'],
 'old_registry_objects_unchanged':all(x in r['objects'] for x in before['objects']),
 'registered_sources_verified':verify_sources(r)==31,
 'new_four_paths':len(summary)==4 and summary.account_id.nunique()==4,
 'execution_passed':read(W/'execution/verification.json')['passed'],
 'independent_new_metrics_passed':read(W/'comparison/new-metric-review.json')['passed'],
 'account_difference_checks_passed':read(W/'comparison/checks.json')['passed'],
 'initial_12_independent':read(W/'chinext-scope/initial-12-review/attribution-review.json')['passed'],
 'additional_6_independent':read(W/'chinext-scope/additional-p50-review/attribution-review.json')['passed'],
 'all40_summary':len(pd.read_csv(W/'comparison/all-40-summary.csv'))==40,
 'all40_phases':len(pd.read_csv(W/'comparison/all-40-fixed-phases.csv'))==120,
 'all18_relative':len(pd.read_csv(W/'comparison/relative-summary.csv'))==18,
 'preliminary_financials_match':read(C/'preliminary-versus-final.json')['same_financial_summary'],
 'report_complete':all(f'## {i}.' in report.read_text() for i in range(1,11)) and '[待' not in report.read_text() and 'PROFIT_TABLE' not in report.read_text(),
 'registry_entry':str(report.relative_to(R)) in read(R/'docs/experiments/registry.json')['entries'],
 'index_entry':report.name in (R/'docs/experiments/INDEX.md').read_text(),
}
for sub in ['execution','qualification']:
 m=read(W/sub/'manifest.json'); records=m.get('files',[]);bad=[]
 for x in records:
  p=Path(x['path']);target=(R/p if str(p).startswith('docs/') else W/sub/p)
  if sha(target)!=x['sha256']:bad.append(str(target))
 checks[sub+'_manifest']=not bad
 assert not bad,bad
assert all(checks.values()),checks
(C/'completion-checks.json').write_text(json.dumps({'passed':True,'checks':checks,'definition_schema_tests':'28 passed in 0.78s','price50_boundary_tests':'5 passed','visual_review':'relative-performance.png viewed: four axes, same fee scales, no clipped text, clear non-account-loss label','limits':['historical membership incomplete','historical availability unknown','no production or automatic observation','no OKR progress changes'],'review_note':'Final small prose additions clarify source date labels, first trial, and known candidate decisions; no post-review financial changes.'},ensure_ascii=False,indent=2)+'\n')
files=sorted([p for p in W.rglob('*') if p.is_file() and p.name!='final-manifest.json' and '__pycache__' not in p.parts]+[report]);m={'sealed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Fixed price50 decision batch; includes failed attempts, qualification, comparisons and independent reviews. Mutable registry/INDEX/plan excluded; registry snapshot included.','files':[{'path':str(p.relative_to(R)),'sha256':sha(p),'bytes':p.stat().st_size} for p in files]};(W/'final-manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n');assert all(sha(R/x['path'])==x['sha256'] for x in m['files']);print(json.dumps({'passed':True,'sealed_files':len(files),'checks':checks},ensure_ascii=False))
