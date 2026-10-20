#!/usr/bin/env python3
"""Compare matched daily adjusted-close changes in two already-saved sources."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq


RAW = Path(__file__).resolve().parent
CONTRACT = RAW / "luna-price-source-contract.json"
OLD_RESULT = Path("/Volumes/win+mac通用/LeiSignal-新实验结果/stock-universe-us-20261015/stock-universe-us-20261015-20261015T194201-82eb0af53148/result")
NEW_PRICES = Path("/Volumes/win+mac通用/LeiSignal-新实验结果/us-op-common-history-20261020/us-op-common-history-20261020-20261020T191922-92db83e55b32/result/sources/prices.parquet")
OUT = Path("/Volumes/win+mac通用/LeiSignal-新实验结果/us-op-common-history-20261020/us-op-common-history-20261020-20261020T191922-92db83e55b32/result/price-source-comparison")
START, END = "2020-01-01", "2024-12-31"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def day_changes(observations):
    """Return date -> prior-date, percentage change for positive finite levels."""
    clean = []
    rejected = []
    seen = set()
    for date, value in observations:
        if date in seen:
            rejected.append((date, "duplicate_date"))
            continue
        seen.add(date)
        if value is None or not math.isfinite(float(value)) or float(value) <= 0:
            rejected.append((date, "nonfinite_or_nonpositive_adj_close"))
            continue
        clean.append((date, float(value)))
    clean.sort(key=lambda x: x[0])
    result = {}
    for (prior_date, prior), (date, value) in zip(clean, clean[1:]):
        result[date] = (prior_date, value / prior - 1.0)
    return result, rejected


def synthetic_check():
    old = [("2024-01-02", 100), ("2024-01-03", 105), ("2024-01-04", 110)]
    constant_scaled = [(d, v * 7.3) for d, v in old]
    a, _ = day_changes(old)
    b, _ = day_changes(constant_scaled)
    common = {d for d in a.keys() & b.keys() if a[d][0] == b[d][0]}
    assert common == {"2024-01-03", "2024-01-04"}
    assert max(abs(a[d][1] - b[d][1]) for d in common) < 1e-12
    missing_day = [("2024-01-02", 100), ("2024-01-04", 110)]
    c, _ = day_changes(missing_day)
    common_missing = {d for d in a.keys() & c.keys() if a[d][0] == c[d][0]}
    assert common_missing == set()
    return {"status": "passed", "constant_level_scale_diff_max": max(abs(a[d][1] - b[d][1]) for d in common), "missing_day_comparable_count": len(common_missing)}


def load_old():
    attempts_path = OLD_RESULT / "attempts.jsonl"
    verification_path = OLD_RESULT / "verification.json"
    contract = json.loads(CONTRACT.read_text())
    bindings = contract["input_binding"]
    assert sha256(attempts_path) == bindings["old_attempts_sha256"]
    assert sha256(verification_path) == bindings["old_verification_sha256"]
    entries = [json.loads(line) for line in attempts_path.read_text().splitlines() if line.strip()]
    old = {}
    no_period_data = []
    checked = []
    for entry in entries:
        if entry.get("status") != "ok" or not entry.get("file"):
            continue
        ticker = entry.get("code")
        if entry.get("returned_symbol") != ticker:
            continue
        path = OLD_RESULT / entry["file"]
        actual = sha256(path)
        if actual != entry.get("sha256"):
            raise ValueError(f"old original SHA mismatch: {entry['file']}")
        checked.append({"file": entry["file"], "sha256": actual})
        payload = json.loads(path.read_text())
        result = (payload.get("chart", {}).get("result") or [None])[0]
        if not result or not ticker:
            continue
        times = result.get("timestamp") or []
        values = result.get("indicators", {}).get("adjclose", [{}])[0].get("adjclose") or []
        if len(times) != len(values):
            raise ValueError(f"old timestamp/adj_close length mismatch: {entry['file']}")
        obs = []
        for ts, value in zip(times, values):
            date = datetime.fromtimestamp(ts, timezone.utc).date().isoformat()
            if START <= date <= END:
                obs.append((date, value))
        if obs:
            old[ticker] = obs
        else:
            no_period_data.append(ticker)
    if len(checked) != 502:
        raise ValueError(f"expected 502 successful old originals with verified SHA, found {len(checked)}")
    return old, checked, sorted(no_period_data)


def load_new():
    contract = json.loads(CONTRACT.read_text())
    if sha256(NEW_PRICES) != contract["input_binding"]["new_prices_sha256"]:
        raise ValueError("new prices parquet SHA mismatch")
    table = pq.read_table(NEW_PRICES, columns=["date", "ticker", "adj_close", "source"])
    groups = defaultdict(list)
    bad = defaultdict(list)
    for date, ticker, value, source in zip(*(table[c].to_pylist() for c in ["date", "ticker", "adj_close", "source"])):
        if ticker is None:
            continue
        if isinstance(date, datetime):
            date = date.date().isoformat()
        elif hasattr(date, "isoformat"):
            date = date.isoformat()
        else:
            date = str(date)[:10]
        if not START <= date <= END:
            continue
        groups[(str(ticker), str(source))].append((date, value))
    return groups


def summarize(values):
    vals = sorted(abs(x) for x in values)
    if not vals:
        return {"n": 0, "median_abs_diff": None, "p90_abs_diff": None, "p99_abs_diff": None, "max_abs_diff": None, "threshold_counts": {}}
    def quantile(p):
        pos = (len(vals) - 1) * p
        lo, hi = math.floor(pos), math.ceil(pos)
        return vals[lo] if lo == hi else vals[lo] * (hi - pos) + vals[hi] * (pos - lo)
    return {"n": len(vals), "median_abs_diff": quantile(.5), "p90_abs_diff": quantile(.9), "p99_abs_diff": quantile(.99), "max_abs_diff": vals[-1], "threshold_counts": {str(t): sum(v > t for v in vals) for t in [1e-5, 1e-4, 1e-3, 1e-2]}}


def main():
    synthetic = synthetic_check()
    old, old_files, old_without_period_data = load_old()
    new_groups = load_new()
    OUT.mkdir(parents=True, exist_ok=True)
    all_diffs = []
    invalid = {"old": [], "new": []}
    old_series = {ticker: day_changes(obs) for ticker, obs in old.items()}
    new_series = {}
    for (ticker, source), obs in new_groups.items():
        key = (ticker, source)
        new_series[key] = day_changes(obs)
    matched_symbols = set(old) & {ticker for ticker, _ in new_groups}
    unmatched_old = sorted(set(old) - {ticker for ticker, _ in new_groups})
    unmatched_new = sorted({ticker for ticker, _ in new_groups} - set(old))
    for ticker in sorted(matched_symbols):
        old_changes, old_bad = old_series[ticker]
        old_values = dict(old[ticker])
        invalid["old"].extend({"ticker": ticker, "date": d, "reason": reason} for d, reason in old_bad)
        for (new_ticker, source), (new_changes, new_bad) in new_series.items():
            if new_ticker != ticker:
                continue
            invalid["new"].extend({"ticker": ticker, "source": source, "date": d, "reason": reason} for d, reason in new_bad)
            for date in old_changes.keys() & new_changes.keys():
                old_prev, old_ret = old_changes[date]
                new_prev, new_ret = new_changes[date]
                if old_prev != new_prev:
                    continue
                new_values = dict(new_groups[(ticker, source)])
                all_diffs.append({"date": date, "ticker": ticker, "source": source, "old_adj_close": old_values[date], "new_adj_close": new_values[date], "old_previous_date": old_prev, "new_previous_date": new_prev, "old_daily_change": old_ret, "new_daily_change": new_ret, "absolute_change_difference": abs(old_ret-new_ret)})
    with (OUT / "differences-over-1pp.csv").open("x", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_diffs[0].keys()) if all_diffs else ["date", "ticker", "source", "old_adj_close", "new_adj_close", "old_previous_date", "new_previous_date", "old_daily_change", "new_daily_change", "absolute_change_difference"])
        writer.writeheader()
        writer.writerows(x for x in all_diffs if x["absolute_change_difference"] > .01)
    by_source = defaultdict(list)
    by_ticker = defaultdict(list)
    for row in all_diffs:
        by_source[row["source"]].append(row["absolute_change_difference"])
        by_ticker[row["ticker"]].append(row["absolute_change_difference"])
    summary = {"period": {"start": START, "end": END}, "old_verified_nonempty_originals": len(old_files), "old_symbols_with_data_in_period": len(old), "old_symbols_without_data_in_period": old_without_period_data, "matched_symbols": len(matched_symbols), "unmatched_old_symbols": unmatched_old, "unmatched_new_symbols": unmatched_new, "matched_daily_change_pairs": len(all_diffs), "source_groups": {source: summarize(vals) for source, vals in sorted(by_source.items())}, "all_sources": summarize([x["absolute_change_difference"] for x in all_diffs]), "per_ticker": {ticker: summarize(vals) for ticker, vals in sorted(by_ticker.items())}, "invalid_observations": invalid, "differences_over_1pp_count": sum(x["absolute_change_difference"] > .01 for x in all_diffs), "source_dependence_note": "New source labels are retained. A source label may identify Yahoo-derived observations; this comparison does not treat all labels as independent providers.", "scope_note": "Price-data quality comparison only. No factor or strategy performance was calculated. Matched dates require identical ticker and identical prior observed date in each series.", "synthetic_validation": synthetic}
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n")
    manifest = {"old_attempts_sha256": sha256(OLD_RESULT/"attempts.jsonl"), "old_verification_sha256": sha256(OLD_RESULT/"verification.json"), "new_prices_sha256": sha256(NEW_PRICES), "old_original_count_sha_verified": len(old_files), "old_originals": old_files, "script_sha256": sha256(Path(__file__)), "outputs": {p.name: {"bytes": p.stat().st_size, "sha256": sha256(p)} for p in sorted(OUT.iterdir()) if p.is_file()}}
    (OUT / "input-output-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n")
    return {"summary": summary, "manifest": manifest}


if __name__ == "__main__":
    if sys.argv[1:] == ["--synthetic-only"]:
        print(json.dumps(synthetic_check(), ensure_ascii=False))
        raise SystemExit(0)
    print(json.dumps(main(), ensure_ascii=False))
