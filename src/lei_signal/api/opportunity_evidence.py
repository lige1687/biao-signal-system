"""Read-only, source-bound evidence for an on-open opportunity review.

This module ranks no trades. It preserves existing rule results and makes
missing identity, dates, and contrary evidence visible to the reviewer.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote
from zoneinfo import ZoneInfo

from fastapi import Request

from lei_signal.api import opportunity_context
from lei_signal.api.config import INDEX_OVERRIDES, US_ETFS
from lei_signal.api.opportunity_signals import build_signal_rows
from lei_signal.api.portfolio_workspace import (
    _expected_bar_date,
    _forming,
    _read_conn,
    build_workspace,
)
from lei_signal.api.routes.opportunities import build_review
from lei_signal.api.routes.symbols import _assessment_dto
from lei_signal.api.sell_signals import extract_sell_signals
from lei_signal.api.watchlist import list_watchlist
from lei_signal.copilot.subjects import display_name

_SHANGHAI = ZoneInfo("Asia/Shanghai")
_CN_ETF = re.compile(r"(?:5[01268]\d{4}\.SS|1[56]\d{4}\.SZ)\Z")
_ROLES = {"support", "opposition", "unknown", "condition", "context", "lead"}
_INTRADAY_GAP = "盘中行情尚未收盘确认"
_SELL_KIND_RULE = {
    "top_structure_confirmed": "top_structure",
    "key_wave_black": "key_wave_black",
    "structure_invalidated": "bottom_structure",
    "exit_proxy": "exit_ema20_costbasis",
}


def _day(value: object, today: date) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value[:10])
    except ValueError:
        return None
    return parsed.isoformat() if value[:10] == parsed.isoformat() and parsed <= today else None


def _evidence(
    role: str,
    text: str,
    source: str,
    when: str | None,
    name: str,
    scope: str = "same_product",
    provenance: str = "existing_rule",
    source_ref: str = "",
    *,
    category: str = "technical",
    public: bool = True,
    published_at: str | None = None,
    checked_at: str | None = None,
    report_date: str | None = None,
    narrative_kind: str | None = None,
    relevance: str | None = None,
    fetched_at: str | None = None,
    quality_status: str | None = None,
) -> dict:
    assert role in _ROLES
    body = {
        "role": role,
        "text": str(text),
        "source": source,
        "source_ref": source_ref,
        "date": when,
        "object_name": name,
        "scope": scope,
        "provenance": provenance,
        "category": category,
        "public": public,
        "published_at": published_at,
        "checked_at": checked_at,
        "report_date": report_date,
    }
    if narrative_kind:
        body["narrative_kind"] = narrative_kind
    if relevance:
        body["relevance"] = relevance
    if provenance == "local_macro_observation":
        body["fetched_at"] = fetched_at
        body["quality_status"] = quality_status
    digest = hashlib.sha256(
        json.dumps(body, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()[:20]
    return {"id": f"ev_{digest}", **body}


def _append(card: dict, row: dict) -> None:
    if not row["source_ref"]:
        row["source_ref"] = (
            "/portfolio"
            if card["subject"]["kind"] == "holding"
            else "/symbol/" + quote(card["subject"]["id"], safe="")
        )
        payload = {k: v for k, v in row.items() if k != "id"}
        row["id"] = (
            "ev_"
            + hashlib.sha256(
                json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
            ).hexdigest()[:20]
        )
    if row["id"] not in {e["id"] for e in card["evidence"]}:
        card["evidence"].append(row)


def _card(subject: dict, intent: str) -> dict:
    return {
        "candidate_key": f"{subject['key']}:{intent}",
        "subject": subject,
        "intent": intent,
        "status": "unknown",
        "headline": "资料待核对",
        "agent_eligible": False,
        "data_as_of": None,
        "evidence": [],
        "searches": [],
        "limitations": [],
    }


def _has_public_context(card: dict) -> bool:
    return any(
        e.get("public") and e.get("category") in {"fundamentals", "industry", "news"}
        for e in card.get("evidence") or []
    )


def _share_public_context(source: dict, target: dict) -> None:
    """Use one exact set of public facts for both directions of a holding."""
    target["evidence"] = [
        e
        for e in target["evidence"]
        if not (e.get("public") and e.get("category") in {"fundamentals", "industry", "news"})
    ]
    for row in source["evidence"]:
        if row.get("public") and row.get("category") in {"fundamentals", "industry", "news"}:
            _append(target, dict(row))
    if source.get("narrative_focus"):
        target["narrative_focus"] = dict(source["narrative_focus"])


def _technical(
    request: Request, symbol: str, now: datetime
) -> tuple[object | None, object | None, list[str]]:
    service = getattr(request.app.state, "analysis_service", None)
    entry = getattr(service, "_entries", {}).get(symbol) if service else None
    result = getattr(entry, "result", None)
    problems: list[str] = []
    if result is None or getattr(entry, "error", None) or getattr(result, "symbol", None) != symbol:
        return None, None, ["同一产品的缓存技术资料不可用"]
    fetched = getattr(entry, "fetched_at", None)
    if (
        fetched is None
        or fetched.tzinfo is None
        or fetched > now
        or fetched.astimezone(_SHANGHAI).date() != now.date()
    ):
        problems.append("技术资料读取时间无法确认为本次查看日")
    if getattr(result, "cache_fallback_used", False):
        problems.append("技术资料使用旧缓存")
    try:
        assessment = _assessment_dto(result)
        bar = _day(assessment.as_of, now.date())
        expected = _expected_bar_date(symbol, now)
        if not bar or not expected or bar < expected:
            problems.append("技术行情日期过旧、未来或无法核实")
        if _forming(result, symbol, entry, now):
            problems.append(_INTRADAY_GAP)
        return result, assessment, problems
    except (AttributeError, TypeError, ValueError, IndexError) as exc:
        return None, None, [f"技术资料无法解析：{type(exc).__name__}"]


def _factor_text(factor: object) -> str:
    def getter(field):
        return factor.get(field) if isinstance(factor, dict) else getattr(factor, field, None)

    label = getter("label_cn") or getter("text_cn") or getter("reason_cn") or getter("name_cn")
    detail = getter("detail_cn") or getter("description_cn")
    rule = getter("rule_id") or getter("code")
    return "；".join(
        str(piece) for piece in (label, detail, f"规则 {rule}" if rule else None) if piece
    )


def _news(
    request: Request,
    symbol: str,
    name: str,
    intent: str,
    now: datetime,
    *,
    fund_name_required: bool = False,
) -> tuple[list[dict], dict]:
    """Both local directions with exact symbol membership; labels remain leads."""
    service = getattr(request.app.state, "newsfeed_service", None)
    path = getattr(service, "_db_path", None)
    if not path or not Path(path).is_file():
        return [], {
            "name": "同产品本地反向消息",
            "status": "unavailable",
            "detail": "本地消息库未配置",
        }
    try:
        with closing(_read_conn(str(path))) as conn:
            where = (
                " FROM news_items WHERE published_at >= ? AND direction IN ('bullish','bearish') "
                "AND CASE WHEN json_valid(symbols) THEN json_type(symbols) ELSE NULL END = 'array' "
                "AND EXISTS (SELECT 1 FROM json_each(CASE WHEN json_valid(symbols) "
                "THEN symbols ELSE '[]' END) WHERE value = ?)"
            )
            params = ((now.date() - timedelta(days=7)).isoformat(), symbol)
            total = conn.execute("SELECT COUNT(*)" + where, params).fetchone()[0]
            rows = conn.execute(
                "SELECT id,title,source,source_name,url,published_at,symbols,direction"
                + where
                + " ORDER BY published_at DESC LIMIT 101",
                params,
            ).fetchall()
    except (sqlite3.Error, OSError) as exc:
        return [], {
            "name": "同产品本地反向消息",
            "status": "unavailable",
            "detail": f"读取失败：{type(exc).__name__}",
        }
    leads: list[dict] = []
    for row in rows:
        if fund_name_required and name not in (row["title"] or ""):
            continue
        try:
            published_at = datetime.fromisoformat(row["published_at"])
        except (TypeError, ValueError):
            continue
        if published_at.tzinfo is None or published_at > now:
            continue
        published = _day(row["published_at"], now.date())
        url = str(row["url"] or "")
        if not published or not url.startswith("https://"):
            continue
        leads.append(
            _evidence(
                "lead",
                ("偏正向" if row["direction"] == "bullish" else "偏负向")
                + "（自动分类，未核原文）："
                + row["title"],
                row["source_name"] or row["source"] or "本地消息",
                published,
                name,
                "narrative",
                "news_lead",
                url,
                category="news",
                published_at=row["published_at"],
                checked_at=now.date().isoformat(),
            )
        )
        if len(leads) == 5:
            break
    return leads, {
        "name": "同产品本地反向消息",
        "status": "checked",
        "detail": (
            f"精确代码{'且完整基金名' if fund_name_required else ''}"
            f"匹配到 {len(leads)} 条近七日正反线索；"
            f"查询共 {total} 条、最多核前 100 条；标题与模型方向未核原文"
        ),
    }


def _public_context(request: Request, card: dict, symbol: str, name: str, now: datetime) -> None:
    """Attach curated public facts and cached, unverified headline leads."""
    rows = opportunity_context.public_sources(symbol, name, today=now.date())
    focus = opportunity_context.narrative_focus(symbol, name)
    if focus["kind"] != "unknown" or "narrative_focus" not in card:
        card["narrative_focus"] = focus
    for row in rows:
        _append(
            card,
            _evidence(
                "context",
                row["text"],
                row["source"],
                row["date"],
                name,
                row["scope"],
                row["provenance"],
                row["source_ref"],
                category=row["category"],
                public=True,
                published_at=row["published_at"],
                checked_at=row["checked_at"],
                report_date=row["report_date"],
                narrative_kind=row.get("narrative_kind"),
                relevance=row.get("relevance"),
            ),
        )
        card["limitations"].extend(row["limitations"])
    card["searches"].append(
        {
            "name": "同产品官方公开资料",
            "status": "checked" if rows else "unavailable",
            "detail": f"准确代码和名称匹配到 {len(rows)} 条有日期和来源的资料"
            if rows
            else "尚无准确代码和名称匹配的已核公开资料",
        }
    )
    if request is not None and focus.get("market") in {"cn", "us"}:
        from lei_signal.api.opportunity_macro import read_macro

        macro = read_macro(request, focus["market"], now)
        for row in macro["rows"]:
            _append(card, _evidence(
                "context", row["text"], row["source"], row["date"], name,
                "narrative", row["provenance"], row["source_ref"],
                category="fundamentals", published_at=row.get("published_at"),
                report_date=row.get("report_date"), checked_at=row.get("checked_at"),
                narrative_kind="macro", relevance="market_context",
                fetched_at=row.get("fetched_at"), quality_status=row.get("quality_status"),
            ))
            card["limitations"].extend(row.get("limitations") or [])
        card["searches"].append({
            "name": "已有宏观资料", "status": macro["status"],
            "detail": f"按产品市场读取 {len(macro['rows'])} 条已有宏观观察；各项保留原资料日",
            "error": macro.get("error") or None, "checked_at": macro.get("checked_at"),
        })
        if macro.get("stale_rows"):
            card["limitations"].append(
                f"{len(macro['stale_rows'])}项宏观资料已过展示时效，未用于当前分析"
            )
    news = opportunity_context.cached_news(request, symbol, name)
    card["searches"].append(
        {"name": "同产品公开消息标题", "status": news["status"], "detail": news["detail"]}
    )
    for item in news["leads"]:
        _append(
            card,
            _evidence(
                "lead",
                "未核原文标题：" + item["title"],
                item["source_name"],
                _day(item["published_at"], now.date()),
                name,
                "narrative",
                "unverified_news",
                item["source_url"],
                category="news",
                public=True,
                published_at=item["published_at"],
                checked_at=news.get("checked_on"),
            ),
        )
    risk_news = opportunity_context.cached_risk_news(request, symbol, name)
    card["searches"].append(
        {
            "name": "同产品风险方向标题检索",
            "status": risk_news["status"],
            "detail": risk_news["detail"],
            "query": risk_news["query"],
            "checked_at": risk_news["checked_at"],
            "count": risk_news["count"],
            "error": risk_news["error"],
        }
    )
    ordinary_titles = {(item["source_url"], item["title"]) for item in news["leads"]}
    for item in risk_news["leads"]:
        if (item["source_url"], item["title"]) in ordinary_titles:
            # The second query is visible in searches, but one article is one lead.
            continue
        _append(
            card,
            _evidence(
                "lead",
                "风险方向查询的未核原文标题（不代表已证实利空）：" + item["title"],
                item["source_name"] + "（风险方向标题检索）",
                _day(item["published_at"], now.date()),
                name,
                "narrative",
                "unverified_news",
                item["source_url"],
                category="news",
                public=True,
                published_at=item["published_at"],
                checked_at=risk_news["checked_at"],
            ),
        )


def _fund_disclosure(card: dict, item: dict, now: datetime) -> None:
    disclosure = item.get("disclosure") or {}
    name = card["subject"]["name"]
    if disclosure.get("status") != "available":
        card["searches"].append(
            {
                "name": "同份额基金公开披露",
                "status": "unavailable",
                "detail": disclosure.get("summary") or "没有可核的直接股票前十资料",
            }
        )
        return
    card["narrative_focus"] = {
        "kind": "mixed", "label": "已披露持仓行业", "market": None,
        "topics": sorted({stock["industry_label"] for stock in disclosure.get("holdings", [])
                          if stock.get("industry_label")}),
    }
    report = _day(disclosure.get("report_date"), now.date())
    published = _day(disclosure.get("published_at"), now.date())
    checked = _day(disclosure.get("checked_at"), now.date())
    source = disclosure.get("source_name") or "基金披露"
    url = disclosure.get("official_report_url") or disclosure.get("source_url") or ""
    url = url if str(url).startswith("https://") else ""
    intro = (
        f"{disclosure.get('report_period') or '季度待核'}直接股票前十；"
        f"成分截止日{report or '未知'}；发布日期{published or '未知'}；"
        f"来源核查日{checked or '未知'}；已披露股票覆盖基金净值"
        f"{disclosure.get('coverage_pct')}%；未覆盖{disclosure.get('unknown_pct')}%；"
        f"有来源的行业标签覆盖{disclosure.get('industry_coverage_pct')}%；"
        f"行业未知{disclosure.get('industry_unknown_pct')}%。"
    )
    common = dict(
        category="fundamentals",
        public=True,
        published_at=disclosure.get("published_at"),
        checked_at=disclosure.get("checked_at"),
        report_date=report,
        narrative_kind="industry", relevance="direct",
    )
    _append(
        card,
        _evidence("context", intro, source, report, name, "narrative", "disclosed", url, **common),
    )
    for stock in disclosure.get("holdings") or []:
        if not stock.get("stock_code") or not stock.get("stock_name"):
            continue
        text = (
            f"披露股票：{stock['stock_name']}（{stock['stock_code']}），"
            f"占基金净值{stock.get('weight_pct')}%。"
        )
        _append(
            card,
            _evidence(
                "context", text, source, report, name, "narrative", "disclosed", url, **common
            ),
        )
        label = stock.get("industry_label")
        industry_url = stock.get("industry_source_url")
        if label and isinstance(industry_url, str) and industry_url.startswith("https://"):
            _append(
                card,
                _evidence(
                    "context",
                    f"{stock['stock_name']}（{stock['stock_code']}）已核业务行业：{label}；"
                    "这是公司业务参照，不代表基金当前完整行业分布。",
                    "公司业务公开资料",
                    report,
                    name,
                    "narrative",
                    "business_reference",
                    industry_url,
                    category="industry",
                    public=True,
                    published_at=disclosure.get("published_at"),
                    checked_at=disclosure.get("checked_at"),
                    report_date=report,
                ),
            )
    seen_reference_sources = set()
    for reference in (item.get("industry_reference") or {}).get("references") or []:
        reference_symbol, reference_name = reference.get("symbol"), reference.get("name")
        if not reference_symbol or not reference_name:
            continue
        for row in opportunity_context.public_sources(
            reference_symbol, reference_name, today=now.date()
        ):
            if (
                row["scope"] not in {"industry_reference", "narrative"}
                or row["source_ref"] in seen_reference_sources
            ):
                continue
            seen_reference_sources.add(row["source_ref"])
            _append(
                card,
                _evidence(
                    "context",
                    row["text"] + " 本基金仅按已披露业务关联参考，当前行业权重及调仓未知。",
                    row["source"],
                    row["date"],
                    name,
                    "industry_reference",
                    row["provenance"],
                    row["source_ref"],
                    category=row["category"],
                    public=True,
                    published_at=row["published_at"],
                    checked_at=row["checked_at"],
                    report_date=row["report_date"],
                    narrative_kind=row.get("narrative_kind"),
                    relevance=row.get("relevance"),
                ),
            )
            card["limitations"].extend(row["limitations"])
    card["limitations"].extend(disclosure.get("limitations") or [])
    if disclosure.get("source_recheck_required"):
        card["limitations"].append("基金披露来源今日尚未重查，不能认定为最新披露")
    card["searches"].append(
        {
            "name": "同份额基金公开披露",
            "status": "checked",
            "detail": "仅直接股票前十及已核行业；其余资产和披露后调仓未知",
        }
    )


def _add_technical_evidence(
    card: dict,
    assessment: object,
    intent: str,
    when: str | None,
    current: bool,
    provisional: bool = False,
) -> None:
    name = card["subject"]["name"]
    supporting = getattr(assessment, "supports", ()) or ()
    opposing = getattr(assessment, "conflicts", ()) or ()
    for role, factors, source in (
        ("support" if intent == "buy" else "opposition", supporting, "技术支持项"),
        ("opposition" if intent == "buy" else "context", opposing, "技术冲突项"),
    ):
        for factor in factors:
            rule_id = (
                factor.get("rule_id")
                if isinstance(factor, dict)
                else getattr(factor, "rule_id", None)
            )
            background_only = rule_id in {"bottom_c_lifecycle", "volume_profile_proxy"}
            fact_text = _factor_text(factor)
            if rule_id == "bottom_c_lifecycle":
                fact_text = "历史结构背景，未绑定近期入场依据：" + fact_text
            elif rule_id == "volume_profile_proxy":
                fact_text = (
                    "按历史成交量估计的价格分布，仅供背景参考；当前实际持有人与卖压未知。"
                    + fact_text
                )
            observed = "盘中观察（尚未收盘）：" + fact_text if provisional else fact_text
            _append(
                card,
                _evidence(
                    role if (current or provisional) and not background_only else "context",
                    observed,
                    ("历史结构与成交分布背景" if background_only else source)
                    + ("" if current else "（历史或盘中）"),
                    when,
                    name,
                    provenance="research_proxy"
                    if rule_id in {"macd_strength", "volume_profile_proxy"}
                    else "existing_rule",
                ),
            )
    for risk in getattr(assessment, "risks", ()) or ():
        risk_code = getattr(risk, "code", None)
        old_top_background = risk_code in {"top_plus_black", "active_top_structure"}
        if old_top_background:
            observed = (
                f"现有风险状态：{getattr(risk, 'label_cn', '顶部风险')}；此处未标明该价位"
                "属于本次顶部触发，具体触发日和价位以带日期的结构信号为准"
            )
        else:
            observed = _factor_text(risk)
        if provisional:
            observed = "盘中观察（尚未收盘）：" + observed
        _append(
            card,
            _evidence(
                ("opposition" if intent == "buy" else "context")
                if (current or provisional) and not old_top_background
                else "context",
                observed,
                "技术风险项",
                when,
                name,
            ),
        )
    for field, label in (("stage_cn", "阶段"), ("color_cn", "颜色"), ("risk_state_cn", "风险状态")):
        value = getattr(assessment, field, None)
        if value:
            _append(card, _evidence("context", f"{label}：{value}", "现有技术判定", when, name))
    dimensions = getattr(assessment, "dimensions", {}) or {}
    for key in ("强度(MACD)", "长周期"):
        if dimensions.get(key):
            _append(
                card,
                _evidence(
                    "context",
                    f"{key}：{dimensions[key]}",
                    "技术维度与盲区补齐",
                    when,
                    name,
                    provenance="research_proxy" if key == "强度(MACD)" else "existing_rule",
                ),
            )
    if dimensions.get("强度(MACD)"):
        _append(
            card,
            _evidence(
                "context",
                "MACD只表示均线强度；破线看LEI颜色，均线拐头看长周期维度；交叉本身不构成买卖点。",
                "MACD口径与盲区",
                when,
                name,
                provenance="research_proxy",
            ),
        )


def _qualified_candidates(
    review: object, bar: str | None, today: date, frame: object = None
) -> tuple[list[object], int]:
    from lei_signal.api.sell_signals import RECENCY_BARS

    recent_days: set[str] = set()
    if frame is not None and getattr(frame, "index", None) is not None and len(frame.index):
        dates = [ts.date().isoformat() for ts in frame.index]
        if dates[-1] == bar:
            recent_days = set(dates[-RECENCY_BARS:])
    raw = [
        c
        for c in list(review.candidates)
        + [c for group in review.resonance_groups for c in group.candidates]
        if c.direction == "long"
    ]
    valid: list[object] = []
    for candidate in raw:
        if candidate.state not in ("watch", "confirmed"):
            continue
        anchor = candidate.last_state_change_date or candidate.opened_date
        anchor_day = _day(anchor, today)
        if not anchor_day or not bar or anchor_day > bar:
            continue
        if anchor_day not in recent_days and (frame is not None or anchor_day != bar):
            continue
        if candidate.opened_date:
            opened_day = _day(candidate.opened_date, today)
            if not opened_day or opened_day > bar:
                continue
        if review.degraded_cn and candidate.module == "C":
            continue
        valid.append(candidate)
    return valid, len(raw) - len(valid)


def _only_old_buy_candidates(review: object, bar: str | None, frame: object) -> bool:
    """Separate dated history from candidates rejected for invalid or future dates."""
    from lei_signal.api.sell_signals import RECENCY_BARS

    if frame is None or not len(frame.index) or frame.index[-1].date().isoformat() != bar:
        return False
    dates = [ts.date().isoformat() for ts in frame.index]
    recent = set(dates[-RECENCY_BARS:])
    candidates = [
        c
        for c in list(review.candidates)
        + [c for group in review.resonance_groups for c in group.candidates]
        if c.direction == "long"
    ]
    return bool(candidates) and all(
        c.state in {"watch", "confirmed"}
        and (anchor := c.last_state_change_date or c.opened_date) in dates
        and anchor not in recent
        for c in candidates
    )


def _add_dated_signal_evidence(
    card: dict, result: object, review: object | None, intent: str,
    *, current: bool, provisional: bool,
) -> set[str]:
    """Carry exact trigger dates and structure prices from the same analysis."""
    if result is None or getattr(result, "frame", None) is None:
        return set()
    source_review = review or SimpleNamespace(
        candidates=[], resonance_groups=[], historical_structures=[]
    )
    try:
        rows = build_signal_rows(result, source_review)
    except (AttributeError, TypeError, ValueError, IndexError):
        return set()
    recent_rows = [row for row in rows if row.get("is_recent")]
    historical_rows = [row for row in rows if not row.get("is_recent")]
    historical_rows.sort(
        key=lambda row: (row.get("state_changed_date") or row.get("event_date") or ""),
        reverse=True,
    )
    selected_history: list[dict] = []
    history_by_side = {"buy": 0, "sell": 0}
    for row in historical_rows:
        side = row.get("side")
        if side in history_by_side and history_by_side[side] < 3:
            selected_history.append(row)
            history_by_side[side] += 1
    if len(selected_history) < len(historical_rows):
        card["limitations"].append(
            "模型仅取买卖各最近三条历史信号核对解除状态；完整历史见 K 线信号清单"
        )
    name = card["subject"]["name"]
    current_sell_rules: set[str] = set()
    for row in recent_rows + selected_history:
        date_text = row.get("event_date")
        if not date_text:
            continue
        recent = bool(row.get("is_recent") and (current or provisional))
        if recent and row.get("side") == "sell" and row.get("rule_id"):
            current_sell_rules.add(row["rule_id"])
        if not recent or row.get("status") == "cleared":
            role = "context"
        elif row.get("side") == intent:
            role = "condition" if row.get("status") == "waiting" else "support"
        else:
            role = "opposition"
        facts = [f"触发日期 {date_text}", row.get("title") or "技术信号"]
        if row.get("age_bars") is not None:
            facts.append(f"距触发已过 {row['age_bars']} 根日 K")
        changed = row.get("state_changed_date")
        if changed and changed != date_text:
            facts.append(f"状态变化日期 {changed}")
        if row.get("summary"):
            facts.append(row["summary"])
        facts.extend(row.get("conditions") or [])
        facts.extend(f"仍需：{text}" for text in row.get("missing_conditions") or [])
        facts.extend(
            f"{price['label']} {price['value']:.4f}"
            for price in row.get("key_prices") or []
        )
        if row.get("invalidation_cn"):
            facts.append(f"解除或失效条件：{row['invalidation_cn']}")
        if row.get("next_step_cn"):
            facts.append(row["next_step_cn"])
        observed = "；".join(facts)
        if provisional and recent:
            observed = "盘中观察（尚未收盘）：" + observed
        _append(
            card,
            _evidence(
                role, observed,
                "同产品近期技术信号" if recent else "同产品历史技术信号",
                date_text, name, provenance=row.get("provenance") or "existing_rule",
            ),
        )
    return current_sell_rules


def _buy_card(request: Request, subject: dict, now: datetime) -> dict:
    card = _card(subject, "buy")
    symbol = subject.get("symbol") if subject.get("kind") == "holding" else subject["id"]
    name = subject["name"]
    result, assessment, problems = (
        _technical(request, symbol, now)
        if symbol
        else (None, None, ["持仓尚未对应到同一产品技术行情"])
    )
    card["limitations"].extend(problems)
    card["searches"].append(
        {
            "name": "同产品技术正反依据",
            "status": "checked" if assessment else "unavailable",
            "detail": "复用已缓存分析；核对阶段、支持、冲突和风险"
            if assessment
            else "无可解析缓存",
        }
    )
    if assessment:
        when = _day(assessment.as_of, now.date())
        provisional = problems == [_INTRADAY_GAP]
        card["data_as_of"] = when
        _add_technical_evidence(card, assessment, "buy", when, not problems, provisional)
        try:
            review = build_review(result, symbol=symbol, display_name=name)
            candidates, rejected = _qualified_candidates(
                review, when, now.date(), getattr(result, "frame", None)
            )
            detailed_sell = _add_dated_signal_evidence(
                card, result, review, "buy", current=not problems, provisional=provisional
            )
            if rejected:
                card["limitations"].append(
                    f"{rejected} 个候选日期无效、超过最近三根日 K、晚于行情或已降级，未计入当前机会"
                )
            for candidate in candidates:
                scenario_name = candidate.scenario_cn or candidate.rule_id or candidate.scenario_id
                source = f"买点条件 {scenario_name}"
                for text in candidate.satisfied_conditions:
                    observed = "盘中观察（尚未收盘）：" + text if provisional else text
                    _append(
                        card,
                        _evidence(
                            "support" if not problems or provisional else "context",
                            observed,
                            source,
                            when,
                            name,
                        ),
                    )
                for text in candidate.missing_conditions:
                    observed = "盘中观察（尚未收盘）：" + text if provisional else text
                    _append(
                        card,
                        _evidence(
                            "condition" if not problems or provisional else "context",
                            observed,
                            source,
                            when,
                            name,
                        ),
                    )
                if candidate.caveat_cn:
                    observed = (
                        "盘中观察（尚未收盘）：" + candidate.caveat_cn
                        if provisional
                        else candidate.caveat_cn
                    )
                    _append(
                        card,
                        _evidence(
                            "unknown",
                            observed,
                            f"{source}的方法限制",
                            when,
                            name,
                        ),
                    )
            if review.tradability:
                for reason in review.tradability.blocking_reasons:
                    observed = "盘中观察（尚未收盘）：" + reason if provisional else reason
                    _append(
                        card,
                        _evidence(
                            "opposition" if not problems or provisional else "context",
                            observed,
                            "可交易性检查",
                            when,
                            name,
                        ),
                    )
            if review.degraded_cn:
                _append(
                    card,
                    _evidence(
                        "unknown",
                        review.degraded_cn,
                        "候选方法与资料缺口",
                        when,
                        name,
                    ),
                )
            for signal in extract_sell_signals(result):
                if _SELL_KIND_RULE.get(getattr(signal, "kind", None)) in detailed_sell:
                    continue
                observed = signal.title + "：" + signal.reason_cn
                if provisional:
                    observed = "盘中观察（尚未收盘）：" + observed
                _append(
                    card,
                    _evidence(
                        "opposition" if not problems or provisional else "context",
                        observed,
                        "同产品反向技术迹象",
                        signal.available_date,
                        name,
                        provenance=signal.provenance,
                    ),
                )
            if provisional:
                if candidates or getattr(assessment, "risks", ()):
                    card["status"], card["headline"] = "waiting", "盘中观察，待收盘确认"
                    card["agent_eligible"] = True
                _append(
                    card,
                    _evidence(
                        "unknown",
                        "盘中技术事实尚未收盘确认，不能作为已成立买点",
                        "收盘状态检查",
                        when,
                        name,
                    ),
                )
            elif not problems:
                tradable = bool(review.tradability and review.tradability.tradable)
                confirmed = any(c.state == "confirmed" for c in candidates)
                if confirmed and tradable:
                    card["status"], card["headline"] = "candidate", "现有买点条件已成立，待人工复核"
                elif candidates and not tradable:
                    card["status"], card["headline"] = "review", "现有买点条件受阻，需复核"
                elif candidates:
                    card["status"], card["headline"] = "waiting", "现有买点条件仍在等待"
                elif _only_old_buy_candidates(review, when, getattr(result, "frame", None)):
                    card["status"], card["headline"] = (
                        "no_opportunity",
                        "近期无买点；旧候选仅作历史",
                    )
                elif (
                    rejected
                    or review.degraded_cn
                    or (
                        review.verdict != "none"
                        and any(
                            c.direction == "long"
                            for c in list(review.candidates)
                            + [c for group in review.resonance_groups for c in group.candidates]
                        )
                    )
                ):
                    card["status"], card["headline"] = "unknown", "近期买点候选无法确认"
                else:
                    card["status"], card["headline"] = "no_opportunity", "现有规则未发现近期买点"
                card["agent_eligible"] = card["status"] in ("candidate", "review", "waiting")
        except (AttributeError, TypeError, ValueError, IndexError) as exc:
            card["limitations"].append(f"买点审阅失败：{type(exc).__name__}")
    context_code = symbol or subject.get("code")
    leads, search = (
        _news(request, context_code, name, "buy", now, fund_name_required=not bool(symbol))
        if context_code
        else (
            [],
            {"name": "同产品本地正反消息", "status": "unavailable", "detail": "无法确认同产品代码"},
        )
    )
    for lead in leads:
        _append(card, lead)
    card["searches"].append(search)
    if context_code:
        _public_context(request, card, context_code, name, now)
    if _has_public_context(card):
        card["agent_eligible"] = True
    if problems:
        _append(
            card,
            _evidence(
                "unknown",
                "当前买点仍需新鲜、同产品、已收盘的技术资料核对",
                "资料时效检查",
                None,
                name,
            ),
        )
    return card


def _sell_card(request: Request, item: dict, now: datetime) -> dict:
    subject = {
        "key": f"holding:{item['holding_id']}",
        "kind": "holding",
        "id": str(item["holding_id"]),
        "name": item["name"],
        "code": item["code"],
    }
    card = _card(subject, "sell")
    name, symbol = item["name"], item.get("symbol")
    for gap in item.get("gaps") or ():
        card["limitations"].append(str(gap))
    if item.get("holding_as_of"):
        _append(
            card,
            _evidence(
                "context",
                "持仓记录日期",
                "持仓台账",
                _day(item["holding_as_of"], now.date()),
                name,
                public=False,
            ),
        )
    if item.get("original_note"):
        _append(
            card,
            _evidence(
                "context",
                item["original_note"],
                "原持仓备注",
                _day(item.get("holding_as_of"), now.date()),
                name,
                public=False,
            ),
        )
    if item.get("nav"):
        nav = item["nav"]
        _append(
            card,
            _evidence(
                "context",
                f"基金净值：{nav['value']}",
                "同份额净值记录",
                _day(nav.get("date"), now.date()),
                name,
                public=False,
            ),
        )
    _fund_disclosure(card, item, now)
    reference = item.get("industry_reference") or {}
    for row in reference.get("references") or ():
        technical = row.get("technical") or {}
        label = row.get("display_name") or row.get("name") or row.get("symbol")
        technical_date = _day(technical.get("as_of"), now.date())
        fresh = (
            technical_date is not None
            and not technical.get("stale", True)
            and not technical.get("is_intraday_forming", True)
            and not technical.get("cache_fallback_used", True)
        )
        description = (
            f"行业参考 {label}（{row.get('symbol') or '代码待核'}）："
            f"{technical.get('stage_cn') or '技术阶段未知'}；"
            f"颜色 {technical.get('color_cn') or '未知'}；"
            f"风险状态 {technical.get('risk_state_cn') or '未知'}；"
            f"行情{'已核收盘' if fresh else '时效或收盘状态待核'}；"
            "仅供核对相关业务"
        )
        ref_url = row.get("source_url") or ""
        _append(
            card,
            _evidence(
                "context",
                description,
                "行业 ETF 参考",
                technical_date,
                name,
                "industry_reference",
                "disclosed",
                ref_url if str(ref_url).startswith("https://") else "",
                category="industry",
                published_at=row.get("published_at"),
                checked_at=reference.get("reference_checked_on"),
                report_date=reference.get("report_date"),
            ),
        )
    for fact in reference.get("fundamentals") or ():
        when = _day(fact.get("published_at"), now.date())
        if when and fact.get("summary"):
            url = fact.get("source_url") or ""
            _append(
                card,
                _evidence(
                    "context",
                    f"{fact.get('kind') or '基金披露观点'}：{fact['summary']}",
                    "基金披露观点",
                    when,
                    name,
                    "narrative",
                    "disclosed",
                    url if str(url).startswith("https://") else "",
                    category="fundamentals",
                    published_at=fact.get("published_at"),
                    checked_at=reference.get("reference_checked_on"),
                    report_date=fact.get("report_date"),
                ),
            )
    result = assessment = None
    buy_review = None
    problems = ["持仓尚未对应到同一产品技术行情"] if not symbol else []
    if symbol:
        result, assessment, problems = _technical(request, symbol, now)
        card["limitations"].extend(problems)
        if assessment:
            when = _day(assessment.as_of, now.date())
            card["data_as_of"] = when
            provisional = problems == [_INTRADAY_GAP]
            _add_technical_evidence(card, assessment, "sell", when, not problems, provisional)
            if not problems:
                try:
                    buy_review = build_review(result, symbol=symbol, display_name=name)
                    candidates, _ = _qualified_candidates(
                        buy_review, when, now.date(), getattr(result, "frame", None)
                    )
                    if candidates:
                        _append(
                            card,
                            _evidence(
                                "opposition",
                                f"同产品买入条件：{buy_review.summary_cn}",
                                "同产品买点审阅",
                                when,
                                name,
                            ),
                        )
                except (AttributeError, TypeError, ValueError, IndexError) as exc:
                    card["limitations"].append(f"反向买点资料无法解析：{type(exc).__name__}")
    card["searches"].append(
        {
            "name": "持仓同产品技术正反依据",
            "status": "checked" if assessment else "unavailable",
            "detail": "只读同产品缓存" if assessment else "同产品缓存或身份缺失",
        }
    )
    provisional = problems == [_INTRADAY_GAP]
    detailed_sell = _add_dated_signal_evidence(
        card, result, buy_review, "sell", current=not problems, provisional=provisional
    )
    signals = extract_sell_signals(result) if result and (not problems or provisional) else []
    for signal in signals:
        if _SELL_KIND_RULE.get(getattr(signal, "kind", None)) in detailed_sell:
            continue
        observed = signal.title + "：" + signal.reason_cn
        if provisional:
            observed = "盘中观察（尚未收盘）：" + observed
        _append(
            card,
            _evidence(
                "support",
                observed,
                "同产品卖出迹象",
                signal.available_date,
                name,
                provenance=signal.provenance,
            ),
        )
    for alert in item.get("alerts") or ():
        _append(
            card,
            _evidence(
                "support"
                if not problems and alert.get("action_kind") in ("EXIT", "REVIEW")
                else "context",
                alert.get("next_step_cn") or alert.get("code") or "原计划提醒",
                "已关联原持仓计划",
                _day(alert.get("data_as_of"), now.date()),
                name,
                public=False,
            ),
        )
    plan = item.get("plan")
    if plan:
        for key, label in (
            ("reason", "原持仓理由"),
            ("stop_plan_cn", "原失效条件"),
            ("take_profit_plan_cn", "原止盈条件"),
        ):
            if plan.get(key):
                _append(
                    card,
                    _evidence(
                        "context",
                        f"{label}：{plan[key]}",
                        "已关联原持仓计划",
                        None,
                        name,
                        public=False,
                    ),
                )
    else:
        card["limitations"].append("原持仓计划未关联；现有迹象不能作为个人退出条件")
        _append(
            card,
            _evidence(
                "unknown", "缺少已确认的原持仓计划，无需补造历史理由", "计划关联检查", None, name
            ),
        )
    if provisional:
        if signals or (assessment and (assessment.conflicts or assessment.risks)):
            card["status"], card["headline"] = "waiting", "盘中观察，待收盘确认"
            card["agent_eligible"] = True
        _append(
            card,
            _evidence(
                "unknown",
                "盘中卖出迹象尚未收盘确认，不能作为个人退出条件",
                "收盘状态检查",
                card["data_as_of"],
                name,
            ),
        )
    elif not problems:
        if any(a.get("action_kind") in ("EXIT", "REVIEW") for a in item.get("alerts") or ()):
            card["status"], card["headline"] = "candidate", "原计划条件提示复核，待人工判断"
        elif signals:
            card["status"], card["headline"] = "review", "同产品出现卖出迹象，需结合原计划复核"
        elif plan:
            card["status"], card["headline"] = "no_opportunity", "现有原计划未提示新动作"
        else:
            card["status"], card["headline"] = "review", "持仓资料可复核，原计划仍未知"
        card["agent_eligible"] = card["status"] in ("candidate", "review")
    else:
        _append(
            card, _evidence("unknown", "缺少同一产品的新鲜技术资料", "资料时效检查", None, name)
        )
    if symbol or item.get("code"):
        leads, search = _news(
            request,
            symbol or str(item["code"]),
            name,
            "sell",
            now,
            fund_name_required=not bool(symbol),
        )
        for lead in leads:
            _append(card, lead)
        card["searches"].append(search)
        _public_context(request, card, symbol or str(item["code"]), name, now)
    else:
        card["searches"].append(
            {"name": "同产品本地反向消息", "status": "unavailable", "detail": "无法确认同产品代码"}
        )
    if card["status"] == "unknown" and any(
        e["public"]
        and (
            e["category"] in {"fundamentals", "news"}
            or (
                e["category"] == "industry"
                and (item.get("disclosure") or {}).get("status") == "available"
            )
        )
        for e in card["evidence"]
    ):
        card["agent_eligible"] = True
    return card


def _sell_symbol_card(request: Request, subject: dict, now: datetime) -> dict:
    """Observe an ETF/index exit condition without claiming a personal holding."""
    card = _card(subject, "sell")
    symbol, name = subject["id"], subject["name"]
    result, assessment, problems = _technical(request, symbol, now)
    card["limitations"].extend(problems)
    card["limitations"].append("仅观察同产品退出条件；没有对应持仓与原计划")
    if assessment:
        when = _day(assessment.as_of, now.date())
        card["data_as_of"] = when
        provisional = problems == [_INTRADAY_GAP]
        _add_technical_evidence(card, assessment, "sell", when, not problems, provisional)
        try:
            buy_review = build_review(result, symbol=symbol, display_name=name)
        except (AttributeError, TypeError, ValueError, IndexError):
            buy_review = None
        detailed_sell = _add_dated_signal_evidence(
            card, result, buy_review, "sell", current=not problems, provisional=provisional
        )
        signals = extract_sell_signals(result) if result and (not problems or provisional) else []
        for signal in signals:
            if _SELL_KIND_RULE.get(getattr(signal, "kind", None)) in detailed_sell:
                continue
            _append(
                card,
                _evidence(
                    "support" if not problems or provisional else "context",
                    ("盘中观察（尚未收盘）：" if provisional else "")
                    + signal.title
                    + "："
                    + signal.reason_cn,
                    "同产品卖出迹象",
                    signal.available_date,
                    name,
                    provenance=signal.provenance,
                ),
            )
        if provisional and signals:
            card["status"], card["headline"] = "waiting", "退出迹象待收盘确认"
            card["agent_eligible"] = True
        elif not problems:
            card["status"], card["headline"] = (
                ("review", "同产品出现退出迹象，仅供观察")
                if signals
                else ("no_opportunity", "现有规则未发现同产品退出迹象")
            )
            card["agent_eligible"] = bool(signals)
    leads, search = _news(request, symbol, name, "sell", now)
    for lead in leads:
        _append(card, lead)
    card["searches"].append(search)
    _public_context(request, card, symbol, name, now)
    if _has_public_context(card):
        card["agent_eligible"] = True
    return card


def build_snapshot(request: Request) -> dict:
    """Collect one deterministic board without market fetching or financial writes."""
    now = datetime.now(_SHANGHAI)
    limitations: list[str] = []
    items: list[dict] = []
    watch_path = getattr(request.app.state, "watchlist_db_path", None)
    watch = []
    if watch_path and Path(watch_path).is_file():
        try:
            with closing(_read_conn(str(watch_path))) as conn:
                watch = list_watchlist(conn)
        except (sqlite3.Error, OSError) as exc:
            limitations.append(f"自选列表读取失败：{type(exc).__name__}")
    else:
        limitations.append("自选列表不可用")
    indices = set(INDEX_OVERRIDES)
    us_etfs = {e.symbol for e in US_ETFS}
    seen: set[str] = set()
    for w in watch:
        symbol = w.symbol
        if symbol in seen or not (
            symbol in indices or symbol in us_etfs or _CN_ETF.fullmatch(symbol)
        ):
            continue
        seen.add(symbol)
        name = display_name(symbol, w.display_name) or "名称待核实"
        subject = {"key": f"symbol:{symbol}", "kind": "symbol", "id": symbol, "name": name}
        items.append(_buy_card(request, subject, now))
        items.append(_sell_symbol_card(request, subject, now))
    try:
        workspace = build_workspace(request)
        holdings = workspace.get("items") or []
    except Exception as exc:  # source failure stays visible board-wide
        holdings = []
        limitations.append(f"持仓快照读取失败：{type(exc).__name__}")
    for holding in holdings:
        try:
            sell = _sell_card(request, holding, now)
            items.append(sell)
            buy_subject = {
                "key": f"holding:{holding['holding_id']}",
                "kind": "holding",
                "id": str(holding["holding_id"]),
                "symbol": holding.get("symbol"),
                "name": holding["name"],
                "code": holding.get("code") or "",
            }
            buy = _buy_card(request, buy_subject, now)
            _fund_disclosure(buy, holding, now)
            _share_public_context(sell, buy)
            if not holding.get("symbol"):
                buy["limitations"].append("持仓尚未对应到同一产品技术行情，买入条件未知")
                buy["status"] = "unknown"
            buy["agent_eligible"] |= _has_public_context(buy)
            items.append(buy)
        except (AttributeError, TypeError, ValueError, KeyError) as exc:
            subject = {
                "key": f"holding:{holding.get('holding_id', 'unknown')}",
                "kind": "holding",
                "id": str(holding.get("holding_id", "unknown")),
                "name": holding.get("name") or "名称待核",
                "code": holding.get("code") or "",
            }
            for intent in ("buy", "sell"):
                card = _card(subject, intent)
                card["limitations"].append(f"持仓证据解析失败：{type(exc).__name__}")
                items.append(card)
    items.sort(key=lambda card: card["candidate_key"])
    unavailable = sum(card["status"] == "unknown" for card in items)
    return {
        "as_of": now.date().isoformat(),
        "checked_at": now.isoformat(),
        "coverage": {
            "watchlist": len(seen),
            "holdings": len(holdings),
            "review_candidates": sum(card["agent_eligible"] for card in items),
            "unavailable": unavailable,
        },
        "limitations": limitations,
        "items": items,
    }
