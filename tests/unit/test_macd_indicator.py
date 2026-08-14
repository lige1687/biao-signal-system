"""MACD 数值层门禁（研究代理 12/26/9）。

口径：MACD 表达均线扩散/密集 = 乖离率 = **强度**，不是转折节点。
本文件只管数值正确性、预热期、因果性（增量安全），解读见 test_macd_strength.py。
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lei_signal.domain.rules_config import get_rule, indicator_config, load_ruleset
from lei_signal.domain.types import Provenance
from lei_signal.features.indicators import compute_features, macd, seeded_ema


def _close(n: int = 200, seed: int = 7) -> pd.Series:
    """带噪声的上行序列：避免恒定斜率导致 DIF 退化为常数。"""
    rng = np.random.default_rng(seed)
    steps = rng.normal(loc=0.15, scale=1.2, size=n)
    values = 100.0 + np.cumsum(steps)
    index = pd.bdate_range("2023-01-02", periods=n)
    return pd.Series(values, index=index, name="close")


def _bars(n: int = 200, seed: int = 7) -> pd.DataFrame:
    close = _close(n, seed)
    return pd.DataFrame(
        {
            "open": close.shift(1).fillna(close.iloc[0]),
            "high": close + 0.6,
            "low": close - 0.6,
            "close": close,
            "volume": 1_000_000.0,
        },
        index=close.index,
    )


def test_dif_equals_manual_ema_difference() -> None:
    """DIF 必须逐点等于 EMA(fast) - EMA(slow)，不允许近似。"""
    close = _close()
    dif, _dea, _hist = macd(close, 12, 26, 9)
    manual = seeded_ema(close, 12) - seeded_ema(close, 26)
    pd.testing.assert_series_equal(
        dif, manual.rename("macd_dif"), check_names=True, rtol=0, atol=0
    )


def test_hist_is_twice_dif_minus_dea() -> None:
    """hist = 2*(DIF-DEA)（国内惯例的 2 倍口径）。"""
    dif, dea, hist = macd(_close(), 12, 26, 9)
    expected = (dif - dea) * 2.0
    np.testing.assert_allclose(
        hist.to_numpy(), expected.to_numpy(), rtol=1e-12, equal_nan=True
    )


def test_warmup_nan_counts() -> None:
    """预热期：DIF 前 slow-1 根为 NaN，DEA 再多 signal-1 根。

    DEA 是在带前导 NaN 的 DIF 上做 EMA，seeded_ema 必须跳过前导 NaN，
    否则种子取到 NaN 会污染整条序列（全 NaN）。
    """
    dif, dea, hist = macd(_close(), 12, 26, 9)
    assert int(dif.isna().sum()) == 25  # slow - 1
    assert int(dea.isna().sum()) == 25 + 8  # + signal - 1
    assert int(hist.isna().sum()) == 33
    # 预热之后不允许再出现 NaN（种子未被污染）
    assert dea.iloc[33:].notna().all()


def test_seeded_ema_unchanged_for_series_without_leading_nan() -> None:
    """为 DIF 加的跳前导 NaN 逻辑，不得改变收盘价这类无前导 NaN 序列的行为。"""
    close = _close()
    ema = seeded_ema(close, 12)
    assert int(ema.isna().sum()) == 11
    assert ema.iloc[11] == pytest.approx(float(close.iloc[:12].mean()))


def test_seeded_ema_skips_leading_nan_and_seeds_from_first_valid() -> None:
    index = pd.bdate_range("2023-01-02", periods=20)
    values = [np.nan] * 5 + [float(i) for i in range(15)]
    series = pd.Series(values, index=index)
    ema = seeded_ema(series, 3)
    # 前 5 个 NaN + 种子前的 2 根
    assert int(ema.isna().sum()) == 7
    assert ema.iloc[7] == pytest.approx((0.0 + 1.0 + 2.0) / 3.0)


def test_causality_appending_future_bars_does_not_rewrite_history() -> None:
    """增量安全：追加未来 K 线不得改动已算出的历史值（只用当前及之前的 bar）。"""
    close = _close(120)
    prefix = close.iloc[:100]
    dif_prefix, dea_prefix, hist_prefix = macd(prefix, 12, 26, 9)
    dif_full, dea_full, hist_full = macd(close, 12, 26, 9)
    for short, full in ((dif_prefix, dif_full), (dea_prefix, dea_full), (hist_prefix, hist_full)):
        np.testing.assert_allclose(
            short.to_numpy(), full.iloc[:100].to_numpy(), rtol=0, atol=0, equal_nan=True
        )


def test_compute_features_emits_macd_columns() -> None:
    frame = compute_features(_bars())
    for column in ("macd_dif", "macd_dea", "macd_hist"):
        assert column in frame.columns
    settings = indicator_config()
    dif, dea, hist = macd(
        frame["close"],
        int(settings["macd_fast"]),
        int(settings["macd_slow"]),
        int(settings["macd_signal"]),
    )
    np.testing.assert_allclose(
        frame["macd_dif"].to_numpy(), dif.to_numpy(), rtol=0, atol=0, equal_nan=True
    )
    np.testing.assert_allclose(
        frame["macd_dea"].to_numpy(), dea.to_numpy(), rtol=0, atol=0, equal_nan=True
    )
    np.testing.assert_allclose(
        frame["macd_hist"].to_numpy(), hist.to_numpy(), rtol=0, atol=0, equal_nan=True
    )


def test_params_come_from_ledger_not_hardcoded() -> None:
    """阈值只允许来自规则账本：12/26/9 且 indicators 与 rule.params 一致。"""
    settings = indicator_config()
    assert (settings["macd_fast"], settings["macd_slow"], settings["macd_signal"]) == (12, 26, 9)
    spec = get_rule("macd_strength")
    assert (spec.param("fast"), spec.param("slow"), spec.param("signal")) == (12, 26, 9)


def test_macd_is_research_proxy_and_emits_no_trade_events() -> None:
    """红线：MACD 是研究代理的强度描述，不产生任何交易事件（金叉不是买点）。"""
    spec = get_rule("macd_strength")
    assert spec.provenance is Provenance.RESEARCH_PROXY
    raw = load_ruleset()["rules"]["macd_strength"]
    assert not raw.get("events"), "macd_strength 不得登记交易事件：强度不是转折"


def test_invalid_params_rejected() -> None:
    close = _close(60)
    with pytest.raises(ValueError):
        macd(close, 26, 12, 9)  # fast >= slow
    with pytest.raises(ValueError):
        macd(close, 12, 26, 0)
