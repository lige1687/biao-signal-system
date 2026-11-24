"""Today's holding review from existing records and cached technical analysis."""
from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import HTTPException, Request

from lei_signal.api import config
from lei_signal.api.bar_status import assess_bar_status
from lei_signal.plans.context import context_from_result
from lei_signal.plans.monitor import evaluate_plan
from lei_signal.plans.store import get_plan, list_plans
from lei_signal.portfolio.disclosure_context import disclosure_for_holding, load_disclosures

_SHANGHAI = ZoneInfo("Asia/Shanghai")
_MARKERS = re.compile(r"[（(]|联接|QDII|LOF|FOF|指数|增强", re.I)
_LINK_TABLE = "portfolio_holding_plan_links"


def _now() -> datetime:
    return datetime.now(_SHANGHAI)


def _db_path(request: Request, kind: str) -> str:
    return str(getattr(request.app.state, f"{kind}_db_path", None) or config.sqlite_path())


def _read_conn(path: str) -> sqlite3.Connection:
    # The shared connect() applies migrations, so GET uses SQLite's read-only URI.
    uri = Path(path).resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    return conn


def _table(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def _fund_suffix(code: str) -> str | None:
    if not re.fullmatch(r"\d{6}", code):
        return None
    if re.match(r"^5[01268]", code):
        return "SS"
    if re.match(r"^1[56]", code):
        return "SZ"
    return None


def _same_name(a: str, b: str) -> bool:
    a, b = re.sub(r"\s+", "", a), re.sub(r"\s+", "", b)
    if not a or not b:
        return False
    if a == b:
        return True
    longer, shorter = (a, b) if len(a) >= len(b) else (b, a)
    return shorter in longer and not _MARKERS.search(longer.replace(shorter, "", 1))


def _symbols(conn: sqlite3.Connection, holdings: list[sqlite3.Row], request: Request) -> dict[str, str]:
    from lei_signal.api.config import US_ETFS
    sources: list[tuple[str, str, str]] = []
    watchlist_path = _db_path(request, "watchlist")
    portfolio_path = _db_path(request, "portfolio")
    if Path(watchlist_path).resolve() != Path(portfolio_path).resolve():
        try:
            watchlist_conn = _read_conn(watchlist_path)
        except sqlite3.OperationalError:
            watchlist_conn = None
    else:
        watchlist_conn = conn
    if watchlist_conn is not None and _table(watchlist_conn, "watchlist_items"):
        for row in watchlist_conn.execute("SELECT symbol, display_name FROM watchlist_items"):
            symbol = str(row["symbol"] or "")
            code, dot, suffix = symbol.partition(".")
            if dot and _fund_suffix(code) == suffix.upper():
                name = row["display_name"] or ""
                service = getattr(request.app.state, "analysis_service", None)
                entry = getattr(service, "_entries", {}).get(symbol) if service else None
                if (
                    entry is not None and entry.result is not None
                    and entry.result.display_name
                    and entry.result.display_name != symbol
                ):
                    name = entry.result.display_name or name
                sources.append((symbol, name, "cn_exchange_fund"))
    if watchlist_conn is not None and watchlist_conn is not conn:
        watchlist_conn.close()
    sources.extend((etf.symbol, etf.display_name, "us_etf_catalog") for etf in US_ETFS)
    matched: dict[str, str] = {}
    for h in holdings:
        code = str(h["code"] or "").strip()
        hits: list[str] = []
        for symbol, name, identity in sources:
            if re.fullmatch(r"[A-Za-z]{1,6}", code):
                if (
                    identity == "us_etf_catalog" and "." not in symbol
                    and symbol.upper() == code.upper() and _same_name(h["name"], name)
                ):
                    hits.append(symbol)
            elif _fund_suffix(code) and identity == "cn_exchange_fund":
                base, _, suffix = symbol.partition(".")
                if base == code and suffix.upper() == _fund_suffix(code) and _same_name(h["name"], name):
                    hits.append(symbol)
        if len(hits) == 1:
            matched[h["holding_id"]] = hits[0]
    return matched


def _plan_dict(plan, linked_at: str | None = None) -> dict:
    return {
        "plan_id": plan.plan_id, "symbol": plan.symbol, "state": plan.state,
        "reason": plan.reason, "stop_plan_cn": plan.stop_plan_cn,
        "take_profit_plan_cn": plan.take_profit_plan_cn, "linked_at": linked_at,
    }


def _cached_result(request: Request, symbol: str):
    # Service.get() can fetch remote data and persist analysis. Cached entries only.
    service = getattr(request.app.state, "analysis_service", None)
    entry = getattr(service, "_entries", {}).get(symbol) if service else None
    return entry.result if entry is not None else None


def _forming(result, symbol: str, entry, now: datetime) -> bool:
    """A cached bar is usable only when that snapshot proves market close."""
    status = assess_bar_status(
        last_date=result.price_data.report.last_date,
        fetched_at=getattr(entry, "fetched_at", None),
        timezone=result.price_data.info.timezone,
        cache_fallback_used=bool(getattr(result, "cache_fallback_used", False)),
    )
    return status.status != "closed"


def _expected_bar_date(symbol: str, now: datetime) -> str | None:
    """Last complete weekday in the relevant exchange clock.

    The project calendar has no holiday table. A holiday therefore remains
    conservatively incomplete until a later bar proves the data current.
    """
    from lei_signal.data.calendar import DEFAULT_TRADING_CALENDAR

    cn = bool(_fund_suffix(symbol.partition(".")[0]))
    local = now.astimezone(_SHANGHAI if cn else ZoneInfo("America/New_York"))
    close_time = time(15) if cn else time(16)
    end = local.date() if local.time() >= close_time else local.date() - timedelta(days=1)
    last = DEFAULT_TRADING_CALENDAR.last_trading_day_in_range(
        end - timedelta(days=30), end
    )
    return last.date().isoformat() if last is not None else None


def build_workspace(request: Request) -> dict:
    """Build one read-only snapshot without migrations or market fetches."""
    now = _now()
    disclosures = load_disclosures(today=now.date())
    with closing(_read_conn(_db_path(request, "portfolio"))) as conn:
        if not _table(conn, "portfolio_holdings"):
            raise HTTPException(503, "持仓台账不可用")
        holdings = conn.execute(
            "SELECT * FROM portfolio_holdings ORDER BY market_value DESC, name"
        ).fetchall()
        groups = {
            r["group_key"]: r["name"]
            for r in conn.execute("SELECT group_key,name FROM portfolio_groups")
        } if _table(conn, "portfolio_groups") else {}
        as_of_row = conn.execute(
            "SELECT value FROM portfolio_meta WHERE key='as_of'"
        ).fetchone() if _table(conn, "portfolio_meta") else None
        as_of = as_of_row["value"] if as_of_row else ""
        navs = {
            r["holding_id"]: dict(r)
            for r in conn.execute(
                "SELECT holding_id,code,latest_nav,latest_nav_date,updated_at FROM portfolio_holdings_nav"
            )
        } if _table(conn, "portfolio_holdings_nav") else {}
        symbols = _symbols(conn, holdings, request)
        links = {
            r["holding_id"]: dict(r)
            for r in conn.execute(
                f"SELECT holding_id,plan_id,linked_at FROM {_LINK_TABLE}"
            )
        } if _table(conn, _LINK_TABLE) else {}
    plans = {}
    try:
        with closing(_read_conn(_db_path(request, "plans"))) as conn:
            if _table(conn, "trade_plans"):
                plans = {p.plan_id: p for p in list_plans(conn)}
    except sqlite3.OperationalError:
        pass

    total_value = sum(float(h["market_value"] or 0) for h in holdings)
    items = []
    for h in holdings:
        hid = h["holding_id"]
        nav_row = navs.get(hid)
        nav = {
            "value": nav_row["latest_nav"], "date": nav_row["latest_nav_date"],
            "updated_at": nav_row["updated_at"],
        } if (
            nav_row and nav_row["latest_nav"] is not None
            and nav_row["code"] == h["code"]
        ) else None
        symbol = symbols.get(hid)
        result = _cached_result(request, symbol) if symbol else None
        technical = None
        context = None
        if result is not None:
            try:
                from lei_signal.api.routes.symbols import CALENDAR_NOTE_CN, _assessment_dto
                assessment = _assessment_dto(result)
                context = context_from_result(result, cache_fallback_used=result.cache_fallback_used)
                service = getattr(request.app.state, "analysis_service", None)
                cache_entry = getattr(service, "_entries", {}).get(symbol) if service else None
                report = getattr(getattr(result, "price_data", None), "report", None)
                bar_state = assess_bar_status(
                    last_date=getattr(report, "last_date", None),
                    fetched_at=getattr(cache_entry, "fetched_at", None),
                    timezone=getattr(getattr(result.price_data, "info", None), "timezone", None),
                    cache_fallback_used=bool(getattr(result, "cache_fallback_used", False)),
                )
                technical = {
                    "assessment": assessment.model_dump(mode="json"),
                    "meta": {
                        "provider": getattr(report, "provider", None),
                        "adjusted": getattr(report, "adjusted", None),
                        "data_time": cache_entry.fetched_at.isoformat() if cache_entry else None,
                        "last_bar_date": context.last_bar_date,
                        "cache_fallback_used": bool(result.cache_fallback_used),
                        "is_intraday_forming": _forming(result, symbol, cache_entry, now),
                        "bar_status": bar_state.status,
                        "bar_status_reason": bar_state.reason,
                        "cache_age_seconds": getattr(result, "cache_age_seconds", None),
                        "sqlite_persisted": getattr(result, "sqlite_persisted", None),
                        "persist_warning": getattr(cache_entry, "persist_conflict", None),
                        "data_warnings": list(getattr(report, "warnings", ()) or ()),
                        "calendar_note_cn": CALENDAR_NOTE_CN,
                    },
                }
            except Exception:
                # A partial cached result is a gap, never evidence of no trigger.
                technical = None
                context = None
        linked = links.get(hid)
        plan_obj = plans.get(linked["plan_id"]) if linked else None
        valid_plan = (
            plan_obj is not None and symbol is not None
            and plan_obj.symbol == symbol and plan_obj.state == "entered"
        )
        plan = _plan_dict(plan_obj, linked["linked_at"]) if valid_plan else None
        candidates = [
            _plan_dict(p) for p in plans.values()
            if symbol and p.symbol == symbol and p.state == "entered"
            and (not linked or p.plan_id != linked["plan_id"])
        ]
        gaps = []
        blockers = []
        if nav is None:
            gaps.append("缺少基金净值")
        if symbol is None:
            blockers.append("未能确认同一产品的技术行情")
        elif technical is None:
            blockers.append("同一产品的技术结果尚未就绪")
        if not valid_plan:
            blockers.append("尚未关联有效的持仓计划")
        if not h["as_of"]:
            blockers.append("持仓记录日期缺失")
        if technical and technical["meta"]["cache_fallback_used"]:
            blockers.append("技术行情使用了旧缓存")
        if technical and not technical["meta"]["last_bar_date"]:
            blockers.append("技术结果缺少行情日期")
        if technical and symbol:
            expected = _expected_bar_date(symbol, now)
            raw_date = technical["meta"]["last_bar_date"]
            try:
                bar_day = date.fromisoformat(raw_date)
                if bar_day.isoformat() != raw_date:
                    raise ValueError("Non-ISO bar date")
            except (TypeError, ValueError):
                blockers.append("技术行情日期格式无法核实")
            else:
                market_tz = _SHANGHAI if _fund_suffix(symbol.partition(".")[0]) else ZoneInfo("America/New_York")
                if bar_day > now.astimezone(market_tz).date():
                    blockers.append("技术行情日期晚于交易所当前日期，暂不能复核")
                elif expected is None or raw_date < expected:
                    blockers.append("技术行情日期早于最近应有的收盘日")
                    gaps.append("交易日历尚未覆盖节假日，休市期间需另行核实行情时效")
        service = getattr(request.app.state, "analysis_service", None)
        entry = getattr(service, "_entries", {}).get(symbol) if service and symbol else None
        if (
            technical and entry is not None
            and entry.fetched_at.astimezone(_SHANGHAI).date() < now.date()
        ):
            blockers.append("技术结果不是本次查看日读取的")
        if technical and entry is not None and entry.fetched_at > now:
            blockers.append("技术资料读取时间晚于当前时间，暂不能复核")
        if technical and technical["meta"]["bar_status"] == "unknown":
            blockers.append("无法核实这根日线是否已收盘")
        gaps.extend(blockers)
        alerts = []
        if not blockers and technical and not technical["meta"]["is_intraday_forming"]:
            alerts = evaluate_plan(plan_obj, context)
            # A hint that supervision cannot evaluate is not a clean no-trigger.
            if any(a.code == "MODULE_NOT_IMPLEMENTED" for a in alerts):
                blockers.append("原计划所属技术模块尚不能监督")
                gaps.append("原计划所属技术模块尚不能监督")
        if blockers:
            status, title = "incomplete", "资料待补齐"
            reason = "；".join(blockers) + "。"
            next_step = "补齐同产品行情与原计划后再复核。"
        elif technical and technical["meta"]["is_intraday_forming"]:
            status, title = "waiting", "等待收盘确认"
            reason = "盘中价格和技术条件尚未定型。"
            next_step = "收盘后重新查看原计划条件。"
        else:
            actionable = [a for a in alerts if a.action_kind in ("EXIT", "REVIEW")]
            if actionable:
                status, title = "action_required", "原计划条件需要复核"
                reason = "；".join(a.next_step_cn for a in actionable)
                next_step = reason
            else:
                status, title = "no_trigger", "原计划暂无新触发"
                reason = "已关联计划和同产品技术结果，原计划条件目前未提示新动作。"
                next_step = "保留原持仓理由，待下一次行情更新再复核。"
        from lei_signal.portfolio.industry_context import cached_industry_reference
        disclosure = disclosure_for_holding(h["code"], h["name"], disclosures)
        items.append({
            "holding_id": hid, "name": h["name"], "code": h["code"],
            "disclosure": disclosure,
            "industry_reference": cached_industry_reference(request, h["code"], h["name"], disclosure, now),
            "original_note": h["note"] or "",
            "group_name": groups.get(h["group_key"], "未分组"),
            "market_value": float(h["market_value"] or 0),
            "weight_pct": round(float(h["market_value"] or 0) / total_value * 100, 2) if total_value else 0,
            "return_pct": h["return_pct"], "holding_as_of": h["as_of"],
            "nav": nav, "symbol": symbol, "status": status,
            "title_cn": title, "reason_cn": reason, "next_step_cn": next_step,
            "gaps": gaps, "technical": technical, "plan": plan,
            "plan_candidates": candidates,
            "alerts": [
                {
                    "code": a.code, "severity": a.severity, "rule_id": a.rule_id,
                    "data_as_of": a.data_as_of,
                    "actionable_from": a.actionable_from,
                    "next_step_cn": a.next_step_cn,
                    "action_kind": a.action_kind, "caveat_cn": a.caveat_cn,
                    "evidence": a.evidence,
                }
                for a in alerts
            ],
        })
    order = {"action_required": 0, "waiting": 1, "incomplete": 2, "no_trigger": 3}
    items.sort(key=lambda x: (order[x["status"]], -x["market_value"], x["name"]))
    coverage = {
        "total": len(items),
        "with_nav": sum(x["nav"] is not None for x in items),
        "with_technical": sum(x["technical"] is not None for x in items),
        "with_plan": sum(x["plan"] is not None for x in items),
    }
    coverage.update({
        s: sum(x["status"] == s for x in items)
        for s in ("action_required", "waiting", "incomplete", "no_trigger")
    })
    return {
        "generated_at": now.isoformat(), "review_date": now.date().isoformat(),
        "as_of": as_of, "total_value": round(total_value, 2),
        "coverage": coverage, "items": items,
    }


def link_plan(request: Request, holding_id: str, plan_id: str) -> dict:
    """Explicit write: append link history; leave plans, holdings and trades untouched."""
    portfolio_path = _db_path(request, "portfolio")
    with closing(_read_conn(portfolio_path)) as conn:
        h = conn.execute(
            "SELECT holding_id,name,code FROM portfolio_holdings WHERE holding_id=?",
            (holding_id,),
        ).fetchone()
        if h is None:
            raise HTTPException(404, "持仓不存在")
        symbol = _symbols(conn, [h], request).get(holding_id)
    if symbol is None:
        raise HTTPException(422, "无法确认持仓与技术标的是同一产品")
    with closing(_read_conn(_db_path(request, "plans"))) as conn:
        plan = get_plan(conn, plan_id) if _table(conn, "trade_plans") else None
    if plan is None:
        raise HTTPException(404, "计划不存在")
    if plan.symbol != symbol or plan.state != "entered":
        raise HTTPException(422, "计划必须属于同一产品且已进入持仓状态")
    linked_at = _now().isoformat()
    conn = sqlite3.connect(portfolio_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            f"CREATE TABLE IF NOT EXISTS {_LINK_TABLE} "
            "(holding_id TEXT PRIMARY KEY, plan_id TEXT NOT NULL, linked_at TEXT NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS portfolio_holding_plan_link_history "
            "(holding_id TEXT NOT NULL, plan_id TEXT NOT NULL, linked_at TEXT NOT NULL)"
        )
        old = conn.execute(
            f"SELECT plan_id,linked_at FROM {_LINK_TABLE} WHERE holding_id=?", (holding_id,)
        ).fetchone()
        if old and old[0] == plan_id:
            linked_at = old[1]
        else:
            conn.execute(
                "INSERT INTO portfolio_holding_plan_link_history VALUES (?,?,?)",
                (holding_id, plan_id, linked_at),
            )
            conn.execute(
                f"INSERT INTO {_LINK_TABLE} VALUES (?,?,?) "
                "ON CONFLICT(holding_id) DO UPDATE SET "
                "plan_id=excluded.plan_id,linked_at=excluded.linked_at",
                (holding_id, plan_id, linked_at),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return _plan_dict(plan, linked_at)
