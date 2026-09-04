"""仓位档位建议（纯函数，参数全部读 rules.v1.yaml 的 copilot_sizing）。

组合层管理建议，不是技术判定（设计定稿 D2）：依据 = 盈亏比（技术层已算）
+ 同板块已有敞口（组合层事实）；输出档位与百分比区间，最终金额由用户定。
"""
from __future__ import annotations

from lei_signal.api.schemas import SizingAdviceDTO
from lei_signal.domain.rules_config import get_rule

_TIERS = ("试仓", "标准", "偏重")


_PARAM_KEYS = (
    "tier_trial_pct_max",
    "tier_standard_pct_min",
    "tier_standard_pct_max",
    "tier_heavy_pct_min",
    "single_symbol_cap_pct",
    "same_group_soft_cap_pct",
    "rr_tier_threshold",
)


def _params() -> dict:
    rule = get_rule("copilot_sizing")
    return {k: rule.param(k) for k in _PARAM_KEYS}


def _tier_pct_cn(tier: str, p: dict) -> str:
    if tier == "试仓":
        return f"不超过 {p['tier_trial_pct_max']:g}%（占总资金）"
    if tier == "标准":
        return f"{p['tier_standard_pct_min']:g}–{p['tier_standard_pct_max']:g}%（占总资金）"
    return (
        f"{p['tier_heavy_pct_min']:g}–{p['single_symbol_cap_pct']:g}%"
        f"（占总资金，硬顶 {p['single_symbol_cap_pct']:g}%）"
    )


def build_sizing_advice(
    symbol: str,
    rr: float | None,
    *,
    rr_computable: bool = True,
    same_group_exposure_pct: float | None = None,
) -> SizingAdviceDTO:
    p = _params()
    reasons: list[str] = []
    if rr is not None and rr_computable:
        reasons.append(f"盈亏比 {rr}（技术层已算）")
        tier = "标准" if rr >= float(p["rr_tier_threshold"]) else "试仓"
    else:
        reasons.append("盈亏比不可计算（目标位无法客观确定）")
        tier = "试仓"
    if (
        same_group_exposure_pct is not None
        and same_group_exposure_pct >= float(p["same_group_soft_cap_pct"])
    ):
        reasons.append(
            f"同板块已有敞口约 {same_group_exposure_pct:g}%，"
            f"超过 {p['same_group_soft_cap_pct']:g}% 软上限，整体降一档"
        )
        idx = _TIERS.index(tier)
        tier = _TIERS[max(0, idx - 1)]
    reasons.append(f"单标的硬顶 {p['single_symbol_cap_pct']:g}%（2026-09-05 用户拍板）")
    return SizingAdviceDTO(
        symbol=symbol,
        tier=tier,
        tier_pct_cn=_tier_pct_cn(tier, p),
        cap_pct=float(p["single_symbol_cap_pct"]),
        reasons=reasons,
    )
