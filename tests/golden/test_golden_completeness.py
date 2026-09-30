"""J1 golden 样本的 bar 完成度标注（W2-S1，2026-09-20）。

为既有引擎黄金样本补 ``completeness=final`` 标注：所有样本按
「最后一个交易日收盘后」观测口径必须是 final——这是 J1 基准成立的
隐含前提（引擎回放的是走完的 bar）。本文件不改既有断言与冻结哈希，
只新增完成度维度（tests/golden/test_golden_entry_engines.py 保持原样）。
"""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import pytest

from lei_signal.data.bar_completeness import FINAL, annotate_bars, require_final_for_production
from tests.golden.fixtures import (
    golden_bottom_c_invalidation,
    golden_bullish_engulfing,
    golden_bullish_outside_reversal,
    golden_color_series,
    golden_delayed_upgrade,
    golden_top_then_black,
)

CN = ZoneInfo("Asia/Shanghai")

#: 观测口径：每个样本最后一根 bar 的下一个工作日早盘（必然已收盘）。
_OBSERVED = dt.datetime(2026, 1, 5, 9, 30, tzinfo=CN)


@pytest.mark.parametrize(
    "sample",
    [
        golden_color_series,
        golden_bullish_engulfing,
        golden_bullish_outside_reversal,
        golden_bottom_c_invalidation,
        golden_delayed_upgrade,
        golden_top_then_black,
    ],
    ids=lambda fn: fn.__name__,
)
def test_golden_samples_are_final(sample) -> None:
    """golden 样本最后一根 bar 按收盘后观测口径全部为 final，生产守卫放行。"""
    frame = sample()
    # 观测时刻必须晚于每个样本最后一根 bar 的收盘：统一取样本末日的
    # 次周一早盘（样本索引最晚不超过 2025 年，2026-01-05 周一必在其后）。
    report = annotate_bars({"golden": frame}, _OBSERVED)
    assert report.last_bar["golden"][0] == FINAL
    require_final_for_production(report)
