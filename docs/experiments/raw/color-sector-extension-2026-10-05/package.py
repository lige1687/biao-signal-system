from pathlib import Path
import json,hashlib,subprocess,datetime
from lei_signal.research.workflow import family_ledger
H=Path(__file__).resolve().parent;R=H.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
paths=[R/n for n in ['src/lei_signal/research/color_continuous_eight_etf.py','src/lei_signal/research/workflow.py','src/lei_signal/research/workflow_inputs.py','src/lei_signal/research/question_contract.py','tests/unit/test_color_continuous_eight_etf.py','docs/research/definitions.v1.json','docs/experiments/registry.json','docs/experiments/INDEX.md','docs/experiments/color-sector-increment-2026-10-05.md','docs/ops/work-progress/technical-factor-sequence.md','docs/progress/technical-factor-sequence.md']]
excluded=[]
for p in H.rglob('*'):
 if not p.is_file():continue
 if p.name in ['manifest.json','SHA256SUMS','publish-paths.local.json'] or p.name.startswith('coordination-') or p.name.startswith('.coord-'):continue
 rel=p.relative_to(H)
 if (any(n.startswith('.') or n=='__pycache__' for n in rel.parts) or '.local.' in p.name or p.name in ['preflight.json','core-01-ledger.json','manifest.json','SHA256SUMS','publish-paths.local.json'] or ('core-01' in rel.parts and p.name=='result.json')):
  excluded.append({'path':str(p.relative_to(R)),'bytes':p.stat().st_size,'sha256':sha(p),'delivered':False,'reason':'local input, model parameters, full observation proof or local coordination state; do not upload','recovery':'original task worktree material; independent remote access not provisioned'});continue
 if p.suffix not in ['.json','.md','.py','.csv','.log']:continue
 assert p.stat().st_size<2500000,(p,p.stat().st_size)
 assert p.suffix != ".json" or '"model_text"' not in p.read_text(),p
 paths.append(p)
for d in (H/'continuous').iterdir():
 if not d.is_dir():continue
 c=json.loads((d/'draft.json').read_text());paths.append(family_ledger(R,c['history']['family']));paths.append(R/c['publication']['report_path'])
paths=sorted(set(paths));entries=[{'path':str(p.relative_to(R)),'bytes':p.stat().st_size,'sha256':sha(p),'delivered':True} for p in paths]
manifest={'schema':'research-publication-manifest/1.0','question':'color-sector-extension-2026-10-05','base_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'work_branch':'codex/technical-factor-sequence-progress-20261004','files':entries,'not_delivered':excluded,'external_required_sources':json.loads((H/'source-manifest.json').read_text()),'closure':'bounded historical analysis completed; saved predictions and source hashes delivered; original source/model/preflight absent remotely','budget':{'real_fits':16,'previous_four_etf':32,'publication_real_fits':0},'created':datetime.datetime.now().astimezone().isoformat()}
put(H/'manifest.json',manifest)
(H/'SHA256SUMS').write_text(''.join(f"{e['sha256']}  {e['path']}\n" for e in entries)+f"{sha(H/'manifest.json')}  {(H/'manifest.json').relative_to(R)}\n")
paths += [H/'manifest.json',H/'SHA256SUMS'];put(H/'publish-paths.local.json',[str(p.relative_to(R)) for p in paths]);print('publish',len(paths),'bytes',sum(p.stat().st_size for p in paths),'excluded',len(excluded))
