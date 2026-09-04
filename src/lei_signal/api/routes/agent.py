"""监督员 agent 表达层路由：接地问答（LLM 只表达，判定权在 Python）。

复用 /alerts 的确定性判定（evaluate_plan），把 alert 讲成人话或回答用户提问。
LLM 输出必须过 ``verify_grounding``（禁用词 + rule_id 白名单），失败降级
``render_alerts`` 模板。plans.py 明确「不接 LLM」，故本路由独立成文件。
"""
from __future__ import annotations

import json
import logging
import re
from contextlib import closing

from fastapi import APIRouter, HTTPException, Request

from lei_signal.api.config import sqlite_path as default_db
from lei_signal.api.routes.plans import _to_alert_dto
from lei_signal.api.schemas import (
    AgentChatReply,
    AgentChatRequest,
    AgentMessageDTO,
    AgentSessionDTO,
    BuyPointChatReply,
    BuyPointChatRequest,
    CreateSessionRequest,
    PlanChatReply,
    PlanChatRequest,
    TraceItem,
)
from lei_signal.plans import llm as plans_llm
from lei_signal.plans.context import context_from_result
from lei_signal.plans.grounding import (
    collect_payload_numbers,
    extract_market_numbers,
    render_alerts,
    verify_grounding,
    verify_numeric_grounding,
)
from lei_signal.plans.llm import (
    build_context_payload,
    chat_ark,
    chat_buy_point,
    load_ark_config,
)
from lei_signal.plans.llm_context import build_discussion_context
from lei_signal.plans.monitor import evaluate_plan
from lei_signal.plans.sessions import (
    append_message,
    create_session,
    get_session,
    list_messages,
    list_sessions,
)
from lei_signal.plans.store import get_plan, list_action_items, list_plans
from lei_signal.storage.sqlite_store import connect

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["agent"])

#: message 为空时的默认概括指令（走 SYSTEM_PROMPT 既定输出格式）。
_DEFAULT_SUMMARY_PROMPT = "请按输出格式概括当前监督结果与待办。"


def _db_path(request: Request) -> str:
    return getattr(request.app.state, "plans_db_path", None) or default_db()


@router.post("/plans/{plan_id}/chat", response_model=PlanChatReply)
def plan_chat(request: Request, plan_id: str, body: PlanChatRequest) -> PlanChatReply:
    """对计划提问。message 空 -> 当前 alert 接地摘要；非空 -> 接地问答。

    LLM 不可用或输出未过 grounding -> 降级模板（grounded=False）。
    """
    with closing(connect(_db_path(request))) as conn:
        plan = get_plan(conn, plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail=f"计划不存在: {plan_id}")
        action_items = list_action_items(conn, plan_id, state="open")

    service = getattr(request.app.state, "analysis_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="分析服务不可用")
    entry = service.get(plan.symbol)
    if entry.result is None:
        raise HTTPException(status_code=502, detail=entry.error or "分析不可用")

    ctx = context_from_result(entry.result)
    alerts = evaluate_plan(plan, ctx)
    alert_dtos = [_to_alert_dto(a) for a in alerts]
    rule_ids = {a.rule_id for a in alerts if a.rule_id}

    config = load_ark_config()
    reply: str | None = None
    grounded = False
    if config is not None:
        payload = build_context_payload(
            alerts, plan=plan, action_items=action_items, context_min=None,
        )
        message = body.message.strip() or _DEFAULT_SUMMARY_PROMPT
        raw = chat_ark(payload, message, config)
        if raw is not None:
            ok, reason = verify_grounding(raw, rule_ids)
            if ok:
                reply = raw
                grounded = True
            else:
                logger.warning("计划 chat 接地校验未过，降级模板：%s", reason)

    if reply is None:
        # 降级：判定层模板直出，不经过 LLM
        reply = render_alerts(alerts, plan=plan, action_items=action_items)
        grounded = False
    return PlanChatReply(
        reply=reply, grounded=grounded, plan_id=plan_id, alerts=alert_dtos,
    )


_BP_DEFAULT_PROMPT = "请概括当前买点审阅：是否构成系统定义的买点、图什么信号、止损与盈亏比。"


@router.post("/symbols/{symbol}/buy-point-chat", response_model=BuyPointChatReply)
def buy_point_chat(
    request: Request, symbol: str, body: BuyPointChatRequest
) -> BuyPointChatReply:
    """就买点审阅提问。LLM 只讲解 review 的确定性字段，不自行判断买点。

    输出过 verify_grounding（禁用词 + rule_id 白名单 = review 内出现的 rule_id），
    失败降级为 review 结构化文本直出（grounded=False）。
    """
    from lei_signal.api.routes.opportunities import (  # noqa: PLC0415
        buy_point_review,
    )

    review = buy_point_review(request, symbol)
    review_dict = review.model_dump()
    rule_ids = {c.rule_id for c in review.candidates if c.rule_id}
    if (
        review.suggested_plan
        and review.suggested_plan.entry_rule_id
    ):
        rule_ids.add(review.suggested_plan.entry_rule_id)
    # 确保白名单非空时才校验；空时 verify_grounding 仍查禁用词
    allowed = rule_ids or {""}

    config = load_ark_config()
    reply: str | None = None
    grounded = False
    if config is not None:
        message = body.message.strip() or _BP_DEFAULT_PROMPT
        raw = chat_buy_point(review_dict, message, config)
        if raw is not None:
            ok, reason = verify_grounding(raw, allowed)
            if ok:
                reply = raw
                grounded = True
            else:
                logger.warning("买点 chat 接地校验未过，降级模板：%s", reason)

    if reply is None:
        # 降级：把 review 讲成结构化文本，不经过 LLM
        reply = _buy_point_template(review)
        grounded = False
    return BuyPointChatReply(
        reply=reply, grounded=grounded, symbol=symbol, review=review,
    )


def _buy_point_template(review) -> str:  # noqa: ANN001
    """review 降级模板：结构化直出，不经过 LLM。
    与 LLM 路径一致：每个候选只列依据/关键价/状态，止损和盈亏比在文末统一提示。

    recency 后: candidates 是近期独立候选, resonance_groups 是价位共振,
    historical_structures 是过期结构 (不展开)。
    """
    lines = [
        f"【买点审阅】{review.display_name} · {review.verdict_cn}",
        f"数据日：{review.as_of}（收盘 {review.last_close or '-'}）",
        review.summary_cn,
    ]
    if review.tradability and not review.tradability.tradable:
        reasons = "、".join(review.tradability.blocking_reasons) or "见门禁明细"
        lines.append(f"阻断：{reasons}（规格 §13）")
    # 1. 共振组 (合并展示, 避免重复)
    for g in review.resonance_groups:
        n_rules = len(g.rule_ids)
        rules_str = " / ".join(g.rule_ids)
        lines.append(
            f"\n· 共振买点（{n_rules} 个 rule 共识）"
            f" 价位 {g.level:.2f}（±{g.tolerance_pct*100:.1f}% 内）"
        )
        lines.append(f"  rule_ids: {rules_str}")
        for c in g.candidates:
            lines.append(
                f"  - {c.scenario_cn} [{c.state_cn}] rule_id:{c.rule_id or '-'}"
                f" 关键价 {c.key_price or '-'}"
            )
    # 2. 独立近期候选 (recency 过滤后, weakened 已静默丢弃, 无需再筛)
    for i, c in enumerate(review.candidates, start=1):
        circled = "①②③④⑤⑥⑦⑧⑨⑩"[i - 1] if i <= 10 else str(i)
        lines.append(
            f"\n· 买点{circled} {c.scenario_cn} [{c.state_cn}] "
            f"rule_id:{c.rule_id or '-'}"
        )
        lines.append(f"  关键价：{c.key_price or '系统未给出'}")
        if c.satisfied_conditions:
            lines.append(f"  已满足：{'；'.join(c.satisfied_conditions)}")
        if c.missing_conditions:
            lines.append(f"  还缺：{'；'.join(c.missing_conditions)}")
        if c.next_step_cn:
            lines.append(f"  触发：{c.next_step_cn}")
        lines.append("  判定方式为研究代理")
    # 3. 历史结构 (一笔带过, 不展开)
    if review.historical_structures:
        n = len(review.historical_structures)
        rules = sorted({h.rule_id for h in review.historical_structures if h.rule_id})
        rules_str = "、".join(rules) if rules else "-"
        lines.append(
            f"\n另有 {n} 个历史结构（{rules_str} 等）已超出 recency 窗口，"
            f"在审阅卡片底部单列, 不构成当下买点。"
        )
    if review.watch_conditions:
        lines.append("\n【到什么情况才算买点】")
        for w in review.watch_conditions:
            if w.kind == "price":
                lines.append(f"· {w.text_cn}（价位 {w.price}）")
            else:
                lines.append(f"· {w.text_cn}（状态型条件）")
    # 止损 / 盈亏比 / 落计划 一句话收尾
    lines.append(
        "\n止损价与盈亏比在落计划时再确认（需用户给认错位 + 目标位，"
        "系统不算 R/R）。五项交易假设必须由人写。"
    )
    if review.suggested_plan:
        sp = review.suggested_plan
        lines.append(
            f"可落计划预填：模块{sp.module} · {sp.direction} · "
            f"entry_rule_id:{sp.entry_rule_id}"
        )
    lines.append(f"\n{review.disclaimer_cn}")
    return "\n".join(lines)


# ---- 统一会话层（spec 2026-08-23）----

#: 从用户消息中抽标的代码 token。lookahead/lookbehind 排除前后紧邻的字母数字
#: （中文紧邻允许，「那515880那个」要能命中）；不用 \b（CJK 属 \w，边界不成立）。
_SYMBOL_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9.])(?:TH\d{6}|SW\d{4}|BK\d{4}|\d{6})(?:\.(?:SS|SZ))?(?![A-Za-z0-9])"
    r"|(?<![A-Za-z0-9])[A-Z]{2,5}(?:\.(?:SS|SZ))?(?![A-Za-z0-9])",
    re.IGNORECASE,
)
#: 最多尝试验证的候选数——每次失败验证都是一次分析往返，控制成本。
_MAX_SYMBOL_PROBES = 3


def _resolve_symbol_from_message(message: str, service: object) -> str | None:
    """从用户消息中提取**可分析**的标的（「515880那个」「看看 IGV」）。

    全局会话里用户报代码时自动带出该标的技术材料，不再反问。
    只返回 analysis_service 能成功分析的候选（普通英文词当代码会被分析失败
    自然过滤）；含数字的候选（A股/ETF/板块）优先于纯字母（美股/ETF）。
    """
    from lei_signal.data.symbols import resolve_symbol  # noqa: PLC0415

    tokens = _SYMBOL_TOKEN_RE.findall(message)
    ordered = sorted(
        dict.fromkeys(t.upper() for t in tokens),
        key=lambda t: 0 if any(c.isdigit() for c in t) else 1,
    )
    for i, tok in enumerate(ordered):
        if i >= _MAX_SYMBOL_PROBES:
            break
        try:
            info = resolve_symbol(tok)
        except ValueError:
            continue
        try:
            entry = service.get(info.symbol)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001  # 分析服务自身兜底，双保险
            continue
        if getattr(entry, "result", None) is not None:
            return info.symbol
    return None


def _last_resolved_symbol(history_rows: list) -> str | None:  # noqa: ANN001
    """从会话最近的 assistant 消息 meta 继承标的。

    「515880那个」之后追问「筹码呢」（无代码）仍有材料。
    """
    for m in reversed(history_rows):
        if m.role != "assistant":
            continue
        try:
            meta = json.loads(m.meta_json or "{}")
        except json.JSONDecodeError:
            return None
        resolved = meta.get("resolved_symbol")
        return resolved if isinstance(resolved, str) else None
    return None


def _degraded_reply(symbol: str, ctx_payload: dict) -> str:
    """LLM 不可用/校验失败时的模板直出（不含工程标注，标注走 trace）。"""
    if ctx_payload.get("context_kind") == "global":
        # global 会话无标的技术材料，直出「【】数据日 -」是空段，给专属文案
        return (
            "当前为全局会话，无标的技术材料。LLM 暂不可用，"
            "请切换到具体标的详情页打开 agent，或稍后重试。"
        )
    a = ctx_payload.get("assessment", {})
    vp = ctx_payload.get("volume_profile") or {}
    lines = [
        f"【{ctx_payload.get('display_name', symbol)}】数据日 {ctx_payload.get('as_of', '-')}",
        f"当前状态：{a.get('color_cn', '-')} / {a.get('stage_cn', '-')}"
        f" / 风险 {a.get('risk_state_cn', '-')}",
    ]
    review = ctx_payload.get("buy_point_review")
    if review and review.get("candidates"):
        for i, c in enumerate(review["candidates"][:3], start=1):
            circled = "①②③④⑤⑥⑦⑧⑨⑩"[i - 1]
            lines.append(
                f"买点{circled} {c.get('scenario_cn', '')} [{c.get('state_cn', '')}]"
                f" 关键价 {c.get('key_price') or '系统未给出'}"
            )
    if vp:
        lines.append(f"筹码分布代理：POC {vp.get('poc')} · VAH {vp.get('vah')}")
    lines.append("（LLM 暂不可用，以上为判定层数据直出）")
    return "\n".join(lines)


def _build_trace(alerts: list) -> list[TraceItem]:
    """从 alert 元数据生成角标数据——溯源信息不再进正文。"""
    return [
        TraceItem(
            label=a.next_step_cn or a.code,
            rule_id=a.rule_id,
            evidence_cn="；".join(f"{k}={v}" for k, v in (a.evidence or {}).items()),
            research_proxy=(a.logic_provenance == "research_proxy") if a.logic_provenance else True,
            principle_source=a.principle_source,
        )
        for a in alerts
    ]


def _discussion_txt_ok(raw: str, rule_ids: set[str]) -> tuple[bool, str]:
    """讨论正文的文本校验：verify_grounding + 不得出现「rule_id:」工程标注。

    后者是确定性加固：``verify_grounding`` 只拒白名单**外**的 rule_id，payload
    本就喂了 structures/events 的 rule_id，LLM 回显一个合法 rule_id 会双校验
    全过、默认 DOM 出现工程明文（FR-2）。溯源只走 trace 角标，正文一律不带。
    仅用于 /agent/chat 讨论路径；plans/buy-point 老端点维持原校验不变。
    """
    ok, reason = verify_grounding(raw, rule_ids)
    if ok and "rule_id:" in raw:
        return False, "正文含 rule_id: 工程标注（溯源走 trace 角标）"
    return ok, reason


@router.post("/agent/chat", response_model=AgentChatReply)
def agent_chat(request: Request, body: AgentChatRequest) -> AgentChatReply:
    """统一讨论入口：多轮记忆 + 技术摘要全喂 + 数值接地。

    连接策略：全程至多两次开关——先读写会话与上下文原料（一次），LLM 往返
    不持连接，回复落库再开一次。load_ark_config/chat_discussion 经
    ``plans_llm`` 模块属性调用（测试 monkeypatch 点），语义与直接调用一致。
    """
    with closing(connect(_db_path(request))) as conn:
        if body.session_id:
            session = get_session(conn, body.session_id)
            if session is None:
                raise HTTPException(status_code=404, detail=f"会话不存在: {body.session_id}")
        else:
            session = create_session(
                conn, body.symbol, body.message[:20] or "新会话"
            )
        history_rows = list_messages(conn, session.session_id, limit=20)

        ctx_payload: dict = {}
        alerts: list = []
        service = getattr(request.app.state, "analysis_service", None)
        # symbol 解析优先级：显式（symbol 上下文）> 消息中提取 > 会话继承。
        # 全局会话里用户报代码（「515880那个」）也能带出技术材料，不再反问。
        explicit = body.context_kind == "symbol" and body.symbol
        symbol: str | None = body.symbol if explicit else None
        if symbol is None and service is not None:
            symbol = _resolve_symbol_from_message(body.message, service)
            if symbol is None:
                symbol = _last_resolved_symbol(history_rows)
        if symbol is not None and service is not None:
            entry = service.get(symbol)
            if entry.result is None:
                if explicit:
                    raise HTTPException(
                        status_code=502, detail=entry.error or "分析不可用"
                    )
                symbol = None  # 提取/继承的代码分析失败不炸请求，退 global
            else:
                from lei_signal.api.routes.opportunities import (  # noqa: PLC0415
                    buy_point_review,
                )
                review = buy_point_review(request, symbol)
                plans = [
                    p for p in list_plans(conn, symbol=symbol)
                    if p.state in ("armed", "entered")
                ]
                open_items = [
                    i for p in plans for i in list_action_items(
                        conn, p.plan_id, state="open"
                    )
                ]
                ctx_payload = build_discussion_context(
                    entry.result, review.model_dump(), plans, open_items
                )
                ctx = context_from_result(entry.result)
                alerts = [a for p in plans for a in evaluate_plan(p, ctx)]
        if symbol is None:
            ctx_payload = {"context_kind": "global"}

    config = plans_llm.load_ark_config()
    reply: str | None = None
    grounded = False
    # 数值白名单 = 技术材料数值 ∪ 本轮 user message 中出现的数字
    # （用户问「8700 是不是更好」、LLM 回显「你说的 8700」时不误降级）
    allowed_nums = collect_payload_numbers(ctx_payload) | frozenset(
        extract_market_numbers(body.message)
    )
    history = [{"role": m.role, "content": m.content} for m in history_rows]
    if config is not None:
        try:
            raw = plans_llm.chat_discussion(ctx_payload, history, body.message, config)
            if raw is not None:
                ok_num, num_reason = verify_numeric_grounding(raw, allowed_nums)
                rule_ids = {a.rule_id for a in alerts if a.rule_id}
                ok_txt, txt_reason = _discussion_txt_ok(raw, rule_ids)
                if ok_num and ok_txt:
                    reply, grounded = raw, True
                else:
                    logger.warning("讨论 chat 校验未过：numeric=%s text=%s",
                                   num_reason, txt_reason)
                    raw2 = plans_llm.chat_discussion(
                        ctx_payload, history, body.message, config
                    )
                    if raw2 is not None:
                        ok2n, _ = verify_numeric_grounding(raw2, allowed_nums)
                        ok2t, _ = _discussion_txt_ok(raw2, rule_ids)
                        if ok2n and ok2t:
                            reply, grounded = raw2, True
        except Exception:  # noqa: BLE001  网络层已在 llm.py 捕获返 None，此处兜真 bug 路径
            logger.warning("讨论 chat LLM 段意外异常，走降级模板", exc_info=True)

    if reply is None:
        reply = _degraded_reply(symbol or "", ctx_payload)
        grounded = False

    trace = _build_trace(alerts)
    meta: dict = {"trace": [t.model_dump() for t in trace]}
    if symbol is not None:
        # 记住本轮生效的标的：后续轮「筹码呢」无代码也能继承材料
        meta["resolved_symbol"] = symbol
    with closing(connect(_db_path(request))) as conn:
        append_message(conn, session.session_id, "user", body.message, True, {})
        append_message(conn, session.session_id, "assistant", reply, grounded, meta)
    return AgentChatReply(
        session_id=session.session_id, reply=reply, grounded=grounded,
        trace=trace, resolved_symbol=symbol,
    )


@router.post("/agent/sessions", response_model=AgentSessionDTO)
def create_agent_session(request: Request, body: CreateSessionRequest) -> AgentSessionDTO:
    with closing(connect(_db_path(request))) as conn:
        s = create_session(conn, body.symbol, body.title_cn or "新会话")
    return AgentSessionDTO(
        session_id=s.session_id, symbol=s.symbol, title_cn=s.title_cn,
        last_active_at=s.last_active_at,
    )


@router.get("/agent/sessions", response_model=list[AgentSessionDTO])
def list_agent_sessions(request: Request, symbol: str | None = None) -> list[AgentSessionDTO]:
    with closing(connect(_db_path(request))) as conn:
        sessions = list_sessions(conn, symbol=symbol)
        out = []
        for s in sessions:
            msgs = list_messages(conn, s.session_id, limit=1)
            out.append(AgentSessionDTO(
                session_id=s.session_id, symbol=s.symbol, title_cn=s.title_cn,
                last_active_at=s.last_active_at,
                last_message_cn=msgs[-1].content[:50] if msgs else "",
            ))
    return out


@router.get("/agent/sessions/{session_id}/messages", response_model=list[AgentMessageDTO])
def agent_session_messages(request: Request, session_id: str) -> list[AgentMessageDTO]:
    with closing(connect(_db_path(request))) as conn:
        if get_session(conn, session_id) is None:
            raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")
        msgs = list_messages(conn, session_id, limit=100)
    return [
        AgentMessageDTO(role=m.role, content=m.content, grounded=m.grounded,
                        created_at=m.created_at)
        for m in msgs
    ]


__all__ = ["router"]
