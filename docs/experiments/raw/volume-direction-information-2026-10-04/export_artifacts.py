"""Copy own small evidence only; inventory large/local-only inputs explicitly."""
from pathlib import Path
import shutil,json,hashlib,re
R=Path(__file__).resolve().parents[4];D=R/'.codex/worktrees/price-volume-risk-delivery';N=Path(__file__).resolve().parent
families=['risk-shape-information-2026-10-03','risk-shape-error-decomposition-2026-10-04','session-composition-information-2026-10-04','volume-direction-information-2026-10-04']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
own_reports=[p for p in (R/'docs/experiments').glob('*.md') if p.name.startswith(('risk-shape-','session-composition-','volume-direction-'))]
for p in own_reports:shutil.copy2(p,D/p.relative_to(R))
for rel in ['docs/research/methods/factor-validation-guide.md','docs/archive/handoffs-plans/etf-price-volume-risk-direction-2026-10-03.md','docs/ops/work-progress/risk-shape-information.md']:
 p=R/rel;(D/rel).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,D/rel)
local=[];copied=[]
for family in families:
 folder=R/'docs/experiments/raw'/family
 for p in folder.rglob('*'):
  if not p.is_file() or '__pycache__' in p.parts:continue
  rel=p.relative_to(R);skip=p.name=='preflight.json' or p.stat().st_size>1_000_000 or p.name in ['workspace-before.json','original-shared-fingerprints.json'] or p.suffix not in ['.json','.jsonl','.md','.py','.csv','.txt','']
  if skip:
   local.append({'path':str(rel),'bytes':p.stat().st_size,'sha256':sha(p),'reason':'complete/large preflight or local-only context; restoration needed for original receipt checks'});continue
  (D/rel).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,D/rel);copied.append(str(rel))
# Frozen source code is audit data; formal adapters never import this archive.
# P2 exact bytes can be saved now; P1 shared blocks recovered only if original hash matches.
paths=['src/lei_signal/research/workflow.py','src/lei_signal/research/workflow_inputs.py','src/lei_signal/research/question_contract.py']
old=json.loads((N/'original-shared-fingerprints.json').read_text());snap=N/'frozen-code';snapshot_entries=[]
for mode,family in [('P2','volume-direction-information-2026-10-04'),('P1','session-composition-information-2026-10-04')]:
 c=json.loads((R/'docs/experiments/raw'/family/'run-main/contract.json').read_text())
 for rel,expected in c['bindings']['files'].items():
  if not rel.startswith(('src/','scripts/')) or not rel.endswith('.py'):continue
  p=R/rel;blob=p.read_bytes()
  if mode=='P1' and rel in paths:
   t=blob.decode()
   if rel.endswith('workflow_inputs.py'):needle="    if contract['feature']['kind'] == 'volume_direction_information':"
   elif rel.endswith('question_contract.py'):needle='    if feature["kind"] == "volume_direction_information":'
   else:needle='    if contract["feature"]["kind"] == "volume_direction_information"'
   # Delete own new-volume blocks, not neighboring old blocks.
   patterns=[needle]
   if rel.endswith('workflow.py'):patterns.append('    if c["feature"]["kind"] == "volume_direction_information":')
   for needle in patterns:
    while needle in t:
     a=t.index(needle);end=re.search(r'^    (?:if |[A-Za-z_][A-Za-z_0-9]* ?=|return |def )',t[a+len(needle):],re.M);assert end;z=a+len(needle)+end.start();t=t[:a]+t[z:]
   t=t.replace(', "volume_direction_information"','');blob=t.encode();assert hashlib.sha256(blob).hexdigest()==old[rel],rel
  actual=hashlib.sha256(blob).hexdigest()
  if actual!=expected:
   snapshot_entries.append({'study':mode,'path':rel,'expected':expected,'current':actual,'saved':False,'reason':'original bytes unavailable; do not claim old code restoration'});continue
  out=snap/mode/rel;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(blob);dst=D/out.relative_to(R);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(out,dst);snapshot_entries.append({'study':mode,'path':rel,'sha256':actual,'saved':True,'artifact':str(out.relative_to(R))})
# Market source bindings remain local: no quotations, action datasets, PDFs or databases uploaded.
c=json.loads((N/'run-main/contract.json').read_text())
for rel,h in c['bindings']['files'].items():
 if rel.startswith('docs/experiments/raw/') and rel not in copied and not rel.startswith(tuple('docs/experiments/raw/'+x+'/' for x in families)):
  p=R/rel;local.append({'path':rel,'bytes':p.stat().st_size,'sha256':h,'reason':'market/action source input or document; local only'})
inputpath=c['data']['path'];p=R/inputpath;local.append({'path':inputpath,'bytes':p.stat().st_size,'sha256':sha(p),'reason':'market panel input; local only'})
manifest={'inherited_base':'2ab565017a7a4959af744430339e32a09ce12667','branch':'codex/price-volume-risk-research-20261004','root_only_reports':[str(p.relative_to(R)) for p in own_reports],'small_evidence_paths':copied,'local_only_artifacts':local,'frozen_code_snapshot':snapshot_entries,'code_integration':'Only own3 kind blocks integrated on published baseline; source SHA differs from historical frozen current-main code. Snapshots archive exact proved bytes; no new market fit. Original contracts intentionally reject un-restored changed code/inputs.','new_market_fits':0}
(N/'git-handoff-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');shutil.copy2(N/'git-handoff-manifest.json',D/(N/'git-handoff-manifest.json').relative_to(R))
# Merge only own registry entries and human navigation lines, no unrelated shared-tree entries.
rel='docs/experiments/registry.json';a=json.loads((R/rel).read_text());b=json.loads((D/rel).read_text())
for p in own_reports:
 key=str(p.relative_to(R));b['entries'][key]=a['entries'][key]
(D/rel).write_text(json.dumps(b,ensure_ascii=False,indent=2)+'\n')
p=D/'docs/experiments/INDEX.md';t=p.read_text();lines=['- 2026-10-04：['+p.stem+']('+p.name+')' for p in own_reports if p.name not in t];p.write_text(t.replace('# docs/experiments 总索引\n','# docs/experiments 总索引\n\n'+'\n'.join(lines)+'\n',1))
print(json.dumps({'reports':len(own_reports),'small_evidence':len(copied),'local_only':len(local),'frozen_code_snapshots':sum(x['saved'] for x in snapshot_entries)},indent=2))
