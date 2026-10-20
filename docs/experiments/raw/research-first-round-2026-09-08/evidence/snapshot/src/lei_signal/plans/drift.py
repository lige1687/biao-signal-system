"""漂移复议判定（规格 §14，决策 1）。

监督员区别于讲解员的唯一硬功能。**判定基准不是浮亏，是方向分类器**：
Python 只判失效价移动方向，不解析预案文本。冻结的五项预案在复议时作为对照原文
摆给人看，代码不读它。

- 收紧（多头上移失效价 / 空头下移）= 移动止盈 -> ``within_playbook`` 放行
- 放宽（多头下移 / 空头上移）= 放松风险 -> ``needs_review``
- 硬规则（不分方向一律 ``needs_review``）：改任一交易假设、entered 后换入场理由
  （§14 正条）、换交易模块（§12）。

判定权完整留在 Python：预案文本不参与判定，只在复议时摆出来给人和 agent 对照。
"""
from __future__ import annotations

from dataclasses import dataclass

from lei_signal.plans.models import (
    PLAN_ENTERED,
    PLAYBOOK_FIELDS,
    VERDICT_NEEDS_REVIEW,
    VERDICT_WITHIN_PLAYBOOK,
    TradePlan,
)

DIRECTION_TIGHTEN = "tighten"
DIRECTION_RELAX = "relax"


@dataclass(frozen=True, slots=True)
class Verdict:
    """一次修订的复议裁决。"""

    verdict: str                       # within_playbook / needs_review
    reason_cn: str
    changed_field: str
    direction: str | None = None       # tighten/relax/None


def _to_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value:
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _classify_invalidation_move(
    direction: str, old: float | None, new: float | None
) -> str | None:
    """失效价移动方向：多头下移/空头上移=放宽；反向=收紧。"""
    if old is None or new is None:
        return None
    if new == old:
        return None
    if direction == "long":
        return DIRECTION_RELAX if new < old else DIRECTION_TIGHTEN
    # short：失效价在上方，上移=放宽，下移=收紧
    return DIRECTION_RELAX if new > old else DIRECTION_TIGHTEN


def check_revision(
    plan: TradePlan, changes: dict[str, object]
) -> Verdict:
    """判定一批拟议修改是否落在预案内。

    ``changes`` = {field: new_value}。任一硬规则命中即 ``needs_review``；
    失效价方向分类器判定收紧/放宽；非冻结字段调整默认 ``within_playbook``。
    """
    # 硬规则（不分方向，一律 needs_review）
    for field in changes:
        if field in PLAYBOOK_FIELDS:
            return Verdict(
                VERDICT_NEEDS_REVIEW,
                f"改的是交易假设本身（{field}），不属于预案内调整",
                field,
            )
        if field == "entry_rule_id" and plan.state == PLAN_ENTERED:
            return Verdict(
                VERDICT_NEEDS_REVIEW,
                "entered 后更换入场理由（规格 §14 正条）",
                field,
            )
        if field == "module":
            return Verdict(
                VERDICT_NEEDS_REVIEW,
                "更换交易模块（规格 §12 模块分别统计）",
                field,
            )

    # 方向分类器（失效价）
    if "invalidation_price" in changes:
        new_price = _to_float(changes["invalidation_price"])
        direction = _classify_invalidation_move(
            plan.direction, plan.invalidation_price, new_price
        )
        if direction == DIRECTION_RELAX:
            return Verdict(
                VERDICT_NEEDS_REVIEW,
                f"放宽失效价（{plan.direction} {'下移' if plan.direction == 'long' else '上移'}）",
                "invalidation_price",
                DIRECTION_RELAX,
            )
        if direction == DIRECTION_TIGHTEN:
            return Verdict(
                VERDICT_WITHIN_PLAYBOOK,
                "收紧失效价（移动止盈），预案内放行",
                "invalidation_price",
                DIRECTION_TIGHTEN,
            )
        return Verdict(
            VERDICT_WITHIN_PLAYBOOK,
            "失效价未移动",
            "invalidation_price",
            None,
        )

    # 非冻结字段调整（entry_trigger_cn / target_b_price 等）-> 预案内
    field = next(iter(changes), "")
    return Verdict(
        VERDICT_WITHIN_PLAYBOOK,
        f"非冻结字段调整（{field}），预案内",
        field,
    )


__all__ = [
    "DIRECTION_RELAX",
    "DIRECTION_TIGHTEN",
    "Verdict",
    "check_revision",
]
