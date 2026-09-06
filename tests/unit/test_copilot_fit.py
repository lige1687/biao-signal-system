"""形态×打法适配器测试（分类规则 + 大白话输出 + 经验联动）。"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lei_signal.copilot.fit import classify_regime, fit_advice, measure_regime


def _frame(closes: list[float]) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=len(closes), freq="B")
    return pd.DataFrame({"close": closes}, index=idx)


def _steady(n=260, base=1.0, vol=0.004):
    """稳涨：每日 +0.35% 漂移，浅回调噪音。"""
    rng = np.random.default_rng(7)
    return [base * (1 + 0.0035 * i + rng.normal(0, vol)) for i in range(n)]


def test_steady_uptrend_classified():
    m = measure_regime(_frame(_steady()), window=250)
    assert m["available"] is True
    assert classify_regime(m) == "steady_uptrend"
    out = fit_advice(_frame(_steady()))
    assert out["regime_cn"] == "稳涨型"
    assert "A模块" in out["fit_cn"] or "趋势回调" in out["fit_cn"]
    assert out["experience"]  # 联动到经验索引


def test_fast_uptrend_classified():
    """急涨：大涨但均线环境撑不住稳涨标准（env < 0.55）。"""
    rng = np.random.default_rng(3)
    closes = []
    price = 1.0
    for i in range(260):
        if i < 130:
            price *= 1 + rng.normal(0, 0.006)          # 前半横盘打底
        else:
            # 后一年：7 天急涨 + 5 天长回调交替——涨幅巨大但 20 日线被
            # 反复打下行（env 压低），科创实测同构
            price *= 1.024 if i % 12 < 7 else 0.975
        closes.append(price)
    m = measure_regime(_frame(closes), window=250)
    regime = classify_regime(m)
    assert regime == "fast_uptrend"
    out = fit_advice(_frame(closes))
    assert "急涨" in out["fit_cn"]
    assert "别硬套" in out["fit_cn"] or "不硬套" in out["fit_cn"]


def test_downtrend_classified():
    closes = [2.0 * (0.9965 ** i) + np.random.default_rng(1).normal(0, 0.004)
              for i in range(260)]
    out = fit_advice(_frame(closes))
    assert out["regime_cn"] == "下跌型"
    assert "不抢反弹" in out["fit_cn"]
    assert out["experience"]  # C 模块负面经验联动


def test_insufficient_data_available_false():
    out = fit_advice(_frame(_steady(80)))
    assert out["available"] is False
    assert "regime" not in out


def test_note_carries_narrative_disclaimer():
    out = fit_advice(_frame(_steady()))
    assert "不参与技术判定" in out["note_cn"]
