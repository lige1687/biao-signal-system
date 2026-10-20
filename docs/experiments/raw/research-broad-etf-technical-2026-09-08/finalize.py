from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
R=Path(__file__).resolve().parents[4]
B=Path(__file__).resolve().parent
manifest=B/'final-manifest.json'
assert not manifest.exists(),'sealed output must not be overwritten'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert read(B/'independent-review/results.json')['status']=='passed'
assert not read(B/'report-review.json')['open_numeric_or_attribution_findings']
assert len(read(B/'decision-analysis/results.json')['checks'])==48
for f in ['execution/source-lock.json','decision-analysis/input-lock.json']:
 assert all(sha(Path(p))==h for p,h in read(B/f)['files'].items())
prior=read(B/'prior-seals-verification.json');assert len(prior)==14 and all(not x['differences'] for x in prior)
for x in prior:
 p=R/f"docs/experiments/raw/research-{x['batch']}-2026-09-08/final-manifest.json"
 assert sha(p)==x['manifest_sha256']
report=R/'docs/experiments/broad-etf-technical-capital-comparison-2026-09-08.md'
learning=[R/f'docs/literature-learning/broad-etf-technical-lessons-2026-09-08.{s}' for s in ['md','json']]
v={'status':'preseal_checks_passed','date_utc':datetime.now(timezone.utc).isoformat(),'accounts':48,'daily_rows':201552,'trades':982,'orders':2754,'positions':496,'annual_rows':576,'source_files_unchanged':17,'prior_batches_unchanged':14,'prior_manifest_file_entries':sum(x['files'] for x in prior),'official_pdf_hashes_verified':4,'zero_trade_table_index_verified':20,'report_numeric_attribution_review':'passed','report_registry_category':'模块与信号','verdict':'mixed','learning_existing_paper_ids':['brock1992','kaminski2014','sullivan1999'],'new_readings':0,'okr_write_performed':False,'okr_progress':{'okr-c05c65463698':'2/4','K-baseline':'3/4','K-newmodules':'0/4'},'final_manifest_dependency':'Created after this verification record and all reviewers stop; finalize.py verifies all sealed file hashes before reporting success.'}
(B/'delivery-verification.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
files=sorted([p for p in B.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p!=manifest]+[report]+learning)
d={'sealed_at_utc':datetime.now(timezone.utc).isoformat(),'scope':'48 broad ETF technical accounts; independent ledger/order review; official next-product preparation; report and learning deliverables','mutable_navigation_excluded':['AGENTS.md','docs/experiments/registry.json','docs/experiments/INDEX.md','docs/superpowers/plans/2026-09-08-broad-index-etf-research.md','live OKR database'],'files':{str(p.relative_to(R)):sha(p) for p in files}}
manifest.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
assert all(sha(R/p)==h for p,h in read(manifest)['files'].items())
assert str(report.relative_to(R)) in d['files']
assert str((B/'report-review.json').relative_to(R)) in d['files']
print(json.dumps({'sealed_files':len(files),'sha256':sha(manifest),'all_hashes_match':True,'report_review_manifest_dependency_closed':True},ensure_ascii=False))
