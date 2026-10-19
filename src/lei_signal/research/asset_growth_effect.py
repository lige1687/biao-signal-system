"""Frozen annual asset-growth/GP selection comparison, for historical research only.

CLI: python -m lei_signal.research.asset_growth_effect --contract CONTRACT.json
The controller preflight runs before any historical quote or future outcome is read.
No market data are fetched, and an output directory must already be authorized.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import shlex
from collections import defaultdict
from datetime import date
from pathlib import Path

from lei_signal.research import lowfreq_discovery as old
from lei_signal.research.lowfreq_research_control import check as control_check

SCHEMA = "asset-growth-effect-contract/1"
METHODS = ("P", "M", "G", "F", "A", "C")
PAIRS = ("A", "G", "F", "M", "P")


def _sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1 << 20), b""):
            h.update(part)
    return h.hexdigest()


def _binding(binding, *, parse=True):
    path = Path(binding["path"])
    if not path.is_absolute() or not path.is_file() or _sha(path) != binding["sha256"]:
        raise ValueError(f"missing or changed binding: {path}")
    return (json.loads(path.read_text(encoding="utf-8")) if parse else None), path


def _finite(value, name):
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} missing") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} nonfinite")
    return number


def _calendar_dates(calendar, year):
    by_month = defaultdict(list)
    for day in calendar:
        by_month[day[:7]].append(day)
    june = by_month[f"{year}-06"]
    july = by_month[f"{year}-07"]
    following = by_month[f"{year+1}-07"]
    if not june or not july or (year <= 2024 and not following):
        raise ValueError(f"calendar lacks fixed annual dates: {year}")
    if year == 2025:
        return june[-1], july[0], None, []
    months = []
    for offset in range(12):
        y, m = year + (6 + offset) // 12, (6 + offset) % 12 + 1
        days = by_month[f"{y}-{m:02d}"]
        if not days:
            raise ValueError(f"calendar lacks monthly mark {y}-{m:02d}")
        months.append(days[-1])
    return june[-1], july[0], following[0], months


def _mean(values):
    return math.fsum(values) / len(values) if values else None


def _median(values):
    ordered = sorted(values)
    n = len(ordered)
    return (ordered[(n-1)//2] + ordered[n//2]) / 2


def _rankpct(rows, field, *, lower_better=False):
    ordered = sorted(rows, key=lambda r: r[field], reverse=not lower_better)
    n = len(ordered)
    result = {}
    i = 0
    while i < n:
        j = i + 1
        while j < n and ordered[j][field] == ordered[i][field]:
            j += 1
        rank = (i + 1 + j) / 2
        for row in ordered[i:j]:
            result[row["code"]] = (n - rank) / max(n - 1, 1)
        i = j
    return result


def _topk(rows, scores, k):
    """Return fractional selection mass, sharing only the cutoff tie."""
    if not 0 <= k <= len(rows):
        raise ValueError("invalid same-count k")
    if not k:
        return {}
    values = sorted((scores[r["code"]] for r in rows), reverse=True)
    cutoff = values[k - 1]
    above = sum(score > cutoff for score in values)
    tied = sum(score == cutoff for score in values)
    fraction = (k - above) / tied
    result = {r["code"]: (1.0 if scores[r["code"]] > cutoff else fraction if scores[r["code"]] == cutoff else 0.0)
              for r in rows}
    if not math.isclose(math.fsum(result.values()), k, abs_tol=1e-10):
        raise AssertionError("cutoff tie mass drift")
    return {code: mass for code, mass in result.items() if mass}


def _fourcells(rows):
    gm = _median([r["growth"] for r in rows])
    fm = _median([r["gp"] for r in rows])
    cells = defaultdict(list)
    for r in rows:
        g = "H" if r["growth"] > gm else "L" if r["growth"] < gm else "T"
        f = "H" if r["gp"] > fm else "L" if r["gp"] < fm else "T"
        cells[g + f].append(r)
    return cells, gm, fm


def _select(rows):
    """Use the same eligible pool, sector weights n/N, and sector count k."""
    sectors = defaultdict(list)
    for r in rows:
        sectors[r["industry"]].append(r)
    n_total = len(rows)
    if not n_total:
        raise ValueError("no common qualified rows")
    weights = {method: {} for method in METHODS}
    metadata = []
    for industry, members in sorted(sectors.items()):
        cells, gm, fm = _fourcells(members)
        excluded = {r["code"] for r in cells.get("HL", [])}
        retained = [r for r in members if r["code"] not in excluded]
        k = len(retained)
        if not k:
            raise ValueError("conditional rule empties an industry")
        sector_weight = len(members) / n_total
        rank_g = _rankpct(members, "growth", lower_better=True)
        rank_f = _rankpct(members, "gp")
        scores = {
            "M": {r["code"]: r["momentum"] for r in members},
            "G": {r["code"]: -r["growth"] for r in members},
            "F": {r["code"]: r["gp"] for r in members},
            "A": {r["code"]: (rank_g[r["code"]] + rank_f[r["code"]]) / 2 for r in members},
        }
        selections = {"P": {r["code"]: 1.0 for r in members},
                      "C": {r["code"]: 1.0 for r in retained}}
        selections.update({method: _topk(members, score, k) for method, score in scores.items()})
        for method, mass in selections.items():
            denominator = len(members) if method == "P" else k
            for code, fraction in mass.items():
                weights[method][code] = sector_weight * fraction / denominator
        metadata.append({"industry": industry, "n": len(members), "k": k,
                         "excluded": sorted(excluded), "growth_median": gm, "gp_median": fm,
                         "cells": {key: len(cells.get(key, [])) for key in ("HH", "HL", "LH", "LL", "HT", "LT", "TH", "TL", "TT")},
                         "all_four_cells": all(cells.get(key) for key in ("HH", "HL", "LH", "LL")),
                         "selected_mass": {method: math.fsum(selections[method].values()) for method in METHODS}})
    for method, stock_weights in weights.items():
        if not math.isclose(math.fsum(stock_weights.values()), 1.0, abs_tol=1e-10):
            raise AssertionError(f"{method} capital not fully invested")
    return weights, metadata


def _selector_rows(path):
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        required = {"decision_date", "code", "industry", "eligibility_status", "score", "financial_score", "momentum"}
        if not required <= set(reader.fieldnames or ()):
            raise ValueError("source-only selector lacks annual growth/GP/momentum")
        return list(reader)


def _candidate_rows(selector, calendar, quotes, membership, years):
    by_year = defaultdict(list)
    coverage = []
    seen = set()
    for year in years:
        decision, entry, exit_day, months = _calendar_dates(calendar, year)
        existing = [r for r in selector if r["decision_date"] == decision]
        if len(existing) != len(membership):
            raise ValueError(f"annual selector must preserve every planned cohort code: {year}")
        counts = defaultdict(int)
        rows = []
        for r in existing:
            code = r["code"]
            key = year, code
            if key in seen:
                raise ValueError("repeated annual selector code")
            seen.add(key)
            if code not in membership:
                raise ValueError("selector code outside frozen cohort")
            if r["eligibility_status"] != "qualified":
                counts["source_unknown"] += 1
                continue
            if not r["industry"] or r["industry"].startswith("J"):
                counts["industry_unknown_or_financial"] += 1
                continue
            q = quotes[code].get(decision)
            if q is None or not q["traded"] or q["is_st"] or not q["status_valid"]:
                counts["decision_not_tradable"] += 1
                continue
            try:
                growth = _finite(r["score"], "growth")
                gp = _finite(r["financial_score"], "GP")
                momentum = _finite(r["momentum"], "momentum")
            except ValueError:
                counts["signal_unknown"] += 1
                continue
            rows.append({"code": code, "industry": r["industry"],
                         "growth": growth, "gp": gp, "momentum": momentum})
        coverage.append({"year": year, "decision": decision, "entry": entry,
                         "exit": exit_day, "planned_selector_rows": len(existing),
                         "qualified_common": len(rows), "excluded_reasons": dict(counts),
                         "mature": year <= 2024})
        by_year[year] = (rows, (decision, entry, exit_day, months))
    return by_year, coverage


def _marks(weights, entry_prices, quotes, dates, unknown_return):
    """Fixed original units; unknown keeps its original weight in both scenarios."""
    series, quality = [1.0], []
    for day in dates:
        total = known_weight = unknown_weight = halt_weight = 0.0
        for code, w in weights.items():
            q = quotes[code].get(day)
            if code not in entry_prices or q is None or q["close"] is None or q["close"] <= 0:
                total += w * (1 + unknown_return)
                unknown_weight += w
            else:
                total += w * q["close"] / entry_prices[code]
                known_weight += w
                if not q["traded"]:
                    halt_weight += w
        series.append(total)
        quality.append({"date": day, "observed_initial_weight": known_weight,
                        "unknown_initial_weight": unknown_weight,
                        "halt_initial_weight": halt_weight})
    if not math.isclose(known_weight + unknown_weight, 1, abs_tol=1e-9):
        raise AssertionError("valuation denominator changed")
    return series, quality


def _entry_quality(weights, entry_prices):
    unknown = math.fsum(w for code, w in weights.items() if code not in entry_prices)
    return {"date": "entry", "observed_initial_weight": 1 - unknown,
            "unknown_initial_weight": unknown, "halt_initial_weight": 0.0}


def _entry_prices(rows, quotes, entry):
    """Actual trading and positive price form units; ST is not a new filter."""
    prices = {}
    for row in rows:
        code = row["code"]
        q = quotes[code].get(entry)
        if q is not None and q["close"] is not None and q["close"] > 0 and q["traded"]:
            prices[code] = q["close"]
    return prices


def _period_change(current, previous):
    return current / previous - 1 if previous > 0 else None


def _net_after_fees(gross_value, basis_points):
    rate = basis_points / 10000
    return gross_value * (1 - rate) / (1 + rate) - 1


def _monthly_records(year, scenario, month_ends, paths, qualities, entries):
    """Exactly twelve entry-to-June periods; annual exit remains separate."""
    if len(month_ends) != 12 or any(len(paths[m]) != 14 or len(qualities[m]) != 13 for m in METHODS):
        raise ValueError("annual path must have entry, twelve month-ends, and one exit")
    result = []
    for i, day in enumerate(month_ends, 1):
        p_change = _period_change(paths["P"][i], paths["P"][i-1])
        c_change = _period_change(paths["C"][i], paths["C"][i-1])
        previous_quality = {m: entries[m] if i == 1 else qualities[m][i-2] for m in METHODS}
        current_quality = {m: qualities[m][i-1] for m in METHODS}
        p_observed = (previous_quality["P"]["unknown_initial_weight"] == 0 and
                      current_quality["P"]["unknown_initial_weight"] == 0)
        pair_observed = p_observed and (previous_quality["C"]["unknown_initial_weight"] == 0 and
                                        current_quality["C"]["unknown_initial_weight"] == 0)
        result.append({"year": year, "scenario": scenario, "date": day,
                       "P_period_change": p_change, "C_period_change": c_change,
                       "market_group": "P_up" if p_change is not None and p_change > 0 else
                                       "P_down" if p_change is not None and p_change < 0 else
                                       "P_flat" if p_change == 0 else "P_unknown",
                       "P_label_has_imputed_quotes": not p_observed,
                       "comparison_quality": "fully_observed" if pair_observed else "scenario_involved",
                       "values": {m: paths[m][i] for m in METHODS},
                       "previous_endpoint_quality": previous_quality,
                       "current_endpoint_quality": current_quality})
    return result


def _drawdown(values):
    peak = values[0]
    worst = 0.0
    for value in values:
        peak = max(peak, value)
        if peak > 0:
            worst = min(worst, value / peak - 1)
    return worst


def _cell_effect(members, quotes, entry_prices, exit_day, unknown_return):
    """Keep every original cell member under the same unknown scenario."""
    cells, _, _ = _fourcells(members)
    values = {}
    for key in ("HH", "HL", "LH", "LL"):
        changes = []
        for row in cells.get(key, []):
            end = quotes[row["code"]].get(exit_day)
            changes.append(end["close"] / entry_prices[row["code"]] - 1
                           if row["code"] in entry_prices and end and end["close"] and end["close"] > 0
                           else unknown_return)
        values[key] = _mean(changes)
    interaction = ((values["HH"] - values["HL"]) - (values["LH"] - values["LL"])) if all(v is not None for v in values.values()) else None
    return values, interaction


def _blocks(values, draws=10000, seed=20261019):
    if len(values) != 10:
        raise ValueError("paired annual uncertainty requires ten completed years")
    rng = random.Random(seed)
    sampled = []
    for _ in range(draws):
        indices = []
        for _ in range(5):
            start = rng.randrange(10)
            indices.extend((start, (start + 1) % 10))
        sampled.append(_mean([values[i] for i in indices]))
    sampled.sort()
    return [sampled[int(0.025 * (draws - 1))], sampled[int(0.975 * (draws - 1))]]


def _pair_summary(annual):
    by_scenario = defaultdict(dict)
    for row in annual:
        by_scenario[row["scenario"]][row["year"]] = row
    result = []
    for scenario, years in by_scenario.items():
        for opponent in PAIRS:
            values = [years[y]["returns"]["C"] - years[y]["returns"][opponent] for y in range(2015, 2025)]
            result.append({"scenario": scenario, "pair": f"C-{opponent}",
                           "mean_difference": _mean(values), "interval_2year_blocks": _blocks(values),
                           "first5": _mean(values[:5]), "last5": _mean(values[5:]),
                           "leave_one_year_out": {str(y): _mean(values[:i] + values[i+1:]) for i, y in enumerate(range(2015, 2025))},
                           "year_differences": dict(zip(map(str, range(2015, 2025)), values))})
    return result


def _effect_diagnostics(annual, monthly, fourcell, holdings, membership):
    """Small, auditable summaries; retain the underlying full rows separately."""
    groups = defaultdict(list)
    for row in monthly:
        groups[(row["scenario"], row["market_group"], row["comparison_quality"])].append(row)
    market = []
    for (scenario, group, quality), rows in sorted(groups.items()):
        market.append({"scenario": scenario, "P_period_group": group,
                       "comparison_quality": quality,
                       "P_label_has_imputed_quotes": any(r["P_label_has_imputed_quotes"] for r in rows),
                       "cohort_periods": len(rows),
                       "mean_C_minus_P_period_return": _mean([r["C_period_change"] - r["P_period_change"]
                                                                for r in rows if r["C_period_change"] is not None and
                                                                r["P_period_change"] is not None])})
    # Cell estimates are explicitly conditional on the same supported sectors.
    by_year = defaultdict(list)
    for row in fourcell:
        if row["supported"]:
            by_year[(row["year"], row["scenario"])].append(row)
    interactions = []
    for scenario in ("unchanged", "total_loss"):
        for year in range(2015, 2025):
            rows = by_year[(year, scenario)]
            denominator = sum(r["n"] for r in rows)
            interactions.append({"year": year, "scenario": scenario,
                                 "supported_industries": len(rows), "supported_stocks": denominator,
                                 "n_weighted_interaction": sum(r["n"] * r["interaction"] for r in rows) / denominator if denominator else None})
    selected_c = defaultdict(set)
    for row in membership:
        if row["method"] == "C":
            selected_c[row["year"]].add(row["code"])
    excluded = defaultdict(list)
    for row in holdings:
        if row["method"] == "P" and row["code"] not in selected_c[row["year"]]:
            excluded[row["year"]].append(row)
    excluded_years = []
    for year in range(2015, 2025):
        rows = excluded[year]
        observed = [r for r in rows if r["annual_quote_return"] is not None]
        excluded_years.append({"year": year, "excluded_count": len(rows),
                               "observed_gain_count": sum(r["annual_quote_return"] > 0 for r in observed),
                               "observed_loss_count": sum(r["annual_quote_return"] < 0 for r in observed),
                               "observed_equal_count": sum(r["annual_quote_return"] == 0 for r in observed),
                               "future_unknown_count": len(rows) - len(observed),
                               "P_initial_weight": math.fsum(r["initial_weight"] for r in rows),
                               "P_observed_contribution": math.fsum(r["initial_weight"] * r["annual_quote_return"] for r in observed),
                               "largest_missed_gain": sorted((r for r in observed if r["annual_quote_return"] > 0),
                                                             key=lambda r: r["initial_weight"] * r["annual_quote_return"], reverse=True)[:5],
                               "largest_avoided_loss": sorted((r for r in observed if r["annual_quote_return"] < 0),
                                                              key=lambda r: r["initial_weight"] * r["annual_quote_return"])[:5]})
    contributors = []
    by_year_method = defaultdict(list)
    for row in holdings:
        if row["annual_quote_return"] is not None:
            by_year_method[(row["year"], row["method"])].append(row)
    for year in range(2015, 2025):
        for method in METHODS:
            rows = by_year_method[(year, method)]
            ranked = sorted(rows, key=lambda r: r["initial_weight"] * r["annual_quote_return"])
            contributors.append({"year": year, "method": method,
                                 "largest_negative": ranked[:5], "largest_positive": ranked[-5:][::-1]})
    by_method_year = defaultdict(dict)
    for row in membership:
        by_method_year[(row["method"], row["year"])][row["code"]] = row["initial_weight"]
    replacement = []
    for method in METHODS:
        for year in range(2016, 2025):
            before = by_method_year[(method, year - 1)]
            after = by_method_year[(method, year)]
            replacement.append({"method": method, "year": year,
                                "target_weight_half_absolute_change": math.fsum(abs(before.get(code, 0) - after.get(code, 0))
                                                                                   for code in before.keys() | after.keys()) / 2,
                                "added_names": len(after.keys() - before.keys()),
                                "removed_names": len(before.keys() - after.keys()),
                                "meaning": "target membership change, not executed turnover"})
    return {"P_up_down_months": market, "fourcell_n_weighted": interactions,
            "excluded_stock_counterexamples": excluded_years,
            "largest_annual_contributors": contributors,
            "target_membership_replacement": replacement}


def _write(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _load_quotes(selected, sources, calendar, membership, *, read_source=_binding, parse=old._quotes):
    quotes, quote_errors = {}, []
    for code in selected:
        source, _ = read_source(sources[code])
        try:
            quote, _, errors = parse(source, code, sources[code]["request"], calendar, membership[code])
            quotes[code] = quote
            quote_errors.extend({"code": code, "date": day, "reason": reason} for day, reason in errors)
        except (ValueError, KeyError, TypeError) as exc:
            quote_errors.append({"code": code, "date": None, "reason": "quote_parser_rejected",
                                 "detail": str(exc)})
    nonfatal = [e for e in quote_errors if e["reason"] == "expected_listed_day_missing_from_source"]
    fatal = [e for e in quote_errors if e["reason"] != "expected_listed_day_missing_from_source"]
    quality = {"schema": "asset-growth-quote-quality/1", "source_count": len(selected),
               "error_count": len(quote_errors), "fatal_count": len(fatal),
               "nonfatal_missing_count": len(nonfatal), "nonfatal_missing": nonfatal,
               "errors": quote_errors,
               "status": "rejected" if fatal else "checked_with_nonfatal_missing" if nonfatal else "checked_no_parser_errors"}
    return quotes, quality


def _execution_mode(spec, guard, decision, *, bind=_binding):
    """Normal effect or one narrowly linked diagnostic repair, nothing else."""
    stage = decision.get("stage")
    if decision.get("status") != "eligible_for_separate_execution":
        raise ValueError(f"control did not authorize a new run: {decision}")
    repair = spec.get("repair_of")
    if stage == "effect":
        if repair is not None:
            raise ValueError("normal effect execution cannot carry repair_of")
        return {"stage": "effect", "mode": "core", "repair_of": None}
    if stage != "diagnostic" or not isinstance(repair, dict) or set(repair) != {"failed_contract", "failed_receipt"}:
        raise ValueError("diagnostic requires exact failed-contract repair binding")
    review, _ = bind(guard["bindings"]["controller_review"])
    if review.get("effects_authorized") is not True:
        raise ValueError("diagnostic repair lacks effect authorization")
    source_binding = guard["bindings"]["source_qualification"]
    source, _ = bind(source_binding)
    if source.get("status") != "terminal" or decision.get("source_counts", {}).get("qualified", 0) <= 0:
        raise ValueError("diagnostic repair lacks terminal qualified source")
    failed, failed_path = bind(repair["failed_contract"])
    receipt, _ = bind(repair["failed_receipt"])
    if failed.get("schema") != SCHEMA or receipt.get("status") != "failed":
        raise ValueError("repair must bind a failed annual effect execution")
    for name in ("design", "selector", "input_contract"):
        if failed.get(name, {}).get("sha256") != spec.get(name, {}).get("sha256"):
            raise ValueError(f"repair changed original {name}")
    failed_guard, _ = bind(failed["control_contract"])
    if failed_guard.get("stage") != "effect" or failed_guard.get("action") != "preflight":
        raise ValueError("repair predecessor was not effect core preflight")
    if failed_guard.get("bindings", {}).get("source_qualification", {}).get("sha256") != source_binding["sha256"]:
        raise ValueError("repair changed source qualification")
    command = shlex.split(receipt.get("command", ""))
    if "--contract" not in command or command.index("--contract") + 1 >= len(command):
        raise ValueError("failed receipt does not identify its contract")
    receipt_contract = Path(command[command.index("--contract") + 1])
    if not receipt_contract.is_absolute():
        # The archived command is relative to the checked-out project root.
        receipt_contract = Path(__file__).resolve().parents[3] / receipt_contract
    if receipt_contract.resolve() != failed_path.resolve():
        raise ValueError("failed receipt refers to a different contract")
    return {"stage": "diagnostic", "mode": "repair",
            "repair_of": {"failed_contract_sha256": repair["failed_contract"]["sha256"],
                          "failed_receipt_sha256": repair["failed_receipt"]["sha256"]}}


def run(contract_path):
    spec, path = _binding({"path": str(Path(contract_path).resolve()), "sha256": _sha(contract_path)})
    if spec.get("schema") != SCHEMA:
        raise ValueError("wrong annual effect contract schema")
    # This guard validates source qualification, source-only selector, accepted
    # design, budget and prior attempts before any raw quote/outcome is opened.
    guard, _ = _binding(spec["control_contract"])
    decision = control_check(guard)
    execution = _execution_mode(spec, guard, decision)
    bindings = guard["bindings"]
    for name, local in (("design", "design"), ("selector", "selector"), ("runner", "runner")):
        if spec[local]["sha256"] != bindings[name]["sha256"]:
            raise ValueError(f"{name} differs from control binding")
    if Path(bindings["runner"]["path"]).resolve() != Path(__file__).resolve():
        raise ValueError("controller bound a different runner")
    if not any(item["sha256"] == spec["input_contract"]["sha256"] for item in guard["scientific_identity"]["inputs"]):
        raise ValueError("original input contract absent from controlled identity")
    design, _ = _binding(spec["design"])
    inputs, _ = _binding(spec["input_contract"])
    _, selector_path = _binding(spec["selector"], parse=False)
    if design.get("schema") != "asset-growth-effect-design/1" or inputs.get("schema") != "lowfreq-evaluator-contract/1":
        raise ValueError("design/input contract identity mismatch")
    if design["input_binding"]["sha256"] != spec["input_contract"]["sha256"]:
        raise ValueError("design references different original input")
    if design.get("status") != "predeclared_before_any_new_outcomes; execute only after source qualification accepted":
        raise ValueError("effect design not frozen")
    parent = Path(spec["output_parent"])
    if not parent.is_absolute() or not parent.is_dir() or parent.stat().st_dev == Path(__file__).stat().st_dev:
        raise ValueError("effect output parent must be an existing external result directory")
    out = parent / spec["output_name"]
    if not spec["output_name"] or "/" in spec["output_name"] or out.exists():
        raise ValueError("output must be one new directory")
    # The first future-facing read happens only after every contract check above.
    selector = _selector_rows(selector_path)
    cohort_doc, _ = _binding(inputs["cohort"])
    calendar_doc, _ = _binding(inputs["calendar"])
    old_design, _ = _binding(inputs["design"])
    selected, _, membership = old._cohort(cohort_doc, old_design["universe"]["asof"], old_design["universe"]["sample_size"])
    calendar = old._calendar(calendar_doc)
    sources = {item["code"]: item for item in inputs["sources"]}
    if set(sources) != set(selected):
        raise ValueError("frozen quote set differs from 600-stock cohort")
    quotes, quote_quality = _load_quotes(selected, sources, calendar, membership)
    if quote_quality["fatal_count"]:
        out.mkdir(parents=False, exist_ok=False)
        _write(out / "quote_quality.json", quote_quality)
        raise ValueError(f"underlying quote source rejected; see {out / 'quote_quality.json'}")
    yearly, coverage = _candidate_rows(selector, calendar, quotes, membership, range(2015, 2026))
    annual, detail, fourcell, monthly, membership_rows, sector_rows = [], [], [], [], [], []
    for year in range(2015, 2026):
        rows, (_, entry, exit_day, month_ends) = yearly[year]
        if year == 2025:
            continue
        weights, sectors = _select(rows)
        sector_rows.extend({"year": year, **sector} for sector in sectors)
        entry_prices = _entry_prices(rows, quotes, entry)
        # Missing entry leaves the original allocation entirely unknown;
        # no fictitious share count, removal or reallocation is allowed.
        for method, allocated in weights.items():
            for code, w in allocated.items():
                membership_rows.append({"year": year, "method": method, "code": code, "initial_weight": w})
                final = quotes[code].get(exit_day)
                actual = (final["close"] / entry_prices[code] - 1) if code in entry_prices and final and final["close"] and final["close"] > 0 else None
                detail.append({"year": year, "method": method, "code": code, "initial_weight": w,
                               "entry_price": entry_prices.get(code), "entry_unknown": code not in entry_prices,
                               "exit_price": final["close"] if final else None,
                               "exit_halt": bool(final and not final["traded"]), "annual_quote_return": actual})
        for scenario, unknown_return in (("unchanged", 0.0), ("total_loss", -1.0)):
            for sector in sectors:
                industry = sector["industry"]
                members = [r for r in rows if r["industry"] == industry]
                values, interaction = _cell_effect(members, quotes, entry_prices, exit_day, unknown_return)
                fourcell.append({"year": year, "scenario": scenario, "industry": industry,
                                 "n": sector["n"], "counts": sector["cells"],
                                 "mean_returns": values, "interaction": interaction,
                                 "supported": interaction is not None})
            paths, qualities = {}, {}
            entries = {method: _entry_quality(allocated, entry_prices) for method, allocated in weights.items()}
            for method, allocated in weights.items():
                paths[method], qualities[method] = _marks(allocated, entry_prices, quotes, month_ends + [exit_day], unknown_return)
            returns = {method: path[-1] - 1 for method, path in paths.items()}
            risk = {method: _drawdown(path) for method, path in paths.items()}
            fee = {str(bp): {method: _net_after_fees(path[-1], bp) for method, path in paths.items()}
                   for bp in (10, 30)}
            annual.append({"year": year, "scenario": scenario, "returns": returns,
                           "max_entry_monthends_exit_drawdown": risk, "round_trip_fee_sensitivity": fee,
                           "fee_model": "hypothetical fully executable buy/sell, netV=grossV*(1-sell_bp/10000)/(1+buy_bp/10000), equal 10 or 30bp each side",
                           "ending_unknown_initial_weight": {m: q[-1]["unknown_initial_weight"] for m, q in qualities.items()},
                           "ending_halt_initial_weight": {m: q[-1]["halt_initial_weight"] for m, q in qualities.items()},
                           "entry_unknown_initial_weight": {m: q["unknown_initial_weight"] for m, q in entries.items()},
                           "drawdown_has_imputed_quotes": {m: entries[m]["unknown_initial_weight"] > 0 or
                                                           any(q["unknown_initial_weight"] > 0 for q in qualities[m])
                                                           for m in METHODS},
                           "stock_count": {m: len(w) for m, w in weights.items()},
                           "max_initial_weight": {m: max(w.values()) for m, w in weights.items()},
                           "weight_squares": {m: math.fsum(x*x for x in w.values()) for m, w in weights.items()}})
            monthly.extend(_monthly_records(year, scenario, month_ends, paths, qualities, entries))
    paired = _pair_summary(annual)
    diagnostics = _effect_diagnostics(annual, monthly, fourcell, detail, membership_rows)
    out.mkdir(parents=False, exist_ok=False)
    outputs = {"quote_quality.json": quote_quality, "coverage.json": coverage,
               "annual.json": annual, "monthly.json": monthly,
               "fourcell.json": fourcell, "sector_selection.json": sector_rows,
               "holdings.json": detail, "membership.json": membership_rows,
               "paired.json": paired, "diagnostics.json": diagnostics}
    for name, payload in outputs.items():
        _write(out / name, payload)
    manifest = {"schema": "asset-growth-effect-result/1", "contract_sha256": _sha(path),
                "control_identity": decision["identity_sha256"], "design_sha256": spec["design"]["sha256"],
                "input_sha256": spec["input_contract"]["sha256"],
                "stage": execution["stage"], "mode": execution["mode"],
                "repair_of": execution["repair_of"],
                "outputs": {name: _sha(out / name) for name in outputs},
                "status": "computed_pending_review", "market_execution": "retrospective_only",
                "limitations": ["dividends and corporate actions not reconciled", "unknown outcomes are sensitivity scenarios",
                                "historical selection/price input qualification remains conditional"]}
    _write(out / "manifest.json", manifest)
    return {"output": str(out), "manifest_sha256": _sha(out / "manifest.json")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.contract), ensure_ascii=False))


if __name__ == "__main__":
    main()
