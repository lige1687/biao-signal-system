"""Read-only recent BaoStock source audit for the nine missing CN breadth dates.

This audits raw quote eligibility, not an adjusted-price breadth value. It reads
registered source pointers in place and writes only the small sibling JSON.
"""

import gzip
import hashlib
import json
import math
from bisect import bisect_right
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd


ROOT = Path("/Volumes/win+mac通用/LeiSignal-新实验结果")
MAIN = ROOT / "public-universe-deep-completion-20261026/public-universe-deep-completion-20261026-20261026T225421-69a3af262800/result/cn-all-equity/all-equity-read-index-v8.jsonl"
OLD = ROOT / "twenty-year-universe-data-20261025/twenty-year-universe-data-20261025-20261025T154847-f27d39c4e083/result/cn/stock-source-union-v4/actual-date-unions.jsonl"
CODES = Path("/Users/yongbiaoli/.lei_signal_lab/cache/a_share_codes.json")
OUT = Path(__file__).with_suffix(".json")
DATES = ("2026-08-19", "2026-09-09", "2026-09-22", "2026-09-23",
         "2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23")
START = "2025-05-01"


def rows(path):
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as f:
        obj = json.load(f)
    fields = obj.get("fields") or []
    return (dict(zip(fields, row)) for row in obj.get("data", []))


def relevant(ref):
    first = ref.get("observed_first_date") or ref.get("first") or ref.get("first_date")
    last = ref.get("observed_last_date") or ref.get("last") or ref.get("last_date")
    return bool(first and last and last >= START and first <= DATES[-1])


def main():
    current = json.loads(CODES.read_text())["codes"]
    current_set = set(current)
    old = {x["code"]: x for x in map(json.loads, OLD.open())}
    summary = {day: Counter() for day in DATES}
    by_market = {day: defaultdict(Counter) for day in DATES}
    exceptions = []
    source_paths = set()
    factor_paths = set()
    factor_errors = []
    breadth = {day: Counter() for day in DATES}
    comparisons = {day: Counter() for day in DATES}
    comparison_examples = []
    index_codes = set()
    qfq = pd.read_parquet(
        "/Users/yongbiaoli/.lei_signal_lab/cache/a_share_klines_qfq.parquet",
        columns=["symbol", "date", "close"],
    )
    qfq = qfq[qfq.date.ge(START)]
    qfq_by_code = {code: dict(zip(g.date, g.close)) for code, g in qfq.groupby("symbol")}

    for x in map(json.loads, MAIN.open()):
        dotted = x["code"]
        code = dotted.replace(".", "")
        if code not in current_set:
            continue
        index_codes.add(code)
        market = code[:2]
        ipo = x.get("supplier_ipo") or "9999"
        out = x.get("supplier_out") or "9999"
        pointers = list(x.get("new_price_sources") or []) + list(x.get("reused_raw_sources") or [])
        if x.get("old_union_lookup"):
            pointers += old.get(dotted, {}).get("source_refs", [])
        factor_refs = list(x.get("new_factor_sources") or []) + list(x.get("reused_factor_sources") or [])
        if x.get("old_union_factor_source"):
            factor_refs.append(x["old_union_factor_source"])
        factor_content_valid = bool(factor_refs)
        factor_events = {}
        for ref in factor_refs:
            path = str(ref.get("source_path") or ref.get("path"))
            factor_paths.add(path)
            opener = gzip.open if path.endswith(".gz") else open
            with opener(path, "rt", encoding="utf-8") as f:
                obj = json.load(f)
            if obj.get("error_code") != "0" or obj.get("fields") != ["code", "dividOperateDate", "foreAdjustFactor", "backAdjustFactor", "adjustFactor"]:
                factor_content_valid = False
                factor_errors.append({"code": code, "path": path, "reason": "source_error_or_fields"})
            for event in obj.get("data", []):
                try:
                    if event[0] != dotted or any(not math.isfinite(float(v)) or float(v) <= 0 for v in event[2:5]):
                        raise ValueError("bad factor row")
                    if event[1] in factor_events and factor_events[event[1]] != event[2:5]:
                        raise ValueError("factor event conflict")
                    factor_events[event[1]] = event[2:5]
                except (ValueError, TypeError, IndexError):
                    factor_content_valid = False
                    factor_errors.append({"code": code, "path": path, "reason": "bad_event_or_conflict"})
        prices = {}
        for ref in pointers:
            if not relevant(ref):
                continue
            path = str(ref.get("source_path") or ref.get("path"))
            source_paths.add(path)
            for row in rows(path):
                day = row.get("date")
                if not day or day < START or day > DATES[-1]:
                    continue
                try:
                    close = float(row["close"])
                    volume = float(row["volume"])
                    amount = float(row["amount"])
                except (ValueError, TypeError, KeyError):
                    close = volume = amount = float("nan")
                state = (str(row.get("tradestatus")), close, volume, amount)
                if day in prices and prices[day] != state:
                    exceptions.append({"code": code, "date": day, "reason": "overlap_conflict"})
                prices[day] = state
        valid_days = sorted(day for day, (st, cl, vo, am) in prices.items()
                            if st == "1" and all(math.isfinite(v) and v > 0 for v in (cl, vo, am)))
        action_days = sorted(factor_events)
        adjusted = {}
        for date_ in valid_days:
            j = bisect_right(action_days, date_) - 1
            if j < 0:
                continue
            adjusted[date_] = prices[date_][1] * float(factor_events[action_days[j]][0])
        adjusted_days = sorted(adjusted)
        qfq_prices = qfq_by_code.get(code, {})
        for day in DATES:
            if not ipo <= day <= out:
                continue
            total = summary[day]
            group = by_market[day][market]
            total["current_list_supplier_active"] += 1
            group["current_list_supplier_active"] += 1
            state = prices.get(day)
            if state is None:
                reason = "raw_row_missing"
            elif state[0] == "0":
                reason = "nontrading_status0"
            elif state[0] != "1" or not all(math.isfinite(v) and v > 0 for v in state[1:]):
                reason = "invalid_quote"
            else:
                reason = "strict_quote"
            total[reason] += 1
            group[reason] += 1
            if reason == "strict_quote":
                n = sum(d <= day for d in valid_days)
                if n >= 200:
                    total["raw_200_eligible"] += 1
                    group["raw_200_eligible"] += 1
                else:
                    total["raw_warmup_under_200"] += 1
                    group["raw_warmup_under_200"] += 1
                if day not in adjusted:
                    total["no_effective_factor_event_by_day"] += 1
                    group["no_effective_factor_event_by_day"] += 1
            if factor_refs:
                total["has_factor_source_pointer"] += 1
                group["has_factor_source_pointer"] += 1
            if factor_content_valid:
                total["factor_content_valid"] += 1
                group["factor_content_valid"] += 1
            if day in adjusted:
                prior = adjusted_days[:bisect_right(adjusted_days, day)]
                for window in (20, 50, 200):
                    if len(prior) < window:
                        continue
                    b = breadth[day]
                    b[f"E{window}"] += 1
                    if adjusted[day] * window > sum(adjusted[d] for d in prior[-window:]):
                        b[f"above{window}"] += 1
                if len(prior) >= 200:
                    b = breadth[day]
                    if adjusted[day] * 50 > sum(adjusted[d] for d in prior[-50:]):
                        b["above50_on_E200"] += 1
                    if day in qfq_prices:
                        c = comparisons[day]
                        c["target_day_overlap"] += 1
                        recent = prior[-200:]
                        if all(d in qfq_prices for d in recent):
                            c["full_200_date_overlap"] += 1
                            anchor_a = adjusted[day]
                            anchor_q = qfq_prices[day]
                            max_diff = max(abs((adjusted[d] / anchor_a) / (qfq_prices[d] / anchor_q) - 1) for d in recent)
                            if max_diff <= 0.0001:
                                c["shape_within_1bp"] += 1
                            else:
                                c["shape_over_1bp"] += 1
                                comparison_examples.append({"code": code, "target": day, "max_relative_shape_difference": round(max_diff, 8)})
                            if max_diff > 0.001:
                                c["shape_over_10bp"] += 1
                            if max_diff > 0.01:
                                c["shape_over_1pct"] += 1
    data = {
        "scope": "Current 2026-11-02 code list intersected with accepted BaoStock supplier list; SH/SZ raw unadjusted quote and 200 valid-quote days only. Not qfq or live CN_ALL_A breadth.",
        "date_range": list(DATES), "raw_lookback_start": START,
        "main_index_sha256": hashlib.sha256(MAIN.read_bytes()).hexdigest(),
        "old_union_index_sha256": hashlib.sha256(OLD.read_bytes()).hexdigest(),
        "codes_sha256": hashlib.sha256(CODES.read_bytes()).hexdigest(),
        "current_code_counts": dict(Counter(c[:2] for c in current)),
        "current_codes_in_supplier_index": len(index_codes),
        "source_files_read": len(source_paths),
        "factor_source_files_read": len(factor_paths),
        "factor_errors": factor_errors[:30],
        "factor_error_count": len(factor_errors),
        "days": {day: {"total": dict(summary[day]), "markets": {m: dict(v) for m, v in by_market[day].items()}} for day in DATES},
        "candidate_breadth": {day: {**dict(breadth[day]),
            **{f"B{w}_pct": round(100 * breadth[day][f"above{w}"] / breadth[day][f"E{w}"], 6) if breadth[day][f"E{w}"] else None for w in (20, 50, 200)},
            "B50_on_E200_pct": round(100 * breadth[day]["above50_on_E200"] / breadth[day]["E200"], 6) if breadth[day]["E200"] else None,
            "E200_over_current_list_supplier_active": round(breadth[day]["E200"] / summary[day]["current_list_supplier_active"], 6),
        } for day in DATES},
        "qfq_comparison": {day: dict(comparisons[day]) for day in DATES},
        "qfq_comparison_exceptions_top20": sorted(comparison_examples, key=lambda x: x["max_relative_shape_difference"], reverse=True)[:20],
        "qfq_comparison_over_1bp_total": len(comparison_examples),
        "overlap_conflicts": len(exceptions), "first_overlap_conflicts": exceptions[:30],
        "limits": ["Offline BaoStock raw3 times effective foreAdjustFactor candidate; not Tencent qfqday or production breadth.", "No full adapt_back_adjusted price-identity/breakpoint acceptance run; overlapping raw conflict and qfq shape differences remain.", "Current list is not date-effective PIT membership.", "BSE not present in BaoStock source index."],
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"out": str(OUT), "source_files_read": len(source_paths), "overlap_conflicts": len(exceptions), "days": {d: dict(summary[d]) for d in DATES}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
