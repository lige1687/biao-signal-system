"""One frozen, retrospective 300-stock activity-stratified account batch.

Only ``--synthetic`` is available without a separately frozen contract and
output plan. The real path does no network access, never overwrites a result,
and refuses source, code or plan drift before opening any source payload.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

D = Path(__file__).resolve().parent
W = D.parents[3]
M = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
ENGINE = W / "src/lei_signal/research/reversal_activity.py"
CROSS_EXPRESSION = "(low_activity_G5-pool)-(high_activity_G5-pool)"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checked(ref):
    path = Path(ref["path"])
    if sha(path) != ref["sha256"]:
        raise ValueError(f"frozen binding changed: {path}")
    return path


def read(ref):
    return json.loads(checked(ref).read_text())


def write_json(path, obj):
    with path.open("x") as f:
        json.dump(obj, f, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def write_csv_gz(path, rows):
    rows = list(rows)
    with path.open("xb") as raw, gzip.GzipFile(fileobj=raw, mode="wb") as gz:
        import io
        with io.TextIOWrapper(gz, encoding="utf-8", newline="") as text:
            if rows:
                writer = csv.DictWriter(text, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)


def load_engine():
    spec = importlib.util.spec_from_file_location("bounded_reversal_activity", ENGINE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def dates_from_source(payload):
    dates = [r[0] for r in payload["data"] if r[1] == "1"]
    if dates != sorted(set(dates)):
        raise ValueError("invalid exchange calendar")
    return dates


def validate_universe(cohort, manifest, old_rows, cohort_sha256, acquisition):
    """Bind the fixed 300 source codes to the larger historical snapshot.

    Opportunity rows may cover fewer than 300 codes because qualification is
    sparse; every observed code must still belong to the frozen source set.
    """
    fields = cohort.get("fields")
    data = cohort.get("data")
    if not isinstance(fields, list) or "code" not in fields or not isinstance(data, list):
        raise ValueError("cohort schema invalid")
    code_ix = fields.index("code")
    if any(not isinstance(row, list) or len(row) != len(fields) for row in data):
        raise ValueError("cohort row width invalid")
    cohort_codes = [row[code_ix] for row in data]
    if any(not isinstance(code, str) or not code for code in cohort_codes):
        raise ValueError("cohort code invalid")
    if len(set(cohort_codes)) != len(cohort_codes):
        raise ValueError("cohort duplicate code")
    if manifest.get("cohort_sha256") != cohort_sha256:
        raise ValueError("manifest refers to a different cohort snapshot")
    if not isinstance(acquisition.get("cohort"), dict) or acquisition["cohort"].get("sha256") != cohort_sha256:
        raise ValueError("selection contract refers to a different cohort snapshot")
    if acquisition.get("selection_rule") != (
        "sha256(salt+|+code) ascending over historical cohort minus old600, first300; no replacement"
    ) or acquisition.get("salt") != "high52-independent-cohort-20261020":
        raise ValueError("historical selection rule changed")
    excluded = acquisition.get("excluded_old_codes")
    if not isinstance(excluded, list) or len(excluded) != 600 or len(set(excluded)) != 600:
        raise ValueError("historical exclusion list invalid")
    if not set(excluded) <= set(cohort_codes):
        raise ValueError("excluded code absent from historical cohort")
    ranked = sorted(set(cohort_codes)-set(excluded), key=lambda code: (
        hashlib.sha256(f"{acquisition['salt']}|{code}".encode()).hexdigest(), code))[:300]
    if len(ranked) != 300 or acquisition.get("codes") != ranked:
        raise ValueError("historical 300-code hash selection differs")
    assets = manifest.get("asset_sources")
    if not isinstance(assets, dict) or len(assets) != 300:
        raise ValueError("manifest must contain exactly 300 source codes")
    source_codes = set(assets)
    if source_codes != set(ranked):
        raise ValueError("manifest codes differ from hash-selected 300")
    if any(not isinstance(row, dict) or not isinstance(row.get("code"), str) or not row["code"]
           for row in old_rows):
        raise ValueError("opportunity code invalid")
    opportunity_codes = {row["code"] for row in old_rows}
    if not opportunity_codes <= source_codes:
        raise ValueError("opportunity codes absent from fixed source set")
    return {"cohort_codes": len(cohort_codes), "excluded_old_codes": len(excluded),
            "eligible_before_hash_selection": len(cohort_codes)-len(excluded),
            "source_codes": len(source_codes),
            "opportunity_codes": len(opportunity_codes),
            "source_without_opportunity": sorted(source_codes-opportunity_codes),
            "opportunity_coverage_of_source": len(opportunity_codes)/len(source_codes)}


def monthly_account(daily):
    by_month = defaultdict(list)
    for row in daily:
        by_month[row["date"][:7]].append(row)
    out = {}
    previous = 100000.0
    for month, rows in sorted(by_month.items()):
        nav = rows[-1]["nav_quote_proxy"]
        out[month] = {"month": month, "return": nav/previous-1,
                      "cash_fraction": sum(r["cash_fraction"] for r in rows)/len(rows),
                      "unknown_fraction": sum(r["unknown_fraction"] for r in rows)/len(rows),
                      "nav_end": nav}
        previous = nav
    return out


def performance(daily, trades, months):
    rows = [r for r in daily if r["date"][:7] in months]
    if not rows:
        return {"calendar_months": len(months), "observed_months": 0}
    first_idx = daily.index(rows[0])
    opening = daily[first_idx-1]["nav_quote_proxy"] if first_idx else 100000.0
    ratio = rows[-1]["nav_quote_proxy"]/opening
    peak, maxdd = opening, 0.0
    for r in rows:
        peak = max(peak, r["nav_quote_proxy"])
        maxdd = min(maxdd, r["nav_quote_proxy"]/peak-1)
    gross = sum(r["gross_traded_today"] for r in rows)
    return {"calendar_months": len(months), "observed_months": len({r["date"][:7] for r in rows}),
            "cumulative_return": ratio-1,
            "annualized_return": ratio**(12/len(months))-1 if ratio > 0 and months else None,
            "max_daily_drawdown": maxdd,
            "average_cash_fraction": sum(r["cash_fraction"] for r in rows)/len(rows),
            "average_unknown_fraction": sum(r["unknown_fraction"] for r in rows)/len(rows),
            "fees": rows[-1]["fees_cumulative"]-(daily[first_idx-1]["fees_cumulative"] if first_idx else 0),
            "trades": sum(t["date"][:7] in months for t in trades),
            "annual_traded_value_over_start_nav": gross/opening*12/len(months)}


def _periods():
    months = [f"{y:04d}-{m:02d}" for y in range(2015, 2026) for m in range(1, 13)]
    return {"full": months,
            "early": [x for x in months if "2015-01" <= x <= "2018-12"],
            "middle": [x for x in months if "2019-01" <= x <= "2021-12"],
            "late": [x for x in months if "2022-01" <= x <= "2025-12"]}


def cross_stratum_differences(gaps, low, high, months):
    """Calendar-keyed low-minus-high activity increment, never reversed."""
    return {m: gaps[low][m]-gaps[high][m]
            for m in months if m in gaps[low] and m in gaps[high]}


def _label_diagnostics(formations, old):
    """Descriptive old labels only; never used to form account membership."""
    index = {(r["month"], r["code"]): r for r in old}
    def number(value):
        try:
            result = float(value)
        except (ValueError, TypeError):
            return None
        return result if math.isfinite(result) else None
    rows = []
    for formation in formations:
        month = formation["month_end"][:7]
        for stratum in formation["strata"]:
            for name, weights in stratum["weights"].items():
                known = unknown = contribution = adverse = 0.0
                known_n = adverse_n = 0
                before_vol = before_mom = after_vol = after_mom = 0.0
                feature = {r["code"]: r for r in formation["features"]}
                pool_n = len(stratum["codes"])
                for code in stratum["codes"]:
                    before_vol += feature[code]["vol60"]/pool_n
                    before_mom += feature[code]["momentum"]/pool_n
                for code, weight in weights.items():
                    after_vol += weight*feature[code]["vol60"]
                    after_mom += weight*feature[code]["momentum"]
                    label = index.get((month, code), {})
                    value = number(label.get("return"))
                    if value is None:
                        unknown += weight
                    else:
                        known += weight
                        known_n += 1
                        contribution += weight*value
                    value = number(label.get("adverse"))
                    if value is not None:
                        adverse += weight*value
                        adverse_n += 1
                rows.append({"month": month, "stratum": stratum["stratum"], "portfolio": name,
                             "known_n": known_n, "known_weight": known, "unknown_weight": unknown,
                             "known_return_contribution": contribution,
                             "complete_return": contribution if unknown < 1e-12 else None,
                             "known_adverse_n": adverse_n,
                             "complete_adverse": adverse if adverse_n == len(weights) else None,
                             "pool_vol60": before_vol, "selected_vol60": after_vol,
                             "pool_momentum": before_mom, "selected_momentum": after_mom})
    return rows


def _rank(values):
    order = sorted(range(len(values)), key=lambda i: (values[i], i))
    ranks = [0.0]*len(values)
    start = 0
    while start < len(order):
        stop = start+1
        while stop < len(order) and values[order[stop]] == values[order[start]]:
            stop += 1
        rank = (start+1+stop)/2
        for i in order[start:stop]:
            ranks[i] = rank
        start = stop
    return ranks


def _rankic(formations, old):
    labels = {(r["month"], r["code"]): r.get("return") for r in old}
    rows = []
    for f in formations:
        month = f["month_end"][:7]
        feature = {r["code"]: r for r in f["features"]}
        for s in f["strata"]:
            pairs = []
            for code in s["codes"]:
                value = labels.get((month, code))
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    continue
                if math.isfinite(value):
                    pairs.append((-feature[code]["hot"], value))
            ic, why = None, None
            if len(pairs) < 3:
                why = "fewer_than_three_known_pairs"
            else:
                x = _rank([p[0] for p in pairs])
                y = _rank([p[1] for p in pairs])
                mx, my = sum(x)/len(x), sum(y)/len(y)
                xx = sum((v-mx)**2 for v in x)
                yy = sum((v-my)**2 for v in y)
                if xx*yy == 0:
                    why = "constant_rank"
                else:
                    ic = sum((a-mx)*(b-my) for a,b in zip(x,y))/(xx*yy)**0.5
            rows.append({"month": month, "stratum": s["stratum"],
                         "known_pairs": len(pairs), "rankic": ic, "reason": why})
    return rows


def _label_increments(rows):
    by_key = {(r["month"], r["stratum"], r["portfolio"]): r for r in rows}
    comparisons = (("G5", "pool"), ("G5", "lowvol"),
                   ("G5", "rev_volbalanced"), ("rev_volbalanced", "pool"))
    out = []
    for month, stratum in sorted({(m, s) for m, s, _ in by_key}):
        for candidate, baseline in comparisons:
            c = by_key.get((month, stratum, candidate))
            b = by_key.get((month, stratum, baseline))
            if c is None or b is None:
                continue
            cr, br = c["complete_return"], b["complete_return"]
            ca, ba = c["complete_adverse"], b["complete_adverse"]
            out.append({"month": month, "stratum": stratum,
                        "candidate": candidate, "baseline": baseline,
                        "known_return_contribution_difference":
                            c["known_return_contribution"]-b["known_return_contribution"],
                        "candidate_unknown_weight": c["unknown_weight"],
                        "baseline_unknown_weight": b["unknown_weight"],
                        "complete_return_difference": cr-br if cr is not None and br is not None else None,
                        "complete_adverse_difference": ca-ba if ca is not None and ba is not None else None})
    return out


def synthetic():
    engine = load_engine()
    days = [f"2014-12-{d:02d}" for d in range(1, 31)] + [f"2015-01-{d:02d}" for d in range(1, 32)]
    raw = {f"C{i:02d}": {day: {"amount": i, "tradestatus": "1"} for day in days} for i in range(90)}
    rows = [{"code": f"C{i:02d}", "hot": i, "vol60": 90-i, "momentum": i}
            for i in range(90)]
    result = engine.form_month(rows, raw, days, days[-1])
    assert result["eligible_n"] == 90 and all(s["qualified"] for s in result["strata"])
    assert all(len(s["weights"]) == 8 for s in result["strata"])
    print("synthetic formation: PASS; no real source opened")


def real():
    contract_path = D / "contract.json"
    contract = json.loads(contract_path.read_text())
    if contract.get("effects_authorized") is not True:
        raise ValueError("effects authorization absent")
    if contract.get("exact_runner_sha256") != sha(__file__):
        raise ValueError("runner code differs from frozen contract")
    if contract.get("exact_engine_sha256") != sha(ENGINE):
        raise ValueError("engine code differs from frozen contract")
    for ref in contract["bindings"]:
        checked(ref)
    plan = read(contract["storage_plan"])
    sys.path.insert(0, str(M / "src"))
    from lei_signal.research.high52_revalidation import adapt_back_adjusted, price_identity
    from lei_signal.research.fip import hac_mean
    from lei_signal.research.output_storage import recheck_saved_plan, _still_mounted
    plan = recheck_saved_plan(M, plan, plan["task_id"], plan["estimated_bytes"],
                              plan["internal_metadata_bytes"])
    if plan["estimated_bytes"] < 250*1024*1024:
        raise ValueError("storage estimate below frozen 250 MiB")
    output = Path(plan["output"])
    if output.exists():
        raise FileExistsError(output)
    refs = read(contract["input_refs"])
    for key in ("source_manifest", "calendar", "cohort", "original_input_rows", "acquisition_contract"):
        checked(refs[key])
    calendar = dates_from_source(read(refs["calendar"]))
    cohort = read(refs["cohort"])
    old = read(refs["original_input_rows"])
    if not isinstance(old, list):
        raise ValueError("old input rows must be a list")
    source = read(refs["source_manifest"])
    acquisition = read(refs["acquisition_contract"])
    universe_coverage = validate_universe(cohort, source, old, refs["cohort"]["sha256"], acquisition)
    # The old input rows are whitelisted. No outcome is passed to form_month.
    by_month = defaultdict(list)
    for row in old:
        by_month[row["month"]].append({k: row.get(k) for k in ("code", "hot", "vol60", "momentum")})
    if len(old) != 36019 or set(by_month) != set(load_engine().FORMATION_MONTHS):
        raise ValueError("historical opportunity set drifted")
    engine = load_engine()
    market, raw_by_code, source_audit = {}, {}, []
    calendar_index = {day: i for i, day in enumerate(calendar)}
    for code, pair in sorted(source["asset_sources"].items()):
        if not _still_mounted(plan):
            raise ValueError("bound output device disappeared")
        adapted = adapt_back_adjusted(read(pair["daily"]), read(pair["adjustments"]), code,
                                      calendar, factor_field="foreAdjustFactor")
        raw_by_code[code] = adapted["raw_by_day"]
        close_by_day = {r["date"]: r for r in adapted["rows"]}
        breaks = set(adapted["break_dates"])
        prior_source_day, latest = {}, None
        for day in calendar:
            prior_source_day[day] = latest
            if day in adapted["raw_by_day"]:
                latest = day
        market[code] = {day: engine.open_market_row(adapted, calendar, day, price_identity,
                      close_by_day, calendar_index, breaks, prior_source_day)
                        for day in calendar if "2014-12-01" <= day <= "2025-12-31"}
        source_audit.append({"code": code, "break_dates": adapted["break_dates"],
                             "failures": adapted["failures"]})
    month_ends = {day[:7]: day for day in calendar}
    formations = [engine.form_month(by_month[month], raw_by_code, calendar, month_ends[month])
                  for month in engine.FORMATION_MONTHS]
    # Membership and features are output before opening the first account; once
    # the external output directory exists a failed run is left as failed evidence.
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "universe-coverage.json", universe_coverage)
    write_json(output / "formations.json", formations)
    write_json(output / "source-audit.json", source_audit)
    write_csv_gz(output / "signal-features.csv.gz", (
        {"month": f["month_end"][:7], "code": r["code"], "hot": r["hot"],
         "vol60": r["vol60"], "momentum": r["momentum"], "amount60": r["amount60"]}
        for f in formations for r in f["features"]))
    labels = _label_diagnostics(formations, old)
    write_csv_gz(output / "old-label-diagnostics.csv.gz", labels)
    write_csv_gz(output / "old-label-increments.csv.gz", _label_increments(labels))
    write_csv_gz(output / "old-label-rankic.csv.gz", _rankic(formations, old))
    account_months, summary = {}, []
    dates = [d for d in calendar if "2014-12-01" <= d <= "2025-12-31"]
    for stratum in range(1, 4):
        for portfolio in engine.PORTFOLIOS:
            targets = {}
            for f in formations:
                s = f["strata"][stratum-1]
                targets[f["month_end"]] = {"qualified": s["qualified"],
                                            "weights": s["weights"].get(portfolio, {})}
            for fee in (0, 25):
                if not _still_mounted(plan):
                    raise ValueError("bound output device disappeared")
                key = f"s{stratum}__{portfolio}__fee{fee}"
                result = engine.simulate_open(dates, market, targets, cost_bps=fee,
                                              initial_cash=100000,
                                              start_date="2015-01-01", end_date="2025-12-31")
                for part, records in result.items():
                    write_csv_gz(output / f"{key}__{part}.csv.gz", records)
                account_months[key] = monthly_account(result["daily"])
                for period, months in _periods().items():
                    summary.append({"account": key, "period": period,
                                    **performance(result["daily"], result["trades"], months)})
    write_csv_gz(output / "account-summary.csv.gz", summary)
    write_json(output / "account-months.json", account_months)
    comparisons = []
    periods = _periods()
    by_summary = {(r["account"], r["period"]): r for r in summary}
    for stratum in range(1, 4):
        for fee in (0, 25):
            for candidate, opponent in (("G5", "pool"), ("G5", "lowvol"),
                                        ("G5", "rev_volbalanced"),
                                        ("rev_volbalanced", "pool")):
                candidate_key = f"s{stratum}__{candidate}__fee{fee}"
                baseline_key = f"s{stratum}__{opponent}__fee{fee}"
                candidate_month = account_months[candidate_key]
                baseline = account_months[baseline_key]
                pool_month = account_months[f"s{stratum}__pool__fee{fee}"]
                for period, months in periods.items():
                    differences = [candidate_month[m]["return"]-baseline[m]["return"]
                                   if m in candidate_month and m in baseline else None for m in months]
                    up = [difference if pool_month.get(m, {}).get("return", 0) > 0 else None
                          for m, difference in zip(months, differences)]
                    down = [difference if pool_month.get(m, {}).get("return", 0) < 0 else None
                            for m, difference in zip(months, differences)]
                    stat = hac_mean(differences, lag=3)
                    candidate_summary = by_summary[candidate_key, period]
                    base_summary = by_summary[baseline_key, period]
                    comparisons.append({"stratum": stratum, "fee_bps": fee,
                                        "candidate": candidate, "baseline": opponent,
                                        "period": period, "calendar_months": len(months),
                                        "hac3": {k: (v if math.isfinite(v) else None)
                                                 for k,v in stat.items()},
                                        "up_months": {"n": sum(v is not None for v in up),
                                                      "mean_difference": sum(v for v in up if v is not None)/sum(v is not None for v in up)
                                                      if any(v is not None for v in up) else None},
                                        "down_months": {"n": sum(v is not None for v in down),
                                                        "mean_difference": sum(v for v in down if v is not None)/sum(v is not None for v in down)
                                                        if any(v is not None for v in down) else None},
                                        "compounded_return_difference": candidate_summary["cumulative_return"]-base_summary["cumulative_return"],
                                        "max_drawdown_difference": candidate_summary["max_daily_drawdown"]-base_summary["max_daily_drawdown"]})
    write_json(output / "monthly-comparisons.json", comparisons)
    cross = []
    for fee in (0, 25):
        gaps = {}
        for stratum in range(1, 4):
            g5 = account_months[f"s{stratum}__G5__fee{fee}"]
            pool = account_months[f"s{stratum}__pool__fee{fee}"]
            gaps[stratum] = {m: g5[m]["return"]-pool[m]["return"]
                             for m in set(g5)&set(pool)}
        for high, low in ((2,1), (3,2), (3,1)):
            for period, months in periods.items():
                paired = cross_stratum_differences(gaps, low, high, months)
                stat = hac_mean([paired.get(m) for m in months], lag=3)
                cross.append({"fee_bps": fee, "higher_activity_stratum": high,
                              "lower_activity_stratum": low, "period": period,
                              "contrast_expression": CROSS_EXPRESSION,
                              "calendar_months": len(months), "monthly_differences": paired,
                              "hac3": {k: (v if math.isfinite(v) else None)
                                       for k,v in stat.items()}})
    write_json(output / "cross-stratum-increments.json", cross)
    write_json(output / "run-receipt.json", {"contract_sha256": sha(contract_path),
               "engine_sha256": sha(ENGINE), "runner_sha256": sha(__file__),
               "streams": 48, "new_market_requests": 0,
               "all_history_previously_seen": True,
               "execution_proxy_only": True,
               "not_executable_net_return": True})
    write_json(output / "manifest.json", {"files": {p.name: {"sha256": sha(p), "bytes": p.stat().st_size}
        for p in sorted(output.iterdir()) if p.is_file()}})
    print(f"completed: {output}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()
    synthetic() if args.synthetic else real()
