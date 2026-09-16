from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
B=Path(__file__).resolve().parent;R=B.parents[3]
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=B/'final-manifest.json';assert not manifest.exists(),'Do not overwrite sealed evidence'
ind=read(B/'independent-review/results.json');assert ind['status']=='passed' and ind['integrity']['all_unchanged']
review=read(B/'report-review.json');assert review['verdict'] in ['passed','pass','approved','pass_pending_root_final_manifest']
for name in ['prior-input-lock.json','execution/source-lock.json','decision-analysis/input-lock.json','decision-analysis/code-lock-before-results.json']:
 assert all(sha(Path(p))==h for p,h in read(B/name)['files'].items())
prior=read(B/'prior-seals-verification.json');assert len(prior)==15 and not any(x['differences'] for x in prior)
for x in prior:
 assert sha(R/f"docs/experiments/raw/research-{x['batch']}-2026-09-08/final-manifest.json")==x['manifest_sha256']
result=read(B/'decision-analysis/results.json');assert len(result['profiles'])==8
assert all(x['same_buy_ids_and_dates'] and x['same_sale_ids_dates_reasons'] for x in result['comparisons'])
progress=B/'progress.md';progress.write_text(progress.read_text().replace('- 报告/学习/登记：已落盘；待最终文字审阅与封存。','- 报告/学习/登记：已完成；最终文字审阅通过，完整证据已交封存。'))
v={'status':'preseal_checks_passed','at_utc':datetime.now(timezone.utc).isoformat(),'new_accounts':4,'referenced_accounts':4,'new_daily_rows':16796,'new_trades':656,'new_candidate_orders':626,'new_all_orders':952,'new_positions':330,'new_closed_positions':326,'new_annual_rows':48,'all_comparative_annual_rows':96,'same_actual_entry_exit_dates':True,'new_risk_cap_binding_buys':330,'independent_results_passed':True,'independent_numeric_max_difference':ind['maximum_numeric_difference'],'execution_tests':7,'execution_source_files_unchanged':14,'prior_batches_verified_unchanged':15,'new_full_paper_readings':0,'new_learning_entries':1,'okr_write_performed':False,'report_review_passed':True,'manifest_dependency':'Final manifest follows this record and is verified by this script after all reviewers stop writing.'}
(B/'delivery-verification.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
report=R/'docs/experiments/broad-etf-risk-sizing-increment-2026-09-08.md'
learning=[R/f'docs/literature-learning/broad-etf-risk-sizing-lessons-2026-09-08.{s}' for s in ['md','json']]
files=sorted([p for p in B.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p!=manifest]+[report]+learning)
m={'sealed_at_utc':datetime.now(timezone.utc).isoformat(),'scope':'Four new fixed risk-sizing ETF accounts, four immutable old R1 references, independent verification and decision/learning deliverables','mutable_navigation_excluded':['AGENTS.md','docs/experiments/registry.json','docs/experiments/INDEX.md','docs/superpowers/plans/2026-09-08-broad-index-etf-research.md','live OKR database'],'files':{str(p.relative_to(R)):sha(p) for p in files}}
manifest.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
assert all(sha(R/p)==h for p,h in read(manifest)['files'].items())
print(json.dumps({'files_sealed':len(files),'manifest_sha256':sha(manifest),'all_hashes_verified':True,'report_review_manifest_dependency_closed':True},ensure_ascii=False))
