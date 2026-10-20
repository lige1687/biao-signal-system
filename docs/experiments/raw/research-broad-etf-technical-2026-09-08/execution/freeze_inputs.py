import hashlib,json
from datetime import datetime,timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
FILES=[ROOT/"protocol.md",ROOT/"protocol-lock.json",HERE/"engine.py",HERE/"metrics.py",HERE/"run_accounts.py",
       HERE/"test_engine.py",HERE/"verify_default_real.py",HERE/"inputs/execution-config.json",HERE/"inputs/actions.json",
       HERE/"inputs/action-coverage.json",HERE/"inputs/dated-restrictions.json",HERE/"inputs/price-limit-regimes.json",
       HERE/"inputs/exit-observations.json.gz",HERE/"inputs/source-candidates/precision-candidates.json.gz",
       HERE/"inputs/source-candidates/diagnostic-candidates.json",HERE/"inputs/bars/sh510300-nominal.csv",
       HERE/"inputs/bars/sz159915-nominal.csv"]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    lock={"created_at_utc":datetime.now(timezone.utc).isoformat(),"status":"before_new_returns",
          "files":{str(p.resolve()):sha(p) for p in FILES}}
    (HERE/"source-lock.json").write_text(json.dumps(lock,ensure_ascii=False,indent=2)+"\n")
if __name__=="__main__":main()
