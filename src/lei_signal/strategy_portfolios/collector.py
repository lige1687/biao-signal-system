"""One bounded, append-only current quote collection for frozen stock universes."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import plistlib
import shutil
import subprocess
import time
import uuid
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime
from pathlib import Path
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from zoneinfo import ZoneInfo

from lei_signal.strategy_portfolios.sources import (
    cn_to_yahoo_symbol,
    completed_market_date,
    fetch_yahoo_history,
    parse_yahoo_history,
)

_ROOT = Path(__file__).resolve().parents[3]
_DESIGN = _ROOT / "docs/experiments/raw/short-reversal-green-selection-2026-10-20/design.json"
_US_CONTRACT = _ROOT / "docs/experiments/raw/stock-universe-expansion-2026-10-15/bulk-contract.json"
_PLAN = _ROOT / "docs/experiments/raw/factor-strategy-portfolios-2026-10-20/storage-plan.json"
_LOCATOR = _ROOT / "docs/experiments/raw/factor-strategy-portfolios-2026-10-20/current-source.json"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_universes() -> dict[str, list[dict]]:
    design = json.loads(_DESIGN.read_text(encoding="utf-8"))
    bound = design["sources"]["new_source_manifest"]
    manifest_raw = Path(bound["path"]).read_bytes()
    if _sha(manifest_raw) != bound["sha256"]:
        raise ValueError("CN frozen manifest hash changed")
    cn = json.loads(manifest_raw)["asset_sources"]
    if len(cn) != 300:
        raise ValueError("CN fixed300 changed")
    us = json.loads(_US_CONTRACT.read_text(encoding="utf-8"))["selection"]["us"]
    if len(us) != 504 or len({x["code"] for x in us}) != 504:
        raise ValueError("US fixed504 changed")
    return {
        "CN": [{"symbol": code, "name": code, "provider_symbol": cn_to_yahoo_symbol(code)}
               for code in sorted(cn)],
        "US": [{"symbol": x["code"], "name": x.get("name") or x["code"],
                "provider_symbol": x["code"]} for x in us],
    }


def _verify_output_plan(plan: dict) -> Path:
    mount = Path(plan["external_mount"])
    output = Path(plan["output"])
    if not mount.is_mount() or not output.is_relative_to(mount):
        raise ValueError("external output mount unavailable")
    info = plistlib.loads(subprocess.check_output(
        ["diskutil", "info", "-plist", str(mount)], timeout=10,
    ))
    if info.get("VolumeUUID") != plan["external_uuid"]:
        raise ValueError("external volume UUID changed")
    if mount.stat().st_dev != plan["external_device"]:
        raise ValueError("external device changed")
    if not output.parent.resolve().is_relative_to(mount.resolve()):
        raise ValueError("planned output path leaves mounted volume")
    available = shutil.disk_usage(mount).free
    if available < plan["external_reserve_bytes"] + plan["estimated_bytes"]:
        raise ValueError("planned external capacity unavailable")
    output.mkdir(parents=True, exist_ok=True)
    if not output.is_dir() or output.stat().st_dev != mount.stat().st_dev:
        raise ValueError("planned output on wrong device")
    return output


def _append_jsonl(path: Path, row: dict) -> None:
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        file.flush()
        os.fsync(file.fileno())


class _RateLimiter:
    def __init__(self, seconds: float = 1.0) -> None:
        self.seconds = seconds
        self.lock = Lock()
        self.next_at = 0.0

    def wait(self) -> None:
        with self.lock:
            now = time.monotonic()
            delay = max(0.0, self.next_at - now)
            self.next_at = max(now, self.next_at) + self.seconds
        if delay:
            time.sleep(delay)


def _request(member: dict, limiter: _RateLimiter, fetcher) -> tuple[dict, dict | None]:
    limiter.wait()
    stamp = datetime.now(ZoneInfo("UTC")).isoformat()
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           f"{quote(member['provider_symbol'])}?interval=1d&range=2y&events=div%2Csplits")
    try:
        fetched = fetcher(member["provider_symbol"], range="2y", timeout=15)
        raw = fetched["raw"]
        if _sha(raw) != fetched["raw_hash"]:
            raise ValueError("fetch response hash mismatch")
        record = {"symbol": member["symbol"], "provider_symbol": member["provider_symbol"],
                  "received_at": fetched["retrieved_at"], "source_url": fetched["source_url"],
                  "raw_hash": fetched["raw_hash"], "bytes": len(raw)}
        try:
            parsed = parse_yahoo_history(fetched["payload"], member["provider_symbol"],
                                         fetched["retrieved_at"])
        except (ValueError, KeyError, TypeError) as exc:
            return ({**record, "status": "source_invalid", "error": str(exc)[:180]},
                    {"raw": raw, "parsed": None})
        return ({**record, "status": "ok",
                 "latest_date": parsed["metadata"]["last_completed_date"],
                 "bars": len(parsed["bars"])}, {"raw": raw, "parsed": parsed})
    except HTTPError as exc:
        return ({"symbol": member["symbol"], "provider_symbol": member["provider_symbol"],
                 "received_at": stamp, "source_url": url, "raw_hash": None,
                 "status": "http_error", "http_status": exc.code,
                 "error": str(exc)[:180]}, None)
    except (URLError, TimeoutError, OSError) as exc:
        return ({"symbol": member["symbol"], "provider_symbol": member["provider_symbol"],
                 "received_at": stamp, "source_url": url, "raw_hash": None,
                 "status": "network_error",
                 "error": str(exc)[:180]}, None)
    except (ValueError, KeyError, TypeError) as exc:
        return ({"symbol": member["symbol"], "provider_symbol": member["provider_symbol"],
                 "received_at": stamp, "source_url": url, "raw_hash": None,
                 "status": "source_invalid",
                 "error": str(exc)[:180]}, None)


def _freshness(market: str, rows: list[dict], received_at: str) -> dict:
    dates = [row["latest_date"] for row in rows if row.get("latest_date")]
    cutoff = completed_market_date(market, received_at)
    latest = max(dates) if dates else None
    count_latest = sum(day == latest for day in dates)
    ratio = count_latest / len(rows) if rows else 0.0
    return {"cutoff_date_without_calendar": cutoff, "latest_observed_date": latest,
            "latest_same_date_count": count_latest, "universe_count": len(rows),
            "latest_fraction": ratio,
            "new_decision_ready": bool(latest == cutoff and ratio >= 0.9),
            "calendar_verified": False}


def collect(*, fetcher=fetch_yahoo_history, plan_path: Path = _PLAN,
            locator_path: Path = _LOCATOR, max_requests: int = 804,
            compress: bool = False) -> dict:
    """Collect probes then the remaining frozen cohort, preserving every attempt."""
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    output = _verify_output_plan(plan)
    universes = _read_universes()
    if max_requests > 804 or max_requests < 2:
        raise ValueError("request budget must be 2..804")
    started = datetime.now(ZoneInfo("UTC")).isoformat()
    batch = output / "current" / (datetime.now(ZoneInfo("UTC")).strftime("%Y%m%dT%H%M%SZ")
                                    + "-" + uuid.uuid4().hex[:8])
    batch.mkdir(parents=True, exist_ok=False)
    if batch.stat().st_dev != plan["external_device"]:
        raise ValueError("batch directory on wrong device")
    attempts_path = batch / "attempts.jsonl"
    limiter = _RateLimiter()
    results: dict[str, dict] = {"CN": {"universe": universes["CN"], "bars": [], "metadata": {}},
                                "US": {"universe": universes["US"], "bars": [], "metadata": {}}}
    attempted, network_streak, stopped = set(), 0, None

    def preserve(market: str, record: dict, value: dict | None) -> None:
        nonlocal network_streak, stopped
        symbol = record["symbol"]
        attempted.add((market, symbol))
        if value is not None:
            filename = f"{market}-{symbol.replace('.', '_')}.json"
            if compress:
                filename += ".gz"
            path = batch / filename
            saved_raw = gzip.compress(value["raw"], mtime=0) if compress else value["raw"]
            with path.open("xb") as file:
                file.write(saved_raw)
                file.flush()
                os.fsync(file.fileno())
            read_back = path.read_bytes()
            if _sha(read_back) != _sha(saved_raw):
                raise ValueError("saved source hash mismatch")
            if _sha(gzip.decompress(read_back) if compress else read_back) != record["raw_hash"]:
                raise ValueError("saved source content changed")
            record["raw_file"] = filename
            record["storage_sha256"] = _sha(saved_raw)
            if value["parsed"] is not None:
                for bar in value["parsed"]["bars"]:
                    results[market]["bars"].append({**bar, "symbol": symbol,
                                                     "provider_symbol": record["provider_symbol"]})
            network_streak = 0
        elif record["status"] == "network_error":
            network_streak += 1
        else:
            network_streak = 0
        _append_jsonl(attempts_path, {"market": market, **record})
        if record.get("http_status") == 429:
            stopped = "http_429"
        elif network_streak >= 3:
            stopped = "three_consecutive_network_failures"

    # Probe both markets before scheduling a larger batch.
    for market in ("US", "CN"):
        member = universes[market][0]
        record, value = _request(member, limiter, fetcher)
        preserve(market, record, value)
        if stopped:
            break
    probe_ok = len(attempted) == 2 and all(
        any(bar["symbol"] == universes[m][0]["symbol"] for bar in results[m]["bars"])
        for m in ("US", "CN")
    )
    if not probe_ok and stopped is None:
        stopped = "probe_failed"
    if probe_ok and stopped is None:
        pending = [(m, row) for m in ("CN", "US") for row in universes[m][1:]]
        pending = pending[:max_requests - 2]
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {}
            index = 0
            while (index < len(pending) or futures) and not stopped:
                while index < len(pending) and len(futures) < 2:
                    market, member = pending[index]
                    futures[pool.submit(_request, member, limiter, fetcher)] = market
                    index += 1
                completed, _ = wait(futures, return_when=FIRST_COMPLETED)
                for future in completed:
                    market = futures.pop(future)
                    record, value = future.result()
                    preserve(market, record, value)
            # Already started calls remain accountable after a stop condition.
            for future, market in futures.items():
                record, value = future.result()
                preserve(market, record, value)

    saved_attempts = [json.loads(line)
                      for line in attempts_path.read_text(encoding="utf-8").splitlines()]
    for market in ("CN", "US"):
        records = [row for row in saved_attempts if row["market"] == market]
        by_symbol = {row["symbol"]: row for row in records}
        missing = {row["symbol"]: by_symbol.get(row["symbol"], {"status": "not_attempted"})
                   for row in universes[market]
                   if by_symbol.get(row["symbol"], {}).get("status") != "ok"
                   or not by_symbol.get(row["symbol"], {}).get("latest_date")}
        received = datetime.now(ZoneInfo("UTC")).isoformat()
        results[market]["metadata"] = {
            "intended_symbols": len(universes[market]), "attempted_symbols": len(records),
            "priced_symbols": sum(bool(row.get("latest_date")) for row in records),
            "missing": missing, "freshness": _freshness(market, records, received),
            "quote_execution_status": "unknown", "membership_frozen": True,
        }
        results[market]["bars"].sort(key=lambda row: (row["symbol"], row["date"]))
    snapshot = {"received_at": datetime.now(ZoneInfo("UTC")).isoformat(),
                "started_at": started, "stopped": stopped,
                "markets": results}
    snapshot_path = batch / ("snapshot.json.gz" if compress else "snapshot.json")
    if compress:
        with gzip.open(snapshot_path, "xt", encoding="utf-8", compresslevel=6) as file:
            json.dump(snapshot, file, ensure_ascii=False, separators=(",", ":"))
    else:
        with snapshot_path.open("x", encoding="utf-8") as file:
            json.dump(snapshot, file, ensure_ascii=False, separators=(",", ":"))
            file.flush()
            os.fsync(file.fileno())
    if compress:
        with snapshot_path.open("rb") as file:
            os.fsync(file.fileno())
    locator = {"schema": "strategy-portfolios-current-source/1",
               "batch": str(batch), "snapshot": str(snapshot_path),
               "snapshot_sha256": _sha(snapshot_path.read_bytes()),
               "compression": "gzip" if compress else None,
               "attempts": str(attempts_path), "stopped": stopped,
               "received_at": snapshot["received_at"],
               "counts": {m: {k: results[m]["metadata"][k]
                               for k in ("intended_symbols", "attempted_symbols", "priced_symbols")}
                          for m in ("CN", "US")}}
    locator_path.parent.mkdir(parents=True, exist_ok=True)
    with locator_path.open("x", encoding="utf-8") as file:
        json.dump(locator, file, ensure_ascii=False, indent=2)
    return locator


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, default=_PLAN)
    args = parser.parse_args()
    print(json.dumps(collect(plan_path=args.plan), ensure_ascii=False, indent=2))
