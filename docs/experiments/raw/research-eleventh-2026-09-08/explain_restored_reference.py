from pathlib import Path
import sys,types,json,gzip
from dataclasses import asdict
import diagnose_history as d
from lei_signal.rules.strict_structure import detect_strict_structures
P=Path(__file__).resolve().parent;O=P.parent/'research-tenth-2026-09-08'
legacy=types.ModuleType('phase11_reference_old_strict');sys.modules[legacy.__name__]=legacy
exec(compile((O/'research-package/src/lei_signal/rules/strict_structure.py').read_text(),'frozen_tenth_strict','exec'),legacy.__dict__)
bars,actions=d.load_inputs();raw=d.raw_asof('sh513100',bars,actions,'2022-01-12');traces=[]
for day in ['2015-12-29','2015-12-30','2015-12-31']:
 f=raw.loc[:day]
 for label,fn in [('old',legacy.detect_strict_structures),('fixed',detect_strict_structures)]:
  ss=[d.plain(asdict(s)) for s in fn(f) if s.side=='bottom' and '2015-12-28'<=s.confirmed_date.isoformat()<=day]
  traces.append(dict(as_of=day,implementation=label,structures=ss))
d.save(P/'restored-reference-investigation.json',dict(reason='Initial comparison wrongly required exact pre-repair source ID. Repair preserves first publication, so old Dec31 recalculation ID may differ from actual Dec30 published ID. Event stability within repaired implementation still compares all fields.',traces=traces))
print(json.dumps(traces,ensure_ascii=False,indent=2))
