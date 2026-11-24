"""On-demand, source-labelled NAV history for one exact portfolio holding.

Fund NAV is a dated line series. Industry ETFs are context only; neither is
converted into a fund candlestick or a trading rule result.
"""

from __future__ import annotations

import json
import math
import re
import threading
import time
import urllib.parse
import urllib.request
from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException, Request

from lei_signal.api.portfolio_workspace import build_workspace
from lei_signal.portfolio.funddata import NavPoint

_SHANGHAI = ZoneInfo("Asia/Shanghai")
_SOURCE = "天天基金公开单位净值历史"
_SOURCE_REF = "https://api.fund.eastmoney.com/f10/lsjz"
_SLOTS = threading.BoundedSemaphore(2)
_LOCK = threading.Lock()
# A per-process, per-code daily attempt, including failures. Never persists
# account data or fetches other holdings just because the board was opened.
_CACHE: dict[str, dict] = {}
_IN_FLIGHT: set[str] = set()


def _now() -> datetime:
    return datetime.now(_SHANGHAI)


def _valid_day(value: object, today: date) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return value if parsed.isoformat() == value and parsed <= today else None


def _points(rows: object, today: date) -> list[dict]:
    """Use finite positive same-day-or-earlier unit NAV, once per date."""
    by_day: dict[str, float] = {}
    for row in rows or ():
        day = _valid_day(getattr(row, "date", None), today)
        value = getattr(row, "unit_nav", None)
        if day is None or isinstance(value, bool) or not isinstance(value, (float, int)):
            continue
        if not math.isfinite(value) or value <= 0:
            continue
        # Provider returns newest first. Retain its first observation of a day.
        by_day.setdefault(day, float(value))
    return [{"date": day, "value": by_day[day]} for day in sorted(by_day)]


def _fallback_nav(item: dict, today: date) -> list[dict]:
    nav = item.get("nav") or {}
    day = _valid_day(nav.get("date"), today)
    value = nav.get("value")
    if (
        day
        and isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value > 0
    ):
        return [{"date": day, "value": float(value)}]
    return []


def _fetch_page(code: str, page: int, timeout: float) -> list[NavPoint]:
    """Read one public HTTPS page using the existing NAV date/value fields."""
    url = f"{_SOURCE_REF}?fundCode={urllib.parse.quote(code)}&pageIndex={page}&pageSize=20"
    request = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://fund.eastmoney.com/"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    if payload.get("ErrCode") != 0:
        raise ValueError("NAV provider returned an error")
    batch = []
    for item in (payload.get("Data") or {}).get("LSJZList") or []:
        try:
            batch.append(NavPoint(date=item["FSRQ"], unit_nav=float(item["DWJZ"])))
        except (KeyError, TypeError, ValueError):
            continue
    return batch


def _fetch_nav_180(code: str) -> tuple[list[NavPoint], str | None]:
    """Read at most nine serial 20-point pages within 20 seconds total.

    The source caps ``PageSize`` at 20 even when a larger size is requested.
    Every page uses the same HTTPS endpoint and the original FSRQ/DWJZ fields.
    """
    deadline = time.monotonic() + 20
    rows: list[NavPoint] = []
    for page in range(1, 10):
        try:
            if page > 1:
                if deadline - time.monotonic() <= 0.8:
                    raise TimeoutError("180-point NAV request exceeded 20 seconds")
                time.sleep(0.8)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("180-point NAV request exceeded 20 seconds")
            batch = _fetch_page(code, page, remaining)
            if not batch:
                break
            rows.extend(batch)
            if len(batch) < 20:
                break
        except (OSError, TimeoutError, ValueError, TypeError) as exc:
            if not rows:
                raise
            return rows[:180], f"历史净值只取得{len(rows)}日：{type(exc).__name__}"
    return rows[:180], None


def _fetch(code: str, now: datetime, *, refresh: bool) -> dict:
    today = now.date().isoformat()
    with _LOCK:
        previous = _CACHE.get(code)
        if previous and previous["day"] == today and not refresh:
            return dict(previous)
        if code in _IN_FLIGHT:
            return {
                "day": today,
                "points": previous["points"] if previous else [],
                "fetched_at": previous["fetched_at"] if previous else None,
                "error": "同一基金净值正在读取，请稍后重试",
            }
        # A busy provider is a temporary visible gap, not a reason to queue
        # an unbounded number of remote calls.
        if not _SLOTS.acquire(blocking=False):
            return {
                "day": today,
                "points": previous["points"] if previous else [],
                "fetched_at": previous["fetched_at"] if previous else None,
                "error": "净值来源正忙，请稍后重试",
            }
        _IN_FLIGHT.add(code)
    try:
        try:
            rows, page_error = _fetch_nav_180(code)
            points = _points(rows, now.date())
            error = page_error or (None if len(points) >= 2 else "来源返回的有效历史净值不足两日")
        except Exception as exc:  # provider/network failure stays a data gap
            points = []
            error = f"净值来源读取失败：{type(exc).__name__}"
        attempted_at = _now().isoformat()
        with _LOCK:
            prior = _CACHE.get(code)
            # Preserve a previous real series if today's attempted refresh fails.
            retained = points if len(points) >= 2 else (prior["points"] if prior else points)
            entry = {
                "day": today,
                "points": retained,
                "fetched_at": attempted_at
                if len(points) >= 2
                else (prior["fetched_at"] if prior else attempted_at),
                "error": error,
            }
            _CACHE[code] = entry
            return dict(entry)
    finally:
        with _LOCK:
            _IN_FLIGHT.discard(code)
        _SLOTS.release()


def market_holding(request: Request, holding_id: str, *, refresh: bool = False) -> dict:
    """Read one real holding identity, then at most one 180-point NAV request."""
    if not re.fullmatch(r"[0-9a-f]{12}", holding_id):
        raise HTTPException(422, "持仓编号格式无效")
    workspace = build_workspace(request)
    item = next(
        (row for row in workspace.get("items") or [] if row.get("holding_id") == holding_id), None
    )
    if item is None:
        raise HTTPException(404, "持仓不存在")
    code = item.get("code")
    if not isinstance(code, str) or not re.fullmatch(r"\d{6}", code):
        raise HTTPException(422, "该持仓没有可核的基金代码")
    now = _now()
    result = _fetch(code, now, refresh=refresh)
    points = result["points"] or _fallback_nav(item, now.date())
    historical = len(points) >= 2
    latest = points[-1] if points else None
    error = result["error"]
    recorded = _fallback_nav(item, now.date())
    if latest and recorded and latest["date"] < recorded[0]["date"]:
        gap = (
            f"公开历史净值末日{latest['date']}早于持仓台账已记录的"
            f"{recorded[0]['date']}，走势资料待更新"
        )
        error = f"{error}；{gap}" if error else gap
    status = "available" if historical and not error else "stale" if points else "unavailable"
    refs = []
    for row in (item.get("industry_reference") or {}).get("references") or []:
        symbol = row.get("symbol")
        name = row.get("name")
        if not isinstance(symbol, str) or not symbol or not isinstance(name, str) or not name:
            continue
        technical = row.get("technical") or {}
        refs.append(
            {
                "symbol": symbol,
                "name": name,
                "relation": "已披露持仓业务的行业ETF参照，不能代替本基金买卖信号",
                "as_of": _valid_day(technical.get("as_of"), now.date()),
            }
        )
    disclosure = item.get("disclosure") or {}
    report_date = _valid_day(disclosure.get("report_date"), now.date())
    published_at = _valid_day(disclosure.get("published_at"), now.date())
    coverage = disclosure.get("coverage_pct")
    if (
        not isinstance(coverage, (int, float))
        or isinstance(coverage, bool)
        or not math.isfinite(coverage)
        or not 0 <= coverage <= 100
    ):
        coverage = None
    return {
        "subject_key": f"holding:{holding_id}",
        "name": item["name"],
        "code": code,
        "nav": {
            "status": status,
            "points": points,
            "latest": latest,
            "source": _SOURCE,
            "source_ref": _SOURCE_REF + f"?fundCode={code}",
            "fetched_at": result["fetched_at"],
            "error": error,
        },
        "references": refs,
        "disclosure": {
            "report_date": report_date,
            "published_at": published_at,
            "coverage_pct": float(coverage) if coverage is not None else None,
        },
    }
