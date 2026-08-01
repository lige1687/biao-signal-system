"""历史有效性研究：后续收益、MFE/MAE、ATR 目标、C/B1 路径。

不模拟真实交易仓位，只研究「信号出现后客观走势」。

统计口径：
  * 一律按 available_date 对齐（形态确认日，不是拐点日）。
  * 连续绿色只算一次开始事件（事件层已按区段起始产生事件）。
  * 同一结构的阶段升级共享 structure_id，可分别研究也可按结构聚类。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from lei_signal.domain.types import STAGE_CN, Stage

if TYPE_CHECKING:
    from lei_signal.compose.pipeline import AnalysisResult

HORIZONS = (1, 5, 10, 20, 60, 120)

#: 用于组合阶段研究的机会阶段（风险阶段不作为「机会信号」统计）
_OPPORTUNITY_STAGES = (
    Stage.BOTTOM_WATCH,
    Stage.STRUCTURE_CONFIRMED,
    Stage.EARLY_STRENGTH,
    Stage.JOINT_CONFIRMED,
    Stage.TREND_REINFORCED,
)


def _market_state(frame: pd.DataFrame) -> pd.Series:
    """粗粒度市场状态，用于分组与匹配基准。

    使用 EMA60/EMA120 关系与颜色，是可复核的工程划分（research_proxy）。
    """
    ema60 = frame.get("ema60")
    ema120 = frame.get("ema120")
    if ema60 is None or ema120 is None:
        return pd.Series("unknown", index=frame.index)
    state = pd.Series("unknown", index=frame.index, dtype=object)
    ready = ema60.notna() & ema120.notna()
    state[ready & (ema60 > ema120)] = "long_bull"
    state[ready & (ema60 <= ema120)] = "long_bear"
    return state


def build_forward_outcomes(result: AnalysisResult) -> pd.DataFrame:
    """为每个信号事件与每个组合阶段起点计算后续走势。

    返回每行一个「信号实例」，含 signal_key、structure_id、
    各期收益、MFE/MAE、ATR 目标天数、C/B1 路径。
    """
    frame = result.frame
    if frame.empty:
        return pd.DataFrame()

    close = frame["close"].astype(float)
    high = frame["high"].astype(float)
    low = frame["low"].astype(float)
    atr = frame.get("atr14")
    market_state = _market_state(frame)
    position_of = {timestamp: index for index, timestamp in enumerate(frame.index)}

    records: list[dict[str, object]] = []

    # --- 原子信号事件 ---
    for event in result.events:
        timestamp = pd.Timestamp(event.available_date)
        if timestamp not in position_of:
            continue
        sub_rule = event.evidence.get("sub_rule")
        key = f"{event.rule_id}:{sub_rule}" if sub_rule else event.rule_id
        records.append(
            _outcome_row(
                signal_key=key,
                signal_kind="atomic",
                event_date=event.event_date,
                available_date=event.available_date,
                position=position_of[timestamp],
                frame=frame,
                close=close,
                high=high,
                low=low,
                atr=atr,
                market_state=market_state,
                structure_id=event.structure_id,
                direction=event.direction.value,
                rule_version=event.rule_version,
                provenance=event.provenance.value,
                result=result,
            )
        )

    # --- 组合阶段起点 ---
    previous_stage: Stage | None = None
    for state in result.history:
        timestamp = pd.Timestamp(state.day)
        if timestamp not in position_of:
            previous_stage = state.stage
            continue
        # 只在阶段「进入」时记录一次，避免连续同阶段每天都算一个信号
        if state.stage in _OPPORTUNITY_STAGES and state.stage != previous_stage:
            records.append(
                _outcome_row(
                    signal_key=f"stage:{state.stage.value}",
                    signal_kind="stage",
                    event_date=state.day,
                    available_date=state.day,
                    position=position_of[timestamp],
                    frame=frame,
                    close=close,
                    high=high,
                    low=low,
                    atr=atr,
                    market_state=market_state,
                    structure_id=(
                        state.primary_bottom.structure_id
                        if state.primary_bottom is not None
                        else None
                    ),
                    direction="bullish",
                    rule_version="1.0.0",
                    provenance="lei_inferred",
                    result=result,
                )
            )
        previous_stage = state.stage

    if not records:
        return pd.DataFrame()

    outcomes = pd.DataFrame(records)
    outcomes["year"] = pd.to_datetime(outcomes["available_date"]).dt.year
    return outcomes


def _outcome_row(
    *,
    signal_key: str,
    signal_kind: str,
    event_date: object,
    available_date: object,
    position: int,
    frame: pd.DataFrame,
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    atr: pd.Series | None,
    market_state: pd.Series,
    structure_id: str | None,
    direction: str,
    rule_version: str,
    provenance: str,
    result: AnalysisResult,
) -> dict[str, object]:
    """单个信号实例的后续走势。所有窗口都严格向前，不使用信号日之前的数据。"""
    entry_close = float(close.iloc[position])
    row: dict[str, object] = {
        "signal_key": signal_key,
        "signal_kind": signal_kind,
        "event_date": event_date,
        "available_date": available_date,
        "structure_id": structure_id,
        "direction": direction,
        "rule_version": rule_version,
        "provenance": provenance,
        "entry_close": entry_close,
        "market_state": market_state.iloc[position],
        "color_at_signal": frame["signal_color"].iloc[position],
    }

    total = len(frame)
    for horizon in HORIZONS:
        end = position + horizon
        if end < total:
            row[f"fwd_return_{horizon}"] = (
                float(close.iloc[end]) / entry_close - 1.0
            ) * 100.0
        else:
            row[f"fwd_return_{horizon}"] = np.nan

        window_end = min(end, total - 1)
        if window_end > position:
            window_high = float(high.iloc[position + 1 : window_end + 1].max())
            window_low = float(low.iloc[position + 1 : window_end + 1].min())
            row[f"mfe_{horizon}"] = (window_high / entry_close - 1.0) * 100.0
            row[f"mae_{horizon}"] = (window_low / entry_close - 1.0) * 100.0
        else:
            row[f"mfe_{horizon}"] = np.nan
            row[f"mae_{horizon}"] = np.nan

    # ATR 目标首次达成天数
    atr_value = (
        float(atr.iloc[position])
        if atr is not None and pd.notna(atr.iloc[position])
        else None
    )
    for label, multiple, is_upside in (
        ("plus_1atr", 1.0, True),
        ("plus_2atr", 2.0, True),
        ("minus_1atr", -1.0, False),
    ):
        days: float = np.nan
        reached = False
        if atr_value and atr_value > 0:
            target = entry_close + multiple * atr_value
            future = frame.iloc[position + 1 :]
            if not future.empty:
                if is_upside:
                    hits = future.index[future["high"].astype(float) >= target]
                else:
                    hits = future.index[future["low"].astype(float) <= target]
                if len(hits) > 0:
                    reached = True
                    days = float(
                        frame.index.get_loc(hits[0]) - position
                    )
        row[f"days_to_{label}"] = days
        row[f"reached_{label}"] = reached
    row["atr_at_signal"] = atr_value

    # C 路径：使用信号当天的主结构 C
    c_price = _c_price_on(result, available_date)
    row["c_price"] = c_price
    touched_c = False
    days_to_touch: float = np.nan
    if c_price is not None:
        future = frame.iloc[position + 1 :]
        hits = future.index[future["low"].astype(float) <= c_price]
        if len(hits) > 0:
            touched_c = True
            days_to_touch = float(frame.index.get_loc(hits[0]) - position)
    row["touched_c"] = touched_c
    row["days_to_touch_c"] = days_to_touch

    # B1 路径
    b1_price = _b1_price_on(result, available_date, entry_close)
    row["b1_price"] = b1_price
    reached_b1 = broke_b1 = False
    extension_after_b1: float = np.nan
    if b1_price is not None:
        future = frame.iloc[position + 1 :]
        touch = future.index[future["high"].astype(float) >= b1_price]
        if len(touch) > 0:
            reached_b1 = True
            breakout = future.index[future["close"].astype(float) > b1_price]
            if len(breakout) > 0:
                broke_b1 = True
                after = frame.loc[frame.index > breakout[0]]
                if not after.empty:
                    extension_after_b1 = (
                        float(after["high"].astype(float).max()) / b1_price - 1.0
                    ) * 100.0
    row["reached_b1"] = reached_b1
    row["broke_b1"] = broke_b1
    row["extension_after_b1_pct"] = extension_after_b1
    return row


def _c_price_on(result: AnalysisResult, day: object) -> float | None:
    """信号当天主结构的 C。"""
    for state in result.history:
        if state.day == day:
            if state.primary_bottom is not None:
                return state.primary_bottom.c_price
            return None
    return None


def _b1_price_on(result: AnalysisResult, day: object, close: float) -> float | None:
    from datetime import date as date_type

    from lei_signal.rules.resistance_b1 import find_b1

    if not isinstance(day, date_type):
        return None
    b1 = find_b1(result.pivots, as_of=day, current_close=close)
    return b1.price if b1 else None


def summarize_by_rule(outcomes: pd.DataFrame, *, horizon: int = 20) -> pd.DataFrame:
    """按信号汇总：样本数、均值、中位数、胜率。

    原子信号与组合阶段都保留，不能只展示表现最好的组合。
    """
    column = f"fwd_return_{horizon}"
    if outcomes.empty or column not in outcomes.columns:
        return pd.DataFrame()

    rows: list[dict[str, object]] = []
    for key, group in outcomes.groupby("signal_key"):
        valid = group[column].dropna()
        rows.append(
            {
                "信号": key,
                "类型": "组合阶段" if str(key).startswith("stage:") else "原子信号",
                "样本数": len(group),
                "有效样本": len(valid),
                f"{horizon}日均值%": round(valid.mean(), 3) if not valid.empty else None,
                f"{horizon}日中位数%": round(valid.median(), 3) if not valid.empty else None,
                "胜率": round(float((valid > 0).mean()), 3) if not valid.empty else None,
                "触及C比例": (
                    round(float(group["touched_c"].mean()), 3)
                    if "touched_c" in group else None
                ),
                "到达B1比例": (
                    round(float(group["reached_b1"].mean()), 3)
                    if "reached_b1" in group else None
                ),
                "来源": group["provenance"].iloc[0],
            }
        )
    summary = pd.DataFrame(rows).sort_values(["类型", "样本数"], ascending=[True, False])
    return summary.reset_index(drop=True)


def gray_transition_stats(frame: pd.DataFrame) -> pd.DataFrame:
    """转灰之后恢复绿色或转黑的概率。"""
    if "signal_color" not in frame.columns:
        return pd.DataFrame()
    colors = frame["signal_color"].tolist()
    to_green = to_black = still_gray = 0

    for index in range(1, len(colors)):
        if colors[index] != "gray" or colors[index - 1] == "gray":
            continue
        outcome = "still_gray"
        for future in colors[index + 1 :]:
            if future == "green":
                outcome = "green"
                break
            if future == "black":
                outcome = "black"
                break
        if outcome == "green":
            to_green += 1
        elif outcome == "black":
            to_black += 1
        else:
            still_gray += 1

    total = to_green + to_black + still_gray
    if total == 0:
        return pd.DataFrame()
    return pd.DataFrame(
        [
            {"转灰后结果": "恢复绿色", "次数": to_green, "占比": round(to_green / total, 3)},
            {"转灰后结果": "转为黑色", "次数": to_black, "占比": round(to_black / total, 3)},
            {"转灰后结果": "仍为灰色", "次数": still_gray, "占比": round(still_gray / total, 3)},
        ]
    )


def top_transition_stats(result: AnalysisResult) -> pd.DataFrame:
    """顶部警报后转黑、新高解除或继续上涨的概率。"""
    tops = [s for s in result.structures if s.side == "top" and s.confirmed_date is not None]
    if not tops:
        return pd.DataFrame()

    frame = result.frame
    turned_black = resolved_by_high = kept_rising = 0
    for top in tops:
        after = frame.loc[frame.index > pd.Timestamp(top.confirmed_date)]
        if after.empty:
            continue
        if top.invalidated_reason == "top_warning_invalidated_by_new_high":
            resolved_by_high += 1
            continue
        black_days = after.index[after["signal_color"].eq("black")]
        if len(black_days) > 0:
            turned_black += 1
        else:
            kept_rising += 1

    total = turned_black + resolved_by_high + kept_rising
    if total == 0:
        return pd.DataFrame()
    return pd.DataFrame(
        [
            {"顶部后结果": "转为黑色", "次数": turned_black,
             "占比": round(turned_black / total, 3)},
            {"顶部后结果": "新高解除", "次数": resolved_by_high,
             "占比": round(resolved_by_high / total, 3)},
            {"顶部后结果": "既未转黑也未解除", "次数": kept_rising,
             "占比": round(kept_rising / total, 3)},
        ]
    )


def stage_label(stage_key: str) -> str:
    """把 stage:xxx 转成中文标签。"""
    if stage_key.startswith("stage:"):
        return STAGE_CN.get(stage_key.split(":", 1)[1], stage_key)
    return stage_key


__all__ = [
    "HORIZONS",
    "build_forward_outcomes",
    "gray_transition_stats",
    "stage_label",
    "summarize_by_rule",
    "top_transition_stats",
]
