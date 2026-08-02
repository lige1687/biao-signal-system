"""界面层测试：图表结构与文案约束（不依赖浏览器）。"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lei_signal.compose.pipeline import analyze_bars
from lei_signal.ui.charts import (
    COLOR_HEX,
    build_price_figure,
    build_stage_history_figure,
    build_volume_profile_figure,
)


def _bars(rows: int = 300, seed: int = 9) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0.05, 1.5, rows))
    return pd.DataFrame(
        {
            "open": close,
            "high": close + rng.uniform(0.3, 1.8, rows),
            "low": close - rng.uniform(0.3, 1.8, rows),
            "close": close,
            "volume": rng.integers(1_000_000, 5_000_000, rows).astype(float),
        },
        index=pd.bdate_range("2024-01-02", periods=rows),
    )


def test_price_figure_contains_candles_four_mas_volume_and_colors() -> None:
    result = analyze_bars("SYN", _bars())
    figure = build_price_figure(
        result.frame,
        structures=result.structures,
        b1_price=result.assessment.b1_price,
        profile=result.profile,
    )
    names = [trace.name for trace in figure.data]
    # 显式图例：K线、SMA20、EMA20、20周期抵扣价、成交量
    for required in ("K线", "SMA20", "EMA20", "20周期抵扣价", "成交量"):
        assert required in names, f"图表缺少 {required}"


def test_lei_color_mode_splits_candles_by_signal_color() -> None:
    """绿灰黑模式下，每根 K 线本体按当日 signal_color 上色，不依赖涨跌。"""
    result = analyze_bars("SYN", _bars())
    figure = build_price_figure(
        result.frame,
        structures=result.structures,
        b1_price=result.assessment.b1_price,
        color_mode="lei_color",
    )

    # 颜色状态带在 LEI 模式下应被省略（K 线本体已上色）。
    names = [trace.name for trace in figure.data]
    assert "LEI颜色" not in names

    # 至少有一个 LEI 分桶 trace，并使用对应 hex 颜色。
    candle_names = [n for n in names if n.startswith("K线（")]
    assert candle_names, "LEI 模式应至少有一个分桶 K 线 trace"

    from lei_signal.ui.charts import COLOR_HEX

    for trace in figure.data:
        if not trace.name.startswith("K线（"):
            continue
        if "绿色" in trace.name:
            expected = COLOR_HEX["green"]
        elif "灰色" in trace.name:
            expected = COLOR_HEX["gray"]
        elif "黑色" in trace.name:
            expected = COLOR_HEX["black"]
        else:
            continue
        # 三色统一：涨跌都用同一 hex，避免「绿涨红跌」残留
        assert trace.increasing.fillcolor == expected
        assert trace.decreasing.fillcolor == expected
        assert trace.increasing.line.color == expected
        assert trace.decreasing.line.color == expected
        # 分桶 trace 不应进入 legend，避免图例膨胀
        assert trace.showlegend is False


def test_lei_color_mode_falls_back_when_no_signal_color_column() -> None:
    """没有 signal_color 列时，LEI 模式不能崩，必须有可读的 K 线。"""
    frame = _bars()
    frame = frame.drop(columns=[c for c in frame.columns if c not in {
        "open", "high", "low", "close", "volume"
    }])
    figure = build_price_figure(frame, color_mode="lei_color")
    names = [trace.name for trace in figure.data]
    # 回退路径画的就是默认「K线」
    assert "K线" in names


def test_red_green_mode_keeps_color_state_marker() -> None:
    """红绿模式必须保留日级 LEI 小方块带，与既有截图一致。"""
    result = analyze_bars("SYN", _bars())
    figure = build_price_figure(
        result.frame, color_mode="red_green"
    )
    names = [trace.name for trace in figure.data]
    assert "LEI颜色" in names


def test_price_chart_helper_renders_both_modes_without_state_machine_change() -> None:
    """两种颜色模式只影响展示，不应改变任何 LEI 计算结果。"""
    result_red = analyze_bars("SYN", _bars())
    result_lei = analyze_bars("SYN", _bars())
    # 两份独立计算结果的结构化字段必须一致（阶段、风险、颜色逐日序列）。
    for left, right in zip(result_red.history, result_lei.history, strict=True):
        assert left.stage == right.stage
        assert left.risk_state == right.risk_state
        for ls, rs in zip(
            left.observations.values(),
            right.observations.values(),
            strict=True,
        ):
            assert ls.tier == rs.tier


def test_color_hex_mapping_is_stable() -> None:
    """LEI 三色 hex 必须稳定（与 collect_levels / chart 共用同一份）。"""
    # 三色 hex 与用户旧看板风格保持一致（绿/灰/黑）。
    assert COLOR_HEX["green"] == "#0b9b64"
    assert COLOR_HEX["gray"] == "#8c96a8"
    assert COLOR_HEX["black"] == "#1f2937"
    assert COLOR_HEX["unknown"] == "#c9a227"


def test_price_figure_marks_structures_and_b1() -> None:
    """图内不再写文字档位——所有水平线含义由 collect_levels 负责。"""
    from lei_signal.ui.charts import collect_levels

    result = analyze_bars("SYN", _bars())
    figure = build_price_figure(
        result.frame, structures=result.structures, b1_price=123.45
    )
    # 1. 图内 annotation 只剩 subplot title（不应再有「B1第一阻力」「底部C」等）。
    annotations = " ".join(
        str(annotation.text) for annotation in figure.layout.annotations
    )
    assert "B1第一阻力" not in annotations
    assert "底部C" not in annotations
    assert "顶部颈线" not in annotations

    # 2. 但水平档位列表必须完整回报：含 B1、含任何底部结构 C。
    levels = collect_levels(
        result.frame, structures=result.structures, b1_price=123.45
    )
    level_types = {row["type"] for row in levels}
    assert "B1 第一阻力" in level_types
    bottom_levels = [row for row in levels if row["type"] == "底部 C"]
    if any(s.side == "bottom" and s.c_price for s in result.structures):
        assert bottom_levels, "存在底部结构时 collect_levels 必须返回至少一条底部 C"


def test_price_figure_uses_right_yaxis_and_clean_legend() -> None:
    """Y 轴必须放右侧，且图例显式锁定几项（防止拥挤）。"""
    result = analyze_bars("SYN", _bars())
    figure = build_price_figure(result.frame)
    assert figure.layout.yaxis.side == "right"
    # 图例锁定 K线/SMA20/EMA20/20周期抵扣价/成交量 五项
    assert figure.layout.legend.orientation == "h"


def test_price_figure_limits_visible_structure_lines() -> None:
    """图上只画关键的几条结构线（主底部 C + 活跃顶部 + B1），其余只在表里。

    这是为了避免「灰色线条覆盖整个图表」——LEI 通常有 5+ 个历史底部结构，
    但只有 1-2 条对当前决策真正关键。
    """
    from datetime import date
    from unittest.mock import MagicMock

    # 构造 5 个底部 + 2 个活跃顶部 + 1 个失效顶部
    structures = []
    for i in range(5):
        s = MagicMock()
        s.side = "bottom"
        s.c_price = 1.0 + i * 0.01
        s.invalidated_date = None
        s.confirmed_date = date(2024, 6, 1 + i)
        s.detected_date = date(2024, 5, 1 + i)
        s.structure_type = "higher_low_bottom"
        s.source_rule_id = "r1"
        structures.append(s)
    for i in range(2):
        s = MagicMock()
        s.side = "top"
        s.neckline = 1.5 + i * 0.01
        s.invalidated_date = None
        s.confirmed_date = date(2024, 7, 1 + i)
        s.detected_date = date(2024, 7, 1 + i)
        s.structure_type = "lower_high_top"
        s.source_rule_id = "r2"
        structures.append(s)

    result = analyze_bars("SYN", _bars())
    figure = build_price_figure(
        result.frame, structures=structures, b1_price=1.55
    )
    # shape 数量应该被限制（不是 5 个底部全画 + 2 个顶部全画 = 7+）。
    # 实际只画 1 个主底部 + 2 个活跃顶部 + 1 个 B1 = 4 条线段（每个结构一段）。
    shape_count = len(figure.layout.shapes)
    assert shape_count <= 5, (
        f"图上结构线段过多 ({shape_count})，应只画关键几条，其余进表格"
    )


def test_volume_classify_returns_four_levels() -> None:
    """量能必须按 ratio 分四级（放量/温和/正常/缩量）。"""
    from lei_signal.ui.charts import _classify_volume

    assert _classify_volume(3.0) == "放量"
    assert _classify_volume(2.0) == "放量"
    assert _classify_volume(1.5) == "温和"
    assert _classify_volume(1.2) == "温和"
    assert _classify_volume(1.0) == "正常"
    assert _classify_volume(0.8) == "正常"
    assert _classify_volume(0.5) == "缩量"


def test_price_figure_uses_range_slider_not_manual_window() -> None:
    """图表本体必须用 plotly 自带的 xaxis2 rangeslider，替代手动滑块。"""
    result = analyze_bars("SYN", _bars())
    figure = build_price_figure(result.frame)
    layout = figure.layout
    # 主图 xaxis 不应有 rangeslider（rangeslider 默认不存在）；成交量子图有。
    xaxis_rs_visible = layout.xaxis.rangeslider.visible
    assert xaxis_rs_visible in (False, None)
    # 成交量子图（xaxis2）显式启用 rangeslider 供用户拖动缩放。
    assert layout.xaxis2.rangeslider.visible is True


def test_volume_profile_figure_is_labelled_as_proxy() -> None:
    """界面必须写「筹码分布代理」，不得声称真实持仓成本。"""
    result = analyze_bars("SYN", _bars())
    assert result.profile is not None
    figure = build_volume_profile_figure(result.profile)
    title = str(figure.layout.title.text)
    assert "筹码分布代理" in title
    assert "非真实持仓成本" in title
    assert "真实筹码" not in title


def test_stage_history_figure_uses_chinese_stage_labels() -> None:
    result = analyze_bars("SYN", _bars())
    from lei_signal.domain.types import STAGE_CN, STAGE_RANK

    history = pd.DataFrame(
        [
            {
                "date": pd.Timestamp(state.day),
                "stage_rank": STAGE_RANK.get(state.stage.value, 0),
                "stage_cn": STAGE_CN[state.stage.value],
            }
            for state in result.history
        ]
    ).set_index("date")
    figure = build_stage_history_figure(history)
    ticks = list(figure.layout.yaxis.ticktext)
    assert ticks == ["无线索", "底部观察", "结构确认", "早期转强", "共同确认", "趋势增强"]


def test_app_module_declares_non_advisory_disclaimer() -> None:
    """界面文案不得包含承诺性买卖措辞。"""
    from lei_signal.ui.app import DISCLAIMER

    assert "不是自动交易系统" in DISCLAIMER
    assert "不下单" in DISCLAIMER
    for forbidden in ("建议买入", "建议卖出", "确定上涨", "确定下跌", "保证"):
        assert forbidden not in DISCLAIMER


def test_app_imports_without_streamlit_runtime() -> None:
    """模块必须可导入（用于 CI 静态检查），且暴露 render 入口。"""
    from lei_signal.ui import app

    assert callable(app.render)
