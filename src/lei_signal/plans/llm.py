"""ark LLM 渲染器（表达层唯一的 LLM 接入点）。

职责边界：**只把判定层已产出的 alert 讲成人话**。不判定、不推算日期、不引新数值。
输出必须过 ``grounding.verify_grounding``（rule_id 白名单 + 禁用词），两次不过降级模板。

上下文裁剪（规格 §7.2）：只喂四块，其余 DTO 字段一律不给--给了它就会引用，
引用了就要校验，不如不给。目标 < 8k tokens。

凭据缺失、网络失败、超时一律**返回 None**（不抛异常）：投递与讲解是 best-effort，
监督链不能因 LLM 不可用而断。``render_alerts`` 会自动降级为模板直出。
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import requests

from lei_signal.plans.models import ActionItem, PlanAlert, TradePlan

logger = logging.getLogger(__name__)

#: ark 默认端点与模型。凭据只走环境变量，绝不硬编码。
DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
ENV_API_KEY = "ARK_API_KEY"
ENV_BASE_URL = "ARK_BASE_URL"
ENV_MODEL = "ARK_MODEL"
ENV_MAX_TOKENS = "ARK_MAX_TOKENS"
ENV_TIMEOUT = "ARK_TIMEOUT"

#: DeepSeek 端点与模型（OpenAI 兼容协议，Bearer 鉴权）。
#: 优先级高于 ARK_* / ANTHROPIC_*：配了 DEEPSEEK_API_KEY 就走 DS。
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"
ENV_DEEPSEEK_API_KEY = "DEEPSEEK_API_KEY"
ENV_DEEPSEEK_BASE_URL = "DEEPSEEK_BASE_URL"
ENV_DEEPSEEK_MODEL = "DEEPSEEK_MODEL"

#: 协议风格。ark 有两种网关：
#:   openai    -> POST {base}/chat/completions，Bearer 鉴权（/api/v3）
#:   anthropic -> POST {base}/v1/messages，x-api-key 鉴权（/api/coding）
STYLE_OPENAI = "openai"
STYLE_ANTHROPIC = "anthropic"
ENV_STYLE = "ARK_API_STYLE"

#: 表达层系统提示：把红线写成 LLM 可执行的约束。
SYSTEM_PROMPT = """你是 LEI 交易系统的纪律监督员的**表达层**。

你的唯一职责：把下面给定的 alert（已由确定性 Python 判定层算出）讲成简洁中文。

铁律（违反即输出被丢弃）：
1. 只能引用给定 alert 里出现过的 rule_id。禁止编造 rule_id。
2. 禁止出现这些词：买入、卖出、建议买、该买、加仓、减仓、抄底。
   用「参考」「提醒」「阻断原因」「可执行日」等中性表述。
3. 不得推算任何日期。日期只能照抄给定的 actionable_from / data_as_of。
4. 不得引入给定数据之外的数值。证据数值必须照抄 evidence。
5. 标注规则（每条 alert 都要写，不可省）：
   - 有 principle_source 时：写「{principle_source} | 判定方式为研究代理」
   - 无 principle_source 但 logic_provenance 是 research_proxy 时：写「判定方式为研究代理」
   这是溯源纪律，漏写等于把研究代理冒充成原始规则。
6. 不输出总分、不输出评级、不预测价格。
7. next_step 必须照抄给定的 next_step_cn，不得自创。待办的「要做什么」也照抄
   action_items 里的 next_step_cn，不要自己造措辞。
8. **阻断优先**：存在 severity=block 的 alert 时，先讲阻断，并明确「按规则本轮不开新仓」。
   此时即使同时存在入场条件成立的提醒，也必须说明它被阻断条件压制，不得让两者并列
   显得可以入场。severity=hint 的提示（如盈亏比不足）不构成阻断。

输出格式（严格遵守，不要额外寒暄）：
【计划】{symbol} 模块{module} · {entry_rule_id} · 状态 {state} · 有效期至 {valid_until}
【数据】{data_as_of}{陈旧警示}

▶ 待办（催办第 N 次）
  {kind}：{照抄 action_items 的 next_step_cn}
  可执行日：{due_from}
  → 你可以：标记已执行 / 推迟（需说明原因）

■ 阻断 / ■ 提醒 / □ 提示
  {人话说明}
  [rule_id:{rule_id} | 证据:{evidence 键值}]
  {按铁律 5 写标注}

【下一步观察】{照抄 next_step_cn；多条时分行列出}
"""


#: 买点分析系统提示。比监督员更严：连「可能构成买点」的措辞也必须引 review 的字段，
#: 不得自行从行情推断。止损只能引 invalidation_price；盈亏比只能照抄 ratio。
BUY_POINT_SYSTEM_PROMPT = """你是 LEI 交易系统的买点分析表达层。

你拿到的是一份**已经由确定性 Python 判定层算好**的买点审阅（buy-point-review）。
你的职责：把它讲成简洁中文，帮用户理解**当前是否构成系统定义的买点、图什么信号、
关键位在哪、什么时候才触发**。

**场景边界——这一段是用户最痛的混淆**：
- 买点分析 = 信号发现阶段：回答「哪个位置、什么结构、需不需要现在行动」
- 落计划/止损/R/R = 执行阶段：等用户真要下单时再讲
- 所以本场景下：**不要展开止损价、不要算盈亏比、不要给目标价**。
  最多在文末用一句话提示「止损/盈亏比/五项假设需在落计划时人工确认」
  然后收住，不在每个买点里重复讲。

铁律（违反即输出被丢弃）：
1. **不得自行判断买点**。买点结论只能来自 review 的 candidates 字段
   （satisfied_conditions / missing_conditions / state）。不得从行情自行推断。
2. 禁止出现这些词：买入、卖出、建议买、该买、加仓、减仓、抄底。
   用「参考」「条件成立」「可执行日」「系统定义的买点」等中性表述。
3. **不得推算任何价位**。关键价只能照抄 candidates 的 key_price；
   watch_conditions 里价位型条件照抄 price，状态型条件（如多头排列未成立）
   不得贴数字。不得预测何时到达。
4. **止损与盈亏比在买点分析中不展开**。每个候选里不要写「止损 xx」「R/R 不可
   计算」这种重复噪音；统一在文末提一次「落计划时需人工确认止损与盈亏比」即可。
   若用户明确问「止损怎么设」/「盈亏比多少」，可以照抄 invalidation_price（如为
   None 则明说「系统未给出，建计划时人工确认」）和 reward_risk_ratio。
5. 不得推算日期。可执行日只能照抄 actionable_from / as_of。
6. research_proxy 标注：场景/可交易性/盈亏比均为研究代理，必须写「判定方式为研究代理」。
7. 不输出总分、不输出评级、不预测价格走势。
8. verdict=blocked 时必须先讲阻断（规格 §13），明确「按规则不开新仓」。
9. 落计划只能提议，不得替用户决定。五项交易假设必须由人写。
10. **引用候选用序号**：只细讲 state=confirmed / watch 的候选（跳过 weakened
    确认减弱的，那类只需一句带过「其余 N 个为确认减弱」），并按它们在 candidates
    数组中的出现顺序称「买点①、买点②、买点③…」（用圆圈数字 ①②③），便于前端在
    图上定位高亮。讲到某个买点时只点明**依据结构 + 关键价 + 触发状态**，不要带
    止损。不要用「第一个买点」这类无序号写法。
11. **输出长度控制**：每个候选 3-5 行即可（依据结构 / 关键价 / 状态 / 触发条件），
    不要在聊天里复述全部 missing_conditions / invalidation_cn 长文本。
    全文不超过 1500 字，除非用户明确要细节。
12. **数字关联（沟通纪律）**——用户问题里出现具体数字时的强制动作：
    用户带数字提问（"8700 是不是更好""我把止损放在 7600"等），说明他在用视觉或
    个人判断对照系统结论。**禁止机械回答"X 不在范围内"，必须先在 review payload
    里主动检索最接近的已知位并连接**：
    - 检索字段：candidates[].key_price（关键价）、reward_risk_target（目标参考）、
      satisfied_conditions / missing_conditions / invalidation_cn / next_step_cn /
      caveat_cn 这些**含数字的文本字段**（结构类规则的 L1/L2/密集区上下沿经常藏在
      文本里，照样要算偏差）、watch_conditions[].price。
    - 偏差 ≤ 5%：**主动连接**——「你说的 X 跟 Y（候选 N 的 key_price / 含数字字段）
      接近，偏差 ~W%，系统里对应的是 Y」。必须用具体百分比，不能含糊。
    - 偏差 5%–15%：说明偏差，并指出最近的对应位是什么。
    - 偏差 > 15% 或无接近位：说明 review 里没在 X 附近的已知位；并解释系统为什么
      不收 X（例如"系统跟踪的是结构位和滚动区间，不跟踪视觉的支撑压力线"）。
    - 不得为了凑关联编造偏差；找不到就老实说没有。
    这是「沟通纪律」而非「判定权」：只把 review 已有数字跟用户数字做差，不引入新价位。
13. **对话聚焦**：用户已看过 review（这是 review 上的对话，不是首次打开），按
    "回答问题"的格式而不是 "复述 review"的格式：
    - 用户问哪个候选 / 哪个数字，就只讲那个；不要重贴全部 candidates。
    - 不要重贴 verdict 阻断全文（用户已知道环境阻断，除非他追问）。
    - 不要重复列 "其余 N 个候选为确认减弱" 之类的兜底。
    - 长度看问题规模：单点问题 5-10 行即可，全量复述仅在用户明确说"重新过一遍"时。
    - 文末免责声明仍可保留一句。
"""


@dataclass(frozen=True, slots=True)
class ArkConfig:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    model: str = "ark-code-latest"
    #: 请求超时（秒）。多候选大 payload 生成耗时长，30s 易在 thinking 阶段超时。
    #: 可用 ARK_TIMEOUT 覆盖。
    timeout: float = 90.0
    style: str = STYLE_OPENAI
    #: 输出 token 上限（thinking+text 共享）。推理模型先 thinking，1500 会被
    #: 34 候选大 payload 的 thinking 占满、不产出 text block -> 误降级。可用
    #: ARK_MAX_TOKENS 覆盖。
    max_tokens: int = 6000
    #: 429/5xx 的退避重试次数。监督员与其他工具共用同一 key 时会撞限频，
    #: 但投递是 best-effort：重试用尽仍失败即返回 None，由调用方降级模板。
    retry_on_throttle: int = 2
    retry_backoff_seconds: float = 2.0


def _infer_style(base_url: str) -> str:
    """按网关路径推断协议风格。/api/coding 是 Anthropic 兼容，/api/v3 是 OpenAI 兼容。"""
    return STYLE_ANTHROPIC if "/coding" in base_url else STYLE_OPENAI


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("环境变量 %s=%r 非整数，用默认 %d", name, raw, default)
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("环境变量 %s=%r 非浮点，用默认 %s", name, raw, default)
        return default


def load_ark_config() -> ArkConfig | None:
    """从环境变量读表达层 LLM 配置。缺 API key 时返回 None（调用方降级模板）。

    优先级：
    1. ``DEEPSEEK_API_KEY`` -> DeepSeek（OpenAI 兼容，Bearer，默认 deepseek-chat）；
    2. ``ARK_*``；
    3. ``ANTHROPIC_*``（本机 Claude Code 用的就是 ark 的 /api/coding 网关，
       复用同一凭据避免重复配置）。

    max_tokens / timeout 可用 ARK_MAX_TOKENS / ARK_TIMEOUT 覆盖默认值。
    """
    max_tokens = _env_int(ENV_MAX_TOKENS, 6000)
    timeout = _env_float(ENV_TIMEOUT, 90.0)

    # DeepSeek 优先：配了就走 DS，不再回退 ark（避免两套凭据同时存在时行为不确定）。
    ds_key = os.environ.get(ENV_DEEPSEEK_API_KEY, "").strip()
    if ds_key:
        ds_base = (
            os.environ.get(ENV_DEEPSEEK_BASE_URL, "").strip() or DEEPSEEK_BASE_URL
        ).rstrip("/")
        return ArkConfig(
            api_key=ds_key,
            base_url=ds_base,
            model=os.environ.get(ENV_DEEPSEEK_MODEL, "").strip() or DEEPSEEK_MODEL,
            style=STYLE_OPENAI,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    api_key = os.environ.get(ENV_API_KEY, "").strip()
    base_url = os.environ.get(ENV_BASE_URL, "").strip()
    model = os.environ.get(ENV_MODEL, "").strip()
    if not api_key:
        api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN", "").strip()
        base_url = base_url or os.environ.get("ANTHROPIC_BASE_URL", "").strip()
        model = model or os.environ.get("ANTHROPIC_MODEL", "").strip()
    if not api_key:
        return None
    base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
    style = os.environ.get(ENV_STYLE, "").strip() or _infer_style(base_url)
    return ArkConfig(
        api_key=api_key,
        base_url=base_url,
        model=model or "ark-code-latest",
        style=style,
        max_tokens=max_tokens,
        timeout=timeout,
    )


def build_context_payload(
    alerts: list[PlanAlert],
    *,
    plan: TradePlan | None = None,
    action_items: list[ActionItem] | None = None,
    context_min: dict[str, Any] | None = None,
    frozen_playbook: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """按规格 §7.2 裁剪上下文：只喂 plan / alerts / action_items / context_min 四块。

    不喂：chart、concepts、全部 backtest、recent_events 全量。
    """
    payload: dict[str, Any] = {
        "alerts": [
            {
                "code": a.code,
                "severity": a.severity,
                "rule_id": a.rule_id,
                "evidence": a.evidence,
                "principle_source": a.principle_source,
                "logic_provenance": a.logic_provenance,
                "caveat_cn": a.caveat_cn,
                "actionable_from": a.actionable_from,
                "data_as_of": a.data_as_of,
                "next_step_cn": a.next_step_cn,
                "action_kind": a.action_kind,
            }
            for a in alerts
        ],
    }
    if plan is not None:
        payload["plan"] = {
            "plan_id": plan.plan_id,
            "symbol": plan.symbol,
            "module": plan.module,
            "direction": plan.direction,
            "entry_rule_id": plan.entry_rule_id,
            "state": plan.state,
            "valid_until": plan.valid_until,
            "invalidation_price": plan.invalidation_price,
            "target_b_price": plan.target_b_price,
        }
        # 冻结预案（revision_no=0）只在复议场景摆出作对照原文
        if frozen_playbook:
            payload["frozen_playbook"] = frozen_playbook
    if action_items:
        # 待办要带上对应 alert 的 next_step_cn，否则 LLM 只能干巴巴造一句
        # 「执行入场类对应操作」--照抄判定层文案才是接地生成。
        next_step_by_code = {
            a.code: a.next_step_cn for a in alerts if a.next_step_cn
        }
        payload["action_items"] = [
            {
                "kind": i.kind,
                "state": i.state,
                "due_from": i.due_from,
                "nag_count": i.nag_count,
                "source_alert_code": i.source_alert_code,
                "next_step_cn": next_step_by_code.get(i.source_alert_code, ""),
            }
            for i in action_items
            if i.state == "open"
        ]
    if context_min:
        payload["context_min"] = context_min
    return payload


def _user_content(prompt_payload: dict[str, Any]) -> str:
    return (
        "把下面的监督结果讲成人话，严格遵守输出格式与铁律：\n"
        + json.dumps(prompt_payload, ensure_ascii=False, indent=2)
    )


def _extract_openai(data: dict[str, Any]) -> str | None:
    choices = data.get("choices") or []
    if not choices:
        return None
    content = choices[0].get("message", {}).get("content")
    return str(content) if content else None


def _extract_anthropic(data: dict[str, Any]) -> str | None:
    """取 content 里的 text block；跳过 thinking block（推理模型会先输出思考）。"""
    blocks = data.get("content") or []
    texts = [
        str(b.get("text", ""))
        for b in blocks
        if isinstance(b, dict) and b.get("type") == "text" and b.get("text")
    ]
    joined = "\n".join(texts).strip()
    return joined or None


def _post_user_content(
    user_content: str,
    config: ArkConfig,
    *,
    system_prompt: str = SYSTEM_PROMPT,
) -> str | None:
    """发单轮 user 消息到 ark（system 可换）。

    call_ark / chat_ark / chat_buy_point 共用此底层：双协议、退避重试、
    thinking/text 抽取。任何失败返回 None（调用方降级）。
    """
    if config.style == STYLE_ANTHROPIC:
        url = f"{config.base_url}/v1/messages"
        headers = {
            "x-api-key": config.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {
            "model": config.model,
            "max_tokens": config.max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_content}],
        }
        extract = _extract_anthropic
    else:
        url = f"{config.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.2,
        }
        extract = _extract_openai

    try:
        for attempt in range(config.retry_on_throttle + 1):
            resp = requests.post(url, headers=headers, json=body, timeout=config.timeout)
            if resp.status_code == 200:
                text = extract(resp.json())
                if text is None:
                    # 200 但取不到 text：推理模型 thinking 占满 max_tokens、未产出
                    # text block 是典型原因。此前静默 None 会误判为「LLM 不可用」。
                    logger.warning(
                        "ark 返回 200 但无 text block 可抽取（疑似 thinking 占满 "
                        "max_tokens=%s，model=%s）；降级模板。",
                        config.max_tokens,
                        config.model,
                    )
                return text
            # 429 限频 / 5xx 瞬时故障：退避重试；其他状态码直接放弃
            throttled = resp.status_code == 429 or resp.status_code >= 500
            if throttled and attempt < config.retry_on_throttle:
                logger.info(
                    "ark HTTP %s，第 %d/%d 次退避重试（model=%s）",
                    resp.status_code,
                    attempt + 1,
                    config.retry_on_throttle,
                    config.model,
                )
                time.sleep(config.retry_backoff_seconds * (2**attempt))
                continue
            logger.warning(
                "ark HTTP %s，放弃（model=%s）。响应摘要：%s",
                resp.status_code,
                config.model,
                getattr(resp, "text", "")[:200],
            )
            return None
        logger.warning(
            "ark 退避重试 %d 次仍失败（model=%s）",
            config.retry_on_throttle + 1,
            config.model,
        )
        return None
    except (requests.RequestException, ValueError, KeyError, IndexError) as exc:
        logger.warning(
            "ark 调用异常：%s: %s（model=%s）",
            type(exc).__name__,
            exc,
            config.model,
        )
        return None


def call_ark(prompt_payload: dict[str, Any], config: ArkConfig) -> str | None:
    """调 ark 把监督结果讲成人话。支持 OpenAI 兼容与 Anthropic 兼容两种网关。

    任何失败返回 None（调用方降级）。
    """
    return _post_user_content(_user_content(prompt_payload), config)


def chat_ark(
    prompt_payload: dict[str, Any], user_message: str, config: ArkConfig
) -> str | None:
    """接地问答：把监督上下文 + 用户问题一起喂给 ark，返回回复。失败返回 None。

    与 call_ark 同一套 SYSTEM_PROMPT（接地铁律）；投递走 ``_request_completion``
    （与 ``_post_user_content`` 同构的双协议底层）。回复仍须由调用方过
    ``verify_grounding``（禁用词 + rule_id 白名单），
    不过则降级模板--判定权始终在 Python，LLM 只表达。
    """
    content = (
        "以下是当前监督结果（只许引用其中出现过的 rule_id 与 evidence 数值，"
        "不得编造 rule_id、不得推算日期、不得引入给定外的数值）：\n"
        + json.dumps(prompt_payload, ensure_ascii=False, indent=2)
        + f"\n\n用户问题：{user_message}"
    )
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": content},
    ]
    return _request_completion(config, messages)


def chat_buy_point(
    review_payload: dict[str, Any], user_message: str, config: ArkConfig
) -> str | None:
    """买点分析问答。用 BUY_POINT_SYSTEM_PROMPT（比监督员更严：禁自行判断买点、
    禁推算价位）。回复仍须由调用方过 verify_grounding，不过则降级。

    review_payload 是 BuyPointReviewDTO 序列化后的 dict（只含确定性字段）。
    """
    content = (
        "以下是买点审阅结果（已由确定性判定层算好，只许引用其中字段，"
        "不得自行判断买点、不得推算 review 未给出的价位或盈亏比）：\n"
        + json.dumps(review_payload, ensure_ascii=False, indent=2)
        + f"\n\n用户问题：{user_message}"
    )
    return _post_user_content(content, config, system_prompt=BUY_POINT_SYSTEM_PROMPT)


def _request_completion(config: ArkConfig, messages: list[dict]) -> str | None:
    """完整 messages 列表的统一请求：双协议、退避重试、text 抽取。

    与 ``_post_user_content`` 同构（chat_ark 历史上走的就是那条路径），区别仅在
    入参是完整 messages 列表而非单条 user 内容，供多轮对话复用：

    - OpenAI 风格：messages 原样透传（含 system 角色）。
    - Anthropic 风格：/v1/messages 不收 messages 内的 system 角色，把首条
      system 消息提为顶层 ``system`` 字段，其余原样投递。

    chat_ark 与 chat_discussion 共用此底层。任何失败返回 None（调用方降级）。
    """
    if config.style == STYLE_ANTHROPIC:
        url = f"{config.base_url}/v1/messages"
        headers = {
            "x-api-key": config.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        conversation = list(messages)
        system_prompt: str | None = None
        if conversation and conversation[0].get("role") == "system":
            system_prompt = str(conversation[0].get("content", ""))
            conversation = conversation[1:]
        body: dict[str, Any] = {
            "model": config.model,
            "max_tokens": config.max_tokens,
        }
        if system_prompt is not None:
            body["system"] = system_prompt
        body["messages"] = conversation
        extract = _extract_anthropic
    else:
        url = f"{config.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": config.model,
            "messages": messages,
            "temperature": 0.2,
        }
        extract = _extract_openai

    try:
        for attempt in range(config.retry_on_throttle + 1):
            resp = requests.post(url, headers=headers, json=body, timeout=config.timeout)
            if resp.status_code == 200:
                text = extract(resp.json())
                if text is None:
                    # 200 但取不到 text：推理模型 thinking 占满 max_tokens、未产出
                    # text block 是典型原因。此前静默 None 会误判为「LLM 不可用」。
                    logger.warning(
                        "ark 返回 200 但无 text block 可抽取（疑似 thinking 占满 "
                        "max_tokens=%s，model=%s）；降级模板。",
                        config.max_tokens,
                        config.model,
                    )
                return text
            # 429 限频 / 5xx 瞬时故障：退避重试；其他状态码直接放弃
            throttled = resp.status_code == 429 or resp.status_code >= 500
            if throttled and attempt < config.retry_on_throttle:
                logger.info(
                    "ark HTTP %s，第 %d/%d 次退避重试（model=%s）",
                    resp.status_code,
                    attempt + 1,
                    config.retry_on_throttle,
                    config.model,
                )
                time.sleep(config.retry_backoff_seconds * (2**attempt))
                continue
            logger.warning(
                "ark HTTP %s，放弃（model=%s）。响应摘要：%s",
                resp.status_code,
                config.model,
                getattr(resp, "text", "")[:200],
            )
            return None
        logger.warning(
            "ark 退避重试 %d 次仍失败（model=%s）",
            config.retry_on_throttle + 1,
            config.model,
        )
        return None
    except (requests.RequestException, ValueError, KeyError, IndexError) as exc:
        logger.warning(
            "ark 调用异常：%s: %s（model=%s）",
            type(exc).__name__,
            exc,
            config.model,
        )
        return None


def make_ark_renderer(
    *,
    plan: TradePlan | None = None,
    action_items: list[ActionItem] | None = None,
    frozen_playbook: dict[str, Any] | None = None,
    config: ArkConfig | None = None,
):
    """构造可传给 ``grounding.render_alerts(llm_render=...)`` 的渲染函数。

    无凭据时返回 None，调用方据此直接走模板（不做无意义的失败重试）。
    """
    resolved = config or load_ark_config()
    if resolved is None:
        return None

    def _render(alerts: list[PlanAlert], context_min: dict[str, Any] | None) -> str:
        payload = build_context_payload(
            alerts, plan=plan, action_items=action_items,
            context_min=context_min, frozen_playbook=frozen_playbook,
        )
        text = call_ark(payload, resolved)
        if text is None:
            # 让 render_alerts 的校验失败路径接管 -> 降级模板
            raise RuntimeError("ark 调用失败")
        return text

    return _render


#: 讨论场景系统提示：技术全貌在手、讨论式解释、数值纪律不变。
#: 溯源标注不由此 prompt 产出（由后端 trace 元数据生成，前端角标渲染）。
DISCUSSION_SYSTEM_PROMPT = """你是 LEI 交易系统的研究讨论伙伴（表达层）。

用户会就当前标的技术面与你讨论（比如「这个买点为什么是买点」）。
你手里有一份确定性 Python 判定层算好的技术全貌：五维度判定、活跃结构、
双均线、量能、筹码分布代理、MACD 事件、近期事件、买点审阅、活跃计划。

职责：依据这份材料**讨论式地解释因果**——为什么这里构成/不构成系统定义的
买点、各维度之间支持还是冲突、到什么情况才算触发。可以用自己的话讲，
讲策略语言（道路/路牌/触发/失效），不发明体系外概念。

铁律（违反即输出被丢弃）：
1. 不得自行判断买点/信号。买点结论只能来自 buy_point_review 的 candidates；
   讨论其他维度时结论也必须能落到给定的判定字段上。
2. 禁止出现这些词：买入、卖出、建议买、该买、加仓、减仓、抄底。
   用「参考」「条件成立」「系统定义的买点」「阻断原因」等中性表述。
3. 数值只能照抄给定材料（价格、百分比、指标值）。不得计算新价位、
   不得预测价格、不得推算日期。
4. 筹码分布必须称「筹码分布代理」，不得声称真实持仓成本。
5. 不输出总分、评级；不下买卖指令；不替用户决定是否落计划。
6. 多轮对话：优先接着上文讲，用户问过的不重复展开；用户追问新维度时
   从材料中取该维度细讲。
7. 状态型条件（如多头排列未成立）不贴数字；价位型条件照抄 price。
8. 若用户想落计划：说明五项交易假设需要他逐项确认，逐项给出基于策略的
   建议值（只能引用材料内数值），收集完成后输出 ```plan-draft 代码块
   （JSON，字段：module/direction/entry_rule_id/entry_trigger_cn/
   invalidation_price/valid_until/thesis_cn/invalidation_criteria_cn/
   drawdown_playbook_cn/take_profit_plan_cn/stop_plan_cn）供前端渲染
   确认卡。落库必须等用户点确认，你不得代替确认。
9. 回答中不得出现 rule_id 字样与研究代理标注字样（溯源信息由系统在别处
   呈现）。回显用户提到的数字时必须冠以用户来源（如「你提到的 8700」），
   并主动与材料中最接近的系统位连接给出偏差百分比，不得把用户数字说成
   系统位。
"""


def chat_discussion(
    payload: dict, history: list[dict], message: str, config: ArkConfig
) -> str | None:
    """讨论式多轮对话。history 最近 10 轮（升序）；失败返回 None。"""
    trimmed = history[-20:]  # 10 轮 = 20 条消息
    messages: list[dict] = [
        {"role": "system", "content": DISCUSSION_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"当前标的技术材料：\n{json.dumps(payload, ensure_ascii=False, default=str)}"
            ),
        },
        *trimmed,
        {"role": "user", "content": message},
    ]
    return _llm_call(config, messages)


#: 统一 LLM 请求入口别名：路由层与测试 monkeypatch 此名字即可不触网替换。
_llm_call = _request_completion


__all__ = [
    "DEFAULT_BASE_URL",
    "ENV_API_KEY",
    "ENV_BASE_URL",
    "ENV_MODEL",
    "ENV_STYLE",
    "STYLE_ANTHROPIC",
    "STYLE_OPENAI",
    "BUY_POINT_SYSTEM_PROMPT",
    "DISCUSSION_SYSTEM_PROMPT",
    "SYSTEM_PROMPT",
    "ArkConfig",
    "build_context_payload",
    "call_ark",
    "chat_ark",
    "chat_buy_point",
    "chat_discussion",
    "load_ark_config",
    "make_ark_renderer",
]
