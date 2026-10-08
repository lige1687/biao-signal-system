"""Read-only packets for the user's 11:35 and 14:40 chat briefings.

This module aggregates existing API evidence. It does not calculate signals,
place trades, update holdings, or interpret free-text plans as executable rules.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import urlopen
from uuid import uuid4
from zoneinfo import ZoneInfo

SHANGHAI = ZoneInfo("Asia/Shanghai")


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
        "code": item.get("code"), "name": item.get("name"),
        "nav_value": nav.get("value"), "nav_date": nav.get("date"),
        "status": item.get("status"), "gaps": item.get("gaps", []),
        "plan_id": plan.get("plan_id"), "plan_version": plan.get("version"),
        "plan": plan, "technical": {"assessment": tech.get("assessment"),
            "meta": {key: meta.get(key) for key in ("last_bar_date", "provider", "adjusted", "is_intraday_forming", "cache_fallback_used")}} if tech else None,
        "alerts": item.get("alerts", []),
    }


def _trade_changes(sources: dict, previous: dict | None) -> dict:
    source = sources.get("trades", {})
    old = (previous or {}).get("trade_ledger", {})
    comparable = bool(old.get("available"))
    before = {row["trade_id"]: row for row in old.get("records", [])}
    records, changes = [], []
    for trade in (source.get("data") or {}).get("trades", []):
        row = {key: trade.get(key) for key in (
            "trade_id", "fund_code", "fund_name", "side", "amount", "trade_date",
            "price_status", "priced_nav", "plan_id", "plan_version_id", "note", "created_at")}
        records.append(row)
        if comparable and row != before.get(row["trade_id"]):
            changes.append({"kind": "updated" if row["trade_id"] in before else "new", "record": row})
    return {
        "available": bool(source.get("ok")), "first_observation": not comparable,
        "records": records, "changes": changes,
        "pending_pricing": [row["trade_id"] for row in records if row["price_status"] != "priced"],
        "reconciliation_note": "成交记录变化不等于旧持仓快照已更新。系统定价可能采用交易日或更早净值；不能当作平台确认的成交份额，不能用此台账推断完整持仓。",
    }


def build_packet(sources: dict, *, slot: str, now: datetime,
                 previous: dict | None = None, authors: list | None = None) -> dict:
    if slot not in {"1135", "1440"}:
        raise ValueError("slot must be 1135 or 1440")
    if now.tzinfo is None:
        raise ValueError("an aware timestamp is required")
    now = now.astimezone(SHANGHAI)
    workspace = sources.get("workspace", {}).get("data") or {}
    items = workspace.get("items") or []
    old = {x["holding_id"]: x for x in (previous or {}).get("holdings", [])}
    first = previous is None
    holdings, changes = [], []
    for item in items:
        hid = item["holding_id"]
        facts = _facts(item)
        changed = [] if first else [key for key, value in facts.items()
                                   if value != old.get(hid, {}).get("facts", {}).get(key)]
        row = {"holding_id": hid, "name": item.get("name"), "code": item.get("code"),
               "group_name": item.get("group_name"), "holding_as_of": item.get("holding_as_of"),
               "facts": facts, "changed_fields": changed}
        holdings.append(row)
        if changed:
            changes.append({"holding_id": hid, "name": item.get("name"), "fields": changed})
    current_ids = {x["holding_id"] for x in holdings}
    removed = [hid for hid in old if hid not in current_ids] if workspace else []

    news_data = sources.get("news", {}).get("data") or {}
    start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    news, blogger_yesterday, unqualified = [], [], []
    for item in news_data.get("items", []):
        stamp = _published_at(item)
        if stamp is None or stamp > now:
            unqualified.append({"id": item.get("id"), "reason": "发布时间缺失、无时区或晚于本次核对"})
            continue
        if stamp < start:
            continue
        row = {key: item.get(key) for key in (
            "id", "title", "url", "source", "source_name", "published_at", "ingested_at",
            "symbols", "summary", "content", "direction", "importance", "llm_note")}
        row["content_basis"] = "已保存正文或字幕，仍需核范围" if row.get("content") else "仅标题或简介，不能概括完整视频建议"
        if item.get("source") == "bilibili" and stamp.date() == start.date():
            blogger_yesterday.append(row)
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
            qualified = (plan.get("state") == "entered" and bool(item.get("technical"))
                         and not item.get("gaps") and not meta.get("is_intraday_forming")
                         and item.get("status") in {"action_required", "no_trigger"})
            review.append({
                "holding_id": item["holding_id"], "name": item.get("name"),
                "state": "按系统原计划逐项复核" if qualified else "原计划或可用行情不足，不能判定安全或失效",
                "plan": plan or None, "system_alerts": item.get("alerts", []) if qualified else [],
                "gaps": item.get("gaps", []),
                "user_stated_context": [entry for entry in user_context if entry.get("fund_code") == item.get("code")],
                "execution_note": "逐条保留 data_as_of 与 actionable_from；盘中触及不自动等于收盘确认，提醒不等于成交。",
            })
    return {
        "schema_version": 1, "slot": slot, "generated_at": now.isoformat(),
        "mode": "information_only" if slot == "1135" else "confirmed_plan_review",
        "holding_record_as_of": workspace.get("as_of"),
        "initial_holdings_confirmation": {"date": "2026-10-08", "count": 29,
            "scope": "用户确认9月4日清单当时仍适用；后续以已确认变化为准，原金额不当作现值。"},
        "coverage": workspace.get("coverage", {}), "first_observation": first,
        "previous_packet_at": (previous or {}).get("generated_at"),
        "holdings": holdings, "changes": changes, "removed_since_previous": removed,
        "trade_ledger": _trade_changes(sources, previous),
        "market_background": {key: sources.get(key, {}) for key in ("cn", "us")},
        "news": news, "blogger_yesterday": blogger_yesterday,
        "configured_authors": authors or [], "unqualified_news": unqualified,
        "news_coverage": {"returned": len(news_data.get("items", [])), "total": news_data.get("total"),
                          "truncated": len(news_data.get("items", [])) < (news_data.get("total") or 0),
                          "last_run": (sources.get("news_status", {}).get("data") or {}).get("last_run"),
                          "note": "无条目不代表无消息；检查抓取状态、发布时间和是否截断。持仓关联需证据，不能按标题猜。"},
        "plan_review": review,
        "user_stated_context": user_context,
        "user_context_note": "用户原话与待整理记录不是已确认的监控计划，也不是新增交易；未知目标和失效条件不得代填。",
        "quantitative_evidence": {"win_rate": None, "reason": "本聚合器不估计概率；仅可引用有对象、时期、样本数和来源的既有研究。"},
        "source_status": {key: {k: value.get(k) for k in ("url", "retrieved_at", "ok", "error")}
                          for key, value in sources.items()},
        "limitations": ["本次定时核对不是连续盯盘。", "未核交易日历；无当日资料不能推出休市或无触发。",
                        "场外基金净值、指数与场内ETF价格不可互换。", "基本面与博主观点仅作背景，不改技术条件。"],
    }


def fetch_sources(base: str, now: datetime) -> dict:
    parsed = urlparse(base)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.username:
        raise ValueError("only the local system HTTP API is supported")
    since = (now.astimezone(SHANGHAI) - timedelta(days=1)).date().isoformat()
    routes = {"workspace": "/api/portfolio/workspace", "cn": "/api/fundamentals/observations?market=cn",
              "us": "/api/fundamentals/observations?market=us", "plans": "/api/plans", "trades": "/api/copilot/trades", "news_status": "/api/news/status",
              "news": "/api/news/items?" + urlencode({"date_from": since, "limit": 200, "with_content": "true"})}

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
    since = (now.astimezone(SHANGHAI) - timedelta(days=1)).date().isoformat()
    rows, total = store.query_items(date_from=since, limit=200, include_content=True)
    items = [dict(row) for row in rows]
    while rows and len(items) < total:
        rows, total = store.query_items(date_from=since, limit=200, offset=len(items), include_content=True)
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
            return {"items": items, "total": total, "receipt": receipt, "receipt_path": str(path), "refresh_skipped": True}
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
    from lei_signal.newsfeed.sources.bilibili import BilibiliClient
    from lei_signal.newsfeed.store import NewsStore

    directory.mkdir(parents=True, exist_ok=True)
    started = datetime.now(SHANGHAI).isoformat()
    store = NewsStore(directory / "news-source-cache.db")
    cfg = load_config()
    extra_errors = []
    try:
        try:
            client = BilibiliClient(directory / "bili-cookies.json")
        except Exception as exc:
            client = None
            extra_errors.append({"source": "bilibili", "error": str(exc)[:200]})
            cfg = {**cfg, "bili_ups": []}  # no fallback to an outside-repo cookie path
        stats, errors = _collect_all(store, cfg, full=False, bili_client=client)
        errors += extra_errors
        items, total = _recent_news(store, now)
        receipt = {"started_at": started, "finished_at": datetime.now(SHANGHAI).isoformat(),
                   "status": "partial" if errors and stats else "failed" if errors else "ok",
                   "per_source": stats, "errors": errors, "total_recent": total,
                   "production_news_database_updated": False, "model_calls": 0, "content_deletions": 0}
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
        receipt = {"started_at": now.isoformat(), "finished_at": datetime.now(SHANGHAI).isoformat(),
                   "status": "failed", "per_source": {},
                   "errors": [{"source": "collector", "error": f"{type(exc).__name__}: {str(exc)[:200]}"}],
                   "production_news_database_updated": False, "model_calls": 0, "content_deletions": 0}
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
    parser.add_argument("--refresh-news", action="store_true", help="collect sources without model scoring, deletion or production writes")
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
        sources["news"] = {"ok": fresh["receipt"]["status"] != "failed", "data": fresh,
                           "url": fresh["receipt_path"], "retrieved_at": now.isoformat(),
                           "error": fresh["receipt"]["errors"] or None}
        sources["news_status"] = {"ok": True, "data": {"last_run": fresh["receipt"]},
                                  "url": fresh["receipt_path"], "retrieved_at": now.isoformat()}
    packet = build_packet(sources, slot=args.slot, now=now, previous=previous, authors=authors)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / f"packet-{now.strftime('%Y%m%dT%H%M%S%f')}-{args.slot}-{uuid4().hex[:8]}.json"
    with output.open("x") as stream:
        json.dump(packet, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"packet": str(output.resolve()), "mode": packet["mode"], "coverage": packet["coverage"],
                      "changes": len(packet["changes"]), "news": len(packet["news"]),
                      "blogger_yesterday": len(packet["blogger_yesterday"]),
                      "trade_changes": len(packet["trade_ledger"]["changes"]),
                      "news_source_errors": (packet["news_coverage"].get("last_run") or {}).get("errors", []),
                      "failed_sources": [key for key, value in packet["source_status"].items() if not value["ok"]]}, ensure_ascii=False))
    return 0 if packet["source_status"]["workspace"]["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
