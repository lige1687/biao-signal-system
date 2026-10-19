#!/usr/bin/env python3
"""Bounded, saved-input-only industry financial-rank gradient diagnostic.

Expected execution contract (all paths and SHA-256 bindings are explicit)::

  {
    "schema": "selection-gradient-run/1",
    "inputs": {
      "design": {"path": ".../selection-gradient-design.json", "sha256": "..."},
      "stock_weights": {"path": ".../stock_weights.csv", "sha256": "..."},
      "core_manifest": {"path": ".../core-01/manifest.json", "sha256": "..."},
      "controller_review": {"path": ".../accepted-review.json", "sha256": "..."}
    },
    "runner": {"path": ".../run_selection_gradient.py", "sha256": "..."},
    "control_contract": {"path": ".../lowfreq-research-control.json", "sha256": "..."},
    "control_module": {"path": ".../lowfreq_research_control.py", "sha256": "..."},
    "storage_module": {"path": ".../output_storage.py", "sha256": "..."},
    "storage_plan": {"path": ".../storage-plan.json", "sha256": "..."},
    "output": {"path": ".../result", "run_directory": "...", "mount": "/Volumes/...",
               "external_device": 123, "external_uuid": "..."},
    "execution_authorized": true,
    "market_data_requests": 0
  }

The review binding is required even for check-only.  This module never fetches
market data; --check-only validates bindings/storage only and does not read the
CSV rows or create an output directory.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


MAIN = Path(__file__).resolve().parents[4]
SCOPES = ("gp", "common_gp", "common_cfo")
PORTFOLIOS = ("P", "M", "F", "B", "D")
GROUPS = (1, 2, 3, 4, 5)  # 1 is lowest financial score; 5 is highest.
SCENARIOS = (("zero", 0.0), ("loss100", -1.0))
EXPECTED_COLUMNS = {
    "scope", "month", "code", "industry", "financial_score", "future_return",
    "sector_n", "weight_P", "weight_M", "weight_F", "weight_B", "weight_D",
}
SEED = 20261019
BLOCKS = (6, 12)
DRAWS = 2000


def sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _finite(value: Any, *, label: str, allow_blank: bool = False) -> float | None:
    if value is None or value == "":
        if allow_blank:
            return None
        raise ValueError(f"missing numeric value: {label}")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid numeric value for {label}: {value!r}") from exc
    if not math.isfinite(number):
        raise ValueError(f"non-finite numeric value for {label}: {value!r}")
    return number


def parse_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    weights: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: {p: 0.0 for p in PORTFOLIOS})
    sector_counts: dict[tuple[str, str, str], int] = defaultdict(int)
    for lineno, raw in enumerate(rows, start=2):
        missing = EXPECTED_COLUMNS - set(raw)
        if missing:
            raise ValueError(f"missing columns at row {lineno}: {sorted(missing)}")
        scope, month, code = str(raw["scope"]), str(raw["month"]), str(raw["code"])
        if scope not in SCOPES or not month or not code:
            raise ValueError(f"invalid identity at row {lineno}: {(scope, month, code)}")
        key = (scope, month, code)
        if key in seen:
            raise ValueError(f"duplicate code within scope/month: {key}")
        seen.add(key)
        industry = str(raw["industry"] or "").strip()
        score = _finite(raw["financial_score"], label=f"financial_score row {lineno}")
        outcome = _finite(raw["future_return"], label=f"future_return row {lineno}", allow_blank=True)
        sector_n_val = _finite(raw["sector_n"], label=f"sector_n row {lineno}")
        if sector_n_val is None or sector_n_val < 1 or int(sector_n_val) != sector_n_val:
            raise ValueError(f"invalid sector_n at row {lineno}: {raw['sector_n']!r}")
        row = {
            "scope": scope, "month": month, "code": code, "industry": industry,
            "financial_score": score, "future_return": outcome,
            "sector_n": int(sector_n_val),
        }
        for portfolio in PORTFOLIOS:
            value = _finite(raw[f"weight_{portfolio}"], label=f"weight_{portfolio} row {lineno}")
            if value is None or value < -1e-12:
                raise ValueError(f"invalid portfolio weight at row {lineno}: {portfolio}={value}")
            row[f"weight_{portfolio}"] = value
            weights[(scope, month)][portfolio] += value
        parsed.append(row)
        sector_counts[(scope, month, industry)] += 1

    if not parsed:
        raise ValueError("input has no stock rows")
    for unit, sums in weights.items():
        for portfolio, total in sums.items():
            if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-8):
                raise ValueError(f"saved portfolio weight sum is not 1: {unit} {portfolio}={total:.17g}")
    for row in parsed:
        actual = sector_counts[(row["scope"], row["month"], row["industry"])]
        if row["industry"] and row["sector_n"] != actual:
            raise ValueError(
                f"sector_n mismatch for {(row['scope'], row['month'], row['industry'])}: "
                f"recorded={row['sector_n']} actual={actual}"
            )
    return parsed


def _partition(scores: list[dict[str, Any]], *, original_n: int | None = None) -> tuple[dict[str, dict[int, float]], list[dict[str, Any]]]:
    """Fractionally overlap exact-score blocks with five equal rank intervals.

    Codes are emitted only as stable identity labels. They never break financial
    ties or determine a group's fraction.
    """
    n = len(scores)
    if n == 0:
        raise ValueError("cannot partition an empty industry")
    original_n = n if original_n is None else original_n
    sorted_scores = sorted(row["financial_score"] for row in scores)
    blocks: list[tuple[float, int, int, list[str]]] = []
    cursor = 0
    while cursor < n:
        score = sorted_scores[cursor]
        end = cursor + 1
        while end < n and sorted_scores[end] == score:
            end += 1
        codes = [row["code"] for row in scores if row["financial_score"] == score]
        blocks.append((score, cursor, end, codes))
        cursor = end

    allocations: dict[str, dict[int, float]] = {row["code"]: {g: 0.0 for g in GROUPS} for row in scores}
    tie_blocks: list[dict[str, Any]] = []
    for score, start, end, codes in blocks:
        block_n = end - start
        overlap_groups = []
        for group in GROUPS:
            lower = (group - 1) * n / 5.0
            upper = group * n / 5.0
            overlap = max(0.0, min(float(end), upper) - max(float(start), lower))
            alpha = overlap / block_n
            if alpha > 0:
                overlap_groups.append(group)
            for code in codes:
                allocations[code][group] = alpha
        for code in codes:
            total = sum(allocations[code].values())
            if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-12):
                raise ValueError(f"quintile alpha does not sum to one: {code}={total}")
        if block_n > 1 and len(overlap_groups) > 1:
            tie_blocks.append({
                "score": score, "tie_count": block_n, "tie_codes": sorted(codes),
                "groups": overlap_groups, "crossed_cut_count": len(overlap_groups) - 1,
                "original_pool_mass": block_n / original_n,
            })
    for group in GROUPS:
        alpha_sum = sum(allocations[row["code"]][group] for row in scores)
        if not math.isclose(alpha_sum, n / 5.0, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"quintile effective count differs from n/5: Q{group}={alpha_sum}, n={n}")
    return allocations, tie_blocks


def analyze_unit(rows: list[dict[str, Any]], *, scope: str, month: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return two scenario rows and sector support/tie details for one scope-month."""
    if rows and all(r["scope"] == scope and r["month"] == month for r in rows):
        unit_rows = rows
    else:
        unit_rows = [r for r in rows if r["scope"] == scope and r["month"] == month]
    if not unit_rows:
        raise ValueError(f"empty scope/month: {(scope, month)}")
    if len({r["code"] for r in unit_rows}) != len(unit_rows):
        raise ValueError(f"duplicate code within scope/month: {(scope, month)}")
    n_total = len(unit_rows)
    by_industry: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in unit_rows:
        by_industry[row["industry"]].append(row)

    group_masses = {group: 0.0 for group in GROUPS}
    supported_n = 0
    support_rows: list[dict[str, Any]] = []
    memberships: dict[str, dict[int, float]] = {}
    sector_weight_by_code: dict[str, float] = {}
    for industry in sorted(by_industry):
        cell = by_industry[industry]
        n_cell = len(cell)
        score_count = len({r["financial_score"] for r in cell})
        mass = n_cell / n_total
        reason = "supported"
        if not industry:
            reason = "missing_industry"
        elif n_cell < 5:
            reason = "sector_n_below_5"
        elif score_count < 2:
            reason = "constant_score"
        allocations: dict[str, dict[int, float]] = {}
        ties: list[dict[str, Any]] = []
        effective_n = [0.0] * 5
        q1_q5_shared_original_mass = 0.0
        q1_q5_shared_target_weight = 0.0
        q1_q5_half_l1 = 0.0
        q1_q5_shared_codes = 0
        q1_q5_differing_codes = 0
        if reason == "supported":
            allocations, ties = _partition(cell, original_n=n_total)
            supported_n += n_cell
            sector_weight = n_cell / n_total
            for group in GROUPS:
                effective_n[group - 1] = sum(allocations[row["code"]][group] for row in cell)
                group_masses[group] += sector_weight
                for row in cell:
                    memberships[row["code"]] = allocations[row["code"]]
                    sector_weight_by_code[row["code"]] = sector_weight
            for row in cell:
                a1 = allocations[row["code"]][1]
                a5 = allocations[row["code"]][5]
                if a1 > 0 and a5 > 0:
                    q1_q5_shared_codes += 1
                    q1_q5_shared_original_mass += 1.0 / n_total
                w1 = sector_weight * a1 / (n_cell / 5.0)
                w5 = sector_weight * a5 / (n_cell / 5.0)
                q1_q5_shared_target_weight += min(w1, w5)
                q1_q5_half_l1 += 0.5 * abs(w1 - w5)
                if not math.isclose(w1, w5, rel_tol=0.0, abs_tol=1e-14):
                    q1_q5_differing_codes += 1
        support_rows.append({
            "row_type": "industry", "scope": scope, "month": month, "industry": industry,
            "sector_n": n_cell, "distinct_scores": score_count,
            "sector_mass": mass, "supported": reason == "supported",
            "exclusion_reason": "" if reason == "supported" else reason,
            **{f"supported_Q{g}_effective_n": effective_n[g - 1] for g in GROUPS},
            "cross_group_tie_block_count": len(ties),
            "cross_group_tie_code_count": len({c for tie in ties for c in tie["tie_codes"]}),
            "cross_group_tie_cut_count": sum(tie["crossed_cut_count"] for tie in ties),
            "cross_group_tie_original_pool_mass": sum(tie["original_pool_mass"] for tie in ties),
            "tie_crossing_cuts": json.dumps(ties, ensure_ascii=False, separators=(",", ":")),
            "q1_q5_shared_constituent_codes": q1_q5_shared_codes,
            "q1_q5_shared_constituent_original_mass": q1_q5_shared_original_mass,
            "q1_q5_shared_target_weight": q1_q5_shared_target_weight,
            "q1_q5_target_half_l1": q1_q5_half_l1,
            "q1_q5_weight_differing_codes": q1_q5_differing_codes,
        })

    rows_by_code = {row["code"]: row for row in unit_rows}
    supported_mass = supported_n / n_total
    for group in GROUPS:
        actual_group_weight = math.fsum(
            sector_weight_by_code[code] * allocations[group] / (rows_by_code[code]["sector_n"] / 5.0)
            for code, allocations in memberships.items() if allocations[group] > 0
        ) if memberships else 0.0
        if not math.isclose(actual_group_weight, supported_mass, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"supported Q{group} weight does not equal supported mass")
    reason_map = {"sector_n_below_5": "small_sector", "constant_score": "constant_score",
                  "missing_industry": "missing_industry"}
    excluded_rows = {
        reason: [r for r in support_rows if r["exclusion_reason"] == reason]
        for reason in reason_map
    }
    month_summary: dict[str, Any] = {
        "row_type": "month", "scope": scope, "month": month, "industry": "",
        "source_n": n_total, "supported_n": supported_n, "supported_mass": supported_mass,
        "excluded_mass": 1.0 - supported_mass,
        "supported_sector_count": sum(r["supported"] for r in support_rows),
        "excluded_sector_count": sum(not r["supported"] for r in support_rows),
        "month_tie_block_count": sum(r["cross_group_tie_block_count"] for r in support_rows),
        "month_tie_code_count": sum(r["cross_group_tie_code_count"] for r in support_rows),
        "month_tie_cut_count": sum(r["cross_group_tie_cut_count"] for r in support_rows),
        "month_tie_original_pool_mass": sum(r["cross_group_tie_original_pool_mass"] for r in support_rows),
        "month_q1_q5_shared_original_mass": sum(r["q1_q5_shared_constituent_original_mass"] for r in support_rows),
        "month_q1_q5_shared_target_weight": sum(r["q1_q5_shared_target_weight"] for r in support_rows),
        "month_q1_q5_target_half_l1": sum(r["q1_q5_target_half_l1"] for r in support_rows),
        "month_q1_q5_shared_constituent_codes": sum(r["q1_q5_shared_constituent_codes"] for r in support_rows),
        "month_q1_q5_weight_differing_codes": sum(r["q1_q5_weight_differing_codes"] for r in support_rows),
    }
    for reason, label in reason_map.items():
        month_summary[f"excluded_{label}_n"] = sum(r["sector_n"] for r in excluded_rows[reason])
        month_summary[f"excluded_{label}_mass"] = sum(r["sector_mass"] for r in excluded_rows[reason])
    support_rows.append(month_summary)
    industry_support_rows = [r for r in support_rows if r["row_type"] == "industry"]
    monthly_rows: list[dict[str, Any]] = []
    for scenario, unknown_value in SCENARIOS:
        result: dict[str, Any] = {
            "row_type": "month",
            "scope": scope, "month": month, "scenario": scenario,
            "source_n": n_total, "supported_n": supported_n, "supported_mass": supported_mass,
            "excluded_mass": 1.0 - supported_mass,
            "supported_sector_count": sum(r["supported"] for r in industry_support_rows),
            "excluded_sector_count": sum(not r["supported"] for r in industry_support_rows),
            "unknown_source_rows": sum(r["future_return"] is None for r in unit_rows),
        }
        for reason, label in reason_map.items():
            rows_for_reason = [r for r in industry_support_rows if r["exclusion_reason"] == reason]
            result[f"excluded_{label}_n"] = sum(r["sector_n"] for r in rows_for_reason)
            result[f"excluded_{label}_mass"] = sum(r["sector_mass"] for r in rows_for_reason)
        supported_rows = [r for r in unit_rows if r["code"] in memberships]
        supported_p_raw = math.fsum((r["future_return"] if r["future_return"] is not None else unknown_value) / n_total
                                    for r in supported_rows)
        supported_p_conditional = supported_p_raw / supported_mass if supported_mass > 0 else None
        result["supported_P_raw_contribution_pct"] = 100.0 * supported_p_raw
        result["supported_P_return_pct"] = 100.0 * supported_p_conditional if supported_p_conditional is not None else None
        group_returns: dict[int, float | None] = {}
        for group in GROUPS:
            contributions: list[float] = []
            group_unknown_mass_parts: list[float] = []
            group_unknown_rows = 0
            group_weight = group_masses[group]
            for code, allocations in memberships.items():
                alpha = allocations[group]
                if alpha <= 0:
                    continue
                row = rows_by_code[code]
                n_sector = row["sector_n"]
                weight = sector_weight_by_code[code] * alpha / (n_sector / 5.0)
                outcome = row["future_return"]
                if outcome is None:
                    outcome = unknown_value
                    group_unknown_mass_parts.append(weight)
                    group_unknown_rows += 1
                contributions.append(weight * outcome)
            raw_contribution = math.fsum(contributions)
            group_unknown_mass = math.fsum(group_unknown_mass_parts)
            conditional = raw_contribution / group_weight if group_weight > 0 else None
            group_returns[group] = conditional
            result[f"supported_Q{group}_raw_contribution_pct"] = 100.0 * raw_contribution
            result[f"supported_Q{group}_return_pct"] = 100.0 * conditional if conditional is not None else None
            result[f"supported_Q{group}_weight"] = group_weight
            result[f"supported_Q{group}_unknown_weight"] = group_unknown_mass
            result[f"supported_Q{group}_unknown_rows"] = group_unknown_rows
        low, high = group_returns[1], group_returns[5]
        result["Q5_minus_Q1_pp"] = 100.0 * (high - low) if low is not None and high is not None else None
        if supported_p_conditional is not None:
            quintile_average = statistics.fmean(group_returns[g] for g in GROUPS)
            if not math.isclose(quintile_average, supported_p_conditional, rel_tol=0.0, abs_tol=1e-10):
                raise ValueError(f"five supported quintiles do not average to supported_P: {scope}/{month}/{scenario}")
        monthly_rows.append(result)
    return monthly_rows, support_rows


def _quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] * (hi - pos) + ordered[hi] * (pos - lo)


def summarize(monthly_rows: list[dict[str, Any]], months: list[str], *, draws: int = DRAWS) -> dict[str, Any]:
    rng = random.Random(SEED)
    draw_matrices: dict[int, list[list[int]]] = {}
    draw_hashes: dict[str, str] = {}
    n = len(months)
    for block in BLOCKS:
        matrix: list[list[int]] = []
        for _ in range(draws):
            positions: list[int] = []
            for _ in range(math.ceil(n / block)):
                start = rng.randrange(n)
                positions.extend((start + j) % n for j in range(block))
            matrix.append(positions[:n])
        draw_matrices[block] = matrix
        draw_hashes[str(block)] = hashlib.sha256(
            json.dumps(matrix, separators=(",", ":")).encode("ascii")
        ).hexdigest()
    summary: dict[str, Any] = {
        "scope": {}, "month_axis": months, "bootstrap": {
            "method": "paired circular month blocks", "block_lengths": list(BLOCKS),
            "draws": draws, "seed": SEED, "interval_percentiles": [2.5, 97.5],
            "shared_date_draw_matrix_sha256": draw_hashes,
        }
    }
    for scope in SCOPES:
        summary["scope"][scope] = {}
        for scenario, _ in SCENARIOS:
            indexed = {(r["month"], r["scenario"]): r for r in monthly_rows if r["scope"] == scope}
            available = [indexed[(m, scenario)] for m in months if (m, scenario) in indexed]
            # The production contract requires the complete 132-month axis.
            if len(available) != len(months):
                raise ValueError(f"incomplete month axis for {(scope, scenario)}: {len(available)}/{len(months)}")
            group_stats: dict[str, Any] = {}
            for group in GROUPS:
                vals = [r[f"supported_Q{group}_return_pct"] for r in available]
                vals_finite = [float(v) for v in vals if v is not None]
                group_stats[f"group{group}"] = {
                    "mean_pct": statistics.fmean(vals_finite) if vals_finite else None,
                    "valid_months": len(vals_finite),
                    "annual_means_pct": _annual_means(months, vals),
                    "period_2015_2019_mean_pct": _period_mean(months, vals, 2015, 2019),
                    "period_2020_2025_mean_pct": _period_mean(months, vals, 2020, 2025),
                    "best_month_pct": max(vals_finite) if vals_finite else None,
                    "worst_month_pct": min(vals_finite) if vals_finite else None,
                }
            diffs = [r["Q5_minus_Q1_pp"] for r in available]
            diff_vals = [float(v) for v in diffs if v is not None]
            pos_share = sum(v > 0 for v in diff_vals) / len(diff_vals) if diff_vals else None
            p_values = [r["supported_P_return_pct"] for r in available]
            block_results = {}
            for block in BLOCKS:
                draw_means: list[float] = []
                all_missing_draws = 0
                for positions in draw_matrices[block]:
                    selected = [diffs[i] for i in positions if diffs[i] is not None]
                    if selected:
                        draw_means.append(statistics.fmean(selected))
                    else:
                        all_missing_draws += 1
                block_results[str(block)] = {
                    "draws_with_values": len(draw_means),
                    "all_missing_draws": all_missing_draws,
                    "interval_pp": [_quantile(draw_means, 0.025), _quantile(draw_means, 0.975)] if draw_means else None,
                }
            supported = [indexed[(m, "zero")] for m in months]
            def coverage_stats(period_rows: list[dict[str, Any]]) -> dict[str, Any]:
                return {
                    "months": len(period_rows),
                    "supported_months": sum(r["supported_mass"] > 0 for r in period_rows),
                    "mean_supported_mass": statistics.fmean(r["supported_mass"] for r in period_rows) if period_rows else None,
                    "source_n": sum(r["source_n"] for r in period_rows),
                    "supported_n": sum(r["supported_n"] for r in period_rows),
                    "excluded_small_sector_n": sum(r["excluded_small_sector_n"] for r in period_rows),
                    "excluded_constant_score_n": sum(r["excluded_constant_score_n"] for r in period_rows),
                    "excluded_missing_industry_n": sum(r["excluded_missing_industry_n"] for r in period_rows),
                }
            coverage_by_year = {
                year: coverage_stats([r for r in supported if r["month"].startswith(year)])
                for year in sorted({m[:4] for m in months})
            }
            coverage_by_period = {
                "2015_2019": coverage_stats([r for r in supported if 2015 <= int(r["month"][:4]) <= 2019]),
                "2020_2025": coverage_stats([r for r in supported if 2020 <= int(r["month"][:4]) <= 2025]),
            }
            summary["scope"][scope][scenario] = {
                "group_returns": group_stats,
                "Q5_minus_Q1_mean_pp": statistics.fmean(diff_vals) if diff_vals else None,
                "Q5_minus_Q1_positive_supported_month_share": pos_share,
                "Q5_minus_Q1_best_supported_month_pp": max(diff_vals) if diff_vals else None,
                "Q5_minus_Q1_worst_supported_month_pp": min(diff_vals) if diff_vals else None,
                "Q5_minus_Q1_annual_means_pp": _annual_means(months, diffs),
                "Q5_minus_Q1_period_2015_2019_mean_pp": _period_mean(months, diffs, 2015, 2019),
                "Q5_minus_Q1_period_2020_2025_mean_pp": _period_mean(months, diffs, 2020, 2025),
                "Q5_minus_Q1_block_intervals_pp": block_results,
                "coverage_by_year": coverage_by_year,
                "coverage_by_period": coverage_by_period,
                "supported_P_mean_pct": statistics.fmean(
                    float(v) for v in p_values if v is not None
                ) if any(v is not None for v in p_values) else None,
                "supported_P_annual_means_pct": _annual_means(months, p_values),
                "supported_P_period_2015_2019_mean_pct": _period_mean(months, p_values, 2015, 2019),
                "supported_P_period_2020_2025_mean_pct": _period_mean(months, p_values, 2020, 2025),
            }
    return summary


def _annual_means(months: list[str], values: list[float | None]) -> dict[str, float | None]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for month, value in zip(months, values):
        if value is not None:
            grouped[month[:4]].append(float(value))
    return {year: statistics.fmean(grouped[year]) if grouped.get(year) else None for year in sorted({m[:4] for m in months})}


def _period_mean(months: list[str], values: list[float | None], first: int, last: int) -> float | None:
    selected = [float(v) for m, v in zip(months, values) if first <= int(m[:4]) <= last and v is not None]
    return statistics.fmean(selected) if selected else None


def calculate(rows: Iterable[dict[str, Any]], *, expected_months: list[str] | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    parsed = parse_rows(rows)
    scopes = sorted({r["scope"] for r in parsed})
    months = expected_months or sorted({r["month"] for r in parsed})
    units = {(r["scope"], r["month"]) for r in parsed}
    expected_units = {(scope, month) for scope in scopes for month in months}
    if units != expected_units:
        raise ValueError(f"scope/month grid mismatch: missing={sorted(expected_units-units)[:5]} extra={sorted(units-expected_units)[:5]}")
    monthly_rows: list[dict[str, Any]] = []
    support_rows: list[dict[str, Any]] = []
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in parsed:
        grouped[(row["scope"], row["month"])].append(row)
    for scope in scopes:
        for month in months:
            monthly, support = analyze_unit(grouped[(scope, month)], scope=scope, month=month)
            monthly_rows.extend(monthly)
            support_rows.extend(support)
    return monthly_rows, support_rows, summarize(monthly_rows, months)


def _load_bound(binding: dict[str, Any], *, json_file: bool = False) -> tuple[Path, Any | None]:
    path = Path(binding["path"])
    if not path.is_absolute() or not path.is_file() or sha256(path) != binding["sha256"]:
        raise ValueError(f"missing or changed bound input: {path}")
    return path, json.loads(path.read_text(encoding="utf-8")) if json_file else None


def validate_control_binding(control: dict[str, Any], *, design_path: str, design_sha256: str,
                             scopes: list[str], runner_path: str, runner_sha256: str,
                             stock_sha256: str) -> None:
    """Ensure the generic controller check is bound to this exact diagnostic."""
    if control.get("action") != "preflight" or control.get("stage") != "diagnostic":
        raise ValueError("research control must be preflight/diagnostic")
    if control.get("scopes") != scopes:
        raise ValueError("research control scope list differs from design")
    bindings = control.get("bindings", {})
    design_binding = bindings.get("design", {})
    runner_binding = bindings.get("runner", {})
    if design_binding.get("path") != design_path or design_binding.get("sha256") != design_sha256:
        raise ValueError("research control is bound to another design")
    if runner_binding.get("path") != runner_path or runner_binding.get("sha256") != runner_sha256:
        raise ValueError("research control is bound to another runner")
    identity_inputs = control.get("scientific_identity", {}).get("inputs", [])
    if not any(isinstance(item, dict) and item.get("sha256") == stock_sha256 for item in identity_inputs):
        raise ValueError("research control scientific identity omits stock_weights input")


def validate_contract(contract_path: Path, *, check_only: bool) -> tuple[dict[str, Any], dict[str, Any], Path]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("schema") != "selection-gradient-run/1":
        raise ValueError("unsupported contract schema")
    if contract.get("market_data_requests") != 0:
        raise ValueError("market data requests must be zero")
    runner = contract["runner"]
    if Path(runner["path"]).resolve() != Path(__file__).resolve() or sha256(__file__) != runner["sha256"]:
        raise ValueError("runner path or hash mismatch")
    inputs = contract["inputs"]
    design_path, design = _load_bound(inputs["design"], json_file=True)
    stock_path, _ = _load_bound(inputs["stock_weights"])
    core_path, core = _load_bound(inputs["core_manifest"], json_file=True)
    review_path, review = _load_bound(inputs["controller_review"], json_file=True)
    if design.get("schema") != "financial-selection-gradient/1" or design.get("status") not in {
        "draft_for_scientific_review", "accepted", "approved",
        "method_accepted_by_controller_pending_data_projection_and_execution_binding"
    }:
        raise ValueError("unexpected or changed design")
    if design.get("already_seen_history") is not True or design.get("scopes") != list(SCOPES):
        raise ValueError("design scope/history mismatch")
    if design.get("outputs") != ["monthly.csv", "support.csv", "summary.json", "manifest.json"]:
        raise ValueError("design output set mismatch")
    selection = design.get("selection", {})
    if selection.get("source") != "financial_score only, no outcomes":
        raise ValueError("selection rule must use financial score only")
    machine_rules = design.get("machine_rules", {})
    if machine_rules != {
        "tie_allocation": "rank_interval_overlap_equal_per_tie",
        "minimum_sector_n": 5,
        "no_support": "retain_calendar_missing_no_zero",
        "same_support_baseline": True,
    }:
        raise ValueError("machine-readable design rules mismatch")
    partition = selection.get("partition", {})
    if not isinstance(partition, dict):
        raise ValueError("tie-preserving fractional partition rule missing")
    if selection.get("sector_mass", "").find("original n/N") < 0:
        raise ValueError("sector mass must retain original industry n/N")
    if selection.get("no_changed_portfolios", "").find("P/M/F/B/D") < 0:
        raise ValueError("original P/M/F/B/D weights must be preserved and checked")
    outcomes = design.get("outcomes", {})
    if outcomes.get("field") != "future_return" or outcomes.get("scenarios") != ["zero", "loss100"]:
        raise ValueError("outcome field/scenarios mismatch")
    if machine_rules["no_support"] != "retain_calendar_missing_no_zero":
        raise ValueError("no-support months must remain missing in block draws")
    manifest_outputs = core.get("outputs", {})
    expected_binding = manifest_outputs.get("stock_weights.csv")
    if not expected_binding or expected_binding.get("sha256") != inputs["stock_weights"]["sha256"]:
        raise ValueError("stock_weights input is not bound by core manifest")
    design_stock_binding = design.get("inputs", {}).get("stock_weights", {})
    if design_stock_binding.get("sha256") != inputs["stock_weights"]["sha256"] or design_stock_binding.get("path") != inputs["stock_weights"]["path"]:
        raise ValueError("design stock_weights binding differs from execution contract")
    design_manifest_binding = design.get("inputs", {}).get("manifest", {})
    if design_manifest_binding.get("sha256") != inputs["core_manifest"]["sha256"] or design_manifest_binding.get("path") != inputs["core_manifest"]["path"]:
        raise ValueError("design core manifest binding differs from execution contract")
    review_design_binding = design.get("scientific_review", {})
    if not review_design_binding.get("path") or not review_design_binding.get("sha256"):
        raise ValueError("design does not bind its scientific method review")
    method_review_path = Path(review_design_binding["path"])
    if not method_review_path.is_file() or sha256(method_review_path) != review_design_binding["sha256"]:
        raise ValueError("design scientific method review binding changed")
    if review.get("supporting_review_sha256") != review_design_binding["sha256"]:
        raise ValueError("controller acceptance does not bind the scientific method review")
    if review.get("design_sha256") != inputs["design"]["sha256"]:
        raise ValueError("controller review does not bind the final design")
    if (review.get("accepted") is not True and
            review.get("scientific_design_accepted") is not True and
            review.get("status") not in {"accepted", "approved"}):
        raise ValueError("controller review is not accepted")
    storage_path, storage = _load_bound(contract["storage_plan"], json_file=True)
    control_path, control_contract = _load_bound(contract["control_contract"], json_file=True)
    control_module_path, _ = _load_bound(contract["control_module"])
    expected_control_module = (MAIN / "src/lei_signal/research/lowfreq_research_control.py").resolve()
    if control_module_path.resolve() != expected_control_module:
        raise ValueError("control module path is outside this worktree")
    storage_module_path, _ = _load_bound(contract["storage_module"])
    expected_storage_module = Path("/Users/yongbiaoli/Desktop/lei-signal-lab/src/lei_signal/research/output_storage.py")
    if storage_module_path.resolve() != expected_storage_module.resolve():
        raise ValueError("storage module path differs from the fixed main-repository helper")
    validate_control_binding(
        control_contract,
        design_path=str(design_path), design_sha256=inputs["design"]["sha256"],
        scopes=design["scopes"], runner_path=str(Path(__file__).resolve()),
        runner_sha256=runner["sha256"], stock_sha256=inputs["stock_weights"]["sha256"],
    )
    control_spec = importlib.util.spec_from_file_location("selection_gradient_control", control_module_path)
    if control_spec is None or control_spec.loader is None:
        raise ValueError("cannot load bound research control module")
    control_module = importlib.util.module_from_spec(control_spec)
    control_spec.loader.exec_module(control_module)
    try:
        control_result = control_module.check(control_contract)
    except control_module.ControlError as exc:
        raise ValueError(f"research control rejected contract: {exc}") from exc
    output = contract["output"]
    parent_out = Path(storage["output"])
    run = Path(storage["run_directory"])
    if run != parent_out.parent or parent_out != run / "result":
        raise ValueError("storage parent path structure mismatch")
    if Path(output["path"]) != parent_out / "gradient-01" or output.get("run_directory") != str(run):
        raise ValueError("gradient output must be the frozen plan's gradient-01 child")
    if output.get("external_device") != storage["external_device"] or output.get("external_uuid") != storage["external_uuid"]:
        raise ValueError("external storage identity mismatch")
    if output.get("mount") != storage["external_mount"]:
        raise ValueError("external mount mismatch")
    if output.get("external_uuid") != "DEBA1C85-6059-3865-B50A-A8EE1F80E4D9":
        raise ValueError("unexpected external volume UUID")
    storage_spec = importlib.util.spec_from_file_location("selection_gradient_storage", storage_module_path)
    if storage_spec is None or storage_spec.loader is None:
        raise ValueError("cannot load bound output-storage module")
    storage_module = importlib.util.module_from_spec(storage_spec)
    storage_spec.loader.exec_module(storage_module)
    storage_root = storage_module_path.resolve().parents[3]
    fresh = storage_module.plan_output(storage_root, storage["task_id"], storage["estimated_bytes"],
                                       internal_bytes=storage["internal_metadata_bytes"])
    for key in ("external_mount", "external_device", "external_uuid", "estimated_bytes",
                "internal_metadata_bytes", "external_reserve_bytes", "internal_reserve_bytes"):
        if storage.get(key) != fresh.get(key):
            raise ValueError(f"storage route identity changed: {key}")
    if Path(storage["run_directory"]).parent != Path(fresh["run_directory"]).parent:
        raise ValueError("storage plan task directory differs from fresh external route")
    out = Path(output["path"])
    if not run.is_dir() or not parent_out.is_dir() or run.stat().st_dev != storage["external_device"] or parent_out.stat().st_dev != storage["external_device"]:
        raise ValueError("prepared parent output is missing or on wrong storage device")
    if out.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {out}")
    if design.get("selector_sha256") != control_contract.get("bindings", {}).get("selector", {}).get("sha256"):
        raise ValueError("source-only selector is not the design-bound projection")
    if not check_only and contract.get("execution_authorized") is not True:
        raise PermissionError("contract does not authorize real computation")
    if not check_only and control_result.get("status") != "eligible_for_separate_execution":
        raise PermissionError(f"research control status blocks execution: {control_result.get('status')}")
    return contract, {"design": design, "core_manifest": core, "review": review, "storage": storage,
                      "control_contract": control_contract, "control_result": control_result,
                      "control_module_path": str(control_module_path),
                      "storage_module_path": str(storage_module_path),
                      "paths": {"design": str(design_path), "stock_weights": str(stock_path),
                                "core_manifest": str(core_path), "controller_review": str(review_path),
                                "storage_plan": str(storage_path), "control_contract": str(control_path)}}, out


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing empty CSV: {path.name}")
    with path.open("x", newline="", encoding="utf-8") as f:
        fieldnames = list(dict.fromkeys(key for row in rows for key in row))
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        f.flush()


def _write_json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
        f.flush()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    contract_path = Path(args.contract)
    contract, bound, out = validate_contract(contract_path, check_only=args.check_only)
    if args.check_only:
        print(json.dumps({"checked": True, "market_data_requests": 0, "output_created": False,
                          "input_hashes_verified": True, "controller_review_accepted": True,
                          "control_status": bound["control_result"]["status"]}, ensure_ascii=False))
        return 0

    out.mkdir(exist_ok=False)
    # Recheck the saved source immediately before processing.
    source_path = Path(contract["inputs"]["stock_weights"]["path"])
    if sha256(source_path) != contract["inputs"]["stock_weights"]["sha256"]:
        raise ValueError("stock_weights changed after preflight")
    with source_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or not EXPECTED_COLUMNS.issubset(reader.fieldnames):
            raise ValueError(f"stock_weights columns missing: {sorted(EXPECTED_COLUMNS-set(reader.fieldnames or []))}")
        monthly_rows, support_rows, summary = calculate(reader, expected_months=[
            f"{year}-{month:02d}" for year in range(2015, 2026) for month in range(1, 13)
        ])
    _write_csv(out / "monthly.csv", monthly_rows)
    _write_csv(out / "support.csv", support_rows)
    _write_json(out / "summary.json", summary)
    output_hashes = {name: sha256(out / name) for name in ("monthly.csv", "support.csv", "summary.json")}
    manifest = {
        "schema": "selection-gradient-result/1",
        "contract_path": str(contract_path), "contract_sha256": sha256(contract_path),
        "runner_sha256": sha256(__file__), "design_sha256": sha256(contract["inputs"]["design"]["path"]),
        "stock_weights_sha256": sha256(source_path), "core_manifest_sha256": sha256(contract["inputs"]["core_manifest"]["path"]),
        "controller_review_sha256": sha256(contract["inputs"]["controller_review"]["path"]),
        "control_contract_path": contract["control_contract"]["path"],
        "control_contract_sha256": sha256(contract["control_contract"]["path"]),
        "control_module_sha256": sha256(contract["control_module"]["path"]),
        "storage_module_sha256": sha256(contract["storage_module"]["path"]),
        "control_status": bound["control_result"].get("status"),
        "control_identity_sha256": bound["control_result"].get("identity_sha256"),
        "source_selector_sha256": bound["control_contract"].get("bindings", {}).get("selector", {}).get("sha256"),
        "market_data_requests": 0, "saved_outcome_diagnostic_run": True,
        "new_strategy_backtest_run": False,
        "scope": list(SCOPES), "months": 132, "scenarios": [name for name, _ in SCENARIOS],
        "outputs": {name: {"path": str(out / name), "sha256": digest} for name, digest in output_hashes.items()},
        "monthly_rows": len(monthly_rows), "support_rows": len(support_rows),
    }
    _write_json(out / "manifest.json", manifest)
    manifest_hash = sha256(out / "manifest.json")
    print(json.dumps({"status": "complete", "manifest": str(out / "manifest.json"),
                      "sha256": manifest_hash, "monthly_rows": len(monthly_rows),
                      "support_rows": len(support_rows), "saved_outcome_diagnostic_run": True,
                      "new_strategy_backtest_run": False, "market_data_requests": 0}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
