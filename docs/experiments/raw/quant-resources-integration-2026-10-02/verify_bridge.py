"""One recorded integration batch: fixtures plus existing archived predictions."""
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
RAW = Path(__file__).resolve().parent
SCRIPTS = ROOT / ".agents/skills/lei-quant-tools/scripts"
sys.path.insert(0, str(SCRIPTS))
import quant_tools
import workflow_bridge

checks = []


def check(name, actual, expected, tolerance=1e-10):
    passed = abs(actual - expected) < tolerance if isinstance(expected, float) else actual == expected
    checks.append({"name": name, "actual": actual, "expected": expected, "passed": passed})
    if not passed:
        raise AssertionError(name)


def must_reject(name, call):
    try:
        call()
    except (ValueError, KeyError, TypeError, OSError):
        rejected = True
    else:
        rejected = False
    check(name, rejected, True)


dates = ["2026-03-02", "2026-03-03", "2026-03-04"]
contract = {"question": {"sampling": "daily", "primary_metric": {"name": "RMSE"}},
            "target": {"kind": "forward_return", "unit": "percentage_point"},
            "weights": {"policy": "equal_asset", "comparison": "fixed_common"},
            "dependence": {"block_length": 1, "draws": 2, "seed": 0, "axis_scope": "evaluation"},
            "calendar": dates, "universe": {"assets": ["A", "B"]},
            "split": {"label_policy": "purge", "folds": [{"train_end": "2026-02-27", "eval_start": dates[0], "eval_end": dates[-1]}]}}
rows = [{"id": f"{asset}|{d}", "asset": asset, "date": d, "fold": "0", "y": 0.,
         "label_end": d, "B0": 1., "B1": 2., "B2": value}
        for d, value in zip(dates, [1., 2., 3.]) for asset in ("A", "B")]
proof = {"observations": [{**r, "features": {}, "eligible": True, "stratum": f"{r['asset']}|2026",
                           "label_reason": None, "tested_condition": None} for r in rows]}
result = {"predictions": rows}
summary, packet = workflow_bridge.prepare_workflow_input(contract, result, proof)
check("complete_daily_panel_ready", summary["status"], "ready")
check("independent_paired_daily_losses", [r["difference"] for r in packet["observations"]], [3., 0., -5.])
check("unit_remains_squared_not_RMSE", summary["unit"], "percentage_point_squared")
check("positive_is_improvement", summary["paired_scores"]["improvement"], -2 / 3)
gap = {"predictions": [r for r in rows if r["date"] != dates[1]]}
s, p = workflow_bridge.prepare_workflow_input(contract, gap, proof)
check("missing_date_prevents_packet", p, None)
check("missing_date_identified", s["missing_dates"], [dates[1]])
unequal = {"predictions": rows[:-1]}
s, p = workflow_bridge.prepare_workflow_input(contract, unequal, proof)
check("unequal_asset_pool_prevents_packet", p, None)
check("unequal_pool_identified", s["incomplete_asset_dates"], {dates[-1]: ["A"]})
changed = copy.deepcopy(result);changed["predictions"][0]["y"] = 4
must_reject("changed_target_identity", lambda: workflow_bridge.prepare_workflow_input(contract, changed, proof))
other_frequency = copy.deepcopy(contract);other_frequency["question"]["sampling"] = "weekly"
check("weekly_not_silently_daily", workflow_bridge.prepare_workflow_input(other_frequency, result, proof)[1], None)
other_scope = copy.deepcopy(contract);other_scope["dependence"]["axis_scope"] = "full"
check("unsupported_original_axis_not_reinterpreted", workflow_bridge.prepare_workflow_input(other_scope, result, proof)[1], None)
wrong_calendar = copy.deepcopy(contract);wrong_calendar["calendar"] = list(reversed(dates))
must_reject("unordered_calendar_rejected", lambda: workflow_bridge.prepare_workflow_input(wrong_calendar, result, proof))

run = ROOT / "docs/experiments/raw/double-ma-order-information-2026-10-01/core-01"
before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in run.iterdir() if p.is_file()}
full, absent = workflow_bridge.inspect_workflow(run)
check("real_full_period_refused", full["status"], "not_applicable")
check("real_full_period_42_missing_dates", len(full["missing_dates"]), 42)
check("real_full_period_no_packet", absent, None)
(RAW / "real-full-readiness.json").write_text(json.dumps(full, ensure_ascii=False, indent=2) + "\n")
part, packet = workflow_bridge.inspect_workflow(run, start="2025-01-02", end="2025-12-02")
check("explicit_auxiliary_period_ready", part["status"], "ready")
check("real_rows", part["prediction_rows"], 888)
check("real_dates", part["prediction_dates"], 222)
check("real_assets", len(part["assets"]), 4)
hac = quant_tools.mean_hac({**packet, "nlags": 20})

# Independent scalar arithmetic on raw archived values, not bridge output.
saved = json.loads((run / "result.json").read_text())["predictions"]
selected = [r for r in saved if "2025-01-02" <= r["date"] <= "2025-12-02"]
old = statistics.fmean((r["B1"] - r["y"]) ** 2 for r in selected)
new = statistics.fmean((r["B2"] - r["y"]) ** 2 for r in selected)
daily = []
for day in sorted({r["date"] for r in selected}):
    same_day = [r for r in selected if r["date"] == day]
    daily.append(statistics.fmean((r["B1"]-r["y"])**2 - (r["B2"]-r["y"])**2 for r in same_day))
mean = statistics.fmean(daily)
centered = [v-mean for v in daily]
scalar_sum = sum(v*v for v in centered)
for lag in range(1, 21):
    scalar_sum += 2 * (1-lag/21) * sum(centered[i]*centered[i-lag] for i in range(lag, len(centered)))
check("real_old_score_independent", part["paired_scores"]["baseline"], old)
check("real_new_score_independent", part["paired_scores"]["candidate"], new)
check("real_improvement_independent", hac["mean_difference"], old-new)
check("real_standard_error_independent", hac["mean_standard_error"], math.sqrt(scalar_sum/len(daily)**2))
part["hac"] = hac
(RAW / "real-explicit-period.json").write_text(json.dumps(part, ensure_ascii=False, indent=2) + "\n")

# Corrupt only a synthetic local fixture; the archived source remains untouched.
fixture = RAW / "bad-receipt-fixture";fixture.mkdir(exist_ok=True)
for name, value in (("contract.json", {}), ("result.json", {}), ("preflight.json", {}),
                    ("receipt.json", {"schema_version": "workflow-receipt/1.0", "contract_sha256": "wrong"})):
    (fixture / name).write_text(json.dumps(value) + "\n")
must_reject("bad_receipt_refused", lambda: workflow_bridge.read_archived_run(fixture))
cli = subprocess.run([sys.executable, str(SCRIPTS / "quant_tools.py"), "workflow-hac", str(run),
                      "--start", "2025-01-02", "--end", "2025-12-02", "--nlags", "20"],
                     capture_output=True, text=True)
check("real_bridge_cli", cli.returncode, 0)
check("real_bridge_cli_matches", json.loads(cli.stdout)["hac"]["mean_difference"], mean)
blocked_cli = subprocess.run([sys.executable, str(SCRIPTS / "quant_tools.py"), "workflow-hac", str(run),
                              "--nlags", "20"], capture_output=True, text=True)
check("unqualified_full_period_cli_refused", blocked_cli.returncode, 2)
check("unqualified_cli_has_no_estimate", json.loads(blocked_cli.stdout)["hac"], None)
after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in run.iterdir() if p.is_file()}
check("archived_source_unchanged", after, before)

output = {"checks": checks, "passed": sum(c["passed"] for c in checks), "total": len(checks),
          "real_auxiliary_result": part, "new_fits": 0, "new_market_observations": 0}
(RAW / "checks.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
manifest = json.loads((RAW / "manifest.json").read_text())
manifest["tests"][-1].update(status="passed", result="checks.json", checks=len(checks))
(RAW / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"passed": output["passed"], "total": len(checks), "real_subperiod": part["paired_scores"],
                  "hac_standard_error": hac["mean_standard_error"]}, ensure_ascii=False))
