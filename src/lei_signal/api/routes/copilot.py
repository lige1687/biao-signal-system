"""Agent 超级入口路由：确定性流水线的 HTTP 壳（判定权在流水线与既有规则层）。

本文件不做任何新判定；推荐/档位/台账/复盘全部来自 copilot 包的纯函数与
既有 DTO。LLM 讲解只在 explain 类端点出现，且输出过接地校验、失败降级模板。
"""
from __future__ import annotations

import logging
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
    """仓位档位建议：盈亏比取该标的买点审阅最优候选，只建议档位不算金额。"""
    from lei_signal.api.routes.opportunities import buy_point_review  # noqa: PLC0415
    from lei_signal.copilot.sizing import build_sizing_advice  # noqa: PLC0415

    review = buy_point_review(request, symbol)
    best = review.candidates[0] if review.candidates else None
    if best is None and review.resonance_groups:
        best = review.resonance_groups[0].candidates[0]
    rr = best.reward_risk_ratio if best else None
    return build_sizing_advice(
        symbol,
        rr,
        rr_computable=bool(best.reward_risk_computable) if best else False,
    )


@router.post("/copilot/dispatch", response_model=CopilotDispatchReply)
def dispatch(request: Request, body: CopilotDispatchRequest) -> CopilotDispatchReply:
    """一句话入口：规则识别意图 → 直达流水线（零 LLM）；识别不到回落通用讨论。"""
    from lei_signal.api.opportunity_scan import today_date  # noqa: PLC0415
    from lei_signal.copilot.intent import parse_intent, parse_trade_report  # noqa: PLC0415

    intent = parse_intent(body.message)
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
    with closing(connect(_db_path(request))) as conn:
        rec = journal.load_recommendation(conn, run_date)
        return ops_mod.build_ops_today(
            conn, run_date=run_date, recommend_card=rec
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
