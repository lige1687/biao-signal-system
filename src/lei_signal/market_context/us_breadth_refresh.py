"""Prepare a verified live breadth tail without changing historical/research files.

python -m lei_signal.market_context.us_breadth_refresh --output <new-directory>
Only the candidate directory is written. Installing its history into the live
cache is a separate, explicitly authorized operation. No scheduler is installed.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import threading
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from lei_signal.api.config import cache_root
from lei_signal.market_context.us_breadth import compute_sp500_breadth

NY = ZoneInfo("America/New_York")
WINDOWS = (20, 50, 200)


def closed_date(now: datetime) -> str:
    """Conservative close cutoff: wait until 17:00 NY, even on half-days."""
    local = now.astimezone(NY)
    day = local.date() if local.hour >= 17 else local.date() - timedelta(days=1)
    return day.isoformat()


def parse_chart(payload: dict, cutoff: str) -> pd.Series:
    chart = payload["chart"]
    if chart.get("error") or not chart.get("result"):
        raise ValueError(str(chart.get("error") or "no chart result"))
    result = chart["result"][0]
    # Recompute every new observation from one consistent adjusted-price window.
    # Never splice unadjusted new prices onto the old adjusted matrix.
    values = result["indicators"]["adjclose"][0]["adjclose"]
    dates = [datetime.fromtimestamp(ts, NY).date().isoformat() for ts in result["timestamp"]]
    s = pd.Series(values, index=pd.to_datetime(dates), dtype=float)
    if s.index.has_duplicates:
        raise ValueError("duplicate trading date")
    s = s.sort_index().loc[:cutoff]
    return s.where(s > 0).dropna()


def fetch_chart(symbol: str, cutoff: str, stopped: threading.Event) -> pd.Series:
    if stopped.is_set():
        raise RuntimeError("provider rate limit; remaining requests stopped")
    response = requests.get(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol.replace('.', '-')}",
        params={"range": "2y", "interval": "1d"},
        headers={"User-Agent": "Mozilla/5.0"}, timeout=25,
    )
    if response.status_code == 429:
        stopped.set()
    response.raise_for_status()
    return parse_chart(response.json(), cutoff)


def build_candidate(old: list[dict], prices: pd.DataFrame, calendar: pd.DatetimeIndex,
                    symbols: list[str], coverage: float = .95) -> tuple[list[dict], list[dict]]:
    if not old or not symbols or len(set(symbols)) != len(symbols):
        raise ValueError("missing history or invalid universe")
    old_dates = [row["date"] for row in old]
    if old_dates != sorted(set(old_dates)):
        raise ValueError("historical dates are not unique and ordered")
    if prices.index.has_duplicates or calendar.has_duplicates:
        raise ValueError("duplicate price/calendar date")
    # Reindex to actual index sessions: a missing stock date invalidates its MA,
    # rather than turning N sessions into N available observations.
    matrix = prices.reindex(index=calendar.sort_values(), columns=symbols)
    new_dates = matrix.index[matrix.index > pd.Timestamp(old_dates[-1])]
    if len(new_dates) == 0:
        raise ValueError("no completed new sessions")
    eligible = {w: (matrix.notna() & matrix.rolling(w).mean().notna()).sum(axis=1) for w in WINDOWS}
    rows = compute_sp500_breadth(matrix)
    by_date = {row["date"]: row for row in rows}
    audit = []
    tail = []
    for day in new_dates:
        date = day.strftime("%Y-%m-%d")
        counts = {str(w): int(eligible[w].loc[day]) for w in WINDOWS}
        if any(n / len(symbols) < coverage for n in counts.values()):
            raise ValueError(f"insufficient coverage {date}: {counts} / {len(symbols)}")
        row = by_date.get(date)
        if row is None or any(row.get(f"breadth_{w}") is None for w in WINDOWS):
            raise ValueError(f"missing breadth {date}")
        tail.append(row)
        audit.append({"date": date, "eligible": counts, "universe_count": len(symbols)})
    return old + tail, audit


def prepare(output: Path) -> dict:
    if output.exists():
        raise ValueError("output must be new; prior candidates are preserved")
    cache = Path(cache_root())
    old_file = cache / "sp500_ma_breadth_history.json"
    matrix_file = cache / "sp500_klines.parquet"
    old_bytes = old_file.read_bytes()
    old = json.loads(old_bytes)
    symbols = [str(c) for c in pd.read_parquet(matrix_file).columns]
    started = datetime.now(NY)
    cutoff = closed_date(started)
    stopped = threading.Event()
    calendar = fetch_chart("^GSPC", cutoff, stopped).index
    if calendar.empty:
        raise ValueError("no index trading calendar")
    frames, failures = {}, {}
    # Small bounded concurrency, no unbounded retries or provider-limit bypass.
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fetch_chart, s, cutoff, stopped): s for s in symbols}
        for i, future in enumerate(as_completed(futures), 1):
            symbol = futures[future]
            try:
                frames[symbol] = future.result()
            except Exception as exc:
                failures[symbol] = f"{type(exc).__name__}: {str(exc)[:200]}"
            if i % 50 == 0 or i == len(symbols):
                print(f"quotes {i}/{len(symbols)}, failures {len(failures)}", flush=True)
    prices = pd.DataFrame(frames)
    output.mkdir(parents=True)
    prices.to_parquet(output / "adjusted-closes.parquet")
    # Preserve the exact old JSON and its fingerprint before making a candidate.
    (output / "previous-history.json").write_bytes(old_bytes)
    receipt = {
        "retrieved_at": started.isoformat(), "cutoff": cutoff,
        "last_index_session": calendar.max().strftime("%Y-%m-%d"),
        "source": "Yahoo Finance chart API adjusted close, 2y",
        "universe": f"Existing {len(symbols)}-column observation snapshot; not point-in-time index membership",
        "symbols": symbols, "failures": failures,
        "previous_file": str(old_file), "previous_sha256": hashlib.sha256(old_bytes).hexdigest(),
        "previous_last_date": old[-1]["date"], "coverage_minimum": .95,
        "historical_availability": "retrieved now; not historical provider-arrival evidence",
        "installed": False,
    }
    try:
        if stopped.is_set():
            raise ValueError("provider rate limit encountered")
        candidate, audit = build_candidate(old, prices, calendar, symbols)
        encoded = json.dumps(candidate, ensure_ascii=False).encode()
        (output / "sp500_ma_breadth_history.json").write_bytes(encoded)
        receipt.update(qualified=True, added_sessions=len(audit), qualification=audit,
                       last_date=candidate[-1]["date"], latest=candidate[-1],
                       candidate_sha256=hashlib.sha256(encoded).hexdigest())
    except ValueError as exc:
        receipt.update(qualified=False, error=str(exc))
    (output / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2))
    return receipt


def install_candidate(output: Path, target: Path) -> dict:
    """Explicit apply step. Caller must have permission to write target/backup.

    Verify both versions before writing; retain exact original bytes and only
    atomically replace the small live history JSON, never the research matrix.
    """
    receipt = json.loads((output / "receipt.json").read_text())
    candidate = (output / "sp500_ma_breadth_history.json").read_bytes()
    original = target.read_bytes()
    digest = lambda value: hashlib.sha256(value).hexdigest()
    if not receipt.get("qualified") or digest(candidate) != receipt["candidate_sha256"]:
        raise ValueError("unqualified or changed candidate")
    if str(target.resolve()) != str(Path(receipt["previous_file"]).resolve()):
        raise ValueError("different target")
    if digest(original) != receipt["previous_sha256"]:
        raise ValueError("live source changed; revalidate before installing")
    previous, proposed = json.loads(original), json.loads(candidate)
    if proposed[:len(previous)] != previous or len(proposed) <= len(previous):
        raise ValueError("candidate does not preserve historical observations")
    suffix = datetime.now(NY).strftime("%Y%m%dT%H%M%S%f")
    backup = target.with_name(f"{target.name}.before-{suffix}.bak")
    temporary = target.with_name(f"{target.name}.pending-{suffix}")
    with backup.open("xb") as f:
        f.write(original)
        f.flush()
        os.fsync(f.fileno())
    with temporary.open("xb") as f:
        f.write(candidate)
        f.flush()
        os.fsync(f.fileno())
    if digest(target.read_bytes()) != receipt["previous_sha256"]:
        raise ValueError("live source changed during preparation; no replacement")
    os.replace(temporary, target)
    assert target.read_bytes() == candidate
    return {"installed": True, "target": str(target), "backup": str(backup),
            "sha256": digest(candidate), "last_date": proposed[-1]["date"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--install-target", type=Path,
                        help="Explicitly install an already prepared candidate; requires target write authorization")
    args = parser.parse_args()
    if args.install_target:
        receipt = install_candidate(args.output, args.install_target)
        (args.output / "installation.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2))
        print(json.dumps(receipt, ensure_ascii=False))
    else:
        receipt = prepare(args.output)
        print(json.dumps({k: v for k, v in receipt.items() if k not in {"symbols", "qualification", "failures"}}, ensure_ascii=False))
        raise SystemExit(0 if receipt["qualified"] else 2)
