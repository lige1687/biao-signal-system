"""Prepared local market observations for opportunity narrative context.

Only preparation may call FundamentalsService. Card rendering reads a small,
dated SQLite snapshot and never starts an external request.
"""

from __future__ import annotations

import json
import math
import queue
import sqlite3
import threading
import time
from collections.abc import Iterable
from contextlib import closing
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import urlencode, urlparse
from zoneinfo import ZoneInfo

from lei_signal.api.config import sqlite_path

_SHANGHAI = ZoneInfo("Asia/Shanghai")
_TABLE = "opportunity_macro_observations"
_FETCH_WAIT_SECONDS = 45
_VALID_MARKETS = {"cn", "us"}
_LOCK = threading.Lock()
_MAX_AGE_DAYS = {"daily": 10, "weekly": 21, "monthly": 75}
_CN_MACRO = {
    "pmi": ("制造业 PMI", "", "RPT_ECONOMY_PMI"),
    "cpi": ("CPI 同比", "%", "RPT_ECONOMY_CPI"),
    "ppi": ("PPI 同比", "%", "RPT_ECONOMY_PPI"),
}
_US_MACRO_KEYS = {"icwa", "payems_yoy", "wei", "cpiaucsl_yoy", "ppiaco_yoy", "dgorder_yoy"}


def _market(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    market = value.strip().lower()
    return market if market in _VALID_MARKETS else None


def _db_path(request) -> str:
    return getattr(request.app.state, "plans_db_path", None) or sqlite_path()


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS {_TABLE} ("
        "market TEXT NOT NULL, checked_on TEXT NOT NULL, status TEXT NOT NULL, "
        "rows_json TEXT NOT NULL, checked_at TEXT, error TEXT NOT NULL DEFAULT '', "
        "started_at TEXT, "
        "PRIMARY KEY(market,checked_on))"
    )
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({_TABLE})")}
    if "started_at" not in columns:
        conn.execute(f"ALTER TABLE {_TABLE} ADD COLUMN started_at TEXT")


def _day(value: object, *, today: date) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed.isoformat() if parsed <= today else None


def _published(value: object, *, checked_at: datetime) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        if len(value) == 10:
            parsed = date.fromisoformat(value)
            return parsed.isoformat() if parsed <= checked_at.astimezone(_SHANGHAI).date() else None
        parsed_at = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed_at.tzinfo is None or parsed_at > checked_at:
            return None
        return parsed_at.isoformat()
    except ValueError:
        return None


def _public_rows(payload: dict, market: str, checked_at: datetime) -> list[dict]:
    today = checked_at.astimezone(_SHANGHAI).date()
    result: list[dict] = []
    for item in payload.get("items") or []:
        if not isinstance(item, dict) or item.get("market") != market:
            continue
        if item.get("source_access") not in {"public_web", "public_with_source_terms"}:
            continue
        url = item.get("source_url")
        if not isinstance(url, str) or urlparse(url).scheme != "https":
            continue
        observation = _day(item.get("observation_date"), today=today)
        value = item.get("value")
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            continue
        if not observation or not math.isfinite(number) or item.get("quality_status") == "missing":
            continue
        label = item.get("label")
        source = item.get("source_name")
        if not isinstance(label, str) or not label or not isinstance(source, str) or not source:
            continue
        unit = item.get("unit") if isinstance(item.get("unit"), str) else ""
        reading = item.get("reading") if isinstance(item.get("reading"), str) else ""
        published = _published(item.get("published_at"), checked_at=checked_at)
        limitations = [str(x) for x in item.get("limitations") or [] if isinstance(x, str)]
        if not published:
            limitations.append("首次公开时间未核实，不能用于历史时点判断")
        if observation != today.isoformat():
            limitations.append(f"观测日为{observation}，不代表{today.isoformat()}的实时情况")
        if item.get("quality_reason"):
            limitations.append(str(item["quality_reason"]))
        text = f"截至{observation}，{label}为{number:g}{unit}。"
        if reading:
            text += reading
        result.append(
            {
                "text": text,
                "source": source,
                "source_ref": url,
                "date": observation,
                "published_at": published,
                "report_date": observation,
                "checked_at": checked_at.isoformat(),
                "category": "fundamentals",
                "scope": "narrative",
                "public": True,
                "provenance": "local_macro_observation",
                "limitations": limitations,
                "narrative_kind": "macro",
                "relevance": "market_context",
                "market": market,
                "metric_id": item.get("metric_id"),
                "observation_date": observation,
                "fetched_at": item.get("fetched_at"),
                "quality_status": item.get("quality_status"),
                "frequency": "weekly" if item.get("metric_id") in {"naaim", "aaii"} else "daily",
            }
        )
    return result


def _observation_gaps(payload: dict, market: str, checked_at: datetime) -> list[str]:
    today = checked_at.astimezone(_SHANGHAI).date()
    no_date = sum(
        1
        for item in payload.get("items") or []
        if isinstance(item, dict)
        and item.get("market") == market
        and item.get("value") is not None
        and not _day(item.get("observation_date"), today=today)
    )
    return [f"{no_date}项来源没有可核验观察日或日期在未来，未进入公开卡片"] if no_date else []


def _treasury(service) -> dict:
    """Reuse the service's treasury cache without rates()'s full-history work."""
    from lei_signal.fundamentals import sources

    cache = service._cache
    return cache.get_or_load("treasury", 12 * 3600, sources.fetch_treasury)[0]


def _fetch_bounded(service, market: str) -> tuple[dict[str, dict], list[str]]:
    """Run three existing service calls concurrently with one 45-second deadline."""
    jobs = {
        "observations": lambda: service.observations(market),
        "treasury": lambda: _treasury(service),
        "economy": (lambda: service.macro_history(page_size=60))
        if market == "cn"
        else (lambda: service.us_macro()),
    }
    completed: queue.Queue[tuple[str, dict | None, str]] = queue.Queue()

    def run(name: str, loader) -> None:
        try:
            payload = loader()
            completed.put((name, payload if isinstance(payload, dict) else None, ""))
        except Exception as exc:
            completed.put((name, None, f"{type(exc).__name__}: {exc}"))

    for name, loader in jobs.items():
        threading.Thread(
            target=run, args=(name, loader), name=f"macro-{market}-{name}", daemon=True
        ).start()
    deadline = time.monotonic() + _FETCH_WAIT_SECONDS
    results: dict[str, dict] = {}
    errors: list[str] = []
    while len(results) + len(errors) < len(jobs):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            name, payload, error = completed.get(timeout=remaining)
        except queue.Empty:
            break
        if payload is None:
            errors.append(f"{name}: {error or '来源未返回有效结果'}")
        else:
            results[name] = payload
    for name in jobs.keys() - results.keys() - {e.split(":", 1)[0] for e in errors}:
        errors.append(f"{name}: 超过{_FETCH_WAIT_SECONDS}秒读取上限")
    return results, errors


def _series_row(
    metric_id: str,
    label: str,
    unit: str,
    value: object,
    observation: object,
    source: str,
    url: str,
    frequency: str,
    checked_at: datetime,
) -> dict | None:
    today = checked_at.astimezone(_SHANGHAI).date()
    day = _day(observation, today=today)
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not day or not math.isfinite(number):
        return None
    limits = ["首次公开时间和后续修订时点未逐期核实，不能用于历史交易回放"]
    if day != today.isoformat():
        limits.append(f"观测日为{day}，不代表{today.isoformat()}的实时情况")
    return {
        "text": f"截至{day}，{label}为{number:g}{unit}。",
        "source": source,
        "source_ref": url,
        "date": day,
        "published_at": None,
        "report_date": day,
        "checked_at": checked_at.isoformat(),
        "category": "fundamentals",
        "scope": "narrative",
        "public": True,
        "provenance": "local_macro_observation",
        "limitations": limits,
        "narrative_kind": "macro",
        "relevance": "market_context",
        "metric_id": metric_id,
        "observation_date": day,
        "fetched_at": None,
        "quality_status": "time_unverified",
        "frequency": frequency,
    }


def _economy_rows(payload: dict, market: str, checked_at: datetime) -> list[dict]:
    rows: list[dict] = []
    if market == "cn":
        for key, (label, unit, report) in _CN_MACRO.items():
            series = (payload.get("series") or {}).get(key) or {}
            dates, values = series.get("dates") or [], series.get("values") or []
            if len(dates) != len(values) or not dates:
                continue
            url = (
                "https://datacenter-web.eastmoney.com/api/data/v1/get?"
                f"reportName={report}&columns=ALL&sortColumns=REPORT_DATE&sortTypes=-1"
                "&pageSize=60&pageNumber=1&source=WEB&client=WEB"
            )
            row = _series_row(
                key,
                label,
                unit,
                values[-1],
                dates[-1],
                "东方财富经济数据",
                url,
                "monthly",
                checked_at,
            )
            if row:
                rows.append(row)
    else:
        from lei_signal.fundamentals import sources

        specs = {spec["key"]: spec for spec in sources._US_MACRO_SPEC}
        for item in payload.get("items") or []:
            if not isinstance(item, dict) or item.get("key") not in _US_MACRO_KEYS:
                continue
            spec = specs.get(item["key"])
            if not spec:
                continue
            series = (payload.get("series") or {}).get(item["key"]) or {}
            row = _series_row(
                item["key"],
                series.get("label") or item.get("label") or spec["label"],
                spec["unit"],
                item.get("value"),
                item.get("date"),
                "FRED",
                f"https://fred.stlouisfed.org/series/{spec['series']}",
                "weekly" if spec["freq"] == "周" else "monthly",
                checked_at,
            )
            if row:
                rows.append(row)
    return rows


def _treasury_rows(payload: dict, market: str, checked_at: datetime) -> list[dict]:
    from lei_signal.fundamentals import sources

    value = (payload.get(market) or {}).get(f"{market}_10y")
    day = payload.get(f"as_of_{market}")
    label = "中国10年期国债收益率" if market == "cn" else "美国10年期国债收益率"
    url = (
        sources._TREASURY_URL
        + "?"
        + urlencode(
            {
                "type": "RPTA_WEB_TREASURYYIELD",
                "sty": "ALL",
                "st": "SOLAR_DATE",
                "sr": "-1",
                "p": "1",
                "ps": "15",
                "pageNo": "1",
                "pageNum": "1",
            }
        )
    )
    row = _series_row(
        f"{market}_10y", label, "%", value, day, "东方财富国债收益率汇总", url, "daily", checked_at
    )
    return [row] if row else []


def _split_fresh(rows: list[dict], today: date) -> tuple[list[dict], list[dict]]:
    fresh, stale = [], []
    for row in rows:
        day = _day(row.get("observation_date"), today=today)
        frequency = row.get("frequency")
        max_age = _MAX_AGE_DAYS.get(frequency)
        if day and max_age is not None and (today - date.fromisoformat(day)).days <= max_age:
            fresh.append(row)
        else:
            stale.append({**row, "stale_reason": "观测日期缺失、未来或超过该指标的审慎展示窗口"})
    return fresh, stale


def prepare_macro(request, markets: Iterable[str]) -> dict[str, dict]:
    """Prepare each exact CN/US market once per Shanghai day, across products."""
    today = datetime.now(_SHANGHAI).date().isoformat()
    results: dict[str, dict] = {}
    for supplied in dict.fromkeys(markets):
        market = _market(supplied)
        if market is None:
            results[str(supplied)] = {
                "status": "unsupported",
                "rows": [],
                "error": "没有对应市场的本地观察接口",
            }
            continue
        try:
            with _LOCK, closing(sqlite3.connect(_db_path(request), timeout=2)) as conn, conn:
                _ensure_table(conn)
                inserted = conn.execute(
                    f"INSERT OR IGNORE INTO {_TABLE}"
                    "(market,checked_on,status,rows_json,started_at) "
                    "VALUES(?,?,'running','[]',?)",
                    (market, today, datetime.now(UTC).isoformat()),
                ).rowcount
        except (sqlite3.Error, OSError) as exc:
            results[market] = {
                "status": "unavailable",
                "rows": [],
                "error": f"本地缓存不可用：{exc}",
            }
            continue
        if inserted:
            try:
                from lei_signal.fundamentals.service import FundamentalsService

                service = (
                    getattr(request.app.state, "fundamentals_service", None)
                    or FundamentalsService()
                )
                payloads, errors = _fetch_bounded(service, market)
                checked_at = datetime.now(UTC)
                rows = _public_rows(payloads.get("observations") or {}, market, checked_at)
                rows += _economy_rows(payloads.get("economy") or {}, market, checked_at)
                rows += _treasury_rows(payloads.get("treasury") or {}, market, checked_at)
                errors += _observation_gaps(payloads.get("observations") or {}, market, checked_at)
                for name, payload in payloads.items():
                    errors += [f"{name}: {entry}" for entry in (payload.get("errors") or [])]
                fresh, stale = _split_fresh(rows, checked_at.astimezone(_SHANGHAI).date())
                if stale:
                    errors.append(f"{len(stale)}项观察日超过审慎展示窗口，已保留在stale_rows中")
                error = "; ".join(errors)[:1200]
                status = "ready" if fresh else "unavailable"
            except Exception as exc:
                checked_at = datetime.now(UTC)
                rows, status, error = [], "unavailable", f"{type(exc).__name__}: {exc}"
            try:
                with closing(sqlite3.connect(_db_path(request), timeout=2)) as conn, conn:
                    conn.execute(
                        f"UPDATE {_TABLE} SET status=?,rows_json=?,checked_at=?,error=? "
                        "WHERE market=? AND checked_on=?",
                        (
                            status,
                            json.dumps(rows, ensure_ascii=False),
                            checked_at.isoformat(),
                            error[:1200],
                            market,
                            today,
                        ),
                    )
            except sqlite3.Error as exc:
                results[market] = {
                    "status": "unavailable",
                    "rows": [],
                    "checked_at": checked_at.isoformat(),
                    "error": f"本地缓存写入失败：{exc}",
                }
                continue
        results[market] = read_macro(request, market, datetime.now(_SHANGHAI))
    return results


def read_macro(request, market: str, now: datetime) -> dict:
    """Read a prepared public snapshot only; old days never masquerade as today."""
    exact = _market(market)
    if exact is None:
        return {
            "status": "unsupported",
            "rows": [],
            "stale_rows": [],
            "checked_at": None,
            "error": "没有对应市场的本地观察接口",
        }
    if now.tzinfo is None:
        raise ValueError("now must have timezone information")
    checked_on = now.astimezone(_SHANGHAI).date().isoformat()
    path = Path(_db_path(request))
    if not path.is_file():
        return {
            "status": "missing",
            "rows": [],
            "stale_rows": [],
            "checked_at": None,
            "error": "尚无当日市场观察",
        }
    try:
        with closing(sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)) as conn:
            row = conn.execute(
                f"SELECT status,rows_json,checked_at,error,started_at FROM {_TABLE} "
                "WHERE market=? AND checked_on=?",
                (exact, checked_on),
            ).fetchone()
    except sqlite3.Error:
        row = None
    if row is None:
        return {
            "status": "missing",
            "rows": [],
            "stale_rows": [],
            "checked_at": None,
            "error": "尚无当日市场观察",
        }
    status = row[0]
    error = row[3]
    if status == "running":
        try:
            started = datetime.fromisoformat(row[4])
            expired = (
                started.tzinfo is None
                or (now.astimezone(UTC) - started).total_seconds() > _FETCH_WAIT_SECONDS + 15
            )
        except (TypeError, ValueError):
            expired = True
        if expired:
            status = "unavailable"
            error = "上次准备中断或超时；当天不会自动重抓"
    try:
        rows = json.loads(row[1]) if status in {"ready", "unavailable"} else []
    except (TypeError, ValueError):
        rows = []
    if not isinstance(rows, list):
        rows = []
    fresh, stale = _split_fresh(rows, now.astimezone(_SHANGHAI).date())
    if status == "ready" and not fresh:
        status = "unavailable"
        error = (error + "; " if error else "") + "当日快照没有可核验时效的观察项"
    return {
        "status": status,
        "rows": fresh,
        "stale_rows": stale,
        "checked_at": row[2],
        "error": error,
    }
