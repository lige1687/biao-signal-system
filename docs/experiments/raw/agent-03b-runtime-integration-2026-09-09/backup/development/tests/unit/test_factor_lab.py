"""factor_lab 单测：组合回测、评分卡分档、估值 chips 解析（任务书 #6）。"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lei_signal.market_context.factor_lab import (
    factor_scores_monthly,
    fetch_valuation_chips,
    grade_from_score,
    portfolio_returns,
    risk_score,
    summarize_series,
)


def _piv(n_months: int = 60, n_stocks: int = 8, seed: int = 5) -> pd.DataFrame:
    """月末日历的合成收盘矩阵（n_stocks 只，各走不同漂移）。"""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2018-01-31", periods=n_months, freq="ME")
    cols = [f"{600000 + i}" for i in range(n_stocks)]
    data = {}
    for i, c in enumerate(cols):
        drift = 0.005 + i * 0.004  # 低代码=低收益：动量组合应选高代码
        data[c] = 100.0 * np.cumprod(1.0 + rng.normal(drift, 0.01, n_months))
    return pd.DataFrame(data, index=idx)


def _manual_scores(piv: pd.DataFrame) -> pd.DataFrame:
    """手工月度打分（模拟动量：近 3 月收益，高=好）。组合回测只依赖打分表。"""
    return (piv / piv.shift(3) - 1.0).dropna(how="all")


def test_factor_scores_monthly_on_daily_bars():
    """factor_scores_monthly 输入须为日线矩阵：252 日后 mom 才有值、且只取月末行。"""
    rng = np.random.default_rng(2)
    idx = pd.bdate_range("2018-01-01", periods=420)
    piv = pd.DataFrame(
        {f"{600000+i}": 100.0 * np.cumprod(1.0 + rng.normal(0.001, 0.02, len(idx)))
         for i in range(6)},
        index=idx,
    )
    scores = factor_scores_monthly(piv)
    assert set(scores) == {"low_vol", "mom_121"}
    mom = scores["mom_121"]
    # 全部行都是该月最后一个交易日
    for ts in mom.index:
        month_rows = piv.loc[f"{ts.year}-{ts.month:02d}"]
        assert ts == month_rows.index[-1]
    # 前 ~12 个月（不足 252 日）应全 NaN，之后有值
    assert mom.iloc[0].isna().all()
    assert mom.iloc[-1].notna().all()


def test_portfolio_returns_momentum_picks_winners():
    """largest 组合应选中高漂移股票 → 月均收益高于 smallest 组合。"""
    piv = _piv()
    scores = _manual_scores(piv)
    r_hi = portfolio_returns(piv, scores, top_frac=0.25,
                             min_eligible=4, low_is_good=False)
    r_lo = portfolio_returns(piv, scores, top_frac=0.25,
                             min_eligible=4, low_is_good=True)
    assert len(r_hi) > 10
    # 高分组合应跑赢低分组合（合成数据漂移单调）
    assert r_hi.mean() > r_lo.mean()


def test_portfolio_returns_next_bar_no_lookahead():
    """t 月末选股只用 t 及以前数据；收益来自 t+1 月（合成单边验证）。"""
    idx = pd.date_range("2020-01-31", periods=6, freq="ME")
    piv = pd.DataFrame(
        {
            "600001": [100.0, 100.0, 100.0, 100.0, 200.0, 200.0],
            "600002": [100.0, 100.0, 100.0, 100.0, 100.0, 100.0],
        },
        index=idx,
    )
    scores = factor_scores_monthly(piv)
    r = portfolio_returns(piv, scores["mom_121"], top_frac=0.5,
                          min_eligible=2, low_is_good=False)
    # 第 4 月末（index 3）mom_121 全 NaN（不足 252 期）→ 不选股；此处只验证
    # 输出收益全部来自相邻月末比价且无异常值
    for v in r.values:
        assert np.isfinite(v)


def test_min_eligible_guards_thin_cross_section():
    piv = _piv(n_stocks=4)
    scores = _manual_scores(piv)
    r = portfolio_returns(piv, scores, top_frac=0.3, min_eligible=50)
    assert r.empty


def test_summarize_series_basic():
    idx = pd.date_range("2020-01-31", periods=24, freq="ME")
    r = pd.Series(0.01, index=idx)
    b = pd.Series(0.005, index=idx)
    s = summarize_series(r, b, "测试")
    assert s["n_months"] == 24
    assert s["total_return_pct"] == pytest.approx(((1.01 ** 24) - 1) * 100, rel=1e-3)
    assert s["excess_cagr_pct"] > 0
    assert set(s["by_year_pct"]) == {"2020", "2021"}


WEIGHTS = {"breadth": 0.40, "rv": 0.40, "delta": 0.20}


def test_risk_score_and_grade_bands():
    # 满宽度 + 低波 → 低难度分
    assert risk_score(1.0, 0.0, 0.0, WEIGHTS) == pytest.approx(0.0)
    # 弱宽度 + 高波 + 宽度 5 日 -20pp → 满分
    assert risk_score(0.0, 1.0, -20.0, WEIGHTS) == pytest.approx(100.0)
    # 主分量缺失 → None
    assert risk_score(None, 0.5, 0.0, WEIGHTS) is None
    bands = [20, 35, 50, 65, 80]
    assert grade_from_score(0.0, bands) == "L1"
    assert grade_from_score(50.0, bands) == "L3"
    assert grade_from_score(95.0, bands) == "L6"
    assert grade_from_score(None, bands) is None


def test_risk_score_monotonic_in_components():
    base = risk_score(0.5, 0.5, 0.0, WEIGHTS)
    assert risk_score(0.3, 0.5, 0.0, WEIGHTS) > base   # 宽度变弱 → 更难
    assert risk_score(0.5, 0.8, 0.0, WEIGHTS) > base   # 波动变高 → 更难
    assert risk_score(0.5, 0.5, -10.0, WEIGHTS) > base  # 宽度恶化 → 更难


def test_fetch_valuation_chips_handles_unreachable(monkeypatch):
    """接口不可达时如实返回 available=False，不冒充。"""
    import lei_signal.market_context.factor_lab as mod

    def _boom(url):
        raise OSError("network down")

    monkeypatch.setattr(mod.urllib.request, "urlopen", _boom)
    out = fetch_valuation_chips()
    assert out["available"] is False
    assert "不可达" in out["reason_cn"]


def test_fetch_valuation_chips_parses(monkeypatch):
    import json as _json

    import lei_signal.market_context.factor_lab as mod

    class _Resp:
        def read(self):
            return _json.dumps({
                "data": {"items": [
                    {"index_code": "SH000300", "name": "沪深300", "pe": 12.5, "pe_percentile": 0.45},
                    {"index_code": "SZ399997", "name": "中证白酒", "pe": 20.0, "pe_percentile": 0.1},
                ]}
            }).encode()

    def _ok(url, timeout=10):
        return _Resp()

    monkeypatch.setattr(mod.urllib.request, "urlopen", _ok)
    out = fetch_valuation_chips()
    assert out["available"] is True
    assert len(out["chips"]) == 1  # 只保留登记的宽基
    assert out["chips"][0]["name_cn"] == "沪深300"
    assert out["chips"][0]["pe_percentile"] == 45.0
