"""Small, read-only public-data adapter; receipt times are never backdated.

Tencent quotes are indicative, not exchange execution reports. Yahoo daily bars
and corporate actions are a second vendor record, not an exchange certification.
Missing action coverage blocks account valuation and execution in the service.
"""

from __future__ import annotations

import hashlib
import math
from datetime import datetime, time
from zoneinfo import ZoneInfo

import requests

from .models import digest, instant

SHANGHAI = ZoneInfo("Asia/Shanghai")
SYMBOL = "510300.SS"
HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://gu.qq.com/"}


def clock() -> datetime:
    return datetime.now(SHANGHAI)


def number(value, *, positive=False):
    try:
        result = float(value)
    except (ValueError, TypeError):
        return None
    if not math.isfinite(result) or (positive and result <= 0):
        return None
    return result


def session_time(at: datetime) -> bool:
    """Time window only; a fresh same-day quote is also required by the service."""
    local = at.astimezone(SHANGHAI)
    t = local.time().replace(tzinfo=None)
    return local.weekday() < 5 and (time(9, 30) <= t < time(11, 30) or time(13) <= t < time(15))


def parse_tencent(raw: bytes, received_at: str) -> dict:
    received = instant(received_at).astimezone(SHANGHAI)
    text = raw.decode("gbk")
    if not text.startswith('v_sh510300="') or not text.rstrip().endswith('";'):
        raise ValueError("unexpected quote identity or envelope")
    parts = text.split('"', 2)[1].split("~")
    if len(parts) < 35 or parts[2] != "510300":
        raise ValueError("quote fields or symbol missing")
    source = datetime.strptime(parts[30], "%Y%m%d%H%M%S").replace(tzinfo=SHANGHAI)
    last, bid, ask = (number(parts[k], positive=True) for k in (3, 9, 19))
    reasons = []
    if last is None:
        reasons.append("last_missing_or_invalid")
    if bid is None or ask is None or bid > ask:
        reasons.append("bid_ask_missing_or_crossed")
    if source > received:
        reasons.append("source_time_in_future")
    # Vendor depth quantities are reported in lots. This declared conversion is
    # a simulation assumption, not a guarantee that those shares can be filled.
    bid_lots, ask_lots = (number(parts[k]) for k in (10, 20))
    result = {
        "symbol": SYMBOL,
        "name": parts[1],
        "source": "Tencent indicative L1",
        "source_time": source.isoformat(),
        "received_at": received.isoformat(),
        "last": last,
        "bid": bid,
        "ask": ask,
        "bid_size": bid_lots * 100 if bid_lots is not None and bid_lots >= 0 else None,
        "ask_size": ask_lots * 100 if ask_lots is not None and ask_lots >= 0 else None,
        "depth_unit": "reported_lots_x_100_shares",
        "market_open": session_time(source)
        and session_time(received)
        and source.date() == received.date(),
        "quality": "valid" if not reasons else "invalid",
        "reasons": reasons,
        "source_hash": hashlib.sha256(raw).hexdigest(),
        "source_url": "https://qt.gtimg.cn/q=sh510300",
        "raw_quote": text.strip(),
        "is_eod": False,
        "corporate_actions_checked_from": None,
        "corporate_actions_checked_through": None,
        "corporate_actions": [],
    }
    return result


def parse_daily(payload: dict, received_at: str) -> dict:
    """Normalize vendor action coverage and a completed same-day daily close.

    A daily bar timestamp identifies its session start. Its conservative end
    time is 15:00 Shanghai. We only publish it after 16:30, with vendor market
    time confirming completion. Adjusted closes are deliberately not used.
    """
    received = instant(received_at).astimezone(SHANGHAI)
    chart = payload.get("chart") or {}
    records = chart.get("result") or []
    if chart.get("error") or len(records) != 1:
        raise ValueError("daily source unavailable")
    data = records[0]
    meta = data.get("meta") or {}
    if meta.get("symbol") != SYMBOL or meta.get("currency") != "CNY":
        raise ValueError("daily source identity or currency mismatch")
    if meta.get("exchangeTimezoneName") != "Asia/Shanghai":
        raise ValueError("daily source timezone mismatch")
    timestamps = data.get("timestamp") or []
    quotes = data.get("indicators", {}).get("quote") or [{}]
    closes = quotes[0].get("close") or []
    if len(timestamps) != len(closes) or not timestamps:
        raise ValueError("daily time/price coverage missing")
    market_time = datetime.fromtimestamp(meta["regularMarketTime"], SHANGHAI)
    if market_time > received:
        raise ValueError("daily source future market time")
    valid = [
        (datetime.fromtimestamp(ts, SHANGHAI), number(close, positive=True))
        for ts, close in zip(timestamps, closes, strict=True)
        if ts <= received.timestamp() and number(close, positive=True) is not None
    ]
    if not valid:
        raise ValueError("no valid daily bars")
    bar_at, close = max(valid, key=lambda x: x[0])
    through = min(bar_at.date(), market_time.date()).isoformat()
    actions = []
    for kind, rows in (data.get("events") or {}).items():
        if kind not in {"dividends", "splits"}:
            continue
        for key, row in rows.items():
            ex = datetime.fromtimestamp(row["date"], SHANGHAI).date().isoformat()
            if ex > through:
                continue
            action = {
                "id": f"yahoo:{SYMBOL}:{kind}:{key}",
                "ex_date": ex,
                "pay_date": None,
                "source": "Yahoo chart corporate actions",
            }
            if kind == "dividends":
                amount = number(row.get("amount"), positive=True)
                if amount is None:
                    raise ValueError("invalid dividend amount")
                action.update(type="cash_dividend", amount=amount)
            else:
                numerator, denominator = (
                    number(row.get(k), positive=True) for k in ("numerator", "denominator")
                )
                if numerator is None or denominator is None:
                    raise ValueError("invalid split ratio")
                action.update(type="split", ratio=numerator / denominator)
            actions.append(action)
    end = datetime.combine(bar_at.date(), time(15), SHANGHAI)
    completed = (
        bar_at.date() == received.date()
        and received.time().replace(tzinfo=None) >= time(16, 30)
        and market_time >= end
        and received.weekday() < 5
    )
    return {
        "from": min(row[0].date() for row in valid).isoformat(),
        "through": through,
        "actions": actions,
        "source_hash": digest(payload),
        "completed_close": {"source_time": end.isoformat(), "last": close} if completed else None,
        "coverage_note": "供应商本次返回的覆盖日期；分红到账日期未知，不计为可用现金。",
    }


def collect(config: dict) -> list[dict]:
    assets = config.get("assets") or []
    if len(assets) != 1 or assets[0].get("symbol") != SYMBOL:
        raise ValueError("collector supports the frozen 510300.SS observation only")
    response = requests.get("https://qt.gtimg.cn/q=sh510300", headers=HEADERS, timeout=20)
    response.raise_for_status()
    quote = parse_tencent(response.content, clock().isoformat())
    try:
        # One year keeps action coverage ahead of a normal running account. The
        # service also detects receipt gaps and does not infer missed entitlements.
        daily_response = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{SYMBOL}",
            params={"range": "1y", "interval": "1d", "events": "div,splits"},
            headers=HEADERS,
            timeout=20,
        )
        daily_response.raise_for_status()
        daily_at = clock().isoformat()
        daily = parse_daily(daily_response.json(), daily_at)
        quote.update(
            corporate_actions_checked_from=daily["from"],
            corporate_actions_checked_through=daily["through"],
            corporate_actions=daily["actions"],
            corporate_actions_source_hash=daily["source_hash"],
            corporate_actions_received_at=daily_at,
            corporate_actions_coverage_note=daily["coverage_note"],
        )
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        daily = None
        quote["corporate_actions_error"] = f"{type(exc).__name__}: {exc}"
    # The entire input is only usable when both sources have arrived.
    quote["received_at"] = clock().isoformat()
    quote["id"] = "quote:" + digest(quote)
    observations = [quote]
    if daily and daily["completed_close"]:
        eod = {
            **quote,
            **daily["completed_close"],
            "source": "Yahoo completed daily close",
            "source_url": f"https://query1.finance.yahoo.com/v8/finance/chart/{SYMBOL}",
            "source_hash": daily["source_hash"],
            "market_open": False,
            "is_eod": True,
            "bid": None,
            "ask": None,
            "bid_size": None,
            "ask_size": None,
            "quality": "valid",
            "reasons": [],
            "raw_quote": None,
        }
        eod.pop("id")
        eod["id"] = "close:" + digest(eod)
        # Earlier close first; source clocks must never move account state back.
        observations = [eod, quote]
    return observations
