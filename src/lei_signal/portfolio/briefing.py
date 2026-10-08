"""Read-only packets for the user's 11:35 and 14:40 chat briefings.

This module aggregates existing API evidence. It does not calculate signals,
place trades, update holdings, or interpret free-text plans as executable rules.
"""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import urlopen
from uuid import uuid4
from zoneinfo import ZoneInfo

SHANGHAI = ZoneInfo("Asia/Shanghai")
BLOGGER_CALENDAR = (
    Path(__file__).resolve().parents[3] / "configs/portfolio-briefing-calendar.v1.json"
)


def blogger_window(now: datetime, calendar_path: Path | None = None) -> dict:
    """A qualified publication day, independent of trading-signal calendars."""
    result = {
        "status": "unavailable",
        "market": "cn_a_share",
        "timezone": "Asia/Shanghai",
        "date": None,
        "start": None,
        "end_exclusive": None,
    }
    try:
        if now.tzinfo is None:
            raise ValueError("aware timestamp required")
        now = now.astimezone(SHANGHAI)
        path = calendar_path or BLOGGER_CALENDAR
        cfg = json.loads(path.read_text())
        if not isinstance(cfg, dict):
            raise ValueError("calendar must be an object")
        if (
            cfg.get("schema_version") != 1
            or cfg.get("market") != "cn_a_share"
            or cfg.get("timezone") != "Asia/Shanghai"
        ):
            raise ValueError("unsupported calendar metadata")
        lower, upper = (
            date.fromisoformat(cfg["coverage_start"]),
            date.fromisoformat(cfg["coverage_end"]),
        )
        published = datetime.fromisoformat(cfg["published_at"])
        if published.tzinfo is None or published > now or not lower <= now.date() <= upper:
            raise ValueError("calendar coverage/publication does not qualify this observation")
        closed = set()
        for left, right in cfg["closed_ranges"]:
            cursor, end = date.fromisoformat(left), date.fromisoformat(right)
            if not lower <= cursor <= end <= upper or (end - cursor).days > 31:
                raise ValueError("invalid closure range")
            while cursor <= end:
                closed.add(cursor)
                cursor += timedelta(days=1)
        cursor = now.date() - timedelta(days=1)
        while cursor >= lower and (cursor.weekday() >= 5 or cursor in closed):
            cursor -= timedelta(days=1)
        if cursor < lower:
            raise ValueError("previous trading day is outside calendar coverage")
        start = datetime.combine(cursor, datetime.min.time(), SHANGHAI)
        result.update(
            status="verified",
            date=cursor.isoformat(),
            start=start.isoformat(),
            end_exclusive=(start + timedelta(days=1)).isoformat(),
            calendar_source=cfg["source_url"],
            calendar_published_at=cfg["published_at"],
            calendar_coverage_start=lower.isoformat(),
            calendar_coverage_end=upper.isoformat(),
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result["error"] = str(exc)
    return result


def _news_since(now: datetime) -> str:
    window = blogger_window(now)
    yesterday = (now.astimezone(SHANGHAI) - timedelta(days=1)).date().isoformat()
    return min(yesterday, window["date"]) if window["date"] else yesterday


def _select_blogger_videos(videos: list[dict], window: dict) -> tuple[list[dict], dict]:
    start, end = (
        datetime.fromisoformat(window["start"]),
        datetime.fromisoformat(window["end_exclusive"]),
    )
    dated = [
        (v, datetime.fromtimestamp(v["created"], SHANGHAI)) for v in videos if v.get("created")
    ]
    oldest = min((stamp for _, stamp in dated), default=None)
    coverage = {
        "returned": len(videos),
        "list_limit": 10,
        "oldest_returned_at": oldest.isoformat() if oldest else None,
        "target_may_be_truncated": len(videos) >= 10 and (oldest is None or oldest >= start),
    }
    return [v for v, stamp in dated if start <= stamp < end], coverage


def _published_at(item: dict) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(item.get("published_at", "")).replace("Z", "+00:00"))
        return dt.astimezone(SHANGHAI) if dt.tzinfo else None
    except ValueError:
        return None


def _facts(item: dict) -> dict:
    """Only evidence changes count; refreshing a timestamp is not a change."""
    nav = item.get("nav") or {}
    plan = item.get("plan") or {}
    tech = item.get("technical") or {}
    meta = tech.get("meta") or {}
    return {
        "code": item.get("code"),
        "name": item.get("name"),
        "nav_value": nav.get("value"),
        "nav_date": nav.get("date"),
        "status": item.get("status"),
        "gaps": item.get("gaps", []),
        "plan_id": plan.get("plan_id"),
        "plan_version": plan.get("version"),
        "plan": plan,
        "technical": {
            "assessment": tech.get("assessment"),
            "meta": {
                key: meta.get(key)
                for key in (
                    "last_bar_date",
                    "provider",
                    "adjusted",
                    "is_intraday_forming",
                    "cache_fallback_used",
                )
            },
        }
        if tech
        else None,
        "alerts": item.get("alerts", []),
    }


def _usable_product_name(value, code) -> str | None:
    if not isinstance(value, str):
        return None
    name = value.strip()
    if not name or name == str(code or "").strip() or name in {"未知", "名称未知", "--"}:
        return None
    return name


def _product_names(items: list[dict], sources: dict, previous: dict | None) -> dict[str, str]:
    """Resolve names only from records carrying the exact same product code."""
    names: dict[str, str] = {}

    def remember(code, value, *, replace=False):
        key = str(code or "").strip()
        name = _usable_product_name(value, key)
        if key and name and (replace or key not in names):
            names[key] = name

    # The current holding record is the primary identity source.
    for item in items:
        remember(item.get("code"), item.get("name"), replace=True)
    # A name attached to that same holding's net asset value can fill a gap.
    for item in items:
        nav = item.get("nav") or {}
        for field in ("fund_name", "product_name"):
            remember(item.get("code"), nav.get(field))
    # Preserve identity for a holding removed from the current snapshot.
    for item in (previous or {}).get("holdings", []):
        remember(item.get("code"), item.get("display_name") or item.get("name"))
    # A transaction ledger may be the only record for a newly recorded trade.
    for trade in (sources.get("trades", {}).get("data") or {}).get("trades") or []:
        remember(trade.get("fund_code"), trade.get("fund_name"))
    return names


def _trade_changes(sources: dict, previous: dict | None, names: dict[str, str]) -> dict:
    source = sources.get("trades", {})
    old = (previous or {}).get("trade_ledger", {})
    comparable = bool(old.get("available"))
    before = {row["trade_id"]: row for row in old.get("records", [])}
    records, changes = [], []
    for trade in (source.get("data") or {}).get("trades", []):
        row = {
            key: trade.get(key)
            for key in (
                "trade_id",
                "fund_code",
                "fund_name",
                "side",
                "amount",
                "trade_date",
                "price_status",
                "priced_nav",
                "plan_id",
                "plan_version_id",
                "note",
                "created_at",
            )
        }
        row["display_name"] = names.get(str(row.get("fund_code") or "").strip(), "名称未知")
        records.append(row)
        if comparable and row != before.get(row["trade_id"]):
            changes.append(
                {"kind": "updated" if row["trade_id"] in before else "new", "record": row}
            )
    return {
        "available": bool(source.get("ok")),
        "first_observation": not comparable,
        "records": records,
        "changes": changes,
        "pending_pricing": [row["trade_id"] for row in records if row["price_status"] != "priced"],
        "reconciliation_note": (
            "成交记录变化不等于旧持仓快照已更新。系统定价可能采用交易日或更"
            "早净值；不能当作平台确认的成交份额，不能用此台账推断完整持仓。"
        ),
    }


def build_packet(
    sources: dict,
    *,
    slot: str,
    now: datetime,
    previous: dict | None = None,
    authors: list | None = None,
) -> dict:
    if slot not in {"1135", "1440"}:
        raise ValueError("slot must be 1135 or 1440")
    if now.tzinfo is None:
        raise ValueError("an aware timestamp is required")
    now = now.astimezone(SHANGHAI)
    workspace = sources.get("workspace", {}).get("data") or {}
    items = workspace.get("items") or []
    names = _product_names(items, sources, previous)
    old = {x["holding_id"]: x for x in (previous or {}).get("holdings", [])}
    first = previous is None
    holdings, changes = [], []
    for item in items:
        hid = item["holding_id"]
        facts = _facts(item)
        changed = (
            []
            if first
            else [
                key
                for key, value in facts.items()
                if value != old.get(hid, {}).get("facts", {}).get(key)
            ]
        )
        row = {
            "holding_id": hid,
            "name": item.get("name"),
            "display_name": _usable_product_name(item.get("name"), item.get("code"))
            or names.get(str(item.get("code") or "").strip(), "名称未知"),
            "code": item.get("code"),
            "group_name": item.get("group_name"),
            "holding_as_of": item.get("holding_as_of"),
            "facts": facts,
            "changed_fields": changed,
        }
        holdings.append(row)
        if changed:
            changes.append(
                {
                    "holding_id": hid,
                    "name": item.get("name"),
                    "code": item.get("code"),
                    "display_name": row["display_name"],
                    "fields": changed,
                }
            )
    current_ids = {x["holding_id"] for x in holdings}
    removed = (
        [
            {
                "holding_id": hid,
                "code": old[hid].get("code"),
                "display_name": names.get(str(old[hid].get("code") or "").strip(), "名称未知"),
            }
            for hid in old
            if hid not in current_ids
        ]
        if workspace
        else []
    )

    news_data = sources.get("news", {}).get("data") or {}
    start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    window = blogger_window(now)
    news, blogger_previous, unqualified = [], [], []
    for item in news_data.get("items", []):
        stamp = _published_at(item)
        if stamp is None or stamp > now:
            unqualified.append(
                {"id": item.get("id"), "reason": "发布时间缺失、无时区或晚于本次核对"}
            )
            continue
        is_blogger = item.get("source") == "bilibili"
        if is_blogger:
            if window["status"] != "verified" or stamp.date().isoformat() != window["date"]:
                continue
        elif stamp < start:
            continue
        row = {
            key: item.get(key)
            for key in (
                "id",
                "title",
                "url",
                "source",
                "source_name",
                "published_at",
                "ingested_at",
                "symbols",
                "summary",
                "content",
                "direction",
                "importance",
                "llm_note",
            )
        }
        row["content_basis"] = (
            "已保存正文或字幕，仍需核范围"
            if row.get("content")
            else "仅标题或简介，不能概括完整视频建议"
        )
        if is_blogger:
            blogger_previous.append(row)
        else:
            news.append(row)

    review = []
    user_context = (sources.get("user_context", {}).get("data") or {}).get("entries", [])
    full_plans = sources.get("plans", {}).get("data") or []
    full_plans = {p["plan_id"]: p for p in full_plans if isinstance(p, dict) and p.get("plan_id")}
    if slot == "1440":
        for item in items:
            plan = item.get("plan") or {}
            plan = full_plans.get(plan.get("plan_id"), plan)
            meta = (item.get("technical") or {}).get("meta") or {}
            # The server's completeness decision remains authoritative.
            qualified = (
                plan.get("state") == "entered"
                and bool(item.get("technical"))
                and not item.get("gaps")
                and not meta.get("is_intraday_forming")
                and not meta.get("cache_fallback_used")
                and bool(meta.get("last_bar_date"))
                and str(meta["last_bar_date"])[:10] <= now.date().isoformat()
                and all(
                    a.get("data_as_of")
                    and a.get("actionable_from")
                    and str(a["data_as_of"])[:10] <= now.date().isoformat()
                    and str(a["actionable_from"])[:10] <= now.date().isoformat()
                    for a in item.get("alerts", [])
                )
                and item.get("status") in {"action_required", "no_trigger"}
            )
            review.append(
                {
                    "holding_id": item["holding_id"],
                    "name": item.get("name"),
                    "display_name": _usable_product_name(item.get("name"), item.get("code"))
                    or names.get(str(item.get("code") or "").strip(), "名称未知"),
                    "state": "按系统原计划逐项复核"
                    if qualified
                    else "原计划或可用行情不足，不能判定安全或失效",
                    "plan": plan or None,
                    "system_alerts": item.get("alerts", []) if qualified else [],
                    "gaps": item.get("gaps", []),
                    "user_stated_context": [
                        entry
                        for entry in user_context
                        if entry.get("fund_code") == item.get("code")
                    ],
                    "execution_note": (
                        "逐条保留 data_as_of 与 actionable"
                        "_from；盘中触及不自动等于收盘确认，提醒不等于成交。"
                    ),
                }
            )
    return {
        "schema_version": 1,
        "slot": slot,
        "generated_at": now.isoformat(),
        "mode": "information_only" if slot == "1135" else "confirmed_plan_review",
        "holding_record_as_of": workspace.get("as_of"),
        "initial_holdings_confirmation": {
            "date": "2026-10-08",
            "count": 29,
            "scope": "用户确认9月4日清单当时仍适用；后续以已确认变化为准，原金额不当作现值。",
        },
        "coverage": workspace.get("coverage", {}),
        "first_observation": first,
        "previous_packet_at": (previous or {}).get("generated_at"),
        "holdings": holdings,
        "changes": changes,
        "removed_since_previous": removed,
        "trade_ledger": _trade_changes(sources, previous, names),
        "market_background": {key: sources.get(key, {}) for key in ("cn", "us")},
        "news": news,
        "blogger_previous_trading_day": blogger_previous,
        "blogger_window": window,
        "blogger_yesterday": blogger_previous,
        "blogger_yesterday_compatibility_note": (
            "兼容字段，内容已改为上个A股交易日；日期以blogger_window为准，不是自然昨天。"
        ),
        "configured_authors": authors or [],
        "unqualified_news": unqualified,
        "news_coverage": {
            "returned": len(news_data.get("items", [])),
            "total": news_data.get("total"),
            "truncated": len(news_data.get("items", [])) < (news_data.get("total") or 0),
            "last_run": (sources.get("news_status", {}).get("data") or {}).get("last_run"),
            "note": (
                "无条目不代表无消息；检查抓取状态、发布时间"
                "和是否截断。持仓关联需证据，不能按标题猜。"
            ),
        },
        "plan_review": review,
        "user_stated_context": user_context,
        "user_context_note": (
            "用户原话与待整理记录不是已确认的监控计划，也不是新增交易；未知目标和失效条件不得代填。"
        ),
        "quantitative_evidence": {
            "win_rate": None,
            "reason": "本聚合器不估计概率；仅可引用有对象、时期、样本数和来源的既有研究。",
        },
        "source_status": {
            key: {k: value.get(k) for k in ("url", "retrieved_at", "ok", "error")}
            for key, value in sources.items()
        },
        "limitations": [
            "本次定时核对不是连续盯盘。",
            "未核交易日历；无当日资料不能推出休市或无触发。",
            "场外基金净值、指数与场内ETF价格不可互换。",
            "基本面与博主观点仅作背景，不改技术条件。",
        ],
    }


def fetch_sources(base: str, now: datetime) -> dict:
    parsed = urlparse(base)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost"}
        or parsed.username
    ):
        raise ValueError("only the local system HTTP API is supported")
    since = _news_since(now)
    routes = {
        "workspace": "/api/portfolio/workspace",
        "cn": "/api/fundamentals/observations?market=cn",
        "us": "/api/fundamentals/observations?market=us",
        "plans": "/api/plans",
        "trades": "/api/copilot/trades",
        "news_status": "/api/news/status",
        "news": "/api/news/items?"
        + urlencode({"date_from": since, "limit": 200, "with_content": "true"}),
    }

    def fetch(pair):
        key, route = pair
        url = base.rstrip("/") + route
        result = {"url": url, "retrieved_at": datetime.now(SHANGHAI).isoformat()}
        try:
            with urlopen(url, timeout=15) as response:
                result.update(ok=True, data=json.load(response))
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            result.update(ok=False, error=str(exc), data=None)
        return key, result

    with ThreadPoolExecutor(max_workers=5) as pool:
        return dict(pool.map(fetch, routes.items()))


def _recent_news(store, now: datetime) -> tuple[list[dict], int]:
    since = _news_since(now)
    rows, total = store.query_items(date_from=since, limit=200, include_content=True)
    items = [dict(row) for row in rows]
    while rows and len(items) < total:
        rows, total = store.query_items(
            date_from=since, limit=200, offset=len(items), include_content=True
        )
        items.extend(dict(row) for row in rows)
    for item in items:
        if isinstance(item.get("symbols"), str):
            item["symbols"] = json.loads(item["symbols"])
    return items, total


def cached_news(directory: Path, now: datetime) -> dict | None:
    """Retain the latest isolated collection when a follow-up skips a refresh."""
    if not (directory / "news-source-cache.db").is_file():
        return None
    from lei_signal.newsfeed.store import NewsStore

    for path in sorted(directory.glob("news-receipt-*.json"), reverse=True):
        try:
            receipt = json.loads(path.read_text())
            if datetime.fromisoformat(receipt["finished_at"]) > now:
                continue
            store = NewsStore(directory / "news-source-cache.db")
            try:
                items, total = _recent_news(store, now)
            finally:
                store.close()
            return {
                "items": items,
                "total": total,
                "receipt": receipt,
                "receipt_path": str(path),
                "refresh_skipped": True,
            }
        except (ValueError, KeyError):
            continue
    return None


def refresh_news(directory: Path, now: datetime) -> dict:
    """Reuse existing collectors in a separate receipt store, without cleanup,
    scoring, external messages, or changes to the production news database.
    Anonymous Bilibili requests use a cookie file inside this output directory.
    """
    from lei_signal.newsfeed.config_loader import load_config
    from lei_signal.newsfeed.pipeline import _collect_all
    from lei_signal.newsfeed.sources.bilibili import BilibiliClient, fetch_new_up_items
    from lei_signal.newsfeed.store import NewsStore

    directory.mkdir(parents=True, exist_ok=True)
    started = datetime.now(SHANGHAI).isoformat()
    store = NewsStore(directory / "news-source-cache.db")
    cfg = load_config()
    extra_errors = []
    window = blogger_window(now)
    blogger_coverage = {}

    class WindowClient(BilibiliClient):
        def fetch_up_videos(self, mid: int, limit: int = 5) -> list[dict]:
            videos = super().fetch_up_videos(mid, limit=10)
            selected, coverage = _select_blogger_videos(videos, window)
            blogger_coverage[str(mid)] = coverage
            if coverage["target_may_be_truncated"]:
                extra_errors.append(
                    {
                        "source": f"bilibili:{mid}",
                        "error": "最新10条列表未覆盖目标日边界，目标视频可能遗漏",
                    }
                )
            return selected

    try:
        try:
            client = (
                WindowClient(directory / "bili-cookies.json")
                if window["status"] == "verified"
                else None
            )
            if client is None:
                extra_errors.append(
                    {"source": "blogger_calendar", "error": window.get("error", "目标日未核实")}
                )
        except Exception as exc:
            client = None
            extra_errors.append({"source": "bilibili", "error": str(exc)[:200]})
            cfg = {**cfg, "bili_ups": []}  # no fallback to an outside-repo cookie path
        # Ordinary news keeps its existing watermark. Blogger day replay ignores
        # that watermark so Monday/holiday windows cannot be lost after a prior fetch.
        stats, errors = _collect_all(store, {**cfg, "bili_ups": []}, full=False, bili_client=None)
        if client is not None:
            for author in cfg.get("bili_ups") or []:
                mid = int(author.get("mid") or 0)
                if not mid:
                    continue
                key = f"bilibili:{mid}"
                try:
                    items, _ = fetch_new_up_items(
                        client,
                        mid,
                        str(author.get("name") or mid),
                        None,
                        lookback_iso=window["start"],
                        title_blocklist=list(cfg.get("bili_title_blocklist") or ["直播回放"]),
                        max_duration_sec=cfg.get("bili_max_duration_sec", 1800),
                    )
                    stats[key] = (
                        store.insert_items([item.to_row() for item in items]) if items else 0
                    )
                except Exception as exc:
                    errors.append({"source": key, "error": str(exc)[:200]})
        errors += extra_errors
        items, total = _recent_news(store, now)
        receipt = {
            "started_at": started,
            "finished_at": datetime.now(SHANGHAI).isoformat(),
            "status": "partial" if errors and stats else "failed" if errors else "ok",
            "per_source": stats,
            "errors": errors,
            "total_recent": total,
            "blogger_window": window,
            "blogger_list_coverage": blogger_coverage,
            "production_news_database_updated": False,
            "model_calls": 0,
            "content_deletions": 0,
        }
        path = directory / f"news-receipt-{now.strftime('%Y%m%dT%H%M%S%f')}-{uuid4().hex[:8]}.json"
        with path.open("x") as stream:
            json.dump(receipt, stream, ensure_ascii=False, indent=2)
        return {"items": items, "total": total, "receipt": receipt, "receipt_path": str(path)}
    finally:
        store.close()


def collect_news_safely(directory: Path, now: datetime, *, refresh: bool = True) -> dict | None:
    """A news import/cache failure must not suppress holdings and plan evidence."""
    try:
        return refresh_news(directory, now) if refresh else cached_news(directory, now)
    except Exception as exc:
        receipt = {
            "started_at": now.isoformat(),
            "finished_at": datetime.now(SHANGHAI).isoformat(),
            "status": "failed",
            "per_source": {},
            "errors": [{"source": "collector", "error": f"{type(exc).__name__}: {str(exc)[:200]}"}],
            "production_news_database_updated": False,
            "model_calls": 0,
            "content_deletions": 0,
        }
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"news-receipt-{now.strftime('%Y%m%dT%H%M%S%f')}-{uuid4().hex[:8]}.json"
        with path.open("x") as stream:
            json.dump(receipt, stream, ensure_ascii=False, indent=2)
        return {"items": [], "total": 0, "receipt": receipt, "receipt_path": str(path)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slot", choices=("1135", "1440"), required=True)
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--refresh-news",
        action="store_true",
        help="collect sources without model scoring, deletion or production writes",
    )
    parser.add_argument(
        "--refresh-video-content",
        action="store_true",
        help="read public target-day audio with existing local ASR; never upload audio",
    )
    args = parser.parse_args()
    now = datetime.now(SHANGHAI)
    previous = None
    if args.output_dir.exists():
        for path in sorted(args.output_dir.glob("packet-*.json"), reverse=True):
            try:
                candidate = json.loads(path.read_text())
                stamp = datetime.fromisoformat(candidate["generated_at"])
                if candidate.get("coverage", {}).get("total") and stamp.tzinfo and stamp < now:
                    previous = candidate
                    break
            except (ValueError, KeyError):
                continue
    cfg = Path(__file__).resolve().parents[3] / "configs/newsfeed.json"
    authors = json.loads(cfg.read_text()).get("bili_ups", []) if cfg.exists() else []
    fresh = collect_news_safely(args.output_dir / "sources", now, refresh=args.refresh_news)
    # Read local market/plan facts after slow external collectors finish.
    now = datetime.now(SHANGHAI)
    sources = fetch_sources(args.base, now)
    context_path = args.output_dir / "user-context.json"
    if context_path.exists():
        source = {"url": str(context_path.resolve()), "retrieved_at": now.isoformat()}
        try:
            context = json.loads(context_path.read_text())
            if not isinstance(context, dict) or not isinstance(context.get("entries"), list):
                raise ValueError("user context must contain an entries list")
            source.update(ok=True, data=context)
        except (ValueError, OSError) as exc:
            source.update(ok=False, error=str(exc), data=None)
        sources["user_context"] = source
    if fresh:
        sources["news"] = {
            "ok": fresh["receipt"]["status"] != "failed",
            "data": fresh,
            "url": fresh["receipt_path"],
            "retrieved_at": now.isoformat(),
            "error": fresh["receipt"]["errors"] or None,
        }
        sources["news_status"] = {
            "ok": True,
            "data": {"last_run": fresh["receipt"]},
            "url": fresh["receipt_path"],
            "retrieved_at": now.isoformat(),
        }
    packet = build_packet(sources, slot=args.slot, now=now, previous=previous, authors=authors)
    from lei_signal.integrations.bilibili_content import collect_video_content

    video = collect_video_content(
        packet["blogger_previous_trading_day"],
        authors,
        (packet.get("blogger_window") or {}).get("date"),
        args.output_dir / "video-content",
        refresh=args.refresh_video_content,
    )
    packet["blogger_previous_trading_day"] = video["items"]
    packet["blogger_yesterday"] = video["items"]
    packet["video_content_coverage"] = {
        "errors": video["errors"],
        "results": [
            {k: v for k, v in row.items() if k not in {"transcript_text", "segments"}}
            for row in video["results"]
        ],
        "note": "平台字幕与本机转写分别标示；转写需校正，不把文字自动改为买卖条件。",
    }
    # Read account/market facts again after slow audio processing, preserving each source date.
    if args.refresh_video_content:
        now = datetime.now(SHANGHAI)
        updated_sources = fetch_sources(args.base, now)
        sources.update(
            {k: v for k, v in updated_sources.items() if k not in {"news", "news_status"}}
        )
        refreshed = build_packet(
            sources, slot=args.slot, now=now, previous=previous, authors=authors
        )
        refreshed.update(
            {
                k: packet[k]
                for k in (
                    "blogger_previous_trading_day",
                    "blogger_yesterday",
                    "video_content_coverage",
                )
            }
        )
        packet = refreshed
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = (
        args.output_dir
        / f"packet-{now.strftime('%Y%m%dT%H%M%S%f')}-{args.slot}-{uuid4().hex[:8]}.json"
    )
    with output.open("x") as stream:
        json.dump(packet, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    from lei_signal.portfolio.brief_render import render_brief

    report = output.with_suffix(".md")
    report.write_text(render_brief(packet), encoding="utf-8")
    print(
        json.dumps(
            {
                "packet": str(output.resolve()),
                "report": str(report.resolve()),
                "mode": packet["mode"],
                "coverage": packet["coverage"],
                "changes": len(packet["changes"]),
                "news": len(packet["news"]),
                "blogger_previous_trading_day": len(packet["blogger_previous_trading_day"]),
                "blogger_window": packet["blogger_window"],
                "trade_changes": len(packet["trade_ledger"]["changes"]),
                "news_source_errors": (packet["news_coverage"].get("last_run") or {}).get(
                    "errors", []
                ),
                "failed_sources": [
                    key for key, value in packet["source_status"].items() if not value["ok"]
                ],
            },
            ensure_ascii=False,
        )
    )
    return 0 if packet["source_status"]["workspace"]["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
