#!/usr/bin/env python3
"""Qualify saved historical membership and exact-date quote coverage, without return analysis."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

import pyarrow.parquet as pq


SPECIAL_TICKERS = ("SIVB", "SBNY", "TWTR", "STI")
MAIN_YEARS = tuple(range(2015, 2025))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def to_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def active_intervals(intervals: list[dict[str, Any]], at: date) -> list[dict[str, Any]]:
    """Return interval rows active at at using start-inclusive/end-exclusive rules."""
    return [r for r in intervals if r["start"] <= at and (r["end"] is None or at < r["end"])]


def ticker_set(rows: Iterable[dict[str, Any]]) -> set[str]:
    return {str(r["ticker"]) for r in rows}


def ticker_sha(tickers: Iterable[str]) -> str:
    payload = "\n".join(sorted(set(tickers))).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def rename_chain(ticker: str, renames: dict[str, str]) -> str:
    seen: set[str] = set()
    current = ticker
    while current in renames:
        if current in seen:
            raise ValueError(f"rename cycle detected from {ticker}: {sorted(seen)}")
        seen.add(current)
        current = renames[current]
    return current


def latest_snapshot_before(snapshots: list[tuple[date, set[str]]], at: date) -> tuple[date, set[str]]:
    eligible = [(d, s) for d, s in snapshots if d <= at]
    if not eligible:
        raise ValueError(f"no FJA snapshot on or before {at}")
    return max(eligible, key=lambda x: x[0])


def load_intervals(path: Path) -> list[dict[str, Any]]:
    table = pq.read_table(path, columns=["ticker", "start", "end"])
    rows = []
    for index, row in enumerate(table.to_pylist()):
        start, end = to_date(row["start"]), to_date(row["end"])
        if not row.get("ticker") or start is None:
            raise ValueError(f"invalid membership interval row {index}")
        if end is not None and end < start:
            raise ValueError(f"membership end precedes start for row {index}")
        rows.append({"interval_id": index, "ticker": str(row["ticker"]), "start": start, "end": end})
    return rows


def read_renames(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            old, new = (row.get("old") or "").strip(), (row.get("new") or "").strip()
            if not old or not new:
                continue
            if old in result and result[old] != new:
                raise ValueError(f"multiple rename targets for {old}")
            result[old] = new
    for key in result:
        rename_chain(key, result)
    return result


def read_fja(path: Path) -> list[tuple[date, set[str]]]:
    snapshots: list[tuple[date, set[str]]] = []
    seen: set[date] = set()
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not {"date", "tickers"}.issubset(reader.fieldnames or []):
            raise ValueError("FJA history must have date,tickers columns")
        for row in reader:
            d = to_date(row["date"])
            if d is None or d in seen:
                raise ValueError(f"invalid or duplicate FJA snapshot date: {row.get('date')}")
            seen.add(d)
            tickers = {x.strip() for x in (row.get("tickers") or "").split(",") if x.strip()}
            snapshots.append((d, tickers))
    snapshots.sort(key=lambda x: x[0])
    return snapshots


def load_no_trade(path: Path, relevant: set[tuple[str, date]]) -> dict[tuple[str, date], str]:
    found: dict[tuple[str, date], str] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not {"ticker", "date"}.issubset(reader.fieldnames or []):
            raise ValueError("no_trade_days.csv must have ticker,date columns")
        for row in reader:
            d = to_date(row.get("date"))
            key = (str(row.get("ticker", "")), d) if d is not None else None
            if key in relevant:
                found[key] = str(row.get("kind", ""))
    return found


def find_monthly_dates(price_path: Path, start: date, end: date, calendar_start: date) -> tuple[dict[str, date], Counter]:
    """Use observed SPY rows as a calendar proxy; do not infer exchange holidays."""
    pf = pq.ParquetFile(price_path)
    counts: Counter[date] = Counter()
    for batch in pf.iter_batches(columns=["date", "ticker"], batch_size=250_000):
        df = batch.to_pandas()
        selected = df.loc[df["ticker"] == "SPY", "date"]
        for value in selected:
            d = to_date(value)
            if d is not None and calendar_start <= d <= end:
                counts[d] += 1
    if not counts:
        raise ValueError("no SPY rows in requested interval")
    monthly: dict[str, date] = {}
    for d in sorted(d for d in counts if start <= d <= end):
        key = d.strftime("%Y-%m")
        monthly[key] = max(monthly.get(key, date.min), d)
    expected = [f"{y}-{m:02d}" for y in MAIN_YEARS for m in range(1, 13)]
    missing = [x for x in expected if x not in monthly]
    if missing:
        raise ValueError(f"SPY calendar missing months: {missing}")
    return {k: monthly[k] for k in expected}, counts


def annual_interval_reentry_counts(intervals: list[dict[str, Any]], year: int) -> tuple[int, int]:
    starts = 0
    reentries = 0
    by_ticker: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in intervals:
        by_ticker[row["ticker"]].append(row)
    for ticker_rows in by_ticker.values():
        ticker_rows.sort(key=lambda r: (r["start"], r["interval_id"]))
        for i, row in enumerate(ticker_rows):
            if row["start"].year == year:
                starts += 1
                if any(prev["end"] is not None and prev["end"] <= row["start"] for prev in ticker_rows[:i]):
                    reentries += 1
    return starts, reentries


def annual_membership_rows(intervals: list[dict[str, Any]], year: int) -> list[dict[str, Any]]:
    begin, finish = date(year, 1, 1), date(year + 1, 1, 1)
    return [r for r in intervals if (r["end"] is None or r["end"] > r["start"]) and r["start"] < finish and (r["end"] is None or r["end"] > begin)]


def missing_number(value: Any) -> bool:
    if value is None:
        return True
    try:
        return not math.isfinite(float(value))
    except (TypeError, ValueError):
        return True


def read_exit_gaps(path: Path) -> dict[tuple[str, date], dict[str, str]]:
    result = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            d = to_date(r.get("removed"))
            if d:
                result[(r.get("ticker", ""), d)] = r
    return result


def write_csv(path: Path, fields: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if v is None else v) for k, v in r.items()})


def run(job_path: Path, storage_path: Path) -> dict[str, Any]:
    job = json.loads(job_path.read_text(encoding="utf-8"))
    storage = json.loads(storage_path.read_text(encoding="utf-8"))
    input_hashes = {}
    input_paths = {}
    for b in job["input_files"]:
        p = Path(b["path"])
        actual = sha256_file(p)
        if actual != b["sha256"]:
            raise ValueError(f"input SHA mismatch: {p}; expected {b['sha256']}, got {actual}")
        input_hashes[p.name] = actual
        input_paths[p.name] = p

    output = Path(job["output"])
    if output.parent != Path(storage["output"]):
        raise ValueError("job output is not a child of bound storage output")
    if output.exists():
        raise FileExistsError(f"refusing existing output directory {output}")
    mount = Path(storage["external_mount"])
    if int(job["external_device"]) != int(storage["external_device"]):
        raise RuntimeError("job/storage external device bindings differ")
    if not mount.is_dir() or mount.stat().st_dev != int(job["external_device"]):
        raise RuntimeError("external device identity mismatch")
    if output.parent.stat().st_dev != int(job["external_device"]):
        raise RuntimeError("output parent is not on the bound external device")
    output.mkdir(parents=False, exist_ok=False)

    interval_path = input_paths["membership_intervals.parquet"]
    price_path = input_paths["prices.parquet"]
    fja_path = input_paths["fja-history.csv"]
    rename_path = input_paths["renames.csv"]
    gap_path = input_paths["exit_gaps.csv"]
    no_trade_path = input_paths["no_trade_days.csv"]
    start, end = to_date(job["main_start"]), to_date(job["main_end"])
    if start is None or end is None:
        raise ValueError("main_start/main_end required")
    intervals = load_intervals(interval_path)
    renames = read_renames(rename_path)
    snapshots = read_fja(fja_path)
    warmup_start = to_date(job["warmup_start"])
    if warmup_start is None:
        raise ValueError("warmup_start required")
    month_dates, spy_counts = find_monthly_dates(price_path, start, end, warmup_start)
    month_members: dict[str, list[dict[str, Any]]] = {}
    month_unique: dict[str, set[str]] = {}
    for month, quote_date in month_dates.items():
        active = active_intervals(intervals, quote_date)
        month_members[month] = active
        month_unique[month] = ticker_set(active)

    sample_dates = [to_date(x) for x in job["sample_dates"]]
    comparisons = [("monthly", month_dates[m], m, month_unique[m]) for m in month_dates]
    for d in sample_dates:
        if d is None:
            raise ValueError("invalid sample date")
        comparisons.append(("anchor", d, d.isoformat(), ticker_set(active_intervals(intervals, d))))

    comparison_rows: list[dict[str, Any]] = []
    comparison_summary: list[dict[str, Any]] = []
    for kind, at, label, member_set in comparisons:
        snap_date, fja_set = latest_snapshot_before(snapshots, at)
        raw_m_only, raw_f_only = member_set - fja_set, fja_set - member_set
        mapped_m: dict[str, set[str]] = defaultdict(set)
        mapped_f: dict[str, set[str]] = defaultdict(set)
        for t in member_set:
            mapped_m[rename_chain(t, renames)].add(t)
        for t in fja_set:
            mapped_f[rename_chain(t, renames)].add(t)
        mapped_m_set, mapped_f_set = set(mapped_m), set(mapped_f)
        for basis, left_only, right_only, left_map, right_map in (
            ("raw", raw_m_only, raw_f_only, {}, {}),
            ("after_renames", mapped_m_set - mapped_f_set, mapped_f_set - mapped_m_set, mapped_m, mapped_f),
        ):
            for ticker in sorted(left_only):
                originals = left_map.get(ticker, {ticker})
                comparison_rows.append({"comparison_type": kind, "comparison_date": label, "membership_quote_date": at.isoformat(), "fja_snapshot_date": snap_date.isoformat(), "basis": basis, "side": "membership_only", "ticker": ticker, "original_tickers": ",".join(sorted(originals))})
            for ticker in sorted(right_only):
                originals = right_map.get(ticker, {ticker})
                comparison_rows.append({"comparison_type": kind, "comparison_date": label, "membership_quote_date": at.isoformat(), "fja_snapshot_date": snap_date.isoformat(), "basis": basis, "side": "fja_only", "ticker": ticker, "original_tickers": ",".join(sorted(originals))})
        comparison_summary.append({
            "comparison_type": kind, "comparison_date": label, "membership_asof_date": at.isoformat(), "fja_snapshot_date": snap_date.isoformat(),
            "membership_count": len(member_set), "membership_sha256": ticker_sha(member_set),
            "fja_count": len(fja_set), "fja_sha256": ticker_sha(fja_set),
            "raw_common": len(member_set & fja_set), "raw_membership_only": len(raw_m_only), "raw_fja_only": len(raw_f_only),
            "mapped_membership_count": len(mapped_m_set), "mapped_fja_count": len(mapped_f_set),
            "mapped_common": len(mapped_m_set & mapped_f_set), "mapped_membership_only": len(mapped_m_set - mapped_f_set), "mapped_fja_only": len(mapped_f_set - mapped_m_set),
            "membership_rename_collisions": sum(len(v) > 1 for v in mapped_m.values()), "fja_rename_collisions": sum(len(v) > 1 for v in mapped_f.values()),
        })

    # Build quote-date key set, then stream only needed price columns and rows.
    price_keys = {(ticker, d) for d, members in ((month_dates[m], month_unique[m]) for m in month_dates) for ticker in members}
    special_intervals = [r for r in intervals if r["ticker"] in SPECIAL_TICKERS and r["end"] is not None]
    selected_tickers = {ticker for ticker, _ in price_keys} | set(SPECIAL_TICKERS)
    no_trade = load_no_trade(no_trade_path, price_keys)
    price_rows: dict[tuple[str, date], list[dict[str, Any]]] = defaultdict(list)
    event_price_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    pf = pq.ParquetFile(price_path)
    cols = ["date", "ticker", "close", "volume", "adj_close", "source"]
    for batch in pf.iter_batches(columns=cols, batch_size=250_000):
        df = batch.to_pandas()
        mask = df["ticker"].isin(selected_tickers)
        if not mask.any():
            continue
        for r in df.loc[mask, cols].itertuples(index=False, name=None):
            d = to_date(r[0]); ticker = str(r[1])
            if d is None:
                continue
            rec = {"date": d, "ticker": ticker, "close": r[2], "volume": r[3], "adj_close": r[4], "source": r[5]}
            key = (ticker, d)
            if key in price_keys:
                price_rows[key].append(rec)
            if ticker in SPECIAL_TICKERS:
                event_price_rows[ticker].append(rec)

    membership_price_rows: list[dict[str, Any]] = []
    price_counts: Counter[str] = Counter()
    for month, quote_date in month_dates.items():
        for ticker in sorted(month_unique[month]):
            key = (ticker, quote_date)
            quotes = price_rows.get(key, [])
            no_trade_kind = no_trade.get(key, "")
            if no_trade_kind:
                price_counts["no_trade_day_listed"] += 1
                price_counts[f"no_trade_kind:{no_trade_kind}"] += 1
            if not quotes:
                state = "missing_price_row"
                price_counts["missing_price_row"] += 1
                q = None
            else:
                if len(quotes) > 1:
                    state = "duplicate_price_rows"
                    price_counts["duplicate_price_keys"] += 1
                    price_counts["duplicate_price_extra_rows"] += len(quotes) - 1
                q = quotes[0]
                for label, value in (("close", q["close"]), ("adj_close", q["adj_close"])):
                    if missing_number(value):
                        price_counts[f"{label}_missing"] += 1
                    elif value < 0:
                        price_counts[f"{label}_negative"] += 1
                    elif value == 0:
                        price_counts[f"{label}_zero"] += 1
                    else:
                        price_counts[f"{label}_positive"] += 1
                volume = q["volume"]
                if missing_number(volume):
                    price_counts["volume_missing"] += 1
                elif volume < 0:
                    price_counts["volume_negative"] += 1
                elif volume == 0:
                    price_counts["volume_zero"] += 1
                else:
                    price_counts["volume_positive"] += 1
                if no_trade_kind:
                    state = "listed_in_no_trade_days"
                elif len(quotes) == 1 and not missing_number(q["close"]) and q["close"] > 0 and not missing_number(q["adj_close"]) and q["adj_close"] > 0 and not missing_number(q["volume"]) and q["volume"] > 0 and q["source"] and str(q["source"]).strip():
                    state = "positive_exact_quote"
                    price_counts["positive_exact_quote"] += 1
                elif len(quotes) == 1:
                    state = "quote_present_but_not_qualified"
                    price_counts["quote_present_but_not_qualified"] += 1
            membership_price_rows.append({
                "month": month, "quote_date": quote_date.isoformat(), "ticker": ticker,
                "active_interval_count": sum(1 for x in month_members[month] if x["ticker"] == ticker),
                "price_row_count": len(quotes), "price_status": state,
                "close": None if q is None else q["close"], "adj_close": None if q is None else q["adj_close"],
                "volume": None if q is None else q["volume"], "source": None if q is None else q["source"],
                "no_trade_days_kind": no_trade_kind,
            })

    annual_rows = []
    for year in MAIN_YEARS:
        year_intervals = annual_membership_rows(intervals, year)
        starts, reentries = annual_interval_reentry_counts(intervals, year)
        year_months = [f"{year}-{m:02d}" for m in range(1, 13)]
        union_month_members = set().union(*(month_unique[m] for m in year_months))
        unique_any = ticker_set(year_intervals)
        end_members = month_unique[f"{year}-12"]
        end_events = [r for r in intervals if r["end"] is not None and r["end"].year == year]
        per_ticker = Counter(r["ticker"] for r in year_intervals)
        overlapping_pairs = 0
        by_ticker: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in year_intervals: by_ticker[r["ticker"]].append(r)
        for items in by_ticker.values():
            for i, left in enumerate(items):
                for right in items[i+1:]:
                    left_end = left["end"] or date.max
                    right_end = right["end"] or date.max
                    if left["start"] < right_end and right["start"] < left_end:
                        overlapping_pairs += 1
        annual_rows.append({
            "year": year, "unique_tickers_any_interval_overlap": len(unique_any),
            "unique_tickers_seen_at_month_end": len(union_month_members), "year_end_month_end_tickers": len(end_members),
            "interval_rows_overlapping_year": len(year_intervals), "interval_starts_in_year": starts,
            "interval_ends_in_year": len(end_events), "reentries_in_year": reentries,
            "tickers_with_multiple_interval_rows_overlapping_year": sum(v > 1 for v in per_ticker.values()),
            "overlapping_interval_pairs_in_year": overlapping_pairs,
        })

    exits = []
    exit_gap_map = read_exit_gaps(gap_path)
    for row in intervals:
        if row["end"] is None or not (start <= row["end"] <= end):
            continue
        prior_spy = [d for d, count in spy_counts.items() if d < row["end"] and count > 0]
        gap = exit_gap_map.get((row["ticker"], row["end"]), {})
        exits.append({
            "ticker": row["ticker"], "interval_id": row["interval_id"], "interval_start": row["start"].isoformat(),
            "interval_end_exclusive": row["end"].isoformat(), "last_spy_quote_date_before_end": max(prior_spy).isoformat() if prior_spy else "",
            "event_type": "index_membership_interval_end", "security_exit_confirmed": False,
            "matching_exit_gap_removed_date": gap.get("removed", ""), "last_trade": gap.get("last_trade", ""),
            "next_trade": gap.get("next_trade", ""), "gap_days": gap.get("gap_days", ""),
        })

    event_rows = []
    for ticker in SPECIAL_TICKERS:
        rows = sorted(event_price_rows.get(ticker, []), key=lambda x: x["date"])
        ticker_exits = [r for r in intervals if r["ticker"] == ticker and r["end"] is not None and start <= r["end"] <= end]
        for ev in ticker_exits:
            before = [r for r in rows if r["date"] < ev["end"]][-5:]
            after = [r for r in rows if r["date"] >= ev["end"]][:5]
            for phase, arr in (("before", before), ("on_or_after_end", after)):
                for r in arr:
                    event_rows.append({"ticker": ticker,"interval_id":ev["interval_id"],"interval_end_exclusive":ev["end"].isoformat(),"window":phase,"date":r["date"].isoformat(),"close":r["close"],"source":r["source"],"volume":r["volume"],"adj_close":r["adj_close"]})
        if not ticker_exits:
            event_rows.append({"ticker":ticker,"interval_id":"","interval_end_exclusive":"","window":"no_matching_exit_event","date":"","close":"","source":"","volume":"","adj_close":""})

    monthly_interval_rows = []
    for month, quote_date in month_dates.items():
        for r in month_members[month]:
            monthly_interval_rows.append({"month":month,"quote_date":quote_date.isoformat(),"ticker":r["ticker"],"interval_id":r["interval_id"],"interval_start":r["start"].isoformat(),"interval_end_exclusive":"" if r["end"] is None else r["end"].isoformat()})

    write_csv(output / "monthly-members.csv", ["month","quote_date","ticker","interval_id","interval_start","interval_end_exclusive"], monthly_interval_rows)
    write_csv(output / "monthly-price-qualification.csv", ["month","quote_date","ticker","active_interval_count","price_row_count","price_status","close","adj_close","volume","source","no_trade_days_kind"], membership_price_rows)
    write_csv(output / "annual-membership-summary.csv", list(annual_rows[0]), annual_rows)
    write_csv(output / "exit-events.csv", ["ticker","interval_id","interval_start","interval_end_exclusive","last_spy_quote_date_before_end","event_type","security_exit_confirmed","matching_exit_gap_removed_date","last_trade","next_trade","gap_days"], exits)
    write_csv(output / "fja-membership-differences.csv", ["comparison_type","comparison_date","membership_quote_date","fja_snapshot_date","basis","side","ticker","original_tickers"], comparison_rows)
    write_csv(output / "special-exit-price-windows.csv", ["ticker","interval_id","interval_end_exclusive","window","date","close","source","volume","adj_close"], event_rows)

    anchor_summary = [r for r in comparison_summary if r["comparison_type"] == "anchor"]
    monthly_comparison = [r for r in comparison_summary if r["comparison_type"] == "monthly"]
    summary = {
        "schema":"us-op-membership-qualification/1", "status":"complete_source_qualification_only",
        "period":{"start":start.isoformat(),"end":end.isoformat(),"monthly_periods":len(month_dates),"warmup_start":job["warmup_start"]},
        "input_sha256":input_hashes, "membership_interval_rows":len(intervals), "fja_snapshot_rows":len(snapshots), "rename_edges":len(renames),
        "monthly_member_interval_rows":len(monthly_interval_rows),"unique_month_ticker_quote_keys":len(membership_price_rows),
        "price_quality_counts":dict(price_counts),"exit_event_rows":len(exits),"special_exit_price_rows":len(event_rows),
        "fja_comparisons":{"monthly_count":len(monthly_comparison),"anchor_points":anchor_summary,"monthly_raw_differences":sum(r["raw_membership_only"]+r["raw_fja_only"] for r in monthly_comparison),"monthly_mapped_differences":sum(r["mapped_membership_only"]+r["mapped_fja_only"] for r in monthly_comparison)},
        "annual":annual_rows,
        "limitations":["FJA and interval lists are not independent sources; rename mapping is only a comparison aid and does not confirm security identity.","Membership interval ends are index-membership events; underlying security exits are not confirmed.","SPY observed quotes are used as a trading-date proxy; quote checks use exact daily rows only.","No returns, momentum, ranking, or strategy effectiveness were calculated."],
    }
    (output/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return {"output":str(output),"summary":summary}


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--job",required=True,type=Path)
    ap.add_argument("--storage-plan",required=True,type=Path)
    args=ap.parse_args()
    result=run(args.job,args.storage_plan)
    print(json.dumps({"status":"complete","output":result["output"],"months":result["summary"]["period"]["monthly_periods"],"interval_rows":result["summary"]["membership_interval_rows"],"price_keys":result["summary"]["unique_month_ticker_quote_keys"]},ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
