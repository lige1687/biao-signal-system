"""模块 A 交易生命周期模拟（规格 §3.3 / §9 A5-A6 / §16）。

执行纪律（全部来自规格，不发明）：
- 信号在 t 收盘生成，**t+1 开盘入场**（§3.3）；
- A = 实际入场价（t+1 开盘）、C = 结构失效价（事件携带，§9 A5）、
  B = 目标价（信号时已存在的数据，§10，由 reward_risk_filter 计算）；
- 退出信号同样收盘确认、**下一根开盘执行**；跳空越过退出价时按开盘价
  记账（§3.3 建议）；
- A6 三版退出（规格 §9 A6）分别模拟、分别统计：
  1. 抵扣价退出：收盘同时 close < EMA20 且 close < close_lag20（§8.1）；
  2. 顶部构造出现后、再出现反向关键性波动（顶部确认日 > 入场日 且 当日
     关键性波动条件成立）；
  3. 仅初始结构止损 C。
- 初始结构止损 C 在三版中始终有效（§14：进场后 A/C 不得漂移）；
- 盈亏比过滤（§10）：R/R = (B−A_ref)/(A_ref−C)（A_ref = 信号日收盘，
  信号时点可得、无泄漏），低于 rr_min 的信号不入场；B 不可计算时标记
  「目标不可计算」，同样不入场（§13 条 4）；
- 费用（账本 fees_and_slippage，〔标定 V2.1〕）：股票单边
  max(5bp 名义值, $0.005/股)（保守档 10bp），敏感性 0/5/10bp 三档全跑；
  R 口径：r_net = ((exit/entry − 1) − round_trip_fraction) × entry / (entry − C)。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from lei_signal.domain.rules_config import get_rule
from lei_signal.domain.types import SignalEvent
from lei_signal.features.indicators import average_true_range
from lei_signal.rules.clock_classifier import clock_series
from lei_signal.rules.first_ma_pullback import (
    ENTRY_CONFIRMED,
    ENTRY_EARLY,
)
from lei_signal.rules.gap_events import GapEvent
from lei_signal.rules.reward_risk_filter import compute_reward_risk
from lei_signal.rules.strict_structure import SIDE_TOP, detect_strict_structures
from lei_signal.rules.trend_stage import trend_stage_series

EXIT_COSTBASIS = "a6_1_costbasis"
EXIT_TOP_PLUS_KEYWAVE = "a6_2_top_plus_keywave"
EXIT_STRUCTURE_STOP = "a6_3_structure_stop"
EXIT_B3_DUAL = "b3_dual"
EXIT_VARIANTS = (
    EXIT_COSTBASIS,
    EXIT_TOP_PLUS_KEYWAVE,
    EXIT_STRUCTURE_STOP,
    EXIT_B3_DUAL,
)

EXIT_VARIANT_CN = {
    EXIT_COSTBASIS: "A6① 抵扣价退出",
    EXIT_TOP_PLUS_KEYWAVE: "A6② 顶部构造+关键性波动",
    EXIT_STRUCTURE_STOP: "A6③ 仅初始结构止损",
    EXIT_B3_DUAL: "B3 双条件退出（跌回密集区上沿+破20组下弯；底线=排列破坏）",
}


@dataclass(frozen=True, slots=True)
class FeeModel:
    """单边费用模型（账本 fees_and_slippage；label: none/standard/conservative）。"""

    label: str
    per_side_bps: float
    per_share_usd: float

    @classmethod
    def from_ledger(cls, label: str) -> FeeModel:
        spec = get_rule("fees_and_slippage")
        per_share = float(spec.param("stock_per_share_usd", 0.005))
        if label == "none":
            return cls(label="none", per_side_bps=0.0, per_share_usd=0.0)
        if label == "conservative":
            return cls(label="conservative", per_side_bps=10.0, per_share_usd=per_share)
        bps = float(spec.param("stock_fee_bps", 5.0))
        return cls(label="standard", per_side_bps=bps, per_share_usd=per_share)

    def round_trip_fraction(self, price: float) -> float:
        """往返费用占价格的比率 = 2 x max(bps, 每股费/价格)。"""
        if price <= 0:
            return 0.0
        per_side = max(self.per_side_bps / 10_000.0, self.per_share_usd / price)
        return 2.0 * per_side


#: 四个交易模块的入场事件契约：rule_id / 确认子规则 / 变体字段 / 变体取值。
#: D 单版本（无变体字段）。变体事件按 evidence 对应字段匹配。
MODULE_ENTRY_CONTRACT: dict[str, dict] = {
    "A": {
        "rule_id": "first_ma_pullback",
        "confirmed_sub": "first_ma_pullback_confirmed",
        "variant_field": "entry_variant",
        "variants": ("early", "confirmed"),
    },
    "B": {
        "rule_id": "dense_breakout",
        "confirmed_sub": "dense_breakout_confirmed",
        "variant_field": "variant",
        "variants": ("ambush", "breakout"),
    },
    "C": {
        "rule_id": "two_b_reversal",
        "confirmed_sub": None,  # 三个子规则各自确认：v1/v2/v3_confirmed
        "variant_field": "version",
        "variants": ("v1", "v2", "v3"),
    },
    "D": {
        "rule_id": "module_d_false_breakout",
        "confirmed_sub": "module_d_long_confirmed",
        "variant_field": None,
        "variants": (None,),
    },
}


@dataclass(frozen=True, slots=True)
class EntrySpec:
    """一次通过过滤的入场信号（全部字段在信号日可得，无泄漏）。"""

    symbol: str
    signal_date: date
    signal_position: int          # 信号日位置（入场在 signal_position+1 开盘）
    entry_ref_price: float        # 信号日收盘（A_ref，R/R 与目标计算用）
    stop_price: float             # C（结构失效价）
    target_price: float | None    # B（None = 目标不可计算）
    target_source: str | None
    reward_risk: float | None
    entry_variant: str
    is_first_touch: bool
    ma_period: int
    clock_type: int
    weekly_bull_env: bool
    event_id: str
    entry_reason: str = ""
    trend_stage: int = 0               # 入场时趋势五步（账本 trend_stage，0=未起步）
    breakout_reference: float | None = None  # 密集区上沿（B3 双条件退出用；非 B 模块为 None）


@dataclass(slots=True)
class Trade:
    """一笔已执行的交易（R 归一，规格 §16）。"""

    symbol: str
    entry_variant: str
    exit_variant: str
    is_first_touch: bool
    ma_period: int
    clock_type: int
    weekly_bull_env: bool
    signal_date: date
    entry_date: date
    entry_price: float
    stop_price: float
    target_price: float | None
    reward_risk: float | None
    exit_date: date | None = None
    exit_price: float | None = None
    exit_reason: str | None = None
    holding_bars: int = 0
    r_gross: float | None = None
    r_net: float | None = None
    benchmark_clock_type: int = 0
    trend_stage: int = 0               # 入场时趋势五步（供 §16 分组）
    meta: dict = field(default_factory=dict)  # entry_reason 等入场依据原文

    @property
    def is_open(self) -> bool:
        return self.exit_date is None


def prepare_frame(frame: pd.DataFrame) -> dict:
    """预计算引擎需要的派生序列（同一 frame 多次模拟时只算一遍）。"""
    atr20 = average_true_range(frame, 20)
    costbasis_cond = (frame["close"] < frame["ema20"]) & (
        frame["close"] < frame["close_lag20"]
    )
    top_dates = sorted(
        s.confirmed_date
        for s in detect_strict_structures(frame)
        if s.side == SIDE_TOP
    )
    return {
        "atr20": atr20,
        "costbasis_cond": costbasis_cond,
        "top_dates": top_dates,
        "clock": clock_series(frame),
    }


def entry_specs_from_events(
    frame: pd.DataFrame,
    events: list[SignalEvent],
    symbol: str,
    *,
    entry_variant: str | None = None,
    rr_min: float | None = None,
    pivots: tuple = (),  # noqa: ANN001 - features.pivots.Pivot 元组
    module: str = "A",
    gaps: list[GapEvent] | None = None,  # 传入即启用目标 B 缺口档（规格 §10 第 2 档）
) -> tuple[list[EntrySpec], int, int]:
    """把模块（默认 A）的 confirmed 事件转成入场信号。

    entry_variant 传 None 时取该模块第一个变体（A=early、C=v1、D=None）。
    返回 (specs, filtered_by_rr, filtered_no_target)；rr_min=None 表示
    不过滤（对照组）。gaps 非空时目标 B 优先级启用「未回补缺口」档。
    """
    contract = MODULE_ENTRY_CONTRACT[module]
    rule_id = contract["rule_id"]
    variant_field = contract["variant_field"]
    if entry_variant is None:
        entry_variant = contract["variants"][0]
    confirmed_subs = (
        (contract["confirmed_sub"],)
        if contract["confirmed_sub"] is not None
        else tuple(f"two_b_reversal_{v}_confirmed" for v in ("v1", "v2", "v3"))
    )

    by_day = {ts.date(): pos for pos, ts in enumerate(frame.index)}
    stages = trend_stage_series(frame)
    specs: list[EntrySpec] = []
    filtered_by_rr = 0
    filtered_no_target = 0
    for event in events:
        if event.rule_id != rule_id:
            continue
        if event.evidence.get("sub_rule") not in confirmed_subs:
            continue
        if variant_field is not None and str(
            event.evidence.get(variant_field, "")
        ) != str(entry_variant):
            continue
        position = by_day.get(event.available_date)
        if position is None:
            continue
        close = float(event.evidence.get("entry_ref_close", event.evidence.get("close", 0)))
        stop = event.evidence.get("stop_price")
        if stop is None or close <= float(stop):
            continue  # 风险非正：不入场（§13 条 3）
        rr = compute_reward_risk(frame, event, pivots, gaps=gaps)
        if rr.reward_risk is None:
            filtered_no_target += 1
            if rr_min is not None:
                continue
        if rr_min is not None and (rr.reward_risk is None or rr.reward_risk < rr_min):
            filtered_by_rr += 1
            continue
        # 密集区上沿（B3 双条件退出用）：突破版直接读 breakout_reference，
        # 埋伏版读确认时的密集区上沿 reference_price；非 B 模块两者皆无。
        reference = event.evidence.get("breakout_reference")
        if reference is None:
            reference = event.evidence.get("reference_price")
        specs.append(
            EntrySpec(
                symbol=symbol,
                signal_date=event.available_date,
                signal_position=position,
                entry_ref_price=close,
                stop_price=float(stop),
                target_price=rr.target_b,
                target_source=rr.target_source,
                reward_risk=rr.reward_risk,
                entry_variant=str(entry_variant),
                is_first_touch=bool(event.evidence.get("is_first_touch", False)),
                ma_period=int(event.evidence.get("ma_period", 0)),
                clock_type=int(event.evidence.get("clock_type", 0)),
                weekly_bull_env=bool(event.evidence.get("weekly_bull_env", False)),
                trend_stage=int(stages.iloc[position]),
                event_id=event.event_id,
                entry_reason=str(getattr(event, "reason_cn", "")),
                breakout_reference=float(reference) if reference is not None else None,
            )
        )
    return specs, filtered_by_rr, filtered_no_target


def is_cn_symbol(symbol: str) -> bool:
    """A 股标的（含 ETF/个股；TH 板块指数无涨跌停，不计入）。"""
    return (symbol.endswith(".SS") or symbol.endswith(".SZ")) and not symbol.startswith("TH")


def simulate_trade(
    frame: pd.DataFrame,
    spec: EntrySpec,
    *,
    exit_variant: str,
    fee: FeeModel,
    prepared: dict,
    limit_guard: bool = False,
) -> Trade:
    """模拟一笔交易：t+1 开盘入场，收盘确认退出信号、下一根开盘执行。

    limit_guard=True 时对 A 股标的施加涨跌停约束（简化 10% 档）：
    入场日开盘较昨收涨幅 >= 9.5% 视为涨停买不进（信号作废，不计入笔数）；
    退出日开盘较昨收跌幅 <= -9.5% 视为跌停卖不出（顺延至下一可交易日开盘）。
    """
    entry_position = spec.signal_position + 1
    if (
        limit_guard
        and is_cn_symbol(spec.symbol)
        and entry_position < len(frame)
        and entry_position >= 1
    ):
        prev_close = float(frame["close"].iloc[entry_position - 1])
        open_price = float(frame["open"].iloc[entry_position])
        if prev_close > 0 and open_price >= prev_close * 1.095:
            return Trade(
                symbol=spec.symbol,
                entry_variant=spec.entry_variant,
                exit_variant=exit_variant,
                is_first_touch=spec.is_first_touch,
                ma_period=spec.ma_period,
                clock_type=spec.clock_type,
                weekly_bull_env=spec.weekly_bull_env,
                trend_stage=spec.trend_stage,
                signal_date=spec.signal_date,
                entry_date=frame.index[entry_position].date(),
                entry_price=open_price,
                stop_price=spec.stop_price,
                target_price=spec.target_price,
                reward_risk=spec.reward_risk,
                exit_reason="skipped_limit_up_at_entry",
            )
    if entry_position >= len(frame):
        # 信号在数据最后一根：尚未入场，计为未平仓（信号本身有效）。
        return Trade(
            symbol=spec.symbol,
            entry_variant=spec.entry_variant,
            exit_variant=exit_variant,
            is_first_touch=spec.is_first_touch,
            ma_period=spec.ma_period,
            clock_type=spec.clock_type,
            weekly_bull_env=spec.weekly_bull_env,
            trend_stage=spec.trend_stage,
            signal_date=spec.signal_date,
            entry_date=spec.signal_date,
            entry_price=spec.entry_ref_price,
            stop_price=spec.stop_price,
            target_price=spec.target_price,
            reward_risk=spec.reward_risk,
            exit_reason="signal_at_end_not_entered",
        )
    trade = Trade(
        symbol=spec.symbol,
        entry_variant=spec.entry_variant,
        exit_variant=exit_variant,
        is_first_touch=spec.is_first_touch,
        ma_period=spec.ma_period,
        clock_type=spec.clock_type,
        weekly_bull_env=spec.weekly_bull_env,
        trend_stage=spec.trend_stage,
        signal_date=spec.signal_date,
        entry_date=frame.index[entry_position].date(),
        entry_price=float(frame["open"].iloc[entry_position]),
        stop_price=spec.stop_price,
        target_price=spec.target_price,
        reward_risk=spec.reward_risk,
        meta={"entry_reason": spec.entry_reason},
    )
    risk = trade.entry_price - spec.stop_price
    if risk <= 0:
        trade.exit_reason = "invalid_nonpositive_risk"
        trade.exit_date = trade.entry_date
        trade.exit_price = trade.entry_price
        trade.r_gross = 0.0
        trade.r_net = 0.0
        return trade

    costbasis = prepared["costbasis_cond"]
    top_dates = prepared["top_dates"]
    tops_since_entry = [d for d in top_dates if spec.signal_date < d]

    def close_at(position: int, reason: str) -> Trade:
        exit_position = position + 1
        # A 股跌停无法卖出：顺延到下一根开盘（涨跌停约束开启时）。
        while (
            limit_guard
            and is_cn_symbol(spec.symbol)
            and exit_position < len(frame)
            and exit_position >= 1
            and float(frame["close"].iloc[exit_position - 1]) > 0
            and float(frame["open"].iloc[exit_position])
            <= float(frame["close"].iloc[exit_position - 1]) * 0.905
        ):
            exit_position += 1
        if exit_position >= len(frame):
            trade.exit_reason = f"{reason}(数据末尾未执行)"
            trade.holding_bars = position - entry_position
            return trade
        trade.exit_date = frame.index[exit_position].date()
        trade.exit_price = float(frame["open"].iloc[exit_position])
        trade.exit_reason = reason
        trade.holding_bars = exit_position - entry_position
        gross = (trade.exit_price - trade.entry_price) / risk
        fees = fee.round_trip_fraction(trade.entry_price)
        trade.r_gross = gross
        trade.r_net = ((trade.exit_price / trade.entry_price - 1.0) - fees) * (
            trade.entry_price / risk
        )
        return trade

    for position in range(entry_position, len(frame)):
        close = float(frame["close"].iloc[position])
        if close < spec.stop_price:
            return close_at(position, "structure_stop_C")
        if exit_variant == EXIT_COSTBASIS and bool(costbasis.iloc[position]):
            return close_at(position, "exit_a6_1_costbasis")
        if exit_variant == EXIT_TOP_PLUS_KEYWAVE:
            has_top = any(d <= frame.index[position].date() for d in tops_since_entry)
            if has_top and bool(costbasis.iloc[position]):
                return close_at(position, "exit_a6_2_top_plus_keywave")
        if exit_variant == EXIT_STRUCTURE_STOP:
            continue  # A6③：仅初始结构止损
        if exit_variant == EXIT_B3_DUAL:
            # 规格 §9 B3（两动作不分先后、必须全部满足）：
            #   1) 收盘跌回密集区上沿下方（close < breakout_reference）
            #   2) 跌破 20 均线组且 20 组向下弯曲（close < SMA20 且 close < close_lag20）
            # 两动作**同日**成立 -> 次日开盘退出。
            # 埋伏单底线（独立触发，不与双条件联立）：多头排列被破坏
            # （SMA20 <= SMA60，规格「20 组与 60 组完成交叉或不可避免要交叉」）。
            row = frame.iloc[position]
            ref = spec.breakout_reference
            cond_back = ref is None or close < float(ref)
            cond_break_ma20 = (
                close < float(row["sma20"]) and close < float(row["close_lag20"])
            )
            cond_alignment_breaks = float(row["sma20"]) <= float(row["sma60"])
            if (cond_back and cond_break_ma20) or cond_alignment_breaks:
                return close_at(position, "exit_b3_dual")
    trade.holding_bars = len(frame) - 1 - entry_position
    trade.exit_reason = "open_at_end"
    return trade


__all__ = [
    "EXIT_COSTBASIS",
    "EXIT_STRUCTURE_STOP",
    "EXIT_TOP_PLUS_KEYWAVE",
    "EXIT_VARIANTS",
    "EXIT_VARIANT_CN",
    "ENTRY_CONFIRMED",
    "ENTRY_EARLY",
    "EntrySpec",
    "FeeModel",
    "Trade",
    "entry_specs_from_events",
    "prepare_frame",
    "simulate_trade",
]
