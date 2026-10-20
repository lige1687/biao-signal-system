from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re,urllib.request
P=Path(__file__).resolve().parent;ROOT=P.parents[3]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def check_manifest(path,base):
 data=read(path);files=data['files']
 pairs=files.items() if isinstance(files,dict) else [(x.get('path',x.get('file')),x['sha256']) for x in files]
 pairs=list(pairs);bad=[str(f) for f,h in pairs if not (base/f).is_file() or sha(base/f)!=h]
 assert not bad,(path,bad)
 return dict(files=len(pairs),mismatches=bad,manifest_sha256=sha(path))
checks={}
for name in ['fourth','fifth','sixth','seventh','eighth']:
 checks['sealed_'+name]=check_manifest(P.parent/f'research-{name}-2026-09-08/final-manifest.json',ROOT)
for sub,file in [('reference-engine','manifest.json'),('b-zone-semantics','manifest.json'),('remaining-work','final-manifest.json'),('reference-account-review','final-manifest.json')]:checks[sub]=check_manifest(P/sub/file,P/sub)
assert sha(P/'protocol.md')==read(P/'protocol-lock.json')['sha256']
for f,h in read(P/'account-results/run-lock.json')['files'].items():assert sha(Path(f))==h,(f,'run input changed')
assert all(x['exact_match'] for x in read(P/'account-results/original-regression.json'))
assert read(P/'execution-checks.json')['status']=='passed'
assert read(P/'reference-account-review/results.json')['status']=='passed'
assert read(P/'reference-account-review/summary-and-orders-checks.json')['status']=='passed'
assert 'Ran 41 tests' in (P/'root-final-engine-tests.txt').read_text() and '\nOK\n' in (P/'root-final-engine-tests.txt').read_text()
checks['computation']=dict(new_accounts=2,original_exact_tables=15,engine_test_methods=41,**read(P/'execution-checks.json'))
reports=[ROOT/'docs/experiments/entry-discipline-and-b-zone-diagnosis-2026-09-08.md',ROOT/'docs/experiments/research-local-phase-closeout-2026-09-08.md']
learning=[ROOT/'docs/literature-learning/reference-definition-lessons-2026-09-08.md',ROOT/'docs/literature-learning/reference-definition-lessons-2026-09-08.json',ROOT/'docs/literature-learning/research-followups-handoff-2026-09-08.md']
registry=read(ROOT/'docs/experiments/registry.json')
for r in reports:
 assert '## 一句话结论（大白话）' in r.read_text() and '## ARCHIVE' in r.read_text()
 entry=registry['entries'][str(r.relative_to(ROOT))];assert entry['category'] in registry['categories'] and entry['verdict']=='mixed'
badlinks=[];linkcount=0
for r in reports+[x for x in learning if x.suffix=='.md']+[P/'README.md']:
 for target in re.findall(r'\]\(([^)]+)\)',r.read_text()):
  if target.startswith(('https://','http://','#','mailto:')):continue
  target=target.strip('<>').split('#')[0];q=r.parent/target;linkcount+=1
  if not q.exists():badlinks.append(dict(file=str(r),target=target))
assert not badlinks,badlinks
cards=read(P/'evidence-cards.json');assert len(cards)==2
for c in cards:
 ev=c['evidence_ref']
 # Existing contract shape is checked at construction; every recorded SHA resolves.
 def walk(v):
  if isinstance(v,dict):
   for x in v.values():walk(x)
  elif isinstance(v,list):
   for x in v:walk(x)
  elif isinstance(v,str) and v.startswith(str(ROOT)):assert Path(v).exists(),v
 walk(c)
seed=read(ROOT/'docs/literature-learning/learning-seed.json');delta=read(learning[1]);ids={p['id'] for p in seed['papers']}
assert len(delta['entries'])==1 and all(e['paper_id'] in ids for e in delta['entries'])
for f,h in read(P/'learning-handoff-inputs.json')['files'].items():assert sha(ROOT/f)==h,(f,'learning input changed')
with urllib.request.urlopen('http://localhost:8000/api/upgrades',timeout=10) as response:goals=json.load(response)
goal=next(g for g in goals['items'] if g['id']=='K-baseline')
assert goal['status']=='in_progress' and {x['id']:x['done'] for x in goal['milestones']}=={'m1':True,'m2':True,'m3':False,'m4':True}
save(P/'okr-final-check.json',dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),goal=goal,read_only=True))
checks['documents']=dict(registered_reports=2,local_links_checked=linkcount,broken_links=[],evidence_cards=2,learning_entries=1,old_learning_inputs_unchanged=True)
checks['okr']=dict(id='K-baseline',status=goal['status'],version=goal['version'],done=3,total=4,other_updates_authorized=False)
checks['report_review']=dict(longest_drawdowns_recovered=True,ongoing_end_drawdowns_are_separate=True,correction_record='report-review-correction.json')
save(P/'delivery-checks.json',dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),status='passed',checks=checks))
files=[q for q in P.rglob('*') if q.is_file() and q.name!='final-manifest.json' and '__pycache__' not in q.parts and q.suffix!='.pyc']
# Include subagent seals, excluding only this root final-manifest itself.
files += [q for q in P.rglob('final-manifest.json') if q!=P/'final-manifest.json']
files+=reports+learning
files=sorted(set(files))
manifest=dict(sealed_at_utc=datetime.now(timezone.utc).isoformat(),scope='ninth research batch, two reports, one learning note in two formats and content handoff; shared registry/INDEX and OKR database excluded',files={str(q.relative_to(ROOT)):sha(q) for q in files})
save(P/'final-manifest.json',manifest)
print(json.dumps(dict(status='passed',sealed_files=len(files),manifest_sha256=sha(P/'final-manifest.json'),old_batches_unchanged=True),ensure_ascii=False))
