"""Create an additional input snapshot, retaining the first review byte-for-byte."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,hashlib
BASE=Path(__file__).resolve().parent;FIRST=BASE.parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--accounts',type=Path,required=True);parser.add_argument('--candidates',type=Path,required=True);parser.add_argument('--precision-source',type=Path,required=True);args=parser.parse_args()
 original=json.loads((FIRST/'first-review-seal.json').read_text())
 assert all(sha(FIRST/p)==h for p,h in original['files'].items()),'First review changed'
 assert (args.accounts/'completion.json').exists()
 target=BASE/'accepted';assert not target.exists()
 # Keep the original-source snapshots; replace only the revised account files and candidate serialization.
 lock=json.loads((FIRST/'accepted-inputs.json').read_text())
 pairs={r['file']:Path(r['source']) for r in lock['files'] if not r['file'].startswith('account-results/')}
 pairs['adapter/candidates.json.gz']=args.candidates
 for p in args.accounts.rglob('*'):
  if p.is_file():pairs[str(Path('account-results')/p.relative_to(args.accounts))]=p
 for p in args.precision_source.rglob('*'):
  if p.is_file() and '__pycache__' not in str(p):pairs[str(Path('precision-fix')/p.relative_to(args.precision_source))]=p
 manifest=[]
 for rel,source in sorted(pairs.items()):
  data=source.read_bytes();dest=target/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
  manifest.append(dict(source=str(source.resolve()),file=rel,sha256=sha(source),bytes=len(data)))
 (BASE/'accepted-inputs.json').write_text(json.dumps(dict(accepted_at_utc=datetime.now(timezone.utc).isoformat(),first_review_seal_sha256=sha(FIRST/'first-review-seal.json'),files=manifest),ensure_ascii=False,indent=2)+'\n')
 print('Additional snapshot:',len(manifest),'files; original review unchanged')

if __name__=='__main__':main()
