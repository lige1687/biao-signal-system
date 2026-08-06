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
import os
import time
from dataclasses import dataclass
from typing import Any

import requests

from lei_signal.plans.models import ActionItem, PlanAlert, TradePlan

#: ark 默认端点与模型。凭据只走环境变量，绝不硬编码。
DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
ENV_API_KEY = "ARK_API_KEY"
ENV_BASE_URL = "ARK_BASE_URL"
ENV_MODEL = "ARK_MODEL"

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
你的职责：把它讲成简洁中文，帮用户理解当前是否构成系统定义的买点、图什么信号、
止损设哪、盈亏比多少，并协助协商落计划。

铁律（违反即输出被丢弃）：
1. **不得自行判断买点**。买点结论只能来自 review 的 candidates 字段
   （satisfied_conditions / missing_conditions / state）。不得从行情自行推断。
2. 禁止出现这些词：买入、卖出、建议买、该买、加仓、减仓、抄底。
   用「参考」「条件成立」「可执行日」「系统定义的买点」等中性表述。
3. **不得推算任何价位**。止损只能照抄 candidates 的 invalidation_price；
   若该字段为 None（场景卡只给失效文案不给价），必须明说「止损价需在建计划时
   人工确认，系统未给出」，不得编一个数字。盈亏比只能照抄 reward_risk_ratio；
   reward_risk_computable=False 时必须说「盈亏比目标不可计算」。
4. **「到什么情况才算买点」只能引 watch_conditions**：价位型条件照抄 price，
   状态型条件（如多头排列未成立）不得贴数字。不得预测何时到达。
5. 不得推算日期。可执行日只能照抄 actionable_from / as_of。
6. research_proxy 标注：场景/可交易性/盈亏比均为研究代理，必须写「判定方式为研究代理」。
7. 不输出总分、不输出评级、不预测价格走势。
8. verdict=blocked 时必须先讲阻断（规格 §13），明确「按规则不开新仓」。
9. 落计划只能提议，不得替用户决定。五项交易假设必须由人写。
"""


@dataclass(frozen=True, slots=True)
class ArkConfig:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    model: str = "ark-code-latest"
    timeout: float = 30.0
    style: str = STYLE_OPENAI
    max_tokens: int = 1500
    #: 429/5xx 的退避重试次数。监督员与其他工具共用同一 key 时会撞限频，
    #: 但投递是 best-effort：重试用尽仍失败即返回 None，由调用方降级模板。
    retry_on_throttle: int = 2
    retry_backoff_seconds: float = 2.0


def _infer_style(base_url: str) -> str:
    """按网关路径推断协议风格。/api/coding 是 Anthropic 兼容，/api/v3 是 OpenAI 兼容。"""
    return STYLE_ANTHROPIC if "/coding" in base_url else STYLE_OPENAI


def load_ark_config() -> ArkConfig | None:
    """从环境变量读 ark 配置。缺 API key 时返回 None（调用方降级模板）。

    兼容两组变量名：优先 ARK_*；未设置时回退 ANTHROPIC_*（本机 Claude Code 用的
    就是 ark 的 /api/coding 网关，复用同一凭据避免重复配置）。
    """
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
                return extract(resp.json())
            # 429 限频 / 5xx 瞬时故障：退避重试；其他状态码直接放弃
            throttled = resp.status_code == 429 or resp.status_code >= 500
            if throttled and attempt < config.retry_on_throttle:
                time.sleep(config.retry_backoff_seconds * (2**attempt))
                continue
            return None
        return None
    except (requests.RequestException, ValueError, KeyError, IndexError):
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

    与 call_ark 同一套 SYSTEM_PROMPT（接地铁律）与底层投递；区别仅在于 user 内容
    追加了用户问题。回复仍须由调用方过 ``verify_grounding``（禁用词 + rule_id 白名单），
    不过则降级模板--判定权始终在 Python，LLM 只表达。
    """
    content = (
        "以下是当前监督结果（只许引用其中出现过的 rule_id 与 evidence 数值，"
        "不得编造 rule_id、不得推算日期、不得引入给定外的数值）：\n"
        + json.dumps(prompt_payload, ensure_ascii=False, indent=2)
        + f"\n\n用户问题：{user_message}"
    )
    return _post_user_content(content, config)


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


__all__ = [
    "DEFAULT_BASE_URL",
    "ENV_API_KEY",
    "ENV_BASE_URL",
    "ENV_MODEL",
    "ENV_STYLE",
    "STYLE_ANTHROPIC",
    "STYLE_OPENAI",
    "BUY_POINT_SYSTEM_PROMPT",
    "SYSTEM_PROMPT",
    "ArkConfig",
    "build_context_payload",
    "call_ark",
    "chat_ark",
    "chat_buy_point",
    "load_ark_config",
    "make_ark_renderer",
]
