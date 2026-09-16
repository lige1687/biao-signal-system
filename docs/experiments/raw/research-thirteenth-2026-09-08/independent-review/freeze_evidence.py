"""Copy completed evidence once; hash source and accepted copies before independent review."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil
BASE=Path(__file__).resolve().parent;ROOT=BASE.parent;RAW=ROOT.parent
SNAP=BASE/'accepted'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
 assert not SNAP.exists(),'Never overwrite accepted snapshot.'
 cfgs=[c['id'] for c in json.loads((ROOT/'configurations.json').read_text())]
 required=[ROOT/'execution/account-results'/v/c/f for v in ('S','T') for c in cfgs for f in ('daily.csv','trades.csv','orders.json','events.json','roundtrips.json')]
 assert all(p.exists() for p in required),'Wait until all execution evidence is ready.'
 pairs=[(p,p.relative_to(ROOT)) for p in (ROOT/'execution').rglob('*') if p.is_file() and '__pycache__' not in str(p)]
 pairs.extend((ROOT/p,Path(p)) for p in ('protocol.md','configurations.json','initial-lock.json'))
 eighth=RAW/'research-eighth-2026-09-08';twelfth=RAW/'research-twelfth-2026-09-08'
 pairs.extend((p,Path('product-qualification')/p.relative_to(eighth/'product-qualification')) for p in (eighth/'product-qualification').glob('*.json'))
 pairs.extend((p,Path('product-qualification/bars-helper-native')/p.name) for p in (eighth/'product-qualification/bars-helper-native').glob('*.csv'))
 pairs.append((twelfth/'precision-fix/candidates.json.gz',Path('twelfth-candidates.json.gz')))
 pairs.extend((twelfth/'precision-account-results'/c/f,Path('twelfth-baseline')/c/f) for c in cfgs for f in ('daily.csv','trades.csv','orders.json','events.json','roundtrips.json'))
 old=twelfth/'independent-review/precision-addendum'
 pairs.extend((old/f,Path('frozen-checker-source')/f) for f in ('verify_accounts.py','verify_orders.py','verify_sources.py','verify_summaries.py','review-addendum-2026-09-08.md'))
 manifest=[]
 for source,rel in pairs:
  dest=SNAP/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
  manifest.append(dict(source=str(source.resolve()),file=str(rel),sha256=sha(source),bytes=source.stat().st_size))
 assert all(sha(Path(r['source']))==sha(SNAP/r['file'])==r['sha256'] for r in manifest)
 (BASE/'accepted-inputs.json').write_text(json.dumps(dict(accepted_at_utc=datetime.now(timezone.utc).isoformat(),files=manifest),indent=2,ensure_ascii=False)+'\n')
 print('Accepted unchanged evidence:',len(manifest),'files')
if __name__=='__main__':run()
