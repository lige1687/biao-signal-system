"""仓位档位建议（纯函数，参数全部读规则账本的 copilot_sizing）。

组合层管理建议，不是技术判定（设计定稿 D2）：依据 = 盈亏比（技术层已算）
+ 同板块已有敞口（组合层事实）+ 宽度环境调节（2026-09-06 用户拍板接入，
带 RS 虹吸豁免）；输出档位与百分比区间，最终金额由用户定。

宽度环境调节的依据与边界：
- 依据：宽度全栈组 31 轮回测验证的「宽度三档管仓位」（低档减仓/高档加仓，
  16 年 A 股等权篮子年化 15.9%/-25.6% 回撤 vs 持有 +2.6%/-46%）——本层
  只取「低档降一档」，不取加仓（保守，单向）。
- 虹吸豁免（用户口径 2026-09-06）：结构性牛市里强势赛道不受全市场宽度
  压制——「每一轮牛市不一样，这一轮可能是虹吸效应」。判定用 RS 虹吸灯
  口径（宽度全栈归档：标的 120 日收益相对基准 >20 个百分点且已持续，
  误报率 8%）；豁免时不降档——价格是最公平的信息反映（用户原则），
  标的自身独立强度已在价格里。
- 阈值不硬编码：宽度档位线读规则账本 breadth_position 段（与宽度全栈
  同源 43.3/56.7），RS 虹吸阈值读 siphon 段（20pp）。
"""
from __future__ import annotations

import pandas as pd

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


def _rule_param(rule_id: str, key: str, default: float) -> float:
    """宽容读账本：段缺失时用默认并允许调用方标注（不硬编码进逻辑分支）。"""
    try:
        rule = get_rule(rule_id)
        v = rule.param(key)
        return float(v) if v is not None else default
    except Exception:  # noqa: BLE001 — 账本缺段不阻塞仓位建议
        return default


def _tier_pct_cn(tier: str, p: dict) -> str:
    if tier == "试仓":
        return f"不超过 {p['tier_trial_pct_max']:g}%（占总资金）"
    if tier == "标准":
        return f"{p['tier_standard_pct_min']:g}–{p['tier_standard_pct_max']:g}%（占总资金）"
    return (
        f"{p['tier_heavy_pct_min']:g}–{p['single_symbol_cap_pct']:g}%"
        f"（占总资金，硬顶 {p['single_symbol_cap_pct']:g}%）"
    )


def breadth_adjustment_cn(
    ma200_pct: float | None,
    *,
    siphon: bool,
) -> tuple[bool, str | None]:
    """宽度环境调节判定（纯函数，供仓位建议与测试复用）。

    返回 (是否降一档, 说明文案)。ma200_pct=None（宽度缺席）不调节；
    低档(<下档位线)降一档；虹吸独立行情豁免（文案说明为何不降）。
    """
    low_line = _rule_param("breadth_position", "low_line", 43.3)
    if ma200_pct is None:
        return False, None
    if ma200_pct < low_line:
        if siphon:
            return (
                False,
                f"宽度环境弱市（站上200日线个股 {ma200_pct:.0f}%，低于 "
                f"{low_line:g}% 档位线）——但标的处于独立行情（虹吸，相对大盘"
                "显著走强），宽度不压它的仓位：价格是最公平的信息反映"
                "（宽度全栈组·RS虹吸灯口径）",
            )
        return (
            True,
            f"宽度环境弱市：站上200日线的个股只有 {ma200_pct:.0f}%"
            f"（低于 {low_line:g}% 档位线），档位降一档"
            "（依据：宽度全栈组16年验证的低档减仓规则，只降不升）",
        )
    return False, None


def siphon_regime(
    frame: pd.DataFrame, bench_frame: pd.DataFrame
) -> tuple[bool, float | None]:
    """RS 虹吸灯（简化口径）：标的 120 日收益 − 基准 120 日收益 > siphon_rs_pp
    且 5 日前同样成立（近似归档规则的「持续 10 日」，代码注释标明口径差异）。

    frame/bench_frame 均为日线（close 列）；数据不足返回 (False, None)。
    """
    pp = _rule_param("siphon", "rs_pp", 20.0)
    c, b = frame["close"], bench_frame["close"]
    if len(c) < 126 or len(b) < 126:
        return False, None
    def rs(series: pd.Series, back: int) -> float | None:
        i = len(series) - 1 - back
        if i - 120 < 0:
            return None
        return float(series.iloc[i] / series.iloc[i - 120] - 1) * 100
    rs_now, rs_5d = rs(c, 0), rs(c, 5)
    bench_now, bench_5d = rs(b, 0), rs(b, 5)
    if None in (rs_now, rs_5d, bench_now, bench_5d):
        return False, None
    diff_now = rs_now - bench_now
    diff_5d = rs_5d - bench_5d
    return (diff_now > pp and diff_5d > pp), diff_now


def build_sizing_advice(
    symbol: str,
    rr: float | None,
    *,
    rr_computable: bool = True,
    same_group_exposure_pct: float | None = None,
    breadth_ma200_pct: float | None = None,
    siphon: bool = False,
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
    # 宽度环境调节（2026-09-06 用户拍板）：弱市降一档，虹吸独立行情豁免。
    downgrade, breadth_cn = breadth_adjustment_cn(breadth_ma200_pct, siphon=siphon)
    if breadth_cn:
        reasons.append(breadth_cn)
    if downgrade:
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
