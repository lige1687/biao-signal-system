"""Agent 超级入口路由：确定性流水线的 HTTP 壳（判定权在流水线与既有规则层）。

本文件不做任何新判定；推荐/档位/台账/复盘全部来自 copilot 包的纯函数与
既有 DTO。LLM 讲解只在 explain 类端点出现，且输出过接地校验、失败降级模板。
"""
from __future__ import annotations

import json
import logging
import re
from contextlib import closing
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from lei_signal.api.config import sqlite_path as default_db
from lei_signal.api.schemas import (
    CopilotDispatchReply,
    CopilotDispatchRequest,
    FundTradeDTO,
    OpsCardDTO,
    RecommendCardDTO,
    ReviewCardDTO,
    SizingAdviceDTO,
    TradePreviewDTO,
    TradesResponseDTO,
)
from lei_signal.copilot import journal
from lei_signal.copilot.recommend import build_recommendation
from lei_signal.plans import llm as plans_llm
from lei_signal.plans.store import list_plans
from lei_signal.storage.sqlite_store import connect

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["copilot"])


def _db_path(request: Request) -> str:
    return getattr(request.app.state, "plans_db_path", None) or default_db()


def _service(request: Request):
    service = getattr(request.app.state, "analysis_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="分析服务不可用")
    return service


def _sector_rows(request: Request) -> list[dict] | None:
    """板块阶段快照（容错：服务缺失/未预计算时返回 None，推荐照常出）。"""
    svc = getattr(request.app.state, "sectors_service", None)
    if svc is None:
        return None
    try:
        data = svc.trend(refresh=False, level="l1")
    except Exception:  # noqa: BLE001  快照缺席不阻断推荐
        return None
    if not isinstance(data, dict):
        return None
    for key in ("sectors", "rows", "items"):
        rows = data.get(key)
        if isinstance(rows, list):
            return rows
    return None


def _news_brief(request: Request) -> dict | None:
    """自选×近3天消息面简报（容错适配在 recommend.extract_news_heat）。"""
    svc = getattr(request.app.state, "newsfeed_service", None)
    if svc is None:
        return None
    try:
        from lei_signal.api.watchlist import list_watchlist  # noqa: PLC0415

        with closing(
            connect(
                getattr(request.app.state, "watchlist_db_path", "")
                or _db_path(request)
            )
        ) as conn:
            watch = [
                {"symbol": w.symbol, "display_name": w.display_name, "market": w.market}
                for w in list_watchlist(conn)
            ]
        return svc.watchlist_brief(watch, days=3)
    except Exception:  # noqa: BLE001
        return None


def _recommend_card(request: Request, *, refresh: bool = False) -> RecommendCardDTO:
    """今日推荐组装（路由/脚本共用）：当日扫描表优先，空表或 refresh 现场扫。"""
    from lei_signal.api.opportunity_scan import (  # noqa: PLC0415
        list_scan,
        today_date,
        upsert_scan_results,
    )
    from lei_signal.api.routes.opportunities import (  # noqa: PLC0415
        _row_to_scan_item,
        run_opportunity_scan,
    )

    db = _db_path(request)
    scan_date = today_date()
    scan_items = None
    if not refresh:
        with closing(connect(db)) as conn:
            rows = list_scan(conn, scan_date)
        if rows:
            scan_items = [_row_to_scan_item(r) for r in rows]
    if scan_items is None:
        response = run_opportunity_scan(_service(request), db, refresh=refresh)
        scan_items = list(response.items)
        with closing(connect(db)) as conn:
            upsert_scan_results(conn, scan_date, scan_items)
            conn.commit()
    from lei_signal.copilot import sentiment as sentiment_mod  # noqa: PLC0415

    s_pack = sentiment_mod.load_sector_sentiment()
    return build_recommendation(
        scan_items,
        run_date=scan_date,
        sector_rows=_sector_rows(request),
        news_brief=_news_brief(request),
        sentiment_index=sentiment_mod.build_symbol_index(s_pack),
        sentiment_available=bool(s_pack.get("available")),
        generated_at=datetime.now(UTC).isoformat(),
    )


@router.get("/copilot/recommend", response_model=RecommendCardDTO)
def get_recommend(
    request: Request, refresh: bool = False, save: bool = True
) -> RecommendCardDTO:
    """今日推荐（确定性，零 LLM）。save=true 时按 run_date 存证进推荐账本。"""
    card = _recommend_card(request, refresh=refresh)
    if save and card.items:
        with closing(connect(_db_path(request))) as conn:
            journal.save_recommendation(conn, card)
            conn.commit()
    return card


@router.get("/copilot/position-advice/{symbol}", response_model=SizingAdviceDTO)
def position_advice(request: Request, symbol: str) -> SizingAdviceDTO:
    """仓位档位建议：盈亏比取该标的买点审阅最优候选，只建议档位不算金额。

    2026-09-06 接入宽度环境调节（弱市降一档）+ RS 虹吸豁免（独立行情不压
    仓位）——依据宽度全栈组验证与用户「分标的、价格最公平」口径。
    """
    from lei_signal.api.routes.opportunities import buy_point_review  # noqa: PLC0415
    from lei_signal.copilot.sizing import build_sizing_advice, siphon_regime  # noqa: PLC0415

    review = buy_point_review(request, symbol)
    best = review.candidates[0] if review.candidates else None
    if best is None and review.resonance_groups:
        best = review.resonance_groups[0].candidates[0]
    rr = best.reward_risk_ratio if best else None
    # 宽度环境（叙事层同一数据源：A股 ma200 占比）。
    # 市场适用性（2026-09-06 用户纠错）：只对 A 股标的生效——跨境 QDII
    # （513xxx 纳指/标普/恒生科技等）与美股/港股不适用 A 股宽度调节
    # （美股有自己的宽度通道，数据另源，缺时不硬套）。
    breadth_ma200 = None
    is_cross_border = symbol.startswith("513")  # 跨境 QDII：纳指/标普/恒科/中概等
    applies = (
        (symbol.endswith((".SS", ".SZ")) or symbol.startswith("TH"))
        and not is_cross_border
    )
    if applies:
        try:
            from lei_signal.copilot import breadth as breadth_mod  # noqa: PLC0415

            b = breadth_mod.a_share_breadth()
            if isinstance(b, dict):
                breadth_ma200 = b.get("ma200_pct")
        except Exception:  # noqa: BLE001
            breadth_ma200 = None
    # RS 虹吸（标的 vs 沪深300，分析服务缓存取日线）
    siphon = False
    try:
        service = getattr(request.app.state, "analysis_service", None)
        if service is not None:
            entry = service.get(symbol)
            bench = service.get("000300.SS")
            if entry.result is not None and bench.result is not None:
                siphon, _ = siphon_regime(entry.result.frame, bench.result.frame)
    except Exception:  # noqa: BLE001
        siphon = False
    return build_sizing_advice(
        symbol,
        rr,
        rr_computable=bool(best.reward_risk_computable) if best else False,
        breadth_ma200_pct=breadth_ma200,
        siphon=siphon,
    )


@router.post("/copilot/dispatch", response_model=CopilotDispatchReply)
def dispatch(request: Request, body: CopilotDispatchRequest) -> CopilotDispatchReply:
    """一句话入口：规则识别意图 → 直达流水线（零 LLM）；识别不到回落通用讨论。"""
    from lei_signal.api.opportunity_scan import today_date  # noqa: PLC0415
    from lei_signal.copilot.intent import parse_intent, parse_trade_report  # noqa: PLC0415

    intent = parse_intent(body.message)
    if intent.kind == "scout":
        from lei_signal.api.schemas import ScoutCardDTO, ScoutItemDTO  # noqa: PLC0415
        from lei_signal.copilot.scout import scout  # noqa: PLC0415

        with closing(connect(_db_path(request))) as conn:
            pack = scout(request, conn)
        def _items(rows: list[dict]) -> list[ScoutItemDTO]:
            return [ScoutItemDTO(**r) for r in rows if isinstance(r, dict)]
        card = ScoutCardDTO(
            available=pack.get("available", False),
            trend=_items(pack.get("trend") or []),
            ambush=_items(pack.get("ambush") or []),
            sentiment=_items(pack.get("sentiment") or []),
            note_cn=pack.get("note_cn", ""),
        )
        note = (
            "当下机会扫描：趋势信号 X 项、埋伏位 Y 项、情绪信号 Z 项——"
            "每项带历史依据，详见卡片。"
        ).replace("X", str(len(card.trend))).replace("Y", str(len(card.ambush))).replace("Z", str(len(card.sentiment)))
        if not card.available:
            note = "扫了一圈：当前没有符合条件的机会（趋势信号、埋伏位、情绪信号均未激活）——空仓等待也是一种操作。"
        return CopilotDispatchReply(
            intent="scout", note_cn=note,
            card={"card_type": "scout", "data": card.model_dump()},
        )
    if intent.kind == "recommend":
        card = _recommend_card(request)
        with closing(connect(_db_path(request))) as conn:
            if card.items:
                journal.save_recommendation(conn, card)
                conn.commit()
        return CopilotDispatchReply(
            intent="recommend",
            card={"card_type": "recommend", "data": card.model_dump()},
            note_cn="推荐为排序结果，不构成新判定；点击标的可看买点审阅。",
        )
    if intent.kind == "trade_report":
        preview = parse_trade_report(body.message, today=today_date())
        return CopilotDispatchReply(
            intent="trade_report",
            preview=preview,
            note_cn="已按你的话抽出信息，请核对后确认记入台账。",
        )
    if intent.kind == "holdings":
        from lei_signal.copilot import trades as trades_mod  # noqa: PLC0415

        with closing(connect(_db_path(request))) as conn:
            plans = [
                {
                    "plan_id": p.plan_id,
                    "symbol": p.symbol,
                    "state": p.state,
                    "module": p.module,
                    "direction": p.direction,
                    "valid_until": p.valid_until,
                }
                for p in list_plans(conn)
                if p.state in ("armed", "entered")
            ]
            fund_positions = [
                p.model_dump() for p in trades_mod.position_summary(
                    conn, fetch_nav=trades_mod.fetch_nav_history
                )
            ]
        data = {
            "active_plans": plans,
            "fund_positions": fund_positions,
            "hint_cn": "盈亏按报单日净值核算（大白话：落袋的算已实现，还在里的算浮动）；"
                       "明细见「我的持仓」页。",
        }
        return CopilotDispatchReply(
            intent="holdings",
            card={"card_type": "holdings", "data": data},
        )
    if intent.kind == "review":
        from lei_signal.copilot import review as review_mod  # noqa: PLC0415

        week_iso = review_mod.prev_iso_week(today_date())
        with closing(connect(_db_path(request))) as conn:
            weekly = review_mod.get_review(conn, "weekly", week_iso)
            if weekly is None:
                weekly = review_mod.build_weekly_review(conn, week_iso)
                review_mod.save_review(conn, weekly)
                conn.commit()
        return CopilotDispatchReply(
            intent="review",
            card={"card_type": "review", "data": weekly.model_dump()},
        )
    return CopilotDispatchReply(
        intent="chat",
        symbol=body.symbol,
        chat_fallback=True,
        note_cn="未命中快捷指令，已转通用讨论。",
    )


class ExplainRequest(BaseModel):
    question: str = ""


class ExplainReply(BaseModel):
    reply: str
    grounded: bool
    card: RecommendCardDTO


_EXPLAIN_DEFAULT_Q = "请概括今日推荐：先看什么、为什么、还缺什么条件。"


def _explain_template(card: RecommendCardDTO) -> str:
    lines = [
        f"· {i.display_name}（{i.symbol}）[{i.verdict_cn}] " + "；".join(i.reasons[:3])
        for i in card.items
    ]
    sectors = [f"· {s.name}（{s.stage_cn}）" for s in card.sectors]
    return (
        f"【今日推荐·数据直出】{card.run_date}\n"
        + ("\n".join(lines) if lines else "今日无上榜标的。")
        + ("\n板块：" + "、".join(sectors) + "\n" if sectors else "\n")
        + "排序仅影响展示顺序，不构成新判定；技术结论以各标的买点审阅为准。"
    )


@router.post("/copilot/recommend/explain", response_model=ExplainReply)
def explain_recommend(request: Request, body: ExplainRequest) -> ExplainReply:
    """推荐讲解：一次 GLM 调用；数值/禁用词接地，失败降级模板直出。"""
    from lei_signal.plans.grounding import (  # noqa: PLC0415
        collect_payload_numbers,
        verify_grounding,
        verify_numeric_grounding,
    )

    card = _recommend_card(request)
    config = plans_llm.load_ark_config()
    reply: str | None = None
    grounded = False
    if config is not None:
        payload = card.model_dump()
        allowed_nums = collect_payload_numbers(payload)
        raw = plans_llm.chat_copilot(
            payload,
            body.question.strip() or _EXPLAIN_DEFAULT_Q,
            config,
            system_prompt=plans_llm.COPILOT_SYSTEM_PROMPT,
        )
        if raw is not None:
            ok_num, _ = verify_numeric_grounding(raw, allowed_nums)
            ok_txt, _ = verify_grounding(raw, {""})  # 白名单空 = 只查禁用词
            if ok_num and ok_txt:
                reply, grounded = raw, True
            else:
                logger.warning("推荐讲解接地未过，降级模板")
    if reply is None:
        reply, grounded = _explain_template(card), False
    return ExplainReply(reply=reply, grounded=grounded, card=card)


class TradeCreateRequest(BaseModel):
    fund_code: str
    fund_name: str
    side: str
    amount: float
    trade_date: str
    note: str = ""


class TradePreviewRequest(BaseModel):
    message: str


@router.post("/copilot/trades/preview", response_model=TradePreviewDTO)
def trades_preview(body: TradePreviewRequest) -> TradePreviewDTO:
    """报单预解析 → 确认卡（零 LLM）。解析是 best-effort，落库走 /copilot/trades。"""
    from lei_signal.api.opportunity_scan import today_date  # noqa: PLC0415
    from lei_signal.copilot.intent import parse_trade_report  # noqa: PLC0415

    return parse_trade_report(body.message, today=today_date())


@router.post("/copilot/trades", response_model=FundTradeDTO)
def trades_create(request: Request, body: TradeCreateRequest) -> FundTradeDTO:
    """确认卡落库（结构化字段直传）+ 立即尝试定价。"""
    from lei_signal.copilot import trades as trades_mod  # noqa: PLC0415

    with closing(connect(_db_path(request))) as conn:
        try:
            trade = trades_mod.create_trade(
                conn,
                fund_code=body.fund_code.strip(),
                fund_name=body.fund_name.strip() or body.fund_code.strip(),
                side=body.side,
                amount=body.amount,
                trade_date=body.trade_date,
                source="web",
                note=body.note,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        trades_mod.price_pending_trades(
            conn, fetch_nav=trades_mod.fetch_nav_history
        )
        conn.commit()
        fresh = next(
            (t for t in trades_mod.list_trades(conn) if t.trade_id == trade.trade_id),
            trade,
        )
    return fresh


@router.get("/copilot/trades", response_model=TradesResponseDTO)
def trades_list(request: Request) -> TradesResponseDTO:
    from lei_signal.copilot import trades as trades_mod  # noqa: PLC0415

    with closing(connect(_db_path(request))) as conn:
        return TradesResponseDTO(
            trades=trades_mod.list_trades(conn),
            positions=trades_mod.position_summary(
                conn, fetch_nav=trades_mod.fetch_nav_history
            ),
        )


@router.get("/copilot/review/trade/{trade_id}", response_model=ReviewCardDTO)
def trade_review(request: Request, trade_id: str) -> ReviewCardDTO:
    """单笔复盘：首访组装+存库（含 GLM 叙事 best-effort），之后读缓存。"""
    from lei_signal.copilot import review as review_mod  # noqa: PLC0415

    with closing(connect(_db_path(request))) as conn:
        card = review_mod.get_review(conn, "trade", trade_id)
        if card is None:
            card = review_mod.build_trade_review(conn, trade_id)
            if card is None:
                raise HTTPException(status_code=404, detail=f"成交不存在: {trade_id}")
            card = review_mod.attach_narrative(
                conn, card, config=plans_llm.load_ark_config()
            )
            review_mod.save_review(conn, card)
            conn.commit()
    return card


@router.get("/copilot/review/weekly", response_model=ReviewCardDTO)
def weekly_review(request: Request, week: str | None = None) -> ReviewCardDTO:
    """周复盘：缺省上一完整 ISO 周。首访组装+存库，之后读缓存。"""
    from lei_signal.api.opportunity_scan import today_date  # noqa: PLC0415
    from lei_signal.copilot import review as review_mod  # noqa: PLC0415

    week_iso = week or review_mod.prev_iso_week(today_date())
    with closing(connect(_db_path(request))) as conn:
        card = review_mod.get_review(conn, "weekly", week_iso)
        if card is None:
            card = review_mod.build_weekly_review(conn, week_iso)
            card = review_mod.attach_narrative(
                conn, card, config=plans_llm.load_ark_config()
            )
            review_mod.save_review(conn, card)
            conn.commit()
    return card


@router.get("/ops/today", response_model=OpsCardDTO)
def ops_today(request: Request) -> OpsCardDTO:
    """每日操作清单（页面数据源；推送由 scripts/copilot_daily.py 同源组装）。"""
    from lei_signal.api.opportunity_scan import today_date  # noqa: PLC0415
    from lei_signal.copilot import ops as ops_mod  # noqa: PLC0415

    run_date = today_date()
    major_events = None
    svc = getattr(request.app.state, "newsfeed_service", None)
    if svc is not None:
        try:
            major_events = svc.major_events_brief()
        except Exception:  # noqa: BLE001 — 消息面失败不阻塞清单
            major_events = None
    with closing(connect(_db_path(request))) as conn:
        rec = journal.load_recommendation(conn, run_date)
        return ops_mod.build_ops_today(
            conn, run_date=run_date, recommend_card=rec,
            major_events=major_events,
        )


@router.get("/copilot/sentiment")
def get_sentiment() -> dict:
    """情绪面数据包：板块热度 + 两融环境（只读，叙事标注层）。"""
    from lei_signal.copilot import breadth as breadth_mod  # noqa: PLC0415
    from lei_signal.copilot import sentiment as sentiment_mod  # noqa: PLC0415

    s_pack = sentiment_mod.load_sector_sentiment()
    s_pack["margin"] = sentiment_mod.margin_regime_cn()
    s_pack["breadth"] = {
        "a_share": breadth_mod.a_share_breadth(),
        "us": breadth_mod.us_breadth(),
        "a_share_cn": breadth_mod.a_share_breadth_cn(),
        "us_cn": breadth_mod.us_breadth_cn(),
    }
    return s_pack


@router.get("/copilot/experience")
def get_experience(
    signal: str | None = None,
    pool: str | None = None,
) -> dict:
    """回测经验索引查询（条件→历史结果，叙事层不参与判定）。

    signal/pool 取值见 docs/experiments/EXPERIENCE-INDEX.md 受控词表；
    支持任意 match 键的子集匹配（两个显式参数外预留 conditions 透传）。
    """
    from lei_signal.copilot import experience as exp_mod

    conditions: dict[str, str] = {}
    if signal:
        conditions["signal"] = signal
    if pool:
        conditions["pool"] = pool
    return exp_mod.query_experience(conditions)


# ------------------------------------------------------------------
# 03B：统一入口解析 + 按需补测（总控协议 §2/§5，2026-09-08）
# ------------------------------------------------------------------


class ResolveRequest(BaseModel):
    message: str
    client_request_id: str | None = None
    session_id: str | None = None
    selected_symbol: str | None = None


def _resolve_symbol_with_ambiguity(request: Request, body: ResolveRequest):
    """标的解析（03B §2 优先级）：本轮明确 → 当前选中 → 会话最近。
    明确名称命中多个不同标的 → 澄清，不猜。返回 (symbol, source, ambiguities)。

    03B-R2 契约1（r3）：**对象识别与资料可用性分离**——消息里语法合法的
    代码就是对象，即使该标的还没有缓存行情（fetch=False 探不到）也仍解析
    为它（缺数据走正式分析路径获取或明示缺口），不回退成选中的另一个标的。"""
    from lei_signal.api.routes.agent import (
        _resolve_symbol_by_catalog,
        _resolve_symbol_by_name,
        _symbol_candidates_from_message,
    )

    service = getattr(request.app.state, "analysis_service", None)
    db = getattr(request.app.state, "plans_db_path", None) or _db_path(request)
    explicit = _symbol_candidates_from_message(body.message)
    if len(explicit) == 1:
        return explicit[0], "message", []
    if len(explicit) > 1:
        # 明确说出多个不同代码 → 先澄清，不边问边猜
        return None, "ambiguous", explicit
    from lei_signal.copilot.subjects import named_subject, asks_for_sector

    named = named_subject(body.message or "")
    if named:
        return named, "message", []
    # 主控裁决（2026-09-15）：用户明确指定的对象（别名/目录全名，如
    # 「科创50板块」里的科创50）优先于笼统的「板块」关键词——先按目录
    # 层解析，确实没有唯一对象才落「板块问法无对象」的澄清路径。
    catalog_hit = _resolve_symbol_by_catalog(body.message or "")
    if catalog_hit:
        return catalog_hit, "message", []
    if asks_for_sector(body.message or ""):
        return None, "none", []
    if service is not None and not re.search(r"\d{6}", body.message or ""):
        # 名称歧义检测：完整名出现在话里的不同标的 > 1 → 先澄清
        from lei_signal.api.watchlist import list_watchlist

        with closing(connect(db)) as conn:
            watch = list_watchlist(conn)
        names: dict[str, str] = {}
        for w in watch:
            from lei_signal.api.routes.agent import _static_symbol_name

            nm = _static_symbol_name(w.symbol, getattr(w, "display_name", None))
            if nm:
                names[nm] = w.symbol
        flat = (body.message or "").replace(" ", "")
        hits = {sym for nm, sym in names.items() if nm and nm in flat}
        if len(hits) > 1:
            return None, "ambiguous", sorted(hits)
    if service is not None:
        by_catalog = _resolve_symbol_by_catalog(body.message or "")
        if by_catalog:
            try:
                entry = service.get(by_catalog, fetch=False)
                if getattr(entry, "result", None) is not None:
                    return by_catalog, "message", []
            except Exception:  # noqa: BLE001
                pass
    if body.selected_symbol:
        return body.selected_symbol, "selected", []
    if body.session_id:
        with closing(connect(db)) as conn:
            from lei_signal.plans.sessions import list_messages
            from lei_signal.plans.sessions import get_session

            if get_session(conn, body.session_id) is not None:
                msgs = list_messages(conn, body.session_id, limit=20)
                for m in reversed(msgs):
                    if m.role != "assistant":
                        continue
                    try:
                        meta = json.loads(m.meta_json or "{}")
                    except (TypeError, ValueError):
                        continue
                    sym = meta.get("resolved_symbol")
                    if isinstance(sym, str) and sym:
                        return sym, "session", []
    return None, "none", []


#: 板块泛指 → 可选的指数观察参考（主控裁决 2026-09-15）。
#: 仅登记有明确产品定义的项；（泛指词, 指数代码, 指数名）。这不是
#: 「板块→指数」的静默顶替：只在澄清文案里作为可选项给出，并明确
#: 指数不代表整个板块。
_SECTOR_AREA_INDEX_REF: tuple[tuple[str, str, str], ...] = (
    ("科创", "000688.SS", "科创50"),
)


def _sector_area_index_reference(message: str) -> tuple[str, str, str] | None:
    """消息含板块泛指词时给出可选的指数观察参考；无登记返回 None。"""
    for area_word, ref_symbol, ref_name in _SECTOR_AREA_INDEX_REF:
        if area_word in (message or ""):
            return ref_symbol, ref_name, area_word
    return None


@router.post("/copilot/resolve")
def copilot_resolve(request: Request, body: ResolveRequest) -> dict:
    """统一入口解析（03B §2）：意图/主题/标的/用途/澄清。

    零 LLM、零写入、不启动回测、不建任何记录。"""
    import re as _re

    from lei_signal.copilot import resolve as resolve_mod
    from lei_signal.copilot import semantic_states
    from lei_signal.data_provenance import winrate_evidence_ref

    from lei_signal.copilot.subjects import display_name, asks_for_sector

    parsed = resolve_mod.parse_request(body.message)
    symbol, source, ambiguities = _resolve_symbol_with_ambiguity(request, body)
    clarification = list(parsed["need_clarification"])
    if not symbol and asks_for_sector(body.message):
        # 主控裁决（2026-09-15）：「科创板块/科创板整体」这类泛指没有唯一
        # 可核实对象——简短澄清，可让用户选择科创50作为观察参考，并明确
        # 它不代表整个科创板；不得恢复「任意板块→ETF/指数」的静默顶替。
        area_ref = _sector_area_index_reference(body.message)
        if area_ref is not None:
            ref_symbol, ref_name, area_word = area_ref
            clarification.append({
                "kind": "sector_ambiguous_index_reference",
                "question_cn": (
                    f"「{area_word}」是板块泛指，系统里没有唯一可核实的"
                    f"对应对象，不能直接给出它的判定。如果你想看的是"
                    f"{ref_name}（{ref_symbol}），可以把它作为观察参考——"
                    f"注意它是 50 只成分股组成的指数，不代表整个板块。"
                    f"要按{ref_name}继续，请直接说「{ref_name}」。"),
                "reference_symbol": ref_symbol,
                "reference_name": ref_name,
            })
        else:
            clarification.append({"kind": "sector_unknown", "question_cn":
                "没有找到这个板块，请提供完整板块名称；不会用相近名称的ETF代替。"})
    if ambiguities:
        clarification.append({
            "kind": "symbol_ambiguous",
            "question_cn": "提到多个标的，请说明想聊哪一个：" + "、".join(ambiguities),
        })

    states = semantic_states.states_for_topic(parsed["topic"])
    evidence = None
    plan_count = None
    db = getattr(request.app.state, "plans_db_path", None) or _db_path(request)
    if symbol:
        evidence = winrate_evidence_ref(symbol).to_dict()
        with closing(connect(db)) as conn:
            from lei_signal.plans.store import list_plans

            plan_count = sum(
                1 for p in list_plans(conn, symbol=symbol)
                if p.state in ("armed", "entered"))
    return {
        "intent": parsed["intent"],
        "topic": parsed["topic"],
        "resolved_symbol": symbol,
        "display_name": (display_name(symbol) if symbol else None),
        "subject_source": source if symbol else ("ambiguous" if ambiguities else "none"),
        "purpose": parsed["purpose"],
        "clarification": clarification,
        "discussion_context": {
            "states": [
                {"id": s["id"], "label_cn": s["label_cn"],
                 "missing_behavior": s["missing_behavior"],
                 "forbidden_claims": s["forbidden_claims"]}
                for s in states
            ],
            "evidence": evidence,
            "active_plan_count": plan_count,
            "client_request_id": body.client_request_id,
        },
    }


class BacktestRequestIn(BaseModel):
    session_id: str
    question_id: int
    client_request_id: str
    symbol: str | None = None
    # 03B-R2 契约2：模块与退出方式必须由用户明确选择（不默认 A、前端不再
    # 统一固定同一退出值）；缺项在 pydantic 层即 422
    module: str
    entry_variant: str | None = None
    exit_variant: str
    rr_min: float | None = 3.0
    fee_label: str = "standard"
    data_cutoff: str | None = None  # R4：截止必须实际作用到引擎输入


@router.post("/copilot/backtest-requests")
def create_backtest_request(request: Request, body: BacktestRequestIn) -> dict:
    """按需补测（03B §5 + R1/R2 返修）：单标的、一套已明确的既有方法；
    服务端校验问题归属/对象绑定/方法与模块合法性，持久保存（queued）后
    由单任务队列原子领取执行。多标的/空标的/缺方法/非法方法 → 422。"""
    from lei_signal.backtest.service import MODULE_ENTRY_CONTRACT
    from lei_signal.copilot.backtest_requests import (
        BacktestRequestConflict,
        BacktestRequestError,
        create_request,
        start_request_worker,
    )

    symbol = (body.symbol or "").strip()
    if not symbol:
        raise HTTPException(status_code=422, detail={
            "code": "BACKTEST_SYMBOL_REQUIRED",
            "message": "补测需要明确一个标的；symbols=None/空/多标的在此入口一律拒绝"})
    if not body.module:
        raise HTTPException(status_code=422, detail={
            "code": "MISSING_METHOD",
            "message": "缺少交易模块：请明确 A 回调 / B 突破 / C 2B / D 假突破（不默认 A）"})
    if body.module.upper() not in MODULE_ENTRY_CONTRACT:
        raise HTTPException(status_code=422, detail={
            "code": "INVALID_METHOD",
            "message": f"未知交易模块: {body.module}（合法：A/B/C/D）"})
    with closing(connect(_db_path(request))) as conn:
        # 服务端校验归属：question_id 必须是该会话的 user 消息
        q = conn.execute(
            "SELECT role, session_id, meta_json FROM agent_messages "
            "WHERE message_id = ?", (body.question_id,)).fetchone()
        if q is None or q["role"] != "user" or q["session_id"] != body.session_id:
            raise HTTPException(status_code=422, detail={
                "code": "QUESTION_OWNERSHIP",
                "message": "question_id 与会话归属不符（不能信任任意旧消息 ID）"})
        # R1/R2：绑定校验——原问题绑定 A 却外传 B → 422 零创建（先记录新
        # 问题才可换对象）；原问题明确方法与请求方法不符 → 422
        try:
            snap = (json.loads(q["meta_json"] or "{}").get("discussion_v1") or {})
        except ValueError:
            snap = {}
        snap_symbol = snap.get("symbol")
        if snap_symbol and snap_symbol != symbol:
            raise HTTPException(status_code=422, detail={
                "code": "OBJECT_MISMATCH",
                "message": (f"原问题绑定 {snap_symbol}，请求却绑定 {symbol}；"
                            "请先就新对象提出新问题，再补测")})
        # 方法归属：请求显式模块优先（来源=request，用户的新选择即新选择）；
        # 原问题的明确方法已保存在快照 method/method_source，供审计对照。
        try:
            out = create_request(
                conn, session_id=body.session_id, question_id=body.question_id,
                client_request_id=body.client_request_id, symbol=symbol,
                module=body.module, entry_variant=body.entry_variant,
                exit_variant=body.exit_variant, rr_min=body.rr_min,
                fee_label=body.fee_label, data_cutoff=body.data_cutoff)
        except BacktestRequestError as exc:
            raise HTTPException(status_code=422, detail={
                "code": "BACKTEST_INVALID", "message": str(exc)}) from exc
        except BacktestRequestConflict as exc:
            raise HTTPException(status_code=409, detail={
                "code": "BACKTEST_CONFLICT", "message": str(exc)}) from exc
        conn.commit()
    # R5：仅 queued 领取执行；completed 重试只读原结果，不重跑引擎
    if out["status"] == "queued":
        start_request_worker(_db_path(request), out["request_id"])
        out = get_backtest_request(request, out["request_id"])
    return out


@router.get("/copilot/backtest-requests/{request_id}")
def get_backtest_request(request: Request, request_id: str) -> dict:
    from lei_signal.copilot.backtest_requests import get_request

    with closing(connect(_db_path(request))) as conn:
        out = get_request(conn, request_id)
    if out is None:
        raise HTTPException(status_code=404, detail=f"补测请求不存在: {request_id}")
    return out


@router.get("/copilot/backtest-requests")
def list_backtest_requests(request: Request, session_id: str | None = None,
                           limit: int = 50) -> dict:
    """任务列表（03B-R2 契约4）：session_id 省略时跨会话取最近任务——
    页面恢复以**服务端列表为权威**，localStorage 只是提示。"""
    from lei_signal.copilot.backtest_requests import (
        list_requests,
        list_requests_any,
    )

    with closing(connect(_db_path(request))) as conn:
        rows = (list_requests_any(conn, limit=max(1, min(limit, 100)))
                if session_id is None else
                list_requests(conn, session_id, limit=max(1, min(limit, 100))))
        return {"requests": rows}
