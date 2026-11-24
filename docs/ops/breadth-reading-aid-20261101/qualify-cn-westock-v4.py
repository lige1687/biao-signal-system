"""Read-only independent qualification of the saved WeStock CN qfq candidate.

Only reads the producer's SHA-bound candidate and saved official listing tables.
Writes a small sibling JSON; never changes the producer or live caches.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
from bisect import bisect_right
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / ".codex/breadth-reading-coordination-20261101"
SOURCE = BASE / "cn-westock-candidate-v4"
LISTING = BASE / "cn-repair-candidate-20261102/listing-evidence"
LIVE = Path("/Users/yongbiaoli/.lei_signal_lab/cache/a_share_ma_breadth_history.json")
CALENDAR = Path("/Volumes/win+mac通用/LeiSignal-新实验结果/downside-sensitivity-universe-20261023-history-20261024/downside-sensitivity-universe-20261023-history-20261024-20261024T093252-9b5d45a6ea04/result/controller-cn-parent/H00300_combined_2006_20261023_trading_days.csv")
RECENT_CALENDAR = ROOT / "docs/ops/breadth-reading-aid-20261101/price-axis-v2.json"
BAO_MAIN = Path("/Volumes/win+mac通用/LeiSignal-新实验结果/public-universe-deep-completion-20261026/public-universe-deep-completion-20261026-20261026T225421-69a3af262800/result/cn-all-equity/all-equity-read-index-v8.jsonl")
BAO_OLD = Path("/Volumes/win+mac通用/LeiSignal-新实验结果/twenty-year-universe-data-20261025/twenty-year-universe-data-20261025-20261025T154847-f27d39c4e083/result/cn/stock-source-union-v4/actual-date-unions.jsonl")
OUTPUT = Path(__file__).with_suffix(".json")
DATES = ("2026-08-19", "2026-09-09", "2026-09-22", "2026-09-23",
         "2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22",
         "2026-10-23", "2026-10-26", "2026-10-27", "2026-10-28",
         "2026-10-29", "2026-10-30")
WINDOWS = (20, 50, 200)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def listings() -> tuple[dict[str, str], dict[str, str]]:
    result = {}
    fingerprints = {}
    for name, prefix, code_key, date_key in (
        ("sh_main", "sh", "证券代码", "上市日期"),
        ("sh_star", "sh", "证券代码", "上市日期"),
        ("sz", "sz", "A股代码", "A股上市日期"),
        ("bj", "bj", "证券代码", "上市日期"),
    ):
        path = LISTING / f"{name}-normalized.csv"
        fingerprints[name] = sha(path)
        with path.open(newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                symbol = prefix + row[code_key].zfill(6)
                if symbol in result:
                    raise ValueError(f"duplicate official code: {symbol}")
                result[symbol] = row[date_key]
    return result, fingerprints


def classify(row: dict, listing_date: str) -> str:
    date = row["date"]
    if date < listing_date:
        return "before_official_ipo"
    if date > DATES[-1]:
        return "after_cutoff"
    n = row["numeric"]
    if any(not math.isfinite(float(n[k])) or float(n[k]) <= 0 for k in ("open", "last", "high", "low")):
        return "nonpositive_or_nonfinite_ohlc"
    if any(not math.isfinite(float(n[k])) or float(n[k]) <= 0 for k in ("volume", "amount")):
        return "zero_or_nonfinite_volume_amount"
    if not float(n["low"]) <= min(float(n["open"]), float(n["last"])) or not float(n["high"]) >= max(float(n["open"]), float(n["last"])):
        return "invalid_ohlc_order"
    return "valid_quote"


def baostock_crosscheck(missing_by_day: dict) -> dict:
    """Read only registered BaoStock raw sources for WeStock-missing SH/SZ dates <=10-23."""
    wanted = {s for day in DATES[:9] for s in missing_by_day[day].get("no_provider_row", [])}
    out = {day: {} for day in DATES[:9]}
    old = {}
    with BAO_OLD.open() as f:
        for line in f:
            x = json.loads(line)
            if x["code"].replace(".", "") in wanted:
                old[x["code"]] = x
    source_files = set()
    index_matched = set()
    with BAO_MAIN.open() as f:
        for line in f:
            x = json.loads(line)
            dotted = x["code"]
            symbol = dotted.replace(".", "")
            if symbol not in wanted:
                continue
            index_matched.add(symbol)
            target_days = {day for day in DATES[:9] if symbol in missing_by_day[day].get("no_provider_row", [])}
            refs = list(x.get("new_price_sources") or []) + list(x.get("reused_raw_sources") or [])
            if x.get("old_union_lookup"):
                refs += old.get(dotted, {}).get("source_refs", [])
            source_rows = defaultdict(list)
            for ref in refs:
                path = str(ref.get("source_path") or ref.get("path"))
                if not path or path == "None":
                    continue
                source_files.add(path)
                opener = gzip.open if path.endswith(".gz") else open
                with opener(path, "rt", encoding="utf-8") as raw:
                    obj = json.load(raw)
                fields = obj.get("fields") or []
                for record in obj.get("data", []):
                    row = dict(zip(fields, record))
                    if row.get("date") in target_days:
                        source_rows[row["date"]].append({
                            "tradestatus": row.get("tradestatus"),
                            "close": row.get("close"),
                            "volume": row.get("volume"),
                            "amount": row.get("amount"),
                        })
            for day in target_days:
                matches = source_rows[day]
                distinct = list({json.dumps(r, sort_keys=True): r for r in matches}.values())
                out[day][symbol] = {
                    "raw_rows_found": len(matches),
                    "distinct_raw_rows": distinct,
                    "status": "source_row_absent" if not matches else "source_conflict" if len(distinct) > 1 else "observed_tradestatus_0" if distinct[0]["tradestatus"] == "0" else "observed_other_status",
                }
    return {
        "registered_index_sha256": sha(BAO_MAIN),
        "registered_old_union_sha256": sha(BAO_OLD),
        "index_matched_symbols": sorted(index_matched),
        "raw_source_file_count": len(source_files),
        "by_day": out,
    }


def main() -> None:
    manifest_path = SOURCE / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if manifest["planned_batches"] != 279 or manifest["completed_batches"] != 279:
        raise RuntimeError("producer incomplete; wait for all 279 batches")
    combined = SOURCE / manifest["combined_jsonl_gzip"]
    if sha(combined) != manifest["combined_gzip_sha256"]:
        raise RuntimeError("combined candidate SHA mismatch")
    code_path = Path(manifest["source_codes"])
    if sha(code_path) != manifest["source_codes_sha256"]:
        raise RuntimeError("current code list changed")
    codes = json.loads(code_path.read_text())["codes"]
    if len(codes) != 5577 or len(set(codes)) != len(codes):
        raise RuntimeError("current code list count/uniqueness mismatch")
    listed, listing_sha = listings()
    if set(listed) != set(codes):
        raise RuntimeError(f"official current list mismatch: {len(set(codes)-set(listed))} missing")
    receipts = [json.loads(p.read_text()) for p in sorted(SOURCE.glob("batch-???.receipt.json"))]
    if len(receipts) != 279:
        raise RuntimeError("receipt count mismatch")
    requested = {}
    parse_rejections = Counter()
    receipt_missing_symbols = set()
    for rec in receipts:
        if rec["codes_sha256"] != manifest["source_codes_sha256"]:
            raise RuntimeError("batch source identity drift")
        for symbol in rec["symbols"]:
            if symbol in requested:
                raise RuntimeError("duplicate batch symbol")
            requested[symbol] = rec["result"]
        parse_rejections.update(rec.get("parse_rejections") or {})
        receipt_missing_symbols.update(rec.get("missing_symbols") or [])
    if set(requested) != set(codes):
        raise RuntimeError("batch requested codes mismatch")
    live = {r["date"]: r for r in json.loads(LIVE.read_text())}
    with CALENDAR.open(newline="") as f:
        calendar = {row["trade_date"] for row in csv.DictReader(f)}
    calendar.update(json.loads(RECENT_CALENDAR.read_text())["dates"])
    calendar = sorted(d for d in calendar if d <= DATES[-1])
    recent_live_dates = sorted(x for x in live if x <= "2026-10-16")[-20:]
    all_dates = sorted(set(DATES) | set(recent_live_dates))
    stats = {d: {m: Counter() for m in ("sh", "sz", "bj", "all")} for d in all_dates}
    unresolved = {d: defaultdict(list) for d in DATES}
    value_diffs = {d: {} for d in recent_live_dates}
    class_counts = Counter()
    unexpected = []
    current_symbol = None
    current_rows = []
    seen_symbols = set()
    seen_pairs = set()
    parsed_rows = 0

    def count(day: str, market: str, key: str, value: int = 1) -> None:
        stats[day][market][key] += value
        stats[day]["all"][key] += value

    def finish(symbol: str, rows: list[dict]) -> None:
        market = symbol[:2]
        ipo = listed[symbol]
        usable = {}
        provider_dates = set()
        for row in rows:
            day = row["date"]
            provider_dates.add(day)
            reason = classify(row, ipo)
            class_counts[reason] += 1
            if bool(row.get("candidate_valid")) != (reason == "valid_quote") and not (reason == "before_official_ipo" and bool(row.get("candidate_valid"))):
                unexpected.append({"symbol": symbol, "date": day, "reason": "producer_reclassification_disagrees"})
            if reason == "valid_quote" and requested[symbol] == "success":
                usable[day] = Decimal(str(row["numeric"]["last"]))
        ordered = sorted(usable)
        prices = [usable[d] for d in ordered]
        for day in all_dates:
            if ipo > day:
                count(day, market, "not_yet_listed_current_code")
                continue
            count(day, market, "listed_current_code")
            if requested[symbol] == "success":
                count(day, market, "requested_success")
            else:
                count(day, market, "request_failed")
            if day not in provider_dates:
                count(day, market, "no_provider_row")
                if day in unresolved:
                    unresolved[day]["no_provider_row"].append(symbol)
                continue
            row = next(x for x in rows if x["date"] == day)
            reason = classify(row, ipo)
            if requested[symbol] != "success":
                count(day, market, "unqualified_failed_batch_row")
                if day in unresolved:
                    unresolved[day]["unqualified_failed_batch_row"].append(symbol)
                continue
            if reason != "valid_quote":
                count(day, market, reason)
                if day in unresolved:
                    unresolved[day][reason].append(symbol)
                continue
            count(day, market, "same_day_valid_quote")
            pos = bisect_right(ordered, day)
            for n in WINDOWS:
                if pos < n:
                    theoretical_sessions = bisect_right(calendar, day) - bisect_right(calendar, ipo) + (1 if ipo in calendar else 0)
                    if ipo < calendar[0]:
                        theoretical_sessions = n  # older listing is certainly warm
                    reason = f"ipo_warmup_under_{n}" if theoretical_sessions < n else f"history_short_or_nontrade_under_{n}"
                    count(day, market, reason)
                    if day in unresolved:
                        unresolved[day][reason].append(symbol)
                    continue
                count(day, market, f"E{n}")
                if prices[pos - 1] * n > sum(prices[pos - n:pos], Decimal(0)):
                    count(day, market, f"above{n}")
        # Results for historical live dates are compared only after aggregation.

    with gzip.open(combined, "rt", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            parsed_rows += 1
            symbol = row["symbol"]
            pair = (symbol, row["date"])
            if symbol not in requested or pair in seen_pairs:
                raise RuntimeError(f"unknown or duplicate provider row: {pair}")
            seen_pairs.add(pair)
            if current_symbol is None:
                current_symbol = symbol
            if symbol != current_symbol:
                if symbol in seen_symbols:
                    raise RuntimeError("non-contiguous symbol rows")
                finish(current_symbol, current_rows)
                seen_symbols.add(current_symbol)
                current_symbol, current_rows = symbol, []
            current_rows.append(row)
    if current_symbol is not None:
        finish(current_symbol, current_rows)
        seen_symbols.add(current_symbol)
    for symbol in codes:
        if symbol not in seen_symbols:
            finish(symbol, [])
    if parsed_rows != manifest["parsed_rows"]:
        raise RuntimeError("parsed row count differs from producer manifest")

    day_result = {}
    for day in all_dates:
        by_market = {m: dict(stats[day][m]) for m in ("sh", "sz", "bj", "all")}
        for m, counter in stats[day].items():
            for n in WINDOWS:
                e = counter[f"E{n}"]
                by_market[m][f"B{n}_pct"] = round(100 * counter[f"above{n}"] / e, 6) if e else None
                by_market[m][f"coverage_E{n}_over_listed_current"] = round(e / counter["listed_current_code"], 6) if counter["listed_current_code"] else None
        day_result[day] = by_market
        if day in recent_live_dates:
            value_diffs[day] = {f"ma{n}": {
                "live": live[day].get(f"ma{n}_pct"),
                "candidate_all": by_market["all"].get(f"B{n}_pct"),
                "difference_pp": round(by_market["all"][f"B{n}_pct"] - live[day][f"ma{n}_pct"], 6) if by_market["all"][f"B{n}_pct"] is not None and live[day].get(f"ma{n}_pct") is not None else None,
            } for n in WINDOWS}

    output = {
        "schema": "qualify-cn-westock-v4/1",
        "producer_manifest_sha256": sha(manifest_path),
        "producer_combined_sha256": manifest["combined_gzip_sha256"],
        "current_codes_sha256": manifest["source_codes_sha256"],
        "official_listing_csv_sha256": listing_sha,
        "calendar_sha256": sha(CALENDAR),
        "recent_calendar_sha256": sha(RECENT_CALENDAR),
        "live_history_sha256": sha(LIVE),
        "request": manifest["request"],
        "batches": {"planned": manifest["planned_batches"], "successful": manifest["successful_batches"], "failed": manifest["failed_batches"]},
        "current_code_count": len(codes),
        "current_codes_by_market": dict(Counter(x[:2] for x in codes)),
        "parsed_rows": parsed_rows,
        "producer_parse_rejections": dict(parse_rejections),
        "receipt_missing_symbols": sorted(receipt_missing_symbols),
        "row_classification": dict(class_counts),
        "producer_vs_independent_mismatches": unexpected[:100],
        "producer_vs_independent_mismatch_count": len(unexpected),
        "target_dates": list(DATES),
        "live_comparison_dates": recent_live_dates,
        "days": day_result,
        "unresolved_symbols_by_day": {d: dict(v) for d, v in unresolved.items()},
        "target_no_provider_row_unique_symbols": sorted({s for d in DATES for s in unresolved[d].get("no_provider_row", [])}),
        "target_history_short_or_nontrade_unique_symbols_by_window": {
            str(n): sorted({s for d in DATES for s in unresolved[d].get(f"history_short_or_nontrade_under_{n}", [])})
            for n in WINDOWS
        },
        "baostock_crosscheck_for_westock_missing_through_2026_10_23": baostock_crosscheck(unresolved),
        "recent_live_read_only_comparison": value_diffs,
        "limits": [
            "Current 2026-11-02 official list with IPO dates; not historical PIT membership.",
            "Single WeStock qfq source only; no cross-provider price splicing.",
            "No invented rows for missing/provider nontrade dates.",
            "200 observed valid history within 300 returned rows may omit older required history; classify short separately.",
            "Production strict-all qualification status and live cache are unchanged.",
        ],
    }
    encoded = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    if len(encoded.encode()) > 5_000_000:
        raise RuntimeError("qualification result exceeds 5MB cap")
    OUTPUT.write_text(encoded)
    print(json.dumps({"output": str(OUTPUT), "rows": parsed_rows, "batches": output["batches"], "targets": {d: day_result[d]["all"] for d in DATES}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
