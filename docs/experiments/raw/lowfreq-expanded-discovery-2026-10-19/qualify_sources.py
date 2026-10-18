"""Inspect frozen source coverage and signal availability without future returns."""
import argparse
import collections
import hashlib
import json
from datetime import datetime
from pathlib import Path

from lei_signal.research import lowfreq_discovery as study


def run(contract_path, output_path):
    spec = json.loads(Path(contract_path).read_text())
    design, _ = study._bound(spec["design"])
    cohort, _ = study._bound(spec["cohort"])
    calendar_doc, _ = study._bound(spec["calendar"])
    codes, population, membership = study._cohort(cohort, "2014-12-31", 600)
    calendar = study._calendar(calendar_doc)
    periods = study._decision_and_execution_dates(calendar)
    sources = {s["code"]: s for s in spec["sources"]}
    if len(sources) != len(spec["sources"]) or set(sources) != set(codes):
        raise ValueError("source universe differs from fixed draw")
    monthly = {m: {"month": m, "eligible": 0, "reasons": collections.Counter(),
                   "blocking_errors": []} for m, *_ in periods}
    summaries, spans, errors_all = [], [], []
    total_rows = normalized = 0
    for code in codes:
        item = sources[code]
        if item["status"] != "ok":
            raise ValueError("unqualified source")
        data, path = study._bound(item)
        quote, valid, errors = study._quotes(data, code, item["request"], calendar, membership[code])
        feature = study._features(valid, calendar, quote)
        total_rows += len(quote)
        normalized += sum(q["normalized_halt_amount"] for q in quote.values())
        errors_all.extend({"code": code, "date": d, "reason": reason} for d, reason in errors)
        summaries.append({"code": code, "rows": len(quote), "first": min(quote),
                          "last": max(quote), "out_date": membership[code]["out"],
                          "error_count": len(errors), "sha256": item["sha256"]})
        for month, decision, *_ in periods:
            m = monthly[month]
            faults = study._relevant_errors(decision, calendar, [code], {code: quote},
                                           {code: feature}, {code: errors}, {code: membership[code]})
            m["blocking_errors"].extend(faults)
            q, f = quote.get(decision), feature.get(decision)
            member = membership[code]
            if decision < member["ipo"] or (member["out"] and decision > member["out"]):
                reason = "outside_historical_listing"
            elif not q or not q["traded"] or not q["close"] or q["close"] <= 0:
                reason = "no_actual_month_end_quote"
            elif not f or f["valid_count"] < 253:
                reason = "under_253_actual_quotes"
            elif any(f[k] is None for k in ("momentum", "short", "vol60", "amount20")):
                reason = "incomplete_factor"
            elif q["is_st"]:
                reason = "historical_isST"
            else:
                reason = "eligible"
                m["eligible"] += 1
                spans.append({"month": month, "code": code,
                              "days_252": f["momentum_252_calendar_days"],
                              "days_21": f["momentum_21_calendar_days"]})
            m["reasons"][reason] += 1
    destination = study._check_output_parent(spec, output_path)
    destination.mkdir()
    available = [m["month"] for m in monthly.values() if not m["blocking_errors"] and m["eligible"]]
    report = {
        "at": datetime.now().astimezone().isoformat(),
        "scope": "source coverage and past-looking signal availability only; no forward returns computed",
        "contract_sha256": hashlib.sha256(Path(contract_path).read_bytes()).hexdigest(),
        "historical_population": population, "fixed_sources": len(codes),
        "total_daily_rows": total_rows, "normalized_halt_amount_rows": normalized,
        "later_exits_recorded": sum(bool(m["out"]) for m in membership.values()),
        "exits_by_2025_end": sum(bool(m["out"] and m["out"] <= "2025-12-31") for m in membership.values()),
        "months_with_qualified_input": len(available), "available_months": available,
        "source_error_counts": dict(collections.Counter(e["reason"] for e in errors_all)),
        "eligible_count_min_max": [min(m["eligible"] for m in monthly.values()), max(m["eligible"] for m in monthly.values())],
        "warning": "provider-defined 2014 historical pool; full exchange completeness and historical data revision independently unverified",
    }
    for name, value in (("summary.json", report), ("monthly.json", list(monthly.values())),
                        ("source-errors.json", errors_all), ("sources.json", summaries)):
        with (destination / name).open("x") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
    study._write_csv(destination / "signal-spans.csv", spans)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--contract", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    run(a.contract, a.out)
