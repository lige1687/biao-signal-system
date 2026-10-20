import json,hashlib,shutil
from pathlib import Path
from datetime import datetime,timezone
P=Path(__file__).resolve().parent;E=P.parents[1]/'research-eighth-2026-09-08';sources=[]
for name,root in [('sync',Path('/Users/yongbiaoli/lei-signal-sync')),('desktop',Path('/Users/yongbiaoli/Desktop/lei-signal-lab'))]:
 for rel in ['AGENTS.md','docs/trading-spec-v1.md','configs/rules.v1.yaml','configs/rules.v2.yaml','src/lei_signal/rules/dense_breakout.py']:
  a=root/rel;b=P/'sources'/name/rel;b.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a,b);sources.append((a,b))
for a in list((E/'b-research-fix/research-package').rglob('*.py'))+list((E/'b-research-fix/research-package/configs').glob('*.yaml')):
 sources.append((a,None))
for rel in ['candidate-review/B-six-events.json','candidate-review/selected-target-checks.json','candidate-review/review-2026-09-08.md','candidate-study/B-events.json.gz','product-qualification/bars-helper-native/sh518880-nominal.csv','product-qualification/actions.json','b-research-fix/manifest.json','candidate-review/manifest.json']:
 sources.append((E/rel,None))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=[{'source':str(a),'copy':str(b.relative_to(P)) if b else None,'sha256':sha(a),'bytes':a.stat().st_size} for a,b in sources]
rows += [{'source':str(p.resolve()),'copy':str(p.relative_to(P)),'sha256':sha(p),'bytes':p.stat().st_size,'historical_git_object_copy':True} for p in (P/'sources').glob('*') if p.is_file()]
(P/'input-manifest.json').write_text(json.dumps({'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(P/'protocol.md'),'clarification_sha256':sha(P/'protocol-clarification-01.md'),'files':rows},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'frozen_files':len(rows),'both_live_v1_equal':sha(P/'sources/sync/docs/trading-spec-v1.md')==sha(P/'sources/desktop/docs/trading-spec-v1.md'),'both_live_v2_yaml_equal':sha(P/'sources/sync/configs/rules.v2.yaml')==sha(P/'sources/desktop/configs/rules.v2.yaml')}))
