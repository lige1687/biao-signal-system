#!/usr/bin/env python3
"""Source-only quote-availability audit v2; applies source-reported no-trade gap windows."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import pathlib
import sys
from collections import Counter
from datetime import datetime, timezone

import pandas as pd


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def json_write(path: pathlib.Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def finite_positive(value) -> bool:
    try:
        x = float(value)
        return math.isfinite(x) and x > 0
    except (TypeError, ValueError):
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", required=True)
    args = ap.parse_args()
    started = datetime.now(timezone.utc).isoformat()
    contract_path = pathlib.Path(args.contract).resolve()
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    source_specs = contract["inputs"] + [contract["prices"]]
    for spec in source_specs:
        p = pathlib.Path(spec["path"])
        if sha256(p) != spec["sha256"]:
            raise RuntimeError(f"input SHA mismatch: {p}")
    out = pathlib.Path(contract["output"] + "-v2")
    out.mkdir(parents=True, exist_ok=False)

    membership_path = pathlib.Path(contract["inputs"][0]["path"])
    gaps_path = pathlib.Path(contract["inputs"][1]["path"])
    no_trade_path = pathlib.Path(contract["inputs"][2]["path"])
    prices_path = pathlib.Path(contract["prices"]["path"])
    intervals = pd.read_parquet(membership_path)
    if not {"ticker", "start", "end"}.issubset(intervals.columns):
        raise RuntimeError(f"unexpected interval schema: {intervals.columns.tolist()}")
    # The frozen source schema calls the exclusive membership endpoint `end`.
    intervals["start"] = pd.to_datetime(intervals["start"], errors="coerce")
    intervals["end"] = pd.to_datetime(intervals["end"], errors="coerce")
    intervals["interval_row"] = range(len(intervals))
    events = intervals[(intervals["end"] >= "2015-01-01") & (intervals["end"] < "2025-01-01")].copy()
    if len(events) != 218:
        raise RuntimeError(f"expected 218 dated end events, found {len(events)}")

    prices = pd.read_parquet(prices_path)
    expected_price_cols = {"date", "ticker", "close", "adj_close", "volume", "source"}
    if not expected_price_cols.issubset(prices.columns):
        raise RuntimeError(f"unexpected price schema: {prices.columns.tolist()}")
    prices["date"] = pd.to_datetime(prices["date"], errors="coerce")
    spy_dates = sorted(prices.loc[prices.ticker.eq("SPY"), "date"].dropna().unique())
    spy_set = set(spy_dates)
    if not spy_dates:
        raise RuntimeError("SPY source calendar is empty")
    by_ticker = {t: g.sort_values("date") for t, g in prices.groupby("ticker", sort=False)}

    no_trade = pd.read_csv(no_trade_path, dtype=str, keep_default_na=False)
    no_trade_set = set(zip(no_trade["ticker"], no_trade["date"]))
    no_trade_kinds = {}
    for r in no_trade.itertuples(index=False):
        no_trade_kinds.setdefault((r.ticker, r.date), []).append(r.kind)
    gaps = pd.read_csv(gaps_path, dtype=str, keep_default_na=False)
    gaps_keep = gaps[gaps.ticker.isin(["SIVB", "SBNY"])].to_dict(orient="records")
    gap_windows = {}
    for g in gaps.itertuples(index=False):
        try:
            last = pd.Timestamp(g.last_trade)
            resumed = pd.Timestamp(g.next_trade)
        except Exception:
            continue
        if pd.notna(last) and pd.notna(resumed) and last < resumed:
            gap_windows.setdefault(str(g.ticker), []).append((last, resumed, g._asdict()))
    # Synthetic regression: positive volume is still rejected inside a source-reported gap.
    synth_last, synth_resume = pd.Timestamp("2023-03-09"), pd.Timestamp("2023-03-28")
    synth_quote_date, synth_volume = pd.Timestamp("2023-03-21"), 4.0
    def in_gap(date, windows):
        d = pd.Timestamp(date)
        return any(a < d < b for a, b in windows)
    assert finite_positive(synth_volume) and in_gap(synth_quote_date, [(synth_last, synth_resume)])
    assert not (finite_positive(synth_volume) and not in_gap(synth_quote_date, [(synth_last, synth_resume)]))

    def spy_month_end(year: int, month: int):
        return next((d for d in reversed(spy_dates) if d.year == year and d.month == month), None)

    rows = []
    for ev in events.itertuples(index=False):
        ticker = str(ev.ticker)
        removal = pd.Timestamp(ev.end)
        prior_y, prior_m = (removal.year - 1, 12) if removal.month == 1 else (removal.year, removal.month - 1)
        formation = spy_month_end(prior_y, prior_m)
        target = spy_month_end(removal.year, removal.month)
        held_at_formation = bool(formation is not None and pd.Timestamp(ev.start) <= formation < removal)
        tg = by_ticker.get(ticker)
        if tg is None:
            exact = pd.DataFrame(columns=prices.columns)
        else:
            exact = tg
        pre = exact[exact.date < removal]
        post = exact[(exact.date >= removal) & (exact.date <= pd.Timestamp("2024-12-31"))]
        target_rows = exact[exact.date.eq(target)] if target is not None else exact.iloc[0:0]

        def row_payload(frame):
            if frame.empty:
                return None
            r = frame.iloc[-1]
            d = pd.Timestamp(r.date).strftime("%Y-%m-%d")
            return {"date": d, "close": None if pd.isna(r.close) else float(r.close),
                    "adj_close": None if pd.isna(r.adj_close) else float(r.adj_close),
                    "volume": None if pd.isna(r.volume) else float(r.volume),
                    "source": None if pd.isna(r.source) else str(r.source),
                    "no_trade_kinds": no_trade_kinds.get((ticker, d), [])}

        pre_payload = row_payload(pre.tail(1))
        target_payload = row_payload(target_rows.tail(1))
        if target_rows.empty:
            target_status = "missing"
        elif len(target_rows) != 1:
            target_status = "duplicate_exact_ticker_date_rows"
        else:
            r = target_rows.iloc[0]
            d = pd.Timestamp(r.date).strftime("%Y-%m-%d")
            if (ticker, d) in no_trade_set:
                target_status = "explicit_no_trade_or_halt_record"
            elif any(a < pd.Timestamp(r.date) < b for a, b, _ in gap_windows.get(ticker, [])):
                target_status = "inside_source_reported_gap_window"
            elif not (finite_positive(r.close) and finite_positive(r.adj_close) and finite_positive(r.volume)):
                target_status = "invalid_or_nonpositive_quote_or_volume"
            else:
                target_status = "observable_quote_candidate"
        first_raw_post = row_payload(post.head(1))
        blocked = []
        for gd, gs, _ in gap_windows.get(ticker, []):
            if gd < gs:
                blocked.append((gd, gs))
        def is_gap_date(value):
            return in_gap(value, blocked)
        post_candidates = post[post.apply(
            lambda r: finite_positive(r.close) and finite_positive(r.adj_close)
                      and finite_positive(r.volume)
                      and (ticker, pd.Timestamp(r.date).strftime("%Y-%m-%d")) not in no_trade_set
                      and not is_gap_date(r.date), axis=1)]
        first_candidate = row_payload(post_candidates.head(1))
        rows.append({
            "interval_row": int(ev.interval_row), "ticker": ticker,
            "membership_start": pd.Timestamp(ev.start).strftime("%Y-%m-%d"),
            "removal_end_exclusive": removal.strftime("%Y-%m-%d"),
            "formation_spy_month_end": None if formation is None else pd.Timestamp(formation).strftime("%Y-%m-%d"),
            "target_spy_removal_month_end": None if target is None else pd.Timestamp(target).strftime("%Y-%m-%d"),
            "held_at_prior_month_end": held_at_formation,
            "pre_removal_last_exact_ticker_quote": json.dumps(pre_payload, ensure_ascii=False, sort_keys=True) if pre_payload is not None else "null",
            "first_post_removal_any_exact_ticker_quote": json.dumps(first_raw_post, ensure_ascii=False, sort_keys=True) if first_raw_post is not None else "null",
            "first_post_removal_source_filtered_quote_candidate": json.dumps(first_candidate, ensure_ascii=False, sort_keys=True) if first_candidate is not None else "null",
            "target_month_end_exact_quote": json.dumps(target_payload, ensure_ascii=False, sort_keys=True) if target_payload is not None else "null",
            "target_quote_status": target_status,
            "target_exact_row_count": int(len(target_rows)),
            "target_no_trade_kinds_json": json.dumps([] if target_payload is None else target_payload["no_trade_kinds"], ensure_ascii=False),
            "post_quote_source_reported_gap_windows": json.dumps([
                {"last_trade": a.strftime("%Y-%m-%d"), "resumed_trade": b.strftime("%Y-%m-%d")}
                for a, b in blocked], ensure_ascii=False),
            "terminal_security_cash_share_entitlement_verified": False,
            "interpretation": "quote availability only; index removal is not a sale; no alias, carry-forward, or zero fill; source-reported gap windows block candidates"
        })

    df = pd.DataFrame(rows)
    csv_path = out / "event-outcomes.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8", lineterminator="\n")
    special = [r for r in rows if r["ticker"] in {"AGN", "CB-201601", "JCI-201609", "SIVB", "SBNY"}]
    json_write(out / "special-cases.json", {
        "focus_events": special,
        "exit_gaps_exact_rows_for_SIVB_SBNY": gaps_keep,
        "limitations": "Exact archived ticker identities only. Dates strictly after last_trade and before next_trade in a matching exit_gaps row are blocked as source-reported gap days. A remaining quote is only an unverified observation candidate; no source flag proves general tradability or terminal value."
    })
    summary = {
        "event_count": len(rows),
        "date_range": [min(r["removal_end_exclusive"] for r in rows), max(r["removal_end_exclusive"] for r in rows)],
        "ticker_event_counts": dict(sorted(Counter(r["ticker"] for r in rows).items())),
        "held_at_prior_month_end": sum(r["held_at_prior_month_end"] for r in rows),
        "not_held_at_prior_month_end": sum(not r["held_at_prior_month_end"] for r in rows),
        "target_quote_status_counts": dict(Counter(r["target_quote_status"] for r in rows)),
        "events_with_any_first_post_removal_exact_quote_through_2024_12_31": sum(r["first_post_removal_any_exact_ticker_quote"] != "null" for r in rows),
        "events_with_source_filtered_post_removal_quote_candidate_through_2024_12_31": sum(r["first_post_removal_source_filtered_quote_candidate"] != "null" for r in rows),
        "search_end_date": "2024-12-31",
        "known_gap_windows_applied_exclusive_endpoints": True,
        "synthetic_gap_volume4_rejected": True,
        "unflagged_dates_are_not_certified_tradable": True,
        "explicit_no_trade_day_rows": len(no_trade),
        "exit_gap_rows_for_SIVB_SBNY": len(gaps_keep),
        "calendar_definition": "Observed SPY dates only; prior-calendar-month end for formation and removal-month end for target observation.",
        "not_a_sale_or_return_test": True,
        "no_network_or_effect_calculation": True,
        "input_hashes": {pathlib.Path(s["path"]).name: s["sha256"] for s in source_specs}
    }
    json_write(out / "summary.json", summary)
    outputs = []
    for name in ["event-outcomes.csv", "special-cases.json", "summary.json"]:
        p = out / name
        outputs.append({"path": name, "sha256": sha256(p), "bytes": p.stat().st_size})
    manifest = {
        "contract_path": str(contract_path), "contract_sha256": sha256(contract_path),
        "created_at": datetime.now(timezone.utc).isoformat(), "outputs": outputs,
        "event_count": len(rows), "source_only": True
    }
    json_write(out / "manifest.json", manifest)
    # Read-back checks are performed before returning success.
    reread = pd.read_csv(csv_path, dtype={"ticker": str})
    if len(reread) != 218 or reread.interval_row.nunique() != 218:
        raise RuntimeError("readback did not preserve all 218 event identities")
    for item in outputs:
        if sha256(out / item["path"]) != item["sha256"]:
            raise RuntimeError(f"readback SHA mismatch: {item['path']}")
    print(json.dumps({"status": "success", "output": str(out), "summary": summary,
                      "manifest_sha256": sha256(out / "manifest.json")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
