"""Saved-panel calendar-support sensitivity; no source requests or market recalculation.

The narrower sample changes stock composition as well as quote-span support.
Its difference from the core study is not an isolated causal time-window effect.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))
from lei_signal.research import lowfreq_discovery as core  # noqa: E402

DESIGN_SHA256 = "22bcfb62b46085ffa654270a3e4290d2a83793d2af39064d60071adfe6b6a5e5"
CORE_MODULE_SHA256 = "dda4de0acd7335e73a481a66913f47359e974de25a0f220f545c31592fcad0df"
INPUT_CONTRACT_SHA256 = "b9108e54acbbdb1c042f30045e46f3a704938cc829606772fb659e638bfa3289"
RESULT_NAMES = ("monthly.csv", "selections.csv", "per_stock_month.csv", "annual.csv",
                "increment.csv", "performance.json", "quality.json")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _csv(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _float(value):
    if value in ("", None):
        return None
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("non-finite saved numeric value")
    return number


def _bool(value):
    if value in (True, "True", "true", "1", 1):
        return True
    if value in (False, "False", "false", "0", 0):
        return False
    raise ValueError(f"invalid saved boolean: {value!r}")


def _validate(core_dir: Path, input_contract: Path, design_path: Path, out: Path):
    if _sha(input_contract) != INPUT_CONTRACT_SHA256:
        raise ValueError("input contract changed")
    if _sha(design_path) != DESIGN_SHA256:
        raise ValueError("sensitivity design changed")
    module_path = Path(core.__file__).resolve()
    if _sha(module_path) != CORE_MODULE_SHA256:
        raise ValueError("formal evaluator changed")
    spec = _json(input_contract)
    destination = core._check_output_parent(spec, out)
    source = core_dir.resolve()
    if source == destination or source.parent != Path(spec["output_parent"]).resolve():
        raise ValueError("core result must be a sibling in bound external output parent")
    manifest_path = source / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError("core manifest missing")
    manifest = _json(manifest_path)
    if (manifest.get("schema") != "lowfreq-result-manifest/1"
            or manifest.get("input_contract_sha256") != INPUT_CONTRACT_SHA256
            or manifest.get("design_sha256") != spec["design"]["sha256"]):
        raise ValueError("core manifest does not bind frozen input and design")
    for name in RESULT_NAMES:
        if manifest.get("outputs", {}).get(name) != _sha(source / name):
            raise ValueError(f"core output missing or changed: {name}")
    design, _ = core._bound(spec["design"])
    calendar_doc, _ = core._bound(spec["calendar"])
    calendar = core._calendar(calendar_doc)
    return spec, destination, manifest_path, design, calendar


def run(core_dir: Path, input_contract: Path, design_path: Path, out: Path):
    core_dir = Path(core_dir).expanduser()
    input_contract = Path(input_contract).expanduser()
    design_path = Path(design_path).expanduser()
    spec, destination, core_manifest_path, design, calendar = _validate(
        core_dir, input_contract, design_path, Path(out))
    core_monthly = _csv(core_dir / "monthly.csv")
    core_panel = _csv(core_dir / "per_stock_month.csv")
    core_quality = _json(core_dir / "quality.json")
    codes = core_quality["sample_codes"]
    if len(codes) != 600 or len(set(codes)) != 600 or len(core_monthly) != 132 or len(core_panel) != 600 * 132:
        raise ValueError("core result lacks the complete fixed 600-by-132 panel")
    by_month = {}
    for row in core_panel:
        by_month.setdefault(row["month"], []).append(row)
    periods = core._decision_and_execution_dates(calendar)
    positions = {day: i for i, day in enumerate(calendar)}
    monthly, selections, per_stock, conditional = [], [], [], []
    support = []
    previous = {method: None for method in core.METHODS}
    if [r["month"] for r in core_monthly] != [r[0] for r in periods]:
        raise ValueError("core monthly calendar differs from frozen periods")
    for source_month, (month, decision, entry, exit_day) in zip(core_monthly, periods):
        rows = by_month.get(month, [])
        if (len(rows) != 600 or {r["code"] for r in rows} != set(codes)
                or any((r["decision_date"], r["entry_date"], r["exit_date"]) !=
                       (decision, entry, exit_day) for r in rows)
                or (source_month["decision_date"], source_month["entry_date"], source_month["exit_date"]) !=
                   (decision, entry, exit_day)):
            raise ValueError(f"core panel identity/date mismatch: {month}")
        at = positions[decision]
        if at < 252:
            raise ValueError(f"decision lacks 252 common trading days: {month}")
        expected_start = calendar[at - 252]
        excluded = []
        panel = []
        for source_row in rows:
            row = dict(source_row)
            row["original_eligibility_reason"] = row["eligibility_reason"]
            if row["eligibility_reason"] == "eligible" and row["momentum_252_start_date"] != expected_start:
                row["eligibility_reason"] = "calendar_window_not_equal"
                excluded.append({"code": row["code"], "original_start_date": row["momentum_252_start_date"],
                                 "original_span_calendar_days": _float(row["momentum_252_calendar_days"]),
                                 "vol60": _float(row["vol60"]), "amount20": _float(row["amount20"])})
            panel.append(row)
        blocked = source_month["status"] == "data_error"
        if source_month["status"] not in ("data_error", "empty_pool", "evaluated"):
            raise ValueError(f"unrecognized core month status: {month}")
        original_eligible = sum(r["original_eligibility_reason"] == "eligible" for r in panel)
        subset_eligible = sum(r["eligibility_reason"] == "eligible" for r in panel)
        support.append({"month": month, "decision_date": decision, "common_252_start_date": expected_start,
                        "original_eligible": original_eligible, "subset_eligible": subset_eligible,
                        "subset_fraction_of_original": subset_eligible / original_eligible if original_eligible else None,
                        "excluded_count": len(excluded), "excluded": excluded,
                        "core_status": source_month["status"]})
        eligible_panel = []
        for row in panel:
            item = {"code": row["code"], "eligibility_reason": row["eligibility_reason"]}
            if row["eligibility_reason"] == "eligible":
                item.update({key: _float(row[key]) for key in ("momentum", "short", "vol60", "amount20")})
            eligible_panel.append(item)
        weights, qualified = core._selections(eligible_panel) if not blocked else (
            {method: {} for method in core.METHODS}, [])
        n = len(qualified)
        outcomes = {r["code"]: (_float(r["future_return"]), r["outcome_reason"],
                                 _float(r["suspension_marked_price_proxy"])) for r in panel}
        halt_flags = {r["code"]: (_bool(r["entry_halt"]), _bool(r["exit_halt"])) for r in panel}
        methods = {}
        for method in core.METHODS:
            result = core._weighted_outcome(weights[method], outcomes, halt_flags)
            result["target_replacement_turnover"] = (
                core._turnover(weights[method], previous[method]) if n else None)
            methods[method] = result
            previous[method] = weights[method] if n else None
            for code, weight in weights[method].items():
                selections.append({"month": month, "method": method, "code": code,
                                   "target_weight": weight, "decision_date": decision,
                                   "entry_date": entry, "exit_date": exit_day})
        for row in panel:
            code = row["code"]
            row["future_return"] = outcomes[code][0]
            row.update({f"weight_{method}": weights[method].get(code, 0) for method in core.METHODS})
            per_stock.append(row)
        cells_by_kind = {}
        for kind, cells in (("vol_amount_9", core._conditional_groups(qualified)),
                            ("vol_amount_short_27", core._conditional_groups(qualified, include_short=True))):
            combined_top, combined_all = core._combined_cell_weights(cells, n)
            cell_rows = []
            for cell in cells:
                cell_rows.append({"vol_group": cell["vol_group"], "amount_group": cell["amount_group"],
                                  "short_group": cell["short_group"], "n": cell["n"],
                                  "share_of_pool": cell["n"] / n if n else 0,
                                  "top_n": len(cell["top"]),
                                  "all": core._weighted_outcome(cell["all"], outcomes, halt_flags),
                                  "top": core._weighted_outcome(cell["top"], outcomes, halt_flags)})
            cells_by_kind[kind] = {"cells": cell_rows, "combined": {
                "top": core._weighted_outcome(combined_top, outcomes, halt_flags),
                "all": core._weighted_outcome(combined_all, outcomes, halt_flags),
                "relative_adversarial": core._relative_unknown(combined_top, combined_all, outcomes)}}
        conditional.append({"month": month, "cells_by_kind": cells_by_kind})
        monthly.append({"month": month, "decision_date": decision, "entry_date": entry,
                        "exit_date": exit_day, "pool_count": n,
                        "status": "data_error" if blocked else ("empty_pool" if n == 0 else "evaluated"),
                        "data_errors": json.loads(source_month["data_errors"]),
                        "ineligible_count": len(panel) - n if not blocked else None,
                        "methods": methods, "relative_adversarial": {
                            "momentum_top20_minus_pool_equal": core._relative_unknown(
                                weights["momentum_top20"], weights["pool_equal"], outcomes),
                            "momentum_top20_minus_short_top20": core._relative_unknown(
                                weights["momentum_top20"], weights["short_top20"], outcomes)}})
    performance, annual, increment = core._aggregate(monthly, selections, per_stock, conditional, design)
    performance["sensitivity_interpretation"] = (
        "Calendar-support subset changes stock composition; differences cannot isolate a causal time-window effect.")
    quality = {"core_result_manifest_sha256": _sha(core_manifest_path),
               "fixed_sample_count": 600, "sample_codes": codes, "monthly_full_rows": len(per_stock),
               "expected_monthly_full_rows": 600 * 132,
               "month_status_counts": dict(Counter(r["status"] for r in monthly)),
               "actual_evaluated_months": sum(r["status"] == "evaluated" for r in monthly),
               "ten_year_support_met": sum(r["status"] == "evaluated" for r in monthly) >= 120,
               "support_by_month": support,
               "original_eligible_stock_months": sum(r["original_eligible"] for r in support),
               "subset_eligible_stock_months": sum(r["subset_eligible"] for r in support),
               "excluded_calendar_window_stock_months": sum(r["excluded_count"] for r in support),
               "ineligible_reasons": dict(Counter(r["eligibility_reason"] for r in per_stock
                                                if r["eligibility_reason"] != "eligible")),
               "source_scope": "same frozen core panel; no source refresh or new market calculation",
               "interpretation_limit": "subset composition changes; not isolated causal time-window effect"}
    destination.mkdir(parents=False, exist_ok=False)
    for name, rows in (("monthly.csv", monthly), ("selections.csv", selections),
                       ("per_stock_month.csv", per_stock), ("annual.csv", annual),
                       ("increment.csv", increment)):
        core._write_csv(destination / name, rows)
    for name, value in (("performance.json", performance), ("quality.json", quality)):
        with (destination / name).open("x", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
    files = {p.name: _sha(p) for p in destination.iterdir()
             if p.is_file() and not p.name.startswith("._") and p.name != ".DS_Store"}
    manifest = {"schema": "lowfreq-calendar-support-sensitivity-result/1",
                "core_manifest_path": str(core_manifest_path),
                "core_manifest_sha256": _sha(core_manifest_path),
                "input_contract_path": str(input_contract.resolve()),
                "input_contract_sha256": _sha(input_contract),
                "sensitivity_design_path": str(design_path.resolve()),
                "sensitivity_design_sha256": _sha(design_path),
                "formal_evaluator_sha256": CORE_MODULE_SHA256,
                "script_sha256": _sha(Path(__file__)), "outputs": files,
                "market_execution": "saved_core_panel_only", "production_authorized": False}
    with (destination / "manifest.json").open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2, allow_nan=False)
    return {"output": str(destination), "manifest_sha256": _sha(destination / "manifest.json")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-dir", required=True, type=Path)
    parser.add_argument("--input-contract", required=True, type=Path)
    parser.add_argument("--design", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.core_dir, args.input_contract, args.design, args.out)))


if __name__ == "__main__":
    main()
