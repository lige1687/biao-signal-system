"""MSCI's public end-of-day XLS export, kept in a local personal-view cache.

The route and arguments are documented by the old official chart's APIRequest.js.
No credentials, ETF substitution, interpolation, scheduler or model calls.
"""
from __future__ import annotations

import hashlib
import json
import math
import statistics
import threading
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

SOURCE = "https://app2.msci.com/products/index-data-search/"
ENDPOINT = "https://app2.msci.com/products/service/index/indexmaster/downloadLevelData"
INDEXES = [
    ("world", "990100", "MSCI World", "WORLD Standard (Large+Mid Cap)"),
    ("momentum", "703755", "动量", "WORLD MOMENTUM Standard (Large+Mid Cap)"),
    ("quality", "702787", "质量", "WORLD QUALITY Standard (Large+Mid Cap)"),
    ("value", "105868", "价值", "WORLD VALUE Standard (Large+Mid Cap)"),
    ("minimumVolatility", "129896", "最小波动", "WORLD MINIMUM VOLATILITY (USD) Standard (Large+Mid Cap)"),
]
CACHE = Path(__file__).resolve().parents[3] / ".codex/market-style-observation-20261020/daily-history-cache.json"
_LOCK = threading.Lock()
_MEMORY: dict | None = None
_RETRY_AFTER = 0.0
_LAST_ERROR = False
MAX_BYTES = 2_000_000


def export_url(today: date) -> str:
    return ENDPOINT + "?" + urlencode({
        "output": "INDEX_LEVELS", "currency_symbol": "USD", "index_variant": "GRTR",
        "start_date": (today - timedelta(days=1100)).strftime("%Y%m%d"),
        "end_date": today.strftime("%Y%m%d"), "data_frequency": "daily",
        "index_codes": ",".join(item[1] for item in INDEXES),
    })


def parse_export_rows(rows: list[list], *, requested_end: date) -> list[dict]:
    """Reject wrong variants/identities; retain missing values, never fill a path."""
    if not any(row[:2] == ["Index Level :", "Gross"] for row in rows):
        raise ValueError("expected_gross_total_return")
    if not any(row[:2] == ["Currency :", "USD"] for row in rows):
        raise ValueError("expected_usd")
    headers = [i for i, row in enumerate(rows) if row and row[0] == "Date"]
    if len(headers) != 1:
        raise ValueError("invalid_date_header")
    start = headers[0]
    header = rows[start]
    expected = {item[3] for item in INDEXES}
    if len(header) != 6 or set(header[1:]) != expected:
        raise ValueError("index_identity_mismatch")
    columns = {item[0]: header.index(item[3]) for item in INDEXES}
    points = []
    for row in rows[start + 1:]:
        if not row or not row[0]:
            break  # The official workbook ends its data table before the disclosures.
        day = datetime.strptime(str(row[0]), "%b %d, %Y").date()
        if day > requested_end or day.weekday() >= 5:
            raise ValueError("invalid_observation_date")
        point = {"date": day.isoformat()}
        for key, column in columns.items():
            raw = row[column] if column < len(row) else None
            if raw in (None, "", "N/A", "NA", "-", "--"):
                point[key] = None
            else:
                value = float(str(raw).replace(",", ""))
                if not math.isfinite(value) or value <= 0:
                    raise ValueError("invalid_index_level")
                point[key] = value
        points.append(point)
    if len(points) < 2 or [p["date"] for p in points] != sorted({p["date"] for p in points}):
        raise ValueError("duplicate_unsorted_or_empty_dates")
    return points


def parse_export(raw: bytes, *, requested_end: date) -> list[dict]:
    import xlrd  # optional preview dependency, listed in requirements-preview.txt
    if not raw.startswith(bytes.fromhex("d0cf11e0a1b11ae1")) or len(raw) > MAX_BYTES:
        raise ValueError("expected_xls_not_html")
    sheet = xlrd.open_workbook(file_contents=raw).sheet_by_index(0)
    return parse_export_rows([sheet.row_values(i) for i in range(sheet.nrows)], requested_end=requested_end)


def store_export(raw: bytes, *, requested_end: date, source_url: str, retrieved_at: str) -> dict:
    points = parse_export(raw, requested_end=requested_end)
    payload = {"schema": 1, "currency": "USD", "variant": "GRTR", "frequency": "daily",
               "points": points, "source_url": source_url, "retrieved_at": retrieved_at,
               "request_date": requested_end.isoformat(), "source_sha256": hashlib.sha256(raw).hexdigest(),
               "fingerprint": hashlib.sha256(json.dumps(points, sort_keys=True).encode()).hexdigest()}
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    temporary = CACHE.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False))
    temporary.replace(CACHE)
    return payload


def get_history() -> dict:
    """At most one successful refresh per UTC date, only when the page is read."""
    global _MEMORY, _RETRY_AFTER, _LAST_ERROR
    today = datetime.now(timezone.utc).date()
    with _LOCK:
        if _MEMORY is None and CACHE.exists():
            try:
                saved = json.loads(CACHE.read_text())
                fingerprint = hashlib.sha256(json.dumps(saved["points"], sort_keys=True).encode()).hexdigest()
                if (saved.get("schema"), saved.get("currency"), saved.get("variant"), saved.get("frequency")) != (1, "USD", "GRTR", "daily") or saved.get("fingerprint") != fingerprint:
                    raise ValueError("invalid_cache")
                _MEMORY = saved
            except (OSError, ValueError, KeyError, TypeError):
                _MEMORY = None
        if (_MEMORY is None or _MEMORY.get("request_date") != today.isoformat()) and time.monotonic() >= _RETRY_AFTER:
            try:
                url = export_url(today)
                with urlopen(url, timeout=20) as response:
                    raw = response.read(MAX_BYTES + 1)
                _MEMORY = store_export(raw, requested_end=today, source_url=url,
                                       retrieved_at=datetime.now(timezone.utc).isoformat())
                _LAST_ERROR = False
            except Exception:
                # Retain a previously verified cache, but expose the failed refresh.
                _LAST_ERROR = True
                _RETRY_AFTER = time.monotonic() + 300
        if _MEMORY is None:
            return {"available": False, "error": "日线来源暂时不可读，未用年度点替代。", "source_url": SOURCE}
        return {**_MEMORY, "available": True, "refresh_failed": _LAST_ERROR}


def build_window(history: dict, days: int = 365) -> dict:
    if days not in (90, 365, 1095):
        raise ValueError("invalid_window")
    if not history.get("available"):
        return history
    all_points = history["points"]
    complete = [p for p in all_points if all(p[k] is not None for k, *_ in INDEXES)]
    if len(complete) < 2:
        return {"available": False, "error": "五个指数没有足够的共同有效日。"}
    end = complete[-1]["date"]
    cutoff = (date.fromisoformat(end) - timedelta(days=days)).isoformat()
    base = next((p for p in complete if p["date"] >= cutoff), None)
    if base is None or base["date"] == end:
        return {"available": False, "error": "所选区间资料不足。"}
    points = [p for p in all_points if base["date"] <= p["date"] <= end]
    parent_return = complete[-1]["world"] / base["world"] - 1
    series = []
    for key, code, name, _ in INDEXES:
        wealth = [p[key] / base[key] * 100 if p[key] is not None else None for p in points]
        relative = [w / (p["world"] / base["world"]) if w is not None and p["world"] is not None else None for w, p in zip(wealth, points)]
        returns = [b / a - 1 for a, b in zip(wealth, wealth[1:]) if a is not None and b is not None]
        peak = wealth[0]
        drawdowns = []
        for value in wealth:
            if value is not None:
                peak = max(peak, value)
                drawdowns.append(value / peak - 1)
        total = wealth[-1] / 100 - 1
        complete_path = all(value is not None for value in wealth)
        series.append({"id": key, "code": code, "name": name, "wealth": wealth, "relative": relative,
                       "return_pct": total * 100, "excess_pp": (total - parent_return) * 100,
                       "volatility_pct": statistics.stdev(returns) * math.sqrt(252) * 100 if complete_path and len(returns) > 1 else None,
                       "max_drawdown_pct": min(drawdowns) * 100 if complete_path else None,
                       "current_drawdown_pct": drawdowns[-1] * 100 if complete_path else None,
                       "missing_points": sum(value is None for value in wealth)})
    age = (datetime.now(timezone.utc).date() - date.fromisoformat(end)).days
    return {"available": True, "currency": "USD", "variant": "GRTR", "frequency": "daily",
            "days": days, "start": base["date"], "end": end, "dates": [p["date"] for p in points], "series": series,
            "point_count": len(points), "full_history_start": all_points[0]["date"],
            "latest_source_date": all_points[-1]["date"], "latest_common_date": end,
            "stale": age > 4, "refresh_failed": history.get("refresh_failed", False),
            "retrieved_at": history["retrieved_at"], "source_url": history["source_url"],
            "fingerprint": history["fingerprint"], "source_sha256": history["source_sha256"]}


def daily_style_card(view: dict) -> dict | None:
    if not view.get("available"):
        return None
    styles = [s for s in view["series"] if s["id"] != "world"]
    comparisons = "、".join(f'{s["name"]}{s["excess_pp"]:+.2f}' for s in styles)
    return {"id": "world_style", "topic": "style", "available": True, "data_date": view["end"],
            "fact": f'{view["start"]}至{view["end"]}，四种全球风格相对MSCI World收益差额为{comparisons}个百分点。',
            "reading": "同日期、美元、含股息的日收盘指数；正差额表示这一段跑赢母指数，领先不保证延续。",
            "watch": "区间不同可能改变排序；行业与估值仍按单独标明的月末资料，日线没有解释收益来自哪些股票。" + (" 当前日线更新失败或日期落后，先核资料日。" if view.get("stale") or view.get("refresh_failed") else ""),
            "source_ids": ["msci_daily"]}
