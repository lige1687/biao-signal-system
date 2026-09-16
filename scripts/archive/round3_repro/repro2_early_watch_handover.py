"""Round 3 最小复现 2：early_watch 在结构确认后正确交接。

复现什么
--------
D2 的原始缺陷是确认档 latch 额外要求「升级当天重新出现一次 EMA20 交叉」。
但 EMA20 收复是一次**进入事件**，进入之后不会每天重复发生，于是：

  * 结构确认那天没有新交叉 → 确认档点不亮
  * ``early_watch`` 一直挂着不熄 → 界面继续说「尚未确认」
  * 已确认结构被当成观察档展示

修复后的要求（任务书第四节）：确认当日必须同时满足
  ``early_watch_by_structure[sid] == False`` 且
  ``early_strength_by_structure[sid] == True``
且升级当天**不需要**新的 EMA20 交叉。

行情设计：同一 lifecycle 内 01-02 开启观察档，01-05 结构确认（当天无新交叉），
01-11 SMA20 转上行→共同确认，01-12 长周期改善→长周期改善档。

运行：/opt/homebrew/bin/python3.11 scripts/round3_repro/repro2_early_watch_handover.py
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from lei_signal.domain.types import (
    Provenance,
    StructureInstance,
    StructureStatus,
)
from lei_signal.rules.dual_ma import ema20_reclaim_state
from lei_signal.rules.ema_reclaim_tiers import detect_structure_bound_ema_reclaim
from lei_signal.state.machine import run_state_machine

_INDEX = pd.bdate_range("2024-01-01", periods=10)


def _frame() -> pd.DataFrame:
    close = [100, 103, 104, 105, 106, 107, 108, 109, 110, 111]
    return pd.DataFrame(
        {
            "open": close,
            "high": [v + 1.0 for v in close],
            "low": [v - 1.0 for v in close],
            "close": close,
            "volume": [1_000_000.0] * 10,
            "ema20": [101, 101.5, 102, 102.5, 103, 103.5, 104, 104.5, 105, 105.5],
            "sma20": [110, 109, 108, 107, 106, 105, 104, 103.5, 104, 104.5],
            "signal_color": ["green"] * 10,
            "long_trend": ["unknown"] * 9 + ["long_improving"],
            "long_is_improving": [False] * 9 + [True],
            "long_is_supportive": [False] * 10,
        },
        index=_INDEX,
    )


def main() -> int:
    frame = _frame()
    structure = StructureInstance(
        structure_id="S-HANDOVER",
        symbol="600000",
        structure_type="bottom_C",
        side="bottom",
        detected_date=date(2024, 1, 1),
        confirmed_date=date(2024, 1, 5),   # <<< 01-05 结构确认
        invalidated_date=None,
        c_price=95.0,
        neckline=105.0,
        status=StructureStatus.CONFIRMED,
        provenance=Provenance.LEI_EXPLICIT,
    )

    events = detect_structure_bound_ema_reclaim(frame, "600000", [structure])
    history = run_state_machine(frame, [structure], ema_reclaim_events=events)

    reclaim = ema20_reclaim_state(frame)
    print("== 前提条件 ==")
    print(f"结构确认日 = {structure.confirmed_date}")
    print("EMA20 收复交叉发生在哪些日子（True = 当天新交叉）：")
    for ts, flag in reclaim.items():
        if bool(flag):
            print(f"  {ts.date()}  <<< 唯一一次进入交叉")
    print("→ 01-05 / 01-11 / 01-12 当天都没有新交叉，若实现仍要求「重新交叉」，"
          "这三档全部点不亮。")
    print()

    print("== 事件层档位链（共享 lifecycle_id）==")
    for event in events:
        print(
            f"  {event.available_date}  tier={event.evidence['tier']:<22}"
            f" strength={event.strength:<3} lifecycle={event.lifecycle_id}"
        )
    print()

    print("== 逐日状态机投影（修复后）==")
    header = (
        f"{'date':<12}{'stage':<20}{'early_watch':<13}{'early_strength':<16}"
        f"{'tier':<22}{'new_cross':<11}lifecycle"
    )
    print(header)
    for state in history:
        sid = "S-HANDOVER"
        obs = state.observations.get(sid)
        new_cross = bool(reclaim.loc[pd.Timestamp(state.day)])
        print(
            f"{str(state.day):<12}"
            f"{state.opportunity_stage.value:<20}"
            f"{str(state.early_watch_by_structure.get(sid, False)):<13}"
            f"{str(state.early_strength_by_structure.get(sid, False)):<16}"
            f"{str(obs.tier if obs else None):<22}"
            f"{str(new_cross):<11}"
            f"{obs.lifecycle_id if obs else '-'}"
        )

    by_day = {s.day: s for s in history}
    failures: list[str] = []

    # 任务书第四节的确认日断言
    confirm_day = by_day[date(2024, 1, 5)]
    if confirm_day.early_watch_by_structure.get("S-HANDOVER", False) is not False:
        failures.append("01-05 early_watch 未熄灭")
    if confirm_day.early_strength_by_structure.get("S-HANDOVER", False) is not True:
        failures.append("01-05 early_strength 未点亮")

    # 升级当天不得依赖新交叉
    for day in (date(2024, 1, 5), date(2024, 1, 11), date(2024, 1, 12)):
        if bool(reclaim.loc[pd.Timestamp(day)]):
            failures.append(f"{day} 竟然有新交叉，本复现前提失效")
        obs = by_day[day].observations.get("S-HANDOVER")
        if obs is None or obs.tier is None:
            failures.append(f"{day} 无档位（升级仍依赖新交叉）")

    # 四档共享一个 lifecycle_id
    lifecycles = {e.lifecycle_id for e in events}
    if len(lifecycles) != 1:
        failures.append(f"档位链 lifecycle_id 不唯一：{lifecycles}")

    print()
    if failures:
        for line in failures:
            print(f"FAIL: {line}")
        return 1
    print("PASS: 01-05 观察档熄灭 + 确认档点亮；01-05/01-11/01-12 三次升级")
    print("      当天均无新 EMA20 交叉；四档共享同一 lifecycle_id "
          f"{next(iter(lifecycles))}。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
