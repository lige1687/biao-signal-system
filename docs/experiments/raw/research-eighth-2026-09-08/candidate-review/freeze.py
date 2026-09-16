from pathlib import Path
import json,hashlib
from datetime import datetime,timezone
P=Path(__file__).resolve().parent;E=P.parent
inputs=[E/'generate_candidates.py',E/'protocol.md',E/'protocol-addendum-01.md',E/'product-qualification/actions.json',E/'product-qualification/price-helper/price_basis.py',E/'b-research-fix/manifest.json']
inputs+=list((E/'product-qualification/bars-helper-native').glob('*.csv'))
inputs+=[E/'candidate-study'/s for s in ['candidates.json.gz','candidates.csv','B-events.json.gz','summary.json','forward-checks.json','run-lock.json']]
inputs+=list((E/'b-research-fix/research-package').rglob('*.py'))+list((E/'b-research-fix/research-package/configs').glob('*.yaml'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(P/'input-manifest.json').write_text(json.dumps({'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(P/'protocol.md'),'files':[{'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(inputs)]},ensure_ascii=False,indent=2)+'\n')
print(len(inputs))
