from pathlib import Path
import json,hashlib,csv,gzip,re
P=Path(__file__).resolve().parent;R=P.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def verify(files,base):
 for name,h in files.items():
  f=Path(name);f=f if f.is_absolute() else base/f
  assert f.is_file(),str(f)
  assert sha(f)==h,str(f)
 return len(files)
out={}
for batch in ['fourth','fifth','sixth','seventh','eighth','ninth','tenth']:
 m=P.parent/f'research-{batch}-2026-09-08/final-manifest.json'
 out[batch+'_sealed_files_unchanged']=verify(read(m)['files'],R)
for f in ['repair-lock.json','runtime-audit-lock.json','history-diagnostic/run-lock.json','continuous-results/run-lock.json']:
 out[f]=verify(read(P/f)['files'],R)
initial=read(P/'initial-lock.json');out['production_source_files_unchanged']=verify(initial['production'],R)
assert sha(P/'protocol.md')==initial['protocol_sha256']
assert sha(P.parent/'research-tenth-2026-09-08/final-manifest.json')==initial['base_manifest_sha256']
mods=[k for k,h in initial['files'].items() if sha(P/k)!=h]
assert set(mods)==set(read(P/'repair-lock.json')['modified_files']) and len(mods)==4
s=read(P/'history-diagnostic/summary.json');assert s['all_checks']==366 and s['unique_check_dates']==122
assert all(m['passed']==122 and m['failed']==0 for m in s['modules'])
rows=list(csv.DictReader((P/'history-diagnostic/prefix-checks.csv').open()));assert len(rows)==366 and all(r['matched']=='True' for r in rows)
assert len({(r['symbol'],r['cutoff']) for r in rows})==122
assert read(P/'history-diagnostic/run-lock.json')['plan']==read(P.parent/'research-tenth-2026-09-08/history-diagnostic/run-lock.json')['plan']
assert json.loads(gzip.decompress((P/'history-diagnostic/differences.json.gz').read_bytes()))==[]
c=read(P/'continuous-results/summary.json');assert c['fund_dates']==42 and c['checks']==168 and c['failed']==0 and c['input_hashes_unchanged']
cr=list(csv.DictReader((P/'continuous-results/checks.csv').open()));assert len(cr)==168 and all(r['matched']=='True' for r in cr)
assert json.loads(gzip.decompress((P/'continuous-results/differences.json.gz').read_bytes()))==[]
assert '64 passed' in (P/'complete-regression-tests.txt').read_text()
assert '1 failed, 31 passed' in (P/'original-integration-tests.txt').read_text()
compare=read(P/'old-new-event-comparison.json');assert len(compare['restored_confirmations'])==4 and all(r['event_preserved'] for r in compare['restored_confirmations'])
assert [len(r['cross_version_changes']) for r in compare['restored_confirmations']]==[1,1,0,0]
assert not list(P.rglob('*.pyc'))
report=R/'docs/experiments/acd-repair-validation-2026-09-08.md'
assert '## 一句话结论（大白话）' in report.read_text() and '## ARCHIVE' in report.read_text()
for p in [report,R/'docs/literature-learning/repair-validation-lessons-2026-09-08.md']:
 for link in re.findall(r'\]\(([^)]+)\)',p.read_text()):
  if '://' not in link:assert (p.parent/link.split('#')[0]).exists(),link
reg=read(R/'docs/experiments/registry.json');k=str(report.relative_to(R));assert reg['entries'][k]['category'] in reg['categories'] and reg['entries'][k]['verdict']=='mixed'
assert report.name in (R/'docs/experiments/INDEX.md').read_text()
assert len(read(P/'evidence-cards.json'))==2
for row in read(P/'integrated-import-paths.json'):assert sha(Path(row['path']))==row['sha256']
for add in read(P/'test-dependency-lock.json')['added']:assert sha(Path(add['source']))==sha(Path(add['destination']))==add['sha256']
out.update(passed=True,fixed_history_checks=366,continuous_checks=168,regression_tests=64,modified_research_rules=4,full_return_comparison_complete=False)
(P/'delivery-check.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False))
