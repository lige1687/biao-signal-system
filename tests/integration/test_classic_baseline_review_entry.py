"""One real synthetic receipt, real CLI, immutable originals, zero review fits."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

from lei_signal.research import workflow as w
from lei_signal.research import workflow_evaluation as evaluation
from lei_signal.research.factor_lab import baseline_review

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts/run_factor_lab.py"


def test_real_cli_saved_receipt_and_failure_pairs(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("review_entry_fixture", Path(__file__).with_name("test_research_workflow_entry.py"))
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    assert Path(w.__file__).resolve().is_relative_to(ROOT / "src")
    assert Path(baseline_review.__file__).resolve().is_relative_to(ROOT / "src")
    root, c, _, _ = fixture.setup_case(tmp_path, family="baseline-review-engineering-only")
    # This test owns a synthetic definition; the publication catalog's missing
    # historical evidence is not replaced or represented as verified A01 data.
    registry_path = root/"docs/research/definitions.v1.json"
    registry = w.read_json(registry_path)
    test_name = "tests/integration/test_classic_baseline_review_entry.py"
    card = {"id":"synthetic.test.sma_distance", "version":"1.0.0",
        "name":"合成工具验收用均线距离", "type":"feature", "uses":["diagnostic"], "not_for":[],
        "scope":"synthetic engineering test only; no market or production claim",
        "definition":{"formula":"100 * (close / previous close - 1)", "parameters":{"lookback":1}, "endpoints":"current and preceding synthetic quote", "unit":"percentage_point", "direction":"signed distance", "transforms":"none"},
        "input":{"fields":["close"],"price_basis":"synthetic close","currency":"synthetic","frequency":"daily","calendar":"artificial weekdays"},
        "universe":{"version":"synthetic/1","eligibility":"synthetic quoted rows only","warmup":"two quotes","missing":"reject","quality_gate":"controlled workflow","degrade":"no market inference"},
        "time":{"observation_time":"synthetic quote close","available_at":"synthetic quote close","decision_at":"engineering only","execution_at":"none","timezone":"Asia/Shanghai","effective_from":"2022-01-03"},
        "dependencies":[],
        "validation":{"method":"engineering boundaries only","tolerance":{"absolute":1e-12,"relative":1e-10,"integer":0},"tests":[test_name],"limitations":"not a market factor study"},
        "status":{"definition_clarity":"synthetic_only","data_qualification":"synthetic_only","implementation":"engineering_fixture","effectiveness":"not_evaluated_for_market","production":"not_authorized"},
        "sources":["synthetic_test"],"lifecycle":{"state":"exists","basis":[test_name]}}
    fixture.dump(registry_path,{"schema_version":"1.0.0","version":"1.3.0","standard":registry["standard"],"standard_version":registry["standard_version"],"profiles":{},"sources":{"synthetic_test":{"path":test_name,"sha256":w.file_hash(Path(__file__))}},"objects":[card],"models":[]})
    c["question"]["factor_refs"]=["synthetic.test.sma_distance@1.0.0"]
    c["question"]["added_information"]="合成均线距离工具验收，不代表真实市场有效性"
    fit_count = 0
    original = evaluation._ridge
    def counting(*args, **kwargs):
        nonlocal fit_count
        fit_count += 1
        return original(*args, **kwargs)
    monkeypatch.setattr(evaluation, "_ridge", counting)
    path = fixture.frozen_path(root, c)
    rehearsal_fits = fit_count
    assert rehearsal_fits == 2
    saved = root / "saved"
    w.execute_workflow(path, saved, root=root)
    assert fit_count == 4  # two rehearsal and two saved synthetic model fits
    (tmp_path / "fit-count.json").write_text(json.dumps({"synthetic_setup_fits":fit_count,"synthetic_rehearsal_fits":rehearsal_fits,"synthetic_saved_run_fits":fit_count-rehearsal_fits,"market_fits":0,"auxiliary_review_fits":0}))
    def forbidden(*args, **kwargs):
        raise AssertionError("review must not fit or execute a research run")
    monkeypatch.setattr(evaluation, "_ridge", forbidden)
    monkeypatch.setattr(evaluation, "_event", forbidden)
    monkeypatch.setattr(w, "execute_workflow", forbidden)
    watched = list(saved.rglob("*")) + [w.family_ledger(root, c["history"]["family"]), root / "docs/experiments/registry.json"]
    def snapshot():
        return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in watched if p.is_file()}
    before = snapshot()
    saved_members = sorted(str(p.relative_to(saved)) for p in saved.rglob("*"))
    direct = baseline_review.review_saved_run(saved, root / "direct-review", root=root)
    assert direct["execution"]["fits"] == 0 and fit_count == 4
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    # The new process explicitly confirms the imported code belongs to this tree.
    probe = subprocess.run([sys.executable,"-c","from pathlib import Path; from lei_signal.research.factor_lab import baseline_review; print(Path(baseline_review.__file__).resolve())"], env=env, cwd=ROOT, capture_output=True, text=True)
    assert probe.returncode == 0 and Path(probe.stdout.strip()).is_relative_to(ROOT / "src")
    def cli(out, *extras):
        return subprocess.run([sys.executable,str(CLI),"--review-baselines",str(saved),"--review-root",str(root),"--out",str(out),*extras],env=env,cwd=ROOT,capture_output=True,text=True)
    out = root / "cli-review"
    success = cli(out)
    assert success.returncode == 0, success.stderr
    review = json.loads((out / "review.json").read_text())
    assert review["performance"] == direct["performance"]
    assert {x["model"] for x in review["performance"]} == {"B0","B1","B2","asset_training_mean"}
    assert review["source_verification"] == "workflow.check_publication"
    assert review["original_run_id"] == w.read_json(saved / "receipt.json")["run_id"]
    assert review["original_conclusion"] == c["publication"]["conclusion"]
    assert review["data_mode"] == "synthetic" and review["execution"]["fits"] == 0
    assert "## 一句话结论（大白话）" in (out / "report.md").read_text()
    assert before == snapshot()
    assert saved_members == sorted(str(p.relative_to(saved)) for p in saved.rglob("*"))
    rejections = []
    for name, destination, extras in [("existing",out,()),("inside",saved/"review",()),("register",root/"bad-register",("--register-report",)),("reuse",root/"bad-reuse",("--reuse-predictions",str(saved)))]:
        result=cli(destination,*extras)
        rejections.append({"case":name,"exit":result.returncode,"stderr":result.stderr})
        assert result.returncode != 0
        if name != "existing": assert not destination.exists()
    for name in ("result.json", "receipt.json"):
        artifact=saved/name; original_bytes=artifact.read_bytes()
        # Missing receipt and altered result must fail the existing verification.
        if name == "receipt.json": artifact.rename(saved/"receipt-unavailable.json")
        else:
            changed=w.read_json(artifact); changed["predictions"][0]["B2"] += 1;fixture.dump(artifact,changed)
        rejected=cli(root / ("bad-"+name))
        rejections.append({"case":name,"exit":rejected.returncode,"stderr":rejected.stderr})
        assert rejected.returncode == 3 and not (root / ("bad-"+name)).exists()
        if name == "receipt.json": (saved/"receipt-unavailable.json").rename(artifact)
        else: artifact.write_bytes(original_bytes)
    source=root/w.CODE_PATHS[0];original_bytes=source.read_bytes();source.write_bytes(original_bytes+b"\n# changed\n")
    stale=cli(root/"stale-source")
    rejections.append({"case":"stale-code","exit":stale.returncode,"stderr":stale.stderr})
    assert stale.returncode == 3 and not (root/"stale-source").exists()
    source.write_bytes(original_bytes)
    wrong_mode=subprocess.run([sys.executable,str(CLI),"--protocol",str(path),"--review-root",str(root),"--out",str(root/"wrong-mode")],env=env,cwd=ROOT,capture_output=True,text=True)
    assert wrong_mode.returncode != 0 and not (root/"wrong-mode").exists()
    rejections.append({"case":"review-root-other-mode","exit":wrong_mode.returncode,"stderr":wrong_mode.stderr})
    (tmp_path/"rejections.json").write_text(json.dumps(rejections,ensure_ascii=False,indent=2))
    ledger = w.family_ledger(root, c["history"]["family"])
    hidden = ledger.with_name("temporarily-unavailable.jsonl")
    ledger.rename(hidden)
    missing_ledger = cli(root/"missing-journal")
    assert missing_ledger.returncode == 3 and not ledger.exists() and not (root/"missing-journal").exists()
    hidden.rename(ledger)
    registry = root/"docs/experiments/registry.json"
    registry_bytes = registry.read_bytes()
    original_check = w.check_publication
    def changed_during_check(*args, **kwargs):
        state = original_check(*args, **kwargs)
        registry.write_bytes(registry_bytes + b"\n")
        return state
    with monkeypatch.context() as guarded:
        guarded.setattr(w,"check_publication",changed_during_check)
        import pytest
        with pytest.raises(ValueError,match="changed during"):
            baseline_review.review_saved_run(saved,root/"changed-during-check",root=root)
    assert not (root/"changed-during-check").exists()
    registry.write_bytes(registry_bytes)
    assert before == snapshot() and fit_count == 4
