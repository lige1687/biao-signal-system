"""Bar 完成度三态契约：纯函数层（W2-S1，2026-09-20）。

契约文档见 ``docs/ops/bar-completeness-contract.md``。本模块只做两件事：

1. **数据层三态判定（仅 A股日线）**：``classify_a_share_bar`` 用
   「交易所收盘时间 + 注入式交易日历 + 观测时刻」判定一根日线 bar 的
   完成度 ∈ {partial, final, unknown}。无 IO、无钟点硬编码（收盘时间
   与日历均可注入，默认值只是参数缺省，不是埋在分支里的启发式）。
2. **调用契约守卫**：生产信号路径要求 ``production_signal_requires_final``，
   遇 partial/unknown 的最后一根 bar 必须抛 ``PartialBarError``（拒绝处置，
   二选一中的「拒绝」语义）；研究/回测路径 ``research_allow_partial``，
   允许通过但必须在返回的标注里显式写出 partial/unknown，不得静默当 final。

边界（本阶段冻结）：
- 不改判定引擎、不改 DataFrame 结构：``annotate_bars`` 不往 frame 上加列，
  只返回旁侧标注 ``BarCompletenessReport``；
- 不改 provider 适配器、不改 ``run_signal_scan`` 本体——守卫以调用契约形式
  供编排层在进入生产信号路径前使用，接线属后续阶段；
- 美股判定不做（W2-S2 设计稿范畴）。
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo

import pandas as pd

from lei_signal.data.calendar import TradingCalendar, WeekdayCalendar

#: 三态取值：形成中（partial）/ 已走完（final）/ 无法判定（unknown）。
PARTIAL = "partial"
FINAL = "final"
UNKNOWN = "unknown"

#: A股观测时区。判定口径：观测时刻换算到上海时间后与收盘时间比较。
_CN_TZ = ZoneInfo("Asia/Shanghai")

#: A股日盘收盘时刻（参数缺省值，可注入；不构成硬编码启发式）。
DEFAULT_A_SHARE_CLOSE_TIME = dt.time(15, 0)


class PartialBarError(RuntimeError):
    """生产信号路径遇到未走完（partial）或无法判定（unknown）的 bar。

    拒绝处置：调用方不得把该 bar 当 final 使用，必须整次拒绝并携带
    本异常中的明细（symbol、完成度、bar 日期）。
    """

    def __init__(self, problems: dict[str, tuple[str, pd.Timestamp]]) -> None:
        self.problems = problems
        detail = ", ".join(
            f"{symbol}: last bar {date.date()} is {state}"
            for symbol, (state, date) in sorted(problems.items())
        )
        super().__init__(f"production_signal_requires_final violated: {detail}")


@dataclass(frozen=True)
class BarCompletenessReport:
    """旁侧标注：不修改 DataFrame，只记录每标的最后一根 bar 的完成度。"""

    #: symbol -> (completeness ∈ {partial, final, unknown}, 最后一根 bar 日期)
    last_bar: dict[str, tuple[str, pd.Timestamp]] = field(default_factory=dict)

    @property
    def all_final(self) -> bool:
        return all(state == FINAL for state, _ in self.last_bar.values())

    @property
    def problems(self) -> dict[str, tuple[str, pd.Timestamp]]:
        """非 final 的条目（partial 或 unknown）。"""
        return {
            symbol: item
            for symbol, item in self.last_bar.items()
            if item[0] != FINAL
        }


def classify_a_share_bar(
    bar_date: dt.date | pd.Timestamp,
    observed_at: dt.datetime,
    *,
    calendar: TradingCalendar | None = None,
    close_time: dt.time = DEFAULT_A_SHARE_CLOSE_TIME,
) -> str:
    """判定一根 A股日线 bar 在 ``observed_at`` 时刻的完成度。

    判定逻辑（纯函数、无 IO）：

    - ``bar_date`` 不是交易日（按注入日历）→ ``unknown``：日历不认，
      无法证明这根 bar 对应一个已结束的交易时段；
    - ``observed_at`` 早于 ``bar_date`` 当天 → ``unknown``：数据时间与
      观测时刻矛盾，属数据异常，保守不判定；
    - ``bar_date`` 是交易日且观测时刻（上海时间）已到达/越过当天收盘
      时刻 → ``final``：日线 bar 一旦所属交易时段收盘即走完，与之后
      是否节假日无关；
    - 其余（交易日当天盘中观测）→ ``partial``。

    保守缺省：判定不出的一律 ``unknown``，生产路径按 partial 同样拒绝。
    """
    cal = calendar or WeekdayCalendar()
    day = pd.Timestamp(bar_date).normalize()
    if not cal.is_trading_day(day):
        return UNKNOWN
    now = observed_at if observed_at.tzinfo else observed_at.replace(tzinfo=_CN_TZ)
    now = now.astimezone(_CN_TZ)
    close_at = dt.datetime.combine(day.date(), close_time, tzinfo=_CN_TZ)
    if now < dt.datetime.combine(day.date(), dt.time(0, 0), tzinfo=_CN_TZ):
        return UNKNOWN
    if now >= close_at:
        return FINAL
    return PARTIAL


def annotate_bars(
    bars_by_symbol: dict[str, pd.DataFrame],
    observed_at: dt.datetime,
    *,
    calendar: TradingCalendar | None = None,
    close_time: dt.time = DEFAULT_A_SHARE_CLOSE_TIME,
) -> BarCompletenessReport:
    """为每标的的日线 DataFrame 生成最后一根 bar 的完成度旁侧标注。

    不修改传入的 DataFrame（不改结构红线）；空 frame 记 ``unknown``
    （无数据即无法判定，保守缺省）。
    """
    report: dict[str, tuple[str, pd.Timestamp]] = {}
    for symbol, frame in bars_by_symbol.items():
        if frame is None or len(frame) == 0:
            report[symbol] = (UNKNOWN, pd.NaT)
            continue
        last_date = pd.Timestamp(frame.index[-1]).normalize()
        state = classify_a_share_bar(
            last_date, observed_at, calendar=calendar, close_time=close_time,
        )
        report[symbol] = (state, last_date)
    return BarCompletenessReport(last_bar=report)


def require_final_for_production(report: BarCompletenessReport) -> None:
    """生产信号路径守卫（拒绝处置）：存在非 final 即抛 ``PartialBarError``。

    调用契约 ``production_signal_requires_final`` 的实现：编排层在把
    bar 数据送入生产信号路径（close 信号语义）之前必须调用本守卫；
    partial 与 unknown 一律拒绝（unknown 按保守缺省视同 partial），
    不得静默降级为 final。
    """
    problems = report.problems
    if problems:
        raise PartialBarError(problems)


def research_view(report: BarCompletenessReport) -> dict[str, str]:
    """研究/回测路径标注（``research_allow_partial``）：允许 partial 通过。

    返回 symbol -> 显式完成度字符串。partial/unknown 不会被过滤，但
    调用方拿到的是带显式标注的结果——下游不得把非 final 值当成收盘
    完成语义使用。
    """
    return {symbol: state for symbol, (state, _) in report.last_bar.items()}


__all__ = [
    "DEFAULT_A_SHARE_CLOSE_TIME",
    "FINAL",
    "PARTIAL",
    "UNKNOWN",
    "BarCompletenessReport",
    "PartialBarError",
    "annotate_bars",
    "classify_a_share_bar",
    "research_view",
    "require_final_for_production",
]
