"""今日信息概述：把 AnalysisResult + 盘口快照映射成四组指标。

分组原则
--------
- price：四价、振幅与 20 日抵扣价乖离。
- technical：EMA/SMA 乖离率、ATR 波动率、双均线开口、日/周长周期趋势。
- volume：量能倍数与分级（来自 volume_ratio20），换手率与量比（来自盘口）。
- capital：流通/总市值、成交额（盘口）。
- signal：LEI 颜色与持续天数、阶段、风险、距 C 点、距 B1、今日新事件数。

诚实原则：盘口源不覆盖的标的（海外指数），相关 value 一律 None，
界面显示「—」，不用日线数据推算冒充换手率。
"""
from __future__ import annotations

from lei_signal.api import labels
from lei_signal.api.card_mapper import color_duration
from lei_signal.api.quotes import QuoteSnapshot
from lei_signal.api.schemas import MetricDTO, TodayOverviewDTO
from lei_signal.compose.pipeline import AnalysisResult
from lei_signal.domain.types import COLOR_CN, LONG_TREND_CN, STAGE_CN

#: 量能分级阈值（与 ui/echarts_kline._classify_vol 同口径）。
_VOL_TIERS: tuple[tuple[float, str, str], ...] = (
    (2.0, "放量", "warn"),
    (1.2, "温和放量", "neutral"),
    (0.8, "正常", "neutral"),
    (0.0, "缩量", "neutral"),
)


def _classify_volume(ratio: float) -> tuple[str, str]:
    for threshold, label, tone in _VOL_TIERS:
        if ratio >= threshold:
            return label, tone
    return "缩量", "neutral"


def _pct_tone(value: float | None) -> str:
    if value is None:
        return "neutral"
    return "up" if value > 0 else "down" if value < 0 else "neutral"


def _distance_metric(
    key: str, label: str, close: float, level: float | None, hint: str, concept: str | None = None
) -> MetricDTO:
    """价格相对某条均线/参考价的距离百分比。正 = 价格在其上方。"""
    if level is None or not level:
        return MetricDTO(
            key=key, label_cn=label, value=None, unit="%", hint_cn=hint, concept=concept
        )
    pct = (close / level - 1) * 100
    return MetricDTO(
        key=key,
        label_cn=label,
        value=round(pct, 2),
        unit="%",
        tone=_pct_tone(pct),
        hint_cn=f"{hint}（当前 {level:.2f}）",
        concept=concept,
    )


def _trend_tone(state: str) -> str:
    if state in ("long_bull", "long_stable_bull", "long_improving"):
        return "up"
    if state in ("long_bear", "long_deteriorating"):
        return "down"
    return "neutral"


def _trend_metric(key: str, label: str, state: str | None, hint: str) -> MetricDTO:
    normalized = state or "unknown"
    return MetricDTO(
        key=key,
        label_cn=label,
        text=LONG_TREND_CN.get(normalized, normalized),
        tone=_trend_tone(normalized),
        hint_cn=hint,
        concept="long_trend",
    )


def build_today_overview(
    result: AnalysisResult,
    *,
    quote: QuoteSnapshot | None,
) -> TodayOverviewDTO:
    frame = result.frame
    if frame.empty:
        return TodayOverviewDTO(as_of=result.assessment.as_of.isoformat(), quote_available=False)

    last = frame.iloc[-1]
    close = float(last["close"])
    open_ = float(last["open"])
    high = float(last["high"])
    low = float(last["low"])

    def col(name: str) -> float | None:
        if name not in frame.columns:
            return None
        raw = last[name]
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return None
        return None if value != value else value  # NaN 过滤

    def text_col(name: str) -> str | None:
        if name not in frame.columns:
            return None
        raw = last[name]
        if raw is None or raw != raw:
            return None
        return str(raw)

    # ---------------- 价格 ----------------
    amplitude = (high - low) / close * 100 if close else None
    price: list[MetricDTO] = [
        MetricDTO(key="open", label_cn="今开", value=round(open_, 3)),
        MetricDTO(key="high", label_cn="最高", value=round(high, 3)),
        MetricDTO(key="low", label_cn="最低", value=round(low, 3)),
        MetricDTO(key="close", label_cn="最新", value=round(close, 3)),
        MetricDTO(
            key="amplitude",
            label_cn="振幅",
            value=round(amplitude, 2) if amplitude is not None else None,
            unit="%",
            hint_cn="(最高-最低)/最新",
        ),
        _distance_metric("dist_ref20", "抵扣价乖离", close, col("close_lag20"),
                         "价格相对20日前收盘的乖离；高于抵扣价通常意味着 MA20 向上",
                         concept="ref20"),
    ]

    # ---------------- 趋势 / 波动 ----------------
    technical: list[MetricDTO] = [
        _distance_metric("dist_ema20", "EMA20乖离率", close, col("ema20"),
                         "(最新价 / EMA20 - 1) × 100%；正值在均线上方，负值在下方",
                         concept="bias"),
        _distance_metric("dist_sma20", "SMA20乖离率", close, col("sma20"),
                         "(最新价 / SMA20 - 1) × 100%；用于观察短周期偏离程度",
                         concept="bias"),
        _distance_metric("dist_ema60", "EMA60乖离率", close, col("ema60"),
                         "(最新价 / EMA60 - 1) × 100%；观察价格相对长周期中枢的位置",
                         concept="bias"),
    ]
    atr = col("atr14")
    atr_pct = atr / close * 100 if atr is not None and close else None
    technical.append(
        MetricDTO(
            key="atr14_pct",
            label_cn="ATR14波动率",
            value=round(atr_pct, 2) if atr_pct is not None else None,
            unit="%",
            hint_cn=(
                f"ATR14={atr:.3f}；ATR14 / 最新价，衡量近期日内真实波动尺度"
                if atr is not None else "ATR14 / 最新价，衡量近期日内真实波动尺度"
            ),
            concept="atr",
        )
    )
    spread = col("ma_spread")
    spread_change = col("ma_spread_change")
    ema_above = bool(last["ema20_above_sma20"]) if "ema20_above_sma20" in frame.columns else None
    spread_pct = spread * 100 if spread is not None else None
    spread_direction = "扩张" if spread_change is not None and spread_change > 0 else "收窄"
    if spread_change == 0:
        spread_direction = "持平"
    position = (
        "EMA20在上"
        if ema_above is True
        else "EMA20在下" if ema_above is False else "位置未知"
    )
    technical.append(
        MetricDTO(
            key="ma_spread",
            label_cn="双均线开口",
            value=round(spread_pct, 2) if spread_pct is not None else None,
            unit="%",
            text=(f"{spread_pct:.2f}% · {spread_direction}" if spread_pct is not None else None),
            tone=(
                "up"
                if spread_change is not None and spread_change > 0 and ema_above is True
                else "down"
                if spread_change is not None and spread_change > 0 and ema_above is False
                else "neutral"
            ),
            hint_cn=f"|EMA20-SMA20| / 最新价；{position}，当前{spread_direction}",
            concept="ma_spread",
        )
    )
    technical.append(
        _trend_metric(
            "daily_long_trend", "日线长趋势", text_col("long_trend"),
            "基于日线 EMA60/EMA120 的相对位置、斜率与开口变化",
        )
    )
    weekly_state: str | None = None
    if not result.weekly_trend.empty and "long_trend" in result.weekly_trend.columns:
        visible_weekly = result.weekly_trend.loc[
            result.weekly_trend.index <= frame.index[-1], "long_trend"
        ]
        if not visible_weekly.empty:
            weekly_state = str(visible_weekly.iloc[-1])
    technical.append(
        _trend_metric(
            "weekly_long_trend", "周线长趋势", weekly_state,
            "仅使用已完成周线的 EMA60/EMA120；数据不足时明确显示数据不足",
        )
    )

    # ---------------- 量能 ----------------
    ratio = col("volume_ratio20")
    volume: list[MetricDTO] = []
    if ratio is not None:
        label, tone = _classify_volume(ratio)
        volume.append(
            MetricDTO(
                key="vol_ratio20",
                label_cn="量能倍数",
                value=round(ratio, 2),
                text=f"{ratio:.2f}× · {label}",
                tone=tone,
                hint_cn="当日成交量 / 20日均量；≥2×放量，1.2-2×温和，0.8-1.2×正常，<0.8×缩量",
                concept="volume_state",
            )
        )
    vol_now = col("volume")
    vol_mean = col("volume_mean20")
    if vol_now is not None:
        volume.append(
            MetricDTO(
                key="volume", label_cn="成交量", value=round(vol_now, 0),
                hint_cn="当日成交量（股/份）",
            )
        )
    if vol_mean is not None:
        volume.append(
            MetricDTO(key="volume_mean20", label_cn="20日均量", value=round(vol_mean, 0))
        )

    quote_available = quote is not None
    if quote is not None:
        volume.append(
            MetricDTO(
                key="turnover_rate",
                label_cn="换手率",
                value=quote.turnover_rate,
                unit="%",
                hint_cn="成交量 / 流通股本（来自实时盘口）",
            )
        )
        volume.append(
            MetricDTO(
                key="volume_ratio",
                label_cn="量比",
                value=quote.volume_ratio,
                hint_cn="当前每分钟均量 / 过去5日同期每分钟均量；>1 表示放量",
            )
        )
    else:
        volume.append(
            MetricDTO(key="turnover_rate", label_cn="换手率", value=None, unit="%",
                      hint_cn="该标的的行情源不提供换手率")
        )
        volume.append(
            MetricDTO(key="volume_ratio", label_cn="量比", value=None,
                      hint_cn="该标的的行情源不提供量比")
        )

    # ---------------- 资金 / 市值 ----------------
    capital: list[MetricDTO] = []
    if quote is not None:
        capital.append(
            MetricDTO(key="amount", label_cn="成交额", value=quote.amount_wan,
                      unit="万元", hint_cn="当日成交金额")
        )
        capital.append(
            MetricDTO(key="float_cap", label_cn="流通市值", value=quote.float_cap_yi, unit="亿元")
        )
        capital.append(
            MetricDTO(key="total_cap", label_cn="总市值", value=quote.total_cap_yi, unit="亿元")
        )

    # ---------------- LEI 信号 ----------------
    assessment = result.assessment
    _, color_days = color_duration(result)
    color_value = assessment.color.value
    signal: list[MetricDTO] = [
        MetricDTO(
            key="color",
            label_cn="LEI 颜色",
            text=f"{COLOR_CN.get(color_value, color_value)}"
            + (f" · 第{color_days}天" if color_days else ""),
            tone="warn" if color_value == "black" else "neutral",
            hint_cn="绿=多头观察 / 灰=中性 / 黑=空头规避；与涨跌红绿无关",
            concept="signal_color",
        ),
        MetricDTO(
            key="stage",
            label_cn="机会阶段",
            text=STAGE_CN.get(
                assessment.opportunity_stage.value, assessment.opportunity_stage.value
            ),
            hint_cn="结构确认程度的递进；early_watch 仅观察不构成买入",
            concept="stage",
        ),
        MetricDTO(
            key="risk_state",
            label_cn="风险状态",
            text=labels.RISK_STATE_CN.get(
                assessment.risk_state.value, assessment.risk_state.value
            ),
            tone="warn" if assessment.risk_state.value != "normal" else "neutral",
            hint_cn="与机会阶段分离的独立维度",
            concept="risk_state",
        ),
    ]

    structure = assessment.primary_structure
    if structure is not None and structure.c_price and close:
        dist_c = (close - structure.c_price) / close * 100
        signal.append(
            MetricDTO(
                key="dist_c",
                label_cn="距C点",
                value=round(dist_c, 2),
                unit="%",
                text=(
                    f"高于 {dist_c:.1f}%" if dist_c >= 0 else f"跌破 {abs(dist_c):.1f}%"
                ),
                tone="down" if dist_c >= 0 else "up",
                hint_cn=f"C={structure.c_price:.2f}；触及即结构永久失效",
                concept="c_point",
            )
        )
    if assessment.b1_price is not None:
        signal.append(
            MetricDTO(
                key="dist_b1",
                label_cn="距B1",
                value=(
                    round(assessment.distance_to_b1_pct, 2)
                    if assessment.distance_to_b1_pct is not None
                    else None
                ),
                unit="%",
                hint_cn=f"B1={assessment.b1_price:.2f}；参考前高，非止盈目标",
                concept="b1",
            )
        )
    signal.append(
        MetricDTO(
            key="new_events",
            label_cn="今日新事件",
            text=f"{len(assessment.new_events)} 条",
            tone="warn" if assessment.new_events else "neutral",
            hint_cn="今天最早可确认的事件数量",
        )
    )

    note = "" if quote_available else "该标的行情源不提供盘口数据（换手率/量比/市值显示为 —）"
    return TodayOverviewDTO(
        as_of=assessment.as_of.isoformat(),
        quote_available=quote_available,
        quote_note_cn=note,
        price=price,
        technical=technical,
        volume=volume,
        capital=capital,
        signal=signal,
    )


__all__ = ["build_today_overview"]
