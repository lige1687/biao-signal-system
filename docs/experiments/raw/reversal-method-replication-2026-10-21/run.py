"""Frozen, review-gated local short-term-reversal method replication.

This program computes research quote comparisons only. It does not change LEI
rules, infer fills, or authorize trading. The market-data branch requires a
separate root execution-review.json with exact design and source hashes.
"""
from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

HERE = Path(__file__).resolve().parent
DESIGN_PATH = HERE / "design.json"
_DESIGN_FOR_ROOT = json.loads(DESIGN_PATH.read_text())
ROOT = Path(_DESIGN_FOR_ROOT["source_code"][0]["path"]).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

import lei_signal.research.fip as fip_module  # noqa: E402
import lei_signal.research.high52_revalidation as high52_module  # noqa: E402
import lei_signal.research.output_storage as output_storage_module  # noqa: E402
import lei_signal.research.short_reversal_selection as reversal_module  # noqa: E402
from lei_signal.research.fip import SOURCE_FIELDS, hac_mean, month_add  # noqa: E402
from lei_signal.research.high52_revalidation import (  # noqa: E402
    ADJUSTMENT_FIELDS,
    adapt_back_adjusted,
    adjusted_future_outcome,
)
from lei_signal.research.output_storage import recheck_saved_plan  # noqa: E402
from lei_signal.research.short_reversal_selection import (  # noqa: E402
    decomposition,
    monthly_features,
    weighted_month,
    weighted_turnover,
)

STORAGE_PATH = HERE / "storage-plan.json"
REVIEW_PATH = HERE / "execution-review.json"
ARMS = ("all", "loser", "winner", "lowvol")
COMPARISONS = (("loser", "all"), ("winner", "all"), ("lowvol", "all"),
               ("loser", "winner"), ("loser", "lowvol"))
GREEN_REASONS = {"not_green", "green_unknown"}

_SOURCE_ROOT = (ROOT / "src").resolve()
for _module in (fip_module, high52_module, output_storage_module, reversal_module):
    if not Path(_module.__file__).resolve().is_relative_to(_SOURCE_ROOT):
        raise RuntimeError(f"research helper imported outside bound source root: {_module.__file__}")


def sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_bound(ref: Mapping) -> dict:
    path = Path(ref["path"])
    if sha256(path) != ref["sha256"]:
        raise ValueError(f"bound input SHA-256 mismatch: {path}")
    return json.loads(path.read_text())


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, (float, np.floating)):
        return float(value) if math.isfinite(value) else None
    if isinstance(value, np.integer):
        return int(value)
    return value


def write_json(path: Path, value) -> None:
    with path.open("x") as stream:
        json.dump(clean(value), stream, ensure_ascii=False, indent=2, allow_nan=False)


def write_csv(path: Path, rows: Sequence[Mapping]) -> None:
    columns = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns or ["empty"])
        writer.writeheader()
        for row in rows:
            normalized = clean(dict(row))
            writer.writerow({
                key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
                for key, value in normalized.items()
            })


def remove_only_green_qualifiers(feature: Mapping) -> dict:
    """Retain every upstream failure except the two explicitly waived colors."""
    result = dict(feature)
    reasons = set(feature.get("reasons", ()))
    result["original_reasons"] = sorted(reasons)
    remaining = reasons - GREEN_REASONS
    result["eligibility_reasons"] = sorted(remaining)
    result["eligible"] = not remaining
    return result


def select_exchange_month(features: Sequence[Mapping], min_n: int = 30) -> dict:
    """Make stable, independent exchange portfolios from pre-outcome features."""
    eligible = [row for row in features if row.get("eligible")]
    if len({row["code"] for row in eligible}) != len(eligible):
        raise ValueError("duplicate eligible code in exchange-month")
    if len(eligible) < min_n:
        return {"eligible_n": len(eligible), "k": None, "weights": {},
                "reason": "eligible_below_30"}
    if any(not all(math.isfinite(float(row[key])) for key in ("hot", "momentum", "vol60"))
           for row in eligible):
        raise ValueError("eligible feature contains non-finite score")
    n = len(eligible)
    k = math.ceil(n / 10)
    low_hot = sorted(eligible, key=lambda row: (float(row["hot"]), row["code"]))
    high_hot = sorted(eligible, key=lambda row: (-float(row["hot"]), row["code"]))
    low_vol = sorted(eligible, key=lambda row: (float(row["vol60"]), row["code"]))
    return {
        "eligible_n": n,
        "k": k,
        "reason": "",
        "weights": {
            "all": {row["code"]: 1 / n for row in eligible},
            "loser": {row["code"]: 1 / k for row in low_hot[:k]},
            "winner": {row["code"]: 1 / k for row in high_hot[:k]},
            "lowvol": {row["code"]: 1 / k for row in low_vol[:k]},
        },
    }


def lag_endpoints(month: str, lag: int, first_trading_day: Mapping[str, str]) -> tuple[str, str]:
    """Return first-session entry/exit for the frozen lag convention."""
    if lag not in (0, 1):
        raise ValueError("only preplanned lag 0 and 1 are permitted")
    entry_month = month_add(month, 1 + lag)
    exit_month = month_add(month, 2 + lag)
    try:
        return first_trading_day[entry_month], first_trading_day[exit_month]
    except KeyError as exc:
        raise ValueError(f"missing scheduled outcome month: {exc.args[0]}") from exc


def cost_at_25bps_per_side(turnover_gross: float | None,
                           liquidation_gross: float = 0.0) -> float | None:
    """Quoted one-side cost approximation; unknown turnover stays unknown."""
    if turnover_gross is None:
        return None
    return (float(turnover_gross) + float(liquidation_gross)) * 0.0025


def average_ranks(values: Sequence[float]) -> np.ndarray:
    """Ascending average ranks for ties, matching standard Spearman ranks."""
    x = np.asarray(values, dtype=float)
    order = np.argsort(x, kind="stable")
    ranks = np.empty(len(x), dtype=float)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and x[order[j]] == x[order[i]]:
            j += 1
        ranks[order[i:j]] = ((i + 1) + j) / 2
        i = j
    return ranks


def _residual_corr(x: np.ndarray, y: np.ndarray, controls: np.ndarray) -> tuple[float | None, str]:
    if len(x) <= controls.shape[1] or np.linalg.matrix_rank(controls) < controls.shape[1]:
        return None, "rank_deficient"
    xr = x - controls @ np.linalg.lstsq(controls, x, rcond=None)[0]
    yr = y - controls @ np.linalg.lstsq(controls, y, rcond=None)[0]
    if np.linalg.norm(xr) < 1e-9 or np.linalg.norm(yr) < 1e-9:
        return None, "rank_deficient"
    return float(np.corrcoef(xr, yr)[0, 1]), ""


def ranked_association(features: Sequence[Mapping], outcomes: Mapping[str, Mapping]) -> dict:
    """Raw and partial Spearman association, with no dummy/empty group columns."""
    common = sorted((row for row in features if row.get("eligible")
                     and outcomes.get(row["code"], {}).get("return") is not None),
                    key=lambda row: row["code"])
    n = len(common)
    answer = {"n": n, "raw": None, "partial_momentum_vol60": None,
              "raw_reason": "", "partial_reason": ""}
    if n < 3:
        answer.update(raw_reason="insufficient_common", partial_reason="insufficient_common")
        return answer
    x = average_ranks([-float(row["hot"]) for row in common])
    y = average_ranks([float(outcomes[row["code"]]["return"]) for row in common])
    m = average_ranks([float(row["momentum"]) for row in common])
    v = average_ranks([float(row["vol60"]) for row in common])
    answer["raw"], answer["raw_reason"] = _residual_corr(x, y, np.ones((n, 1)))
    answer["partial_momentum_vol60"], answer["partial_reason"] = _residual_corr(
        x, y, np.column_stack((np.ones(n), m, v)))
    return answer


def outcome_ranks_and_capture(features: Sequence[Mapping], outcomes: Mapping[str, Mapping],
                              weights: Mapping[str, float]) -> dict:
    known = sorted((code for code in weights if outcomes.get(code, {}).get("return") is not None),
                   key=lambda code: (-float(outcomes[code]["return"]), code))
    all_known = sorted((row["code"] for row in features if row.get("eligible")
                        and outcomes.get(row["code"], {}).get("return") is not None),
                       key=lambda code: (-float(outcomes[code]["return"]), code))
    top = set(all_known[:math.ceil(len(all_known) / 10)]) if all_known else set()
    winners20 = {code for code in all_known if float(outcomes[code]["return"]) >= .20}
    return {
        "known_top_decile_capture": len(set(weights) & top) / len(top) if top else None,
        "top_decile_known_denominator": len(all_known),
        "known_20pct_winner_capture": len(set(weights) & winners20) / len(winners20) if winners20 else None,
        "winner20_known_denominator": len(winners20),
    }


def prepare_selection(features: Sequence[Mapping], min_n: int = 30) -> dict:
    """Selection API deliberately accepts features only; no outcome argument."""
    return select_exchange_month(features, min_n=min_n)


def _paired_difference(left: Mapping, right: Mapping, field: str) -> float | None:
    a, b = left.get(field), right.get(field)
    return None if a is None or b is None else float(a) - float(b)


def common_gross_net_difference(left: Mapping, right: Mapping) -> tuple[float | None, float | None]:
    """Return complete-sample gross, cost-sample gross, and matched net differences."""
    gross = _paired_difference(left, right, "complete_return")
    net = _paired_difference(left, right, "after_cost_25bps")
    gross_on_net_sample = gross if gross is not None and net is not None else None
    return gross, gross_on_net_sample, net


def rebalance_turnover(month_index: int, previous_weights: Mapping | None,
                       previous_outcomes: Mapping | None, target_weights: Mapping) -> dict:
    """Initial month buys once; only missing later history creates unknown turnover."""
    if not target_weights:
        return {"traded_gross": None, "half_l1": None, "reason": "no_qualified_weights"}
    if month_index == 0:
        return {"traded_gross": 1.0, "half_l1": 1.0, "reason": "initial_purchase"}
    if previous_weights is None:
        return {"traded_gross": None, "half_l1": None, "reason": "no_qualified_prior_month"}
    return weighted_turnover(previous_weights, previous_outcomes, target_weights)


def _stats(axis: Sequence[float | None]) -> dict:
    return hac_mean(axis, lag=6)


def summarize_axis(axis: Sequence[str], values: Sequence[float | None], periods: Sequence[Sequence[str]]) -> dict:
    return {
        "all": _stats(values),
        "periods": {f"{start}..{end}": _stats([v for m, v in zip(axis, values) if start <= m <= end])
                    for start, end in periods},
        "years": {str(year): _stats([v for m, v in zip(axis, values) if m.startswith(str(year))])
                  for year in range(int(axis[0][:4]), int(axis[-1][:4]) + 1)} if axis else {},
        "calendar_axis_length": len(axis),
        "missing_months": sum(v is None for v in values),
    }


def _bound_inputs(design: Mapping) -> tuple[dict, list[str], list[str]]:
    manifest = read_bound(design["sources"]["new_source_manifest"])
    cohort = read_bound(design["sources"]["cohort"])
    calendar_payload = read_bound(design["sources"]["calendar"])
    if manifest.get("schema") != "high52-new-source-manifest/1":
        raise ValueError("unexpected fixed-cohort source manifest schema")
    asset_sources = manifest.get("asset_sources", {})
    if len(asset_sources) != 300 or len(set(asset_sources)) != 300:
        raise ValueError("bound source manifest does not contain exactly 300 unique codes")
    if cohort.get("fields", [])[:1] != ["code"]:
        raise ValueError("unexpected historical cohort schema")
    cohort_codes = {row[0] for row in cohort.get("data", []) if isinstance(row, list) and row}
    if not set(asset_sources).issubset(cohort_codes):
        raise ValueError("source manifest includes a code outside the bound historical cohort")
    if manifest.get("summary", {}).get("failed_queries") != 0:
        raise ValueError("source manifest records failed acquisition queries")
    calendar = [row[0] for row in calendar_payload["data"] if row[1] == "1"]
    if calendar != sorted(set(calendar)):
        raise ValueError("trading calendar is not sorted and unique")
    return manifest, calendar, sorted(asset_sources)


def _verify_bindings(design: Mapping) -> dict:
    checked = {"source_code": {}, "strategy_sources": {}}
    for category in checked:
        for binding in design.get(category, []):
            path = Path(binding["path"])
            actual = sha256(path)
            if actual != binding["sha256"]:
                raise ValueError(f"bound {category} file changed: {path}")
            checked[category][str(path)] = actual
    return checked


def _check_execution_review() -> tuple[dict, dict, dict]:
    design = json.loads(DESIGN_PATH.read_text())
    if design.get("schema") != "reversal-method-replication/1" or design.get("state") != "design_frozen_execution_pending_review":
        raise ValueError("design schema/state is not frozen for this runner")
    source_hashes = _verify_bindings(design)
    if sha256(STORAGE_PATH) != design["storage_plan"]["sha256"]:
        raise ValueError("frozen storage plan hash changed")
    storage_plan = json.loads(STORAGE_PATH.read_text())
    if Path(design["storage_plan"]["path"]) != STORAGE_PATH:
        raise ValueError("design points at a different saved storage plan")
    if not REVIEW_PATH.is_file():
        raise ValueError("root execution-review.json is required before --run")
    review = json.loads(REVIEW_PATH.read_text())
    required = {
        "accepted": True,
        "run_sha256": sha256(Path(__file__)),
        "design_sha256": sha256(DESIGN_PATH),
    }
    if any(review.get(key) != value for key, value in required.items()):
        raise ValueError("execution review must accept the exact run.py and design hashes")
    if not design.get("root_review_required_before_effects"):
        raise ValueError("design review gate must remain enabled")
    rechecked = recheck_saved_plan(ROOT, storage_plan, storage_plan["task_id"],
                                  storage_plan["estimated_bytes"],
                                  storage_plan["internal_metadata_bytes"])
    return design, source_hashes, rechecked


def _source_row(code: str, refs: Mapping, calendar: Sequence[str]) -> dict:
    if refs["daily"].get("status") != "ok" or refs["adjustments"].get("status") != "ok":
        raise ValueError(f"source manifest does not qualify both saved inputs: {code}")
    daily = read_bound(refs["daily"])
    actions = read_bound(refs["adjustments"])
    if daily.get("fields") != list(SOURCE_FIELDS):
        raise ValueError(f"daily schema mismatch: {code}")
    if actions.get("fields") != list(ADJUSTMENT_FIELDS):
        raise ValueError(f"corporate-action schema mismatch: {code}")
    return adapt_back_adjusted(daily, actions, code, calendar, factor_field="foreAdjustFactor")


def _market_run(design: Mapping, source_hashes: Mapping, storage_plan: Mapping) -> dict:
    manifest, calendar, codes = _bound_inputs(design)
    ends: dict[str, str] = {}
    firsts: dict[str, str] = {}
    for day in calendar:
        ends[day[:7]] = day
        firsts.setdefault(day[:7], day)
    axis = []
    month = design["first_month"]
    while month <= design["last_month"]:
        axis.append(month)
        month = month_add(month, 1)
    if len(axis) != 131:
        raise ValueError("frozen 2014-12..2025-10 monthly axis must contain 131 slots")

    features_by_exchange_month: dict[tuple[str, str], list[dict]] = defaultdict(list)
    eligible_feature_by_code_month: dict[tuple[str, str], dict] = {}
    features_rows, source_checks = [], []
    for index, code in enumerate(codes, 1):
        adapted = _source_row(code, manifest["asset_sources"][code], calendar)
        original = monthly_features(adapted, calendar, code,
                                    design["first_month"], design["last_month"])
        for row in original:
            cooked = remove_only_green_qualifiers(row)
            cooked["exchange"] = code.split(".", 1)[0]
            features_rows.append(cooked)
            features_by_exchange_month[(cooked["exchange"], cooked["month"])].append(cooked)
            if cooked["eligible"]:
                eligible_feature_by_code_month[(code, cooked["month"])] = cooked
        source_checks.append({
            "code": code,
            "daily_sha256": manifest["asset_sources"][code]["daily"]["sha256"],
            "adjustments_sha256": manifest["asset_sources"][code]["adjustments"]["sha256"],
            "daily_rows": adapted["source_rows"],
            "adjustment_rows": adapted["action_rows"],
            "break_dates": adapted["break_dates"],
            "failures": adapted["failures"],
        })
        if index % 50 == 0:
            print(f"source-qualified {index}/300", flush=True)
        del adapted
        if index % 50 == 0:
            gc.collect()

    selections: dict[tuple[str, str], dict] = {}
    weight_rows = []
    for exchange in ("sh", "sz"):
        for month in axis:
            rows = features_by_exchange_month.get((exchange, month), [])
            selection = prepare_selection(rows, min_n=30)
            selections[(exchange, month)] = selection
            score_by_code = {row["code"]: row for row in rows if row["eligible"]}
            for arm in ARMS:
                for code, weight in selection["weights"].get(arm, {}).items():
                    score = score_by_code[code]
                    weight_rows.append({"exchange": exchange, "month": month, "arm": arm,
                                        "code": code, "weight": weight,
                                        "hot": score["hot"], "momentum": score["momentum"],
                                        "vol60": score["vol60"]})

    # Only after every month's weights are fixed do we inspect future quotes.
    outcomes_by_key: dict[tuple[str, str, int], dict[str, dict]] = defaultdict(dict)
    outcomes_rows = []
    for index, code in enumerate(codes, 1):
        adapted = _source_row(code, manifest["asset_sources"][code], calendar)
        exchange = code.split(".", 1)[0]
        for month in axis:
            feature = eligible_feature_by_code_month.get((code, month))
            if feature is None:
                continue
            for lag in (0, 1):
                entry, exit_day = lag_endpoints(month, lag, firsts)
                result = adjusted_future_outcome(adapted, calendar,
                                                 feature["decision_date"], entry, exit_day)
                record = {"exchange": exchange, "month": month, "lag": lag, "code": code,
                          "decision_date": feature["decision_date"],
                          "entry_date": entry, "exit_date": exit_day, **result}
                outcomes_rows.append(record)
                outcomes_by_key[(exchange, month, lag)][code] = record
        if index % 50 == 0:
            print(f"outcomes-qualified {index}/300", flush=True)
        del adapted
        if index % 50 == 0:
            gc.collect()

    monthly_rows, comparison_rows, decomposition_rows = [], [], []
    rank_rows = []
    for exchange in ("sh", "sz"):
        previous_by_lag: dict[int, dict | None] = {0: None, 1: None}
        arm_lookup = {}
        for month in axis:
            rows = features_by_exchange_month.get((exchange, month), [])
            selection = selections[(exchange, month)]
            eligible = [row for row in rows if row["eligible"]]
            for lag in (0, 1):
                outcome_map = outcomes_by_key[(exchange, month, lag)]
                assoc = ranked_association(eligible, outcome_map)
                rank_rows.append({"exchange": exchange, "month": month, "lag": lag, **assoc})
                arms = {}
                for arm in ARMS:
                    weights = selection["weights"].get(arm, {})
                    record = {"exchange": exchange, "month": month, "lag": lag, "arm": arm,
                              "eligible_n": selection["eligible_n"], "k": selection["k"],
                              "selection_reason": selection["reason"], "selected_n": len(weights)}
                    if weights:
                        metrics = weighted_month(weights, outcome_map)
                        sensitive = weighted_month(weights, outcome_map,
                                                    field="adverse_flat_as_unknown_return")
                        previous = previous_by_lag[lag]
                        turnover = rebalance_turnover(
                            axis.index(month),
                            None if previous is None else previous["weights"].get(arm),
                            None if previous is None else previous["outcomes"],
                            weights,
                        )
                        final_liquidation = 1.0 if month == axis[-1] else 0.0
                        record.update(metrics)
                        record.update({
                            "sensitive_complete_return": sensitive["complete_return"],
                            "sensitive_unknown_weight": sensitive["unknown_weight"],
                            "turnover_gross": turnover["traded_gross"],
                            "turnover_reason": turnover.get("reason", ""),
                            "final_liquidation_gross": final_liquidation,
                            "cost_25bps_per_side": cost_at_25bps_per_side(
                                turnover["traded_gross"], final_liquidation),
                            "after_cost_25bps": None if metrics["complete_return"] is None or
                                turnover["traded_gross"] is None else metrics["complete_return"] -
                                cost_at_25bps_per_side(turnover["traded_gross"], final_liquidation),
                            "known_top_decile_capture": outcome_ranks_and_capture(
                                eligible, outcome_map, weights)["known_top_decile_capture"],
                            "top_decile_known_denominator": outcome_ranks_and_capture(
                                eligible, outcome_map, weights)["top_decile_known_denominator"],
                            "known_20pct_winner_capture": outcome_ranks_and_capture(
                                eligible, outcome_map, weights)["known_20pct_winner_capture"],
                            "winner20_known_denominator": outcome_ranks_and_capture(
                                eligible, outcome_map, weights)["winner20_known_denominator"],
                            "momentum_exposure": sum(weight * float(next(r["momentum"] for r in eligible
                                if r["code"] == code)) for code, weight in weights.items()),
                            "vol60_exposure": sum(weight * float(next(r["vol60"] for r in eligible
                                if r["code"] == code)) for code, weight in weights.items()),
                            "hhi": sum(weight * weight for weight in weights.values()),
                        })
                    else:
                        record.update({"known_weighted_contribution": 0.0,
                                       "unknown_weight": None,
                                       "complete_return": None,
                                       "known_weighted_adverse": 0.0,
                                       "unknown_adverse_weight": None,
                                       "mean_adverse": None,
                                       "cost_25bps_per_side": None,
                                       "after_cost_25bps": None,
                                       "turnover_gross": None,
                                       "turnover_reason": "no_qualified_weights"})
                    monthly_rows.append(record)
                    arms[arm] = record
                arm_lookup[(exchange, month, lag)] = arms
                # Keep the immediate prior calendar month state. A gap remains
                # unknown; it must never turn into an artificial initial buy.
                if selection["weights"]:
                    previous_by_lag[lag] = {
                        "weights": selection["weights"],
                        "outcomes": outcome_map,
                        "month": month,
                    }
                else:
                    previous_by_lag[lag] = None

        for lag in (0, 1):
            for left, right in COMPARISONS:
                vals = []
                gross_on_net_vals = []
                net_vals = []
                for month in axis:
                    left_row = arm_lookup[(exchange, month, lag)][left]
                    right_row = arm_lookup[(exchange, month, lag)][right]
                    # Primary gross uses all paired complete-return months.
                    # gross_on_net_sample and net use the same narrower cost-known months.
                    gross_diff, gross_on_net_diff, net_diff = common_gross_net_difference(
                        left_row, right_row)
                    vals.append(gross_diff)
                    gross_on_net_vals.append(gross_on_net_diff)
                    net_vals.append(net_diff)
                comparison_rows.append({"exchange": exchange, "lag": lag,
                                        "comparison": f"{left}_minus_{right}",
                                        "gross": summarize_axis(axis, vals, design["inference"]["periods"]),
                                        "gross_on_net_sample": summarize_axis(
                                            axis, gross_on_net_vals, design["inference"]["periods"]),
                                        "after_cost_25bps": summarize_axis(
                                            axis, net_vals, design["inference"]["periods"]),
                                        "monthly_values": vals,
                                        "monthly_after_cost_values": net_vals})
            # The preplanned decay comparison uses only common complete loser
            # and winner portfolios at both lags, preserving paired months.
        decay = []
        for month in axis:
            l0 = arm_lookup[(exchange, month, 0)]
            l1 = arm_lookup[(exchange, month, 1)]
            if all(lag_rows[arm]["complete_return"] is not None
                   for lag_rows in (l0, l1) for arm in ("loser", "winner")):
                decay.append((l0["loser"]["complete_return"] - l0["winner"]["complete_return"]) -
                             (l1["loser"]["complete_return"] - l1["winner"]["complete_return"]))
            else:
                decay.append(None)
        comparison_rows.append({"exchange": exchange, "lag": "decay_0_minus_1",
                                "comparison": "(loser_minus_winner)_lag0_minus_lag1",
                                "gross": summarize_axis(axis, decay, design["inference"]["periods"]),
                                "monthly_values": decay})

        for lag in (0, 1):
            for month in axis:
                arms = arm_lookup[(exchange, month, lag)]
                outcome_map = outcomes_by_key[(exchange, month, lag)]
                if not selections[(exchange, month)]["weights"]:
                    continue
                eligible = [row for row in features_by_exchange_month[(exchange, month)]
                            if row["eligible"]]
                for baseline in ("all", "lowvol"):
                    pieces = decomposition(selections[(exchange, month)]["weights"]["loser"],
                                            selections[(exchange, month)]["weights"][baseline],
                                            outcome_map)
                    decomposition_rows.append({"exchange": exchange, "month": month,
                                               "lag": lag, "baseline": baseline, **pieces})

    output = Path(storage_plan["output"])
    output.mkdir(parents=True, exist_ok=False)
    write_csv(output / "features.csv", features_rows)
    write_csv(output / "outcomes.csv", outcomes_rows)
    write_csv(output / "weights.csv", weight_rows)
    write_csv(output / "monthly.csv", monthly_rows)
    write_csv(output / "comparisons.csv", comparison_rows)
    write_csv(output / "decomposition.csv", decomposition_rows)
    write_csv(output / "rank-association.csv", rank_rows)
    write_csv(output / "sourcechecks.csv", source_checks)
    rank_summary = {}
    for exchange in ("sh", "sz"):
        for lag in (0, 1):
            for key in ("raw", "partial_momentum_vol60"):
                rank_summary[f"{exchange}_{lag}_{key}"] = summarize_axis(
                    axis,
                    [next((row[key] for row in rank_rows
                           if row["exchange"] == exchange and row["month"] == month
                           and row["lag"] == lag), None) for month in axis],
                    design["inference"]["periods"],
                )
    summary = {
        "schema": "reversal-method-replication-result/1",
        "status": "completed_quote_diagnostics",
        "cohorts": "CN300 fixed historical cohort, Shanghai and Shenzhen reported separately",
        "calendar_months": axis,
        "calendar_axis_length": len(axis),
        "eligible_stock_months": sum(row["eligible"] for row in features_rows),
        "source_codes": len(codes),
        "exchange_counts": dict(Counter(code.split(".", 1)[0] for code in codes)),
        "rejection_reasons": dict(Counter(reason for row in features_rows
                                           for reason in row["eligibility_reasons"])),
        "source_break_stocks": sum(bool(row["break_dates"]) for row in source_checks),
        "source_break_days": sum(len(row["break_dates"]) for row in source_checks),
        "mechanism_boundary": design["mechanism_boundary"],
        "comparisons": comparison_rows,
        "rank_association": rank_summary,
        "binding_hashes": {"design": sha256(DESIGN_PATH), "run": sha256(Path(__file__)),
                           "source_code": source_hashes},
        "scope_limit": "historical adjusted quote research; not the original paper population, actual fills, total shareholder return, or account performance",
    }
    write_json(output / "summary.json", summary)
    print(json.dumps({"status": summary["status"], "output": str(output),
                      "months": len(axis), "source_codes": len(codes)}, ensure_ascii=False))
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="requires exact root execution review")
    args = parser.parse_args(argv)
    if not args.run:
        parser.error("no market-data action is implicit; use --run only after root approval")
    design, source_hashes, storage_plan = _check_execution_review()
    _market_run(design, source_hashes, storage_plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
