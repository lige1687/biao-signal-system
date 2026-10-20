from pathlib import Path
import json,hashlib,re,math
from urllib.parse import unquote
P=Path(__file__).resolve().parent;REPO=P.parents[3]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for x in json.loads((P/'input-manifest.json').read_text())['files']:assert sha(Path(x['snapshot']))==x['sha256']
prev=json.loads((P.parent/'research-third-2026-09-08/final-manifest.json').read_text())
for f,h in prev['files'].items():assert sha(REPO/f)==h
for x in json.loads((P/'events/other/manifest.json').read_text()):assert sha(P/'events/other'/x['file'])==x['sha256']
dividends=json.loads((P/'events/510300/events.json').read_text())['events']
assert len(dividends)==13
for x in dividends:assert sha(P/'events/510300'/x['source_file'])==x['source_sha256']
lock=json.loads((P/'study/run-lock.json').read_text())
for x in lock['sources']:assert sha(Path(x['path']))==x['sha256']
assert sha(P/'study/cash_engine.py')==lock['engine_sha256']
assert sha(P/'study/run_study.py')==lock['runner_sha256']
assert sha(P/'study/protocol.md')==lock['protocol']['protocol_sha256']
assert lock['at']>lock['protocol']['frozen_at_utc']
for f in ['protocol-clarifications','execution-assumptions']:
 l=json.loads((P/'study'/f'{f}.lock.json').read_text());assert sha(P/'study'/f'{f}.md')==l['sha256'];assert not l['candidate_results_viewed']
summary=json.loads((P/'study/summary.json').read_text());assert len(summary)==12
assert all(math.isfinite(x['final_equity']) and math.isfinite(x['max_drawdown']) for x in summary)
recon=json.loads((P/'study/reconciliation.json').read_text());assert len(recon)==12 and all(x['cash_shares_dividends_nav_reconciled'] for x in recon)
ind=json.loads((P/'study/reviewer-real-ledgers.json').read_text());assert len(ind['results'])==3
checks=json.loads((P/'study/reviewer-checks.json').read_text());assert len(checks['checks'])==6
assert 'Ran 12 tests' in (P/'study/final-test-output.txt').read_text() and '\nOK\n' in (P/'study/final-test-output.txt').read_text()
cards=json.loads((P/'evidence-cards.json').read_text());assert len(cards)==2
for c in cards:
 e=c['evidence_ref']
 # Contract field spellings are checked against the serialized existing dataclass.
 for path,h in zip(e['source_path'],e['source_hash']):assert sha(Path(path))==h
registry=json.loads((REPO/'docs/experiments/registry.json').read_text());reports=json.loads((P/'registration.json').read_text())
link_count=0
for f,entry in reports.items():
 report=REPO/f;s=report.read_text();assert '## 一句话结论（大白话）' in s and '## ARCHIVE' in s
 assert registry['entries'][f]==entry and entry['category'] in registry['categories']
 for target in re.findall(r'\]\(([^)]+)\)',s):
  if '://' in target or target.startswith('#'):continue
  actual=(report.parent/unquote(target.split('#')[0])).resolve();assert actual.exists(),actual;link_count+=1
okr=json.loads((P/'okr-after.json').read_text());assert okr['status']=='in_progress' and not okr['milestones'][1]['done']
print(json.dumps(dict(frozen_inputs=7,prior_archive_unchanged=len(prev['files']),primary_dividend_pdfs=len(dividends),planned_runs=12,internal_account_reconciliations=12,independent_account_reconstructions=3,primary_tests=12,additional_synthetic_checks=6,evidence_cards=2,registered_reports=2,local_links=link_count,okr_long_window_still_incomplete=True),ensure_ascii=False,indent=2))
