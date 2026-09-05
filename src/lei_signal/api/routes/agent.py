"""监督员 agent 表达层路由：接地问答（LLM 只表达，判定权在 Python）。

复用 /alerts 的确定性判定（evaluate_plan），把 alert 讲成人话或回答用户提问。
LLM 输出必须过 ``verify_grounding``（禁用词 + rule_id 白名单），失败降级
``render_alerts`` 模板。plans.py 明确「不接 LLM」，故本路由独立成文件。
"""
from __future__ import annotations

import contextlib
import json
import logging
import re
from contextlib import closing

from fastapi import APIRouter, HTTPException, Request

from lei_signal.api.config import INDEX_OVERRIDES, OVERSEAS_NAME_CN
from lei_signal.api.config import sqlite_path as default_db
from lei_signal.api.labels import THS_INDUSTRY_NAMES
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


#: 中文口语片段里的常见废话词——先剔掉再做名字匹配，降低误命中。
_NAME_STOPWORDS = frozenset((
    "怎么看", "怎么样", "怎么", "现在", "觉得", "帮我", "看看", "看一下",
    "分析", "一下", "买点", "这个", "那个", "什么", "如何", "今天", "昨天",
    "还能", "可以", "没有", "自己", "走势", "情况", "问题", "意思",
))
_CJK_RUN_RE = re.compile(r"[\u4e00-\u9fa5]+")


def _lcs_len(a: str, b: str) -> int:
    """两串最长公共子串长度（名字都短，O(nm) 足够）。"""
    best = 0
    prev = [0] * (len(b) + 1)
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        ai = a[i - 1]
        for j in range(1, len(b) + 1):
            if ai == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
        prev = cur
    return best


def _static_symbol_name(symbol: str, db_name: str | None) -> str:
    """标的中文名：DB 存的名 > TH 行业静态表 > 指数/海外静态表。零 IO。

    生产库 watchlist 的 display_name 常为空（只存代码），取名全靠静态表；
    特意**不走分析服务取名**——冷启动会逐标的拉行情（曾致 46s 请求 +
    database is locked），名称联动必须是廉价操作。
    """
    name = str(db_name or "").strip()
    if name:
        return name
    if symbol.startswith("TH") and symbol.endswith(".SECTOR"):
        return THS_INDUSTRY_NAMES.get(symbol.split(".")[0][2:], "")
    override = INDEX_OVERRIDES.get(symbol)
    if override is not None:
        return override.display_name
    return OVERSEAS_NAME_CN.get(symbol, "")


#: 口语别名 → 标的（目录名不含的常用说法）。命中优先级：自选 > 别名 > 目录精确子串。
_CATALOG_ALIAS: dict[str, str] = {
    "科创": "000688.SS",
    "科创板": "000688.SS",
    "科创50": "000688.SS",
    "恒生科技": "^HSTECH",
    "中概": "513050.SS",
    "中概互联": "513050.SS",
    "越南": "513880.SS",
}


def _resolve_symbol_by_catalog(message: str) -> str | None:
    """目录搜索层：自选没命中时，按「目录名完整出现在话里」+ 口语别名解析。

    「白酒板块现在怎么看」→ 目录名「白酒」完整在句中 → TH881273；
    「科创板块现在怎么看」→ 别名表「科创」→ 000688.SS（科创50）。
    不做模糊公共子串：目录词汇面大（90行业+500概念），2 字模糊串会
    把「市场环境」误配到「环保工程」这类。命中的 symbol 由调用方交给
    分析服务，失败自然回退全局。
    """
    from lei_signal.api import catalog as catalog_mod  # noqa: PLC0415
    from lei_signal.api.config import STRATEGY_INDICES, US_ETFS  # noqa: PLC0415
    from lei_signal.api.labels import THS_INDUSTRY_NAMES  # noqa: PLC0415

    # 1) 口语别名（最长键优先，防「科创板」被「科创」截胡）
    for alias in sorted(_CATALOG_ALIAS, key=len, reverse=True):
        if alias in message:
            return _CATALOG_ALIAS[alias]

    # 2) 目录名完整出现在话里（行业/指数/美股ETF/概念）
    entries: list[tuple[str, str]] = []  # (symbol, name)
    entries += [(f"TH{code}", name) for code, name in THS_INDUSTRY_NAMES.items()]
    entries += [(idx.symbol, idx.display_name) for idx in STRATEGY_INDICES]
    entries += [(etf.symbol, etf.display_name) for etf in US_ETFS]
    with contextlib.suppress(Exception):  # 概念目录缺席不影响其余三组
        entries += [
            (str(c.get("symbol", "")), str(c.get("name", "")))
            for c in catalog_mod.concept_boards()
            if c.get("symbol")
        ]

    best: tuple[int, str] | None = None  # (名称更长=更具体, symbol)
    for symbol, name in entries:
        if name and name in message and (best is None or len(name) > best[0]):
            best = (len(name), symbol)
    return best[1] if best else None


def _resolve_symbol_by_name(message: str, watch_items: list) -> str | None:
    """中文名称模糊解析：说「通信设备」「纳指怎么样」也能带出对应标的。

    匹配对象是自选列表的中文名（DB display_name，缺失时静态表取名：
    「通信设备（中证）」「通信ETF」…）。策略：取消息里的连续中文片段，
    与名称做包含或最长公共子串匹配，公共部分 ≥2 字即命中（口语常带尾巴：
    「通信设备怎么看」vs「通信ETF」公共「通信」2字 → 命中）。多命中取
    分高者（更具体优先）。整段命中停用词的片段（「怎么看」）跳过。
    """
    scored: list[tuple[int, str]] = []
    names: list[tuple[str, str]] = []
    for w in watch_items:
        name = _static_symbol_name(w.symbol, getattr(w, "display_name", None))
        if name:
            names.append((w.symbol, name))
    for frag in _CJK_RUN_RE.findall(message):
        if frag in _NAME_STOPWORDS:
            continue
        for symbol, name in names:
            if frag == name or frag in name or name in frag:
                score = max(len(frag), len(name))
            else:
                score = _lcs_len(frag, name)
            if score >= 2:
                scored.append((score, symbol))
    if not scored:
        return None
    scored.sort(key=lambda t: -t[0])
    return scored[0][1]


def _payload_symbol_numbers(ctx_payload: dict) -> set[float]:
    """上下文字符串里 ≥4 位的数字段（标的/板块代码，如 TH881129 的 881129）。

    verify_numeric_grounding 用宽泛数字正则抽回复文本，代码串会被当数值；
    这些数字来自系统材料本身，收集进白名单避免「提代码=编数字」的误伤。
    """
    nums: set[float] = set()

    def walk(value: object) -> None:
        if isinstance(value, str):
            for token in re.findall(r"\d{4,}", value):
                try:
                    nums.add(float(token))
                except ValueError:  # pragma: no cover - 纯数字正则不会走到
                    continue
        elif isinstance(value, dict):
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(ctx_payload)
    return nums


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


def _prepare_discussion(
    request: Request, body: AgentChatRequest, on_stage=None
) -> tuple[str, list, dict, list, str | None]:
    """agent_chat 与流式版共用的准备段（一个连接内完成）。

    返回 (session_id, history_rows, ctx_payload, alerts, symbol)。
    阶段回调 ``on_stage``（可选）用于流式路径向 UI 报告调用链进度。
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
        # symbol 解析优先级：显式（symbol 上下文）> 消息中代码 > 中文名称 > 会话继承。
        # 全局会话里用户报代码（「515880那个」）或说名字（「通信设备」）都能带出材料。
        explicit = body.context_kind == "symbol" and body.symbol
        symbol: str | None = body.symbol if explicit else None
        if on_stage:
            on_stage("resolve", "识别标的与意图")
        if symbol is None and service is not None:
            symbol = _resolve_symbol_from_message(body.message, service)
            if symbol is None:
                from lei_signal.api.watchlist import list_watchlist  # noqa: PLC0415

                symbol = _resolve_symbol_by_name(body.message, list_watchlist(conn))
            if symbol is None:
                symbol = _resolve_symbol_by_catalog(body.message)
            if symbol is None:
                symbol = _last_resolved_symbol(history_rows)
        if symbol is not None and service is not None and on_stage:
            on_stage("fetch", f"拉取 {symbol} 行情（首次约 1 分钟）")
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
                if on_stage:
                    on_stage("context", "组装技术材料与监督状态")
                news_brief = None
                major_events = None
                try:
                    from lei_signal.newsfeed.service import (  # noqa: PLC0415
                        NewsfeedService,
                    )

                    _nf = NewsfeedService()
                    news_brief = _nf.watchlist_brief(
                        [{
                            "symbol": symbol,
                            "display_name": getattr(entry.result, "display_name", "") or symbol,
                            "market": "",
                        }],
                        days=5,
                    )
                    major_events = _nf.major_events_brief()
                except Exception:  # noqa: BLE001  消息面缺席不阻断技术材料
                    news_brief = None
                    major_events = None
                ctx_payload = build_discussion_context(
                    entry.result, review.model_dump(), plans, open_items,
                    news_brief=news_brief,
                    major_events=major_events,
                )
                ctx = context_from_result(entry.result)
                alerts = [a for p in plans for a in evaluate_plan(p, ctx)]
        if symbol is None:
            ctx_payload = {"context_kind": "global"}
            # 全局兜底材料：宽度+融资一句话（叙事层），搜不到标的时
            # 至少能答大盘环境，而不是两手一摊说没数据。
            try:
                from lei_signal.copilot import breadth as b  # noqa: PLC0415

                ctx_payload["breadth_cn"] = b.a_share_breadth_cn()
            except Exception:  # noqa: BLE001
                ctx_payload["breadth_cn"] = None
            try:
                from lei_signal.copilot import sentiment as st  # noqa: PLC0415

                m = st.margin_regime_cn()
                ctx_payload["margin_cn"] = (m or {}).get("regime_cn")
            except Exception:  # noqa: BLE001
                ctx_payload["margin_cn"] = None
            # 重大事件（客观字段 only，2026-09-05 用户口径）：聊大盘环境时
            # 带上「英伟达资本开支」级别的产业/宏观大事，叙事参考层。
            try:
                from lei_signal.newsfeed.service import (  # noqa: PLC0415
                    NewsfeedService,
                )

                ctx_payload["major_events"] = NewsfeedService().major_events_brief()
            except Exception:  # noqa: BLE001
                ctx_payload["major_events"] = None
        return session.session_id, history_rows, ctx_payload, alerts, symbol


@router.post("/agent/chat", response_model=AgentChatReply)
def agent_chat(request: Request, body: AgentChatRequest) -> AgentChatReply:
    """统一讨论入口：多轮记忆 + 技术摘要全喂 + 数值接地。

    连接策略：全程至多两次开关——先读写会话与上下文原料（一次），LLM 往返
    不持连接，回复落库再开一次。load_ark_config/chat_discussion 经
    ``plans_llm`` 模块属性调用（测试 monkeypatch 点），语义与直接调用一致。
    """
    session_id, history_rows, ctx_payload, alerts, symbol = _prepare_discussion(
        request, body
    )

    config = plans_llm.load_ark_config()
    reply: str | None = None
    grounded = False
    # 数值白名单 = 技术材料数值 ∪ 本轮 user message 中出现的数字
    # （用户问「8700 是不是更好」、LLM 回显「你说的 8700」时不误降级）
    # ∪ 上下文字符串里的代码数字段（TH881129/515880 这类标的代码会被校验器
    #   当数字抽取，它们本就来自系统材料，不进白名单就是误伤——glm-5.3 讲
    #   板块时必带代码，曾因此整链降级）
    allowed_nums = (
        collect_payload_numbers(ctx_payload)
        | frozenset(extract_market_numbers(body.message))
        | frozenset(_payload_symbol_numbers(ctx_payload))
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
        append_message(conn, session_id, "user", body.message, True, {})
        append_message(conn, session_id, "assistant", reply, grounded, meta)
    return AgentChatReply(
        session_id=session_id, reply=reply, grounded=grounded,
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



def _quick_card(ctx_payload: dict, symbol: str | None) -> dict | None:
    """标的速览卡（展示层）：总评徽标 + 上下各一关键价位与距离。

    数值全部直读 ctx_payload；距离百分比为展示层算术（收盘与价位之比），
    非判定层新数值。与右栏 K 线配合读图，AI 正文不必罗列价位清单。
    """
    if not symbol or not isinstance(ctx_payload, dict):
        return None
    a = ctx_payload.get("assessment") or {}
    dual = ctx_payload.get("dual_ma") or {}
    close = dual.get("close")
    if close is None:
        return None
    card: dict = {
        "symbol": symbol,
        "display_name": ctx_payload.get("display_name") or symbol,
        "as_of": ctx_payload.get("as_of"),
        "close": close,
        "color_cn": a.get("color_cn"),
        "stage_cn": a.get("stage_cn"),
        "risk_cn": a.get("risk_state_cn"),
        "levels": [],
    }
    levels: list[dict] = []
    for st in ctx_payload.get("structures") or []:
        if not isinstance(st, dict):
            continue
        for role, key in (("失效位", "c_price"), ("阻力位", "neckline"),
                               ("前高", "reference_high")):
            price = (st.get("key_prices") or {}).get(key)
            if price is None or not isinstance(price, (int, float)) or price <= 0:
                continue
            levels.append({
                # 方向优先于字段名：低于现价的统一叫「下方关键位」，
                # 高于现价的才叫「上方阻力」，避免把下方支撑标成阻力。
                "role": ("下方关键位" if float(price) < float(close)
                         else ("上方阻力" if role == "阻力位" else role)),
                "price": float(price),
                "kind": "below" if price < float(close) else "above",
                "dist_pct": round(abs(float(close) / float(price) - 1) * 100, 2),
                "from_cn": st.get("type_cn") or "",
            })
    below = sorted(
        (v for v in levels if v["kind"] == "below"),
        key=lambda x: -x["price"],
    )[:2]
    above = sorted(
        (v for v in levels if v["kind"] == "above"),
        key=lambda x: x["price"],
    )[:1]
    card["levels"] = below + above
    card["note_cn"] = "价位直读系统结构（研究代理）；距离为展示层换算"
    return card


@router.post("/agent/chat/stream")
def agent_chat_stream(request: Request, body: AgentChatRequest):
    """流式讨论入口：SSE 推送调用链阶段 + GLM 真·逐字正文 + 校验结果。

    事件协议（data 均为 JSON）：
      stage {key, text}      阶段推进（resolve/fetch/context/llm/verify）
      token {t}              正文增量（AI 原文流式）
      done  {session_id, resolved_symbol, grounded, verify_note?, fallback?}
    数值/禁用词校验在聚合全文后执行：未过校验时 done 携带 verify_note 与
    模板 fallback，前端在原文下方并排展示模板直出——红线不因流式而放松。
    LLM 不可用（无凭据/网络失败零 token）时直接推模板 fallback。
    """
    import json as _json
    from collections.abc import Iterator

    from fastapi.responses import StreamingResponse  # noqa: PLC0415

    def _sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {_json.dumps(data, ensure_ascii=False)}\n\n"

    def _generate() -> Iterator[str]:
        import queue as _queue
        import threading as _threading

        # 准备段（解析/行情/材料）在后台线程跑，阶段事件经队列实时推给客户端：
        # 用户在等待的第一秒就能看到「识别标的→拉取行情」逐条点亮，而不是
        # 全部跑完才收到一串。
        q: _queue.Queue[tuple] = _queue.Queue()

        def on_stage(key: str, text: str) -> None:
            q.put(("stage", (key, text)))

        def _work() -> None:
            try:
                q.put((
                    "prepared",
                    _prepare_discussion(request, body, on_stage=on_stage),
                ))
            except Exception as exc:  # noqa: BLE001
                q.put(("error", exc))

        _threading.Thread(target=_work, daemon=True).start()

        prepared = None
        while True:
            try:
                kind, payload = q.get(timeout=180)
            except _queue.Empty:
                yield _sse("done", {
                    "session_id": "", "resolved_symbol": None, "grounded": False,
                    "verify_note": "准备阶段超时（180s），请稍后重试。",
                })
                return
            if kind == "stage":
                yield _sse("stage", {"key": payload[0], "text": payload[1]})
            elif kind == "error":
                yield _sse("done", {
                    "session_id": "", "resolved_symbol": None, "grounded": False,
                    "verify_note": f"准备阶段失败：{payload}",
                })
                return
            else:
                prepared = payload
                break

        session_id, history_rows, ctx_payload, alerts, symbol = prepared

        config = plans_llm.load_ark_config()
        pieces: list[str] = []
        if config is not None:
            yield _sse("stage", {"key": "llm", "text": "AI 组织语言（逐字输出）"})
            for piece in plans_llm.chat_discussion_stream(
                ctx_payload,
                [{"role": m.role, "content": m.content} for m in history_rows],
                body.message,
                config,
            ):
                pieces.append(piece)
                yield _sse("token", {"t": piece})

        full = "".join(pieces).strip()
        grounded = False
        verify_note = ""
        fallback = ""
        if full:
            from lei_signal.plans.grounding import (  # noqa: PLC0415
                collect_payload_numbers,
                verify_numeric_grounding,
            )

            allowed_nums = (
                collect_payload_numbers(ctx_payload)
                | frozenset(extract_market_numbers(body.message))
                | frozenset(_payload_symbol_numbers(ctx_payload))
            )
            rule_ids = {a.rule_id for a in alerts if a.rule_id}
            ok_num, num_reason = verify_numeric_grounding(full, allowed_nums)
            ok_txt, txt_reason = _discussion_txt_ok(full, rule_ids)
            if ok_num and ok_txt:
                grounded = True
            else:
                verify_note = (
                    f"以上 AI 流式原文未过溯源校验（{txt_reason or num_reason}），"
                    "请以下方模板直出为准。"
                )
        if not full or not grounded:
            fallback = _degraded_reply(symbol or "", ctx_payload)

        trace = _build_trace(alerts)
        meta: dict = {"trace": [t.model_dump() for t in trace]}
        if symbol is not None:
            meta["resolved_symbol"] = symbol
        try:
            with closing(connect(_db_path(request))) as conn:
                append_message(conn, session_id, "user", body.message, True, {})
                append_message(
                    conn, session_id, "assistant", full or fallback, grounded, meta
                )
        except Exception:  # noqa: BLE001  落库失败不断流（锁窗口下次再试不可行，丢历史可接受）
            yield _sse(
                "done", {"session_id": session_id, "resolved_symbol": symbol,
                         "grounded": grounded, "verify_note": "会话记录保存失败（不影响本次回复）",
                         "fallback": fallback})
            return
        yield _sse(
            "done",
            {
                "session_id": session_id,
                "resolved_symbol": symbol,
                "grounded": grounded,
                **({"verify_note": verify_note} if verify_note else {}),
                **({"fallback": fallback} if fallback else {}),
                **({"quick_card": _quick_card(ctx_payload, symbol)} if symbol else {}),
            },
        )

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
