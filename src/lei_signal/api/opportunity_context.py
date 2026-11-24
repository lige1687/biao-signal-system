"""Bounded, public narrative context for opportunity cards.

Reading a snapshot never fetches the network. ``prepare_context`` is the only
network entry point and stores unverified headline leads in a separate table.
"""

from __future__ import annotations

import json
import re
import sqlite3
import threading
import time
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import closing
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

import requests

from lei_signal.api.config import INDEX_OVERRIDES, US_ETFS, sqlite_path
from lei_signal.newsfeed.sources.rss import _GNEWS_TMPL, _HEADERS, _parse_feed

SOURCES_PATH = Path(__file__).resolve().parents[3] / "configs" / "opportunity-sources.v1.json"
_SHANGHAI = ZoneInfo("Asia/Shanghai")
_LOCK = threading.Lock()
_REQUEST_TIMEOUT = 10
_BATCH_DEADLINE = 80  # Leave one request timeout before the 90-second total.
_RUNNING_LEASE = timedelta(seconds=30)
_SQLITE_WRITE_TIMEOUT = 2.0
_SQLITE_WRITE_ATTEMPTS = 3
_MIN_ALIAS_LENGTH = 4
_GENERIC_ALIASES = {"信息产业", "科技创新", "消费行业", "新能源", "半导体"}
_RISK_TERMS = ("风险", "亏损", "下调", "调查", "risk", "downgrade")
_RISK_TABLE = "opportunity_context_risk_sources"
_PUBLIC_US_ETF_CODES = {item.symbol for item in US_ETFS}
_BROAD_INDICES = {
    "000001.SS", "000016.SS", "000300.SS", "000688.SS", "000698.SS",
    "000905.SS", "000852.SS", "399311.SZ", "399303.SZ", "000985.SS",
    "399006.SZ", "399005.SZ", "^IXIC", "^GSPC", "^NDX", "^DJI", "^RUT", "^HSI",
}
_BROAD_US_ETFS = {"SPY", "IVV", "VOO", "QQQ", "DIA", "IWM", "VTI"}


def narrative_focus(symbol: str, name: str, *, path: Path = SOURCES_PATH) -> dict:
    """Route narrative by registered product identity, never by a fuzzy name match."""
    unknown = {"kind": "unknown", "label": "产品背景", "market": None, "topics": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        payload = {}
    matches = [
        row for row in payload.get("profiles", [])
        if isinstance(row, dict) and row.get("symbol") == symbol
        and name in row.get("names", [])
    ]
    if len(matches) == 1:
        profile = matches[0]
        if profile.get("kind") in {"sector", "broad", "mixed"}:
            return {key: profile.get(key) for key in ("kind", "label", "market", "topics")}
    registered = INDEX_OVERRIDES.get(symbol)
    if symbol in _BROAD_INDICES and registered and name == registered.display_name:
        market = {"A股": "cn", "美股": "us", "港股": "hk"}.get(registered.market_cn)
        return {"kind": "broad", "label": "市场宏观", "market": market, "topics": []}
    if symbol in _BROAD_US_ETFS and any(
        item.symbol == symbol and item.display_name == name for item in US_ETFS
    ):
        return {"kind": "broad", "label": "美国宏观", "market": "us", "topics": []}
    return unknown


def macro_markets(snapshot: dict) -> list[str]:
    """Only request macro data for a market already bound to a product."""
    return sorted({
        focus["market"] for card in snapshot.get("items", [])
        if (focus := card.get("narrative_focus") or {}).get("market") in {"cn", "us"}
    })


def _day(value: object, today: date) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value[:10])
    except ValueError:
        return None
    return parsed.isoformat() if parsed <= today and value[:10] == parsed.isoformat() else None


def _source_day(value: object, today: date) -> str | None:
    """Require an ISO date or timezone-aware timestamp, never a date prefix alone."""
    if not isinstance(value, str):
        return None
    try:
        if len(value) == 10:
            parsed = date.fromisoformat(value)
        else:
            instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if instant.tzinfo is None or instant > datetime.now(_SHANGHAI):
                return None
            parsed = instant.date()
    except ValueError:
        return None
    return parsed.isoformat() if parsed <= today else None


def public_sources(symbol: str, name: str, *, today: date, path: Path = SOURCES_PATH) -> list[dict]:
    """Return exact-identity public facts with observation and publication dates kept apart."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if payload.get("schema_version") != 1 or not isinstance(payload.get("products"), list):
        return []
    # An explicitly registered alias can identify the canonical product name,
    # but only inside this exact symbol. Several dated rows may share that name;
    # an alias on one row therefore identifies all rows for that product.
    canonical_names = {
        row["name"]
        for row in payload["products"]
        if isinstance(row, dict)
        and row.get("symbol") == symbol
        and isinstance(row.get("name"), str)
        and (
            row["name"] == name
            or name in (
                row.get("aliases") if isinstance(row.get("aliases"), list) else []
            )
        )
    }
    if len(canonical_names) != 1:
        return []
    canonical_name = next(iter(canonical_names))
    result = []
    for row in payload["products"]:
        if (
            not isinstance(row, dict)
            or row.get("enabled") is False
            or row.get("symbol") != symbol
            or row.get("name") != canonical_name
        ):
            continue
        publication_value = row.get("published_at")
        published = _source_day(publication_value, today) if publication_value else None
        checked = _source_day(row.get("checked_at") or payload.get("checked_at"), today)
        report_value = row.get("report_date")
        report = _source_day(report_value, today) if report_value else None
        reporting_value = row.get("reporting_as_of")
        reporting = _source_day(reporting_value, today) if reporting_value else None
        profile = row.get("provenance") == "product_profile"
        url = row.get("source_url")
        if (
            not checked
            or (publication_value and not published)
            or (report_value and not report)
            or (reporting_value and not reporting)
            or (published and published > checked)
            or (not profile and not published and not (report or reporting))
            or not isinstance(url, str)
            or not url.startswith("https://")
            or not row.get("summary")
            or not row.get("source_name")
        ):
            continue
        if published and ((report and report > published) or (reporting and reporting > published)):
            continue
        limitations = list(row.get("limitations") or [])
        if checked < today.isoformat():
            limitations.append(f"公开资料上次核查为{checked}，今日尚未复核是否更新")
        if profile:
            limitations.append("仅为产品静态投资范围；最新成分、实际持仓与盈利情况尚未核实")
        elif not published:
            limitations.append("发布日期未知；报告期不等于可获得日期，不能用于当时可知的买卖判断")
        result.append(
            {
                "text": str(row["summary"]),
                "source": str(row["source_name"]),
                "source_ref": url,
                "date": None if profile else published or reporting or report,
                "published_at": publication_value if published and not profile else None,
                "checked_at": row.get("checked_at") or payload.get("checked_at"),
                "report_date": None if profile else report or reporting,
                "category": "industry"
                if profile
                else row.get("category")
                if row.get("category") in {"fundamentals", "industry", "news"}
                else "fundamentals",
                "scope": row.get("scope")
                if row.get("scope") in {"same_product", "industry_reference", "narrative"}
                else "same_product",
                "public": True,
                "provenance": "product_profile"
                if profile
                else ("verified_public_source" if published else "reporting_date_only"),
                "limitations": limitations,
                "narrative_kind": row.get("narrative_kind") or "profile",
                "relevance": row.get("relevance") or "direct",
            }
        )
    return result


def _subjects(snapshot: dict) -> list[tuple[str, str]]:
    subjects = set()
    for card in snapshot.get("items") or []:
        subject = card.get("subject") or {}
        kind = subject.get("kind")
        key = subject.get("key") if isinstance(subject.get("key"), str) else ""
        if kind == "holding" or (not kind and key.startswith("holding:")):
            # A holding ID is private and must never become a public search term.
            symbol = subject.get("code")
            if not isinstance(symbol, str) or not (
                re.fullmatch(r"\d{6}", symbol) or symbol in _PUBLIC_US_ETF_CODES
            ):
                continue
        elif kind == "symbol" or (not kind and key.startswith("symbol:")):
            symbol = subject.get("id")
        else:
            continue
        name = subject.get("name")
        if isinstance(symbol, str) and symbol and isinstance(name, str) and name:
            subjects.add((symbol, name))
    return sorted(subjects)


def _db_path(request) -> str:
    return getattr(request.app.state, "plans_db_path", None) or sqlite_path()


def _read_saved(request, subject: tuple[str, str], today: str) -> dict | None:
    """Read without migrations or writes; an absent database is simply a gap."""
    path = Path(_db_path(request))
    if not path.is_file():
        return None
    try:
        with closing(sqlite3.connect(f"file:{path}?mode=ro", uri=True)) as conn:
            row = conn.execute(
                "SELECT status,leads_json,error,started_at FROM opportunity_context_sources "
                "WHERE symbol=? AND product_name=? AND checked_on=?",
                (*subject, today),
            ).fetchone()
    except sqlite3.Error:
        return None
    if row is None:
        return None
    try:
        leads = json.loads(row[1] or "[]")
    except ValueError:
        leads = []
    return {
        "checked_on": today,
        "status": row[0],
        "leads": leads,
        "error": row[2] or "",
        "started_at": row[3],
    }


def _read_risk_saved(request, subject: tuple[str, str], today: str) -> dict | None:
    """A legacy general-news row never proves that a risk lookup ran."""
    path = Path(_db_path(request))
    if not path.is_file():
        return None
    try:
        with closing(sqlite3.connect(f"file:{path}?mode=ro", uri=True)) as conn:
            row = conn.execute(
                "SELECT status,leads_json,error,started_at,query,checked_at,matched_count "
                f"FROM {_RISK_TABLE} WHERE symbol=? AND product_name=? AND checked_on=?",
                (*subject, today),
            ).fetchone()
    except sqlite3.Error:
        return None
    if row is None:
        return None
    try:
        leads = json.loads(row[1] or "[]")
    except ValueError:
        leads = []
    return {
        "checked_on": today,
        "status": row[0],
        "leads": leads,
        "error": row[2] or "",
        "started_at": row[3],
        "query": row[4],
        "checked_at": row[5] or None,
        "count": row[6],
    }


def _interrupted(row: dict | None) -> bool:
    if not row or row.get("status") != "running":
        return False
    try:
        started = datetime.fromisoformat(row.get("started_at") or "")
        return started.tzinfo is None or datetime.now(UTC) - started > _RUNNING_LEASE
    except ValueError:
        return True


def _latest_saved_day(request, subject: tuple[str, str]) -> str | None:
    path = Path(_db_path(request))
    if not path.is_file():
        return None
    try:
        with closing(sqlite3.connect(f"file:{path}?mode=ro", uri=True)) as conn:
            row = conn.execute(
                "SELECT MAX(checked_on) FROM opportunity_context_sources "
                "WHERE symbol=? AND product_name=?",
                subject,
            ).fetchone()
        return row[0] if row else None
    except sqlite3.Error:
        return None


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS opportunity_context_sources ("
        "symbol TEXT NOT NULL, product_name TEXT NOT NULL, checked_on TEXT NOT NULL, "
        "status TEXT NOT NULL, leads_json TEXT NOT NULL, error TEXT NOT NULL DEFAULT '', "
        "started_at TEXT, "
        "PRIMARY KEY(symbol,product_name,checked_on))"
    )
    columns = {row[1] for row in conn.execute("PRAGMA table_info(opportunity_context_sources)")}
    if "started_at" not in columns:
        conn.execute("ALTER TABLE opportunity_context_sources ADD COLUMN started_at TEXT")
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS {_RISK_TABLE} ("
        "symbol TEXT NOT NULL, product_name TEXT NOT NULL, checked_on TEXT NOT NULL, "
        "status TEXT NOT NULL, leads_json TEXT NOT NULL, error TEXT NOT NULL DEFAULT '', "
        "started_at TEXT, query TEXT NOT NULL, checked_at TEXT, matched_count INTEGER NOT NULL "
        "DEFAULT 0, PRIMARY KEY(symbol,product_name,checked_on))"
    )


def _write_cache(db_path: str, write: Callable[[sqlite3.Connection], object]) -> object:
    """Retry only a busy cache transaction; never repeat its upstream lookup."""
    for attempt in range(_SQLITE_WRITE_ATTEMPTS):
        try:
            with closing(sqlite3.connect(db_path, timeout=_SQLITE_WRITE_TIMEOUT)) as conn, conn:
                return write(conn)
        except sqlite3.OperationalError as exc:
            code = getattr(exc, "sqlite_errorcode", None)
            if (
                code is None
                or code & 0xFF != sqlite3.SQLITE_BUSY
                or attempt + 1 == _SQLITE_WRITE_ATTEMPTS
            ):
                raise
            time.sleep(0.1 * (attempt + 1))
    raise AssertionError("unreachable")


def needs_context(request, snapshot: dict, *, retry_failed: bool = False) -> bool:
    """Whether either daily headline lookup is absent, interrupted, or explicitly retried."""
    today = datetime.now(_SHANGHAI).date().isoformat()
    return any(
        (row := reader(request, subject, today)) is None
        or _interrupted(row)
        or (retry_failed and row.get("status") == "unavailable")
        for subject in _subjects(snapshot)
        for reader in (_read_saved, _read_risk_saved)
    )


def _aliases(code: str, name: str) -> list[str]:
    """Use only curated aliases attached to the same exact product identity."""
    try:
        payload = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if payload.get("schema_version") != 1:
        return []
    aliases: set[str] = set()
    for row in payload.get("products") or []:
        if not isinstance(row, dict) or row.get("symbol") != code or row.get("name") != name:
            continue
        for alias in row.get("aliases") or []:
            if (
                isinstance(alias, str)
                and len(alias.strip()) >= _MIN_ALIAS_LENGTH
                and alias.strip() != name
                and alias.strip() not in _GENERIC_ALIASES
            ):
                aliases.add(alias.strip())
    return sorted(aliases)


def _bare_code(code: str) -> str:
    return re.sub(r"\.(?:SS|SZ)\Z", "", code, flags=re.I)


def _token_conversion_namesake(title: str) -> bool:
    # A tokenized namesake is a different product from the underlying ETF.
    return bool(
        re.search(r"\b(?:Robinhood\s+Token|Tokenized)\b|代币", title, re.I)
        and re.search(r"\b(?:Convert(?:s|ed|ing)?|Conversion|Crypto)\b|兑换|加密", title, re.I)
    )


def _title_matches(title: str, code: str, name: str, aliases: list[str]) -> bool:
    if _token_conversion_namesake(title):
        return False
    if (name not in _GENERIC_ALIASES and name in title) or any(alias in title for alias in aliases):
        return True
    bare = _bare_code(code)
    if len(bare) < 3:
        return False
    return bool(re.search(r"(?<![0-9A-Za-z])" + re.escape(bare) + r"(?![0-9A-Za-z])", title, re.I))


def _fetch_headlines(query: str) -> list[tuple[str, str, datetime, str]]:
    """Fetch only Google News RSS with a ten-second network timeout."""
    url = _GNEWS_TMPL.format(query=quote_plus(query))
    response = requests.get(url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT)
    response.raise_for_status()
    rows = []
    for title, link, published, _ in _parse_feed(response.text)[:20]:
        if title and link and published is not None:
            rows.append((title, link, published, "Google News"))
    return rows


def _query_text(subject: tuple[str, str], *, risk: bool) -> str:
    code, name = subject
    aliases = _aliases(code, name)
    terms = ([name] if name not in _GENERIC_ALIASES else []) + aliases + [_bare_code(code)]
    identity = "(" + " OR ".join(f'"{term.replace(chr(34), "")}"' for term in terms) + ")"
    direction = " (" + " OR ".join(_RISK_TERMS) + ")" if risk else ""
    return identity + direction + " when:7d"


def _query(
    subject: tuple[str, str], today: date, *, risk: bool = False
) -> tuple[tuple[str, str], dict]:
    code, name = subject
    aliases = _aliases(code, name)
    query = _query_text(subject, risk=risk)
    try:
        items = _fetch_headlines(query)
        leads = []
        now = datetime.now(_SHANGHAI)
        for title, url, published_at, source_name in items:
            if (
                published_at.tzinfo is None
                or published_at > now
                or published_at < now - timedelta(days=7)
                or not url.startswith("https://")
                or not _title_matches(title, code, name, aliases)
            ):
                continue
            leads.append(
                {
                    "title": title,
                    "published_at": published_at.isoformat(),
                    "source_name": source_name,
                    "source_url": url,
                }
            )
            if len(leads) >= 5:
                break
        return subject, {
            "checked_on": today.isoformat(),
            "checked_at": datetime.now(_SHANGHAI).isoformat(),
            "status": "checked",
            "query": query,
            "leads": leads,
            "count": len(leads),
        }
    except Exception as exc:
        return subject, {
            "checked_on": today.isoformat(),
            "checked_at": datetime.now(_SHANGHAI).isoformat(),
            "status": "unavailable",
            "query": query,
            "leads": [],
            "count": 0,
            "error": type(exc).__name__,
        }


def prepare_context(request, snapshot: dict, *, retry_failed: bool = False) -> None:
    """Share one bounded worker pool across general and risk-direction lookups."""
    today = datetime.now(_SHANGHAI).date()
    pending = iter(
        (subject, kind)
        for subject in _subjects(snapshot)
        for kind, reader in (("general", _read_saved), ("risk", _read_risk_saved))
        if (row := reader(request, subject, today.isoformat())) is None
        or _interrupted(row)
        or (retry_failed and row.get("status") == "unavailable")
    )
    cutoff = time.monotonic() + _BATCH_DEADLINE

    def claim_next(pool: ThreadPoolExecutor, running: dict) -> bool:
        while time.monotonic() < cutoff:
            try:
                subject, kind = next(pending)
            except StopIteration:
                return False
            table = "opportunity_context_sources" if kind == "general" else _RISK_TABLE
            stamp = datetime.now(UTC).isoformat()
            expired_before = (datetime.now(UTC) - _RUNNING_LEASE).isoformat()

            def claim(
                conn: sqlite3.Connection, *, kind=kind, table=table, subject=subject,
                stamp=stamp, today=today, expired_before=expired_before,
                retry_failed=retry_failed,
            ) -> int:
                _ensure_table(conn)
                if kind == "risk":
                    inserted = conn.execute(
                        f"INSERT OR IGNORE INTO {table} "
                        "(symbol,product_name,checked_on,status,leads_json,error,started_at,query) "
                        "VALUES (?,?,?,'running','[]','',?,?)",
                        (*subject, today.isoformat(), stamp, _query_text(subject, risk=True)),
                    ).rowcount
                else:
                    inserted = conn.execute(
                        f"INSERT OR IGNORE INTO {table} "
                        "(symbol,product_name,checked_on,status,leads_json,error,started_at) "
                        "VALUES (?,?,?,'running','[]','',?)",
                        (*subject, today.isoformat(), stamp),
                    ).rowcount
                if not inserted:
                    inserted = conn.execute(
                        f"UPDATE {table} SET started_at=?,error='' "
                        "WHERE symbol=? AND product_name=? AND checked_on=? "
                        "AND status='running' AND (started_at IS NULL OR started_at<?)",
                        (stamp, *subject, today.isoformat(), expired_before),
                    ).rowcount
                if not inserted and retry_failed:
                    inserted = conn.execute(
                        f"UPDATE {table} SET "
                        "status='running',started_at=?,error='',leads_json='[]' "
                        "WHERE symbol=? AND product_name=? AND checked_on=? "
                        "AND status='unavailable'",
                        (stamp, *subject, today.isoformat()),
                    ).rowcount
                return inserted

            with _LOCK:
                inserted = _write_cache(_db_path(request), claim)
            if inserted:
                running[pool.submit(_query, subject, today, risk=kind == "risk")] = (
                    subject, kind, stamp
                )
                return True
        return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        running: dict = {}
        while len(running) < 2 and claim_next(pool, running):
            pass
        while running:
            done, _ = wait(
                running, timeout=max(0, cutoff - time.monotonic()), return_when=FIRST_COMPLETED
            )
            if not done:
                # Active ten-second requests finish on executor exit; untouched
                # lookup kinds have no database row and remain retryable.
                done = set(running)
            for future in done:
                subject, kind, stamp = running.pop(future)
                _, result = future.result()
                table = "opportunity_context_sources" if kind == "general" else _RISK_TABLE

                def save_result(
                    conn: sqlite3.Connection, *, kind=kind, table=table, result=result,
                    subject=subject, today=today, stamp=stamp,
                ) -> None:
                    values = (
                        result["status"],
                        json.dumps(result["leads"], ensure_ascii=False),
                        result.get("error", ""),
                    )
                    if kind == "risk":
                        conn.execute(
                            f"UPDATE {table} SET status=?,leads_json=?,error=?,"
                            "query=?,checked_at=?,matched_count=? "
                            "WHERE symbol=? AND product_name=? AND checked_on=? "
                            "AND status='running' AND started_at=?",
                            (
                                *values,
                                result["query"],
                                result["checked_at"],
                                result["count"],
                                *subject,
                                today.isoformat(),
                                stamp,
                            ),
                        )
                    else:
                        conn.execute(
                            f"UPDATE {table} SET status=?,leads_json=?,error=? "
                            "WHERE symbol=? AND product_name=? AND checked_on=? "
                            "AND status='running' AND started_at=?",
                            (*values, *subject, today.isoformat(), stamp),
                        )
                _write_cache(_db_path(request), save_result)
            while len(running) < 2 and claim_next(pool, running):
                pass


def cached_news(request, symbol: str, name: str) -> dict:
    today = datetime.now(_SHANGHAI).date().isoformat()
    row = _read_saved(request, (symbol, name), today)
    if not row:
        previous = _latest_saved_day(request, (symbol, name))
        detail = (
            f"今日尚未检索；最近一次为{previous}，已过期"
            if previous
            else "今日尚未检索同产品公开消息"
        )
        return {"status": "unavailable", "detail": detail, "leads": []}
    if row.get("status") == "running":
        detail = (
            "同产品公开消息检索已中断，可重新读取" if _interrupted(row) else "同产品公开消息检索中"
        )
        return {"status": "unavailable", "detail": detail, "leads": []}
    if row.get("status") == "unavailable":
        return {"status": "unavailable", "detail": "同产品公开消息检索失败", "leads": []}
    visible = [item for item in row["leads"] if not _token_conversion_namesake(item["title"])]
    excluded = len(row["leads"]) - len(visible)
    detail = (
        f"近七日准确名称与代码检索，取得{len(row['leads'])}条未核原文标题线索"
        if row["leads"]
        else "近七日本次未找到可关联的同产品标题；不代表没有消息或不利事实"
    )
    if excluded:
        detail += f"；其中{excluded}条同名代币兑换标题已从展示排除"
    return {"status": "checked", "detail": detail, "checked_on": today, "leads": visible}


def cached_risk_news(request, symbol: str, name: str) -> dict:
    """Expose an auditable risk-direction lookup, never verified article facts."""
    today = datetime.now(_SHANGHAI).date().isoformat()
    subject = (symbol, name)
    row = _read_risk_saved(request, subject, today)
    receipt = {
        "query": row["query"] if row else _query_text(subject, risk=True),
        "checked_at": row["checked_at"] if row else None,
        "count": row["count"] if row else 0,
        "error": row["error"] if row else "",
        "leads": [],
    }
    if not row:
        return {
            **receipt,
            "status": "unavailable",
            "detail": "今日尚未执行同产品风险方向标题检索；不能据此认为没有风险",
        }
    if row["status"] == "running":
        detail = "风险方向检索已中断，可重新读取" if _interrupted(row) else "风险方向检索中"
        return {**receipt, "status": "unavailable", "detail": detail}
    if row["status"] == "unavailable":
        return {**receipt, "status": "unavailable", "detail": "同产品风险方向标题检索失败"}
    visible = [item for item in row["leads"] if not _token_conversion_namesake(item["title"])]
    excluded = len(row["leads"]) - len(visible)
    detail = (
        f"近七日风险方向查询，原采集到{row['count']}条未核原文标题线索"
        if row["count"]
        else "近七日风险方向查询未找到同产品标题；不代表没有风险或不利事实"
    )
    if excluded:
        detail += f"；其中{excluded}条同名代币兑换标题已从展示排除"
    return {**receipt, "status": "checked", "detail": detail, "leads": visible}
