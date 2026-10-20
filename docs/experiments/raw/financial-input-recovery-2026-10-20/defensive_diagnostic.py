#!/usr/bin/env python3
"""Frozen saved-panel comparison. Real inputs are read only after full hash binding."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import statistics
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
DESIGN_PATH = HERE / "defensive-design-v3.json"
SELF_TEST_OUTPUT = HERE / "defensive-synthetic.json"
REQUIRED_COLUMNS = {
    "month", "decision_date", "code", "entry_date", "exit_date",
    "eligibility_reason", "momentum", "vol60", "future_return",
    "outcome_reason", "entry_halt", "exit_halt", "either_halt",
    "suspension_marked_price_proxy", "weight_momentum_top20",
}
METHODS = ("pool_equal", "momentum_top20", "momentum75", "lowvol_top20", "momentum_lowvol")
FIRST_MONTH, LAST_MONTH = "2015-01", "2025-12"
EXPECTED_MONTHS = 132
EXPECTED_ROWS = 79_200


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_design() -> tuple[dict, str]:
    if not DESIGN_PATH.is_file():
        raise ValueError(f"missing frozen design: {DESIGN_PATH}")
    return json.loads(DESIGN_PATH.read_text(encoding="utf-8")), sha256_file(DESIGN_PATH)


def load_source_isolation(design):
    spec = design["population"]["source_integrity_isolation"]
    path = Path(spec["path"]).resolve()
    if not path.is_file() or sha256_file(path) != spec["sha256"]:
        raise ValueError(f"source-integrity audit fingerprint mismatch: {path}")
    audit = json.loads(path.read_text(encoding="utf-8"))
    if audit.get("no_new_effects_computed") is not True or audit.get("future_fields_used") != []:
        raise ValueError("source-integrity audit does not declare a no-effects source review")
    if audit.get("fresh_all_600_guard", {}).get("status") != "blocked":
        raise ValueError("source-integrity audit guard state changed")
    for audit_key, expected in (("original_blocked_months", []),
                                ("integrity_blocked_months", spec.get("blocked_months")),
                                ("combined_blocked_months", spec.get("blocked_months"))):
        if audit.get(audit_key) != expected:
            raise ValueError(f"source-integrity audit {audit_key} differs from frozen design")
    expected_counts = {"calendar": EXPECTED_MONTHS, "original_blocked": 0,
                       "price_integrity_blocked": 63, "combined_blocked": 63, "evaluable": 69}
    if (audit.get("retained_counts") != expected_counts or
            audit.get("period_support") != spec.get("period_support") or
            spec.get("planned_calendar_months") != EXPECTED_MONTHS or
            spec.get("evaluable_months") != 69):
        raise ValueError("source-integrity audit counts/period support differ from frozen design")
    months = _months()
    evaluable = audit.get("retained_evaluable_months")
    if (not isinstance(evaluable, list) or evaluable != sorted(set(evaluable)) or
            set(evaluable) != set(months)-set(spec["blocked_months"]) or len(evaluable) != 69):
        raise ValueError("source-integrity audit evaluable dates differ from frozen calendar/block list")
    if {m[:4] for m in evaluable if m <= "2020-12"} and sum(m <= "2020-12" for m in evaluable) != 9:
        raise ValueError("source-integrity audit pre-2021 evaluable support differs")
    if sum(m >= "2021-01" for m in evaluable) != 60:
        raise ValueError("source-integrity audit 2021-2025 support differs")
    return path, audit


def _consecutive_month_pairs(months):
    return sum((int(b[:4])*12+int(b[5:7]))-(int(a[:4])*12+int(a[5:7])) == 1
               for a, b in zip(months, months[1:]))


def load_helpers(design: dict):
    spec = design["helper"]
    path = Path(spec["path"]).resolve()
    if not path.is_file() or sha256_file(path) != spec["sha256"]:
        raise ValueError(f"helper fingerprint mismatch: {path}")
    module_spec = importlib.util.spec_from_file_location("frozen_lowfreq_discovery_helpers", path)
    if module_spec is None or module_spec.loader is None:
        raise ValueError(f"cannot load frozen helper module: {path}")
    module = importlib.util.module_from_spec(module_spec)
    sys.dont_write_bytecode = True
    module_spec.loader.exec_module(module)
    names = ("_weighted_outcome", "_relative_unknown", "_turnover", "_blocks", "_mean", "_sample_std")
    if any(not callable(getattr(module, name, None)) for name in names):
        raise ValueError("frozen helper API changed")
    return module


def _number(value):
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def _bool(value):
    if value in (True, 1, "1", "true", "True", "TRUE"):
        return True
    if value in (False, 0, "0", "false", "False", "FALSE", "", None):
        return False
    raise ValueError(f"invalid boolean field: {value!r}")


def _nullable_number(value, field):
    if value in (None, ""):
        return None
    parsed = _number(value)
    if parsed is None:
        raise ValueError(f"invalid nonempty {field}: {value!r}")
    return parsed


def _months(first=FIRST_MONTH, last=LAST_MONTH):
    result = []
    y, m = map(int, first.split("-"))
    ey, em = map(int, last.split("-"))
    while (y, m) <= (ey, em):
        result.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return result


def _validate_month_calendar(month, month_rows):
    for field in ("decision_date", "entry_date", "exit_date"):
        if len({r[field] for r in month_rows}) != 1:
            raise ValueError(f"{field} differs within month {month}")
    if month_rows[0]["entry_date"][:7] != month:
        raise ValueError(f"entry month differs from panel month {month}")


def _validate_output_binding(bound, requested):
    if Path(bound).expanduser().resolve() != Path(requested).resolve():
        raise ValueError("--out does not match frozen contract output_directory")


def _weights(panel):
    eligible = [r for r in panel if r["eligibility_reason"] == "eligible"]
    if any(r["momentum"] is None or r["vol60"] is None for r in eligible):
        raise ValueError("eligible row lacks finite momentum or vol60")
    n = math.ceil(.20 * len(eligible))
    ranked_momentum = sorted(eligible, key=lambda r: (-r["momentum"], r["code"]))
    ranked_lowvol = sorted(eligible, key=lambda r: (r["vol60"], r["code"]))
    top = ranked_momentum[:n]
    screen = ranked_momentum[:min(2 * n, len(eligible))]
    combined = sorted(screen, key=lambda r: (r["vol60"], r["code"]))[:n]
    def equal(rows, scale=1.0):
        if not rows:
            return {}
        weight = scale / len(rows)
        return {r["code"]: weight for r in rows}
    return {
        "pool_equal": equal(eligible),
        "momentum_top20": equal(top),
        "momentum75": equal(top, .75),
        "lowvol_top20": equal(ranked_lowvol[:n]),
        "momentum_lowvol": equal(combined),
    }, eligible


def _original_month_blocked(panel):
    """Respect the saved baseline's empty/zero whole-month state; never reopen it."""
    saved = [_number(r.get("weight_momentum_top20")) for r in panel]
    if all(v is None for v in saved):
        return True
    if any(v is None for v in saved):
        raise ValueError(f"partially missing saved momentum weights in {panel[0]['month']}")
    if all(v == 0 for v in saved):
        return True
    return False


def _validate_rows(rows):
    months = _months()
    if len(months) != EXPECTED_MONTHS or months[0] != FIRST_MONTH or months[-1] != LAST_MONTH:
        raise AssertionError("internal frozen month range error")
    if len(rows) != EXPECTED_ROWS:
        raise ValueError(f"expected {EXPECTED_ROWS} rows, got {len(rows)}")
    by_month = defaultdict(list)
    seen = set()
    all_codes = None
    for raw in rows:
        month, code = raw["month"], raw["code"]
        key = (month, code)
        if month not in months or key in seen:
            raise ValueError(f"unexpected or duplicate row key: {key}")
        seen.add(key)
        for field in ("decision_date", "entry_date", "exit_date"):
            date.fromisoformat(raw[field])
        if not raw["decision_date"] < raw["entry_date"] < raw["exit_date"]:
            raise ValueError(f"decision/entry/exit order violated: {key}")
        by_month[month].append(raw)
    if set(by_month) != set(months):
        raise ValueError("months differ from frozen 2015-01..2025-12 set")
    for month in months:
        month_rows = by_month[month]
        codes = [r["code"] for r in month_rows]
        if len(codes) != 600 or len(set(codes)) != 600:
            raise ValueError(f"expected 600 distinct stock codes in {month}")
        _validate_month_calendar(month, month_rows)
        current = set(codes)
        if all_codes is None:
            all_codes = current
        elif current != all_codes:
            raise ValueError(f"historical 600-code cohort changed in {month}")
    return by_month


def _read_panel(source: Path, expected_sha: str):
    if not source.is_file() or sha256_file(source) != expected_sha:
        raise ValueError(f"input fingerprint mismatch: {source}")
    rows = []
    with source.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or not REQUIRED_COLUMNS <= set(reader.fieldnames):
            raise ValueError(f"required panel columns missing: {sorted(REQUIRED_COLUMNS-set(reader.fieldnames or []))}")
        for raw in reader:
            row = dict(raw)
            row["momentum"] = _number(raw.get("momentum"))
            row["vol60"] = _number(raw.get("vol60"))
            raw_future = raw.get("future_return")
            row["future_return"] = _number(raw_future)
            if raw_future not in (None, "") and row["future_return"] is None:
                raise ValueError(f"invalid nonempty future_return at CSV line {reader.line_num}")
            row["entry_halt"] = _bool(raw.get("entry_halt"))
            row["exit_halt"] = _bool(raw.get("exit_halt"))
            row["either_halt"] = _bool(raw.get("either_halt"))
            row["suspension_marked_price_proxy"] = _nullable_number(raw.get("suspension_marked_price_proxy"), "suspension_marked_price_proxy")
            rows.append(row)
    return rows


def _check_baseline_weights(by_month, original_blocked_months):
    for month, panel in by_month.items():
        if month in original_blocked_months:
            continue
        weights, _ = _weights(panel)
        expected = weights["momentum_top20"]
        for row in panel:
            saved = _number(row["weight_momentum_top20"])
            target = expected.get(row["code"], 0.0)
            if saved is None or abs(saved - target) > 1e-12:
                raise ValueError(f"saved momentum weights differ in {month} {row['code']}: {saved} != {target}")


def _monthly_row(month, panel, prior_weights, helpers, blocked, original_blocked=None, source_integrity_blocked=False):
    if original_blocked is None:
        original_blocked = blocked
    if blocked:
        method_weights = {method: {} for method in METHODS}
        eligible = [r for r in panel if r["eligibility_reason"] == "eligible"]
    else:
        method_weights, eligible = _weights(panel)
    outcomes = {r["code"]: (r["future_return"], r.get("outcome_reason")) for r in panel}
    halts = {r["code"]: (r["entry_halt"], r["exit_halt"]) for r in panel}
    outcome = {}
    for method in METHODS:
        result = helpers._weighted_outcome(method_weights[method], outcomes, halts)
        result["negative_component_scenario_zero"] = min(result["scenario_zero"], 0.0) if result["scenario_zero"] is not None else None
        result["positive_component_scenario_zero"] = max(result["scenario_zero"], 0.0) if result["scenario_zero"] is not None else None
        result["negative_component_scenario_minus100"] = min(result["scenario_minus100"], 0.0) if result["scenario_minus100"] is not None else None
        result["positive_component_scenario_minus100"] = max(result["scenario_minus100"], 0.0) if result["scenario_minus100"] is not None else None
        result["target_weight_sum"] = math.fsum(method_weights[method].values())
        result["assumed_cash_weight"] = .25 if method == "momentum75" else 0.0
        result["cash_return_assumption"] = "0; no interest or financing benefit" if method == "momentum75" else None
        prior = prior_weights.get(method) if prior_weights is not None else None
        result["target_replacement_turnover"] = (
            None if blocked or prior_weights is None else helpers._turnover(method_weights[method], prior))
        result["selected_names"] = sorted(method_weights[method])
        if not result["empty_selection"]:
            if abs(result["scenario_zero"] - result["observed_contribution"]) > 1e-12:
                raise ValueError(f"scenario_zero identity failed for {month}/{method}")
            if abs(result["scenario_minus100"] - (result["observed_contribution"] - result["unknown_weight"])) > 1e-12:
                raise ValueError(f"scenario_minus100 identity failed for {month}/{method}")
        outcome[method] = result
    observed = [] if blocked else [r for r in eligible if r["future_return"] is not None]
    k = math.ceil(.10 * len(observed))
    best_observed = {r["code"] for r in sorted(observed, key=lambda r: (-r["future_return"], r["code"]))[:k]}
    best_observed_positive_count = sum(r["future_return"] > 0 for r in observed if r["code"] in best_observed)
    mom_names = set(method_weights["momentum_top20"])
    for method in METHODS:
        names = set(method_weights[method])
        outcome[method]["observed_best_decile_name_share_selected"] = (
            len(names & best_observed) / len(best_observed) if best_observed else None)
        outcome[method]["selected_count"] = len(names)
        outcome[method]["momentum_name_overlap_share"] = (
            len(names & mom_names) / len(names) if names else None)
    if len({outcome[m]["empty_selection"] for m in METHODS}) != 1:
        raise ValueError(f"method support differs in {month}")
    # Paired uncertainty coefficients are retained as ranges, not filled outcomes.
    relative = {}
    for comparator in ("momentum_top20", "momentum75", "lowvol_top20"):
        relative[comparator] = helpers._relative_unknown(
            method_weights["momentum_lowvol"], method_weights[comparator], outcomes)
    return {"month": month, "original_full_month_blocked": original_blocked,
            "source_integrity_blocked": source_integrity_blocked,
            "combined_blocked": blocked,
            "retained_rows": len(panel), "eligible_count": len(eligible), "observed_outcome_count": len(observed),
            "best_observed_decile_count": len(best_observed),
            "best_observed_decile_positive_return_count": best_observed_positive_count,
            "methods": outcome, "momentum_lowvol_relative_unknown_total_return": relative}, method_weights


def _mean_nonempty(helpers, values):
    return helpers._mean(values)


def _series(rows, method, field):
    return [row["methods"][method].get(field) for row in rows]


def _sum_stats(rows, helpers, method):
    result = {}
    for scenario in ("scenario_zero", "scenario_minus100"):
        vals = _series(rows, method, scenario)
        finite = [v for v in vals if v is not None]
        neg = [min(v, 0.0) for v in finite]
        pos = [max(v, 0.0) for v in finite]
        worst10 = sorted(finite)[:math.ceil(len(finite) / 10)] if finite else []
        result[scenario] = {
            "defined_months": len(finite),
            "mean_total_monthly_price_change": helpers._mean(finite),
            "mean_negative_component": helpers._mean(neg),
            "mean_positive_component": helpers._mean(pos),
            "monthly_standard_deviation": helpers._sample_std(finite),
            "worst_month": min(finite) if finite else None,
            "mean_worst10pct_months": helpers._mean(worst10),
        }
    for field, label in (("unknown_weight", "unknown_weight"),
                         ("entry_halt_weight", "entry_halt_weight"),
                         ("exit_halt_weight", "exit_halt_weight"),
                         ("either_halt_weight", "either_halt_weight")):
        included = [r for r in rows if not r["methods"][method]["empty_selection"]]
        values = [r["methods"][method].get(field) for r in included]
        finite = [x for x in values if x is not None]
        result[label] = {"mean": helpers._mean(finite), "max": max(finite) if finite else None}
    turnover = [x for x in _series(rows, method, "target_replacement_turnover") if x is not None]
    result["mean_target_replacement_turnover_ex_first_month"] = helpers._mean(turnover)
    result["target_replacement_pair_count"] = len(turnover)
    result["mean_observed_best_decile_name_share_selected"] = helpers._mean(
        [r["methods"][method]["observed_best_decile_name_share_selected"] for r in included
         if r["methods"][method]["observed_best_decile_name_share_selected"] is not None])
    result["mean_selected_count"] = helpers._mean([r["methods"][method]["selected_count"] for r in included])
    result["mean_momentum_name_overlap_share"] = helpers._mean(
        [r["methods"][method]["momentum_name_overlap_share"] for r in included
         if r["methods"][method]["momentum_name_overlap_share"] is not None])
    return result


def _method_detail(rows, helpers, method):
    annual = {}
    for year in sorted({r["month"][:4] for r in rows}):
        subset = [r for r in rows if r["month"].startswith(year)]
        annual[year] = _sum_stats(subset, helpers, method)
    periods = {}
    for label, lo, hi in (("2015-2020", "2015-01", "2020-12"), ("2021-2025", "2021-01", "2025-12")):
        subset = [r for r in rows if lo <= r["month"] <= hi]
        periods[label] = _sum_stats(subset, helpers, method)
    pool = {r["month"]: r["methods"]["pool_equal"]["scenario_zero"] for r in rows}
    conditional = {}
    for group, predicate in (("pool_down", lambda v: v is not None and v < 0),
                             ("pool_up", lambda v: v is not None and v > 0)):
        diffs = []
        for r in rows:
            base = pool[r["month"]]
            val = r["methods"][method]["scenario_zero"]
            if predicate(base) and val is not None:
                diffs.append(val - base)
        conditional[group] = {"months": len(diffs), "mean_method_minus_pool_scenario_zero": helpers._mean(diffs)}
    nonempty = sum(bool(r["methods"][method]["selected_names"]) for r in rows)
    original_blocked = sum(r["original_full_month_blocked"] for r in rows)
    source_blocked = sum(r["source_integrity_blocked"] for r in rows)
    combined_blocked = sum(r["combined_blocked"] for r in rows)
    return {"retained_date_count": len(rows), "actual_nonempty_date_count": nonempty,
            "summary_date_count_excluding_empty_selection": sum(not r["methods"][method]["empty_selection"] for r in rows),
            "original_full_month_blocked_count": original_blocked,
            "source_integrity_blocked_count": source_blocked,
            "combined_blocked_count": combined_blocked,
            "all_months": _sum_stats(rows, helpers, method), "annual_means": annual,
            "periods": periods, "same_month_pool_condition": conditional}


def _performance(months, helpers, design):
    performance = {"schema": "saved-selection-performance/1", "methods": {}, "primary_increment": {},
                   "uncertainty": {}, "interpretation_limits": [
                       "未来字段仅用于选法冻结后的结果统计；不代表可成交价格或扣费后账户收益。",
                       "不计算账户累计回撤、成交、费用或交易实现；momentum75现金按每月0收益假设。",
                       "132个月相互有关且均已看过；月份分块范围是历史不确定性描述，不是实盘有效性证明。",
                       "缺失结果保持未知；0和-100%仅为指定情景，不把缺失值改成已知观测。"]}
    for method in METHODS:
        performance["methods"][method] = _method_detail(months, helpers, method)
    for row in months:
        for scenario in ("scenario_zero", "scenario_minus100"):
            active = {row["methods"][m][scenario] is not None for m in METHODS}
            if len(active) != 1:
                raise ValueError(f"paired method dates differ in {row['month']}/{scenario}")
        for method in METHODS:
            m = row["methods"][method]
            if (m["scenario_zero"] is None) != (m["scenario_minus100"] is None):
                raise ValueError(f"paired scenario dates differ in {row['month']}/{method}")
    for comparator in ("momentum_top20", "momentum75", "lowvol_top20"):
        comparison = {}
        for scenario in ("scenario_zero", "scenario_minus100"):
            detail = {}
            for field in (scenario,):
                deltas = []
                neg = []
                pos = []
                for row in months:
                    left, right = row["methods"]["momentum_lowvol"], row["methods"][comparator]
                    a, b = left[field], right[field]
                    deltas.append(a - b if a is not None and b is not None else None)
                    nf = "negative_component_" + scenario
                    pf = "positive_component_" + scenario
                    x, y = left[nf], right[nf]
                    neg.append(x - y if x is not None and y is not None else None)
                    x, y = left[pf], right[pf]
                    pos.append(x - y if x is not None and y is not None else None)
                detail["mean_total_increment"] = helpers._mean(deltas)
                detail["mean_negative_component_increment"] = helpers._mean(neg)
                detail["mean_positive_component_increment"] = helpers._mean(pos)
                detail["defined_months_total"] = sum(x is not None for x in deltas)
                detail["circular_month_blocks"] = {}
                for length in (12, 24):
                    detail["circular_month_blocks"][str(length)] = {
                        "total": helpers._blocks(deltas, [length], 2000, 20261020)[str(length)],
                        "negative_component": helpers._blocks(neg, [length], 2000, 20261020)[str(length)],
                        "positive_component": helpers._blocks(pos, [length], 2000, 20261020)[str(length)],
                    }
            comparison[scenario] = detail
        rel = [r["momentum_lowvol_relative_unknown_total_return"][comparator] for r in months]
        comparison["relative_unknown_total_return_coefficients"] = {
            key: helpers._mean([x[key] for x in rel if x and x.get(key) is not None])
            for key in ("observed_delta", "adverse_unknown_minus100_or_zero", "favorable_unknown_minus100_or_zero")
        }
        performance["primary_increment"][f"momentum_lowvol_minus_{comparator}"] = comparison
    performance["relative_unknown_note"] = (
        "helper relative range applies only to linear total-return contrast; it is not used for negative or positive component increments.")
    performance["component_order"] = "For each fixed scenario, first calculate each method's weighted monthly total, then take min(R,0) and max(R,0); their means sum to the mean total."
    performance["question"] = design["question"]
    performance["primary_measure"] = design["evaluation"]["primary_measure"]
    performance["cash_method"] = "momentum75: same momentum top names, target weights sum to 0.75; remaining 0.25 cash contributes 0 each month."
    performance["paired_support_and_blocks"] = (
        "All methods and both scenarios share the same retained month axis; empty-selection months remain null and are excluded from summaries. "
        "Each paired contrast uses aligned months. The frozen block helper resets to the same seed for each same-length input, so equal axes and equal finite-month support use identical circular block start draws; finite_months_range reports support within draws.")
    return performance


def _write_csv(path, by_month, monthly_weights):
    fields = ["month", "code", "eligibility_reason", "momentum", "vol60", "future_return", "outcome_reason",
              "entry_halt", "exit_halt", "either_halt", "suspension_marked_price_proxy"]
    for method in METHODS:
        fields.extend((f"weight_{method}", f"unknown_weight_{method}"))
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for month in _months():
            for row in by_month[month]:
                out = {field: row.get(field, "") for field in fields[:len(fields)-2*len(METHODS)]}
                for method in METHODS:
                    weight = monthly_weights[month][method].get(row["code"], 0.0)
                    out[f"weight_{method}"] = format(weight, ".17g")
                    out[f"unknown_weight_{method}"] = format(weight if weight and row["future_return"] is None else 0.0, ".17g")
                writer.writerow(out)


def _bindings(contract: dict):
    bindings = contract.get("bindings")
    if not isinstance(bindings, dict):
        raise ValueError("run contract must contain bindings for design, input, helper, and runner")
    return bindings


def _verify_run_contract(contract_path: Path, design: dict, design_sha: str):
    if not contract_path.is_file():
        raise ValueError(f"missing run contract: {contract_path}")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("status") not in ("frozen", "approved_frozen"):
        raise ValueError("run contract is not frozen/approved; real mode remains blocked")
    output_directory = contract.get("output_directory")
    if not isinstance(output_directory, str) or not output_directory:
        raise ValueError("run contract must bind output_directory")
    bindings = _bindings(contract)
    expected = {
        "design": (DESIGN_PATH.resolve(), design_sha),
        "input": (Path(design["source"]["path"]).resolve(), design["source"]["sha256"]),
        "helper": (Path(design["helper"]["path"]).resolve(), design["helper"]["sha256"]),
        "source_integrity": (Path(design["population"]["source_integrity_isolation"]["path"]).resolve(),
                             design["population"]["source_integrity_isolation"]["sha256"]),
        "runner": (Path(__file__).resolve(), sha256_file(Path(__file__).resolve())),
    }
    for name, (path, digest) in expected.items():
        item = bindings.get(name)
        if not isinstance(item, dict) or Path(item.get("path", "")).expanduser().resolve() != path or item.get("sha256") != digest:
            raise ValueError(f"run contract {name} path/SHA binding mismatch")
        if not path.is_file() or sha256_file(path) != digest:
            raise ValueError(f"current {name} file SHA mismatch: {path}")
    return contract, expected


def _run_real(contract_path: Path, out_path: Path):
    design, design_sha = load_design()
    contract, expected = _verify_run_contract(contract_path, design, design_sha)
    _validate_output_binding(contract["output_directory"], out_path)
    if out_path.exists():
        raise ValueError(f"output directory must be new: {out_path}")
    audit_path, audit = load_source_isolation(design)
    helpers = load_helpers(design)
    source = expected["input"][0]
    rows = _read_panel(source, expected["input"][1])
    by_month = _validate_rows(rows)
    original_blocked = set(audit["original_blocked_months"])
    source_blocked = set(audit["integrity_blocked_months"])
    combined_blocked = set(audit["combined_blocked_months"])
    if original_blocked != {month for month, panel in by_month.items() if _original_month_blocked(panel)}:
        raise ValueError("saved panel original full-month blocked set differs from source audit")
    if combined_blocked != original_blocked | source_blocked:
        raise ValueError("combined blocked set is not the union of original and source-integrity blocks")
    if len(combined_blocked) != 63 or EXPECTED_MONTHS-len(combined_blocked) != 69:
        raise ValueError("frozen source isolation month counts changed")
    _check_baseline_weights(by_month, original_blocked)
    monthly, weights_by_month = [], {}
    previous = None
    for month in _months():
        blocked = month in combined_blocked
        result, weights = _monthly_row(month, by_month[month], previous, helpers, blocked,
                                       original_blocked=month in original_blocked,
                                       source_integrity_blocked=month in source_blocked)
        monthly.append(result)
        weights_by_month[month] = weights
        previous = None if blocked else weights
    performance = _performance(monthly, helpers, design)
    performance["provenance"] = {
        "run_contract_path": str(contract_path.resolve()),
        "run_contract_sha256": sha256_file(contract_path),
        "design_path": str(DESIGN_PATH), "design_sha256": design_sha,
        "source_integrity_audit_path": str(audit_path), "source_integrity_audit_sha256": sha256_file(audit_path),
        "source_integrity_isolation": {
            "audit_guard_status": audit["fresh_all_600_guard"]["status"],
            "original_full_month_blocked_months": audit["original_blocked_months"],
            "source_integrity_blocked_months": audit["integrity_blocked_months"],
            "combined_blocked_months": audit["combined_blocked_months"],
            "retained_counts": audit["retained_counts"],
            "period_support": audit["period_support"],
            "evaluable_date_count": len(audit["retained_evaluable_months"]),
            "evaluable_date_ranges": [["2016-08", "2016-10"], ["2020-07", "2025-12"]],
            "adjacent_evaluable_target_replacement_pairs": _consecutive_month_pairs(audit["retained_evaluable_months"]),
            "audit_interpretation": "bound pre-effect source-isolation audit; no full-package qualification claim"
        },
        "input_path": str(source), "input_sha256": expected["input"][1],
        "helper_path": str(expected["helper"][0]), "helper_sha256": expected["helper"][1],
        "runner_path": str(Path(__file__).resolve()), "runner_sha256": expected["runner"][1],
        "row_count": len(rows), "retained_date_count": EXPECTED_MONTHS,
        "actual_nonempty_date_count": EXPECTED_MONTHS-len(combined_blocked),
        "original_full_month_blocked_months": sorted(original_blocked),
        "source_integrity_blocked_months": sorted(source_blocked),
        "combined_blocked_months": sorted(combined_blocked),
        "supported_period_counts": audit["period_support"],
        "evaluable_date_count": len(audit["retained_evaluable_months"]),
        "evaluable_date_ranges": [
            ["2016-08", "2016-10"], ["2020-07", "2025-12"]
        ],
        "adjacent_evaluable_target_replacement_pairs": _consecutive_month_pairs(audit["retained_evaluable_months"]),
    }
    out_path.mkdir(parents=True, exist_ok=False)
    (out_path / "per_month.json").write_text(json.dumps(monthly, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_path / "performance.json").write_text(json.dumps(performance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_csv(out_path / "new_weights.csv", by_month, weights_by_month)
    return {"status": "completed", "output_directory": str(out_path.resolve()), "rows": len(rows), "months": EXPECTED_MONTHS}


def _synthetic_test(design, design_sha, helpers, audit_path, audit):
    panel = []
    for i in range(10):
        code = f"sh.600{i+1:03d}"
        panel.append({"month": "2015-01", "code": code, "eligibility_reason": "eligible",
                      "momentum": .20 if i in (0, 1) else .10 - i * .005,
                      "vol60": .30 if i == 0 else .20 if i == 1 else .10 + i * .01,
                      "future_return": None if i == 0 else (-.10 if i == 1 else .05),
                      "outcome_reason": "synthetic_missing" if i == 0 else "observed",
                      "entry_halt": i == 0, "exit_halt": i == 1, "either_halt": i in (0, 1),
                      "suspension_marked_price_proxy": i in (0, 1)})
    w, elig = _weights(panel)
    assert [r["code"] for r in sorted(panel, key=lambda r: (-r["momentum"], r["code"]))[:2]] == ["sh.600001", "sh.600002"]
    # Changing future values must not affect any target weight.
    changed = [dict(r, future_return=.99 if r["future_return"] is None else -r["future_return"],
                    outcome_reason="synthetic_changed", entry_halt=not r["entry_halt"],
                    exit_halt=not r["exit_halt"], either_halt=not r["either_halt"])
               for r in panel]
    w_changed, _ = _weights(changed)
    assert w == w_changed
    assert _nullable_number("0.12", "proxy") == .12 and _nullable_number("", "proxy") is None
    try:
        _nullable_number("n/a", "proxy")
    except ValueError:
        invalid_proxy_rejected = True
    else:
        invalid_proxy_rejected = False
    assert invalid_proxy_rejected
    mini_dates = [{"decision_date": "2015-01-02", "entry_date": "2015-01-05", "exit_date": "2015-01-30"}]
    _validate_month_calendar("2015-01", mini_dates)
    try:
        _validate_month_calendar("2015-01", [dict(mini_dates[0], entry_date="2015-02-02")])
    except ValueError:
        date_consistency_rejected = True
    else:
        date_consistency_rejected = False
    assert date_consistency_rejected
    _validate_output_binding("/tmp/new-output", Path("/tmp/new-output"))
    try:
        _validate_output_binding("/tmp/frozen-output", Path("/tmp/other-output"))
    except ValueError:
        output_mismatch_rejected = True
    else:
        output_mismatch_rejected = False
    assert output_mismatch_rejected
    out = {r["code"]: (r["future_return"], r["outcome_reason"]) for r in panel}
    halts = {r["code"]: (r["entry_halt"], r["exit_halt"]) for r in panel}
    mom = helpers._weighted_outcome(w["momentum_top20"], out, halts)
    mom75 = helpers._weighted_outcome(w["momentum75"], out, halts)
    assert abs(mom["unknown_weight"] - .5) < 1e-12
    assert abs(mom["scenario_zero"] - (-.05)) < 1e-12
    assert abs(mom75["unknown_weight"] - .375) < 1e-12
    assert abs(math.fsum(w["momentum75"].values()) - .75) < 1e-12
    assert abs(mom75["scenario_zero"] - (-.0375)) < 1e-12
    assert abs(mom["entry_halt_weight"] - .5) < 1e-12 and abs(mom["exit_halt_weight"] - .5) < 1e-12
    assert abs(mom["entry_halt_weight"] - mom75["entry_halt_weight"] / .75) < 1e-12
    turnover = helpers._turnover({"sh.600001": .5, "sh.600002": .5}, {"sh.600001": .5, "sh.600003": .5})
    assert abs(turnover - .5) < 1e-12
    equal = [dict(r, future_return=.05) for r in panel]
    equal_w, _ = _weights(equal)
    equal_out = {r["code"]: (r["future_return"], "observed") for r in equal}
    pool = helpers._weighted_outcome(equal_w["pool_equal"], equal_out)
    lowvol = helpers._weighted_outcome(equal_w["lowvol_top20"], equal_out)
    mom_cash = helpers._weighted_outcome(equal_w["momentum75"], equal_out)
    assert abs(pool["scenario_zero"] - .05) < 1e-12
    assert abs(lowvol["scenario_zero"] - .05) < 1e-12
    assert abs(mom_cash["scenario_zero"] - .0375) < 1e-12
    synthetic_month, _ = _monthly_row("2015-01", equal, None, helpers, blocked=False)
    assert (synthetic_month["methods"]["momentum_top20"]["observed_best_decile_name_share_selected"] ==
            synthetic_month["methods"]["momentum75"]["observed_best_decile_name_share_selected"])
    negative_equal = [dict(r, future_return=-.01) for r in panel]
    negative_month, _ = _monthly_row("2015-01", negative_equal, None, helpers, blocked=False)
    assert negative_month["methods"]["pool_equal"]["scenario_zero"] < 0
    assert negative_month["observed_outcome_count"] == 10
    blocked_panel = [dict(r, weight_momentum_top20="0") for r in panel]
    assert _original_month_blocked(blocked_panel)
    blocked_month, empty_weights = _monthly_row("2015-01", blocked_panel, None, helpers, blocked=True)
    assert blocked_month["original_full_month_blocked"]
    assert all(not empty_weights[m] for m in METHODS)
    assert all(blocked_month["methods"][m]["scenario_zero"] is None for m in METHODS)
    assert all(blocked_month["methods"][m]["selected_count"] == 0 and
               blocked_month["methods"][m]["empty_selection"] for m in METHODS)
    source_blocked_month, source_empty_weights = _monthly_row(
        "2015-01", panel, None, helpers, blocked=True,
        original_blocked=False, source_integrity_blocked=True)
    assert not source_blocked_month["original_full_month_blocked"]
    assert source_blocked_month["source_integrity_blocked"] and source_blocked_month["combined_blocked"]
    assert all(source_blocked_month["methods"][m]["scenario_zero"] is None for m in METHODS)
    assert source_blocked_month["best_observed_decile_count"] == 0
    assert all(source_blocked_month["methods"][m]["observed_best_decile_name_share_selected"] is None and
               source_blocked_month["methods"][m]["selected_count"] == 0 for m in METHODS)
    source_active_after, _ = _monthly_row("2015-02", panel, None, helpers, blocked=False,
                                          original_blocked=False, source_integrity_blocked=False)
    source_pair_perf = _performance([source_blocked_month, source_active_after], helpers,
                                    {"question": "synthetic", "evaluation": {"primary_measure": "synthetic"}})
    source_detail = source_pair_perf["methods"]["momentum_top20"]
    assert source_detail["original_full_month_blocked_count"] == 0
    assert source_detail["source_integrity_blocked_count"] == 1
    assert source_detail["combined_blocked_count"] == 1
    assert source_active_after["methods"]["momentum_top20"]["target_replacement_turnover"] is None
    active_after_block, _ = _monthly_row("2015-02", panel, None, helpers, blocked=False)
    assert active_after_block["methods"]["momentum_top20"]["target_replacement_turnover"] is None
    two_month_performance = _performance([blocked_month, active_after_block], helpers,
                                         {"question": "synthetic", "evaluation": {"primary_measure": "synthetic"}})
    assert "momentum_lowvol_minus_lowvol_top20" in two_month_performance["primary_increment"]
    lowvol_detail = two_month_performance["methods"]["lowvol_top20"]["all_months"]
    assert lowvol_detail["scenario_zero"]["defined_months"] == 1
    assert lowvol_detail["mean_selected_count"] == 2
    assert two_month_performance["methods"]["lowvol_top20"]["retained_date_count"] == 2
    assert two_month_performance["methods"]["lowvol_top20"]["actual_nonempty_date_count"] == 1
    relative = helpers._relative_unknown(w["momentum_lowvol"], w["momentum_top20"], out)
    assert relative is not None and "adverse_unknown_minus100_or_zero" in relative
    block = helpers._blocks([-.1, 0, .1, None], [2], 20, 20261020)["2"]
    assert block["draws_requested"] == 20 and block["valid_draws"] > 0
    evaluable_set = set(audit["retained_evaluable_months"])
    axis132 = [1.0 if month in evaluable_set else None for month in _months()]
    assert len(axis132) == 132 and sum(x is not None for x in axis132) == 69
    double_axis132 = [None if x is None else 2*x for x in axis132]
    paired_blocks = helpers._blocks(axis132, [12, 24], 100, 20261020)
    paired_double_blocks = helpers._blocks(double_axis132, [12, 24], 100, 20261020)
    for length in ("12", "24"):
        assert paired_blocks[length]["valid_draws"] == paired_double_blocks[length]["valid_draws"]
        assert paired_blocks[length]["finite_months_range"] == paired_double_blocks[length]["finite_months_range"]
        lo, hi = paired_blocks[length]["percentile_95"]
        lo2, hi2 = paired_double_blocks[length]["percentile_95"]
        assert abs(lo2-2*lo) < 1e-12 and abs(hi2-2*hi) < 1e-12
    assert len(audit["retained_evaluable_months"]) == 69
    assert len(audit["combined_blocked_months"]) == 63
    return {
        "schema": "saved-selection-synthetic-checks/1",
        "status": "passed",
        "mode": "synthetic_only_no_real_panel_opened",
        "design_path": str(DESIGN_PATH), "design_sha256": design_sha,
        "source_integrity_audit_path": str(audit_path), "source_integrity_audit_sha256": sha256_file(audit_path),
        "source_integrity_isolation": {
            "audit_guard_status": audit["fresh_all_600_guard"]["status"],
            "original_full_month_blocked_months": audit["original_blocked_months"],
            "source_integrity_blocked_months": audit["integrity_blocked_months"],
            "combined_blocked_months": audit["combined_blocked_months"],
            "retained_counts": audit["retained_counts"],
            "period_support": audit["period_support"],
            "evaluable_date_count": len(audit["retained_evaluable_months"]),
            "evaluable_date_ranges": [["2016-08", "2016-10"], ["2020-07", "2025-12"]],
            "adjacent_evaluable_target_replacement_pairs": _consecutive_month_pairs(audit["retained_evaluable_months"]),
            "audit_interpretation": "registered source-isolation audit evidence; this synthetic check does not recompute or upgrade the audit claim"
        },
        "helper_path": design["helper"]["path"], "helper_sha256": design["helper"]["sha256"],
        "source_path_expected_but_not_opened": design["source"]["path"],
        "source_sha256_expected_but_not_verified_or_opened": design["source"]["sha256"],
        "runner_path": str(Path(__file__).resolve()), "runner_sha256": sha256_file(Path(__file__).resolve()),
        "checks": {
            "momentum_tie_break_code_ascending": "passed",
            "future_return_changes_do_not_change_weights": "passed",
            "unknown_outcome_keeps_original_target_weight_without_renormalizing": "passed",
            "momentum75_cash_weight_25pct_zero_return": "passed",
            "entry_and_exit_halt_weights_remain_flagged": "passed",
            "target_replacement_turnover": "passed",
            "equal_outcomes_produce_equal_fully_invested_returns": "passed",
            "observed_best_decile_is_not_assumed_positive": "passed",
            "momentum75_same_name_hit_rate_as_full_momentum": "passed",
            "original_all_zero_month_stays_blocked_and_empty": "passed",
            "blocked_previous_month_has_unknown_turnover": "passed",
            "paired_unknown_scenario_coefficients": "passed",
            "circular_month_block_helper_determinism_and_shape": "passed",
            "lowvol_comparator_and_full_performance_path": "passed",
            "nullable_numeric_suspension_proxy": "passed",
            "blocked_month_excluded_from_selection_means": "passed",
            "monthly_date_consistency_is_enforced": "passed",
            "future_and_outcome_halt_changes_do_not_change_weights": "passed",
            "best_observed_decile_positive_count_recorded": "passed",
            "paired_scenario_support_and_return_identity": "passed",
            "real_output_path_contract_binding": "passed",
            "source_integrity_month_blocked_for_all_methods": "passed",
            "blocked_month_best_decile_hit_share_is_null": "passed",
            "original_and_source_block_reasons_separated": "passed",
            "replacement_after_source_block_is_unknown": "passed",
            "source_audit_count_and_period_support": "passed",
            "132_date_shared_block_support_same_seed": "passed"
        },
        "synthetic_results": {
            "momentum_top20_weights": w["momentum_top20"],
            "momentum_top20_scenario_zero": mom["scenario_zero"],
            "momentum_top20_unknown_weight": mom["unknown_weight"],
            "momentum75_weights": w["momentum75"],
            "momentum75_cash_weight": .25,
            "momentum75_scenario_zero": mom75["scenario_zero"],
            "momentum75_unknown_weight": mom75["unknown_weight"],
            "replacement_turnover_example": turnover,
            "equal_outcome_pool_and_lowvol": {"pool_equal": pool["scenario_zero"], "lowvol_top20": lowvol["scenario_zero"]},
            "negative_observed_best_decile_fixture_pool_return": negative_month["methods"]["pool_equal"]["scenario_zero"],
            "blocked_month_target_weight_sum": 0.0,
            "turnover_after_blocked_month": None,
            "observed_best_decile_can_be_negative": True
        }
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--self-test", action="store_true", help="run synthetic checks only and write the contract-bound synthetic receipt")
    group.add_argument("--contract", type=Path, help="frozen run contract for real saved-panel diagnostic")
    parser.add_argument("--out", type=Path, help="new output directory; required with --contract")
    args = parser.parse_args(argv)
    try:
        design, design_sha = load_design()
        audit_path, audit = load_source_isolation(design)
        helpers = load_helpers(design)
        if args.self_test:
            if args.out is not None:
                raise ValueError("--out is not accepted with --self-test")
            result = _synthetic_test(design, design_sha, helpers, audit_path, audit)
            SELF_TEST_OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"status": result["status"], "output": str(SELF_TEST_OUTPUT), "checks": len(result["checks"])}, ensure_ascii=False))
            return 0
        if args.out is None:
            raise ValueError("--contract requires --out NEW_DIRECTORY")
        result = _run_real(args.contract.expanduser().resolve(), args.out.expanduser().resolve())
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(f"defensive_diagnostic: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
