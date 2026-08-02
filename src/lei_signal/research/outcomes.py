"""历史有效性研究：后续收益、MFE/MAE、ATR 目标、C/B1 路径。

不模拟真实交易仓位，只研究「信号出现后客观走势」。

统计口径：
  * 一律按 available_date 对齐（形态确认日，不是拐点日）。
  * 连续绿色只算一次开始事件（事件层已按区段起始产生事件）。
  * 同一结构的阶段升级共享 structure_id，可分别研究也可按结构聚类。
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from lei_signal.domain.types import STAGE_CN, Stage
from lei_signal.events.lifecycle import END_SUB_RULES

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


def _as_float(value: object) -> float | None:
    """把 row 中的数值安全转成 float；None / NaN / 非数值一律返回 None。

    存在的意义：``row`` 的静态类型是 ``dict[str, object]``，直接对取回的值
    做算术运算既不类型安全也容易把 NaN 当成有效数字使用。
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float | np.number):
        number = float(value)
        return None if math.isnan(number) else number
    return None


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
        # 结束标记事件（*_ended / top_warning_invalidated_by_new_high）方向为 neutral，
        # 不是持续信号，绝不参与后续收益 / MFE / MAE 统计，否则会污染样本数、
        # 均值与方向命中率。它们只用于「结束某状态」，由解释层与生命周期处理。
        if sub_rule in END_SUB_RULES:
            continue
        key = f"{event.rule_id}:{sub_rule}" if sub_rule else event.rule_id
        tier = event.evidence.get("tier")
        buy_flag = event.evidence.get("is_buy_signal")
        records.append(
            _outcome_row(
                signal_key=key,
                signal_kind="atomic",
                transition_kind=None,
                signal_tier=tier if isinstance(tier, str) else None,
                is_buy_signal=buy_flag if isinstance(buy_flag, bool) else None,
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

    # --- 组合机会阶段起点（修复 5：必须使用 opportunity_stage）---
    # 风险状态产生的变化不参与此处的「机会阶段」记录。
    # 同一机会阶段在风险期间保持不变，风险解除后不应被错误地记为新信号。
    #
    # 类型体系（兼容方案）：
    #   signal_kind    仍然只有 "atomic" / "stage" 两种，保持旧测试与 UI 契约不变；
    #   transition_kind 为新增的**独立**维度，机会阶段转换 = "opportunity"，
    #                   原子事件 = None。风险状态转换不进入本表，
    #                   由 build_risk_transitions() 单独产出。
    previous_opportunity: Stage | None = None
    for state in result.history:
        timestamp = pd.Timestamp(state.day)
        if timestamp not in position_of:
            previous_opportunity = state.opportunity_stage
            continue
        # 只在 opportunity_stage 「进入」时记录一次
        if (
            state.opportunity_stage in _OPPORTUNITY_STAGES
            and state.opportunity_stage != previous_opportunity
        ):
            records.append(
                _outcome_row(
                    signal_key=f"stage:{state.opportunity_stage.value}",
                    signal_kind="stage",
                    transition_kind="opportunity",
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
        # 关键：无论是否记录，都必须推进 previous_opportunity，
        # 否则同一机会阶段的连续日会被重复记为新信号。
        previous_opportunity = state.opportunity_stage

    if not records:
        return pd.DataFrame()

    outcomes = pd.DataFrame(records)
    if not outcomes.empty:
        outcomes["year"] = pd.to_datetime(outcomes["available_date"]).dt.year
        outcomes["asset_class"] = infer_asset_class(result.symbol)
    return outcomes


def build_risk_transitions(result: AnalysisResult) -> pd.DataFrame:
    """风险状态转换表（修复 5：与机会阶段**分表**统计）。

    设计决定（明确记录，避免以后又混回去）：
      * 风险状态转换**不参加**收益研究，因此**不进入** ``build_forward_outcomes``
        产出的 outcomes 表。outcomes 表要求每行都具备完整的收益 / MFE / MAE /
        C / B1 字段，而风险转换只是状态机的状态变化，没有对应的「信号方向」，
        强行塞进去会污染 ``summarize_by_rule`` 的方向命中率与样本数。
      * 因此这里只保存**状态转换事实**：何时、从什么风险状态、变成什么风险状态。
      * 若将来确实要研究风险状态的后续走势，必须改为调用 ``_outcome_row()``
        并给出明确的 direction，而不是继续追加轻量字典。

    返回列：``day`` / ``from_risk_state`` / ``to_risk_state`` / ``color`` /
    ``opportunity_stage``（同日机会阶段，便于核对两条线确实独立）。
    """
    rows: list[dict[str, object]] = []
    previous_risk = None
    for state in result.history:
        if previous_risk is not None and state.risk_state != previous_risk:
            rows.append(
                {
                    "day": state.day,
                    "from_risk_state": previous_risk.value,
                    "to_risk_state": state.risk_state.value,
                    "color": state.color.value,
                    "opportunity_stage": state.opportunity_stage.value,
                }
            )
        previous_risk = state.risk_state
    return pd.DataFrame(rows)


def _outcome_row(
    *,
    signal_key: str,
    signal_kind: str,
    transition_kind: str | None,
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
    signal_tier: str | None = None,
    is_buy_signal: bool | None = None,
) -> dict[str, object]:
    """单个信号实例的后续走势。所有窗口都严格向前，不使用信号日之前的数据。"""
    entry_close = float(close.iloc[position])
    row: dict[str, object] = {
        "signal_key": signal_key,
        "signal_kind": signal_kind,
        "transition_kind": transition_kind,
        # 分档维度：EMA20 早期转强的 early_watch / structure_confirmed /
        # joint_confirmed / long_trend_improved。其余信号为 None。
        # 有了它就不必在下游靠切 signal_key 字符串来还原档位。
        "signal_tier": signal_tier,
        # early_watch 是观察不是买入，聚合时必须能一键剔除。
        "is_buy_signal": is_buy_signal,
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

    # C 路径（修复 6.2）：优先使用事件自身关联结构的 C；
    # 若事件没有关联结构，则用信号当天主结构 C，并标记为「推断」口径。
    c_price, c_source = _c_price_with_source(result, available_date, structure_id)
    row["c_price"] = c_price
    row["c_source"] = c_source   # "own_structure" | "inferred_primary"
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

    # 方向标准化（修复 6.1）
    #
    # 看多信号：调整值 = 原始值。
    # 看空信号：
    #   * 收益取反（下跌 = 方向正确）；
    #   * MFE/MAE 必须**先交换再取反**，不能只取反：
    #     对看空而言「有利极值」是原始最低点，「不利极值」是原始最高点，
    #       bearish adjusted MFE = -(raw MAE)
    #       bearish adjusted MAE = -(raw MFE)
    #     若只取反不交换，会得到 adjusted MFE < adjusted MAE 的非法结果。
    is_bearish = direction in ("bearish", "risk")
    for horizon in HORIZONS:
        raw_return = _as_float(row.get(f"fwd_return_{horizon}"))
        raw_mfe = _as_float(row.get(f"mfe_{horizon}"))
        raw_mae = _as_float(row.get(f"mae_{horizon}"))

        if raw_return is None:
            row[f"direction_adjusted_return_{horizon}"] = np.nan
            row[f"direction_hit_{horizon}"] = None
        else:
            row[f"direction_adjusted_return_{horizon}"] = (
                -raw_return if is_bearish else raw_return
            )
            row[f"direction_hit_{horizon}"] = (
                raw_return < 0.0 if is_bearish else raw_return > 0.0
            )

        # 有利/不利极值按方向取原始序列的对应端点
        favourable = raw_mae if is_bearish else raw_mfe
        adverse = raw_mfe if is_bearish else raw_mae
        row[f"mfe_adjusted_{horizon}"] = (
            np.nan
            if favourable is None
            else (-favourable if is_bearish else favourable)
        )
        row[f"mae_adjusted_{horizon}"] = (
            np.nan if adverse is None else (-adverse if is_bearish else adverse)
        )

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


def _c_price_with_source(
    result: AnalysisResult,
    day: object,
    structure_id: str | None,
) -> tuple[float | None, str]:
    """优先返回事件自身关联结构的 C；否则用当天主结构 C，并标注推断口径。

    返回 ``(c_price, source)``：source 为
      * ``"own_structure"`` —— 事件带 structure_id 且对应结构仍存在；
      * ``"inferred_primary"`` —— 事件无关联结构，使用当天主结构（推断）；
      * ``"unavailable"`` —— 没有任何结构。
    """
    if structure_id is not None:
        for structure in result.structures:
            if structure.structure_id == structure_id and structure.c_price is not None:
                return structure.c_price, "own_structure"
    inferred = _c_price_on(result, day)
    if inferred is not None:
        return inferred, "inferred_primary"
    return None, "unavailable"


def infer_asset_class(symbol: str) -> str:
    """尽量可靠地推断资产类别；无法判断时返回 unknown。"""
    s = symbol.upper()
    if s.endswith(".SS") or s.endswith(".SZ"):
        return "cn_equity"
    if s.endswith(".HK"):
        return "hk_equity"
    if s.endswith((".L", ".LSE", ".LON")):
        return "uk_equity"
    if s.endswith((".T", ".TYO", ".JPX")):
        return "jp_equity"
    if s.endswith((".KS", ".KSE")):
        return "kr_equity"
    # 常见 ETF 后缀：QQQ, SPY, IWM, 510300.SS, 159915.SZ
    if s.isalpha() and len(s) <= 5:
        # 简单启发：3 字母全字母 → 可能是美股 ETF 或股票
        return "us_equity_or_etf"
    return "unknown"


def _b1_price_on(result: AnalysisResult, day: object, close: float) -> float | None:
    from datetime import date as date_type

    from lei_signal.rules.resistance_b1 import find_b1

    if not isinstance(day, date_type):
        return None
    b1 = find_b1(result.pivots, as_of=day, current_close=close)
    return b1.price if b1 else None


def summarize_by_rule(outcomes: pd.DataFrame, *, horizon: int = 20) -> pd.DataFrame:
    """按信号汇总：样本数、方向命中率、均值、中位数。

    看多信号：方向命中率 = 后续上涨比例。
    看空/风险信号：方向命中率 = 后续下跌比例（即对信号方向有利）。
    列名清楚写明「方向命中」，避免把 bearish 信号后下跌显示为 0%。
    """
    raw_column = f"fwd_return_{horizon}"
    adj_column = f"direction_adjusted_return_{horizon}"
    hit_column = f"direction_hit_{horizon}"
    if outcomes.empty or raw_column not in outcomes.columns:
        return pd.DataFrame()

    rows: list[dict[str, object]] = []
    for key, group in outcomes.groupby("signal_key"):
        valid_raw = group[raw_column].dropna()
        valid_adj = group[adj_column].dropna() if adj_column in group else pd.Series(dtype=float)
        hit_series = group[hit_column] if hit_column in group else pd.Series(dtype=object)
        valid_hit = hit_series.dropna()
        rows.append(
            {
                "信号": key,
                "类型": "组合阶段" if str(key).startswith("stage:") else "原子信号",
                "样本数": len(group),
                "有效样本": len(valid_raw),
                f"{horizon}日均值%": round(valid_raw.mean(), 3) if not valid_raw.empty else None,
                f"{horizon}日中位数%": (
                    round(valid_raw.median(), 3) if not valid_raw.empty else None
                ),
                f"{horizon}日方向调整均值%": (
                    round(valid_adj.mean(), 3) if not valid_adj.empty else None
                ),
                "方向命中率": (
                    round(float(valid_hit.astype(bool).mean()), 3)
                    if not valid_hit.empty else None
                ),
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
    """顶部警报后续结果——按**最早发生**的事件分类（修复 6.3）。

    每个顶部独立观察：
      * 若首先出现「转黑」日 → 计入「转为黑色」；
      * 否则若首先出现「创新高解除」日 → 计入「新高解除」；
      * 否则在样本末仍未发生 → 计入「截至样本末未发生」。
    旧实现会因为最终创新高而忽略此前已经先转黑，违反时间顺序。
    """
    tops = [s for s in result.structures if s.side == "top" and s.confirmed_date is not None]
    if not tops:
        return pd.DataFrame()

    frame = result.frame
    turned_black = resolved_by_high = kept_rising = 0
    for top in tops:
        after = frame.loc[frame.index > pd.Timestamp(top.confirmed_date)]
        if after.empty:
            kept_rising += 1
            continue
        # 第一次出现「转黑」或「新高解除」按时间顺序先到者
        black_days = after.index[after["signal_color"].eq("black")]
        first_black = black_days[0] if len(black_days) > 0 else None
        new_high_day = (
            top.invalidated_date
            if top.invalidated_reason == "top_warning_invalidated_by_new_high"
            and top.invalidated_date is not None
            and pd.Timestamp(top.invalidated_date) in after.index
            else None
        )
        # 决定谁先到
        if first_black is not None and new_high_day is not None:
            if first_black <= pd.Timestamp(new_high_day):
                turned_black += 1
            else:
                resolved_by_high += 1
        elif first_black is not None:
            turned_black += 1
        elif new_high_day is not None:
            resolved_by_high += 1
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
    "build_risk_transitions",
    "gray_transition_stats",
    "infer_asset_class",
    "stage_label",
    "summarize_by_rule",
    "top_transition_stats",
]
