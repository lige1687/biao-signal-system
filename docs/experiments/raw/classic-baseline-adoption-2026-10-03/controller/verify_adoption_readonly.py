from copy import deepcopy
from contextlib import ExitStack
from datetime import datetime
import hashlib,json
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo
from lei_signal.research import workflow as w, workflow_evaluation as e
from lei_signal.research.factor_lab import baseline_review as b
root=Path.cwd()
base=root/"docs/experiments/raw/classic-baseline-adoption-2026-10-03"
hand=json.loads((base/"controller/hand-example.json").read_text())
def reject(*a,**k): raise AssertionError("no fits in independent review")
checks={}
with ExitStack() as stack:
    for name in ("_ridge","_event","evaluate_observations"): stack.enter_context(patch.object(e,name,reject))
    for policy in ("equal_asset","equal_date"):
        c=deepcopy(hand["contract"]);c["weights"]["policy"]=policy
        r=b.build_baseline_review(c,hand["observations"],hand["predictions"])
        scores={x["model"]:x["mse"] for x in r["performance"]}
        expected=hand["independent_expected"][policy]
        assert all(abs(scores[k]-expected[k])<1e-12 for k in expected),(scores,expected)
        assert {x["asset"]:x["mean"] for x in r["training_means"]}=={"A":1.0,"B":10.0}
        changed=deepcopy(hand["observations"]);changed[2]["y"]=-99999
        assert b.build_baseline_review(c,changed,hand["predictions"])["performance"]==r["performance"]
        checks[policy]={"expected":expected,"actual":scores,"immature_label_ignored":True}
fixture=base/"executor-tests/round-03/test_real_cli_saved_receipt_an0/repo"
saved=fixture/"saved"
c=w.read_json(saved/"contract.json")
watch=[p for p in saved.rglob("*") if p.is_file()]+[w.family_ledger(fixture,c["history"]["family"]),fixture/"docs/experiments/registry.json",w.resolve_path(fixture,c["data"]["path"])]
def snap(): return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in watch}
before=snap()
with patch.object(e,"_ridge",reject),patch.object(e,"_event",reject),patch.object(w,"execute_workflow",reject):
    original=w.check_publication(saved,fixture)
    numerical=b.build_baseline_review(c,w.read_json(saved/"preflight.json")["observations"],w.read_json(saved/"result.json")["predictions"])
    cli=w.read_json(fixture/"cli-review/review.json")
    assert numerical["performance"]==cli["performance"]
    assert numerical["increments"]==cli["increments"]
    assert cli["source_verification"]=="workflow.check_publication"
    assert cli["data_mode"]=="synthetic" and cli["execution"]["fits"]==0
    assert original["evidence"]==cli["original_conclusion"]
assert before==snap()
report=(fixture/"cli-review/report.md").read_text()
assert "各ETF自己的历史平均" in report and "新增拟合：0" in report
print(json.dumps({"status":"passed_readonly_synthetic_acceptance","updated_at":datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),"hand_checks":checks,"saved_cli_results_recomputed":True,"source_files_unchanged":before,"original_conclusion":original["evidence"],"new_model_fits":0,"code_sha256":{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(b.__file__),root/"scripts/run_factor_lab.py"]},"limitations":["Executor real CLI passed; separate controller CLI output not attempted after confirmed ENOSPC","Controller check_publication and independent arithmetic completed with no file output","Synthetic evidence only; historical lifecycle dependencies missing","No market data, no new market fits, macOS only"]},ensure_ascii=False))
