"""Approved release helper. No DB/service operations. Dry-run by default.
Only run --apply after the controller coordinates the production update.
Rollback refuses to overwrite files changed since this candidate.
"""
import pathlib,json,hashlib,sys
O=pathlib.Path(__file__).resolve().parent;R=pathlib.Path('/Users/yongbiaoli/Desktop/lei-signal-lab')
rows=json.loads((O/'manifest.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
mode=sys.argv[1] if len(sys.argv)>1 else '--check'
assert mode in ['--check','--apply','--rollback']
for r in rows:
 assert sha(O/'candidate'/r['path'])==r['candidate_sha'],r['path']+' candidate drift'
 expect=r['candidate_sha'] if mode=='--rollback' else r['runtime_sha']
 assert sha(R/r['path'])==expect,r['path']+' runtime drift; STOP'
if mode!='--check':
 for r in rows:
  dest=R/r['path']
  if mode=='--rollback' and r['runtime_sha'] is None:dest.unlink()
  else:
   src=O/('before' if mode=='--rollback' else 'candidate')/r['path']
   dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(src.read_bytes())
print(json.dumps({'mode':mode,'files':len(rows),'all_preconditions_passed':True}))
