from pathlib import Path
import json,subprocess,os,sys,hashlib
root=Path.cwd(); base=root/"docs/experiments/raw/classic-baseline-adoption-2026-10-03"
p=base/"controller/write-check.json"
p.write_text(json.dumps({"reason":"retry after observed available capacity recovered from 108MiB to 1.1GiB","scope":"small acceptance output only"}))
fixture=base/"executor-tests/round-03/test_real_cli_saved_receipt_an0/repo"
from lei_signal.research import workflow as w
saved=fixture/"saved"; c=w.read_json(saved/"contract.json")
paths=[p for p in saved.rglob("*") if p.is_file()]+[w.family_ledger(fixture,c["history"]["family"]),fixture/"docs/experiments/registry.json",w.resolve_path(fixture,c["data"]["path"])]
def snap():return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
before=snap()
out=base/"controller/cli-review"
cmd=[sys.executable,"scripts/run_factor_lab.py","--review-baselines",str(saved.relative_to(root)),"--review-root",str(fixture.relative_to(root)),"--out",str(out.relative_to(root))]
r=subprocess.run(cmd,env={**os.environ,"PYTHONPATH":str(root/"src"),"PYTHONDONTWRITEBYTECODE":"1"},capture_output=True,text=True)
assert r.returncode==0,(r.returncode,r.stdout,r.stderr)
review=w.read_json(out/"review.json"); assert review["performance"]==w.read_json(fixture/"cli-review/review.json")["performance"]
assert review["execution"]["fits"]==0 and review["data_mode"]=="synthetic"
assert before==snap()
print(json.dumps({"status":"passed","command":cmd,"exit_code":r.returncode,"source_files_unchanged":True,"data_mode":review["data_mode"],"fits":0,"stdout":r.stdout,"stderr":r.stderr,"review_json_sha256":hashlib.sha256((out/"review.json").read_bytes()).hexdigest(),"report_sha256":hashlib.sha256((out/"report.md").read_bytes()).hexdigest()},ensure_ascii=False))
