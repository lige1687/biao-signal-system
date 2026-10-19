"""Hash-bound, read-only diagnostics of the frozen fixed-600 study inputs.

No return series is rerun.  Output describes source health and alternative
calendar-month price scores; it cannot establish executable trades.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

CODE_RE = re.compile(r"^(?:sh\.60|sz\.00|sz\.30)\d{4}$")


def insist(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def checked(ref):
    path = Path(ref["path"])
    insist(path.is_file() and sha256(path) == ref["sha256"], f"missing or changed input: {path}")
    return path


def table(doc, required):
    fields = doc["fields"]
    insist(len(set(fields)) == len(fields) and set(required) <= set(fields), "source columns missing or repeated")
    for values in doc["data"]:
        insist(len(values) == len(fields), "source row length differs from fields")
        yield dict(zip(fields, values))


def decimal(value):
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def positive(value):
    n = decimal(value)
    return n if n is not None and n > 0 else None


def status(row):
    if row is None:
        return "missing"
    if str(row.get("tradestatus")) == "0":
        return "halt"
    if str(row.get("tradestatus")) != "1" or positive(row.get("close")) is None:
        return "invalid"
    return "traded"


def one_price_up(row):
    if row is None or status(row) != "traded":
        return False
    prices = [decimal(row.get(k)) for k in ("open", "high", "low", "close")]
    change, volume = decimal(row.get("pctChg")), decimal(row.get("volume"))
    return (all(p is not None for p in prices) and len(set(prices)) == 1
            and change is not None and change > 0 and volume is not None and volume > 0)


def selected_exposure(weight, entry_row, decision, out_date):
    """Keep saved selection weight; execution flags never rerank or redistribute."""
    selected = weight > 0
    return {"selected": selected, "weight": weight,
            "entry_state": status(entry_row),
            "pre_exit_selected": selected and bool(out_date) and decision <= out_date}


def months_before(month, count):
    year, number = map(int, month.split("-"))
    index = year * 12 + number - 1 - count
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def calendar_days(doc):
    days, previous = [], ""
    for row in table(doc, ("calendar_date", "is_trading_day")):
        day = row["calendar_date"]
        date.fromisoformat(day)
        insist(day > previous, "calendar not strictly increasing")
        previous = day
        if str(row["is_trading_day"]) in ("1", "True", "true"):
            days.append(day)
    insist(len(days) == len(set(days)), "duplicate trading date")
    return days


def month_endpoints(calendar):
    last = {}
    for day in calendar:
        last[day[:7]] = day
    return last


def calendar_score(quotes, ends, decision):
    month = decision[:7]
    a, b = ends.get(months_before(month, 1)), ends.get(months_before(month, 12))
    if not a or not b:
        return None, a, b, "calendar_missing"
    first, last = quotes.get(a), quotes.get(b)
    for row in (first, last):
        s = status(row)
        if s != "traded":
            return None, a, b, f"endpoint_{s}"
    return positive(first["close"]) / positive(last["close"]) - 1, a, b, "ok"


def actual_quote_index(quotes):
    valid = sorted((day, positive(row.get("close"))) for day, row in quotes.items()
                   if status(row) == "traded" and positive(row.get("close")) is not None
                   and str(row.get("isST")) in ("0", "1"))
    return valid, [day for day, _ in valid]


def actual_quote_features(index, decision):
    valid, days = index
    i = bisect_right(days, decision) - 1
    if i < 0 or days[i] != decision:
        return None, None, None
    start252 = valid[i - 252][0] if i >= 252 else None
    start21 = valid[i - 21][0] if i >= 21 else None
    value = valid[i - 21][1] / valid[i - 252][1] - 1 if i >= 252 else None
    return value, start21, start252


def average_ranks(values):
    ranked = sorted(values.items(), key=lambda item: (-item[1], item[0]))
    result, i = {}, 0
    while i < len(ranked):
        j = i + 1
        while j < len(ranked) and ranked[j][1] == ranked[i][1]:
            j += 1
        rank = Decimal(i + 1 + j) / 2
        for code, _ in ranked[i:j]:
            result[code] = rank
        i = j
    return result


def load_saved(path):
    with path.open(newline="", encoding="utf-8") as stream:
        yield from csv.DictReader(stream)


def repo_root(script):
    for parent in script.resolve().parents:
        if parent.name == ".codex":
            return parent.parent
    raise ValueError("script is not in expected managed worktree")


def source_health(source, code, calendar_set):
    insist(source.get("error_code") == "0", f"failed source: {code}")
    quotes, bad_adjust, previous = {}, 0, ""
    for row in table(source, ("date", "code", "close", "tradestatus", "isST", "adjustflag",
                              "open", "high", "low", "pctChg", "volume")):
        day = row["date"]
        date.fromisoformat(day)
        insist(row["code"] == code and day > previous and day in calendar_set,
               f"wrong, unordered, repeated, or noncalendar source row: {code} {day}")
        previous = day
        quotes[day] = row
        bad_adjust += str(row["adjustflag"]) != "2"
    return quotes, bad_adjust


def audit(design_path, plan_path, output):
    design_path, plan_path, output = map(Path, (design_path, plan_path, output))
    design, plan = json.loads(design_path.read_text()), json.loads(plan_path.read_text())
    insist(str(output) == design["output"] == plan["output"], "output differs from frozen route")
    contract_path = checked(design["input_contract"])
    contract = json.loads(contract_path.read_text())
    insist(contract.get("schema") == "lowfreq-evaluator-contract/1", "wrong input contract schema")
    for name in ("design", "cohort", "calendar"):
        checked(contract[name])
    for name in ("saved_per_stock", "saved_monthly"):
        checked(design[name])
    sources = contract["sources"]
    insist(len(sources) == 600 and len({s["code"] for s in sources}) == 600, "expected 600 distinct sources")
    for source in sources:
        insist(source.get("status") == "ok" and source["request"]["code"] == source["code"]
               and source["request"]["adjustflag"] == "2", "unqualified source request")
        checked(source)
    # Every bound byte is checked before the first statistic, including sources later quarantined.
    original_design = json.loads(Path(contract["design"]["path"]).read_text())
    cohort = json.loads(Path(contract["cohort"]["path"]).read_text())
    calendar = calendar_days(json.loads(Path(contract["calendar"]["path"]).read_text()))
    ends = month_endpoints(calendar)
    sample_size = original_design["universe"]["sample_size"]
    insist(sample_size == 600, "frozen sample size changed")
    asof = original_design["universe"]["asof"]
    membership = {}
    for row in table(cohort, ("code",)):
        code = row["code"]
        if not CODE_RE.fullmatch(code):
            continue
        ipo, out = row.get("ipoDate") or row.get("ipo_date"), row.get("outDate") or row.get("out_date")
        if not ipo or ipo > asof or (out and out <= asof) or str(row.get("type", "1")) not in ("1", ""):
            continue
        membership[code] = (ipo, out or None)
    ordered = sorted(membership, key=lambda c: (hashlib.sha256(("lowfreq-20141231-v1|" + c).encode()).hexdigest(), c))[:600]
    insist(set(ordered) == {s["code"] for s in sources}, "source set differs from frozen cohort")

    saved = {}
    for row in load_saved(Path(design["saved_per_stock"]["path"])):
        key = (row["month"], row["code"])
        insist(key not in saved, "duplicate saved per-stock row")
        saved[key] = row
    monthly = {r["month"]: r for r in load_saved(Path(design["saved_monthly"]["path"]))}
    months = sorted(monthly)
    insist(len(months) == 132 and len(saved) == 132 * 600, "saved panel is not 132 x 600")
    insist(months[0] == "2015-01" and months[-1] == "2025-12"
           and all(months_before(months[i], 1) == months[i - 1] for i in range(1, len(months))),
           "saved months are not the frozen consecutive 132 months")
    for month in months:
        old_month = monthly[month]
        expected_decision = ends.get(months_before(month, 1))
        decision = old_month["decision_date"]
        at = bisect_right(calendar, decision)
        insist(decision == expected_decision and at < len(calendar) and calendar[at] == old_month["entry_date"],
               f"saved monthly decision/entry timing differs from calendar: {month}")
    for month in months:
        insist(sum((month, code) in saved for code in ordered) == 600, f"saved universe incomplete: {month}")
        for code in ordered:
            row = saved[(month, code)]
            insist(row["decision_date"] == monthly[month]["decision_date"]
                   and row["entry_date"] == monthly[month]["entry_date"],
                   f"per-stock timing differs from saved month: {month} {code}")

    # Capacity and device identity are rechecked before any output directory exists.
    root = repo_root(Path(__file__))
    sys.path.insert(0, str(root / "src"))
    from lei_signal.research.output_storage import recheck_saved_plan
    recheck_saved_plan(root, plan, plan["task_id"], plan["estimated_bytes"], plan["internal_metadata_bytes"])
    insist(not output.exists(), "output already exists")

    per_rows = []
    aggregates = {m: Counter() for m in months}
    ranks = {m: {"saved": {}, "calendar": {}} for m in months}
    bad_sources = []
    later_delisted_codes = {c for c in ordered if membership[c][1]}
    calendar_set = set(calendar)
    for item in sources:
        code = item["code"]
        quotes, bad_adjust = source_health(json.loads(Path(item["path"]).read_text()), code, calendar_set)
        actual_index = actual_quote_index(quotes) if not bad_adjust else None
        if bad_adjust:
            bad_sources.append(code)
        for month in months:
            old = saved[(month, code)]
            decision, entry = old["decision_date"], old["entry_date"]
            at_t, at_entry = quotes.get(decision), quotes.get(entry)
            cal_value, ep1, ep12, ep_reason = calendar_score(quotes, ends, decision) if not bad_adjust else (None, None, None, "source_quarantine")
            actual_value, actual21, actual252 = actual_quote_features(actual_index, decision) if not bad_adjust else (None, None, None)
            old_score = decimal(old["momentum"])
            saved_start252 = old.get("momentum_252_start_date") or None
            saved_start21 = None  # Original CSV records 21-day span, not its exact source date.
            selected_weight = decimal(old.get("weight_momentum_top20")) or Decimal(0)
            exposure = selected_exposure(selected_weight, at_entry, decision, membership[code][1])
            selected = exposure["selected"]
            eligible = old["eligibility_reason"] == "eligible"
            common = eligible and not bad_adjust and cal_value is not None and old_score is not None
            if common:
                ranks[month]["saved"][code] = old_score
                ranks[month]["calendar"][code] = cal_value
            agg = aggregates[month]
            agg["original600"] += 1
            agg["saved_reason_" + old["eligibility_reason"]] += 1
            agg["source_qualified"] += not bool(bad_adjust)
            agg["source_quarantined"] += bool(bad_adjust)
            agg["current_" + status(at_t)] += 1
            agg["current_ST"] += at_t is not None and str(at_t.get("isST")) == "1"
            agg["next_" + status(at_entry)] += 1
            agg["current_oneprice_up_ambiguous"] += one_price_up(at_t)
            agg["next_oneprice_up_ambiguous"] += one_price_up(at_entry)
            agg["calendar_" + ep_reason] += 1
            agg["calendar_common"] += common
            agg["actual252_start_mismatch_saved"] += (saved_start252 is not None and actual252 is not None and saved_start252 != actual252)
            if selected:
                agg["saved_top20_count"] += 1
                agg["saved_top20_weight"] += selected_weight
                agg["top20_next_" + status(at_entry)] += 1
                agg["top20_next_" + status(at_entry) + "_weight"] += selected_weight
                agg["top20_next_oneprice_up_ambiguous"] += one_price_up(at_entry)
                agg["top20_next_oneprice_up_ambiguous_weight"] += selected_weight if one_price_up(at_entry) else 0
            if code in later_delisted_codes:
                agg["later_delisted_member"] += 1
                if exposure["pre_exit_selected"]:
                    agg["later_delisted_preexit_top20_count"] += 1
                    agg["later_delisted_preexit_top20_weight"] += selected_weight
            per_rows.append({"month": month, "code": code, "decision_date": decision, "entry_date": entry,
                             "saved_reason": old["eligibility_reason"], "source_qualified": not bool(bad_adjust),
                             "bad_adjust_rows": bad_adjust, "current_state": status(at_t),
                             "current_ST": at_t is not None and str(at_t.get("isST")) == "1",
                             "next_state": status(at_entry), "current_oneprice_up_ambiguous": one_price_up(at_t),
                             "next_oneprice_up_ambiguous": one_price_up(at_entry),
                             "calendar_t_minus_1": ep1, "calendar_t_minus_12": ep12,
                             "calendar_score": cal_value, "calendar_reason": ep_reason,
                             "saved_momentum": old_score, "same_universe_common": common,
                             "score_difference": cal_value - old_score if common else None,
                             "actual252_score": actual_value, "actual21_start": actual21,
                             "actual252_start": actual252, "saved252_start": saved_start252,
                             "saved21_start": saved_start21, "selected_weight_unchanged": selected_weight,
                             "later_delisted": code in later_delisted_codes,
                             "out_date": membership[code][1] or ""})

    rank_saved, rank_calendar = {}, {}
    monthly_rows = []
    for month in months:
        a, b = ranks[month]["saved"], ranks[month]["calendar"]
        insist(set(a) == set(b), "rank comparison universes differ")
        rank_saved[month], rank_calendar[month] = average_ranks(a), average_ranks(b)
        differences = [abs(float(a[c] - b[c])) for c in a]
        rank_differences = [abs(float(rank_saved[month][c] - rank_calendar[month][c])) for c in a]
        agg = aggregates[month]
        monthly_rows.append({"month": month, "decision_date": monthly[month]["decision_date"],
                             "saved_status": monthly[month]["status"], **{k: str(v) for k, v in sorted(agg.items())},
                             "same_universe_score_diff_count": sum(x > 1e-12 for x in differences),
                             "same_universe_score_abs_max": max(differences, default=None),
                             "same_universe_rank_diff_count": sum(x > 0 for x in rank_differences),
                             "same_universe_rank_abs_max": max(rank_differences, default=None)})
    for row in per_rows:
        month, code = row["month"], row["code"]
        row["saved_average_rank_common"] = rank_saved[month].get(code)
        row["calendar_average_rank_common"] = rank_calendar[month].get(code)
        row["rank_difference_common"] = (rank_calendar[month][code] - rank_saved[month][code]
                                         if code in rank_saved[month] else None)

    output.mkdir(parents=True, exist_ok=False)
    def write_csv(name, rows):
        path = output / name
        fields = list(dict.fromkeys(k for row in rows for k in row))
        with path.open("x", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fields)
            writer.writeheader()
            for row in rows:
                writer.writerow({k: str(v) if v is not None else "" for k, v in row.items()})
        return path
    per_path = write_csv("per_stock_audit.csv", per_rows)
    monthly_path = write_csv("monthly_health.csv", monthly_rows)
    summary = {"schema": "fixed600-saved-input-audit/1", "months": len(months), "original_sources": len(sources),
               "quarantined_adjustflag_sources": bad_sources, "later_delisted_cohort_codes": sorted(later_delisted_codes),
               "same_universe_common_rows": sum(int(r["same_universe_common"]) for r in per_rows),
               "score_abs_max": max((abs(float(r["score_difference"])) for r in per_rows if r["score_difference"] is not None), default=None),
               "rank_abs_max": max((abs(float(r["rank_difference_common"])) for r in per_rows if r["rank_difference_common"] is not None), default=None),
               "unavailable": ["nominal unadjusted price", "historical total and free-float shares",
                               "exact price limit", "order book and actual fill", "new returns or costs"],
               "interpretation": "one-price-up is an ambiguous diagnostic; selected weight is preserved without reranking",
               "scope": "Saved-input audit only. No new return, cost, fill, or whole-system effectiveness claim."}
    summary_path = output / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest = {"runner": {"path": str(Path(__file__).resolve()), "sha256": sha256(__file__)},
                "design": {"path": str(design_path), "sha256": sha256(design_path)},
                "input_contract": design["input_contract"], "saved_per_stock": design["saved_per_stock"],
                "saved_monthly": design["saved_monthly"], "cohort": contract["cohort"],
                "calendar": contract["calendar"], "source_count": len(sources),
                "source_sha256": {s["code"]: s["sha256"] for s in sources},
                "outputs": {p.name: sha256(p) for p in (per_path, monthly_path, summary_path)}}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary


def self_test():
    days = ["2014-01-30", "2014-01-31", "2014-12-30", "2014-12-31", "2015-01-29", "2015-01-30"]
    ends = month_endpoints(days)
    q = {"2014-01-31": {"close": "10", "tradestatus": "1", "isST": "0"},
         "2014-12-31": {"close": "12", "tradestatus": "1", "isST": "0"},
         "2015-01-30": {"close": "20", "tradestatus": "1", "isST": "0"}}
    score, newer, older, reason = calendar_score(q, ends, "2015-01-30")
    assert (score, newer, older, reason) == (Decimal("0.2"), "2014-12-31", "2014-01-31", "ok")
    halted = dict(q)
    halted["2014-12-31"] = {"close": "12", "tradestatus": "0"}
    assert calendar_score(halted, ends, "2015-01-30")[3] == "endpoint_halt"
    # A suspended quote can make actual-quote indexing differ from shared month ends.
    actual = {f"2014-01-{i:02d}": {"close": "10", "tradestatus": "1", "isST": "0"} for i in range(1, 29)}
    actual.update(q)
    assert calendar_score(halted, ends, "2015-01-30")[0] is None
    assert actual_quote_features(actual_quote_index(actual), "2015-01-30")[0] is None  # too few actual rows
    many = {f"2014-{month:02d}-{day:02d}": {"close": "10", "tradestatus": "1", "isST": "0"}
            for month in range(1, 12) for day in range(1, 25)}
    many["2014-12-31"] = {"close": "12", "tradestatus": "0", "isST": "0"}
    many["2015-01-30"] = {"close": "20", "tradestatus": "1", "isST": "0"}
    indexed_score, start21, start252 = actual_quote_features(actual_quote_index(many), "2015-01-30")
    assert indexed_score == Decimal(0) and start21 == "2014-11-04" and start252 == "2014-01-13"
    assert calendar_score(many, ends, "2015-01-30")[3] == "endpoint_halt"
    changed_future = dict(q)
    changed_future["2015-02-02"] = {"close": "999", "tradestatus": "1"}
    assert calendar_score(changed_future, ends, "2015-01-30")[0] == score
    assert average_ranks({"A": score, "B": Decimal("0.1")}) == {"A": Decimal(1), "B": Decimal(2)}
    assert average_ranks({"A": score, "B": Decimal("0.1")}) == average_ranks({"A": calendar_score(changed_future, ends, "2015-01-30")[0], "B": Decimal("0.1")})
    out_date = "2020-06-01"
    exposure = selected_exposure(Decimal("0.2"), {"close": "10", "tradestatus": "0"}, "2015-01-30", out_date)
    assert exposure == {"selected": True, "weight": Decimal("0.2"), "entry_state": "halt", "pre_exit_selected": True}
    assert selected_exposure(Decimal("0.8"), {"close": "10", "tradestatus": "1"}, "2015-01-30", None)["weight"] == Decimal("0.8")
    assert one_price_up({"open": "1.00", "high": "1.0", "low": "1", "close": "1.000",
                         "pctChg": "1", "volume": "10", "tradestatus": "1"})
    print("self-test passed: calendar endpoints, suspension, future isolation, delisting, frozen weight, Decimal one-price")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design")
    parser.add_argument("--storage-plan")
    parser.add_argument("--out")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    insist(all((args.design, args.storage_plan, args.out)), "--design --storage-plan --out required")
    print(json.dumps(audit(args.design, args.storage_plan, args.out), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
