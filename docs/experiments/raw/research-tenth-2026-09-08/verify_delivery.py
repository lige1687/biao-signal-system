from pathlib import Path
import json,hashlib,csv,gzip,re
P=Path(__file__).resolve().parent; R=P.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def check(files,base):
 for path,h in files.items():
  p=Path(path); p=p if p.is_absolute() else base/p
  assert p.is_file(),str(p)
  assert sha(p)==h,str(p)
 return len(files)
out={}
for batch in ['fourth','fifth','sixth','seventh','eighth','ninth']:
 p=P.parent/f'research-{batch}-2026-09-08/final-manifest.json'; j=read(p)
 out[batch+'_unchanged']=check(j['files'],R)
out['run_inputs_unchanged']=check(read(P/'history-diagnostic/run-lock.json')['files'],R)
out['original_copy_unchanged']=check(read(P/'source-lock.json')['files'],R)
for d in ['a-contract','a-review']:
 out[d+'_sealed_files']=check(read(P/d/'manifest.json'),P/d)
art=read(P/'cd-contract/artifact-manifest.json')
out['cd_sealed_files']=check({x['path']:x['sha256'] for x in art},P/'cd-contract')
for row in read(P/'source-lock.json')['added_from_current']:
 assert sha(Path(row['source']))==row['sha256']
assert sha(P/'protocol.md')==read(P/'protocol-lock.json')['sha256']
rows=list(csv.DictReader((P/'history-diagnostic/prefix-checks.csv').open()))
assert len(rows)==366
assert len({(r['symbol'],r['cutoff']) for r in rows})==122
bad=[r for r in rows if r['matched']=='False']; assert len(bad)==2 and all(r['module']=='A' for r in bad)
assert sum(int(r['removed_after_future']) for r in rows)==4
assert sum(int(r['added_after_future']) for r in rows)==2
assert sum(int(r['changed_after_future']) for r in rows)==0
assert {(r['symbol'],r['cutoff']) for r in bad}=={('sh513100','2015-12-31'),('sh518880','2022-12-30')}
dif=json.loads(gzip.decompress((P/'history-diagnostic/differences.json.gz').read_bytes())); assert len(dif)==6
s=read(P/'history-diagnostic/summary.json'); assert s['raw_event_records']==2987 and s['all_checks']==366
assert sum(x['raw_confirmed'] for x in s['modules'])==1366
assert read(P/'history-diagnostic/completion.json')['input_hashes_unchanged']
assert '20 passed' in (P/'a-contract/existing-tests.txt').read_text()
assert '10 passed' in (P/'cd-contract/existing-tests.txt').read_text()
assert not list(P.rglob('*.pyc'))
report=R/'docs/experiments/acd-information-qualification-2026-09-08.md'
for p in [report,R/'docs/literature-learning/event-time-lessons-2026-09-08.md']:
 for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
  if '://' not in target: assert (p.parent/target.split('#')[0]).exists(),target
assert '## 一句话结论（大白话）' in report.read_text() and '## ARCHIVE' in report.read_text()
r=read(R/'docs/experiments/registry.json'); key=str(report.relative_to(R)); assert r['entries'][key]['category'] in r['categories']
assert report.name in (R/'docs/experiments/INDEX.md').read_text()
assert len(read(P/'evidence-cards.json'))==2
out.update(checks=366,fund_date_pairs=122,changed_checkpoints=2,removed_confirmations=4,added_failures=2,passed=True)
(P/'delivery-check.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False))
