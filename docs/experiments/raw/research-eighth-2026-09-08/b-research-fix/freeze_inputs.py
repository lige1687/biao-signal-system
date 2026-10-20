import ast,hashlib,json,shutil
from datetime import datetime,timezone
from pathlib import Path
P=Path(__file__).resolve().parent
OLD=P.parents[1]/'research-seventh-2026-09-08/rules-qualification'
BASE=OLD/'snapshot';DEST=P/'research-package';SRC=BASE/'src'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files={p.relative_to(SRC).with_suffix('').as_posix().replace('/','.') if p.name!='__init__.py' else p.parent.relative_to(SRC).as_posix().replace('/','.'):p for p in SRC.rglob('*.py')}
queue=['lei_signal.backtest.engine','lei_signal.rules.dense_breakout','lei_signal.rules.tradability_gate','lei_signal.features.indicators','lei_signal.features.pivots'];seen=set()
while queue:
 mod=queue.pop()
 if mod in seen or mod not in files:continue
 seen.add(mod);p=files[mod]
 for i in range(1,len(mod.split('.'))):queue.append('.'.join(mod.split('.')[:i]))
 for n in ast.walk(ast.parse(p.read_text())):
  if isinstance(n,ast.Import):queue.extend(a.name for a in n.names if a.name.startswith('lei_signal'))
  elif isinstance(n,ast.ImportFrom):
   prefix=n.module or ''
   if n.level:
    parent=mod.split('.') if p.name=='__init__.py' else mod.split('.')[:-1]
    prefix='.'.join(parent[:len(parent)-n.level+1]+([prefix] if prefix else []))
   if prefix.startswith('lei_signal'):
    queue.append(prefix);queue.extend(prefix+'.'+a.name for a in n.names)
paths=[files[m].relative_to(BASE) for m in sorted(seen)]
paths+=list(map(Path,['configs/rules.v1.yaml','configs/rules.v2.yaml']))
entries=[]
for rel in paths:
 a=BASE/rel;b=DEST/rel;b.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a,b)
 entries.append({'source':str(a),'copy':str(b.relative_to(P)),'bytes':a.stat().st_size,'sha256':sha(a),'kind':'runtime_dependency'})
for rel in ['src/lei_signal/backtest/service.py','src/lei_signal/backtest/runner.py','src/lei_signal/api/routes/backtest.py','docs/trading-spec-v1.md','AGENTS.md','.claude/skills/macd-reading/SKILL.md','docs/plan-sector-trend-page.md']:
 a=BASE/rel;b=P/'frozen-provenance'/rel;b.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a,b)
 entries.append({'source':str(a),'copy':str(b.relative_to(P)),'bytes':a.stat().st_size,'sha256':sha(a),'kind':'static_evidence'})
for rel in ['synthetic_checks.py','input-manifest.json','manifest.json','qualification.json','attempt-01/results.json','s02-age-diagnostic.json']:
 a=OLD/rel;b=P/'seventh-evidence'/rel;b.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a,b)
 entries.append({'source':str(a),'copy':str(b.relative_to(P)),'bytes':a.stat().st_size,'sha256':sha(a),'kind':'prior_evidence'})
obj={'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'before_research_edits':True,'protocol_sha256':sha(P/'protocol.md'),'files':entries,'runtime_modules':sorted(seen)}
(P/'source-manifest.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'runtime_modules':len(seen),'source_files':len(entries),'package':str(DEST)}))
