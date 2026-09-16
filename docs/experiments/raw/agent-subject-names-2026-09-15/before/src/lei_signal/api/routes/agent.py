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
    r"(?<![A-Za-z0-9.])(?:TH\d{6}|SW\d{4}|BK\d{4}|\d{6})(?:\.(?:SS|SZ))?(?![A-Za-z0-9])"
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
        try:
            info = resolve_symbol(tok)
        except ValueError:
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
    name = str(db_name or "").strip()
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
_CATALOG_ALIAS: dict[str, str] = {
    "科创": "000688.SS",
    "科创板": "000688.SS",
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


def _inherit_session_facts(conn, session_id: str | None, parsed: dict) -> dict:
    """契约3：预算/用途沿会话真实继承——本轮没说的，取本会话最近一次明确
    说法（记录来源问题号），不每轮丢弃、也不每轮重复问。"""
    inherited: dict = {}
    if session_id is None:
        return inherited
    rows = conn.execute(
        "SELECT message_id, meta_json FROM agent_messages "
        "WHERE session_id = ? AND role = 'user' AND meta_json LIKE '%discussion_v1%' "
        "ORDER BY message_id DESC LIMIT 20",
        (session_id,)).fetchall()
    for r in rows:
        try:
            snap = (json.loads(r["meta_json"] or "{}") or {}).get("discussion_v1") or {}
        except json.JSONDecodeError:
            continue
        if not inherited.get("budget") and parsed.get("budget") is None \
                and snap.get("budget"):
            inherited["budget"] = {**snap["budget"],
                                   "inherited_from_question": r["message_id"]}
        if not inherited.get("purpose") and (parsed.get("purpose") in (None, "unknown")) \
                and snap.get("purpose") not in (None, "unknown"):
            inherited["purpose"] = snap["purpose"]
            inherited["purpose_source_question"] = r["message_id"]
    return inherited


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
            source_id="analysis_service(compose.pipeline)",
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
    inherited = _inherit_session_facts(conn, session_id, parsed)
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
    budget = parsed.get("budget") or inherited.get("budget")
    purpose = parsed.get("purpose")
    if purpose in (None, "unknown"):
        purpose = inherited.get("purpose") or parsed.get("purpose")
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

    # ① 先回答这次问题：第一句就是大白话结论（只重组既有判定字段，
    # 不做新判定；候选状态/价位照抄，不加解释性定语）。
    if candidates:
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
        lines.append(
            f"数据日 {as_of}。AI 讲解暂时不可用，以下是系统直接给出的数据事实。"
        )

    # 系统标签（颜色/阶段/风险）是细节，不再当第一句。
    lines.append(
        f"系统状态：{a.get('color_cn', '状态未知')} / {a.get('stage_cn', '-')}"
        f" / 风险关注 {a.get('risk_state_cn', '-')}。"
    )

    # ③ 机会与风险：有候选列候选（阻断原因已进第一句，不重复）。
    if candidates:
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
    if not symbol:
        return []
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
        blocks["mindset"] = {
            "available": False,
            "note_cn": "心态内容只在用户求助时按其认可且兼容的一条引用，不当规则",
        }
    elif topic == "money":
        blocks["money"] = {
            "purpose_needed": True,
            "note_cn": "资金用途需用户明确：持续新收入/已有闲钱/技术交易；"
                       "不跨用途借成绩，不代估预算",
        }
    return blocks


def _prepare_discussion(
    request: Request, body: AgentChatRequest, on_stage=None,
    session_id: str | None = None,
    resume_question_id: int | None = None,
) -> tuple[str, list, dict, list, str | None]:
    """agent_chat 与流式版共用的准备段（一个连接内完成）。

    03B-R2 契约1：会话由统一事务入口（enter_chat_request）先行裁决——本函数
    只按给定 session_id 组装材料，不再自行创建会话（重试/冲突在准备之前处理）。

    返回 (session_id, history_rows, ctx_payload, alerts, symbol)。
    阶段回调 ``on_stage``（可选）用于流式路径向 UI 报告调用链进度。
    """
    with closing(connect(_db_path(request))) as conn:
        session = get_session(conn, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")
        history_rows = list_messages(conn, session.session_id, limit=20)

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
        if symbol is None:
            from lei_signal.api.watchlist import list_watchlist  # noqa: PLC0415

            symbol = _resolve_symbol_by_name(body.message, list_watchlist(conn))
        if symbol is not None:
            subject_source = "message"
        if symbol is None and explicit:
            symbol = body.symbol
            subject_source = "selected"
        if symbol is None:
            symbol = _last_resolved_symbol(history_rows)
            if symbol is not None:
                subject_source = "session"
        if symbol is not None and service is not None and on_stage:
            on_stage("fetch", f"拉取 {symbol} 行情（首次约 1 分钟）")
        if symbol is not None and service is not None:
            entry = service.get(symbol)
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
        # R3（03B-R1）：按主题装载既有适配器数据（DCA/情绪/证据/心态/资金），
        # 两个路径（有标的/全局）都消费；目录说明不代替实际数据。
        from lei_signal.copilot import resolve as resolve_mod

        parsed_topic = resolve_mod.parse_request(body.message)["topic"]
        ctx_payload.update(_topic_blocks(parsed_topic, symbol))
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

    outcome = _enter_chat(request, body)
    if outcome.kind == "replay":
        return _reply_from_payload(outcome.replay_reply or {})
    if outcome.kind == "incomplete":
        # S4：同一问题未生成回答时的**明确未完成**出口（服务端状态约束，
        # 不复用下一问题/补测卡，也不产生第二个问题）
        return _reply_from_payload(outcome.incomplete_reply or {})

    resume = outcome.kind == "resume"
    (session_id, history_rows, ctx_payload, alerts, symbol,
     window_sel) = _prepare_discussion(
        request, body, session_id=outcome.session_id,
        resume_question_id=outcome.question_id if resume else None,
    )
    question_id: int | None = outcome.question_id if resume else None
    if not resume:
        # 03B：先落 user 消息 + discussion_v1 快照（回测绑定需要 question_id）；
        # 并发双发在写事务内收口：输家直接复用赢家的原问题，不产生第二个问题
        with closing(connect(_db_path(request))) as conn:
            appended, user_msg, dup = _append_user_for_claim(
                conn, outcome, body, symbol,
                review_dump=ctx_payload.get("buy_point_review"),
                as_of=ctx_payload.get("as_of"), window_sel=window_sel)
            question_id = user_msg.message_id if user_msg is not None else None
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
    with closing(connect(_db_path(request))) as conn:
        _append_answer(conn, session_id=session_id, question_id=question_id,
                       content=reply, grounded=grounded, meta=meta,
                       claim_cid=outcome.claim_cid,
                       source_request_id=outcome.claim_cid or "")
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
                # 契约1：统一事务入口在准备/建模之前裁决（重试复用/409/
                # 未完成/恢复）
                outcome = _enter_chat(request, body)
                q.put(("entered", outcome))
                if outcome.kind in ("proceed", "resume"):
                    q.put((
                        "prepared",
                        _prepare_discussion(
                            request, body, on_stage=on_stage,
                            session_id=outcome.session_id,
                            resume_question_id=outcome.question_id
                            if outcome.kind == "resume" else None),
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

        prepared = None
        outcome = None
        while True:
            try:
                kind, payload = q.get(timeout=180)
            except _queue.Empty:
                logger.warning(
                    "agent_chat_stream 准备段超时180s（session=%s message=%r）",
                    body.session_id, body.message[:50],
                )
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
            elif kind == "entered":
                outcome = payload
                if outcome.kind == "replay":
                    p = outcome.replay_reply or {}
                    yield _sse("token", {"t": p.get("reply") or ""})
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
                    })
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
                    })
                    return
            else:
                prepared = payload
                break

        (session_id, history_rows, ctx_payload, alerts, symbol,
         window_sel) = prepared
        resume = outcome.kind == "resume"
        question_id: int | None = outcome.question_id if resume else None

        # 可靠性一期（2026-09-14）：系统资料就绪即推送，不等模型。字段与
        # done 同名同源（不是第二套证据），前端据此先渲染事实卡并提示
        # 「资料已就绪，AI 解释仍在生成」；done 仍是唯一的最终完成信号。
        yield _sse("prepared", {
            "session_id": session_id,
            "resolved_symbol": symbol,
            "quick_card": _quick_card(ctx_payload, symbol),
            "evidence_card": ctx_payload.get("evidence_card"),
            "next_steps": _build_next_steps(ctx_payload, symbol),
        })

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
                # 落库失败不假装开始回答：资料已展示，如实说明历史没存上，
                # 重试同一问题走既有 replay/resume 身份（不重复建问题）。
                logger.exception(
                    "agent_chat_stream 问题落库失败（session=%s）", session_id)
                yield _sse("done", {
                    "session_id": session_id,
                    "resolved_symbol": symbol,
                    "grounded": False,
                    "verify_note": (
                        "系统资料已在上方展示；但本次问题未能写入历史记录"
                        f"（{type(exc).__name__}），AI 解释没有开始。"
                        "请稍后重试同一问题。"
                    ),
                })
                return
            if appended == "duplicate":
                dup = dup or {}
                yield _sse("done", {
                    "session_id": dup.get("session_id") or session_id,
                    "resolved_symbol": dup.get("resolved_symbol"),
                    "grounded": bool(dup.get("grounded")),
                    "question_id": dup.get("question_id"),
                    "evidence_card": dup.get("evidence_card"),
                    "replayed": True,
                })
                return

        # 03B-R3 S5：整理计划类问题生成服务端产物（原问题绑定）
        _maybe_plan_artifact(request, session_id, question_id, body, symbol,
                             ctx_payload)

        config = plans_llm.load_ark_config()
        pieces: list[str] = []
        interrupt_reason = ""
        if config is not None:
            yield _sse("stage", {"key": "llm", "text": "AI 组织语言（逐字输出）"})
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
                pieces.append(piece)
                yield _sse("token", {"t": piece})

        _INCOMPLETE_CN = {
            "connection_interrupted": "连接中断",
            "no_completion_marker": "连接提前关闭（未收到正常结束标记）",
            "server_error_event": "模型服务返回错误事件",
            "max_tokens_truncated": "输出额度截断",
        }
        interrupted = bool(interrupt_reason)
        full = "".join(pieces).strip()
        grounded = False
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
        if full and not interrupted:
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
        # UX 第一期：下一步动作随流式回答持久化/下发（与普通路径同一函数）
        next_steps = _build_next_steps(ctx_payload, symbol)
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
        except Exception:  # noqa: BLE001  落库失败不断流（锁窗口下次再试不可行，丢历史可接受）
            yield _sse(
                "done", {"session_id": session_id, "resolved_symbol": symbol,
                         "grounded": grounded,
                         "answer_state": "incomplete" if interrupted else "answered",
                         "verify_note": "会话记录保存失败（不影响本次回复）",
                         "fallback": fallback})
            return
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
