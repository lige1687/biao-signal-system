"""Bounded Yahoo daily-chart refresh of the previously verified US502 file pool.

Run: python3 docs/ops/microstructure-observations-20261108/constituents/fetch_us_recent.py
This saves source responses; it never alters the old files or publishes a card.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, quote
from zoneinfo import ZoneInfo

import requests


OLD = Path("/Volumes/win+mac通用/LeiSignal-新实验结果/stock-universe-us-20261015/stock-universe-us-20261015-20261015T194201-82eb0af53148/result")
OUT = Path("/Volumes/win+mac通用/LeiSignal-新实验结果/microstructure-observations-20261108/equity/us-recent")
HERE = Path(__file__).resolve().parent
PERIOD1 = int(datetime(2026, 8, 25, tzinfo=timezone.utc).timestamp())
PERIOD2 = int(datetime(2026, 11, 7, tzinfo=timezone.utc).timestamp())
MAX_REQUESTS = 600
MAX_BYTES = 30 * 1024 * 1024
MAX_SECONDS = 8 * 60
MAX_WORKERS = 4


def old_pool() -> list[str]:
    symbols = []
    for path in OLD.glob("*.json"):
        if path.name.startswith("._") or path.stem in {"summary", "verification"}:
            continue
        try:
            body = json.loads(path.read_text())
            if body.get("chart", {}).get("result"):
                symbols.append(path.stem)
        except (OSError, ValueError, TypeError):
            pass
    symbols.sort()
    if len(symbols) != 502:
        raise RuntimeError(f"old successful pool changed: {len(symbols)} != 502")
    return symbols


def chart_url(symbol: str) -> str:
    params = {"period1": PERIOD1, "period2": PERIOD2, "interval": "1d", "events": "div,splits", "includeAdjustedClose": "true"}
    return "https://query1.finance.yahoo.com/v8/finance/chart/" + quote(symbol, safe="") + "?" + urlencode(params)


def fetch_one(symbol: str) -> tuple[dict, bytes | None]:
    url = chart_url(symbol)
    started = datetime.now(timezone.utc).isoformat()
    try:
        response = requests.get(url, timeout=18, headers={"User-Agent": "Mozilla/5.0"})
        body = response.content
        record = {"symbol": symbol, "url": response.url, "requestedAt": started,
                  "status": response.status_code, "bytes": len(body),
                  "sha256": hashlib.sha256(body).hexdigest()}
        return record, body
    except requests.RequestException as exc:
        return {"symbol": symbol, "url": url, "requestedAt": started, "failure": repr(exc)}, None


def summarize_raw(symbol: str, body: bytes) -> dict:
    try:
        doc = json.loads(body)
        result = doc.get("chart", {}).get("result")
        if not result:
            return {"symbol": symbol, "qualification": "empty chart.result", "sourceError": doc.get("chart", {}).get("error")}
        if len(result) != 1:
            return {"symbol": symbol, "qualification": "unexpected result count"}
        row = result[0]
        returned = row.get("meta", {}).get("symbol")
        stamps = row.get("timestamp") or []
        indicators = row.get("indicators") or {}
        adj = ((indicators.get("adjclose") or [{}])[0].get("adjclose") or [])
        close = ((indicators.get("quote") or [{}])[0].get("close") or [])
        if returned != symbol or len(stamps) != len(adj) or len(stamps) != len(close):
            return {"symbol": symbol, "qualification": "symbol or array length mismatch", "returnedSymbol": returned,
                    "timestamps": len(stamps), "adjclose": len(adj), "close": len(close)}
        zone = ZoneInfo(row.get("meta", {}).get("exchangeTimezoneName") or "America/New_York")
        dates = [datetime.fromtimestamp(t, zone).date().isoformat() for t in stamps]
        valid = [day for day, price in zip(dates, adj) if price is not None and isinstance(price, (int, float)) and price > 0]
        if len(set(dates)) != len(dates):
            return {"symbol": symbol, "qualification": "duplicate local trade dates"}
        return {"symbol": symbol, "qualification": "ok" if valid else "no adjusted prices",
                "returnedSymbol": returned, "rowCount": len(stamps), "adjustedCount": len(valid),
                "firstDate": valid[0] if valid else None, "lastDate": valid[-1] if valid else None,
                "dates": valid, "dividendEvents": len((row.get("events") or {}).get("dividends") or {}),
                "splitEvents": len((row.get("events") or {}).get("splits") or {})}
    except (ValueError, TypeError, KeyError, IndexError) as exc:
        return {"symbol": symbol, "qualification": "invalid chart payload", "detail": repr(exc)}


def save_json(path: Path, data: object) -> None:
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    temp.replace(path)


def main() -> None:
    symbols = old_pool()
    OUT.mkdir(parents=True, exist_ok=True)
    HERE.mkdir(parents=True, exist_ok=True)
    ledger_path = HERE / "source-ledger.json"
    ledger: list[dict] = json.loads(ledger_path.read_text()) if ledger_path.exists() else []
    attempted = {row["symbol"] for row in ledger}
    pending = [symbol for symbol in symbols if symbol not in attempted]
    total_bytes = sum(int(row.get("bytes", 0)) for row in ledger)
    began = time.monotonic()
    stop_reason = None
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for offset in range(0, len(pending), MAX_WORKERS):
            if time.monotonic() - began >= MAX_SECONDS:
                stop_reason = "wall time budget"
                break
            if len(ledger) + MAX_WORKERS > MAX_REQUESTS or total_bytes >= MAX_BYTES:
                stop_reason = "request or byte budget"
                break
            batch = pending[offset:offset + MAX_WORKERS]
            futures = {pool.submit(fetch_one, symbol): symbol for symbol in batch}
            batch_results = []
            for future in as_completed(futures):
                record, body = future.result()
                if body is not None:
                    if total_bytes + len(body) > MAX_BYTES:
                        record["qualification"] = "byte budget reached; raw omitted"
                        stop_reason = "byte budget"
                    else:
                        destination = OUT / f"{record['symbol']}.json"
                        if destination.exists():
                            record["qualification"] = "raw destination already exists; not overwritten"
                        else:
                            destination.write_bytes(body)
                            record["path"] = str(destination)
                            record.update({key: value for key, value in summarize_raw(record["symbol"], body).items() if key != "dates"})
                    total_bytes += len(body)
                batch_results.append(record)
            ledger.extend(sorted(batch_results, key=lambda item: item["symbol"]))
            save_json(ledger_path, ledger)
            if any(row.get("status") == 429 for row in batch_results):
                stop_reason = "HTTP 429: stopped without retry"
            if stop_reason:
                break
            if len(ledger) % 40 == 0:
                print(f"{len(ledger)}/{len(symbols)} requests; {total_bytes} bytes", flush=True)
    # Read saved raw files back so a previous interrupted run is summarized too.
    valid_rows = []
    for symbol in symbols:
        path = OUT / f"{symbol}.json"
        if path.exists():
            row = summarize_raw(symbol, path.read_bytes())
            if row.get("qualification") == "ok":
                valid_rows.append(row)
    common = set(valid_rows[0]["dates"]) if valid_rows else set()
    for row in valid_rows[1:]:
        common.intersection_update(row["dates"])
    missing = [symbol for symbol in symbols if symbol not in {row["symbol"] for row in valid_rows}]
    coverage = Counter(day for row in valid_rows for day in row["dates"])
    last_date = max((row["lastDate"] for row in valid_rows), default=None)
    current_rows = [row for row in valid_rows if row["lastDate"] == last_date]
    current_common = set(current_rows[0]["dates"]) if current_rows else set()
    for row in current_rows[1:]:
        current_common.intersection_update(row["dates"])
    summary = {"oldFixedPool": len(symbols), "attempted": len(ledger), "qualified": len(valid_rows),
               "missing": missing, "stopReason": stop_reason, "responseBytes": total_bytes,
               "firstObservedDate": min((row["firstDate"] for row in valid_rows), default=None),
               "lastObservedDate": last_date,
               "allQualifiedCommonFirst": min(common) if common else None,
               "allQualifiedCommonLast": max(common) if common else None,
               "allQualifiedCommonDays": len(common),
               "lastObservedDateCoverage": coverage[last_date] if last_date else 0,
               "absentOnLastObservedDate": [row["symbol"] for row in valid_rows if last_date not in row["dates"]],
               "lastDateCohortCommonFirst": min(current_common) if current_common else None,
               "lastDateCohortCommonLast": max(current_common) if current_common else None,
               "lastDateCohortCommonDays": len(current_common),
               "recentCoverage": {day: coverage[day] for day in sorted(coverage) if day >= "2026-10-26"},
               "sourceLedger": str(ledger_path), "rawDirectory": str(OUT)}
    save_json(HERE / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
