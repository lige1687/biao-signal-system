"""MACD 强度解读门禁（研究代理）。

用户口径（不可改写）：MACD 研究均线的扩散和密集状态，本质是乖离率，
表示**强度**而不是转折趋势节点。趋势转折 5 步骤中，MACD 只能表达
「交叉」与「多头排列+乖离率」；「破线」与「均线拐头」必须由系统既有的
LEI 颜色与均线斜率补齐。金叉/死叉只是强度描述，不构成买点。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lei_signal.api.explanations import lookup
from lei_signal.compose.pipeline import analyze_bars
from lei_signal.rules.macd_strength import BLIND_SPOT_CN, read_macd_strength


def _row(dif: float, dea: float) -> pd.Series:
    return pd.Series({"macd_dif": dif, "macd_dea": dea, "macd_hist": (dif - dea) * 2.0})


def _read(dif: float, dea: float, prev_dif: float, prev_dea: float):
    reading = read_macd_strength(_row(dif, dea), _row(prev_dif, prev_dea))
    assert reading is not None
    return reading


def test_golden_cross_is_support_but_never_a_buy_point() -> None:
    """DIF 上穿 DEA = 金叉：强度转向增强，维度支持，但不得表述为买点。"""
    reading = _read(dif=1.0, dea=0.5, prev_dif=-0.2, prev_dea=0.1)
    assert reading.cross == "金叉"
    assert reading.status == "金叉"
    assert reading.dimension_value == "支持"
    banned = ("买入", "卖出", "建议买", "该买", "加仓", "减仓", "抄底")
    text = f"{reading.label_cn}{reading.detail_cn}"
    assert not any(word in text for word in banned)


def test_dead_cross_is_conflict() -> None:
    reading = _read(dif=-0.4, dea=0.2, prev_dif=0.5, prev_dea=0.3)
    assert reading.cross == "死叉"
    assert reading.status == "死叉"
    assert reading.dimension_value == "冲突"


def test_bullish_expansion_is_support() -> None:
    """DIF 在 0 轴上方 + 柱体放大 = 乖离扩散 = 多头强度增强。"""
    reading = _read(dif=1.5, dea=0.6, prev_dif=1.0, prev_dea=0.7)
    assert reading.cross == "无"
    assert reading.status == "多头扩散"
    assert reading.dimension_value == "支持"


def test_bullish_contraction_is_neutral() -> None:
    """柱体收缩 = 均线趋密集 = 强度衰减，只作中性，不作转折。"""
    reading = _read(dif=1.0, dea=0.9, prev_dif=1.5, prev_dea=0.6)
    assert reading.status == "多头收敛"
    assert reading.dimension_value == "中性"


def test_bearish_expansion_is_conflict() -> None:
    reading = _read(dif=-1.5, dea=-0.6, prev_dif=-1.0, prev_dea=-0.7)
    assert reading.status == "空头扩散"
    assert reading.dimension_value == "冲突"


def test_bearish_contraction_is_neutral() -> None:
    reading = _read(dif=-1.0, dea=-0.9, prev_dif=-1.5, prev_dea=-0.6)
    assert reading.status == "空头收敛"
    assert reading.dimension_value == "中性"


def test_every_reading_carries_blind_spot_completion() -> None:
    """红线：MACD 不能交代破线与均线拐头，每条读数都必须带补齐来源。"""
    reading = _read(dif=1.5, dea=0.6, prev_dif=1.0, prev_dea=0.7)
    assert reading.blind_spot_cn == BLIND_SPOT_CN
    assert "破线" in BLIND_SPOT_CN
    assert "拐头" in BLIND_SPOT_CN
    assert "LEI 颜色" in BLIND_SPOT_CN
    assert "斜率" in BLIND_SPOT_CN


def test_label_marks_research_proxy() -> None:
    reading = _read(dif=1.5, dea=0.6, prev_dif=1.0, prev_dea=0.7)
    assert "研究代理" in reading.label_cn


def test_warmup_and_missing_columns_return_none() -> None:
    """预热期（DIF/DEA 为 NaN）与缺列都必须返回 None，不得瞎猜。"""
    nan_row = pd.Series({"macd_dif": np.nan, "macd_dea": np.nan, "macd_hist": np.nan})
    assert read_macd_strength(nan_row, nan_row) is None
    assert read_macd_strength(pd.Series({"close": 10.0}), None) is None
    # 首个有效日无前一行：可读（无法判交叉，按乖离方向给强度）
    first = read_macd_strength(_row(1.5, 0.6), None)
    assert first is not None
    assert first.cross == "无"
    assert first.prev_hist is None


# ---------------- 接入 build_assessment 的集成门禁 ----------------


def _bars(n: int = 180, seed: int = 11) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100.0 + np.cumsum(rng.normal(loc=0.2, scale=1.1, size=n))
    index = pd.bdate_range("2023-01-02", periods=n)
    return pd.DataFrame(
        {
            "open": np.r_[close[0], close[:-1]],
            "high": close + 0.7,
            "low": close - 0.7,
            "close": close,
            "volume": 1_000_000.0,
        },
        index=index,
    )


def test_assessment_exposes_macd_strength_dimension() -> None:
    result = analyze_bars("TEST", _bars())
    assessment = result.assessment
    assert "强度(MACD)" in assessment.dimensions
    assert assessment.dimensions["强度(MACD)"] in {"支持", "冲突", "中性"}


def test_assessment_factor_routing_matches_dimension() -> None:
    """支持进 supports、冲突进 conflicts、中性只进维度不进列表。"""
    result = analyze_bars("TEST", _bars())
    assessment = result.assessment
    value = assessment.dimensions["强度(MACD)"]
    supports = [f for f in assessment.supports if f.rule_id == "macd_strength"]
    conflicts = [f for f in assessment.conflicts if f.rule_id == "macd_strength"]
    if value == "支持":
        assert len(supports) == 1 and not conflicts
        factor = supports[0]
    elif value == "冲突":
        assert len(conflicts) == 1 and not supports
        factor = conflicts[0]
    else:
        assert not supports and not conflicts
        return
    assert factor.dimension == "强度(MACD)"
    assert "研究代理" in factor.label_cn
    assert factor.provenance.value == "research_proxy"
    # 盲区补齐必须跟着 Factor 一路走到 UI / agent
    assert BLIND_SPOT_CN in factor.detail_cn


def test_macd_produces_no_signal_events() -> None:
    """红线：金叉/死叉不得生成任何交易事件。"""
    result = analyze_bars("TEST", _bars(), build_history=True)
    assert all(event.rule_id != "macd_strength" for event in result.events)


def test_chart_payload_carries_macd_series() -> None:
    from lei_signal.ui.echarts_kline import serialize_result

    payload = serialize_result(analyze_bars("TEST", _bars()), color_mode="red_green")
    for key in ("macdDif", "macdDea", "macdHist"):
        assert key in payload
        assert len(payload[key]) == len(payload["dates"])
    # 末值应已成形（180 根远超预热期 33）
    assert payload["macdDif"][-1] is not None
    assert payload["macdHist"][-1] is not None


def test_explanation_entry_states_strength_not_reversal() -> None:
    entry = lookup(rule_id="macd_strength")
    assert entry is not None
    blob = " ".join(str(v) for v in entry.values())
    assert "乖离率" in blob
    assert "强度" in blob
    assert "研究代理" in blob
    assert "不构成买点" in blob
