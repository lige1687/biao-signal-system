"""Materialize exact frozen research code for receipt verification and publication.
No active source, old contract, old result, old receipt, or family budget is changed.
"""
import hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
RAW=Path(__file__).resolve().parent
VERIFY=RAW/'verification-root'
c=json.loads((RAW/'run-joint/contract.json').read_text())
VERIFY.mkdir(exist_ok=False)
shutil.copytree(ROOT/'src/lei_signal',VERIFY/'src/lei_signal',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
q=Path('src/lei_signal/research/question_contract.py')
shutil.copyfile(RAW/'frozen-source-copy'/q,VERIFY/q)
paths=set(c['bindings']['files'])|{c['data']['path'],'docs/research/definitions.v1.json','docs/experiments/registry.json'}
# Include every card/profile evidence path needed by the registry validator.
reg=json.loads((ROOT/'docs/research/definitions.v1.json').read_text())
paths.update(reg['sources'])
def evidence_paths(value):
    if isinstance(value,dict):
        for key,item in value.items():
            if key in ('basis','tests') and isinstance(item,list):
                paths.update(v for v in item if isinstance(v,str) and (ROOT/v).is_file())
            else:evidence_paths(item)
    elif isinstance(value,list):
        for item in value:evidence_paths(item)
evidence_paths(reg)
# Bind the same shared attempt ledger, preserving every actual prior run/cost.
paths.add(c['history']['ledger_path'])
for ledger in (ROOT/'docs/experiments/raw/research-workflow-ledgers-2026-09-29').glob('*/attempts.jsonl'):
 paths.add(str(ledger.relative_to(ROOT)))
for name in sorted(paths):
 p=Path(name)
 if p.is_absolute():continue
 source=ROOT/p;target=VERIFY/p
 if target.exists():continue
 target.parent.mkdir(parents=True,exist_ok=True)
 if name=='scripts/run_factor_lab.py':shutil.copyfile(source,target)
 else:target.symlink_to(source)
for ident in ('joint','amplitude','serial','factor_only'):
 c=json.loads((RAW/f'run-{ident}/contract.json').read_text())
 report=VERIFY/c['publication']['report_path'];report.parent.mkdir(parents=True,exist_ok=True)
 report.symlink_to(ROOT/c['publication']['report_path'])
 for name,sha in c['bindings']['files'].items():
  p=Path(name) if Path(name).is_absolute() else VERIFY/name
  assert hashlib.sha256(p.read_bytes()).hexdigest()==sha,name
record=dict(root=str(VERIFY),all_frozen_file_hashes_match=True,source_copy='exact frozen bytes including recovered single unrelated EMA spelling',
 shared_writes_only=['existing family ledger records for zero-fit reaggregation','new authorized generated reports and existing experiment registry'],
 no_old_artifact_changed=True,no_active_source_changed=True)
(RAW/'verification-root-manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print(record)
