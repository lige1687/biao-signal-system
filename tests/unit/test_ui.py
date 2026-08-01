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
    for required in ("复权K线", "MA20", "EMA20", "EMA60", "EMA120", "颜色状态", "成交量"):
        assert required in names, f"图表缺少 {required}"


def test_color_hex_mapping_is_stable() -> None:
    assert COLOR_HEX["green"] == "#16a34a"
    assert COLOR_HEX["gray"] == "#9ca3af"
    assert COLOR_HEX["black"] == "#111827"
    assert COLOR_HEX["unknown"] == "#e5e7eb"


def test_price_figure_marks_structures_and_b1() -> None:
    result = analyze_bars("SYN", _bars())
    figure = build_price_figure(
        result.frame, structures=result.structures, b1_price=123.45
    )
    annotations = " ".join(
        str(annotation.text) for annotation in figure.layout.annotations
    )
    assert "B1第一阻力" in annotations
    if any(s.side == "bottom" and s.c_price for s in result.structures):
        assert "底部C" in annotations


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
