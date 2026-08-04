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
from dataclasses import dataclass
from typing import Any

import requests

from lei_signal.plans.models import ActionItem, PlanAlert, TradePlan

#: ark 默认端点与模型。凭据只走环境变量，绝不硬编码。
DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
ENV_API_KEY = "ARK_API_KEY"
ENV_BASE_URL = "ARK_BASE_URL"
ENV_MODEL = "ARK_MODEL"

#: 表达层系统提示：把红线写成 LLM 可执行的约束。
SYSTEM_PROMPT = """你是 LEI 交易系统的纪律监督员的**表达层**。

你的唯一职责：把下面给定的 alert（已由确定性 Python 判定层算出）讲成简洁中文。

铁律（违反即输出被丢弃）：
1. 只能引用给定 alert 里出现过的 rule_id。禁止编造 rule_id。
2. 禁止出现这些词：买入、卖出、建议买、该买、加仓、减仓、抄底。
   用「参考」「提醒」「阻断原因」「可执行日」等中性表述。
3. 不得推算任何日期。日期只能照抄给定的 actionable_from / data_as_of。
4. 不得引入给定数据之外的数值。证据数值必须照抄 evidence。
5. 带 principle_source 的 alert，必须同时写出原文出处与「判定方式为研究代理」。
6. 不输出总分、不输出评级、不预测价格。
7. next_step 必须照抄给定的 next_step_cn，不得自创。

输出格式（严格遵守，不要额外寒暄）：
【计划】{symbol} 模块{module} · {entry_rule_id} · 状态 {state} · 有效期至 {valid_until}
【数据】{data_as_of}{陈旧警示}

▶ 待办（催办第 N 次）
  {kind}：{要做什么}
  可执行日：{due_from}
  → 你可以：标记已执行 / 推迟（需说明原因）

■ 阻断 / ■ 提醒 / □ 提示
  {人话说明}
  [rule_id:{rule_id} | 证据:{evidence 键值}]
  {原文出处 | 判定方式为研究代理}

【下一步观察】{照抄 next_step_cn}
"""


@dataclass(frozen=True, slots=True)
class ArkConfig:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    model: str = "ark-code-latest"
    timeout: float = 30.0


def load_ark_config() -> ArkConfig | None:
    """从环境变量读 ark 配置。缺 API key 时返回 None（调用方降级模板）。"""
    api_key = os.environ.get(ENV_API_KEY, "").strip()
    if not api_key:
        return None
    return ArkConfig(
        api_key=api_key,
        base_url=os.environ.get(ENV_BASE_URL, DEFAULT_BASE_URL).rstrip("/"),
        model=os.environ.get(ENV_MODEL, "ark-code-latest"),
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
        payload["action_items"] = [
            {
                "kind": i.kind,
                "state": i.state,
                "due_from": i.due_from,
                "nag_count": i.nag_count,
                "source_alert_code": i.source_alert_code,
            }
            for i in action_items
            if i.state == "open"
        ]
    if context_min:
        payload["context_min"] = context_min
    return payload


def call_ark(prompt_payload: dict[str, Any], config: ArkConfig) -> str | None:
    """调 ark chat completions。任何失败返回 None（调用方降级）。"""
    url = f"{config.base_url}/chat/completions"
    body = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "把下面的监督结果讲成人话，严格遵守输出格式与铁律：\n"
                    + json.dumps(prompt_payload, ensure_ascii=False, indent=2)
                ),
            },
        ],
        "temperature": 0.2,
    }
    try:
        resp = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=config.timeout,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            return None
        content = choices[0].get("message", {}).get("content")
        return str(content) if content else None
    except (requests.RequestException, ValueError, KeyError, IndexError):
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


__all__ = [
    "DEFAULT_BASE_URL",
    "ENV_API_KEY",
    "ENV_BASE_URL",
    "ENV_MODEL",
    "SYSTEM_PROMPT",
    "ArkConfig",
    "build_context_payload",
    "call_ark",
    "load_ark_config",
    "make_ark_renderer",
]
