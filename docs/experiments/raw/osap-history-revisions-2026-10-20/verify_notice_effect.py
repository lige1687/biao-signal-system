"""Check one source annotation against saved inputs, never calculate market returns."""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / "lowfreq-profitability-increment-2026-10-19"
spec = importlib.util.spec_from_file_location("saved_source_selector", OLD / "build_financial_panel.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
contract = json.loads((OLD / "source-panel-final-01-contract.json").read_text())
inputs = contract["inputs"]
assert module.sha(inputs["runner"]["path"]) == inputs["runner"]["sha256"]
progress = module.json_bound(inputs["progress"])
prep = module.json_bound(inputs["preparation"][0])
controller = module.json_bound(inputs["controller_review"])
old_review = module.json_bound(inputs["notice_review"])
new_review = json.loads((HERE / "notice-review-one.json").read_text())
assert not any(d["announcement_id"] == "1206159525" for d in old_review["decisions"])
review = {**new_review, "decisions": old_review["decisions"] + new_review["decisions"]}
code = "sz.300048"
records = module.expected_index(progress, [code])
module.merge_preparation(records, [{**prep, "documents": [d for d in prep["documents"]
                                                        if d["cohort_code"] == code]}])
coverage = module.catalog_coverage(progress, [code])
old_events = module.events_for(records, controller, old_review)
new_events = module.events_for(records, controller, review)
audit = json.loads((Path(contract["output"]["path"]) / "audit.json").read_text())
source_check = json.loads((HERE / "public-saved-audit.json").read_text())
affected = source_check["new_exact_notice_review"]["old_affected_feature_months"]
out = []
for item in affected:
    row = next(r for r in audit if r["code"] == code and r["month"] == item["month"])
    date = row["decision_date"]
    feature = item["feature"]
    before = module.select_feature(records, old_events, code, date, feature, coverage, True)
    assert before == row[feature], (row["month"], feature, "old saved evidence mismatch")
    after = module.select_feature(records, new_events, code, date, feature, coverage, True)
    assert before["status"] == "unknown" and after["status"] == "qualified"
    out.append({"month": row["month"], "decision_date": row["decision_date"], "feature": feature,
                "before_reason": before["reason"], "after": after})
result = {
    "schema": "single-notice-source-effect/1", "code": code,
    "annotation": {"path": str(HERE / "notice-review-one.json"), "sha256": module.sha(HERE / "notice-review-one.json")},
    "archived_contract": {"path": str(OLD / "source-panel-final-01-contract.json"),
                          "sha256": module.sha(OLD / "source-panel-final-01-contract.json")},
    "scope": "Only source qualification for stock-months blocked by this exact notice; same archived selection rules and raw input.",
    "before_exactly_matches_saved_audit": True, "qualified_feature_months": len(out),
    "qualified_company_months": len({r["month"] for r in out}), "rows": out,
    "archived_inputs_panel_or_results_written": False, "market_outcomes_read_or_computed": False,
    "limits": "Not a new full panel or investment result; annotation and this receipt must be explicitly bound in a later authorized source revision.",
}
with (HERE / "notice-effect-verification.json").open("x") as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write("\n")
print(json.dumps({k: result[k] for k in ("qualified_feature_months", "qualified_company_months",
                                        "before_exactly_matches_saved_audit")}))
