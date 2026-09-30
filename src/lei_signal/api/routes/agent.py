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
from datetime import datetime
from pathlib import Path

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
    r"(?<![A-Za-z0-9.])(?:TH\d{6}|SW\d{4}|BK\d{4}|\d{6})(?:\.(?:SS|SZ|SECTOR))?(?![A-Za-z0-9])"
    r"|(?<![A-Za-z0-9])[A-Z]{2,5}(?:\.(?:SS|SZ))?(?![A-Za-z0-9])",
    re.IGNORECASE,
)
#: 最多尝试验证的候选数——每次失败验证都是一次分析往返，控制成本。
_MAX_SYMBOL_PROBES = 3


def _symbol_candidates_from_message(message: str) -> list[str]:
    """从用户消息中提取**语法合法**的标的候选（03B-R2 契约1/r3）。

    对象识别与资料可用性**分离**：`resolve_symbol` 校验通过的代码就是合法
    对象——即使该标的还没有缓存行情也仍是它（缺数据走正式分析路径获取或
    明确报缺），**不能**回退成页面选中的另一个标的。含数字的候选
    （A股/ETF/板块）优先于纯字母（美股/ETF）。

    运行编号（run_id）误判防护（d2）：消息里给出的 run_id 形如
    `20260909-174652-779593`，其数字/字母片段（174652、779593、RUN）会被
    `_SYMBOL_TOKEN_RE` 当成证券候选；先识别该身份并从其文本片段中剔除，避免
    把运行编号当成证券代码。用户同时明确指定的其他证券仍正常解析。"""
    from lei_signal.data.symbols import resolve_symbol  # noqa: PLC0415
    from lei_signal.copilot import resolve as resolve_mod  # noqa: PLC0415

    # 只遮住编号所在的原文位置；同值的独立证券代码仍是用户明确指定的对象。
    scan = resolve_mod._RUN_ID_RE.sub(
        lambda match: " " * (match.end() - match.start()), message or "",
    )

    tokens = _SYMBOL_TOKEN_RE.findall(scan)
    ordered = sorted(
        dict.fromkeys(t.upper() for t in tokens),
        key=lambda t: 0 if any(c.isdigit() for c in t) else 1,
    )
    valid: list[str] = []
    for i, tok in enumerate(ordered):
        if i >= _MAX_SYMBOL_PROBES:
            break
        if tok == "ETF":
            continue
        try:
            info = resolve_symbol(tok)
        except ValueError:
            continue
        # 收口一（二轮复验 2026-09-17）：纯字母 token 同时是技术指标词时，
        # 指标/方法语境不算指名该证券——「ATR止损/ATR距离/ATR缓冲」是波动
        # 指标用法，不能因此把对象从当前讨论截走；「ATR 这只股票」这类明确
        # 证券问法仍正常解析（不全局禁用代码）。
        if tok in _INDICATOR_WORD_SYMBOLS and \
                _INDICATOR_WORD_SYMBOLS[tok].search(message or ""):
            continue
        if info.symbol not in valid:
            valid.append(info.symbol)
    return valid


def _resolve_symbol_from_message(message: str, service: object,
                                 *, fetch: bool = True) -> str | None:
    """兼容入口：消息候选中第一个**当前可分析**的标的（老调用方语义）。

    03B-R2 起统一入口的对象识别改用 ``_symbol_candidates_from_message``
    （可用性无关）；本函数保留给「必须有现成分析结果」的老路径。"""
    for symbol in _symbol_candidates_from_message(message):
        try:
            try:
                entry = service.get(symbol, fetch=fetch)  # type: ignore[attr-defined]
            except TypeError:
                entry = service.get(symbol)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001  分析服务自身兜底，双保险
            continue
        if getattr(entry, "result", None) is not None:
            return symbol
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
    """标的中文名：DB 存的名 > TH 行业静态表 > 自选补充表 > 指数/海外静态表。零 IO。

    生产库 watchlist 的 display_name 常为空（只存代码），取名全靠静态表；
    特意**不走分析服务取名**——冷启动会逐标的拉行情（曾致 46s 请求 +
    database is locked），名称联动必须是廉价操作。
    """
    from lei_signal.copilot.subjects import display_name

    name = display_name(symbol, db_name)
    if name:
        return name
    if symbol.startswith("TH") and symbol.endswith(".SECTOR"):
        return THS_INDUSTRY_NAMES.get(symbol.split(".")[0][2:], "")
    watch_name = _WATCH_NAME_CN.get(symbol)
    if watch_name:
        return watch_name
    override = INDEX_OVERRIDES.get(symbol)
    if override is not None:
        return override.display_name
    return OVERSEAS_NAME_CN.get(symbol, "")


#: 口语别名 → 标的（目录名不含的常用说法）。命中优先级：自选 > 别名 > 目录精确子串。
#: 主控裁决（2026-09-15）：别名只收**用户明确指定的产品/指数**；
#: 「科创」「科创板」这类整个板块的泛指不再静默映射到科创50指数——
#: 板块整体没有唯一可核实对象时，由 resolve 层澄清（科创50 只作可选
#: 观察参考并明确它不代表整个板块），不用指数顶替板块。
_CATALOG_ALIAS: dict[str, str] = {
    "科创50": "000688.SS",
    "恒生科技": "^HSTECH",
    "中概": "513050.SS",
    "中概互联": "513050.SS",
    "越南": "513880.SS",
}

#: 自选中文名补充表（2026-09-05）：watchlist 的 display_name 常为空，
#: TH 行业板块有 THS_INDUSTRY_NAMES 兜底，但 ETF/个股/部分海外没有——
#: 「通信ETF」这类自然名此前对 515880 解析不到（名字链全空）。
#: **维护点**：自选新增非 TH 板块标的时，若 DB 未写 display_name 需在此补。
_WATCH_NAME_CN: dict[str, str] = {
    "515880.SS": "通信ETF",
    "512890.SS": "红利低波ETF",
    "601689.SS": "拓普集团",
    "IGV": "美国软件IGV",
}


#: 同名证券代码也是技术指标词的守卫（收口一）：词 → 指标/方法语境模式。
_INDICATOR_WORD_SYMBOLS: dict[str, re.Pattern[str]] = {
    "ATR": re.compile(r"ATR.{0,8}(止损|止盈|缓冲|距离|指标|通道|倍数|退出|真实波幅)|"
                      r"(止损|止盈|缓冲|距离|指标|通道|倍数|退出|真实波幅).{0,8}ATR",
                      re.IGNORECASE),
}


def _resolve_symbol_by_catalog(message: str) -> str | None:
    """目录搜索层：自选没命中时，按「目录名完整出现在话里」+ 口语别名解析。

    「白酒板块现在怎么看」→ 板块名「白酒」完整在句中 → TH881273；
    「科创50指数现在怎么看」→ 别名表「科创50」→ 000688.SS。
    不做模糊公共子串：目录词汇面大（90行业+500概念），2 字模糊串会
    把「市场环境」误配到「环保工程」这类。命中的 symbol 由调用方交给
    分析服务，失败自然回退全局。

    主控裁决（2026-09-15）：用户**明确指定**的对象（板块专名/别名/目录
    全名）优先于笼统的「板块/版块/行业」关键词——「科创50板块」里的
    科创50是指数身份，不被板块二字截断；而「科创板块/科创板整体」没有
    唯一可核实对象 → None（由 resolve 层澄清，不用指数/ETF 顶替板块）。
    """
    from lei_signal.api import catalog as catalog_mod  # noqa: PLC0415
    from lei_signal.api.config import (  # noqa: PLC0415
        DASHBOARD_INDICES,
        STRATEGY_INDICES,
        US_ETFS,
    )
    from lei_signal.api.labels import THS_INDUSTRY_NAMES  # noqa: PLC0415

    from lei_signal.copilot.subjects import named_subject

    # 1) 板块专名（通信板块→BK1215 等，含「板块」二字的真实板块）
    named = named_subject(message)
    if named:
        return named

    # 2) 口语别名（最长键优先；明确对象优先于「板块」关键词）
    for alias in sorted(_CATALOG_ALIAS, key=len, reverse=True):
        if alias in message:
            return _CATALOG_ALIAS[alias]

    # 3) 目录名完整出现在话里（默认大盘/行业/指数/美股ETF/概念）。
    #    DASHBOARD_INDICES 一并装入（2026-09-18 名称绑定修复）：否则说
    #    「沪深300/上证指数」这类默认大盘名解析不到，旧选中/会话对象接管，
    #    回答和资料卡跟错对象。
    entries: list[tuple[str, str]] = []  # (symbol, name)
    entries += [(idx.symbol, idx.display_name) for idx in DASHBOARD_INDICES]
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
            # 收口一（二轮复验 2026-09-17）：同名代码同时是技术指标词时，
            # 指标/方法语境不算指名该证券——「ATR止损/ATR距离/ATR缓冲」是
            # 波动指标用法，不该把对象截走；「ATR 这只股票/看看 ATR」这类
            # 明确证券问法仍按证券身份解析（不全局禁用代码）。
            if name in _INDICATOR_WORD_SYMBOLS and \
                    _INDICATOR_WORD_SYMBOLS[name].search(message):
                continue
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
    # 第一档：完整名字直接出现在消息里（含中英混合名如「通信ETF」——CJK
    # 分段会把 ETF 切掉，单靠中文片段匹配时更长的中文名会抢分：说「通信ETF」
    # 曾被「通信设备（中证）」以 8>5 截走、解析到无数据源的指数后整体退
    # global）。名字完整出现是最强信号，以 100+名字长度 显著胜出。
    # 名字与消息都去空格再比：「半导体 SOXX」对「半导体SOXX」也要命中。
    msg_flat = message.replace(" ", "")
    full_hits: list[tuple[int, str, str]] = []
    for symbol, name in names:
        if name and name.replace(" ", "") in msg_flat:
            full_hits.append((len(name), symbol, name))
    # 短名是另一个更长名字的真子串时，第一档作废——用户说的很可能是长名
    # （「通信」嵌在「通信设备ETF」里：说「通信设备」不该被「通信」截走；
    # 竞争检查对全部自选名做，不限于也进第一档的名字）。
    all_names = [n for _, n in names if n]
    for _, symbol, name in full_hits:
        if not any(other != name and name in other for other in all_names):
            scored.append((100 + len(name), symbol))
    for frag in _CJK_RUN_RE.findall(message):
        if frag in _NAME_STOPWORDS:
            continue
        for symbol, name in names:
            # name in frag（名字被更长的话包含）仅对中文名 >=3 字开放：
            # 「科技 XLK」的中文部分只有 2 字，会被「恒生科技」这类长词
            # 误包含（2026-09-06 真机：「恒生科技」被截到 XLK）。
            name_cn = "".join(ch for ch in name if "\u4e00" <= ch <= "\u9fa5")
            name_in_ok = len(name_cn) >= 3 and name_cn in frag
            if frag == name or frag in name or name_in_ok:
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
    """上下文字符串里的数字段（标的/板块代码 + 消息标题内嵌数值）。

    verify_numeric_grounding 用宽泛数字正则抽回复文本，代码串/标题数字会被
    当数值；这些数字来自系统材料本身，收集进白名单避免「提代码/引标题=
    编数字」的误伤。2026-09-05 扩展：改用 extract_market_numbers 抽取——
    它会先剥千分位逗号（标题「162,000」裸正则只能抽出 162/000 两个碎段，
    AI 照抄 162000 时反被拒）；豁免口径同校验器，两边对称。

    消息面叙事子树（news/major_events）的数字额外预扩单位换算族
    （×10/×100/÷10/÷100）：标题金额常以 Billion/百万 计，AI 口述换算成
    亿（12.93B→129.3亿）是精确换算不是编造；价位类白名单不扩，保持严格
    （曾试过在 verify 层做通用换算派生，任何价位×10 都被放水，已回滚）。
    """
    from lei_signal.plans.grounding import extract_market_numbers  # noqa: PLC0415

    narrative_keys = {"news", "major_events"}
    nums: set[float] = set()

    def expand_units(v: float) -> None:
        for k in (10.0, 100.0, 0.1, 0.01):
            nums.add(v * k)

    def walk(value: object, narrative: bool = False) -> None:
        if isinstance(value, str):
            got = list(extract_market_numbers(value))
            nums.update(got)
            if narrative:
                for v in got:
                    expand_units(v)
            for token in re.findall(r"\d{4,}", value):
                try:
                    nums.add(float(token))
                except ValueError:  # pragma: no cover - 纯数字正则不会走到
                    continue
        elif isinstance(value, dict):
            for key, child in value.items():
                walk(child, narrative=narrative or key in narrative_keys)
        elif isinstance(value, list):
            for child in value:
                walk(child, narrative=narrative)

    walk(ctx_payload)
    return nums


_A_SHARE_CODE_PREFIXES = frozenset(
    {"60", "68", "51", "56", "58", "00", "30", "15", "16", "18"}
)


#: R3 身份标记模式集（agent-whitelist-fix-r3-2026-09-20）：6 位数字必须
#: 紧邻这些「明确标的指向」语境才算代码。只列写法变体（X代码 / 标的X），
#: 不枚举具体数值或前缀白名单之外的证券存在性判断。
_HISTORY_CODE_IDENTITY_MARKERS = re.compile(
    r"(?:"
    # 「代码 510300」「标的代码是 510300」「基金代码：510300」「ETF 代码=510300」
    r"(?:标的|证券|股票|基金|指数|[Ee][Tt][Ff])?代码(?:是|为|[:：=])?"
    # 「标的是 510300」「讨论的标的 510300」——「标的」后只允许是/为/冒号
    r"|标的(?:是|为|[:：=])?"
    r")\s*$"
)

#: R3 候选数字形态：恰好 6 位、前后无相邻数字、非小数的一部分
#: （510300.25 的整数段不算代码）、后面不紧跟计量单位字（元/股/份/手/张/%，
#: 「510300 元」「510300 股」是金额/数量，不是标的）。
_HISTORY_CODE_TOKEN = re.compile(
    r"(?<!\d)(?<!\d\.)\d{6}(?!\d)(?!\.\d)(?!\s*[元股份手张%])"
)


def _history_symbol_numbers(history_rows: list) -> set[float]:  # noqa: ANN001
    """会话历史**用户消息**里的标的代码数字段（S4-2 误拦修复，R3 2026-09-20）。

    会话上下文整体喂给模型（chat_discussion 的 history）；追问轮因消息带
    「板块」命中 asks_for_sector 不继承标的时走全局路径，材料里没有任何
    标的代码，模型回显上一轮讨论过的代码（如 510300）是忠于所给材料，却
    被数值校验当编数字误拦→好答案被换成降级模板（真模型评测
    agent-realmodel-eval-2026-09-20 B 类）。

    R3 身份标记准入（GPT ITERATION:20 BLOCK 纠正，形状过滤不充分）：
    「账户金额是 510300 元」「成交价是 510300.25 元」同为 6 位、无相邻
    数字、前缀合法、来自用户——仅凭形状无法与代码区分。收紧为：6 位
    前缀合法数字必须伴随**文本内明确的标的指向语境**（
    ``_HISTORY_CODE_IDENTITY_MARKERS`` 模式集，见其注释）才入补集；
    无标记→不加入，该句数值由既有 chat_fallback 降级承接。不以枚举
    前缀或排除特定数值代替身份判别。前缀集合
    ``_A_SHARE_CODE_PREFIXES`` 是**本补集支持范围**（沪：60/68/51/56/58；
    深：00/30/15/16/18），不是证券存在性证明。
    来源分层（R2 保持）：只扫 role == "user" 的消息——助手自由文本里的
    代码不得仅因进入历史而自合法化。价位类校验保持严格。
    """
    nums: set[float] = set()
    for m in history_rows:
        if getattr(m, "role", None) != "user":
            continue
        content = getattr(m, "content", None)
        if not isinstance(content, str):
            continue
        for match in _HISTORY_CODE_TOKEN.finditer(content):
            token = match.group()
            if token[:2] not in _A_SHARE_CODE_PREFIXES:
                continue
            # 身份判别：代码前必须紧邻标的指向语境（窗口收 16 字，
            # 覆盖「我要讨论的标的代码是」这类自然前缀）。
            window = content[max(0, match.start() - 16):match.start()]
            if not _HISTORY_CODE_IDENTITY_MARKERS.search(window):
                continue
            try:
                nums.add(float(token))
            except ValueError:  # pragma: no cover - 纯数字正则不会走到
                continue
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


def _market_of(symbol: str) -> str:
    """按标的代码推导市场（真实元信息口径），不给所有市场固定 cn。"""
    if symbol.endswith((".SS", ".SZ")) or symbol.startswith("TH"):
        return "cn"
    if symbol.startswith("^HS"):
        return "hk"
    return "us"


def _resolve_window_for_question(conn, body, symbol, session_id, message) -> dict:
    """03B-R3 T1 单入口窗口选择（一次选定，冻结与比较共用）。

    返回结构化选择结果，绑定对象/start/end/来源/有效状态；本轮比较、问题
    快照、后续继承使用这一份值。流程：
    1. 新明确日期：验证合法性；非法时保留「明确改变但无效」的状态与原因。
    2. 明确采用历史运行：定位**本对象**的具体运行；歧义未解则记「尚未选定」，
       不静默用最新一条（解决跨对象与并发下显示/冻结不一致）。
    3. 没有新选择：读取本对象最近窗口状态；最近是无效/待选则继承其未核实
       状态，不越过它复活更早的有效窗口（u1）。
    """
    from lei_signal.copilot import resolve as resolve_mod

    win_choice = resolve_mod.parse_window_choice(message)
    # ① 本条消息明确起止
    if win_choice and win_choice.get("kind") == "explicit_dates":
        if win_choice.get("invalid"):
            return {"kind": "explicit_dates", "invalid": True,
                    "state": "unverified", "start": None, "end": None,
                    "symbol": symbol, "run_id": None,
                    "source": "message（区间日历非法，未核实）",
                    "reason": win_choice.get("reason") or "日期不合法或倒序"}
        return {"kind": "explicit_dates", "invalid": False, "state": "verified",
                "start": win_choice["start"], "end": win_choice["end"],
                "symbol": symbol, "run_id": None,
                "source": "message（用户本条消息明确给出的区间）"}
    # ② 明确采用历史运行：必须定位**本对象具体且唯一**的运行，不凭最新一条
    # 静默决定（z5）。多个候选且指向未定 → 尚未选定并说明可选范围；用户明确
    # 给出 run_id 则只在候选中定位该运行。data_range 非对象也视为不可用（z6）。
    if win_choice and win_choice.get("kind") == "adopt_run_window" and session_id:
        try:
            cand_rows = conn.execute(
                "SELECT run_id, result_ref FROM agent_backtest_requests "
                "WHERE session_id = ? AND symbol = ? AND status = 'completed' "
                "AND result_ref != '' ORDER BY created_at DESC",
                (session_id, symbol)).fetchall()
        except Exception:  # noqa: BLE001  表缺席不阻断讨论
            cand_rows = []
        want_run = win_choice.get("run_id")
        if want_run:
            cand_rows = [r for r in (cand_rows or []) if r["run_id"] == want_run]
        if len(cand_rows) == 1:
            rrow = cand_rows[0]
            try:
                adopted = json.loads(
                    Path(rrow["result_ref"]).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                adopted = None
            if not isinstance(adopted, dict):
                adopted = {}
            arange = adopted.get("data_range")
            if not isinstance(arange, dict):
                arange = {}
            if arange.get("start") and arange.get("end"):
                return {"kind": "adopt_run_window", "invalid": False,
                        "state": "verified",
                        "start": arange["start"], "end": arange["end"],
                        "symbol": symbol, "run_id": rrow["run_id"],
                        "source": f"adopted:run:{rrow['run_id']}"
                                  "（明确采用该历史运行的窗口）"}
        # 0 个或 >1 个候选：指向未定，不静默用最新一条（z5）
        reason = ("有多个完成运行但指向未定，需明确指定采用哪一份（run_id）"
                  if cand_rows else "未找到本对象已完成的明确运行")
        return {"kind": "adopt_run_window", "invalid": True,
                "state": "unverified", "start": None, "end": None,
                "symbol": symbol, "run_id": None,
                "source": "message（采用历史窗口，但指向未定）",
                "reason": reason}
    # ③ 无新选择：读取本对象最近窗口状态（含无效/待选），不越过它复活旧窗口
    return _read_inherited_window(conn, session_id, symbol)


def _read_inherited_window(conn, session_id, symbol) -> dict:
    """03B-R3 T1：无新选择时读取本对象最近一次窗口状态。最近状态若是无效/
    待选则继承其未核实状态；只有最近状态为有效起止才继承为 verified。"""
    if not session_id:
        return {"kind": "inherit", "invalid": True, "state": "unverified",
                "start": None, "end": None, "symbol": symbol,
                "source": "none（无会话、无选择）"}
    try:
        rows = conn.execute(
            "SELECT meta_json FROM agent_messages WHERE session_id = ? "
            "AND role = 'user' AND meta_json LIKE '%discussion_v1%' "
            "ORDER BY message_id DESC LIMIT 20",
            (session_id,)).fetchall()
    except Exception:  # noqa: BLE001
        return {"kind": "inherit", "invalid": True, "state": "unverified",
                "start": None, "end": None, "symbol": symbol,
                "source": "none（读取继承失败）"}
    for r in rows:
        try:
            snap = (json.loads(r["meta_json"] or "{}") or {}).get("discussion_v1") or {}
        except json.JSONDecodeError:
            continue
        if snap.get("symbol") != symbol:
            continue  # 跨对象不继承
        win = (snap.get("method") or {}).get("window")
        if win is None:
            continue  # 该快照无窗口记录，继续找更早
        # 找到本对象最近一次窗口记录：有效则继承，无效/待选则继承未核实
        if win.get("invalid"):
            return {"kind": "inherit", "invalid": True, "state": "unverified",
                    "start": None, "end": None, "symbol": symbol,
                    "source": win.get("source")
                    or "inherited:question（最近一次选择无效/待选）",
                    "reason": win.get("reason") or "最近一次选择未核实"}
        if win.get("start") and win.get("end"):
            return {"kind": "inherit", "invalid": False, "state": "verified",
                    "start": win["start"], "end": win["end"], "symbol": symbol,
                    "run_id": win.get("run_id"),
                    "source": win.get("source") or "inherited:question"}
        # start/end 缺失但非 invalid 标记：视为未核实，不越过复活
        return {"kind": "inherit", "invalid": True, "state": "unverified",
                "start": None, "end": None, "symbol": symbol,
                "source": win.get("source") or "inherited:question（窗口缺失）",
                "reason": "继承的窗口起止不完整"}
    return {"kind": "inherit", "invalid": True, "state": "unverified",
            "start": None, "end": None, "symbol": symbol,
            "source": "none（无本对象窗口记录）"}


def _read_frozen_window_for_question(conn, question_id: int | None) -> dict | None:
    """03B-R3 T1（恢复路径）：读原问题快照里冻结的窗口选择。恢复/重放已有
    问题时必须用这一份，不按当前会话最新历史重选（避免借到后来讨论的区间）。
    返回 discussion_v1.method.window（有效窗口或无效/待选结构化结果），无则 None。"""
    if question_id is None:
        return None
    try:
        row = conn.execute(
            "SELECT meta_json FROM agent_messages WHERE message_id = ?",
            (question_id,)).fetchone()
    except Exception:  # noqa: BLE001
        return None
    if row is None:
        return None
    try:
        snap = (json.loads(row["meta_json"] or "{}") or {}).get("discussion_v1") or {}
    except json.JSONDecodeError:
        return None
    return (snap.get("method") or {}).get("window")


def _window_projection(selection: dict | None) -> dict | None:
    """展示与冻结共用窗口身份；旧材料没有运行编号时保留未知。"""
    if not selection or not selection.get("start") or not selection.get("end"):
        return None
    return {"start": selection["start"], "end": selection["end"],
            "source": selection.get("source"), "run_id": selection.get("run_id")}


def _discussion_snapshot(conn, body, symbol: str | None,
                         question_id: int | None = None,
                         review_dump: dict | None = None,
                         as_of: str | None = None,
                         session_id: str | None = None,
                         window_sel: dict | None = None) -> dict:
    """03B-R1 §3：本次问题事实的不可变快照（存 user 消息 meta_json.discussion_v1）。
    03B-R2 契约3（r4）：evidence_refs / rule_refs 用 v1.2 完整引用（含内容
    摘要），不再固定空列表/裸 ID 字符串；市场与生成时间取真实元信息——
    行情日只写 observed_at，generated_at 是本次材料生成时间，不互相冒充。"""
    from datetime import UTC as _UTC, datetime as _dt

    # Factor queries freeze their own read-only materials; do not fabricate an
    # analysis_service/rule reference or inherit a technical backtest window.
    if window_sel and window_sel.get("factor_readonly") is not None:
        pack = window_sel["factor_readonly"]
        return {
            "question_id": question_id, "client_request_id": body.client_request_id,
            "symbol": symbol, "context_kind": "factor_readonly",
            "intent": "discussion", "topic": "evidence", "purpose": "unknown",
            "factor_readonly": pack, "method": {}, "rule_refs": [],
            "data_refs": [], "evidence_refs": pack.get("sources", []),
            "backtest_request_ids": [], "plan_id": None, "budget": None,
        }

    from lei_signal.copilot import resolve as resolve_mod
    from lei_signal.data_provenance import (
        MarketDataRef,
        rule_ref,
        ruleset_ref,
        winrate_evidence_ref,
    )

    parsed = resolve_mod.parse_request(body.message)
    candidates = [c.get("rule_id") for c in ((review_dump or {}).get("candidates") or [])
                  if isinstance(c, dict) and c.get("rule_id")]
    now_iso = _dt.now(_UTC).isoformat()
    data_refs: list[dict] = []
    evidence_refs: list[dict] = []
    if symbol:
        data_refs.append(MarketDataRef(
            source_id=("sector_trend_snapshot.json" if symbol.startswith("BK")
                       else "analysis_service(compose.pipeline)"),
            instrument_id=symbol,
            market=_market_of(symbol),
            observed_at=as_of,           # 行情日（数据观察时点）
            available_at=None,           # 来源发布节奏未核实，不猜
            generated_at=now_iso,        # 本次分析材料生成时间
            last_valid_at=as_of,
            health="unknown",
            reason="判定层分析结果；底层行情发布节奏未核实（unknown 不当当前）",
        ).to_dict())
        evidence_refs.extend(data_refs)
        wr = winrate_evidence_ref(symbol)
        evidence_refs.append(wr.to_dict())
    rule_refs = [ruleset_ref().to_dict()]
    rule_refs.extend(rule_ref(rid).to_dict() for rid in candidates if rid)
    history = list_messages(conn, session_id, limit=21) if session_id else []
    if question_id is not None:
        history = [row for row in history if row.message_id < question_id]
    current_background = resolve_mod.apply_user_facts(
        _user_background(history[-20:], symbol), body.message)
    # 03B-R3 T1：窗口选择一次生成（_resolve_window_for_question），此处直接
    # 冻结其结构化结果——不再自行查库选运行，保证「显示」与「存档」是同一份依据
    # （u2：并发下显示与冻结一致）。window_sel 为 None 时退化为即时解析（兜底）。
    if window_sel is None:
        window_sel = _resolve_window_for_question(conn, body, symbol, session_id, body.message)
    if window_sel and window_sel.get("start") and window_sel.get("end"):
        window_frozen = _window_projection(window_sel)
    elif window_sel and window_sel.get("invalid"):
        # 明确但无效/待选的选择也要冻结下来，供后续「继续讨论」继承未核实状态，
        # 不越过它复活更早的有效窗口（u1）。
        window_frozen = {"invalid": True, "state": "unverified",
                         "source": window_sel.get("source"),
                         "reason": window_sel.get("reason"),
                         "symbol": symbol}
    else:
        window_frozen = None
    budget = current_background.get("budget")
    purpose = current_background.get("purpose") or "unknown"
    return {
        "question_id": question_id,
        "client_request_id": body.client_request_id,
        "symbol": symbol,
        "purpose": purpose,
        "topic": parsed["topic"],
        "intent": parsed["intent"],
        "method": {
            "module": (parsed.get("method_choice") or {}).get("module"),
            "method_source": (parsed.get("method_choice") or {}).get("source"),
            # 03B-R3 S2：退出方式后端统一识别并随快照冻结（可证明继承）
            "exit_variant": (parsed.get("method_choice") or {}).get("exit_variant"),
            "entry_variant": None,
            "condition_definition": None, "horizon": None,
            "rule_refs": list((parsed.get("method_choice") or {}).get("rule_refs", [])),
            # 03B-R3 T1：窗口随原问题冻结（继承读取端依赖此字段；未选择=None）
            "window": window_frozen,
        },
        "evidence_query": parsed["topic"],
        "evidence_refs": evidence_refs,
        "data_refs": data_refs,
        "rule_refs": rule_refs,
        "gaps": [],
        "backtest_request_ids": [],
        "plan_id": None, "plan_version": None,
        "budget": budget,
        "holdings": None, "risk_preference": None,
        "user_background": current_background,
        "user_fact_updates": resolve_mod.user_fact_events(body.message),
        "user_fact_contract": "own-factual-v1",
    }


def _append_user_with_snapshot(conn, session_id: str, body, symbol: str | None,
                               review_dump: dict | None = None,
                               as_of: str | None = None,
                               window_sel: dict | None = None):
    """先落 user 消息并回填 discussion_v1 快照（question_id=消息自身 ID）。"""
    from lei_signal.plans.sessions import set_message_meta

    user_msg = append_message(conn, session_id, "user", body.message, True, {})
    snapshot = _discussion_snapshot(
        conn, body, symbol, question_id=user_msg.message_id,
        review_dump=review_dump, as_of=as_of, session_id=session_id,
        window_sel=window_sel)
    set_message_meta(conn, user_msg.message_id, {"discussion_v1": snapshot})
    return user_msg


def _append_user_for_claim(conn, outcome, body, symbol: str | None,
                           review_dump: dict | None, as_of: str | None,
                           window_sel: dict | None = None):
    """并发首撞收口（契约1）：写事务内核对领号归属——question_id 仍为 0 的
    赢家落 user 消息并回填问题号；已被别人占号（并发双发）的输家不重复落
    消息，直接拿赢家的原问题出口。返回 ("appended", user_msg, None) 或
    ("duplicate", None, replay_payload)。无编号请求走原路无条件落消息。"""
    import json as _json
    from datetime import UTC as _UTC, datetime as _dt

    from lei_signal.copilot.chat_identity import build_replay
    from lei_signal.plans.sessions import AgentMessage

    if not outcome.claim_cid:
        user_msg = _append_user_with_snapshot(
            conn, outcome.session_id, body, symbol,
            review_dump=review_dump, as_of=as_of, window_sel=window_sel)
        return "appended", user_msg, None
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute(
            "SELECT question_id FROM agent_chat_requests WHERE client_request_id = ?",
            (outcome.claim_cid,)).fetchone()
        if row is not None and int(row["question_id"]) != 0:
            conn.rollback()
            return "duplicate", None, build_replay(conn, outcome.claim_cid)
        now = _dt.now(_UTC).isoformat(timespec="seconds")
        cur = conn.execute(
            "INSERT INTO agent_messages (session_id, role, content, grounded, "
            "meta_json, created_at) VALUES (?, 'user', ?, 1, '', ?)",
            (outcome.session_id, body.message, now))
        message_id = int(cur.lastrowid or 0)
        snapshot = _discussion_snapshot(
            conn, body, symbol, question_id=message_id,
            review_dump=review_dump, as_of=as_of,
            session_id=outcome.session_id, window_sel=window_sel)
        conn.execute(
            "UPDATE agent_messages SET meta_json = ? WHERE message_id = ?",
            (_json.dumps({"discussion_v1": snapshot}, ensure_ascii=False), message_id))
        conn.execute(
            "UPDATE agent_sessions SET last_active_at = ? WHERE session_id = ?",
            (now, outcome.session_id))
        conn.execute(
            "UPDATE agent_chat_requests SET question_id = ? "
            "WHERE client_request_id = ? AND question_id = 0",
            (message_id, outcome.claim_cid))
        conn.commit()
    except Exception:  # noqa: BLE001
        conn.rollback()
        raise
    user_msg = AgentMessage(message_id, outcome.session_id, "user", body.message,
                            True, "", now)
    return "appended", user_msg, None


def _append_answer(conn, *, session_id: str, question_id: int | None,
                   content: str, grounded: bool, meta: dict,
                   kind: str = "", source_request_id: str = "",
                   claim_cid: str | None = None,
                   incomplete: bool = False):
    """回答落库（03B-R3 S4）：question_id/kind/来源请求写入**精确列**；带
    claim_cid 时回答插入与 claim 的状态绑定**同一事务**——不会出现
    「回答已写、绑定丢失」或「绑定指向他人回答」的窗口。

    ``incomplete=True``（主控复核 2026-09-15 固定补修二）：本次回答以未完成
    收场（流中断/未正常收尾/截断）——部分原文照常落库保留，但 claim 记为
    ``incomplete`` 而非 answered，同编号重试会重新生成而非回放半截话。
    调用方须先把 ``answer_incomplete`` 写入 meta。"""
    import json as _json
    from datetime import UTC as _UTC, datetime as _dt

    conn.execute("BEGIN IMMEDIATE")
    try:
        now = _dt.now(_UTC).isoformat(timespec="seconds")
        cur = conn.execute(
            "INSERT INTO agent_messages (session_id, role, content, grounded, "
            "meta_json, created_at, question_id, message_kind, source_request_id) "
            "VALUES (?, 'assistant', ?, ?, ?, ?, ?, ?, ?)",
            (session_id, content, int(grounded),
             _json.dumps(meta, ensure_ascii=False), now, question_id, kind,
             source_request_id))
        message_id = int(cur.lastrowid or 0)
        if claim_cid:
            from lei_signal.copilot.chat_identity import (
                mark_answered, mark_incomplete,
            )

            if incomplete:
                mark_incomplete(conn, claim_cid, message_id)
            else:
                mark_answered(conn, claim_cid, message_id)
        conn.execute(
            "UPDATE agent_sessions SET last_active_at = ? WHERE session_id = ?",
            (now, session_id))
        conn.commit()
    except Exception:  # noqa: BLE001
        conn.rollback()
        raise
    from lei_signal.plans.sessions import AgentMessage

    return AgentMessage(message_id, session_id, "assistant", content, grounded,
                        _json.dumps(meta, ensure_ascii=False), now)


def _server_plan_artifact(conn, session_id: str, question_id: int,
                          symbol: str | None, review_dump: dict | None,
                          message: str = "") -> dict:
    """03B-R3 S5：**服务端**计划产物——从真实 suggested_plan（系统已算出
    的值）+ 用户本条消息**明确给出**的合法字段 + 本问题的冻结依据生成
    结构化待补草稿；五项预案与缺失字段如实待补。字段来源逐项记录；
    **不从**用户预算或普通聊天数字猜结构失效价；模型只解释，不成为产物来源。"""
    from datetime import UTC as _UTC, datetime as _dt

    from lei_signal.copilot import resolve as resolve_mod
    from lei_signal.data_provenance import ruleset_ref

    sp = (review_dump or {}).get("suggested_plan") or {}
    mc = resolve_mod.parse_request(message).get("method_choice") or {}
    # 本问题的冻结依据直接取自该问题消息的 discussion_v1 快照（已随提问冻结）
    evidence_refs: list = []
    rule_refs: list = []
    try:
        row = conn.execute(
            "SELECT meta_json FROM agent_messages WHERE message_id = ?",
            (question_id,)).fetchone()
        snap = ((json.loads(row[0] or "{}") or {}).get("discussion_v1") or {}) \
            if row else {}
        evidence_refs = snap.get("evidence_refs") or []
        rule_refs = snap.get("rule_refs") or []
    except Exception:  # noqa: BLE001  快照缺席如实标注
        evidence_refs = []

    def _field(value, source: str, note_cn: str = "") -> dict:
        return {"value": value, "source": source, "note_cn": note_cn}

    def _sp(name: str) -> tuple[object, str]:
        v = sp.get(name)
        return (v, "suggested_plan") if v is not None else \
            (None, "pending（待用户补）")

    module_v, module_s = _sp("module")
    if module_v is None and mc.get("module"):
        module_v, module_s = mc["module"], "message（用户本条消息明确给出）"
    dir_v, dir_s = _sp("direction")
    if dir_v is None and mc.get("direction"):
        dir_v, dir_s = mc["direction"], "message（用户本条消息明确给出）"
    if dir_v is None and (module_v is not None):
        dir_v = "long"
        dir_s = "module_default（A/B/C 均为多头打法；默认多头方向）"
    fields = {
        "module": _field(module_v, module_s),
        "direction": _field(dir_v, dir_s),
        # T3：所有字段一律 {value, source, note_cn}——缺值也保持同结构
        # （此前这两项直接返回二元组，前端按 .value 读取会拿到空值）
        "entry_rule_id": _field(*_sp("entry_rule_id")),
        "entry_trigger_cn": _field(*_sp("entry_trigger_cn")),
        "invalidation_price": _field(*_sp("invalidation_price"),
                                     note_cn="结构失效价只来自系统建议或用户"
                                             "明确给出；不从预算/聊天数字猜"),
        "target_b_price": _field(*_sp("target_b_price")),
        # 五项预案必须人写（规格 §13）：系统建议不含 → 一律待补
        "thesis_cn": _field(None, "pending（五项预案必须由人写）"),
        "invalidation_criteria_cn": _field(None, "pending（五项预案必须由人写）"),
        "drawdown_playbook_cn": _field(None, "pending（五项预案必须由人写）"),
        "take_profit_plan_cn": _field(None, "pending（五项预案必须由人写）"),
        "stop_plan_cn": _field(None, "pending（五项预案必须由人写）"),
    }
    return {
        "kind": "server_plan_draft_v1",
        "artifact_id": f"spa_{question_id}",
        "question_id": question_id,
        "session_id": session_id,
        "symbol": symbol,
        "fields": fields,
        "ruleset_ref": ruleset_ref().to_dict(),
        "evidence_refs": evidence_refs,
        "rule_refs": rule_refs,
        "created_at": _dt.now(_UTC).isoformat(timespec="seconds"),
        "note_cn": "服务端产物：模型不参与字段构造；待补字段确认时由 04B 拒绝",
    }


#: 连续讨论一轮（2026-09-16）：「板块 → 对应ETF/产品」追问的确定性识别。
#: 系统目录没有可核实的板块→产品跟踪关系资料，这类问题的诚实答案是完全
#: 确定的，不走模型（防止凭名称猜跟踪关系或擅自选定产品）。
_SECTOR_PRODUCT_RE = re.compile(r"ETF|基金|产品|可以买的|能买的")
_SECTOR_RELATION_RE = re.compile(
    r"对应|跟踪|相关|哪些|哪个|有没有|关联|挂钩|可以买|能买")

#: 「和刚才相比有什么变化」类资料新旧比较追问（案例8）——C2 窄匹配：
#: 必须锚定「与此前资料相比」或裸问资料/数据/状态更新；方法（止损/止盈/
#: 胜率/回测/模块/退出）、资金（金额/预算/仓位/数字+单位）、基本面消息类
#: 的「变化」问题一律放行给原有链路，不靠堆关键词代替边界判定。
_COMPARISON_ANCHOR_RE = re.compile(
    r"(和|与)(刚才|之前|此前|上次)(相比)?|"
    r"^有(什么|啥)(新)?变化[吗呢？?]{0,2}$|"
    r"(资料|数据|状态).{0,6}(更新|变化)|"
    r"^(资料|数据)?(有)?更新了吗[？?]{0,1}$")
_COMPARISON_EXCLUDE_RE = re.compile(
    r"止损|止盈|胜率|回测|补测|复跑|方法|模块|退出|打法|"
    r"金额|预算|仓位|股|元|块|万|千|美元|港币|欧元|成本|"
    r"基本面|消息|新闻|公告|财报|ATR|atr")


def _sector_product_relation_reply(ctx_payload: dict, message: str) -> str | None:
    """板块语境下问「对应的ETF/有哪些产品」→ 确定性诚实回答（案例2）。

    系统目录不存在板块→ETF 的可核实跟踪关系（已核实：目录只有板块与产品
    各自的名称，没有跟踪/对应关系数据）。如实说明，不仅凭名称猜、不自动选一个。
    """
    if ctx_payload.get("context_kind") != "sector":
        return None
    if not (_SECTOR_PRODUCT_RE.search(message) and _SECTOR_RELATION_RE.search(message)):
        return None
    name = ctx_payload.get("display_name") or "该"
    as_of = ctx_payload.get("as_of") or "未知"
    return (
        f"你问的「对应的ETF」：系统目录里没有可核实的「{name}板块 → ETF/产品」"
        "跟踪关系资料——我不会仅凭名称相近猜哪个产品跟踪这个板块，也不替你选定"
        "某一个产品。\n"
        "想继续的话：直接说具体产品的名称或代码，我按那个产品自己的系统资料来讲"
        f"（不会把板块的整体统计当成某个产品的成绩）。{name}板块本身的观察仍按"
        f"截至 {as_of} 的板块资料。")


def _user_background(history_rows: list, symbol: str | None) -> dict:
    """同会话、同对象内用户**自己声明过**的事实背景（C3 + 收口二精确归属）。

    归属用现成的精确绑定：用户消息的 ``message_id`` = assistant 回答的
    ``question_id``。只收集「绑定对象 == 当前 symbol」的声明；
    **无精确归属（无 message_id / 尚无绑定回答）的旧消息标未知、不可继承，
    不得跨过下一条 user 去猜归属**；中断后重试/同一问题的多个回答共享同一
    question_id，天然按同一问题处理；symbol 未知（全局）不收集任何背景。
    明确撤销（没持有/已卖出/没预算）即时清除；沉默不影响。
    这是**讨论背景**：不是成交记录、不是写库授权、不是新的交易许可。
    返回 {holding, budget, purpose, stated}；没有任何已知事实时返回 {}。
    """
    from lei_signal.copilot import resolve as resolve_mod  # noqa: PLC0415

    if not history_rows or not symbol:
        return {}
    # 问题号 → 回答绑定对象集合；多回答冲突时不猜采用哪一个
    bound_by_qid: dict[int, set[str]] = {}
    for row in history_rows:
        if row.role != "assistant":
            continue
        qid = getattr(row, "question_id", None)
        if not qid:
            continue
        try:
            meta = json.loads(row.meta_json or "{}")
        except (TypeError, ValueError):
            continue
        sym = meta.get("resolved_symbol")
        if isinstance(sym, str) and sym:
            bound_by_qid.setdefault(int(qid), set()).add(sym)
    bg: dict = {"holding": False, "budget": None, "purpose": None}
    for row in history_rows:
        if row.role != "user":
            continue
        mid = getattr(row, "message_id", None)
        if not mid:
            continue  # 无身份：不可继承
        bound = bound_by_qid.get(int(mid))
        if bound is None:
            continue  # 无精确归属（旧消息/尚无绑定回答）：标未知，不猜
        if bound != {symbol}:
            continue  # 别的对象的声明不串用
        previous_budget = bg.get("budget")
        bg = resolve_mod.apply_user_facts(bg, row.content or "")
        if bg.get("budget") and bg["budget"] != previous_budget:
            bg["budget"] = {**bg["budget"], "inherited_from_question": int(mid)}
    return {k: v for k, v in bg.items() if v}


def _previous_turn_facts(history_rows: list) -> list[dict]:
    """会话历史中 assistant 轮的可比事实（对象/资料日期/结论），新→旧排序。"""
    facts: list[dict] = []
    for m in reversed(history_rows):
        if m.role != "assistant":
            continue
        try:
            meta = json.loads(m.meta_json or "{}")
        except (TypeError, ValueError):
            continue
        resolved = meta.get("resolved_symbol")
        card = meta.get("evidence_card") or {}
        f = card.get("facts") or {}
        facts.append({
            "symbol": resolved if isinstance(resolved, str) else None,
            "display_name": f.get("display_name"),
            "as_of": f.get("as_of"),
            "verdict_cn": f.get("verdict_cn"),
            "candidate_n": f.get("buy_point_candidate_n"),
        })
    return facts


def _comparison_reply(history_rows: list, symbol: str | None,
                      ctx_payload: dict, message: str) -> str | None:
    """「和刚才相比有什么变化」→ 确定性比较回答（案例8，C1 口径）。

    比较的是同对象、同口径的**已冻结事实**（历史证据卡与当前材料的
    资料日期/系统结论/买点候选数），不是只比日期：
    - 已比较字段全部相同 → 只说「这些已比较字段相同」；系统没有每份资料
      的完整版本快照，不断言所有内容都没更新（C1）；
    - 同一数据日但内容字段不同 → 如实说同一数据日内的资料内容有变化
      （盘中/当日修订允许存在），不得说成没有变化；
    - 日期倒退（当前比刚才更旧）→ 明确是退回较旧资料，不是「更新」；
    - 日期或字段缺失 → 该字段诚实不可比，不猜。
    全部直读已落库事实，不引入第二套行情计算。
    """
    if not _COMPARISON_ANCHOR_RE.search(message):
        return None
    if _COMPARISON_EXCLUDE_RE.search(message):
        return None
    prev = _previous_turn_facts(history_rows)
    cur_name = ctx_payload.get("display_name") or symbol or "当前对象"
    cur_as_of = ctx_payload.get("as_of")
    cur_card = ctx_payload.get("evidence_card") or {}
    cur_facts = cur_card.get("facts") or {}
    cur_verdict = cur_facts.get("verdict_cn")
    cur_n = cur_facts.get("buy_point_candidate_n")
    if not prev:
        return ("这是本会话里我能看到的第一份资料，没有可比较的之前状态。"
                f"当前 {cur_name} 的资料截至 {cur_as_of or '未知'}。")
    last = prev[0]
    last_name = last.get("display_name") or last.get("symbol") or "上一个对象"
    if symbol and last.get("symbol") and last["symbol"] != symbol:
        return (
            f"刚才聊的是 {last_name}（资料截至 {last.get('as_of') or '未知'}），"
            f"现在这份是 {cur_name}（资料截至 {cur_as_of or '未知'}）——两个对象的"
            "资料不是同一份，不能互相比新旧。"
            + (f"{cur_name} 当前的系统结论：{cur_verdict}。" if cur_verdict else ""))
    # 只与同对象的已冻结事实比（C1）：全局轮/其他对象轮不冒充同一份资料。
    same_object = [p for p in prev if p.get("symbol") and p["symbol"] == symbol] \
        if symbol else [p for p in prev if not p.get("symbol")]
    if not same_object:
        return (
            f"刚才聊的不是 {cur_name}，这个对象在本会话里还没有可比较的之前"
            f"资料。当前 {cur_name} 的资料截至 {cur_as_of or '未知'}。"
            + (f"系统结论：{cur_verdict}。" if cur_verdict else ""))
    last_same = same_object[0]
    prev_as_of = last_same.get("as_of")
    prev_verdict = last_same.get("verdict_cn")
    prev_n = last_same.get("candidate_n")

    # 日期倒退：退回较旧资料，绝不能写成「更新」（C1 反例）。
    if prev_as_of and cur_as_of and cur_as_of < prev_as_of:
        return (
            f"注意：现在这份资料的日期（{cur_as_of}）比刚才那份（{prev_as_of}）"
            "更旧——你看到的是退回较旧的资料，不是新数据；要谈变化请以较新"
            "日期的资料为准。")

    # 逐字段比较（双方都有值才可比；缺失的字段诚实列入不可比）。
    field_rows = [
        ("系统结论", prev_verdict, cur_verdict),
        ("买点候选数", prev_n, cur_n),
    ]
    changed: list[str] = []
    unverifiable: list[str] = []
    for label, old, new in field_rows:
        if old is None or new is None:
            unverifiable.append(label)
        elif old != new:
            changed.append(f"{label}从「{old}」变成「{new}」")
    dates_known = bool(prev_as_of and cur_as_of)
    if changed:
        date_bit = (
            f"资料日期都是 {cur_as_of}（同一数据日内的资料内容变化）"
            if dates_known and prev_as_of == cur_as_of else
            f"资料日期从 {prev_as_of} 到 {cur_as_of}"
            if dates_known else "资料日期无法完整核实")
        tail = (f"；另：{'、'.join(unverifiable)}无法核实对比" if unverifiable else "")
        return f"有变化：{date_bit}。" + "；".join(changed) + f"。{tail}"
    if unverifiable and len(unverifiable) == len(field_rows):
        # 一个可比字段都没有：如实说无法对比，不列空清单（C1）。
        return (
            f"刚才的旧记录里缺少可对比的字段（{'、'.join(unverifiable)}都没有"
            "留档），无法核实对比——不能断言有没有变化。"
            + (f"当前系统结论：{cur_verdict}。" if cur_verdict else ""))
    if unverifiable:
        same_bit = "已比较的字段（" + "、".join(
            label for label, old, new in field_rows
            if old is not None and new is not None) + "）相同"
        date_bit = (f"，资料日期同为 {cur_as_of}" if dates_known and prev_as_of == cur_as_of
                    else f"，资料日期从 {prev_as_of} 到 {cur_as_of}" if dates_known else "")
        return (
            f"{same_bit}{date_bit}；但{'、'.join(unverifiable)}在旧记录里缺字段，"
            "无法核实对比——只能保证已比较字段相同，不能断言有没有变化。")
    # 已比较字段全部相同：只说已比较字段相同，不断言系统没变化（C1）。
    date_bit = (f"，资料日期同为 {cur_as_of}" if dates_known and prev_as_of == cur_as_of
                else f"，资料日期从 {prev_as_of} 到 {cur_as_of}" if dates_known
                else "，资料日期无法完整核实")
    return (
        f"和刚才相比，已比较的字段（系统结论、买点候选数）相同{date_bit}。"
        "系统没有保存每份资料的完整版本快照，只能保证这些已比较字段相同，"
        "不能断言所有细节都没更新。"
        + (f"当前系统结论：{cur_verdict}。" if cur_verdict else ""))


def _deterministic_reply(history_rows: list, symbol: str | None,
                         ctx_payload: dict, message: str) -> str | None:
    """答案完全由确定性事实决定的问题类型，直接系统作答（不走模型）。

    连续讨论一轮（2026-09-16）：板块→产品关系追问（案例2）、与刚才比较的
    变化追问（案例8）。这些回答的「诚实版本」不依赖表达发挥，交给模型反而
    有编造风险；产出按普通回答落库（grounded=True，依据系统数据）。
    """
    if ctx_payload.get("context_kind") == "factor_readonly":
        return ctx_payload["factor_readonly"]["reply"]
    if not message:
        return None
    rel = _sector_product_relation_reply(ctx_payload, message)
    if rel is not None:
        return rel
    return _comparison_reply(history_rows, symbol, ctx_payload, message)


def _degraded_reply(symbol: str, ctx_payload: dict) -> str:
    """AI 讲解不可用/校验失败时的系统直出（可靠性一期 2026-09-14 改写）。

    表达口径（任务书 §5；改前/改后对照见实验报告 E 节）：第一句直接回答
    这次问题（大白话），颜色/阶段等系统标签放后文作细节；数据日期不是
    今天时同强度说明「不能直接代表今天」（只读日期事实，不发明按天数
    折算的新鲜度规则）；依据一句话说清「能否支持本次判断」；下一步 ≤3 条
    且贴问题，优先给可观察的既有条件。数值全部直读 ctx_payload，
    不新增判定逻辑。
    """
    today = datetime.now().astimezone().strftime("%Y-%m-%d")
    if ctx_payload.get("context_kind") == "sector":
        return (f"{ctx_payload['display_name']}板块（{symbol}）："
                f"资料日期 {ctx_payload.get('as_of') or '未知'}，"
                f"阶段为{ctx_payload['assessment']['stage_cn']}。"
                "AI讲解暂不可用，请核对下方板块资料；这不是ETF买卖建议。")
    if ctx_payload.get("context_kind") == "global":
        # global 会话无标的技术材料：只给大盘概况与环境信息，不硬凑标的内容
        lines = ["AI 讲解暂时不可用，以下是系统直接给出的市场概况。"]
        if ctx_payload.get("breadth_cn"):
            lines.append(f"市场宽度：{ctx_payload['breadth_cn']}")
        if ctx_payload.get("margin_cn"):
            lines.append(f"融资环境：{ctx_payload['margin_cn']}")
        lines.append(
            "接下来可以：说一个标的名称或代码进入具体讨论，或稍后再试 AI 讲解。"
        )
        return "\n".join(lines)
    a = ctx_payload.get("assessment", {})
    display = ctx_payload.get("display_name", symbol)
    as_of = ctx_payload.get("as_of", "-")
    review = ctx_payload.get("buy_point_review") or {}
    candidates = review.get("candidates") or []
    trad = review.get("tradability") or {}
    blocked = bool(trad) and not trad.get("tradable") and bool(
        trad.get("blocking_reasons"))

    # 连续讨论一轮（2026-09-16）：用户声明的立场与问题主题决定第一句的
    # 讲法——已持有按持仓管理讲（案例6），资金问题先正面回答再给纪律与
    # 最关键缺失信息（案例7）；都不改变判定层结论，只换解释口径。
    stance = (ctx_payload.get("discussion_stance") or {}).get("kind")
    q_topic = ctx_payload.get("question_topic")
    # 本条明确是资金问题时资金分支优先（C3：持仓者问钱，答钱不按持仓模板）；
    # 否则持仓语境优先于通用首买模板。
    if stance == "holding" and q_topic != "money":
        lines = [
            f"{display}（{symbol}）：你说已经持有了——这次就从持仓管理角度讲，"
            "不按首次买入说。",
        ]
        if blocked:
            lines.append(
                f"系统当前状态：{'、'.join(trad['blocking_reasons'])}——"
                "这是环境层面的提醒，不是让你立刻动作。")
        elif candidates:
            c0 = candidates[0]
            lines.append(
                f"系统当前有 {len(candidates)} 个买点候选在观察中，最近的"
                f"「{c0.get('scenario_cn', '')}」（{c0.get('state_cn', '')}）"
                "——持仓语境下它们只是参照，不是新的入场引导。")
        else:
            lines.append("系统当前没有新的买点候选；持仓期间重点看失效位与观察条件。")
        known_budget = ctx_payload.get("user_budget") or {}
        known_amt = known_budget.get("amount")
        if isinstance(known_amt, (int, float)):
            lines.append(
                f"你之前说过可投入的资金是 {known_amt:g} 元（这是讨论背景，"
                "不是成交记录）；成本信息这段系统直出未核实（系统目前没有"
                "成本提取能力），不编造。具体的退出位以你自己确认过的计划为准。"
                "这里没有记录任何成交。")
        else:
            lines.append(
                "成本与资金信息这段系统直出未核实（系统目前没有成本提取能力），"
                "不编造；这段讨论里也没有你的成交信息。具体的退出位以你自己"
                "确认过的计划为准。这里没有记录任何成交。")
    elif q_topic == "money":
        budget = ctx_payload.get("user_budget") or {}
        amt = budget.get("amount")
        amt_txt = f"{amt:g} 元" if isinstance(amt, (int, float)) else "这笔钱"
        if blocked:
            verdict_line = (
                f"先回答能不能买：按系统数据，{display}（{symbol}）现在按规则"
                f"不适合开新仓——{'、'.join(trad['blocking_reasons'])}。")
        elif candidates:
            c0 = candidates[0]
            verdict_line = (
                f"先回答能不能买：{display}（{symbol}）现在有 {len(candidates)} 个"
                f"系统定义的买点候选，最近的「{c0.get('scenario_cn', '')}」状态"
                f"「{c0.get('state_cn', '')}」——还不等于可以直接行动。")
        else:
            verdict_line = (
                f"先回答能不能买：按系统数据，{display}（{symbol}）现在没有"
                "系统定义的买点候选。")
        # C3：用途已知（本条或同会话同对象背景）就不再重复追问，
        # 直接按已知用途给纪律边界；未知才问这最关键的一项。
        known_purpose = ctx_payload.get("user_purpose")
        if known_purpose == "spare_cash":
            purpose_line = ("你说过这是一笔已有的闲钱：按闲钱的用法，分几批、"
                            "每批多少由你决定——不再追问用途。")
        elif known_purpose == "income_dca":
            purpose_line = ("你说过这是持续投入的新收入：按定投式的用法，"
                            "节奏和金额由你决定——不再追问用途。")
        else:
            purpose_line = ("还差一项关键信息：这笔钱是持续投入的新收入，"
                            "还是已有的闲钱？这影响怎么分批，先确认这一项再细聊。")
        lines = [
            verdict_line,
            f"{amt_txt}怎么安排由你决定；系统纪律是盈亏比不足 3 的机会放弃"
            "（研究代理口径），仓位档位只是参考。",
            purpose_line,
            "现在只是讨论——没有确认任何计划，也不会替你下单。",
        ]
    # ① 先回答这次问题：第一句就是大白话结论（只重组既有判定字段，
    # 不做新判定；候选状态/价位照抄，不加解释性定语）。
    elif candidates:
        c0 = candidates[0]
        lines = [
            f"{display}（{symbol}）：按系统数据，目前有 {len(candidates)} 个"
            f"系统定义的买点候选；最接近的一个是「{c0.get('scenario_cn', '')}」，"
            f"状态「{c0.get('state_cn', '')}」，关键价位 "
            f"{c0.get('key_price') or '系统未给出'}。",
        ]
    elif blocked:
        lines = [
            f"{display}（{symbol}）：按系统数据，现在不构成可执行的入场计划"
            "——按规则本轮不适合讨论开新仓。",
            f"系统给出的原因是：{'、'.join(trad['blocking_reasons'])}。",
        ]
    else:
        lines = [
            f"{display}（{symbol}）：按系统数据，现在没有系统定义的买点候选，"
            "还整理不成可执行的入场计划。",
        ]

    # ② 数据日期与讲解状态：AI 不可用必须可见；日期不是今天就同强度说明
    # 「不能直接代表今天」（只读日期事实，不发明按天数折算的新鲜度规则）。
    if as_of and as_of != "-" and as_of != today:
        lines.append(
            f"注意：AI 讲解暂时不可用。以下是系统按 {as_of} 数据直接给出的"
            f"事实——今天是 {today}，这是过去的数据，不能直接代表今天；"
            "先用最新数据核实再谈下一步。"
        )
    else:
        # 连续讨论一轮（日期口径，主控复验 §3）：当天数据不说「今日收盘」——
        # 没有完成交易时段的来源证明，只说截至该日的最新记录，不凭更新时间猜。
        lines.append(
            f"截至 {as_of} 的最新记录（系统没有该日是否已收盘的来源证明，"
            "不凭更新时间猜）。AI 讲解暂时不可用，以下是系统直接给出的数据事实。"
        )

    # 系统标签（颜色/阶段/风险）是细节，不再当第一句。
    lines.append(
        f"系统状态：{a.get('color_cn', '状态未知')} / {a.get('stage_cn', '-')}"
        f" / 风险关注 {a.get('risk_state_cn', '-')}。"
    )

    # ③ 机会与风险：有候选列候选（阻断原因已进第一句，不重复）。
    # 持仓语境不列入场向的「机会」行，避免把持仓管理答成首次买入。
    if candidates and stance != "holding":
        for c in candidates[:2]:
            lines.append(
                f"机会：{c.get('scenario_cn', '')}目前[{c.get('state_cn', '')}]，"
                f"关键价位 {c.get('key_price') or '系统未给出'}。"
            )
    vp = ctx_payload.get("volume_profile") or {}
    if vp.get("poc"):
        lines.append(
            f"参考：成交最密集的价位在 {vp['poc']}（筹码分布代理，"
            "不是真实持仓成本）。"
        )

    # ④ 历史依据够不够：首层一句话说清能否支持本次判断，明细留在依据卡。
    card = ctx_payload.get("evidence_card") or {}
    hs = card.get("history_and_scope") or {}
    matched = [r for r in (hs.get("matched_runs") or []) if isinstance(r, dict)]
    exact_n = sum(1 for r in matched if r.get("supports_question"))
    if exact_n:
        lines.append(
            f"历史依据：有 {exact_n} 次与本问题方法完全一致的补测结果，"
            "可以支撑这次判断（数值见下方依据卡）。"
        )
    elif matched:
        lines.append(
            "历史依据：现在不能给这次判断附上可靠的胜率——本标的有历史补测，"
            "但没有与这次问题完全一致的方法组合，旧结果只作参考（见下方依据卡）。"
        )
    else:
        we = hs.get("winrate_evidence") or {}
        if we.get("compatibility") == "exact":
            lines.append("历史依据：本标的有同方法的历史胜率表，适用于这次问题。")
        else:
            lines.append(
                "历史依据：现在不能给这次判断附上可靠的胜率——现有记录不足以"
                "核实是否是同一种做法（明细见下方依据卡）。"
            )

    # ⑤ 接下来可以做什么：≤3 条、贴问题；无候选时不再让用户先选打法。
    pending = [str(x) for x in (card.get("pending_conditions") or []) if x]
    if pending:
        lines.append(
            "接下来先观察这些条件，哪条变化了再回来讨论："
            + "；".join(pending[:3]) + "。"
        )
    elif candidates:
        lines.append(
            "接下来可以：在下方动作里选一项继续（查看依据详情 / 准备补测 / "
            "讨论进出计划）。"
        )
    else:
        lines.append(
            "接下来可以先核实这个标的的最新数据；想继续讨论的话，说一个你"
            "关心的条件或价位，系统有对应事实时再展开。"
        )
    return "\n".join(lines)


def _build_next_steps(ctx_payload: dict, symbol: str | None) -> list[dict]:
    """UX 第一期（2026-09-13）：回答的下一步动作建议（纯展示层转换）。

    从既有事实（买点审阅的观察条件、证据卡的补测比较结果、买点候选）推导
    最多 3 个动作；不产生新判定、不造数字。draft_cn 是可直接放进输入框的
    完整中文问题，**带标的代码**——用户切到别的标的后点旧按钮也不会串对象。
    历史恢复与即时回答共用同一份（存 meta.next_steps）。
    """
    if ctx_payload.get("context_kind") == "factor_readonly":
        return []  # No plan/backtest actions for a research lookup or proposal.
    if not symbol:
        return []
    if ctx_payload.get("context_kind") == "sector":
        return [{"kind": "expand_evidence", "label_cn": "查看板块依据"}]
    steps: list[dict] = [
        {"kind": "expand_evidence", "label_cn": "查看依据详情"},
    ]
    review = ctx_payload.get("buy_point_review") or {}
    watch = [
        w.get("text_cn") for w in (review.get("watch_conditions") or [])
        if isinstance(w, dict) and w.get("text_cn")
    ]
    card = ctx_payload.get("evidence_card") or {}
    matched = [
        r for r in ((card.get("history_and_scope") or {}).get("matched_runs") or [])
        if isinstance(r, dict)
    ]
    has_exact = any(r.get("supports_question") for r in matched)
    candidates = review.get("candidates") or []
    if watch:
        steps.append({
            "kind": "ask_conditions",
            "label_cn": "看看还需满足什么条件",
            "draft_cn": (
                f"关于 {symbol}，现在距离系统定义的买点还缺哪些条件？"
                "分别要到什么价位或什么状态才算满足？"
            ),
        })
    if not has_exact:
        steps.append({
            "kind": "prepare_backtest",
            "label_cn": "准备补测",
            "note_cn": "这个标的还没有与本次问题完全匹配的历史测试结果",
        })
    if candidates and len(steps) < 3:
        steps.append({
            "kind": "discuss_plan",
            "label_cn": "讨论进出计划",
            "draft_cn": (
                f"关于 {symbol} 当前的买点，把入场条件、认错位和目标位整理成"
                "计划草案讨论一下（先讨论，不直接确认计划）。"
            ),
        })
    return steps[:3]


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


#: 影响结果的过滤参数及其**引擎默认值**（与 BacktestParams 默认一致；
#: 比较配置逐项记录 source=engine_default，缺失不默认相同）
_ENGINE_DEFAULT_FILTERS: dict[str, object] = {
    "volume_confirm": False, "volume_confirm_window": 5,
    "profile_filter": "none", "volume_filter": "none",
    "gap_target": False, "gap_momentum": False, "gap_momentum_lookback": 10,
    "bias_filter": None, "accel_filter": None, "accel_lookback": 60,
    "stop_atr_buffer": None, "min_stop_distance": None,
    "shrink_recent": None, "shrink_prior": None,
    "volume_filter_vr_max": None, "limit_guard": True,
}
_COMPARABLE_FILTER_FIELDS = tuple(_ENGINE_DEFAULT_FILTERS)


def _question_comparison_config(conn, session_id: str | None, message: str,
                                symbol: str | None,
                                window_sel: dict | None = None) -> dict:
    """03B-R3 S2：本问题的**完整方法比较配置**——来源只有三种并逐项记录：
    用户本条消息明确选择 > 同会话可证明的继承（历史快照的明确选择）>
    明示的既有引擎默认值。缺失不能默认为相同；窗口未指定=该维度尚未核实。"""
    from lei_signal.copilot import resolve as resolve_mod
    from lei_signal.backtest.service import _ruleset_content_hash

    parsed = resolve_mod.parse_request(message)
    mc = parsed.get("method_choice") or {}

    inherited: dict = {}
    if session_id:
        rows = conn.execute(
            "SELECT message_id, meta_json FROM agent_messages "
            "WHERE session_id = ? AND role = 'user' "
            "AND meta_json LIKE '%discussion_v1%' ORDER BY message_id DESC LIMIT 20",
            (session_id,)).fetchall()
        for r in rows:
            try:
                snap = (json.loads(r["meta_json"] or "{}") or {}).get("discussion_v1") or {}
            except json.JSONDecodeError:
                continue
            method = snap.get("method") or {}
            if method.get("module") and "module" not in inherited:
                inherited["module"] = {"value": method["module"],
                                       "source": f"inherited:question:{r['message_id']}"}
            if method.get("exit_variant") and "exit_variant" not in inherited:
                inherited["exit_variant"] = {
                    "value": method["exit_variant"],
                    "source": f"inherited:question:{r['message_id']}"}
            # 窗口继承已统一由 _resolve_window_for_question 处理（与冻结共用
            # 同一份选择），此处不再独立读取快照窗口，避免「显示」与「存档」
            # 来源不同（T1 单入口契约）。

    def _field(name: str, explicit, default):
        if explicit:
            return {"value": explicit, "source": "message"}
        if inherited.get(name):
            return dict(inherited[name])
        return {"value": default, "source": "engine_default"}

    # —— 比较区间（T1）：来自一次性结构化选择 window_sel（冻结与比较共用同一
    # 份），本函数不再二次选运行/查最新结果（u2 并发一致性）——
    window: dict[str, Any] | None = None
    if window_sel and window_sel.get("start") and window_sel.get("end"):
        window = _window_projection(window_sel)
    elif window_sel is None:
        # 兜底（非标准调用路径）：退化为本次消息即时解析，不跨查询
        _wc = resolve_mod.parse_window_choice(message)
        if (_wc and _wc.get("kind") == "explicit_dates" and not _wc.get("invalid")
                and _wc.get("start") and _wc.get("end")):
            window = _window_projection({**_wc,
                      "source": "message（用户本条消息明确给出的区间）"})
    window_state = (window_sel or {}).get("state") or ("verified" if window else "unverified")

    return {
        "symbol": symbol,
        "module": _field("module", mc.get("module"), "A"),
        "exit_variant": _field("exit_variant", mc.get("exit_variant"),
                               "a6_1_costbasis"),
        "entry_variant": _field("entry_variant", mc.get("entry_variant"), None),
        "rr_min": {"value": 3.0, "source": "engine_default"},
        "fee_label": {"value": "standard", "source": "engine_default"},
        "ruleset_sha256": {"value": _ruleset_content_hash(),
                           "source": "current_active_ledger"},
        # 研究窗口/截止：来源可证明才填；未指定=该维度尚未核实，不默认相同
        "window": window,
        "window_state": window_state,
        "note_cn": "配置来源=message/inherited:question:N/adopted:run:ID/"
                   "engine_default；window 为 null 表示窗口维度尚未核实，"
                   "不默认与旧运行相同，也不进入「支持本问题」材料",
    }


def _compare_run_with_config(config: dict, row, result: dict | None,
                             current_rules_sha: str | None) -> dict:
    """单个旧运行与本问题配置的完整比较：字段完整且一致（含来源 run 与冻结
    输入自证）才 exact；有差异 → incompatible 并逐项列出；不可考 → unknown。
    用公共引用契约字段（compatibility），不自造第二套胜率口径。

    03B-R3 T2：比较分两步——第一步先完整核验「产物是否真属于本请求」
    （对象/运行/完整配置/输入指纹/规则摘要/实际数据区间），失败则直接
    unknown、不得进入「支持本问题」集合；第二步才比较用户所选模块/退出/窗口。
    正常完成、异常恢复、后续证据读取共用同一 `_validate_output_for_request`。"""
    from lei_signal.copilot import backtest_requests as br
    from lei_signal.data_provenance import (
        COMPAT_EXACT,
        COMPAT_INCOMPATIBLE,
        COMPAT_UNKNOWN,
    )

    entry: dict = {
        "request_id": row["request_id"], "run_id": row["run_id"],
        "symbol": row["symbol"], "module": row["method"],
        "exit_variant": row["exit_variant"],
        "entry_variant": row["entry_variant"],
        "data_cutoff": row["data_cutoff"],
        "ruleset_version": row["ruleset_version"],
        "completed_at": row["updated_at"],
        "differences_cn": [],
    }
    params = result.get("params") if isinstance(result, dict) else None
    diffs = entry["differences_cn"]
    # —— 第一步：产物属于本请求的完整核验（只读，不重跑引擎）——
    # 调用方先读字段也必须在任何 .get 之前做结构化检查（z3/z6）：结果顶层
    # 非对象、冻结引用坏 JSON/非列表，均作为该记录拒绝原因，不抛到外层毁整卡。
    try:
        refs = json.loads(row["input_refs_json"] or "[]")
    except (ValueError, TypeError):
        refs = None
    if not isinstance(refs, list):
        refs = None
    _reject = (br._validate_output_for_request(row, result, refs)
               if result is not None else "结果文件缺失")
    if _reject is not None:
        entry["input_verified"] = False
        entry["unverified_fields"] = ["输入归属"]
        entry["validation_reject"] = _reject
        # T4：拒绝原因进入前端实际消费字段 differences_cn（EvidenceCardView
        # 只渲染该字段），用户真实可见，不只在 JSON 里新增字段。
        if _reject:
            entry["differences_cn"].append(f"不采纳：{_reject}")
        entry["compatibility"] = COMPAT_UNKNOWN
        entry["module_matches_question"] = row["method"] == config["module"]["value"]
        entry["supports_question"] = False
        if result is not None:
            _ov = {}
            try:
                _ov = result["groups"]["True"]["总览"][0]
            except (KeyError, TypeError, IndexError, ValueError):
                _ov = {}
            entry["summary"] = {
                "trade_count": _ov.get("trade_count"),
                "win_rate": _ov.get("win_rate"),
                "expectancy_r": _ov.get("expectancy_r"),
                "profit_factor": _ov.get("profit_factor"),
                "zero_trades": not _ov.get("trade_count"),
            }
        return entry
    # T1：完整性用**结构化状态**表达，不靠差异文案里有没有"不可考"来判断——
    # unverified=该维度无法核实（→ unknown）；diffs 里的其余项=已证实的差异
    unverified: list[str] = []
    entry["unverified_fields"] = unverified

    # —— 来源与产物自证（S3 联动）：旧运行的输入是否真属于它 ——
    input_verified = False
    try:
        out_manifest = (result or {}).get("run_manifest")
        row_manifest = json.loads(row["run_manifest_json"]) \
            if row["run_manifest_json"] else None
        if out_manifest is not None and row_manifest is not None:
            input_verified = (str(out_manifest) == str(row_manifest))
            if not input_verified:
                diffs.append("运行产物清单与请求登记清单不符（输入归属不可证明）")
        elif not out_manifest:
            diffs.append("旧结果缺运行清单（run_manifest），实际输入不可考")
        else:
            # 产物有清单、请求侧登记缺失：同样无法证明归属（不能因文案缺省而放过）
            diffs.append("请求登记的运行清单缺失，输入归属不可证明")
    except (ValueError, TypeError):
        diffs.append("运行清单解析失败，实际输入不可考")
    if not input_verified:
        unverified.append("输入归属")
    entry["input_verified"] = input_verified

    # —— 逐项方法比较（缺失不能默认相同）——
    def _cmp(label: str, config_field: dict, run_value, *, verify_value=True,
             fmt=None) -> None:
        want = config_field.get("value")
        shown = (lambda x: str(x)) if fmt is None else fmt
        if run_value is None and config_field.get("source") != "engine_default":
            diffs.append(f"{label}在旧运行中缺失，无法核实是否一致")
            unverified.append(label)
            return
        if verify_value and str(run_value) != str(want):
            source = config_field.get("source")
            origin = {"message": "本轮明确选择"}.get(
                source, "会话继承的选择" if source and source.startswith("inherited")
                else "引擎默认值")
            diffs.append(f"{label}：旧运行为 {shown(run_value)}，本问题为 "
                         f"{shown(want)}（{origin}）——不借旧成绩")

    def _module_cn(v):
        return f"模块{v}" if v else "未指定"

    def _exit_cn(v):
        return {"a6_1_costbasis": "退出1（EMA20+抵扣价）",
                "a6_2_top_plus_keywave": "退出2（顶部构造+关键波动）",
                "a6_3_structure_stop": "退出3（初始止损）"}.get(str(v), str(v))

    _cmp("交易模块", config["module"], row["method"], fmt=_module_cn)
    _cmp("退出方式", config["exit_variant"], row["exit_variant"], fmt=_exit_cn)
    _cmp("入场版本", config["entry_variant"], params.get("entry_variant"))
    _cmp("费用档", config["fee_label"], params.get("fee_label"))
    _cmp("盈亏比门槛", config["rr_min"], params.get("rr_min"))
    for field in _COMPARABLE_FILTER_FIELDS:
        _cmp(f"过滤参数{field}",
             {"value": _ENGINE_DEFAULT_FILTERS[field], "source": "engine_default"},
             params.get(field), verify_value=True)
    # 规则内容：与当前账本比（不同账本不背书）；窗口：未指定=未核实
    if not params.get("ruleset_sha256"):
        diffs.append("旧结果缺规则内容摘要，无法核实规则是否与当前一致")
        unverified.append("规则摘要")
    elif current_rules_sha and params["ruleset_sha256"] != current_rules_sha:
        diffs.append("运行时的规则账本内容与当前不同（规则已更新，不背书）")
    run_range = (result or {}).get("data_range") or {}
    cfg_window = config.get("window")
    if cfg_window and cfg_window.get("start"):
        # 窗口已核实：服务端比较实际起止，不同区间不能互相替代
        if (str(run_range.get("start") or "") != str(cfg_window["start"])
                or str(run_range.get("end") or "") != str(cfg_window["end"])):
            diffs.append(
                f"比较区间：本问题为 {cfg_window['start']}~{cfg_window['end']}"
                f"（{cfg_window.get('source', '')}），旧运行实际为 "
                f"{run_range.get('start') or '未知'}~"
                f"{run_range.get('end') or '未知'}——不能用另一区间替代")
    else:
        entry["window_note_cn"] = (
            "本问题没有可证明的比较窗口；旧运行窗口见 data_cutoff="
            f"{row['data_cutoff']}、实际区间 "
            f"{run_range.get('start') or '未知'}~{run_range.get('end') or '未知'}，"
            "窗口维度尚未核实")
        diffs.append("比较区间尚未核实（没有可证明的窗口来源；旧运行自己的"
                     "数字只作描述参考，不进入支持本问题的材料）")
        unverified.append("比较区间")
    entry["run_window"] = {
        "data_cutoff": row["data_cutoff"],
        "data_range": run_range,
    }

    # 有任一维度无法核实 → unknown（不等于相同）；否则有差异 → incompatible
    if unverified:
        entry["compatibility"] = COMPAT_UNKNOWN
        entry["module_matches_question"] = row["method"] == config["module"]["value"]
    elif diffs:
        entry["compatibility"] = COMPAT_INCOMPATIBLE
        entry["module_matches_question"] = row["method"] == config["module"]["value"]
    else:
        entry["compatibility"] = COMPAT_EXACT
        entry["module_matches_question"] = True
    entry["supports_question"] = entry["compatibility"] == COMPAT_EXACT

    if result is None:
        entry["differences_cn"].append("结果文件缺失，数字不可引用")
        entry["compatibility"] = COMPAT_UNKNOWN
        entry["supports_question"] = False
    else:
        overview = {}
        try:
            overview = result["groups"]["True"]["总览"][0]
        except (KeyError, TypeError, IndexError, ValueError):
            overview = {}
        entry["summary"] = {
            "trade_count": overview.get("trade_count"),
            "win_rate": overview.get("win_rate"),
            "expectancy_r": overview.get("expectancy_r"),
            "profit_factor": overview.get("profit_factor"),
            "zero_trades": not overview.get("trade_count"),
        }
    return entry


def _matched_backtest_runs(conn, symbol: str | None, session_id: str | None,
                           message: str = "",
                           window_sel: dict | None = None) -> dict:
    """03B-R3 S2：先形成本问题完整比较配置，再对**全部**同标的已完成运行
    逐项比较——exact 优先返回（不被较新的不匹配记录挤掉）；不匹配/未知的
    旧结果只作该次运行的描述单列，不进「支持本问题」材料。返回
    {comparison_config, matched_runs, supporting_runs, note_cn}。"""
    empty = {"comparison_config": None, "matched_runs": [],
             "supporting_runs": [], "note_cn": "无同标的已完成补测运行"}
    if not symbol:
        return empty
    try:
        rows = conn.execute(
            "SELECT * FROM agent_backtest_requests WHERE symbol = ? "
            "AND status = 'completed' ORDER BY created_at DESC",
            (symbol,)).fetchall()
    except Exception:  # noqa: BLE001  表缺席（未升级库）不阻断讨论
        return empty
    config = _question_comparison_config(conn, session_id, message, symbol,
                                        window_sel=window_sel)
    current_rules = config["ruleset_sha256"]["value"]
    entries = []
    for row in rows:
        result = None
        if row["result_ref"]:
            try:
                result = json.loads(Path(row["result_ref"]).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                result = None
        entries.append(_compare_run_with_config(config, row, result, current_rules))
    exact = [e for e in entries if e["supports_question"]]
    others = [e for e in entries if not e["supports_question"]]
    return {
        "comparison_config": config,
        "matched_runs": exact + others,     # exact 优先；展示限长在卡片层
        "supporting_runs": [e["request_id"] for e in exact],
        "note_cn": ("只有 compatibility=exact 的运行支持本问题；"
                    "incompatible/unknown 仅作该次旧运行的描述单列"),
    }


def _topic_blocks(topic: str | None, symbol: str | None) -> dict:
    """R3（03B-R1，2026-09-08）：按讨论主题调用既有适配器，把**实际**状态/
    依据装进讨论材料——目录说明不代替数据；缺席时如实标注，不硬凑。

    - dca：证据账本可用性 + 状态板来源（逐状态 signals/data_refs 由 DCA
      服务给出，unknown 不改成 false）；
    - sentiment：全市场情绪环境 + 板块热概况（环境前提与板块条件分开）；
    - evidence：本标的经验索引（池类型匹配，宁缺毋滥）；
    - mindset：仅说明引用边界（用户求助时按其认可内容引用）；
    - money：用途边界（不跨用途借成绩，不代估预算）。
    """
    blocks: dict = {}
    if topic == "dca":
        try:
            from lei_signal.dca import service as dca_service

            ev = dca_service.load_evidence()
            blocks["dca_evidence"] = {
                "available": bool(ev.get("available")),
                "version": ev.get("version"),
                "error": ev.get("error_detail"),
                "note_cn": "定投状态与触发板基于该证据账本；实际成交走报单确认",
            }
        except Exception as exc:  # noqa: BLE001 缺席如实
            blocks["dca_evidence"] = {"available": False, "error": str(exc)}
        # 03B-R2 契约3（r5）：调用**真实** DCA 状态与证据适配器——本标的
        # 逐状态判断（deep20/bottom_zone 的 active/current）、数据依赖与
        # 日期、未知原因、可引用研究（含内容哈希的引用卡）。接口地址和
        # 说明不是状态，不再用「/api/dca/state」一行字顶替。
        try:
            from lei_signal.dca import service as dca_service
            from lei_signal.dca.state import default_data_loader, read_breadth

            ev2 = dca_service.load_evidence()
            loader = default_data_loader()
            readings = {}
            for key, market in (("cn", "cn_all"), ("us", "sp500")):
                try:
                    readings[key] = read_breadth(market)
                except Exception:  # noqa: BLE001
                    readings[key] = None
            b_cn = readings.get("cn").value if readings.get("cn") is not None else None
            b_us = readings.get("us").value if readings.get("us") is not None else None
            breadth_meta = {k: v.meta() for k, v in readings.items()
                            if v is not None}
            states = dca_service.targets_state(
                loader, ev2, [(symbol, symbol)] if symbol else None,
                b_cn, b_us, breadth_meta=breadth_meta)
            blocks["dca_state"] = {
                "states": states,
                "breadth": {k: (v.meta().to_dict() if v is not None else None)
                            for k, v in readings.items()},
                "note_cn": ("逐状态 signals 给出 active/current/health/reason 与"
                            "数据引用；缺数据=无法判定（null），条件不满足=false，"
                            "两者分开；发布节奏未核实时不称当前"),
            }
            try:
                from lei_signal.api.routes.dca import _DEFAULT_EVIDENCE

                blocks["dca_evidence_refs"] = {
                    "meta": dca_service.evidence_meta(_DEFAULT_EVIDENCE),
                    "note_cn": "可引用研究：每条数字带来源路径/内容哈希/状态/窗口",
                }
            except Exception as exc:  # noqa: BLE001
                blocks["dca_evidence_refs"] = {"available": False, "error": str(exc)}
        except Exception as exc:  # noqa: BLE001 适配器缺席如实标注，不硬凑
            blocks["dca_state"] = {
                "available": False,
                "error": str(exc),
                "note_cn": "定投状态适配器当前不可用——如实缺口，不编状态",
            }
        blocks["dca"] = {
            "purpose_boundary": "持续新收入定投/闲钱分批/技术交易三种用途分开；"
                                "不跨用途借成绩",
        }
    elif topic == "sentiment":
        try:
            from lei_signal.market_context import market_mood as mm

            cn = mm.cn_mood() or {}
            heat = mm.sector_heat_boards() or {}
            blocks["sentiment"] = {
                "cn_mood_state": cn.get("state_cn") or cn.get("state"),
                "icepoint_environment_premise": str(cn.get("state")) == "cold",
                "sector_conditions_checked": False,
                "heat_boards": [b.get("name") for b in (heat.get("boards") or [])][:5],
                "note_cn": "环境前提≠完整机会；板块四条件另核；强热环境未知不给条件统计",
            }
        except Exception as exc:  # noqa: BLE001
            blocks["sentiment"] = {"available": False, "error": str(exc)}
    elif topic == "evidence" and symbol:
        try:
            from lei_signal.copilot import experience as exp_mod
            from lei_signal.data_provenance import winrate_evidence_ref

            blocks["evidence"] = {
                "winrate": winrate_evidence_ref(symbol).to_dict(),
                "experience": exp_mod.experience_for_symbol(symbol)[:3],
                "note_cn": "按兼容性引用：本标的同方法→明确差异→其他对象参考→缺口",
            }
        except Exception as exc:  # noqa: BLE001
            blocks["evidence"] = {"available": False, "error": str(exc)}
    elif topic == "mindset":
        from lei_signal.copilot import mindset as mindset_mod

        pack = mindset_mod.load_mindset_seeds()
        blocks["mindset"] = {
            "available": bool(pack.get("available")),
            "count": pack.get("count"),
            "note_cn": "心态内容只在用户求助时按其认可且兼容的一条引用，不当规则"
                       "；只叙事，不参与判定",
        }
    elif topic == "money":
        blocks["money"] = {
            "purpose_needed": True,
            "note_cn": "资金用途需用户明确：持续新收入/已有闲钱/技术交易；"
                       "不跨用途借成绩，不代估预算",
        }
    return blocks


def _factor_request_message(message: str, history_rows: list) -> str | None:
    """Carry an explicit factor discussion through short follow-ups only.

    Never treat a past factor answer as permission to run an experiment. An
    explicit new technical question leaves this scope normally.
    """
    from lei_signal.copilot.factor_readonly import is_factor_question

    if is_factor_question(message):
        return message
    if not re.match(r"^(那|它|这个|刚才|继续|开始|执行|跑|补测|回测|帮我|请|试试|验证|好|可以|"
                    r"现在|当前|为什么|有没有|有用|有效)",
                    (message or "").strip()):
        return None
    if re.search(r"买点|卖点|止损|筹码|MACD|macd|均线|技术分析|报单|成交", message):
        return None
    for row in reversed(history_rows):
        if row.role != "assistant":
            continue
        try:
            meta = json.loads(row.meta_json or "{}")
            pack = (meta.get("evidence_card") or {}).get("factor_readonly")
        except (ValueError, TypeError, AttributeError):
            return None
        if not isinstance(pack, dict):
            return None
        refs = pack.get("definition_refs") or []
        return message + "；沿用刚才的因子问题" + ("：" + "、".join(refs) if refs else "")
    return None


def _prepare_discussion(
    request: Request, body: AgentChatRequest, on_stage=None,
    session_id: str | None = None,
    resume_question_id: int | None = None,
    timing=None,
) -> tuple[str, list, dict, list, str | None]:
    """agent_chat 与流式版共用的准备段（一个连接内完成）。

    03B-R2 契约1：会话由统一事务入口（enter_chat_request）先行裁决——本函数
    只按给定 session_id 组装材料，不再自行创建会话（重试/冲突在准备之前处理）。

    返回 (session_id, history_rows, ctx_payload, alerts, symbol)。
    阶段回调 ``on_stage``（可选）用于流式路径向 UI 报告调用链进度。
    ``timing``（可选，AskTiming）：分段计时——行情准备、材料组装、叙事块
    各自耗时进 spans（2026-09-15 agent-ask-stability，回答「准备慢在哪」）。
    """
    from lei_signal.api.ask_timing import NULL_TIMING  # noqa: PLC0415

    tm = timing if timing is not None else NULL_TIMING
    with closing(connect(_db_path(request))) as conn:
        session = get_session(conn, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")
        history_rows = list_messages(conn, session.session_id, limit=20)

        if resume_question_id is not None:
            frozen_row = conn.execute(
                "SELECT meta_json FROM agent_messages "
                "WHERE message_id=? AND session_id=? AND role='user'",
                (resume_question_id, session.session_id),
            ).fetchone()
            try:
                frozen_meta = json.loads(frozen_row[0] or "{}") if frozen_row else {}
                frozen = frozen_meta.get("discussion_v1", {})
            except (ValueError, TypeError):
                frozen = {}
            if frozen.get("context_kind") == "factor_readonly":
                pack = frozen["factor_readonly"]
                if on_stage:
                    on_stage("context", "恢复本问题已保存的因子材料")
                ctx = {"context_kind": "factor_readonly", "factor_readonly": pack,
                       "evidence_card": {"factor_readonly": pack}}
                return (session.session_id, history_rows, ctx, [], pack.get("symbol"),
                        {"factor_readonly": pack})

        factor_message = _factor_request_message(body.message, history_rows)
        if factor_message is not None:
            from lei_signal.api.routes.copilot import ResolveRequest, _resolve_symbol_with_ambiguity
            from lei_signal.copilot.factor_readonly import build_factor_reply

            factor_symbol, source, ambiguities = _resolve_symbol_with_ambiguity(
                request, ResolveRequest(message=body.message, session_id=session_id,
                                        selected_symbol=body.symbol), read_only=True)
            if on_stage:
                on_stage("context", "读取因子定义与已有材料（不计算、不回测）")
            svc = getattr(request.app.state, "factor_service", None)
            # The loader is only invoked by an observation query. No refresh,
            # auto-precompute, quote provider, or generic analysis fallback.
            pack = build_factor_reply(
                factor_message, factor_symbol,
                panel_loader=svc.panel if svc is not None else lambda: None)
            if ambiguities:
                pack.update(symbol=None, status="needs_clarification",
                            reply="标的还不能唯一确定：" + "、".join(ambiguities)
                                  + "。请明确产品代码；未运行计算。")
            pack.setdefault("metadata", {})["subject_source"] = source
            factor_symbol = pack.get("symbol")
            ctx = {"context_kind": "factor_readonly", "factor_readonly": pack,
                   "evidence_card": {"factor_readonly": pack}}
            tm.mark("prep_factor_readonly")
            return (session.session_id, history_rows, ctx, [], factor_symbol,
                    {"factor_readonly": pack})

        ctx_payload: dict = {}
        alerts: list = []
        service = getattr(request.app.state, "analysis_service", None)
        # R1（03B-R1）symbol 解析优先级：**本轮明确对象**（消息中代码 > 目录
        # 别名 > 自选名称）> 当前选中（页面传入 symbol）> 会话最近明确对象。
        # 页面传来的 symbol 只是「当前选中」，不得覆盖用户本轮明确改问的对象。
        # 03B-R2（r3）：对象识别与资料可用性**分离**——消息里语法合法的代码
        # 就是对象，即使还没有缓存行情也是它（缺数据走正式分析路径获取），
        # 不能回退成选中的另一个标的。
        explicit = body.context_kind == "symbol" and body.symbol
        subject_source = "none"
        symbol: str | None = None
        window_sel: dict | None = None  # 兜底初值；下方按路径（正常/全局/恢复）统一生成
        if on_stage:
            on_stage("resolve", "识别标的与意图")
        candidates = _symbol_candidates_from_message(body.message)
        if candidates:
            symbol = candidates[0]
            subject_source = "message"
        if symbol is None:
            # 目录层（人工维护的精确别名/目录名）先于自选模糊匹配：
            # 说「恒生科技」「科创50」这类专名时，自选名的 2 字模糊
            # 子串不该截走（2026-09-06：「恒生科技」曾被「科技 XLK」
            # 的 LCS 命中截走）。
            symbol = _resolve_symbol_by_catalog(body.message)
        from lei_signal.copilot.subjects import asks_for_sector
        sector_question = asks_for_sector(body.message)
        if symbol is None and not sector_question:
            from lei_signal.api.watchlist import list_watchlist  # noqa: PLC0415

            symbol = _resolve_symbol_by_name(body.message, list_watchlist(conn))
        if symbol is not None:
            subject_source = "message"
        if symbol is None and explicit and not sector_question:
            symbol = body.symbol
            subject_source = "selected"
        if symbol is None and not sector_question:
            symbol = _last_resolved_symbol(history_rows)
            if symbol is not None:
                subject_source = "session"
        from lei_signal.copilot.subjects import sector_context, asks_for_sector

        tm.mark("prep_resolve")
        sector_payload = sector_context(symbol) if symbol else None
        if sector_payload is not None:
            window_sel = (_read_frozen_window_for_question(conn, resume_question_id)
                          if resume_question_id is not None else
                          _resolve_window_for_question(conn, body, symbol, session_id, body.message))
            if on_stage:
                on_stage("context", f"读取{sector_payload['display_name']}板块资料")
            tm.mark("prep_sector")
            return session.session_id, history_rows, sector_payload, [], symbol, window_sel
        if symbol is not None and service is not None and on_stage:
            on_stage("fetch", f"拉取 {symbol} 行情（首次约 1 分钟）")
        if symbol is not None and service is not None:
            entry = service.get(symbol)
            tm.mark("prep_analysis")
            if entry.result is None:
                if explicit and subject_source == "selected":
                    raise HTTPException(
                        status_code=502, detail=entry.error or "分析不可用"
                    )
                symbol = None  # 提取/继承的代码分析失败不炸请求，退 global
            else:
                from lei_signal.api.routes.opportunities import (  # noqa: PLC0415
                    buy_point_review,
                )
                review = buy_point_review(request, symbol)
                tm.mark("prep_review")
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
                tm.mark("prep_plans")
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
                tm.mark("prep_news")
                # 回测经验（叙事层，不参与判定）：该标的池类型的历史结论，
                # 供 AI 引用「同类信号在这个池上历史成绩如何」。
                experience_items: list = []
                try:
                    from lei_signal.copilot import experience as exp_mod  # noqa: PLC0415

                    experience_items = exp_mod.experience_for_symbol(symbol)
                except Exception:  # noqa: BLE001
                    experience_items = []
                # 形态×打法适配（用户口径 2026-09-06：给一个标的要主动说
                # 「它现在的形态适合什么打法」，不无脑等信号触发）：
                # 近一年涨法画像（稳涨/急涨/下跌/震荡）+ 历史经验联动。
                fit_block = None
                try:
                    from lei_signal.copilot import fit as fit_mod  # noqa: PLC0415

                    fit_block = fit_mod.fit_advice(entry.result.frame)
                except Exception:  # noqa: BLE001
                    fit_block = None
                tm.mark("prep_extras")  # 经验叙事 + 形态适配
                # 横向机会：当前标的无系统买点候选时，带出当日扫描表里
                # 其他 actionable/waiting 标的（用户口径 2026-09-05：聊 A
                # 没买点时应主动提示 B/C 有观察价值，引导开下一个讨论）。
                alternatives: list = []
                review_dump = review.model_dump()
                if not (review_dump.get("candidates") or []):
                    try:
                        from lei_signal.api.opportunity_scan import (  # noqa: PLC0415
                            list_scan,
                            today_date,
                        )

                        alt_rows = list_scan(
                            conn, today_date()
                        )
                        alternatives = [
                            {
                                "symbol": r.symbol,
                                "display_name": r.display_name or r.symbol,
                                "verdict_cn": r.verdict_cn,
                                "missing_summary_cn": r.missing_summary_cn,
                            }
                            for r in alt_rows
                            if r.symbol != symbol
                            and r.verdict in ("actionable", "waiting")
                        ][:5]
                    except Exception:  # noqa: BLE001
                        alternatives = []
                ctx_payload = build_discussion_context(
                    entry.result, review_dump, plans, open_items,
                    news_brief=news_brief,
                    major_events=major_events,
                )
                ctx_payload["display_name"] = _static_symbol_name(
                    symbol, ctx_payload.get("display_name")) or "名称待核实"
                tm.mark("prep_context")
                if experience_items:
                    ctx_payload["experience"] = {
                        "note_cn": "历史经验叙事层（回测定案报告），不参与技术判定",
                        "items": experience_items,
                    }
                if fit_block and fit_block.get("available"):
                    ctx_payload["fit"] = fit_block
                # 情绪信号状态（2026-09-06 用户口径：讨论中主动提醒）：
                # 标的讨论也带全A情绪环境与两条信号的激活状态——AI 依据
                # 提示词规则在激活/警报时必须主动提，不等用户问。
                try:
                    from lei_signal.market_context import market_mood as mm

                    _cn = mm.cn_mood() or {}
                    _heat = mm.sector_heat_boards() or {}
                    # R3（03B-R1）：市场恐慌只是环境前提；板块四条件另核，
                    # 不得写成「冰点机会存在」。
                    ctx_payload["sentiment_signals"] = {
                        "cn_mood": {
                            "state": _cn.get("state"),
                            "state_cn": _cn.get("state_cn"),
                        },
                        "icepoint_environment_premise": str(_cn.get("state")) == "cold",
                        "sector_conditions_checked": False,
                        "heat_boards_n": len(_heat.get("boards") or []),
                        "note_cn": (
                            "市场恐慌只是冰点机会的环境前提；板块级四条件"
                            "（60日跌幅/散户流入强度/板块宽度）须逐项核实，"
                            "未核实前不构成完整机会。强热警报适用性取决于"
                            "市场环境，未判定时不给条件统计。"
                        ),
                    }
                except Exception:  # noqa: BLE001
                    pass
                try:
                    from lei_signal.copilot import winrate as winrate_mod  # noqa: PLC0415

                    _w = winrate_mod.winrate_for(symbol)
                    if _w:
                        ctx_payload["winrate"] = _w
                except Exception:  # noqa: BLE001
                    pass
                tm.mark("prep_sentiment_winrate")  # 情绪信号 + 胜率材料
                # 03B-R3 T1：本问题窗口选择一次生成（冻结与比较共用同一份）。
                # 恢复已有问题：用原问题快照冻结的选择，不按当前会话最新历史
                # 重选（z4）；新问题：对象确定后统一解析一次（u2 显示/冻结一致）。
                if resume_question_id is not None:
                    window_sel = _read_frozen_window_for_question(conn, resume_question_id)
                else:
                    window_sel = _resolve_window_for_question(
                        conn, body, symbol, session_id, body.message)
                try:
                    from lei_signal.data_provenance import winrate_evidence_ref

                    review_c = review_dump.get("candidates") or []
                    runs = _matched_backtest_runs(
                        conn, symbol, session_id, body.message,
                        window_sel=window_sel)
                    card = {
                        "facts": {
                            "symbol": symbol,
                            "display_name": ctx_payload["display_name"],
                            "as_of": review_dump.get("as_of"),
                            "verdict_cn": review_dump.get("verdict_cn"),
                            "buy_point_candidate_n": len(review_c),
                        },
                        "history_and_scope": {
                            "winrate_evidence": winrate_evidence_ref(symbol).to_dict(),
                            # 03B-R3 S2：完整方法比较（配置来源逐项记录；
                            # exact 优先；不匹配/未知单列不进支持材料）
                            **runs,
                            "note_cn": ("旧胜率表缺入场退出变体/规则版本/来源"
                                        "运行信息（兼容性 unknown），只能描述"
                                        "该表自己的历史结果；本标的补测结果按"
                                        "完整方法逐项比较，只有 exact 支持"
                                        "本问题——换退出/入场/规则/费用都不借"),
                        },
                        "explanations": {
                            "kinds": ["news", "major_events", "sentiment", "experience"],
                            "note_cn": "解释/假设，不参与技术判定、不是统计结论",
                        },
                        "pending_conditions": [
                            w.get("text_cn")
                            for w in (review_dump.get("watch_conditions") or [])
                            if isinstance(w, dict)
                        ],
                    }
                    ctx_payload["evidence_card"] = card
                except Exception:  # noqa: BLE001 证据卡缺席不阻断讨论
                    pass
                tm.mark("prep_evidence")
                if alternatives:
                    ctx_payload["alternatives"] = alternatives
                ctx = context_from_result(entry.result)
                alerts = [a for p in plans for a in evaluate_plan(p, ctx)]
        if symbol is None:
            # 03B-R3 T1：全局/降级路径也形成一次选择（明确未核实），原全局讨论
            # 照常回答；不能让 window_sel 在返回时空绑定（z1 全局回归）。
            if resume_question_id is not None:
                window_sel = _read_frozen_window_for_question(conn, resume_question_id)
            else:
                window_sel = _resolve_window_for_question(
                    conn, body, None, session_id, body.message)
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
            # 散户情绪信号材料（2026-09-06 接入，prompt-sentiment-ai 口径）：
            # 两融三票情绪 + 市场结构极化 + 板块热度触发，纯叙事标注层。
            try:
                from lei_signal.market_context import market_mood as mm

                ctx_payload["sentiment_dashboard"] = {
                    "cn_mood": mm.cn_mood(),
                    "market_structure": mm.market_structure(),
                    "sector_heat": mm.sector_heat_boards(),
                    "note_cn": "情绪面叙事层（research_proxy）：不参与技术判定、不构成买卖点",
                }
            except Exception:  # noqa: BLE001 — 情绪缺席不阻断
                ctx_payload["sentiment_dashboard"] = None
            # 重大事件（客观字段 only，2026-09-05 用户口径）：聊大盘环境时
            # 带上「英伟达资本开支」级别的产业/宏观大事，叙事参考层。
            try:
                from lei_signal.newsfeed.service import (  # noqa: PLC0415
                    NewsfeedService,
                )

                ctx_payload["major_events"] = NewsfeedService().major_events_brief()
            except Exception:  # noqa: BLE001
                ctx_payload["major_events"] = None
            tm.mark("prep_global_material")  # 全局兜底材料（宽度/两融/情绪/大事）
        # R3（03B-R1）：按主题装载既有适配器数据（DCA/情绪/证据/心态/资金），
        # 两个路径（有标的/全局）都消费；目录说明不代替实际数据。
        from lei_signal.copilot import resolve as resolve_mod

        parsed = resolve_mod.parse_request(body.message)
        parsed_topic = parsed["topic"]
        ctx_payload.update(_topic_blocks(parsed_topic, symbol))
        # 连续讨论一轮（2026-09-16）+ C3 补修：主题、用户声明立场与
        # 会话背景进材料。本条消息明确说的优先；同会话同对象此前声明过
        # 且未撤销的作为背景补齐（不重复追问、不再声称用户没提供）；
        # 本条明确撤销的立即失效。背景=讨论语境，不是成交记录或新授权；
        # 判定层规则不因立场改变。
        ctx_payload["question_topic"] = parsed_topic
        bg = resolve_mod.apply_user_facts(_user_background(history_rows, symbol), body.message)
        # Current input and historical replay use exactly the same field updates.
        # Uncertain/foreign/hypothetical text remains available for discussion only.
        ctx_payload["user_fact_updates"] = resolve_mod.user_fact_events(body.message)
        stance = "holding" if bg.get("holding") else None
        if bg.get("budget"):
            ctx_payload["user_budget"] = bg["budget"]
        if bg.get("purpose"):
            ctx_payload["user_purpose"] = bg["purpose"]
        if bg and ctx_payload.get("context_kind") != "sector":
            ctx_payload["user_background"] = {
                "holding": bool(bg.get("holding")), "budget": bg.get("budget"),
                "purpose": bg.get("purpose"),
                "note_cn": ("用户在本会话、该对象上明确声明的背景。只作讨论参考，"
                            "不是成交记录、不是写库授权；假设或别人情况不能覆盖这些事实。"),
            }
        if stance == "holding" and ctx_payload.get("context_kind") != "sector":
            ctx_payload["discussion_stance"] = {
                "kind": "holding",
                "note_cn": ("用户声明已持有该标的：从持仓管理角度解释（当前系统"
                            "状态、失效位与观察条件），不按首次买入引导；用户未"
                            "提供的成本与资金信息不得编造；不记录成交；有既有"
                            "计划时结合计划状态讲。"),
            }
        tm.mark("prep_done")  # 主题块（DCA/情绪/证据/心态/资金）之后准备完成
        # window_sel 已在构建证据卡前统一算好（冻结与比较共用同一份依据）
        return session.session_id, history_rows, ctx_payload, alerts, symbol, window_sel


def _enter_chat(request: Request, body: AgentChatRequest):
    """契约1 统一事务入口：在创建会话、落问题、调用模型**之前**处理同编号
    请求的重试与冲突（agent_chat 与流式版共用）。返回 chat_identity 的
    EnterOutcome：replay=直接复用原回答；proceed=按给定会话继续。"""
    from lei_signal.copilot.chat_identity import (
        ChatRequestConflict,
        chat_request_hash,
        enter_chat_request,
    )

    h = chat_request_hash(message=body.message, context_kind=body.context_kind,
                          symbol=body.symbol)
    with closing(connect(_db_path(request))) as conn:
        if body.session_id and get_session(conn, body.session_id) is None:
            raise HTTPException(status_code=404,
                                detail=f"会话不存在: {body.session_id}")
        try:
            return enter_chat_request(
                conn, client_request_id=body.client_request_id,
                request_hash=h, session_id=body.session_id,
                new_session_symbol=body.symbol,
                new_session_title=body.message[:20] or "新会话",
                request_message=body.message,
                request_context_kind=body.context_kind or "global",
                request_symbol=body.symbol)
        except ChatRequestConflict as exc:
            raise HTTPException(status_code=409, detail={
                "code": "REQUEST_CONFLICT",
                "message": str(exc),
            }) from exc


def _maybe_plan_artifact(request: Request, session_id: str, question_id: int | None,
                         body: AgentChatRequest, symbol: str | None,
                         ctx_payload: dict) -> None:
    """整理计划类问题 → 生成服务端计划产物并挂到 ctx（即时/流式/历史同一产物）。"""
    if question_id is None:
        return
    if ctx_payload.get("context_kind") == "factor_readonly":
        return
    try:
        from lei_signal.copilot import resolve as resolve_mod

        if resolve_mod.parse_request(body.message).get("topic") != "plan":
            return
        with closing(connect(_db_path(request))) as conn:
            artifact = _server_plan_artifact(
                conn, session_id, question_id, symbol,
                ctx_payload.get("buy_point_review"), body.message)
        if artifact:
            ctx_payload["plan_artifact"] = artifact
    except Exception:  # noqa: BLE001  产物缺席不阻断讨论（如实无卡）
        return


@router.post("/agent/chat", response_model=AgentChatReply)
def agent_chat(request: Request, body: AgentChatRequest) -> AgentChatReply:
    """统一讨论入口：多轮记忆 + 技术摘要全喂 + 数值接地。

    连接策略：全程至多两次开关——先读写会话与上下文原料（一次），LLM 往返
    不持连接，回复落库再开一次。load_ark_config/chat_discussion 经
    ``plans_llm`` 模块属性调用（测试 monkeypatch 点），语义与直接调用一致。
    03B-R2 契约1：同编号请求在准备/建模**之前**裁决——重试复用原会话原问题
    原回答（不重复落问题、不重复跑模型），换内容/换会话 409。
    03B-R3 S4：回答按 question_id 精确绑定（列绑定+claim 状态机）；重试
    不再取「问题之后第一条 assistant」——未生成就明确未完成或按固定逻辑
    恢复原问题，绝不复用下一问题或补测卡。
    """
    def _reply_from_payload(p: dict) -> AgentChatReply:
        items: list[TraceItem] = []
        for t in (p.get("trace") or []):
            if isinstance(t, dict):
                try:
                    items.append(TraceItem(**{k: t.get(k) for k in
                                              ("label", "rule_id", "evidence_cn",
                                               "research_proxy", "principle_source")}))
                except Exception:  # noqa: BLE001
                    continue
        return AgentChatReply(
            session_id=p.get("session_id") or outcome.session_id or "",
            reply=p.get("reply") or "",
            grounded=bool(p.get("grounded")),
            trace=items,
            resolved_symbol=p.get("resolved_symbol"),
            question_id=p.get("question_id"),
            evidence_card=p.get("evidence_card"),
            # T3：重试/未完成出口都要保留原产物，不能有的一条路径丢卡
            plan_artifact=p.get("plan_artifact"),
            answer_state=p.get("answer_state"),
            next_steps=p.get("next_steps") or [],
        )

    from lei_signal.api.ask_timing import AskTiming  # noqa: PLC0415

    timing = AskTiming()
    timing.mark("received")
    outcome = _enter_chat(request, body)
    timing.mark("identity")
    if outcome.kind == "replay":
        return _reply_from_payload(outcome.replay_reply or {})
    if outcome.kind == "incomplete":
        # S4：同一问题未生成回答时的**明确未完成**出口（服务端状态约束，
        # 不复用下一问题/补测卡，也不产生第二个问题）
        return _reply_from_payload(outcome.incomplete_reply or {})

    resume = outcome.kind == "resume"

    def _release_claim() -> None:
        """失败收场时把生成权放回 pending：同身份重试立即恢复（与流式同源）。
        无 claim_state_at（非本次领取）不动，防误伤重试者的新领取。"""
        if not outcome.claim_cid or not outcome.claim_state_at:
            return
        try:
            from lei_signal.copilot.chat_identity import (  # noqa: PLC0415
                release_generation,
            )

            with closing(connect(_db_path(request))) as conn:
                release_generation(conn, outcome.claim_cid,
                                   expected_state_at=outcome.claim_state_at)
        except Exception:  # noqa: BLE001
            logger.exception("agent_chat 释放生成权失败")

    try:
        (session_id, history_rows, ctx_payload, alerts, symbol,
         window_sel) = _prepare_discussion(
            request, body, session_id=outcome.session_id,
            resume_question_id=outcome.question_id if resume else None,
            timing=timing,
        )
    except Exception:
        _release_claim()  # 准备失败不把 claim 卡在 generating 600 秒
        raise
    timing.mark("prepared")
    question_id: int | None = outcome.question_id if resume else None
    if not resume:
        # 03B：先落 user 消息 + discussion_v1 快照（回测绑定需要 question_id）；
        # 并发双发在写事务内收口：输家直接复用赢家的原问题，不产生第二个问题
        try:
            with closing(connect(_db_path(request))) as conn:
                appended, user_msg, dup = _append_user_for_claim(
                    conn, outcome, body, symbol,
                    review_dump=ctx_payload.get("buy_point_review"),
                    as_of=ctx_payload.get("as_of"), window_sel=window_sel)
                question_id = user_msg.message_id if user_msg is not None else None
        except Exception:
            _release_claim()
            raise
        if appended == "duplicate":
            dup = dup or {}
            return AgentChatReply(
                session_id=dup.get("session_id") or session_id,
                reply=dup.get("reply") or "该问题已受理，回答生成中。",
                grounded=bool(dup.get("grounded")),
                resolved_symbol=dup.get("resolved_symbol"),
                question_id=dup.get("question_id"),
                evidence_card=dup.get("evidence_card"),
                plan_artifact=dup.get("plan_artifact"),
                next_steps=dup.get("next_steps") or [],
            )

    # 03B-R3 S5：整理计划类问题生成服务端产物（原问题绑定，模型不参与构造）
    _maybe_plan_artifact(request, session_id, question_id, body, symbol, ctx_payload)

    # 连续讨论一轮（2026-09-16）：答案完全由确定性事实决定的问题（板块→产品
    # 关系、与刚才比较）直接系统作答，不走模型也不走降级模板。
    det_reply = _deterministic_reply(history_rows, symbol, ctx_payload, body.message)
    config = plans_llm.load_ark_config() if det_reply is None else None
    reply: str | None = det_reply
    grounded = det_reply is not None
    # 数值白名单 = 技术材料数值 ∪ 本轮 user message 中出现的数字
    # （用户问「8700 是不是更好」、LLM 回显「你说的 8700」时不误降级）
    # ∪ 上下文字符串里的代码数字段（TH881129/515880 这类标的代码会被校验器
    #   当数字抽取，它们本就来自系统材料，不进白名单就是误伤——glm-5.3 讲
    #   板块时必带代码，曾因此整链降级）
    # ∪ 会话历史里的代码数字段（S4-2 误拦修复：全局追问回显上一轮标的代码）
    allowed_nums = (
        collect_payload_numbers(ctx_payload)
        | frozenset(extract_market_numbers(body.message))
        | frozenset(_payload_symbol_numbers(ctx_payload))
        | frozenset(_history_symbol_numbers(history_rows))
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
    # 契约3：同一证据产物进历史（恢复/重开时从会话记录拿回，不依赖模型复述）
    if ctx_payload.get("evidence_card") is not None:
        meta["evidence_card"] = ctx_payload["evidence_card"]
    # 03B-R3 S5：服务端计划产物（真实 suggested_plan + 用户明确字段）进
    # meta/响应/历史——模型只解释，不是唯一产物来源
    if ctx_payload.get("plan_artifact") is not None:
        meta["plan_artifact"] = ctx_payload["plan_artifact"]
    # UX 第一期：下一步动作随回答下发并进历史（两入口/历史同一份）
    next_steps = _build_next_steps(ctx_payload, symbol)
    if next_steps:
        meta["next_steps"] = next_steps
    try:
        with closing(connect(_db_path(request))) as conn:
            _append_answer(conn, session_id=session_id, question_id=question_id,
                           content=reply, grounded=grounded, meta=meta,
                           claim_cid=outcome.claim_cid,
                           source_request_id=outcome.claim_cid or "")
    except Exception:
        _release_claim()  # 保存失败不把 claim 卡在 generating（重试可立即恢复）
        raise
    timing.mark("answer_saved")
    logger.info(
        "agent_ask_timing mode=plain session=%s symbol=%s %s",
        session_id, symbol or "-",
        json.dumps(timing.summary(), ensure_ascii=False, sort_keys=True))
    return AgentChatReply(
        session_id=session_id, reply=reply, grounded=grounded,
        trace=trace, resolved_symbol=symbol,
        question_id=question_id,
        evidence_card=ctx_payload.get("evidence_card"),
        plan_artifact=ctx_payload.get("plan_artifact"),
        answer_state="answered",
        next_steps=next_steps,
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
        from lei_signal.copilot.subjects import catalog_names
        names = catalog_names()
        out = []
        for s in sessions:
            msgs = list_messages(conn, s.session_id, limit=1)
            out.append(AgentSessionDTO(
                session_id=s.session_id, symbol=s.symbol, title_cn=s.title_cn,
                display_name=names.get(s.symbol, "名称待核实") if s.symbol else None,
                last_active_at=s.last_active_at,
                last_message_cn=msgs[-1].content[:50] if msgs else "",
            ))
    return out


@router.get("/agent/sessions/{session_id}/messages", response_model=list[AgentMessageDTO])
def agent_session_messages(request: Request, session_id: str) -> list[AgentMessageDTO]:
    """会话历史（契约1/3）：带问题归属、证据卡、补测系统卡与草稿绑定——
    刷新/历史重开时前端据此恢复同一张卡、同一个 plan_id，不依赖模型复述。"""
    with closing(connect(_db_path(request))) as conn:
        if get_session(conn, session_id) is None:
            raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")
        msgs = list_messages(conn, session_id, limit=100)
        bindings: dict[int, dict] = {}
        try:
            for b in conn.execute(
                    "SELECT * FROM agent_plan_draft_bindings WHERE session_id = ?",
                    (session_id,)).fetchall():
                qid = b["question_id"]
                if qid is not None and qid not in bindings:
                    bindings[int(qid)] = {
                        "plan_id": b["plan_id"], "symbol": b["symbol"],
                        "client_request_id": b["client_request_id"],
                    }
        except Exception:  # noqa: BLE001  表未升级时历史仍可用
            bindings = {}
        # 二轮复验（2026-09-15 遗漏二）：为 incomplete 回答投影**可核实的原问题
        # 重试身份**（领号时保存的原始三输入 + 回答行上的来源编号）；旧记录/
        # 已完成问题不投影，前端不得用当前会话/标的猜原请求。
        retry_map: dict[int, dict] = {}
        try:
            from lei_signal.copilot.chat_identity import retry_identity_for

            for r in conn.execute(
                    "SELECT message_id, source_request_id FROM agent_messages "
                    "WHERE session_id = ? AND role = 'assistant' "
                    "AND source_request_id != '' "
                    "AND instr(meta_json, 'answer_incomplete') > 0",
                    (session_id,)).fetchall():
                ident = retry_identity_for(
                    conn, r["source_request_id"], message_id=r["message_id"])
                if ident:
                    retry_map[int(r["message_id"])] = ident
        except Exception:  # noqa: BLE001  表未升级时历史仍可用
            retry_map = {}
    out: list[AgentMessageDTO] = []
    for m in msgs:
        try:
            meta = json.loads(m.meta_json or "{}")
        except json.JSONDecodeError:
            meta = {}
        # 旧回答正文保持原样；展示卡补可核实名称，不回写原始存证。
        if isinstance(meta.get("evidence_card"), dict):
            facts = meta["evidence_card"].get("facts")
            if isinstance(facts, dict) and facts.get("symbol") and not facts.get("display_name"):
                facts["display_name"] = _static_symbol_name(facts["symbol"], None) or "名称待核实"
        # 03B-R3 S4：归属走**精确列**——user 消息=自身 ID；assistant 消息=
        # 回答绑定的 question_id（旧记录 NULL=不可考，不按相邻位置猜）
        if m.role == "user":
            qid: int | None = m.message_id
        else:
            qid = m.question_id if m.question_id is not None else None
        kind = m.message_kind if m.message_kind else (
            "backtest_result" if meta.get("kind") == "backtest_result" else "")
        # 草稿绑定按问题号取：user 消息=自身 ID；assistant=其绑定的原问题
        plan_draft = bindings.get(m.message_id if m.role == "user" else qid)
        out.append(AgentMessageDTO(
            role=m.role, content=m.content, grounded=m.grounded,
            created_at=m.created_at,
            message_id=m.message_id,
            question_id=qid,
            resolved_symbol=meta.get("resolved_symbol"),
            evidence_card=meta.get("evidence_card"),
            system_generated=bool(meta.get("system_generated")) or kind != "",
            message_kind=kind,
            plan_artifact=meta.get("plan_artifact"),
            plan_draft=plan_draft,
            next_steps=meta.get("next_steps") or [],
            answer_incomplete=meta.get("answer_incomplete"),
            retry=retry_map.get(m.message_id),
        ))
    return out


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


class _StreamState:
    """流式请求中后台工作者与消费者共用的结束/归属状态（S1，2026-09-15）。

    cancelled：消费者已断开/退出（finally 里无条件置位）——工作者晚取得
    生成权时据此立即收尾，不开始准备/生成；
    outcome：工作者的领号结果（生成权归属的唯一载体，claim_state_at CAS）；
    terminal：消费者已到终态（含失败 done）——finally 不再重复释放。"""

    __slots__ = ("lock", "cancelled", "outcome", "terminal")

    def __init__(self) -> None:
        import threading

        self.lock = threading.Lock()
        self.cancelled = False
        self.outcome = None
        self.terminal = False


def _http_disconnect_poll(request: Request) -> bool:
    """同步轮询真实 HTTP 客户端是否已断开（S1 矩阵 5）。

    真实断开时 uvicorn 不会及时把 GeneratorExit 送进响应生成器（实测：
    客户端断开后同步生成器长期悬挂、claim 无人收尾）。ASGI 服务器会把
    ``http.disconnect`` 放进 receive 通道——这里以近零超时取一条消息
    （没有消息=仍连接），经 ``anyio.from_thread.run`` 回到事件循环执行。

    只在 anyio 工作线程内有效（生产=StreamingResponse 的线程池迭代器）；
    主线程手动驱动生成器的测试/探针环境没有 anyio token，异常一律按
    「未断开」处理——那些环境由 close()/finally 路径负责收尾。"""
    try:
        import asyncio as _asyncio  # noqa: PLC0415

        import anyio  # noqa: PLC0415

        async def _poll() -> bool:
            try:
                message = await _asyncio.wait_for(request.receive(), 0.001)
            except _asyncio.TimeoutError:
                return False
            return message.get("type") == "http.disconnect"

        return bool(anyio.from_thread.run(_poll))
    except Exception:  # noqa: BLE001  非 anyio 工作线程/通道不可用=按未断开
        return False


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

    from lei_signal.api.ask_timing import AskTiming  # noqa: PLC0415

    def _sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {_json.dumps(data, ensure_ascii=False)}\n\n"

    def _generate() -> Iterator[str]:
        import queue as _queue
        import threading as _threading

        # 分段计时（任务书 §一）：收到→身份登记→资料准备→资料展示→
        # 模型首字→回答保存；汇总进 done 与服务端日志，回答「慢在哪一段」。
        timing = AskTiming()
        timing.mark("received")

        # 准备段（解析/行情/材料）在后台线程跑，阶段事件经队列实时推给客户端：
        # 用户在等待的第一秒就能看到「识别标的→拉取行情」逐条点亮，而不是
        # 全部跑完才收到一串。
        q: _queue.Queue[tuple] = _queue.Queue()

        def on_stage(key: str, text: str) -> None:
            q.put(("stage", (key, text)))

        # S1（主控复验 2026-09-15）：后台工作者与流消费者**共用**结束/取消
        # 状态与生成权归属。消费者提前退出（断连/停止）时，工作者之后晚取得
        # 的生成权也必须收尾——否则 claim 卡在 generating，同身份重试被
        # 「回答正在生成」错误地挡满租约。清理只放自己的领取（claim_state_at
        # CAS），绝不触碰重试者的新领取；无消费者后不开始准备/生成。
        shared = _StreamState()

        def _release_claim(out) -> None:
            """失败/断连收场：把生成权放回 pending，同身份重试可立即恢复
            （不等 600 秒租约）。只放自己的领取——无 claim_state_at（非本次
            领取/replay/incomplete 出口）一律不动，防误伤重试者的新领取。"""
            if (out is None or not getattr(out, "claim_cid", None)
                    or not getattr(out, "claim_state_at", None)):
                return
            try:
                from lei_signal.copilot.chat_identity import (  # noqa: PLC0415
                    release_generation,
                )

                with closing(connect(_db_path(request))) as conn:
                    release_generation(
                        conn, out.claim_cid,
                        expected_state_at=out.claim_state_at)
            except Exception:  # noqa: BLE001
                logger.exception(
                    "agent_chat_stream 释放生成权失败（cid=%s…）",
                    str(getattr(out, "claim_cid", ""))[:8])

        def _work() -> None:
            try:
                # 契约1：统一事务入口在准备/建模之前裁决（重试复用/409/
                # 未完成/恢复）
                outcome = _enter_chat(request, body)
                with shared.lock:
                    shared.outcome = outcome
                    gone = shared.cancelled
                if gone:
                    # 消费者已断开：晚领号也收尾；不开始准备/生成（S1 矩阵1/2）
                    _release_claim(outcome)
                    return
                q.put(("entered", outcome))
                if outcome.kind in ("proceed", "resume"):
                    q.put((
                        "prepared",
                        _prepare_discussion(
                            request, body, on_stage=on_stage,
                            session_id=outcome.session_id,
                            resume_question_id=outcome.question_id
                            if outcome.kind == "resume" else None,
                            timing=timing),
                    ))
            except Exception as exc:  # noqa: BLE001
                # 可靠性一期（2026-09-14）：准备段失败必须留服务端日志。
                # 此前异常只进 SSE、不打日志，运行版首问「database is locked」
                # 在服务端无任何痕迹（见实验报告 A 节归因）。
                logger.exception(
                    "agent_chat_stream 准备段失败（session=%s message=%r）",
                    body.session_id, body.message[:50],
                )
                q.put(("error", exc))

        _threading.Thread(target=_work, daemon=True).start()

        def _log_timing(mode: str, session_id: str | None,
                        symbol: str | None) -> None:
            """单请求分段耗时汇总进服务端日志（不含问题原文/密钥/SQL 参数）。"""
            summary = timing.summary()
            logger.info(
                "agent_ask_timing mode=%s session=%s symbol=%s %s",
                mode, session_id or "-", symbol or "-",
                _json.dumps(summary, ensure_ascii=False, sort_keys=True),
            )

        def _fail_payload(note: str, *, out=None, session_id: str = "",
                          symbol: str | None = None,
                          retryable: bool = True) -> dict:
            """可重试的失败出口（任务书 §三）：失败如实说明、保留问题、
            给明确重试入口；不假装开始回答，也不把数据库等待说成 AI 思考。"""
            _release_claim(out)
            timing.mark("failed")
            payload = {
                "session_id": session_id,
                "resolved_symbol": symbol,
                "grounded": False,
                "answer_state": "failed",
                "retryable": retryable,
                "verify_note": note,
                "timing_ms": timing.summary(),
            }
            _log_timing("stream_failed", session_id or (out.session_id if out else ""),
                        symbol)
            return payload

        import time as _time

        def _mark_terminal() -> None:
            with shared.lock:
                shared.terminal = True

        prepared = None
        outcome = None
        phase = "identity"  # identity=登记中；prepare=准备资料中（心跳文案据此区分）
        wait_started = _time.monotonic()
        try:
            # 提交即回执（任务书 §三）：不等内容，先告诉用户「已收到问题」。
            # 在 try 内：首条 yield 即断开时 finally 仍会标记取消并收尾（S1）。
            yield _sse("stage", {"key": "received", "text": "已收到问题，正在登记请求"})
            while True:
                try:
                    kind, payload = q.get(timeout=5)
                except _queue.Empty:
                    if _http_disconnect_poll(request):
                        # 真实 HTTP 断开（S1 矩阵 5）：立刻退出，finally
                        # 标记取消并收尾生成权；不等服务器写失败才发现。
                        return
                    waited = int(_time.monotonic() - wait_started)
                    if waited > 180:
                        logger.warning(
                            "agent_chat_stream 准备段超时180s"
                            "（session=%s message=%r）",
                            body.session_id, body.message[:50],
                        )
                        yield _sse("done", _fail_payload(
                            "准备阶段超时（等待 180 秒仍未就绪）。问题已保留，"
                            "可点「重试」继续，不会重复记录。",
                            out=outcome))
                        _mark_terminal()
                        return
                    # 真实阶段心跳（不虚构进度/倒计时）：数据库等待如实说
                    # 「等待系统处理」，绝不描述成「AI 正在思考」。
                    if phase == "identity":
                        text = ("等待系统处理：正在登记请求"
                                f"（数据库繁忙时需排队，已等待 {waited} 秒）")
                    else:
                        text = f"仍在读取系统资料（已等待 {waited} 秒）"
                    yield _sse("stage", {"key": "waiting", "text": text})
                    continue
                if kind == "stage":
                    yield _sse("stage", {"key": payload[0], "text": payload[1]})
                elif kind == "error":
                    exc = payload
                    import sqlite3 as _sqlite3  # noqa: PLC0415

                    if isinstance(exc, _sqlite3.OperationalError) and \
                            "locked" in str(exc).lower():
                        note = (
                            "准备阶段失败：系统数据库正被后台任务占用，"
                            "等待后仍不可用（database is locked）。"
                            "你的问题已保留——可点「重试」继续，不会重复记录。"
                        )
                    elif isinstance(exc, HTTPException):
                        note = f"准备阶段失败：{exc.detail}"
                    else:
                        note = f"准备阶段失败：{exc}"
                    retryable = not (
                        isinstance(exc, HTTPException) and exc.status_code < 500)
                    yield _sse("done", _fail_payload(
                        note, out=outcome, retryable=retryable))
                    _mark_terminal()
                    return
                elif kind == "entered":
                    outcome = payload
                    timing.mark("identity")
                    phase = "prepare"
                    if outcome.kind == "replay":
                        p = outcome.replay_reply or {}
                        yield _sse("token", {"t": p.get("reply") or ""})
                        timing.mark("answer_saved")
                        yield _sse("done", {
                            "session_id": p.get("session_id") or outcome.session_id or "",
                            "resolved_symbol": p.get("resolved_symbol"),
                            "grounded": bool(p.get("grounded")),
                            "question_id": p.get("question_id"),
                            "evidence_card": p.get("evidence_card"),
                            "plan_artifact": p.get("plan_artifact"),
                            "answer_state": p.get("answer_state") or "answered",
                            "next_steps": p.get("next_steps") or [],
                            "replayed": True,
                            "timing_ms": timing.summary(),
                        })
                        _log_timing("stream_replay",
                                    p.get("session_id") or outcome.session_id,
                                    p.get("resolved_symbol"))
                        _mark_terminal()
                        return
                    if outcome.kind == "incomplete":
                        # S4：未完成明确出口（不复用下一问题/补测卡）
                        p = outcome.incomplete_reply or {}
                        yield _sse("token", {"t": p.get("reply") or ""})
                        yield _sse("done", {
                            "session_id": p.get("session_id") or outcome.session_id or "",
                            "resolved_symbol": None,
                            "grounded": False,
                            "question_id": p.get("question_id"),
                            "answer_state": p.get("answer_state") or "pending",
                            "incomplete": True,
                            "timing_ms": timing.summary(),
                        })
                        _log_timing("stream_incomplete",
                                    p.get("session_id") or outcome.session_id, None)
                        _mark_terminal()
                        return
                else:
                    prepared = payload
                    timing.mark("prepared")
                    break

            (session_id, history_rows, ctx_payload, alerts, symbol,
             window_sel) = prepared
            resume = outcome.kind == "resume"
            question_id: int | None = outcome.question_id if resume else None

            # 可靠性一期（2026-09-14）：系统资料就绪即推送，不等模型。字段与
            # done 同名同源（不是第二套证据），前端据此先渲染事实卡并提示
            # 「资料已就绪，AI 解释仍在生成」；done 仍是唯一的最终完成信号。
            # 下一步动作在此处算一次，done 复用同一份（不重复推导）。
            next_steps = _build_next_steps(ctx_payload, symbol)
            yield _sse("prepared", {
                "session_id": session_id,
                "resolved_symbol": symbol,
                "quick_card": _quick_card(ctx_payload, symbol),
                "evidence_card": ctx_payload.get("evidence_card"),
                "next_steps": next_steps,
            })
            timing.mark("material_sent")

            if not resume:
                # 03B：先落 user 消息 + discussion_v1 快照（回测绑定需要 question_id）；
                # 编号已在进入时领取——并发双发在此收口，输家复用赢家原问题
                try:
                    with closing(connect(_db_path(request))) as conn:
                        appended, user_msg, dup = _append_user_for_claim(
                            conn, outcome, body, symbol,
                            review_dump=ctx_payload.get("buy_point_review"),
                            as_of=ctx_payload.get("as_of"), window_sel=window_sel)
                        question_id = (
                            user_msg.message_id if user_msg is not None else None)
                except Exception as exc:  # noqa: BLE001
                    # 落库失败不假装开始回答：资料已展示，如实说明历史没存上；
                    # 释放生成权，重试同一问题立即恢复（不重复建问题）。
                    logger.exception(
                        "agent_chat_stream 问题落库失败（session=%s）", session_id)
                    yield _sse("done", _fail_payload(
                        "系统资料已在上方展示；但本次问题未能写入历史记录"
                        f"（{type(exc).__name__}），AI 解释没有开始。"
                        "问题已保留——可点「重试」继续，不会重复记录。",
                        out=outcome, session_id=session_id, symbol=symbol))
                    _mark_terminal()
                    return
                timing.mark("question_saved")
                if appended == "duplicate":
                    dup = dup or {}
                    yield _sse("done", {
                        "session_id": dup.get("session_id") or session_id,
                        "resolved_symbol": dup.get("resolved_symbol"),
                        "grounded": bool(dup.get("grounded")),
                        "question_id": dup.get("question_id"),
                        "evidence_card": dup.get("evidence_card"),
                        "replayed": True,
                        "timing_ms": timing.summary(),
                    })
                    _log_timing("stream_duplicate", session_id, symbol)
                    _mark_terminal()
                    return

            # 03B-R3 S5：整理计划类问题生成服务端产物（原问题绑定）
            _maybe_plan_artifact(request, session_id, question_id, body, symbol,
                                 ctx_payload)

            # 连续讨论一轮（2026-09-16）：确定性作答（板块→产品关系、与刚才
            # 比较）不走模型——正文一条 token 下发，grounded=True（依据系统
            # 数据），跳过后续模型校验（自己的系统文案不过模型接地校验器）。
            det_reply = _deterministic_reply(history_rows, symbol, ctx_payload,
                                             body.message)
            config = plans_llm.load_ark_config() if det_reply is None else None
            pieces: list[str] = []
            interrupt_reason = ""
            if det_reply is not None:
                timing.mark("first_token")
                pieces.append(det_reply)
                yield _sse("token", {"t": det_reply})
            if config is not None:
                yield _sse("stage", {"key": "llm", "text": "生成解释（AI 逐字输出）"})
                try:
                    for piece in plans_llm.chat_discussion_stream(
                        ctx_payload,
                        [{"role": m.role, "content": m.content} for m in history_rows],
                        body.message,
                        config,
                    ):
                        # 完成契约（主控复核 2026-09-15 固定补修一）：流未正常收尾/
                        # 被截断都以 StreamInterrupt 收尾，原因入落库与提示
                        if isinstance(piece, plans_llm.StreamInterrupt):
                            interrupt_reason = piece.reason
                            break
                        if not pieces:
                            timing.mark("first_token")
                        if _http_disconnect_poll(request):
                            # 真实客户端断开（S1 矩阵 5）：停止继续生成，
                            # finally 收尾（历史只留问题，不落假回答）
                            return
                        pieces.append(piece)
                        yield _sse("token", {"t": piece})
                except GeneratorExit:
                    # 客户端断连/停止接收：不再产出事件；finally 释放生成权，
                    # 历史只留问题不落假回答（既有「停止接收」语义）。
                    raise
                except Exception:  # noqa: BLE001
                    # 模型迭代器意外抛错（网络层已在 llm.py 收敛，这里是真 bug
                    # 兜底）：按未完成收场——部分正文保留、claim 记 incomplete，
                    # 不让异常逃出流、把 claim 卡在 generating。
                    logger.exception(
                        "agent_chat_stream 模型流意外异常（session=%s）", session_id)
                    interrupt_reason = interrupt_reason or "generation_error"
            timing.mark("llm_end")

            _INCOMPLETE_CN = {
                "connection_interrupted": "连接中断",
                "no_completion_marker": "连接提前关闭（未收到正常结束标记）",
                "server_error_event": "模型服务返回错误事件",
                "max_tokens_truncated": "输出额度截断",
                "generation_error": "生成过程出现异常",
            }
            interrupted = bool(interrupt_reason)
            full = "".join(pieces).strip()
            # 确定性作答自带 grounded（系统数据直出）；模型路径仍须过校验。
            grounded = det_reply is not None and bool(full) and not interrupted
            verify_note = ""
            fallback = ""
            if interrupted:
                reason_cn = _INCOMPLETE_CN.get(interrupt_reason, interrupt_reason)
                if full:
                    # 有部分正文：保留已收到内容，如实标记解释未完成；不再叠加完整模板
                    grounded = False
                    verify_note = (
                        f"AI 讲解未完成（{reason_cn}）；以上是已收到的部分，"
                        "上方系统资料仍然可用。可重试同一问题重新生成"
                        "（不会重复记录）。"
                    )
                else:
                    verify_note = f"AI 讲解未完成（{reason_cn}），系统改用模板直出。"
            if full and not interrupted and det_reply is None:
                from lei_signal.plans.grounding import (  # noqa: PLC0415
                    collect_payload_numbers,
                    verify_numeric_grounding,
                )

                allowed_nums = (
                    collect_payload_numbers(ctx_payload)
                    | frozenset(extract_market_numbers(body.message))
                    | frozenset(_payload_symbol_numbers(ctx_payload))
                    | frozenset(_history_symbol_numbers(history_rows))
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
            if (not full or not grounded) and not (interrupted and full):
                fallback = _degraded_reply(symbol or "", ctx_payload)

            trace = _build_trace(alerts)
            meta: dict = {"trace": [t.model_dump() for t in trace]}
            if symbol is not None:
                meta["resolved_symbol"] = symbol
            # 契约3：同一证据产物进历史（r6：流式路径同样持久化，恢复不依赖模型复述）
            if ctx_payload.get("evidence_card") is not None:
                meta["evidence_card"] = ctx_payload["evidence_card"]
            # 03B-R3 S5：服务端计划产物随流式回答持久化/下发
            if ctx_payload.get("plan_artifact") is not None:
                meta["plan_artifact"] = ctx_payload["plan_artifact"]
            # UX 第一期：下一步动作随流式回答持久化/下发（与 prepared 同一份）
            if next_steps:
                meta["next_steps"] = next_steps
            if interrupted:
                # 补修二：未完成原因进持久化 meta（历史/恢复可区分未完成与其他）
                meta["answer_incomplete"] = {
                    "reason": interrupt_reason,
                    "reason_cn": _INCOMPLETE_CN.get(interrupt_reason, interrupt_reason),
                }
            try:
                with closing(connect(_db_path(request))) as conn:
                    # S4：流式完成回答同样按 question_id 精确绑定（列+claim 状态）；
                    # interrupted 时 claim 记 incomplete（重试重新生成，不回放半截话）
                    _append_answer(
                        conn, session_id=session_id, question_id=question_id,
                        content=full or fallback, grounded=grounded, meta=meta,
                        claim_cid=outcome.claim_cid, incomplete=interrupted,
                        source_request_id=outcome.claim_cid or "")
            except Exception:  # noqa: BLE001
                # 保存失败不谎报已回答：如实说「回答已生成但未能写入历史」，
                # 释放生成权——同身份重试立即对原问题重新生成（不重复记录）。
                logger.exception(
                    "agent_chat_stream 回答落库失败（session=%s）", session_id)
                yield _sse("done", _fail_payload(
                    "本次回答已生成但未能写入历史记录"
                    "（系统数据库暂时不可用）。以上内容本次有效；"
                    "需要留档可点「重试」对同一问题重新生成，不会重复记录。",
                    out=outcome, session_id=session_id, symbol=symbol))
                _mark_terminal()
                return
            timing.mark("answer_saved")
            yield _sse(
                "done",
                {
                    "session_id": session_id,
                    "resolved_symbol": symbol,
                    "grounded": grounded,
                    "question_id": question_id,
                    "evidence_card": ctx_payload.get("evidence_card"),
                    "plan_artifact": ctx_payload.get("plan_artifact"),
                    "answer_state": "incomplete" if interrupted else "answered",
                    "next_steps": next_steps,
                    "timing_ms": timing.summary(),
                    **({"verify_note": verify_note} if verify_note else {}),
                    **({"fallback": fallback} if fallback else {}),
                    **({"quick_card": _quick_card(ctx_payload, symbol)} if symbol else {}),
                },
            )
            _log_timing("stream", session_id, symbol)
            _mark_terminal()
        finally:
            # S1：消费者退出（断连/停止/异常）一律标记取消——工作者晚领号
            # 时据此收尾；未达终态且生成权已领则放回 pending（CAS 只放自己
            # 的领取，重试者的新领取不受影响）。
            with shared.lock:
                shared.cancelled = True
                _out = shared.outcome
                _term = shared.terminal
            if not _term:
                _release_claim(_out)
                _log_timing("stream_aborted",
                            _out.session_id if _out else None, None)

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
