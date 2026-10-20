"""One frozen correction of existing methods; no new source or parameter search."""
from pathlib import Path
from collections import Counter
import csv
import datetime as dt
import hashlib
import importlib.util
import json
import math
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.dont_write_bytecode = True
from lei_signal.research import lowfreq_discovery as core
from lei_signal.research.lowfreq_derived_prices import load_derived_sources


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_bound(binding):
    assert sha(binding["path"]) == binding["sha256"], binding["path"]
    return Path(binding["path"])


def save(path, obj):
    with Path(path).open("x") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def csv_rows(path):
    with Path(path).open(newline="") as f:
        return list(csv.DictReader(f))


def csv_text(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def same(old, new):
    if old == csv_text(new):
        return True
    try:
        a, b = float(old), float(new)
        return math.isfinite(a) and math.isfinite(b) and math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)
    except (ValueError, TypeError):
        return False


def compare_panel(old, new):
    old_by = {(r["month"], r["code"]): r for r in old}
    assert len(old_by) == len(old) == len(new) == 79200
    assert set(old_by) == {(r["month"], r["code"]) for r in new}
    changes = []
    exact_counts = Counter()
    fields = set(old[0])
    for row in new:
        before = old_by[(row["month"], row["code"])]
        for field in fields:
            if before[field] != csv_text(row.get(field)):
                exact_counts[field] += 1
            if not same(before[field], row.get(field)):
                changes.append({"month": row["month"], "code": row["code"], "field": field,
                                "before": before[field], "after": row.get(field)})
    return changes, dict(exact_counts)


def nested_differences(a, b, path=""):
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return [{"path": path, "reason": "keys differ"}]
        return [d for k in a for d in nested_differences(a[k], b[k], path + "/" + k)]
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [{"path": path, "reason": "length differs"}]
        return [d for i, (x, y) in enumerate(zip(a, b))
                for d in nested_differences(x, y, path + "/" + str(i))]
    if isinstance(a, (int, float)) and not isinstance(a, bool) and isinstance(b, (int, float)):
        if math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12):
            return []
    elif a == b:
        return []
    return [{"path": path, "before": a, "after": b}]


def record_attempt(out, family, budget):
    save(out / (family + "-attempt.json"), {
        "at": dt.datetime.now().astimezone().isoformat(),
        "status": "actual_computation_attempt_started", "budget": budget,
        "no_automatic_retry": True})


def main():
    contract_path = HERE / "execution-contract.json"
    spec = json.loads(contract_path.read_text())
    assert spec["status"] == "approved_frozen"
    for binding in spec["bindings"].values():
        load_bound(binding)
    for binding in spec["protected"]:
        load_bound(binding)
    out = Path(spec["output"])
    out.mkdir(exist_ok=False)
    input_path = load_bound(spec["bindings"]["derived_input"])
    design, selected, membership, calendar, sources, qualification = load_derived_sources(input_path)
    save(out / "input-qualification.json", qualification)
    assert qualification["status"] == "conditional_derived_historical_only"
    record_attempt(out, "p1", spec["budgets"]["p1"])
    monthly, selections, panel, conditional = core._evaluate(design, selected, sources, calendar, membership)
    assert len(monthly) == 132 and len(panel) == 79200
    # The original source guard remains blocked. Only this new derived-input version is used.
    core._write_csv(out / "per_stock_month.csv", panel)
    core._write_csv(out / "monthly.csv", monthly)
    core._write_csv(out / "selections.csv", selections)
    save(out / "conditional.json", conditional)
    old_rows = csv_rows(load_bound(spec["bindings"]["old_panel"]))
    changes, exact_counts = compare_panel(old_rows, panel)
    core._write_csv(out / "panel-differences.csv", changes)
    changed_fields = Counter(r["field"] for r in changes)
    save(out / "impact.json", {
        "status": "actual_derived_dataflow_evaluated",
        "rows": len(panel), "months": len(monthly), "fixed_codes": len(selected),
        "month_status_counts": dict(Counter(r["status"] for r in monthly)),
        "numeric_comparison_tolerance": {"relative": 1e-12, "absolute": 1e-12},
        "exact_changed_cell_counts": exact_counts, "material_changed_cell_counts": dict(changed_fields),
        "changed_months": sorted({r["month"] for r in changes}),
        "feature_outcome_changed_codes": sorted({r["code"] for r in changes if not r["field"].startswith("weight_")}),
        "weight_changed_codes_count": len({r["code"] for r in changes if r["field"].startswith("weight_")}),
        "original_panel": spec["bindings"]["old_panel"], "derived_panel_sha256": sha(out / "per_stock_month.csv"),
        "all_fields_checked": sorted(set(old_rows[0])),
        "original_methods_math_unchanged": spec["bindings"]["core"],
        "note": "Tolerance only classifies negligible floating-point differences; derived calculations use all actual values."})
    performance, annual, increment = core._aggregate(monthly, selections, panel, conditional, design)
    save(out / "p1-performance.json", performance)
    core._write_csv(out / "annual.csv", annual)
    core._write_csv(out / "increment.csv", increment)
    old_inc = csv_rows(load_bound(spec["bindings"]["old_increment"]))
    assert len(old_inc) == len(increment)
    inc_diffs = []
    for old, new in zip(old_inc, increment):
        for key in old:
            if not same(old[key], new.get(key)):
                inc_diffs.append({"month": old["month"], "control": old["control"],
                                  "field": key, "before": old[key], "after": new.get(key)})
    core._write_csv(out / "conditional-differences.csv", inc_diffs)
    print("P1 correction saved", flush=True)
    # Use the frozen defensive mathematics, not its old 69-month source-mask launcher.
    defensive = module(load_bound(spec["bindings"]["defensive_runner"]), "frozen_defensive_math")
    ddesign = json.loads(load_bound(spec["bindings"]["defensive_design"]).read_text())
    audit = json.loads(load_bound(spec["bindings"]["old_dependency_audit"]).read_text())
    old_defense = json.loads(load_bound(spec["bindings"]["old_defensive_monthly"]).read_text())
    by_month = defensive._validate_rows(panel)
    original_blocked = {r["month"] for r in monthly if r["status"] != "evaluated"}
    defensive._check_baseline_weights(by_month, original_blocked)
    record_attempt(out, "defensive", spec["budgets"]["defensive"])
    same_support = []
    prior_same = None
    old_mask = set(audit["combined_blocked_months"])
    for month in defensive._months():
        r, weights = defensive._monthly_row(
            month, by_month[month], prior_same, core, month in old_mask,
            original_blocked=month in audit["original_blocked_months"],
            source_integrity_blocked=month in audit["integrity_blocked_months"])
        same_support.append(r)
        prior_same = None if month in old_mask else weights
    parity = nested_differences(old_defense, same_support)
    save(out / "defensive-same-support-parity.json", {
        "original_dates": len(old_defense),
        "old_evaluable_months": 132 - len(old_mask),
        "difference_count": len(parity), "differences": parity,
        "all_nested_fields_compared": True, "tolerance": 1e-12})
    if parity:
        raise ValueError("original supported defensive observations changed; investigate before extending")
    full, weights_by_month = [], {}
    prior_full = None
    for month in defensive._months():
        r, weights = defensive._monthly_row(
            month, by_month[month], prior_full, core, month in original_blocked,
            original_blocked=month in original_blocked, source_integrity_blocked=False)
        full.append(r)
        weights_by_month[month] = weights
        prior_full = None if month in original_blocked else weights
    save(out / "defensive-monthly.json", full)
    save(out / "defensive-performance.json", defensive._performance(full, core, ddesign))
    defensive._write_csv(out / "defensive-weights.csv", by_month, weights_by_month)
    save(out / "defensive-support.json", {
        "old_source_blocked_months": sorted(old_mask),
        "new_blocked_months": sorted(original_blocked),
        "evaluated_months": 132 - len(original_blocked),
        "restored_months": sorted(old_mask - original_blocked),
        "same_support_parity_verified": True,
        "turnover_note": "Full-series turnover includes newly restored consecutive months; original69 parity uses original mask and resets.",
        "derived_input": spec["bindings"]["derived_input"],
        "unchanged_frozen_method_design": spec["bindings"]["defensive_design"]})
    for binding in spec["protected"]:
        load_bound(binding)
    outputs = {p.name: {"sha256": sha(p), "bytes": p.stat().st_size}
               for p in out.iterdir() if p.is_file() and not p.name.startswith("._")}
    save(out / "manifest.json", {
        "status": "completed_pending_independent_review", "contract_sha256": sha(contract_path),
        "derived_input_sha256": sha(input_path), "outputs": outputs,
        "market_scope": "already_seen_historical_price_diagnostic",
        "originals_preserved": True, "production_authorized": False})
    print("Fixed correction complete", flush=True)


if __name__ == "__main__":
    main()
