"""Bounded official-source news discovery for opportunity narrative context.

This module neither scores trading signals nor sends notifications. Feed titles
are leads only: a record becomes an event after its official article supplies
both a publication date and substantive body text.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor, wait
from contextlib import closing
from datetime import UTC, date, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

import requests

SOURCES_PATH = Path(__file__).resolve().parents[3] / "configs" / "opportunity-news-sources.v1.json"
_SHANGHAI = ZoneInfo("Asia/Shanghai")
_HTTP_TIMEOUT = 12
_MAX_BYTES = 1_000_000
_MAX_SOURCES = 8
_MAX_CANDIDATES = 2
_DEADLINE = 75
_LEASE_SECONDS = 110
_FAILURE_COOLDOWN = timedelta(hours=6)
_SUCCESS_COOLDOWN = timedelta(days=1)
_MIN_BODY = 120
_DATE_KEYS = {
    "article:published_time",
    "datepublished",
    "pubdate",
    "publishdate",
    "dc.date",
    "dc.date.issued",
    "date",
    "citation_publication_date",
}
_FAILURE_TEXT = {
    "no_article_links": "来源页没有可核的原文链接",
    "missing_article_date": "原文缺少明确发布日期",
    "insufficient_article_body": "原文正文不足",
    "deadline": "核对超时",
    "index_only_expired": "来源索引只列旧公告，近期覆盖待核",
}


def _failure(source_id: str, reason: str | None, sources: dict[str, dict]) -> dict:
    code = reason or "unknown"
    if code.startswith("feed_"):
        message = "来源页暂未读到"
    elif code.startswith("article_"):
        message = "原文暂未读到"
    else:
        message = _FAILURE_TEXT.get(code, "本次核对未完成")
    return {
        "source_id": source_id,
        "source_name": sources.get(source_id, {}).get("name", source_id),
        "reason_code": code,
        "reason": message,
    }


def _today(as_of: date | None) -> date:
    return as_of or datetime.now(_SHANGHAI).date()


def _cache_path(db_path: str | Path) -> Path:
    path = Path(db_path)
    return path.with_name(f"{path.stem}-opportunity-news.sqlite3")


def _connect(db_path: str | Path) -> sqlite3.Connection:
    path = _cache_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=2)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=2000")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS opportunity_news_events (
            id TEXT PRIMARY KEY, source_id TEXT NOT NULL, published_at TEXT NOT NULL,
            checked_at TEXT NOT NULL, payload TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS opportunity_news_attempts (
            as_of TEXT NOT NULL, source_id TEXT NOT NULL, status TEXT NOT NULL,
            checked_at TEXT, next_retry_at TEXT, failure TEXT,
            missing_original INTEGER NOT NULL DEFAULT 0,
            missing_date INTEGER NOT NULL DEFAULT 0,
            expired INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(as_of, source_id)
        );
        CREATE TABLE IF NOT EXISTS opportunity_news_lease (
            as_of TEXT PRIMARY KEY, expires_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS opportunity_news_event_versions (
            content_hash TEXT PRIMARY KEY, event_id TEXT NOT NULL,
            saved_at TEXT NOT NULL, payload TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS opportunity_news_attempt_history (
            attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
            as_of TEXT NOT NULL, source_id TEXT NOT NULL, status TEXT NOT NULL,
            checked_at TEXT NOT NULL, failure TEXT, fingerprint TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS opportunity_news_source_fingerprints (
            as_of TEXT NOT NULL, source_id TEXT NOT NULL, fingerprint TEXT NOT NULL,
            PRIMARY KEY(as_of, source_id)
        );
    """)
    # Preserve records made by the initial cache format before the first
    # refresh with append-only versions. No historical record is removed.
    for row in conn.execute("SELECT id, checked_at, payload FROM opportunity_news_events"):
        event = json.loads(row["payload"])
        conn.execute(
            "INSERT OR IGNORE INTO opportunity_news_event_versions VALUES (?, ?, ?, ?)",
            (_content_hash(event), row["id"], row["checked_at"], row["payload"]),
        )
    conn.commit()
    return conn


def _content_hash(event: dict) -> str:
    content = {key: value for key, value in event.items() if key not in {"checked_at", "products"}}
    return hashlib.sha256(
        json.dumps(content, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def _source_fingerprint(source: dict) -> str:
    return hashlib.sha256(
        json.dumps(source, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def _fingerprints(conn: sqlite3.Connection, as_of: date) -> dict[str, str]:
    try:
        return {
            row["source_id"]: row["fingerprint"]
            for row in conn.execute(
                "SELECT source_id, fingerprint FROM opportunity_news_source_fingerprints "
                "WHERE as_of=?",
                (as_of.isoformat(),),
            )
        }
    except sqlite3.OperationalError:
        return {}


def _read_connection(db_path: str | Path) -> sqlite3.Connection | None:
    path = _cache_path(db_path)
    if not path.is_file():
        return None
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)
    except sqlite3.OperationalError:
        return None
    conn.row_factory = sqlite3.Row
    return conn


def _sources(path: Path = SOURCES_PATH) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if data.get("schema_version") != 1:
        return []
    rows = data.get("sources")
    if not isinstance(rows, list):
        return []
    result = []
    for row in rows:
        if not isinstance(row, dict) or row.get("enabled") is False:
            continue
        if (
            row.get("kind") not in {"macro", "industry"}
            or row.get("feed_type", "rss") not in {"rss", "html_index"}
            or row.get("market") not in {"cn", "us"}
            or not isinstance(row.get("id"), str)
            or not isinstance(row.get("name"), str)
            or not isinstance(row.get("official_domains"), list)
            or not _official(row.get("feed_url"), row["official_domains"])
        ):
            continue
        result.append(row)
    return result


def _profiles(profiles: list[dict] | None) -> list[dict]:
    if not isinstance(profiles, list):
        return []
    return [p for p in profiles if isinstance(p, dict) and p.get("market") in {"cn", "us"}]


def _eligible(source: dict, profiles: list[dict]) -> bool:
    if source["kind"] == "macro":
        return True
    topics = {str(t).casefold() for t in source.get("topics", []) if isinstance(t, str)}
    markets = set(source.get("related_markets") or [source["market"]])
    return bool(topics) and any(
        p.get("market") in markets
        and topics.intersection(
            str(t).casefold() for t in p.get("topics", []) if isinstance(t, str)
        )
        for p in profiles
    )


def _official(url: object, domains: list) -> bool:
    if not isinstance(url, str) or not url.startswith("https://"):
        return False
    host = (urlsplit(url).hostname or "").lower()
    return bool(host) and any(
        isinstance(domain, str)
        and host in {domain.lower().lstrip("."), "www." + domain.lower().lstrip(".")}
        for domain in domains
    )


def _canonical(url: str) -> str:
    parts = urlsplit(url)
    path = re.sub(r"/(?:(?:default|index)\.html?)$", "", parts.path, flags=re.IGNORECASE)
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            path.rstrip("/") or "/",
            "",
            "",
        )
    )


def _get(url: str, domains: list[str]) -> tuple[str, str]:
    if not _official(url, domains):
        raise ValueError("non_official_url")
    response = requests.get(
        url,
        timeout=_HTTP_TIMEOUT,
        headers={"User-Agent": "LeiSignal/1.0 (research source verification)"},
        stream=True,
    )
    try:
        response.raise_for_status()
        if not _official(response.url, domains):
            raise ValueError("non_official_redirect")
        chunks = []
        size = 0
        for chunk in response.iter_content(chunk_size=16384):
            size += len(chunk)
            if size > _MAX_BYTES:
                raise ValueError("response_too_large")
            chunks.append(chunk)
        payload = b"".join(chunks)
        # Several official sites declare UTF-8 in the document but serve an
        # ISO-8859-1 HTTP header. Prefer a lossless UTF-8 decode in that case.
        try:
            decoded = payload.decode("utf-8-sig")
        except UnicodeDecodeError:
            decoded = payload.decode(response.encoding or "utf-8", errors="replace")
        return decoded, response.url
    finally:
        response.close()


class _Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.dates: list[str] = []
        self.paragraphs: list[str] = []
        self.links: list[tuple[str, str]] = []
        self.release_start: int | None = None
        self._active: list[tuple[str, list[str]]] = []
        self._blocked = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        fields = dict(attrs)
        if tag in {"script", "style", "nav", "footer", "header"}:
            self._blocked += 1
        if tag == "meta":
            key = (
                fields.get("property") or fields.get("name") or fields.get("itemprop") or ""
            ).lower()
            if key in _DATE_KEYS and fields.get("content"):
                self.dates.append(fields["content"])
        if tag == "time" and fields.get("datetime"):
            self.dates.append(fields["datetime"])
        if tag in {"p", "h1", "title", "time", "a"} or (
            tag == "div" and "dates" in (fields.get("class") or "").split()
        ):
            self._active.append((tag, []))
            if tag == "a":
                self._active[-1][1].append("\x00" + (fields.get("href") or "") + "\x00")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "nav", "footer", "header"}:
            self._blocked = max(0, self._blocked - 1)
        if self._active and self._active[-1][0] == tag:
            _, parts = self._active.pop()
            value = re.sub(r"\s+", " ", "".join(parts)).strip()
            if tag == "a":
                match = re.match(r"\x00([^\x00]*)\x00(.*)", value)
                if match and match.group(2).strip():
                    self.links.append((match.group(1), match.group(2).strip()))
            elif tag == "time" and value:
                self.dates.append(value)
            elif tag == "div" and value.lower().startswith("release date:"):
                self.dates.append(value.removeprefix("Release Date:").strip())
                self.release_start = len(self.paragraphs)
            elif tag in {"title", "h1"} and value:
                self.title = value
            elif tag == "p" and value and not self._blocked:
                self.paragraphs.append(value)

    def handle_data(self, data: str) -> None:
        if self._active and not self._blocked:
            self._active[-1][1].append(data)


def _page(html: str) -> _Page:
    page = _Page()
    page.feed(html)
    # NVIDIA's official release template states publication time in this
    # PublishDate field rather than article metadata or a <time> element.
    page.dates.extend(
        re.findall(
            r"ga_four_event\(\s*['\"]PublishDate['\"]\s*,\s*['\"]View['\"]\s*,\s*['\"]([^'\"]+)['\"]",
            html,
        )
    )
    return page


def _published(values: list[str], as_of: date) -> str | None:
    for value in values:
        value = value.strip()
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            stamp = parsed.astimezone(_SHANGHAI).date() if parsed.tzinfo else parsed.date()
        except ValueError:
            match = re.search(r"\b(20\d\d)[-/年](\d{1,2})[-/月](\d{1,2})", value)
            if match:
                try:
                    stamp = date(*(int(x) for x in match.groups()))
                except ValueError:
                    continue
            else:
                try:
                    stamp = datetime.strptime(value, "%B %d, %Y").date()
                except ValueError:
                    continue
        # A future publication marker must not be bypassed by another date
        # elsewhere in the document (for example an older report period).
        return stamp.isoformat() if stamp <= as_of else None
    return None


def _leads(source: dict, text: str, feed_url: str) -> list[tuple[str, str]]:
    if source.get("feed_type", "rss") == "html_index":
        return [(urljoin(feed_url, href), title) for href, title in _page(text).links]
    # The Federal Reserve RDF feed embeds named HTML entities inside XML text.
    # Expand only non-XML names; keep &amp; and the other XML entities escaped.
    text = re.sub(
        r"&([A-Za-z][A-Za-z0-9]+);",
        lambda match: (
            match.group(0)
            if match.group(1) in {"amp", "lt", "gt", "quot", "apos"}
            else html.unescape(match.group(0))
        ),
        text,
    )
    root = ElementTree.fromstring(text)
    leads = []
    for entry in root.iter():
        if entry.tag.rsplit("}", 1)[-1] not in {"item", "entry"}:
            continue
        title = ""
        link = ""
        for child in entry:
            tag = child.tag.rsplit("}", 1)[-1]
            if tag == "title":
                title = " ".join(child.itertext()).strip()
            if tag == "link":
                link = child.attrib.get("href") or (child.text or "").strip()
            if tag == "description" and source.get("article_url_pattern"):
                for candidate in re.findall(r'https://[^"\s<>]+', child.text or ""):
                    candidate = html.unescape(candidate)
                    if re.search(source["article_url_pattern"], candidate):
                        link = candidate
                        break
        if link and title:
            leads.append((urljoin(feed_url, link), title))
    return leads


def _matched_products(source: dict, profiles: list[dict]) -> list[dict]:
    topics = {str(t).casefold() for t in source.get("topics", [])}
    markets = set(source.get("related_markets") or [source["market"]])
    return [
        {
            "symbol": p["symbol"],
            "name": p.get("name", p["symbol"]),
            "relation": (
                "cross_market_industry_reference"
                if p.get("market") != source["market"]
                else "industry_reference"
            ),
        }
        for p in profiles
        if isinstance(p.get("symbol"), str)
        and p.get("market") in markets
        and topics.intersection(str(t).casefold() for t in p.get("topics", []))
    ]


def _collect(source: dict, as_of: date, profiles: list[dict]) -> tuple[list[dict], dict]:
    result = {
        "source_id": source["id"],
        "status": "success",
        "reason": None,
        "missing_original": 0,
        "missing_date": 0,
        "expired": 0,
    }
    events = []
    try:
        feed, final_feed_url = _get(source["feed_url"], source["official_domains"])
        leads = _leads(source, feed, final_feed_url)
    except (requests.RequestException, ValueError, ElementTree.ParseError) as exc:
        result.update(status="failed", reason=f"feed_{type(exc).__name__}")
        return events, result
    pattern = source.get("article_url_pattern")
    leads = [
        (url, title)
        for url, title in leads
        if _official(url, source["official_domains"]) and (not pattern or re.search(pattern, url))
    ]
    if not leads:
        result.update(status="partial", reason="no_article_links")
        return events, result
    keywords = [
        str(word).casefold() for word in source.get("keywords", []) if isinstance(word, str)
    ]
    seen = set()
    for url, lead_title in leads:
        if len(seen) >= _MAX_CANDIDATES:
            break
        if not _official(url, source["official_domains"]):
            continue
        if pattern and not re.search(pattern, url):
            continue
        if _canonical(url) in seen:
            continue
        if keywords and not any(word in lead_title.casefold() for word in keywords):
            continue
        seen.add(_canonical(url))
        try:
            html, final_url = _get(url, source["official_domains"])
            page = _page(html)
        except (requests.RequestException, ValueError) as exc:
            result["missing_original"] += 1
            result.update(status="partial", reason=f"article_{type(exc).__name__}")
            continue
        published = _published(page.dates, as_of)
        if not published:
            result["missing_date"] += 1
            result.update(status="partial", reason="missing_article_date")
            continue
        if published < (as_of - timedelta(days=4)).isoformat():
            result["expired"] += 1
            continue
        body = " ".join(
            page.paragraphs[page.release_start :]
            if page.release_start is not None
            else page.paragraphs
        )
        body = re.sub(r"\s+", " ", body).strip()
        if len(body) < _MIN_BODY:
            result["missing_original"] += 1
            result.update(status="partial", reason="insufficient_article_body")
            continue
        if keywords and not any(word in body.casefold() for word in keywords):
            continue
        # The index/feed title is part of the same official source. Many
        # article templates contain generic or script-generated <title>/<h1>.
        title = (lead_title or page.title).strip()[:180]
        if not title:
            continue
        ref = _canonical(final_url)
        digest = hashlib.sha256(f"{ref}|{published}".encode()).hexdigest()[:20]
        checked = datetime.now(_SHANGHAI).isoformat(timespec="seconds")
        events.append(
            {
                "id": f"news_{digest}",
                "scope": source["kind"],
                "market": source["market"],
                "products": _matched_products(source, profiles)
                if source["kind"] == "industry"
                else [],
                "source": source["name"],
                "source_id": source["id"],
                "source_ref": ref,
                "title": title,
                "source_excerpt": body[:1000],
                "text": body[:1000],
                "source_document_hash": hashlib.sha256(body.encode()).hexdigest(),
                "published_at": published,
                "report_date": None,
                "checked_at": checked,
                "provenance": "verified_public_source",
                "event_type": source.get(
                    "event_type",
                    "macro_release" if source["kind"] == "macro" else "industry_update",
                ),
                "importance": int(source.get("importance", 1)),
                "impact": "unknown",
                "limitations": [
                    "仅是官方原件摘录，不证明市场或产品价格影响。",
                    "相关行业或跨市场产业链参考不代表 ETF 当前持有该公司。",
                ],
            }
        )
    if (
        source.get("feed_type") == "html_index"
        and not events
        and result["expired"] > 0
        and result["status"] == "success"
    ):
        result.update(status="partial", reason="index_only_expired")
    return events, result


def _attempt_rows(conn: sqlite3.Connection, as_of: date) -> dict[str, sqlite3.Row]:
    return {
        r["source_id"]: r
        for r in conn.execute(
            "SELECT * FROM opportunity_news_attempts WHERE as_of=?", (as_of.isoformat(),)
        )
    }


def news_due(
    db_path: str | Path, as_of: date | None = None, profiles: list[dict] | None = None
) -> bool:
    """True when a configured source is absent or past its retry time."""
    day = _today(as_of)
    sources = [s for s in _sources() if _eligible(s, _profiles(profiles))][:_MAX_SOURCES]
    if not sources:
        return False
    conn = _read_connection(db_path)
    if conn is None:
        return True
    with closing(conn):
        attempts = _attempt_rows(conn, day)
        fingerprints = _fingerprints(conn, day)
        now = datetime.now(UTC)
        for source in sources:
            row = attempts.get(source["id"])
            if row is None or fingerprints.get(source["id"]) != _source_fingerprint(source):
                return True
            if not row["next_retry_at"]:
                return True
            if datetime.fromisoformat(row["next_retry_at"]) <= now:
                return True
    return False


def read_news(
    db_path: str | Path, as_of: date | None = None, profiles: list[dict] | None = None
) -> dict:
    """Read the local verified cache only; no HTTP requests."""
    day = _today(as_of)
    start = day - timedelta(days=4)
    profs = _profiles(profiles)
    sources = {s["id"]: s for s in [x for x in _sources() if _eligible(x, profs)][:_MAX_SOURCES]}
    conn = _read_connection(db_path)
    attempts = {}
    fingerprints = {}
    rows = []
    if conn is not None:
        with closing(conn):
            try:
                attempts = _attempt_rows(conn, day)
                fingerprints = _fingerprints(conn, day)
                rows = conn.execute(
                    "SELECT payload FROM opportunity_news_events "
                    "WHERE published_at BETWEEN ? AND ?",
                    (start.isoformat(), day.isoformat()),
                ).fetchall()
            except sqlite3.OperationalError:
                pass
    attempts = {key: value for key, value in attempts.items() if key in sources}
    fingerprints = {key: value for key, value in fingerprints.items() if key in sources}
    events = []
    for row in rows:
        event = json.loads(row["payload"])
        source = sources.get(event.get("source_id"))
        if not source:
            continue
        if event["scope"] == "industry":
            event["products"] = _matched_products(source, profs)
            if not event["products"]:
                continue
        events.append(event)
    events.sort(
        key=lambda e: (
            -int(e.get("importance", 1)),
            -date.fromisoformat(e["published_at"]).toordinal(),
            e["id"],
        )
    )
    failures = [
        _failure(s, r["failure"], sources) for s, r in attempts.items() if r["status"] != "success"
    ]
    stale_config = [
        s
        for s, source in sources.items()
        if s in attempts and fingerprints.get(s) != _source_fingerprint(source)
    ]
    checked = [r["checked_at"] for r in attempts.values() if r["checked_at"]]
    return {
        "as_of": day.isoformat(),
        "window_start": start.isoformat(),
        "events": events,
        "coverage": {
            "status": "partial"
            if failures or stale_config or len(attempts) < len(sources)
            else "complete",
            "stale_config_sources": stale_config,
            "expected_sources": len(sources),
            "checked_sources": sum(s in attempts and s not in stale_config for s in sources),
            "failed_sources": len(failures),
            "last_checked_at": max(checked) if checked else None,
            "missing_original": sum(r["missing_original"] for r in attempts.values()),
            "missing_date": sum(r["missing_date"] for r in attempts.values()),
            "expired": sum(r["expired"] for r in attempts.values()),
            "failures": failures,
        },
    }


def refresh_news(
    db_path: str | Path,
    as_of: date | None = None,
    profiles: list[dict] | None = None,
    force: bool = False,
) -> dict:
    """Refresh up to eight official sources with an SQLite lease and bounded requests."""
    day = _today(as_of)
    profs = _profiles(profiles)
    sources = [s for s in _sources() if _eligible(s, profs)][:_MAX_SOURCES]
    now = datetime.now(UTC)
    to_run = []
    with closing(_connect(db_path)) as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            lease = conn.execute(
                "SELECT expires_at FROM opportunity_news_lease WHERE as_of=?", (day.isoformat(),)
            ).fetchone()
            if lease and datetime.fromisoformat(lease["expires_at"]) > now:
                conn.rollback()
                result = read_news(db_path, day, profs)
                result["refresh"] = {
                    "status": "busy",
                    "checked_at": result["coverage"]["last_checked_at"],
                    "attempted_sources": 0,
                    "verified_new": 0,
                    "failures": [],
                }
                return result
            attempts = _attempt_rows(conn, day)
            fingerprints = _fingerprints(conn, day)
            for source in sources:
                row = attempts.get(source["id"])
                if (
                    force
                    or row is None
                    or fingerprints.get(source["id"]) != _source_fingerprint(source)
                    or not row["next_retry_at"]
                    or datetime.fromisoformat(row["next_retry_at"]) <= now
                ):
                    to_run.append(source)
            if not to_run:
                conn.rollback()
                result = read_news(db_path, day, profs)
                status = "cached" if result["coverage"]["status"] == "complete" else "cooldown"
                result["refresh"] = {
                    "status": status,
                    "checked_at": result["coverage"]["last_checked_at"],
                    "attempted_sources": 0,
                    "verified_new": 0,
                    "failures": [],
                }
                return result
            conn.execute(
                "INSERT INTO opportunity_news_lease VALUES (?, ?) "
                "ON CONFLICT(as_of) DO UPDATE SET expires_at=excluded.expires_at",
                (day.isoformat(), (now + timedelta(seconds=_LEASE_SECONDS)).isoformat()),
            )
            conn.commit()
        except sqlite3.OperationalError:
            conn.rollback()
            result = read_news(db_path, day, profs)
            result["refresh"] = {
                "status": "busy",
                "checked_at": result["coverage"]["last_checked_at"],
                "attempted_sources": 0,
                "verified_new": 0,
                "failures": [],
            }
            return result
    output = []
    pool = ThreadPoolExecutor(max_workers=3)
    futures = {pool.submit(_collect, source, day, profs): source for source in to_run}
    done, pending = wait(futures, timeout=_DEADLINE)
    for future in done:
        source = futures[future]
        try:
            output.append(future.result())
        except Exception as exc:  # Keep a bad source from blocking technical analysis.
            output.append(
                (
                    [],
                    {
                        "source_id": source["id"],
                        "status": "failed",
                        "reason": f"collector_{type(exc).__name__}",
                        "missing_original": 0,
                        "missing_date": 0,
                        "expired": 0,
                    },
                )
            )
    for future in pending:
        future.cancel()
        output.append(
            (
                [],
                {
                    "source_id": futures[future]["id"],
                    "status": "failed",
                    "reason": "deadline",
                    "missing_original": 0,
                    "missing_date": 0,
                    "expired": 0,
                },
            )
        )
    pool.shutdown(wait=False, cancel_futures=True)
    verified_new = 0
    checked_at = datetime.now(_SHANGHAI).isoformat(timespec="seconds")
    with closing(_connect(db_path)) as conn:
        for events, state in output:
            for event in events:
                payload = json.dumps(event, ensure_ascii=False)
                conn.execute(
                    "INSERT OR IGNORE INTO opportunity_news_event_versions VALUES (?, ?, ?, ?)",
                    (_content_hash(event), event["id"], event["checked_at"], payload),
                )
                cursor = conn.execute(
                    "INSERT OR IGNORE INTO opportunity_news_events VALUES (?, ?, ?, ?, ?)",
                    (
                        event["id"],
                        state["source_id"],
                        event["published_at"],
                        event["checked_at"],
                        payload,
                    ),
                )
                verified_new += cursor.rowcount
                if cursor.rowcount == 0:
                    conn.execute(
                        "UPDATE opportunity_news_events SET checked_at=?, payload=? WHERE id=?",
                        (event["checked_at"], payload, event["id"]),
                    )
            next_retry = now + (
                _SUCCESS_COOLDOWN if state["status"] == "success" else _FAILURE_COOLDOWN
            )
            conn.execute(
                """INSERT INTO opportunity_news_attempts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(as_of,source_id) DO UPDATE SET status=excluded.status,
                checked_at=excluded.checked_at,next_retry_at=excluded.next_retry_at,
                failure=excluded.failure,missing_original=excluded.missing_original,
                missing_date=excluded.missing_date,expired=excluded.expired""",
                (
                    day.isoformat(),
                    state["source_id"],
                    state["status"],
                    checked_at,
                    next_retry.isoformat(),
                    state["reason"],
                    state["missing_original"],
                    state["missing_date"],
                    state["expired"],
                ),
            )
            fingerprint = _source_fingerprint(
                next(source for source in to_run if source["id"] == state["source_id"])
            )
            conn.execute(
                "INSERT INTO opportunity_news_attempt_history "
                "(as_of,source_id,status,checked_at,failure,fingerprint) VALUES (?,?,?,?,?,?)",
                (
                    day.isoformat(),
                    state["source_id"],
                    state["status"],
                    checked_at,
                    state["reason"],
                    fingerprint,
                ),
            )
            conn.execute(
                "INSERT INTO opportunity_news_source_fingerprints VALUES (?,?,?) "
                "ON CONFLICT(as_of,source_id) DO UPDATE SET fingerprint=excluded.fingerprint",
                (day.isoformat(), state["source_id"], fingerprint),
            )
        if not pending:
            conn.execute("DELETE FROM opportunity_news_lease WHERE as_of=?", (day.isoformat(),))
        conn.commit()
    result = read_news(db_path, day, profs)
    source_map = {source["id"]: source for source in sources}
    failures = [
        _failure(state["source_id"], state["reason"], source_map)
        for _, state in output
        if state["status"] != "success"
    ]
    result["refresh"] = {
        "status": "partial" if failures else "fresh",
        "checked_at": checked_at,
        "attempted_sources": len(to_run),
        "verified_new": verified_new,
        "failures": failures,
    }
    return result
