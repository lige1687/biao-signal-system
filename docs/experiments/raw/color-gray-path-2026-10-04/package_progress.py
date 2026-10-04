from pathlib import Path
import hashlib,json,subprocess,re
R=Path(__file__).resolve().parents[4];H=Path(__file__).resolve().parent
paths=['docs/research/definitions.v1.json','docs/experiments/registry.json','docs/experiments/INDEX.md','docs/experiments/color-gray-continuous-ranking-2026-10-05.md','docs/ops/work-progress/technical-factor-sequence.md','docs/progress/technical-factor-sequence.md']
paths += ['src/lei_signal/research/'+n+'.py' for n in ['question_contract','workflow','workflow_evaluation','workflow_inputs','color_history_information','bull_gray_origin_information','color_continuous_information','color_continuous_workflow','lightgbm_information']]
paths += ['tests/unit/test_'+n+'.py' for n in ['color_history_information','color_continuous_information','lightgbm_information']]
local=[]
for p in H.rglob('*'):
 if not p.is_file():continue
 rel=p.relative_to(H)
 if any(part.startswith('.') or part=='__pycache__' for part in rel.parts) or '.local.' in p.name or p.name.endswith('.local.json') or p.name.endswith('.local.md'):continue
 if p.name in ['manifest.json','SHA256SUMS','publish-paths.json','git-sync.json','package_progress.py']:continue
 if p.name in ['preflight.json','core-01-ledger.json'] or (p.name=='result.json' and p.parent.name=='core-01'):
  local.append({'path':str(p.relative_to(R)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'delivered':False,'reason':'full per-observation proof or fitted model parameters retained locally; no model weights uploaded'});continue
 if p.stat().st_size>1_000_000:raise ValueError('unexpected large delivery '+str(p))
 if p.suffix not in ['.json','.md','.py','.csv','.log','.jsonl','.txt']:continue
 paths.append(str(p.relative_to(R)))
for group in ['core','continuous']:
 for branch in ['ridge-forward_return','ridge-mae','lightgbm-forward_return','lightgbm-mae']:
  c=json.loads((H/group/branch/'accepted-01/contract.json').read_text());paths.append(c['publication']['report_path']);paths.append(c['history']['ledger_path'])
  for s in [c['data']]+c.get('sources',[]):
   p=R/s['path']
   if p.exists() and not any(x['path']==s['path'] for x in local):local.append({'path':s['path'],'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'delivered':False,'reason':'existing source inputs; obtain authorized exact bytes separately, no data export in this sync'})
paths=sorted(set(paths));items=[]
for path in paths:
 p=R/path;data=p.read_bytes()
 if len(data)>1_000_000:raise ValueError('oversize '+path)
 if re.search(rb'(?:sk-[A-Za-z0-9]{24,}|gh[pousr]_[A-Za-z0-9]{30,}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----)',data):raise ValueError('credential-shaped content '+path)
 items.append({'path':path,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'delivered':True})
manifest={'schema':'technical-progress-delivery/1.0','task':'technical-factor-sequence','base_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'branch':'codex/technical-factor-sequence-progress-20261004','scope':'32 fixed fits and saved diagnostics; actual datasets/full proofs/model parameters not exported','files':items,'local_only_required':local,'missing_inputs':['qualified market index panel','qualified historical stock members/identity/actions/tradability','actionable next-price/fees/limits for net portfolio'],'restore':'Read report, verify SHA256SUMS; saved predictions support remote read-only numerical audit. Exact full execution requires separately authorized local_only_required bytes and pinned native runtime; no cross-platform replay claimed.'}
(H/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');sums=''.join(x['sha256']+'  '+x['path']+'\n' for x in items);(H/'SHA256SUMS').write_text(sums)
paths += [str((H/n).relative_to(R)) for n in ['manifest.json','SHA256SUMS','package_progress.py']]
(H/'publish-paths.json').write_text(json.dumps(paths,indent=2)+'\n');print(json.dumps({'files':len(paths),'bytes':sum(x['bytes'] for x in items),'excluded':len(local)}))
