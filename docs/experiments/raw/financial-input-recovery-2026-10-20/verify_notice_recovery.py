"""Apply only independently accepted annotations to a NEW source diagnostic."""
import csv
import hashlib
import importlib.util
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
OLD = HERE.parent / "lowfreq-profitability-increment-2026-10-19"
sys.path.insert(0, str(ROOT / "src"))
from lei_signal.research.output_storage import recheck_saved_plan, _still_mounted


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, data):
    with Path(path).open("x") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")

run_contract = json.loads((HERE / "source-recovery-contract.json").read_text())
assert run_contract["mode"] == "source_qualification_only"
assert run_contract["market_effects_allowed"] == 0
for binding in run_contract["bindings"].values():
    assert sha(binding["path"]) == binding["sha256"]
assert Path(run_contract["bindings"]["runner"]["path"]).resolve() == Path(__file__).resolve()

approval = json.loads((HERE / "review-reconciliation.json").read_text())
assert approval["root_accepted"] is True
for binding in approval["bindings"].values():
    assert sha(binding["path"]) == binding["sha256"]
new_review = json.loads((HERE / "controller-notice-review-v2.json").read_text())
assert len(new_review["decisions"]) == 14 and len(new_review["held_outside_applied_decisions"]) == 6
spec = importlib.util.spec_from_file_location("unchanged_archived_selector", OLD / "build_financial_panel.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
contract = json.loads((OLD / "source-panel-final-01-contract.json").read_text())
bound = contract["inputs"]
assert sha(bound["runner"]["path"]) == bound["runner"]["sha256"]
assert sha(bound["parser"]["path"]) == bound["parser"]["sha256"]
progress, prep, controller, old_review = (module.json_bound(bound[k]) for k in
                                         ("progress", "preparation", "controller_review", "notice_review")) if not isinstance(bound["preparation"], list) else (
    module.json_bound(bound["progress"]), module.json_bound(bound["preparation"][0]),
    module.json_bound(bound["controller_review"]), module.json_bound(bound["notice_review"]))
review = {**new_review, "decisions": old_review["decisions"] + new_review["decisions"]}
codes = sorted({d["cohort_code"] for d in new_review["decisions"]})
records = module.expected_index(progress, codes)
module.merge_preparation(records, [{**prep, "documents": [d for d in prep["documents"]
                                                       if d["cohort_code"] in codes]}])
coverage = module.catalog_coverage(progress, codes)
old_events = module.events_for(records, controller, old_review)
new_events = module.events_for(records, controller, review)
by_code = {code: {key: row for key, row in records.items() if key[0] == code} for code in codes}
packet = json.loads((HERE / "review-packet.json").read_text())
audit = module.json_bound(packet["source_bindings"]["audit"])
assert len(audit) == 600 * 132
feasible = json.loads((HERE / "local-feasibility.json").read_text())
price_path = Path(feasible["p4_saved_panel"]["path"])
assert sha(price_path) == feasible["p4_saved_panel"]["sha256"]
# Select only eligibility keys; no numeric future outcome value is read into
# the analysis. This is a source recovery, not a market performance study.
eligible = {}
with price_path.open() as stream:
    reader = csv.reader(stream)
    header = next(reader)
    positions = [header.index(key) for key in ("month", "code", "eligibility_reason")]
    for raw in reader:
        month, code, reason = [raw[i] for i in positions]
        eligible[(month, code)] = reason == "eligible"
changes, checked, unchanged_qualified = [], 0, 0
summary = defaultdict(lambda: Counter())
recovered_codes, technical_gains = set(), set()
for row in audit:
    month, code = row["month"], row["code"]
    before = {feature: row[feature] for feature in ("gp", "cfo")}
    after = dict(before)
    if code in by_code:
        for feature in ("gp", "cfo"):
            reproduced = module.select_feature(by_code[code], old_events, code,
                                               row["decision_date"], feature, coverage, True)
            assert reproduced == before[feature], (code, month, feature, "archived baseline mismatch")
            checked += 1
            after[feature] = module.select_feature(by_code[code], new_events, code,
                                                  row["decision_date"], feature, coverage, True)
            if before[feature]["status"] == "qualified":
                assert after[feature]["status"] == "qualified"
                assert after[feature]["value"] == before[feature]["value"]
                unchanged_qualified += 1
            if before[feature] != after[feature]:
                changes.append({"code": code, "month": month, "feature": feature,
                                "before": before[feature], "after": after[feature],
                                "industry_reason": row["industry_reason"],
                                "technical_eligible": eligible[(month, code)]})
    for stage, values in (("before", before), ("after", after)):
        gp = values["gp"]["status"] == "qualified"
        cfo = values["cfo"]["status"] == "qualified"
        common = gp and cfo and row["industry_reason"] is None
        summary[month][stage + "_gp"] += gp
        summary[month][stage + "_cfo"] += cfo
        summary[month][stage + "_common"] += common
        summary[month][stage + "_technical_common"] += common and eligible[(month, code)]
    old_common = all(v["status"] == "qualified" for v in before.values()) and row["industry_reason"] is None
    new_common = all(v["status"] == "qualified" for v in after.values()) and row["industry_reason"] is None
    if new_common and not old_common:
        recovered_codes.add(code)
        if eligible[(month, code)]:
            technical_gains.add((month, code))
counts = Counter()
gain_by_code = defaultdict(set)
remaining_blocked = defaultdict(set)
for change in changes:
    if change["before"]["status"] != "qualified" and change["after"]["status"] == "qualified":
        counts[change["feature"]] += 1
        gain_by_code[change["code"]].add(change["month"])
    if change["after"].get("blockers"):
        remaining_blocked[change["code"]].add(change["month"])
plan = json.loads((HERE / "storage-plan.json").read_text())
recheck_saved_plan(ROOT, plan, plan["task_id"], plan["estimated_bytes"], plan["internal_metadata_bytes"])
assert _still_mounted(plan)
run = Path(plan["run_directory"])
assert run.parent.parent.is_dir() and run.parent.parent.stat().st_dev == plan["external_device"]
run.parent.mkdir(exist_ok=True)
run.mkdir()
out = Path(plan["output"])
out.mkdir()
assert out.stat().st_dev == plan["external_device"] and _still_mounted(plan)
save(out / "changed-source-rows.json", changes)
save(out / "monthly-coverage.json", [{"month": month, **summary[month]} for month in sorted(summary)])
save(out / "applied-review.json", review)
save(run / "storage-plan.json", plan)
assert _still_mounted(plan)
receipt = {
    "schema": "notice-recovery-verification/1",
    "population": {"stocks": 600, "months": 132, "start": "2015-01", "end": "2025-12"},
    "reviewed_notices": 20, "applied_notices": 14, "held_notices": 6,
    "old_feature_months_reproduced_exactly": checked,
    "previously_qualified_values_unchanged": unchanged_qualified,
    "recovered_feature_months": dict(counts),
    "recovered_company_months_any_feature": sum(len(v) for v in gain_by_code.values()),
    "recovered_common_nonfinancial_company_months": sum(v["after_common"] - v["before_common"] for v in summary.values()),
    "recovered_technical_eligible_common_company_months": len(technical_gains),
    "recovered_companies_common": sorted(recovered_codes),
    "gains_by_code": {code: len(months) for code, months in gain_by_code.items()},
    "still_blocked_after_partial_notice_clearance": {code: len(months) for code, months in remaining_blocked.items()},
    "outputs": [{"path": str(path), "sha256": sha(path), "bytes": path.stat().st_size}
                for path in sorted(out.iterdir())],
    "source_selector_and_original_panel_written": False,
    "new_original_downloads": 0, "market_effects_computed": 0,
    "next_qualification_boundary": "New source revision only; not merged into archived panel and no new factor result.",
}
save(HERE / "source-recovery-receipt.json", receipt)
print(json.dumps({k: receipt[k] for k in
                  ("old_feature_months_reproduced_exactly", "recovered_feature_months",
                   "recovered_company_months_any_feature", "recovered_common_nonfinancial_company_months",
                   "recovered_technical_eligible_common_company_months")}, ensure_ascii=False))
