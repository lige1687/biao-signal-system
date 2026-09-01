"""入场确认过滤器（引擎开关，全部默认关；开不开由实验说了算）。

三个过滤器都作用在「已通过模块确认与盈亏比过滤的 EntrySpec」之上，
逐信号按信号日可得数据判定，前向无泄漏：

- 量能确认（规格 §4.8 / 账本 volume_proxies）：近 volume_confirm_window 日内
  任一日 volume_ratio20 >= 账本 up_surge_ratio（常规级别 ≥2.0×MA20(vol)，
  不发明新阈值；窗口=1 即信号日当日）。只做「有/无异常大量」的确认过滤，
  不做连续量能序列分析。
- 筹码峰确认（规格 §11 / 账本 volume_profile_proxy）：poc_support = 入场
  参考价下方 1×ATR20 内存在 POC（踩峰买）；vacuum = overhead_supply_ratio
  <= 账本 vacuum_overhead_max（上方无套牢盘）；both = 两者同时。
  profile 逐信号日计算较贵，按 (symbol, ISO周) 粒度缓存--同周内首个信号日
  的 profile 供全周复用（只用更早数据，无泄漏，仅轻微陈旧）。
  代理数据不可计算时视为「确认不成立」过滤掉（不静默放行）。
- 缺口动能确认（账本 gap_events）：信号日近 lookback_bars 日内存在未回补
  向上缺口才做（标志性动作确认，规格 §4.8 标志性动作）。
- 缩量回调确认（账本 volume_proxies，pullback_shrink 量能口径，第四轮补充
  验证）：shrink(t) = 近 shrink_recent_window 日均量 < 前 shrink_prior_window
  日均量（严格小于）。与 live 标签 pullback_shrink 的量能窗口一致，但不要求
  close 下跌--模块 A 信号日本身就在回调确认场景里。窗口不足（NaN）或
  volume_ratio20 缺失时视为不满足（过滤掉，不静默放行）。
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from lei_signal.backtest.engine import EntrySpec
from lei_signal.domain.rules_config import get_rule
from lei_signal.features.volume_profile import compute_volume_profile
from lei_signal.rules.gap_events import (
    GapEvent,
    recent_unfilled_up_gap,
)

PROFILE_MODES = ("none", "poc_support", "vacuum", "both")


def filter_specs_by_volume(
    frame: pd.DataFrame,
    specs: list[EntrySpec],
    *,
    window: int = 5,
) -> tuple[list[EntrySpec], int]:
    """量能确认过滤；返回 (通过 specs, 被过滤数)。window=1 即信号日当日。"""
    if window < 1:
        raise ValueError(f"volume_confirm_window 必须 >= 1: {window}")
    if "volume_ratio20" not in frame.columns:
        raise ValueError("行情缺少 volume_ratio20 列（应由 compute_features 生成）")
    threshold = float(get_rule("volume_proxies").param("up_surge_ratio", 2.0))
    ratio = frame["volume_ratio20"].astype(float)

    kept: list[EntrySpec] = []
    dropped = 0
    for spec in specs:
        position = spec.signal_position
        lo = max(0, position - window + 1)
        segment = ratio.iloc[lo : position + 1]
        if bool((segment >= threshold).any()):
            kept.append(spec)
        else:
            dropped += 1
    return kept, dropped


def filter_specs_by_profile(
    frame: pd.DataFrame,
    specs: list[EntrySpec],
    *,
    mode: str,
    prepared: dict,
    cache: dict[tuple[str, int, int], object] | None = None,
) -> tuple[list[EntrySpec], int]:
    """筹码峰确认过滤；返回 (通过 specs, 被过滤数)。

    cache 以 (symbol, ISO年, ISO周) 为键复用同周首个信号日的 profile
    （口径见模块 docstring）。prepared 需含 atr20（engine.prepare_frame）。
    """
    if mode not in PROFILE_MODES or mode == "none":
        raise ValueError(f"未知或未启用的筹码过滤档: {mode}")
    spec_rule = get_rule("volume_profile_proxy")
    poc_atr_mult = float(spec_rule.param("poc_support_atr", 1.0))
    overhead_max = float(spec_rule.param("vacuum_overhead_max", 0.30))
    atr20 = prepared["atr20"]
    cache = cache if cache is not None else {}

    kept: list[EntrySpec] = []
    dropped = 0
    for spec in specs:
        signal_day = spec.signal_date
        iso = signal_day.isocalendar()
        key = (spec.symbol, iso[0], iso[1])
        profile = cache.get(key)
        if profile is None:
            profile = compute_volume_profile(frame.iloc[: spec.signal_position + 1])
            cache[key] = profile
        if profile is None:
            dropped += 1  # 代理数据不可计算 -> 确认不成立
            continue
        atr_value = float(atr20.iloc[spec.signal_position])
        ok = True
        if mode in ("poc_support", "both"):
            atr_ok = pd.notna(atr_value) and atr_value > 0
            near_poc = bool(
                atr_ok
                and profile.poc <= spec.entry_ref_price
                and (spec.entry_ref_price - profile.poc) <= poc_atr_mult * atr_value
            )
            ok = ok and near_poc
        if mode in ("vacuum", "both"):
            ok = ok and profile.overhead_supply_ratio <= overhead_max
        if ok:
            kept.append(spec)
        else:
            dropped += 1
    return kept, dropped


def filter_specs_by_gap_momentum(
    specs: list[EntrySpec],
    *,
    gaps: list[GapEvent],
    bar_dates: list[date],
    lookback_bars: int = 10,
) -> tuple[list[EntrySpec], int]:
    """缺口动能过滤：信号日近 lookback_bars 日内存在未回补向上缺口才做。"""
    if lookback_bars < 1:
        raise ValueError(f"gap_momentum_lookback 必须 >= 1: {lookback_bars}")
    kept: list[EntrySpec] = []
    dropped = 0
    for spec in specs:
        gap = recent_unfilled_up_gap(
            gaps,
            as_of=spec.signal_date,
            lookback_bars=lookback_bars,
            bar_dates=bar_dates,
        )
        if gap is not None:
            kept.append(spec)
        else:
            dropped += 1
    return kept, dropped


def filter_specs_by_shrink(
    frame: pd.DataFrame,
    specs: list[EntrySpec],
    *,
    recent_window: int | None = None,
    prior_window: int | None = None,
    vr_max: float | None = None,
) -> tuple[list[EntrySpec], int]:
    """缩量回调过滤；返回 (通过 specs, 被过滤数)。

    窗口默认读账本 volume_proxies.shrink_recent_window / shrink_prior_window
    （=3/3，即 mean(vol[t-2:t+1]) < mean(vol[t-5:t-2])）。vr_max 非空时叠加
    「信号日 volume_ratio20 < vr_max」更严格分档。均量不足（NaN）或量比缺失
    判 False（不通过）。
    """
    rule = get_rule("volume_proxies")
    recent_w = recent_window if recent_window is not None else int(
        rule.param("shrink_recent_window", 3)
    )
    prior_w = prior_window if prior_window is not None else int(
        rule.param("shrink_prior_window", 3)
    )
    if recent_w < 1 or prior_w < 1:
        raise ValueError(f"缩量窗口必须 >= 1: recent={recent_w}, prior={prior_w}")
    if vr_max is not None and vr_max <= 0:
        raise ValueError(f"volume_filter_vr_max 必须为正: {vr_max}")

    vol = frame["volume"].astype(float)
    recent_mean = vol.rolling(recent_w, min_periods=recent_w).mean()
    prior_mean = (
        vol.rolling(prior_w, min_periods=prior_w).mean().shift(recent_w)
    )
    shrink = (recent_mean < prior_mean).fillna(False)
    if vr_max is not None:
        if "volume_ratio20" not in frame.columns:
            raise ValueError("行情缺少 volume_ratio20 列（应由 compute_features 生成）")
        ratio = frame["volume_ratio20"].astype(float)
        shrink = shrink & (ratio < vr_max).fillna(False)

    kept: list[EntrySpec] = []
    dropped = 0
    for spec in specs:
        if bool(shrink.iloc[spec.signal_position]):
            kept.append(spec)
        else:
            dropped += 1
    return kept, dropped


def filter_specs_by_bias(
    frame: pd.DataFrame,
    specs: list[EntrySpec],
    *,
    bias_max: float,
) -> tuple[list[EntrySpec], int]:
    """深乖离增强过滤（规格 §4.7 / C1 增强条件）：信号日 close/EMA120 - 1
    <= bias_max（负值，如 -0.15 = 低于 EMA120 15% 以上）才入场。

    乖离只作增强条件不单独触发（C1 原则）；NaN（EMA120 未就绪）判 False。
    口径与 rules/two_b_reversal._bias_ema120 完全一致（单一真相源）。
    """
    if bias_max >= 0:
        raise ValueError(f"bias_max 必须为负（深乖离档）: {bias_max}")
    for col in ("close", "ema120"):
        if col not in frame.columns:
            raise ValueError(f"行情缺少 {col} 列（应由 compute_features 生成）")
    ema120 = frame["ema120"].astype(float)
    bias = (frame["close"].astype(float) / ema120 - 1.0).where(ema120 != 0)
    deep = (bias <= bias_max).fillna(False)

    kept: list[EntrySpec] = []
    dropped = 0
    for spec in specs:
        if bool(deep.iloc[spec.signal_position]):
            kept.append(spec)
        else:
            dropped += 1
    return kept, dropped


__all__ = [
    "PROFILE_MODES",
    "filter_specs_by_bias",
    "filter_specs_by_gap_momentum",
    "filter_specs_by_profile",
    "filter_specs_by_shrink",
    "filter_specs_by_volume",
]
