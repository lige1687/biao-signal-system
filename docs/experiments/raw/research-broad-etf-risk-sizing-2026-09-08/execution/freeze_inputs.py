import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
H=Path(__file__).parent;R=H.parent
files=[R/'protocol.md',R/'protocol-lock.json',R/'prior-input-lock.json',H/'engine.py',H/'metrics.py',H/'run_accounts.py',H/'test_engine.py',H/'verify_real_default.py',H/'execution-config.json',H/'inputs/actions.json',H/'inputs/exit-observations.json.gz',H/'inputs/diagnostic-candidates.json',H/'inputs/bars/sh510300-nominal.csv',H/'inputs/bars/sz159915-nominal.csv']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(H/'source-lock.json').write_text(json.dumps({'created_at_utc':datetime.now(timezone.utc).isoformat(),'status':'before_new_returns','files':{str(p.resolve()):sha(p) for p in files}},indent=2)+'\n')
