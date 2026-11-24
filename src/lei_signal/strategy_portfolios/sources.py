"""Read frozen stock sources into research bars; no cache or network side effects."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import date, datetime, time
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

from lei_signal.research.high52_revalidation import adapt_back_adjusted

_CN_CALENDAR = Path(
    "/Volumes/win+mac通用/LeiSignal-新实验结果/lowfreq-expanded-discovery-20261019/"
    "lowfreq-expanded-discovery-20261019-20261019T013345-d1a1ec5ca080/"
    "result/probe/trade_dates.json"
)
_US_CONTRACT = Path(__file__).resolve().parents[3] / (
    "docs/experiments/raw/stock-universe-expansion-2026-10-15/bulk-contract.json"
)


def _bound_json(binding: dict) -> dict:
    path = Path(binding["path"])
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != binding["sha256"]:
        raise ValueError(f"source hash changed: {path}")
    return json.loads(raw)


def _calendar(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("fields") != ["calendar_date", "is_trading_day"]:
        raise ValueError("unexpected calendar schema")
    days = [day for day, flag in payload["data"] if flag == "1"]
    if days != sorted(set(days)):
        raise ValueError("calendar dates unordered or duplicated")
    return days


def load_historical_cn(manifest_path: str | Path, calendar_path: str | Path | None = None) -> dict:
    """Load only the SHA-bound historical 300 cohort; never include the old 600."""
    manifest_file = Path(manifest_path)
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    assets = manifest.get("asset_sources")
    if not isinstance(assets, dict) or len(assets) != 300:
        raise ValueError("expected frozen historical 300-stock source manifest")
    calendar = _calendar(Path(calendar_path) if calendar_path else _CN_CALENDAR)
    bars, universe, failures, priced = [], [], {}, 0
    for code, pair in sorted(assets.items()):
        daily = _bound_json(pair["daily"])
        actions = _bound_json(pair["adjustments"])
        adapted = adapt_back_adjusted(daily, actions, code, calendar,
                                      factor_field="foreAdjustFactor")
        broken = set(adapted["break_dates"])
        universe.append({"symbol": code, "name": code, "market": "CN"})
        if adapted["failures"]:
            failures[code] = adapted["failures"]
        if adapted["rows"]:
            priced += 1
        included_days = set()
        for row in adapted["rows"]:
            included_days.add(row["date"])
            traded = row["tradestatus"] == "1"
            is_st = row["isST"] == "1"
            valid = row["date"] not in broken
            bars.append({"symbol": code, "date": row["date"],
                         "open": float(row["open"]) if row["open"] else None,
                         "close": float(row["close"]),
                         "volume": float(row["volume"] or 0),
                         "valid": valid, "tradable": valid and traded,
                         "eligible_buy": valid and traded and not is_st,
                         "open_tradable": valid and traded,
                         "open_buy_allowed": valid and traded and not is_st,
                         "is_st": is_st, "source_break": not valid,
                         "tradestatus": row["tradestatus"]})
        for day, raw in adapted["raw_by_day"].items():
            if day in included_days:
                continue
            bars.append({"symbol": code, "date": day, "open": None, "close": None,
                         "volume": float(raw["volume"] or 0), "valid": False,
                         "tradable": False, "eligible_buy": False,
                         "open_tradable": False, "open_buy_allowed": False,
                         "is_st": raw["isST"] == "1", "source_break": True,
                         "tradestatus": raw["tradestatus"]})
    bars.sort(key=lambda row: (row["symbol"], row["date"]))
    return {"bars": bars, "universe": universe,
            "metadata": {"market": "CN", "cohort": "historical_2014_fixed300",
                         "intended_symbols": 300, "priced_symbols": priced,
                         "price_basis": (
                             "BaoStock raw OHLC times effective foreAdjustFactor; research units"
                         ),
                         "current_membership_bias": False,
                         "execution_status_basis": (
                             "BaoStock full-day tradestatus is only an open-session proxy"
                         ),
                         "source_manifest": str(manifest_file), "source_failures": failures}}


def _market_spec(market: str) -> tuple[ZoneInfo, str, time]:
    if market == "US":
        return ZoneInfo("America/New_York"), "USD", time(16, 15)
    if market == "CN":
        return ZoneInfo("Asia/Shanghai"), "CNY", time(15, 15)
    raise ValueError("unsupported market")


def _aware_received(received_at: str | datetime, market: str) -> datetime:
    value = datetime.fromisoformat(received_at) if isinstance(received_at, str) else received_at
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("received_at must include timezone")
    return value.astimezone(_market_spec(market)[0])


def completed_market_date(market: str, received_at: str | datetime) -> str:
    """Last date eligible for a confirmed close in the market's local time."""
    from datetime import timedelta

    local = _aware_received(received_at, market)
    cutoff = _market_spec(market)[2]
    last_day = local.date() if local.time() >= cutoff else local.date() - timedelta(days=1)
    return last_day.isoformat()


def proposed_session_open(market: str, day: str | date) -> str:
    """Timestamp for a proposed open; the caller must verify the trading calendar."""
    local_day = date.fromisoformat(day) if isinstance(day, str) else day
    if not isinstance(local_day, date) or isinstance(local_day, datetime):
        raise ValueError("expected calendar date")
    zone = _market_spec(market)[0]
    return datetime.combine(local_day, time(9, 30), tzinfo=zone).isoformat()


def parse_yahoo_history(payload: dict, symbol: str, received_at: str | datetime) -> dict:
    """Parse Yahoo chart data without treating an unfinished session as a close.

    Yahoo quote OHLC is split adjusted in its own chart semantics, and is not
    historical share-face price. Adjclose also includes Yahoo dividend scaling.
    """
    market = "CN" if symbol.endswith((".SS", ".SZ")) else "US"
    timezone, currency, _ = _market_spec(market)
    received = _aware_received(received_at, market)
    chart = payload.get("chart") or {}
    results = chart.get("result") or []
    if chart.get("error") or len(results) != 1:
        raise ValueError("Yahoo chart unavailable")
    result = results[0]
    meta = result.get("meta") or {}
    if meta.get("symbol") != symbol or meta.get("currency") != currency:
        raise ValueError("Yahoo symbol or currency mismatch")
    if meta.get("exchangeTimezoneName") != timezone.key:
        raise ValueError("Yahoo exchange timezone mismatch")
    timestamps = result.get("timestamp") or []
    indicators = result.get("indicators") or {}
    quotes = indicators.get("quote") or []
    adjusted = indicators.get("adjclose") or []
    if len(quotes) != 1 or len(adjusted) != 1:
        raise ValueError("Yahoo quote/adjclose missing")
    q, adj = quotes[0], adjusted[0].get("adjclose") or []
    fields = (q.get("open") or [], q.get("high") or [], q.get("low") or [],
              q.get("close") or [], q.get("volume") or [], adj)
    if any(len(field) != len(timestamps) for field in fields):
        raise ValueError("Yahoo indicator lengths differ")
    bars, skipped, previous = [], [], ""
    for i, stamp in enumerate(timestamps):
        day = datetime.fromtimestamp(stamp, timezone).date().isoformat()
        if day <= previous:
            raise ValueError("Yahoo dates unordered or duplicated")
        previous = day
        if day > received.date().isoformat():
            raise ValueError("Yahoo future bar")
        if day > completed_market_date(market, received):
            skipped.append({"date": day, "reason": "close_not_complete"})
            continue
        raw_open, raw_high, raw_low, raw_close, volume, adjusted_close = (
            field[i] for field in fields
        )
        prices = (raw_open, raw_high, raw_low, raw_close, adjusted_close)
        if (any(not isinstance(x, (int, float)) or not math.isfinite(x) for x in prices)
                or min(prices) <= 0
                or raw_low > min(raw_open, raw_close)
                or raw_high < max(raw_open, raw_close)
                or (volume is not None and (
                    not isinstance(volume, (int, float))
                    or not math.isfinite(volume) or volume < 0
                ))):
            skipped.append({"date": day, "reason": "missing_or_invalid_price"})
            continue
        ratio = adjusted_close / raw_close
        if not math.isfinite(ratio) or ratio <= 0:
            skipped.append({"date": day, "reason": "invalid_adjustment_ratio"})
            continue
        observed_volume_positive = volume > 0 if volume is not None else None
        bars.append({"symbol": symbol, "date": day, "source_date": day,
                     "raw_open": float(raw_open), "raw_high": float(raw_high),
                     "raw_low": float(raw_low), "raw_close": float(raw_close),
                     "open": float(raw_open * ratio), "high": float(raw_high * ratio),
                     "low": float(raw_low * ratio), "close": float(adjusted_close),
                     "volume": float(volume) if volume is not None else None,
                     "observed_volume_positive": observed_volume_positive,
                     "valid": True, "tradable": None,
                     "eligible_buy": False if observed_volume_positive is False else None,
                     "open_tradable": None, "open_buy_allowed": None,
                     "adjustment_ratio": float(ratio)})
    events = result.get("events") or {}
    return {"bars": bars, "events": {"dividends": events.get("dividends") or {},
                                     "splits": events.get("splits") or {}},
            "metadata": {"symbol": symbol, "market": market,
                         "currency": currency, "timezone": timezone.key,
                         "received_at": received.isoformat(),
                         "last_completed_date": bars[-1]["date"] if bars else None,
                         "source_rows": len(timestamps), "retained_rows": len(bars),
                         "skipped": skipped,
                         "st_status": "unknown", "limit_status": "unknown",
                         "suspension_status": "unknown", "open_execution_status": "unknown",
                         "price_basis": (
                             "Yahoo split-adjusted quote and dividend-adjusted close; "
                             "research units"
                         )}}


def load_historical_us(raw_directory: str | Path) -> dict:
    """Load every IVV equity in the frozen contract, retaining failed symbols."""
    directory = Path(raw_directory)
    contract = json.loads(_US_CONTRACT.read_text(encoding="utf-8"))
    symbols = contract["selection"]["us"]
    attempts = {}
    for line in (directory / "attempts.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["code"] in attempts:
            raise ValueError("duplicate Yahoo attempt")
        attempts[row["code"]] = row
    if len(symbols) != 504 or set(attempts) != {s["code"] for s in symbols}:
        raise ValueError("incomplete frozen IVV cohort")
    bars, universe, missing = [], [], {}
    for member in symbols:
        symbol = member["code"]
        universe.append({"symbol": symbol, "name": member.get("name") or symbol,
                         "market": "US"})
        attempt = attempts[symbol]
        if attempt.get("status") != "ok":
            missing[symbol] = attempt.get("status") or "unavailable"
            continue
        path = directory / attempt["file"]
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != attempt["sha256"]:
            raise ValueError(f"Yahoo source hash changed: {symbol}")
        parsed = parse_yahoo_history(json.loads(raw), symbol, attempt["retrieved_at"])
        if not parsed["bars"]:
            missing[symbol] = "empty_price_history"
        bars.extend(parsed["bars"])
    bars.sort(key=lambda row: (row["symbol"], row["date"]))
    return {"bars": bars, "universe": universe,
            "metadata": {"market": "US", "cohort": "IVV_equity_2026-10-13",
                         "intended_symbols": len(symbols),
                         "priced_symbols": len(symbols) - len(missing),
                         "missing_symbols": missing, "current_membership_bias": True,
                         "official_historical_sp500_membership": False,
                         "source_directory": str(directory),
                         "price_basis": (
                             "Yahoo adjusted research units, not executable historical shares"
                         )}}


def fetch_yahoo_history(symbol: str, range: str = "2y", timeout: float = 15) -> dict:
    """Make exactly one chart request; caller must persist returned raw bytes."""
    import urllib.request

    if not symbol or not symbol.replace("-", "").replace(".", "").isalnum():
        raise ValueError("invalid Yahoo symbol")
    if range not in {"1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"}:
        raise ValueError("unsupported range")
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}"
           f"?interval=1d&range={range}&events=div%2Csplits")
    request = urllib.request.Request(url, headers={"User-Agent": "LeiSignal/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
    return {"payload": json.loads(raw), "raw": raw,
            "retrieved_at": datetime.now(ZoneInfo("UTC")).isoformat(),
            "source_url": url, "raw_hash": hashlib.sha256(raw).hexdigest()}


def cn_to_yahoo_symbol(symbol: str) -> str:
    prefix, dot, code = symbol.partition(".")
    if dot != "." or len(code) != 6 or not code.isdigit() or prefix not in {"sh", "sz"}:
        raise ValueError("expected sh. or sz. plus six digits")
    return f"{code}.{'SS' if prefix == 'sh' else 'SZ'}"
