"""Bounded collector checks with synthetic responses only."""

from __future__ import annotations

import gzip
import hashlib
import json
from datetime import datetime
from urllib.error import HTTPError
from zoneinfo import ZoneInfo

from lei_signal.strategy_portfolios import collector


def _payload(symbol: str, cn: bool) -> dict:
    zone = "Asia/Shanghai" if cn else "America/New_York"
    stamp = int(datetime(2026, 10, 19, 12, tzinfo=ZoneInfo(zone)).timestamp())
    return {"chart": {"error": None, "result": [{
        "meta": {"symbol": symbol, "currency": "CNY" if cn else "USD",
                 "exchangeTimezoneName": zone},
        "timestamp": [stamp],
        "indicators": {"quote": [{"open": [10.0], "high": [11.0], "low": [9.0],
                                  "close": [10.0], "volume": [100.0]}],
                       "adjclose": [{"adjclose": [10.0]}]},
        "events": {"dividends": {}, "splits": {}},
    }]}}


def _setup(tmp_path, monkeypatch):
    monkeypatch.setattr(collector, "_verify_output_plan", lambda plan: tmp_path)
    monkeypatch.setattr(collector, "_read_universes", lambda: {
        "CN": [{"symbol": "sh.600000", "name": "Example CN",
                "provider_symbol": "600000.SS"}],
        "US": [{"symbol": "AAPL", "name": "Example US", "provider_symbol": "AAPL"}],
    })
    monkeypatch.setattr(collector._RateLimiter, "wait", lambda self: None)
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"external_device": tmp_path.stat().st_dev}))
    return plan, tmp_path / "locator.json"


def _attempts(result):
    return [json.loads(line)
            for line in collector.Path(result["attempts"]).read_text().splitlines()]


def test_two_probes_persist_raw_and_snapshot(tmp_path, monkeypatch):
    plan, locator = _setup(tmp_path, monkeypatch)

    def fetcher(symbol, *, range, timeout):
        assert range == "2y" and timeout == 15
        raw = json.dumps(_payload(symbol, symbol.endswith(".SS"))).encode()
        return {"raw": raw, "raw_hash": hashlib.sha256(raw).hexdigest(),
                "payload": json.loads(raw), "source_url": f"https://example/{symbol}",
                "retrieved_at": "2026-10-20T18:00:00+08:00"}

    result = collector.collect(fetcher=fetcher, plan_path=plan,
                               locator_path=locator, max_requests=2)
    batch = result["batch"]
    attempts = _attempts(result)
    snap = json.loads(collector.Path(result["snapshot"]).read_text())
    assert len(attempts) == 2 and all(row["status"] == "ok" for row in attempts)
    assert result["stopped"] is None
    assert len(snap["markets"]["CN"]["bars"]) == 1
    assert len(snap["markets"]["US"]["bars"]) == 1
    assert (tmp_path / "locator.json").exists()
    assert (collector.Path(batch) / "CN-sh_600000.json").exists()


def test_http_429_stops_after_first_probe_and_keeps_missing(tmp_path, monkeypatch):
    plan, locator = _setup(tmp_path, monkeypatch)

    def limited(*_args, **_kwargs):
        raise HTTPError("https://example/AAPL", 429, "Too Many Requests", {}, None)

    result = collector.collect(fetcher=limited, plan_path=plan,
                               locator_path=locator, max_requests=2)
    snap = json.loads(collector.Path(result["snapshot"]).read_text())
    attempts = _attempts(result)
    assert result["stopped"] == "http_429"
    assert len(attempts) == 1
    assert snap["markets"]["CN"]["metadata"]["missing"]["sh.600000"]["status"] == "not_attempted"


def test_invalid_payload_still_preserves_raw(tmp_path, monkeypatch):
    plan, locator = _setup(tmp_path, monkeypatch)

    def invalid(symbol, *, range, timeout):
        raw = b'{"chart":{"result":null}}'
        return {"raw": raw, "raw_hash": hashlib.sha256(raw).hexdigest(),
                "payload": json.loads(raw), "source_url": f"https://example/{symbol}",
                "retrieved_at": "2026-10-20T18:00:00+08:00"}

    result = collector.collect(fetcher=invalid, plan_path=plan,
                               locator_path=locator, max_requests=2)
    attempts = _attempts(result)
    assert result["stopped"] == "probe_failed"
    assert all(row["status"] == "source_invalid" for row in attempts)
    assert all((collector.Path(result["batch"]) / row["raw_file"]).exists()
               for row in attempts)


def test_optional_gzip_keeps_original_payload_and_snapshot(tmp_path, monkeypatch):
    plan, locator = _setup(tmp_path, monkeypatch)

    def fetcher(symbol, *, range, timeout):
        raw = json.dumps(_payload(symbol, symbol.endswith(".SS"))).encode()
        return {"raw": raw, "raw_hash": hashlib.sha256(raw).hexdigest(),
                "payload": json.loads(raw), "source_url": f"https://example/{symbol}",
                "retrieved_at": "2026-10-20T18:00:00+08:00"}

    result = collector.collect(fetcher=fetcher, plan_path=plan,
                               locator_path=locator, max_requests=2, compress=True)
    assert result["compression"] == "gzip"
    attempts = _attempts(result)
    for row in attempts:
        saved = collector.Path(result["batch"]) / row["raw_file"]
        assert saved.name.endswith(".json.gz")
        assert hashlib.sha256(gzip.decompress(saved.read_bytes())).hexdigest() == row["raw_hash"]
    with gzip.open(result["snapshot"], "rt", encoding="utf-8") as file:
        snapshot = json.load(file)
    assert len(snapshot["markets"]["US"]["bars"]) == 1
