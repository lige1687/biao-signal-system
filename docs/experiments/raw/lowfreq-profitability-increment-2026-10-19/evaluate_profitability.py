"""Frozen financial discovery evaluator. No fetch, fitting, or trading output.

CLI contract schema financial-evaluation-run/1: ``inputs`` maps design,
amendment, cohort, prices, panel, parser, runner to {path, sha256}; ``output``
is {path, mount, external_device}.  Every bound byte is checked before writing.
The panel builder is separate and must supply as-known financial eligibility.
"""

from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import json
import math
import os
import random
import re
import statistics
import struct
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

DESIGN_SHA = "648476bf2cb79056d4982884e96b387ffc76a494598475644b12be0c69e526bc"
AMENDMENT_SHA = "49ae1ab6af18622686e5f8feae58e19493a95dfb4ece8759f2d173addf3d0405"
COHORT_SHA = "6f073e37809613469efe6cd2adb6b7ef1b4e77515e99e7149e1636d9e390cc16"
PARSER_SHA = "dc009a8e95ae1e61dabed0ee861f0109b686f0bebeacb7b1985a91dd5e1f42ae"
METHODS = ("P", "M", "F", "B", "D")
SCOPES = (("gp", "gpa", False), ("common_gp", "gpa", True),
          ("common_cfo", "cfoa", True))
PAIRS = (("F", "P"), ("B", "M"), ("B", "D"), ("B", "P"), ("B", "F"))
SCENARIOS = {"unknown_minus_one": -1.0, "unknown_zero": 0.0}
CODE = re.compile(r"^(?:sh\.60|sz\.00|sz\.30)\d{4}$")
INDUSTRY = re.compile(r"^[A-Z]\d{2}$")
MONTH = re.compile(r"^20\d{2}-(?:0[1-9]|1[0-2])$")
PRICE_FIELDS = {"month", "decision_date", "code", "eligibility_reason", "momentum",
                "entry_date", "exit_date", "future_return", "outcome_reason", "either_halt"}
PANEL_FIELDS = {"month", "decision_date", "code", "industry", "gp_status", "gpa",
                "cfo_status", "cfoa", "report_year", "announcement_id",
                "publication_date", "reason"}


def _sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for part in iter(lambda: f.read(1 << 20), b""):
            h.update(part)
    return h.hexdigest()


def _number(raw, *, required=False):
    if raw is None or str(raw).strip() == "":
        if required:
            raise ValueError("required numeric field blank")
        return None
    try:
        value = float(raw)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"invalid numeric field: {raw!r}") from exc
    if not math.isfinite(value):
        raise ValueError(f"nonfinite numeric field: {raw!r}")
    return value


def _bool(raw):
    if raw not in ("True", "False"):
        raise ValueError(f"invalid boolean: {raw!r}")
    return raw == "True"


def _months():
    return [f"{year:04d}-{month:02d}" for year in range(2015, 2026)
            for month in range(1, 13)]


def _next(month):
    y, m = map(int, month.split("-"))
    return f"{y + (m == 12):04d}-{m % 12 + 1:02d}"


def _previous(month):
    y, m = map(int, month.split("-"))
    return f"{y - (m == 1):04d}-{12 if m == 1 else m - 1:02d}"


def _csv_rows(path, required):
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError(f"missing/duplicate CSV columns: {path}")
        if not required <= set(reader.fieldnames):
            raise ValueError(f"CSV columns absent: {sorted(required - set(reader.fieldnames))}")
        return list(reader)


def _load_inputs(bound):
    cohort = json.loads(Path(bound["cohort"]["path"]).read_text(encoding="utf-8"))
    if len(cohort["fixed_codes"]) != 600 or len(set(cohort["fixed_codes"])) != 600:
        raise ValueError("frozen 600 identity invalid")
    codes = set(cohort["fixed_codes"])
    if any(not CODE.fullmatch(code) for code in codes):
        raise ValueError("invalid cohort code")
    if _sha(cohort["price_quality_path"]) != cohort["price_quality_sha256"]:
        raise ValueError("price quality identity changed")
    if Path(bound["prices"]["path"]).resolve() != (Path(cohort["price_quality_path"]).parent /
                                                  "per_stock_month.csv").resolve():
        raise ValueError("price CSV is not the saved core-v1 result")
    quality = json.loads(Path(cohort["price_quality_path"]).read_text(encoding="utf-8"))
    if quality["sample_codes"] != cohort["fixed_codes"] or quality["monthly_full_rows"] != 79200:
        raise ValueError("core result differs from frozen cohort")
    prices = _csv_rows(bound["prices"]["path"], PRICE_FIELDS)
    panel = _csv_rows(bound["panel"]["path"], PANEL_FIELDS)
    expected = {(m, c) for m in _months() for c in codes}
    if len(prices) != len(panel) or len(prices) != len(expected):
        raise ValueError("price/panel do not have 600 x 132 rows")
    price_map, panel_map, dates = {}, {}, {}
    for row in prices:
        key = (row["month"], row["code"])
        if key not in expected or key in price_map:
            raise ValueError(f"price missing/duplicate/outside code-month: {key}")
        if not MONTH.fullmatch(row["month"]):
            raise ValueError(f"price month malformed: {key}")
        date.fromisoformat(row["decision_date"])
        date.fromisoformat(row["entry_date"])
        date.fromisoformat(row["exit_date"])
        if (row["decision_date"][:7] != _previous(row["month"]) or
                row["entry_date"][:7] != row["month"] or
                row["exit_date"][:7] != _next(row["month"]) or
                not row["decision_date"] < row["entry_date"] < row["exit_date"]):
            raise ValueError(f"decision/entry/exit month mismatch: {key}")
        triplet = tuple(row[n] for n in ("decision_date", "entry_date", "exit_date"))
        if row["month"] in dates and dates[row["month"]] != triplet:
            raise ValueError(f"mixed dates in price month {row['month']}")
        dates[row["month"]] = triplet
        _bool(row["either_halt"])
        future = _number(row["future_return"])
        if future is not None and (future < -1 or not row["outcome_reason"].startswith("observed")):
            raise ValueError(f"unqualified future return: {key}")
        if future is None and row["outcome_reason"].startswith("observed"):
            raise ValueError(f"observed outcome without return: {key}")
        if row["eligibility_reason"] == "eligible":
            _number(row["momentum"], required=True)
        price_map[key] = row
    for row in panel:
        key = (row["month"], row["code"])
        if key not in expected or key in panel_map:
            raise ValueError(f"panel missing/duplicate/outside code-month: {key}")
        if row["decision_date"] != dates[key[0]][0]:
            raise ValueError(f"panel decision date differs from prices: {key}")
        industry = row["industry"]
        if industry and industry != "unknown" and not INDUSTRY.fullmatch(industry):
            raise ValueError(f"invalid two-digit industry: {key}:{industry}")
        for status, field in (("gp_status", "gpa"), ("cfo_status", "cfoa")):
            if row[status] not in ("qualified", "unknown"):
                raise ValueError(f"invalid panel status: {key}:{status}")
            value = _number(row[field])
            if (row[status] == "qualified") != (value is not None):
                raise ValueError(f"status/value contradiction: {key}:{field}")
        if ("unknown" in (row["gp_status"], row["cfo_status"]) and not row["reason"]):
            raise ValueError(f"unknown financial field lacks reason: {key}")
        if row["report_year"]:
            year = int(row["report_year"])
            if not 2013 <= year <= 2024:
                raise ValueError(f"report year outside frozen range: {key}")
        if row["publication_date"]:
            date.fromisoformat(row["publication_date"])
            if row["publication_date"] >= row["decision_date"]:
                raise ValueError(f"future filing in as-known panel: {key}")
        if any(row[status] == "qualified" for status in ("gp_status", "cfo_status")):
            if not (row["report_year"] and row["announcement_id"] and row["publication_date"]):
                raise ValueError(f"qualified field missing source identity: {key}")
            report_year = int(row["report_year"])
            decision = date.fromisoformat(row["decision_date"])
            age_months = (decision.year - report_year) * 12 + decision.month - 12
            if not 1 <= age_months <= 16:
                raise ValueError(f"qualified report outside 16-month annual age: {key}")
        panel_map[key] = row
    if set(price_map) != expected or set(panel_map) != expected or len(dates) != 132:
        raise ValueError("incomplete exact cohort/month coverage")
    return price_map, panel_map, dates, cohort["fixed_codes"]


def _rank_percentiles(items, feature):
    ordered = sorted(items, key=lambda r: r[feature])
    n = len(ordered)
    result = {}
    i = 0
    while i < n:
        j = i + 1
        while j < n and ordered[j][feature] == ordered[i][feature]:
            j += 1
        result.update({row["code"]: (i + j - 1) / (2 * (n - 1)) if n > 1 else 1.0
                       for row in ordered[i:j]})
        i = j
    return result


def _weights(pool, financial):
    """Same sector n/N for all five targets, with a stable code cutoff."""
    if not pool:
        return None
    if len({row["code"] for row in pool}) != len(pool):
        raise ValueError("duplicate security in one month/pool")
    by_industry = defaultdict(list)
    for row in pool:
        by_industry[row["industry"]].append(row)
    total = len(pool)
    weights = {method: defaultdict(float) for method in METHODS}
    details = {}
    for industry, members in sorted(by_industry.items()):
        n = len(members)
        k = n if n < 5 else math.ceil(0.2 * n)
        m_rank = _rank_percentiles(members, "momentum")
        f_rank = _rank_percentiles(members, financial)
        combined = {code: (m_rank[code] + f_rank[code]) / 2 for code in m_rank}
        chosen = {
            "M": {r["code"] for r in sorted(members, key=lambda r: (-m_rank[r["code"]], r["code"]))[:k]},
            "F": {r["code"] for r in sorted(members, key=lambda r: (-f_rank[r["code"]], r["code"]))[:k]},
            "B": {r["code"] for r in sorted(members, key=lambda r: (-combined[r["code"]], r["code"]))[:k]},
        }
        for row in members:
            code = row["code"]
            weights["P"][code] = 1 / total
            for method in ("M", "F", "B"):
                weights[method][code] = n / total / k if code in chosen[method] else 0.0
            details[code] = {"sector_n": n, "sector_selected_k": k, "tiny_no_selection": n < 5,
                             "momentum_percentile": m_rank[code],
                             "financial_percentile": f_rank[code],
                             "blend_percentile": combined[code]}
    for row in pool:
        code = row["code"]
        weights["D"][code] = (weights["M"][code] + weights["P"][code]) / 2
    if any(not math.isclose(sum(w.values()), 1, abs_tol=1e-10) for w in weights.values()):
        raise AssertionError("target weights fail to sum to one")
    return {method: dict(w) for method, w in weights.items()}, details


def _spearman(pool, financial):
    if len(pool) < 3:
        return None
    m, f = _rank_percentiles(pool, "momentum"), _rank_percentiles(pool, financial)
    return _pearson([m[r["code"]] for r in pool], [f[r["code"]] for r in pool])


def _pearson(x, y):
    if len(x) < 3:
        return None
    mean_x, mean_y = statistics.mean(x), statistics.mean(y)
    var_x = sum((v - mean_x) ** 2 for v in x)
    var_y = sum((v - mean_y) ** 2 for v in y)
    if var_x <= 0 or var_y <= 0:
        return None
    return sum((a - mean_x) * (b - mean_y) for a, b in zip(x, y)) / math.sqrt(var_x * var_y)


def _outcomes(pool, weights):
    results = {}
    for method in METHODS:
        w = weights[method]
        unknown = sum(w[r["code"]] for r in pool if r["future"] is None)
        halted = sum(w[r["code"]] for r in pool if r["halt"])
        results[method] = {"unknown_weight": unknown, "either_halt_weight": halted,
                           **{scenario: sum(w[r["code"]] *
                               (r["future"] if r["future"] is not None else substitute)
                               for r in pool)
                              for scenario, substitute in SCENARIOS.items()}}
    return results


def _moments(values, *, complete=False):
    vals = [v for v in values if v is not None]
    if not vals:
        return {"status": "not_evaluated", "defined_months": 0, "mean": None,
                "sample_std": None, "worst_month": None, "worst_10pct_mean": None,
                "marked_quote_max_drawdown": None}
    n = len(vals)
    worst = sorted(vals)[:math.ceil(0.1 * n)]
    drawdown = None
    if complete and n == 132:
        wealth = peak = 1.0
        drawdown = 0.0
        for value in vals:
            wealth *= 1 + value
            peak = max(peak, wealth)
            drawdown = min(drawdown, wealth / peak - 1)
    return {"status": "evaluated", "defined_months": n, "mean": statistics.mean(vals),
            "sample_std": statistics.stdev(vals) if n >= 2 else None,
            "worst_month": min(vals), "worst_10pct_mean": statistics.mean(worst),
            "marked_quote_max_drawdown": drawdown}


def _series(monthly, scope, scenario, method):
    return [monthly.get((scope, month), {}).get("methods", {}).get(method, {}).get(scenario)
            for month in _months()]


def _period_mask(name):
    months = _months()
    if name == "all":
        return [True] * len(months)
    if name == "2015-2019":
        return [month[:4] <= "2019" for month in months]
    if name == "2020-2025":
        return [month[:4] >= "2020" for month in months]
    if name.startswith("year-"):
        return [month[:4] == name[-4:] for month in months]
    if name.startswith("without-"):
        return [month[:4] != name[-4:] for month in months]
    raise ValueError(name)


def _summaries(monthly):
    names = ("all", "2015-2019", "2020-2025") + tuple(f"year-{y}" for y in range(2015, 2026)) + tuple(
        f"without-{y}" for y in range(2015, 2026))
    performance, paired = [], []
    for scope, _, _ in SCOPES:
        for scenario in SCENARIOS:
            series = {method: _series(monthly, scope, scenario, method) for method in METHODS}
            down = [v is not None and v < 0 for v in series["P"]]
            for period in names:
                mask = _period_mask(period)
                for method in METHODS:
                    values = [v if use else None for v, use in zip(series[method], mask)]
                    performance.append({"scope": scope, "scenario": scenario, "period": period,
                                        "method": method, **_moments(values, complete=period == "all"),
                                        "p_down_common_mean": _moments([v if use and d else None
                                                                           for v, use, d in zip(series[method], mask, down)])["mean"],
                                        "p_down_common_months": sum(use and d for use, d in zip(mask, down))})
                for left, right in PAIRS:
                    values = [(a - b) if use and a is not None and b is not None else None
                              for a, b, use in zip(series[left], series[right], mask)]
                    paired.append({"scope": scope, "scenario": scenario, "period": period,
                                   "comparison": f"{left}-{right}", **_moments(values),
                                   "p_down_common_mean": _moments([v if d else None
                                                                      for v, d in zip(values, down)])["mean"],
                                   "p_down_common_months": sum(v is not None and d
                                                                for v, d in zip(values, down))})
    for scenario in SCENARIOS:
        common_p = _series(monthly, "common_gp", scenario, "P")
        down = [v is not None and v < 0 for v in common_p]
        for method in ("F", "B"):
            cash = _series(monthly, "common_cfo", scenario, method)
            gross = _series(monthly, "common_gp", scenario, method)
            for period in names:
                mask = _period_mask(period)
                values = [(a - b) if use and a is not None and b is not None else None
                          for a, b, use in zip(cash, gross, mask)]
                paired.append({"scope": "common_candidate", "scenario": scenario, "period": period,
                               "comparison": f"CFO_{method}-GP_{method}", **_moments(values),
                               "p_down_common_mean": _moments([v if d else None
                                                                  for v, d in zip(values, down)])["mean"],
                               "p_down_common_months": sum(v is not None and d
                                                            for v, d in zip(values, down))})
    return performance, paired


def _quantile(sorted_values, q):
    position = (len(sorted_values) - 1) * q
    lo, hi = math.floor(position), math.ceil(position)
    return sorted_values[lo] * (hi - position) + sorted_values[hi] * (position - lo) if hi != lo else sorted_values[lo]


def _bootstrap(monthly, *, draws=10000):
    arrays = {}
    for scope, _, _ in SCOPES:
        for scenario in SCENARIOS:
            for method in METHODS:
                arrays[(scope, scenario, method)] = _series(monthly, scope, scenario, method)
            for left, right in PAIRS:
                a, b = arrays[(scope, scenario, left)], arrays[(scope, scenario, right)]
                arrays[(scope, scenario, f"{left}-{right}")] = [x - y if x is not None and y is not None else None
                                                                 for x, y in zip(a, b)]
    for scenario in SCENARIOS:
        for method in ("F", "B"):
            cash = arrays[("common_cfo", scenario, method)]
            gross = arrays[("common_gp", scenario, method)]
            arrays[("common_candidate", scenario, f"CFO_{method}-GP_{method}")] = [
                x - y if x is not None and y is not None else None for x, y in zip(cash, gross)]
    output = []
    for block in (6, 12):
        rng = random.Random(20261019)
        digest = hashlib.sha256()
        samples = {key: [] for key in arrays}
        n = 132
        for _ in range(draws):
            positions = []
            for _ in range(math.ceil(n / block)):
                start = rng.randrange(n)
                positions.extend((start + j) % n for j in range(block))
            positions = positions[:n]
            for pos in positions:
                digest.update(struct.pack(">H", pos))
            for key, values in arrays.items():
                valid = [values[pos] for pos in positions if values[pos] is not None]
                if valid:
                    samples[key].append(statistics.fmean(valid))
        for key, values in samples.items():
            values.sort()
            for confidence in (0.95, 0.975):
                output.append({"scope": key[0], "scenario": key[1], "measure": key[2],
                               "block_months": block, "draws_requested": draws,
                               "draws_valid": len(values), "confidence": confidence,
                               "lower": _quantile(values, (1 - confidence) / 2) if values else None,
                               "upper": _quantile(values, 1 - (1 - confidence) / 2) if values else None,
                               "status": "evaluated" if values else "not_evaluated",
                               "shared_index_sha256": digest.hexdigest(),
                               "algorithm": "circular month-block resampling of all 132 dated positions; missing positions excluded per draw",
                               "rng": "Python random.Random MT19937", "python_version": __import__("platform").python_version()})
    return output


def _other(monthly):
    summaries = []
    for scope, _, _ in SCOPES:
        rows = [monthly.get((scope, month)) for month in _months()]
        existing = [r for r in rows if r]
        summaries.append({"scope": scope, "scenario": "all",
                          "defined_months": len(existing),
                          "mean_pool_n": statistics.mean(r["pool_n"] for r in existing) if existing else None,
                          "mean_overlap_F_M": statistics.mean(r["overlap_F_M"] for r in existing) if existing else None,
                          "mean_overlap_B_M": statistics.mean(r["overlap_B_M"] for r in existing) if existing else None,
                          "mean_financial_momentum_spearman": statistics.mean(v for r in existing
                              if (v := r["spearman_financial_momentum"]) is not None)
                              if any(r["spearman_financial_momentum"] is not None for r in existing) else None,
                          "method_uses": {method: {
                              "mean_holdings": statistics.mean(r["methods"][method]["holdings"] for r in existing)
                              if existing else None,
                              "mean_max_weight": statistics.mean(r["methods"][method]["max_weight"] for r in existing)
                              if existing else None,
                              "mean_target_replacement": statistics.mean(v for r in existing
                                  if (v := r["methods"][method]["target_replacement"]) is not None)
                                  if any(r["methods"][method]["target_replacement"] is not None for r in existing)
                                  else None} for method in METHODS}})
        for scenario in SCENARIOS:
            f = [r["methods"]["F"][scenario] if r else None for r in rows]
            m = [r["methods"]["M"][scenario] if r else None for r in rows]
            b = [r["methods"]["B"][scenario] if r else None for r in rows]
            common_fm = [(a, c) for a, c in zip(f, m) if a is not None and c is not None]
            common_bm = [(a, c) for a, c in zip(b, m) if a is not None and c is not None]
            summaries.append({"scope": scope, "scenario": scenario,
                              "return_corr_F_M": _pearson(*zip(*common_fm)) if len(common_fm) >= 3 else None,
                              "return_corr_B_M": _pearson(*zip(*common_bm)) if len(common_bm) >= 3 else None,
                              "corr_common_months_F_M": len(common_fm),
                              "corr_common_months_B_M": len(common_bm)})
    return summaries


def _evaluate(price_map, panel_map, dates, codes):
    monthly, stock_rows, layer_rows = {}, [], []
    prior_targets = {scope: {} for scope, _, _ in SCOPES}
    prior_ann = {}
    for month in _months():
        joined = []
        layers = Counter()
        ann_changes = 0
        for code in codes:
            p, f = price_map[(month, code)], panel_map[(month, code)]
            if f["announcement_id"] and code in prior_ann and prior_ann[code] != f["announcement_id"]:
                ann_changes += 1
            if f["announcement_id"]:
                prior_ann[code] = f["announcement_id"]
            reason = None
            if p["eligibility_reason"] != "eligible":
                reason = "price:" + p["eligibility_reason"]
            elif not INDUSTRY.fullmatch(f["industry"]):
                reason = "industry_unknown"
            elif f["industry"].startswith("J"):
                reason = "financial_industry_excluded"
            elif f["gp_status"] != "qualified":
                reason = "gp:" + (f["reason"] or "unqualified")
            elif f["cfo_status"] != "qualified":
                reason = "cfo:" + (f["reason"] or "unqualified")
            layers[reason or "gp_and_cfo_qualified"] += 1
            if reason and (reason.startswith("price:") or reason in ("industry_unknown", "financial_industry_excluded")
                           or reason.startswith("gp:")):
                continue
            joined.append({"code": code, "industry": f["industry"], "momentum": _number(p["momentum"], required=True),
                           "gpa": _number(f["gpa"], required=True), "cfoa": _number(f["cfoa"]),
                           "future": _number(p["future_return"]), "halt": _bool(p["either_halt"]),
                           "source": f})
        layer_rows.append({"month": month, "decision_date": dates[month][0],
                           "original_600": 600,
                           "price_eligible": sum(price_map[(month, c)]["eligibility_reason"] == "eligible" for c in codes),
                           "sector_eligible": sum(price_map[(month, c)]["eligibility_reason"] == "eligible" and
                                                  INDUSTRY.fullmatch(panel_map[(month, c)]["industry"]) is not None and
                                                  not panel_map[(month, c)]["industry"].startswith("J") for c in codes),
                           "gp_pool": len(joined),
                           "common_pool": sum(r["cfoa"] is not None for r in joined),
                           "reason_counts": dict(layers), "announcement_id_changes": ann_changes})
        for scope, feature, common in SCOPES:
            pool = [r for r in joined if r["cfoa"] is not None] if common else joined
            selected = _weights(pool, feature)
            if selected is None:
                prior_targets[scope] = {}
                continue
            weights, rank_details = selected
            outcomes = _outcomes(pool, weights)
            previous = prior_targets[scope]
            turnover = {method: (0.5 * sum(abs(weights[method].get(code, 0) - previous[method].get(code, 0))
                                                   for code in set(weights[method]) | set(previous[method]))
                                 if previous else None) for method in METHODS}
            prior_targets[scope] = weights
            overlap_fm = sum(min(weights["F"].get(code, 0), weights["M"].get(code, 0)) for code in weights["P"])
            overlap_bm = sum(min(weights["B"].get(code, 0), weights["M"].get(code, 0)) for code in weights["P"])
            monthly[(scope, month)] = {"scope": scope, "month": month, "decision_date": dates[month][0],
                                       "entry_date": dates[month][1], "exit_date": dates[month][2],
                                       "pool_n": len(pool), "spearman_financial_momentum": _spearman(pool, feature),
                                       "overlap_F_M": overlap_fm, "overlap_B_M": overlap_bm,
                                       "announcement_id_changes": ann_changes,
                                       "methods": {method: {**outcomes[method],
                                                            "holdings": sum(w > 0 for w in weights[method].values()),
                                                            "max_weight": max(weights[method].values()),
                                                            "target_replacement": turnover[method]}
                                                   for method in METHODS}}
            for row in pool:
                code, source = row["code"], row["source"]
                stock_rows.append({"scope": scope, "month": month, "decision_date": dates[month][0],
                                   "entry_date": dates[month][1], "exit_date": dates[month][2],
                                   "code": code, "industry": row["industry"],
                                   "momentum": row["momentum"], "financial_feature": feature,
                                   "financial_score": row[feature], "gpa": row["gpa"], "cfoa": row["cfoa"],
                                   "report_year": source["report_year"],
                                   "announcement_id": source["announcement_id"],
                                   "publication_date": source["publication_date"],
                                   "future_return": row["future"], "either_halt": row["halt"],
                                   **rank_details[code], **{f"weight_{method}": weights[method][code]
                                                            for method in METHODS}})
    return monthly, stock_rows, layer_rows


def _write_json(path, value):
    with path.open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.flush()
        os.fsync(f.fileno())


def _write_csv(path, rows):
    if not rows:
        return _write_json(path.with_suffix(".json"), {"status": "not_evaluated", "rows": []})
    fields = list(rows[0])
    with path.open("x", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
        f.flush()
        os.fsync(f.fileno())


def run(contract_path, out_path):
    started = time.monotonic()
    started_utc = datetime.now(timezone.utc).isoformat()
    contract_path = Path(contract_path).resolve()
    spec = json.loads(contract_path.read_text(encoding="utf-8"))
    if spec.get("schema") != "financial-evaluation-run/1":
        raise ValueError("wrong evaluation contract schema")
    bound = spec["inputs"]
    if set(bound) != {"design", "amendment", "cohort", "prices", "panel", "parser", "runner",
                      "panel_manifest", "panel_contract", "qualification_amendment"}:
        raise ValueError("missing/extraneous bound input")
    for name, item in bound.items():
        path = Path(item["path"]).resolve()
        if _sha(path) != item["sha256"]:
            raise ValueError(f"changed input: {name}")
    if (bound["design"]["sha256"] != DESIGN_SHA or
            bound["amendment"]["sha256"] != AMENDMENT_SHA or
            bound["cohort"]["sha256"] != COHORT_SHA or
            bound["parser"]["sha256"] != PARSER_SHA or
            Path(bound["runner"]["path"]).resolve() != Path(__file__).resolve()):
        raise ValueError("frozen protocol or runner identity mismatch")
    panel_manifest = json.loads(Path(bound["panel_manifest"]["path"]).read_text(encoding="utf-8"))
    panel_contract = json.loads(Path(bound["panel_contract"]["path"]).read_text(encoding="utf-8"))
    qualification = json.loads(Path(bound["qualification_amendment"]["path"]).read_text(encoding="utf-8"))
    if (panel_manifest.get("schema") != "financial-panel-result/1" or
            panel_manifest.get("contract_sha256") != bound["panel_contract"]["sha256"] or
            panel_manifest.get("outputs", {}).get("panel.csv") != bound["panel"]["sha256"] or
            Path(bound["panel"]["path"]).resolve() !=
            Path(panel_contract["output"]["path"]).resolve() / "panel.csv" or
            panel_manifest.get("inputs") != panel_contract.get("inputs") or
            panel_contract["inputs"].get("parser") != bound["parser"] or
            panel_contract["inputs"].get("design") != bound["design"] or
            panel_contract["inputs"].get("cohort") != bound["cohort"] or
            panel_contract["inputs"].get("qualification_amendment") != bound["qualification_amendment"] or
            qualification.get("root_accepted") is not True or qualification.get("effect_runs_before") != 0 or
            qualification.get("new_rules_sha256") != panel_contract["inputs"]["version_rules"]["sha256"]):
        raise ValueError("financial source qualification lineage differs from accepted panel")
    design = json.loads(Path(bound["design"]["path"]).read_text(encoding="utf-8"))
    amendment = json.loads(Path(bound["amendment"]["path"]).read_text(encoding="utf-8"))
    if (amendment["base_design_sha256"] != DESIGN_SHA or design["reuse"]["monthly_decisions"] != 132 or
            design["selection"]["fraction"] != 0.2 or design["stability"]["uncertainty"]["draws"] != 10000):
        raise ValueError("frozen design parameters not recognized")
    if spec.get("units") != {"momentum": "simple_decimal_return",
                             "future_return": "simple_decimal_return",
                             "gpa": "ratio", "cfoa": "ratio"}:
        raise ValueError("panel/price units not bound as frozen decimal ratios")
    price_map, panel_map, dates, codes = _load_inputs(bound)
    output = spec["output"]
    out_path = Path(out_path).resolve()
    mount = Path(output["mount"]).resolve()
    if (str(out_path) != str(Path(output["path"]).resolve()) or not os.path.ismount(mount) or
            mount.stat().st_dev != output["external_device"] or
            out_path.exists() or not out_path.parent.is_dir() or
            out_path.parent.stat().st_dev != output["external_device"]):
        raise ValueError("create-only external output binding failed")
    monthly, stock, layers = _evaluate(price_map, panel_map, dates, codes)
    performance, paired = _summaries(monthly)
    uncertainty = _bootstrap(monthly)
    other = _other(monthly)
    out_path.mkdir()
    _write_json(out_path / "monthly.json", list(monthly.values()))
    _write_csv(out_path / "stock_weights.csv", stock)
    _write_json(out_path / "qualification_layers.json", layers)
    _write_json(out_path / "performance.json", performance)
    _write_json(out_path / "paired.json", paired)
    _write_json(out_path / "uncertainty.json", uncertainty)
    _write_json(out_path / "other_uses.json", other)
    generated = {p.name: {"sha256": _sha(p), "bytes": p.stat().st_size}
                 for p in out_path.iterdir() if p.is_file() and not p.name.startswith("._") and p.name != ".DS_Store"}
    _write_json(out_path / "manifest.json", {"schema": "financial-evaluation-result/1",
                                              "contract_path": str(contract_path),
                                              "contract_sha256": _sha(contract_path),
                                              "inputs": bound, "outputs": generated,
                                              "started_utc": started_utc,
                                              "elapsed_seconds": time.monotonic() - started,
                                              "monthly_positions": 132,
                                              "scope_defined_months": {scope: sum((scope, m) in monthly for m in _months())
                                                                       for scope, _, _ in SCOPES},
                                              "interpretation": "quote selection research; unknown scenarios are assumptions, not executable wealth bounds"})
    return out_path


def _self_test():
    pool = [
        {"code": f"sh.60000{i}", "industry": "C26", "momentum": float(i),
         "gpa": float(6 - i), "cfoa": float(i), "future": None if i == 0 else 0.1,
         "halt": i == 0} for i in range(6)]
    pool += [{"code": "sz.000001", "industry": "C27", "momentum": -1.0,
              "gpa": -2.0, "cfoa": -3.0, "future": 0.2, "halt": False}]
    weights, detail = _weights(pool, "gpa")
    assert all(math.isclose(sum(weights[method].values()), 1) for method in METHODS)
    assert all(math.isclose(sum(weights[method].get(r["code"], 0) for r in pool if r["industry"] == "C26"), 6 / 7)
               for method in METHODS)
    assert detail["sz.000001"]["tiny_no_selection"]
    assert weights["P"]["sz.000001"] == weights["F"]["sz.000001"]
    assert weights["M"] != weights["F"] and weights["B"] != weights["D"]
    assert weights["F"]["sh.600000"] > 0 and weights["M"]["sh.600005"] > 0
    outcomes = _outcomes(pool, weights)
    assert outcomes["F"]["unknown_weight"] > 0
    assert outcomes["F"]["unknown_minus_one"] < outcomes["F"]["unknown_zero"]
    tied = [dict(r) for r in pool]
    for r in tied:
        r["gpa"] = 1.0
    tied_weights, _ = _weights(tied, "gpa")
    assert tied_weights["F"]["sh.600000"] > 0 and tied_weights["F"]["sh.600001"] > 0
    assert tied_weights["F"]["sh.600002"] == 0
    assert _moments([None] * 132)["status"] == "not_evaluated"
    assert _spearman(pool, "gpa") is not None
    try:
        _weights(pool + [dict(pool[0])], "gpa")
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate security was accepted")
    # A small entirely invented panel exercises both financial candidates on
    # exactly the same month and securities, with one GP-only observation.
    price_map, panel_map, dates = {}, {}, {}
    synthetic_codes = [r["code"] for r in pool]
    for month in _months():
        py, pm = map(int, _previous(month).split("-"))
        decision = f"{py:04d}-{pm:02d}-{calendar.monthrange(py, pm)[1]:02d}"
        entry, exit_ = month + "-01", _next(month) + "-01"
        dates[month] = (decision, entry, exit_)
        for row in pool:
            code = row["code"]
            price_map[(month, code)] = {"eligibility_reason": "eligible",
                                       "momentum": str(row["momentum"]),
                                       "future_return": "" if row["future"] is None else str(row["future"]),
                                       "either_halt": str(row["halt"])}
            panel_map[(month, code)] = {"industry": row["industry"], "gp_status": "qualified",
                                       "gpa": str(row["gpa"]),
                                       "cfo_status": "unknown" if code == "sh.600000" else "qualified",
                                       "cfoa": "" if code == "sh.600000" else str(row["cfoa"]),
                                       "report_year": "2014", "announcement_id": "synthetic",
                                       "publication_date": "2015-01-01", "reason": "synthetic_missing_cash"}
    monthly, stocks, layers = _evaluate(price_map, panel_map, dates, synthetic_codes)
    assert monthly[("gp", "2015-01")]["pool_n"] == 7
    assert monthly[("common_gp", "2015-01")]["pool_n"] == 6
    assert monthly[("common_cfo", "2015-01")]["pool_n"] == 6
    gp_common = {r["code"] for r in stocks if r["scope"] == "common_gp" and r["month"] == "2015-01"}
    cfo_common = {r["code"] for r in stocks if r["scope"] == "common_cfo" and r["month"] == "2015-01"}
    assert gp_common == cfo_common and "sh.600000" not in gp_common
    assert layers[0]["gp_pool"] == 7 and layers[0]["common_pool"] == 6
    for method in ("P", "M", "D"):
        assert (monthly[("common_gp", "2015-01")]["methods"][method]["unknown_zero"] ==
                monthly[("common_cfo", "2015-01")]["methods"][method]["unknown_zero"])
    perf, paired = _summaries(monthly)
    assert perf and paired
    assert any(r["comparison"] == "CFO_F-GP_F" and r["period"] == "all" for r in paired)
    sample_ci = _bootstrap(monthly, draws=20)
    assert sample_ci and all(r["shared_index_sha256"] for r in sample_ci)
    empty_ci = _bootstrap({}, draws=2)
    assert empty_ci and all(r["status"] == "not_evaluated" and r["draws_valid"] == 0
                            for r in empty_ci)
    assert _other({})
    print("self-test: sectors, ties, missing outcomes, duplicate security, same-date common pool, summaries, shared blocks passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        if args.contract or args.out:
            parser.error("--self-test cannot run market inputs")
        _self_test()
        return
    if not args.contract or not args.out:
        parser.error("--contract and --out required")
    print(run(args.contract, args.out))


if __name__ == "__main__":
    main()
