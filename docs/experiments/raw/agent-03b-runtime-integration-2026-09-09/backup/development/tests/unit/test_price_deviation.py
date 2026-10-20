"""price_deviation 单测：合成趋势序列验证分位、连续极端天数与提醒落库（任务书 #3）。"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

import lei_signal.market_context.price_deviation as pd_mod
from lei_signal.market_context.price_deviation import (
    DeviationReading,
    build_reading,
    consecutive_extreme_days,
    ema_deviation_series,
    evaluate_alerts,
    get_price_deviation,
    load_alert_history,
    persist_alerts,
)


def _params(**overrides) -> dict:
    base = {
        "ma_windows": [20, 60, 200],
        "percentile_windows": [756, 1260],
        "percentile_min_periods": 50,   # 测试用小窗口
        "extreme_high": 0.95,
        "extreme_low": 0.05,
        "consecutive_days_min": 3,
        "watch": {},
        "overheat_reference_pct": {"000300.SS": 15.0},
    }
    base.update(overrides)
    return base


def _idx(n: int) -> pd.DatetimeIndex:
    return pd.bdate_range("2020-01-02", periods=n)


def test_ema_deviation_flat_series_is_zero():
    close = pd.Series(np.full(300, 100.0), index=_idx(300))
    dev = ema_deviation_series(close, 20)
    assert dev.abs().max() < 1e-9


def test_consecutive_extreme_days_counts_trailing_run():
    pct = pd.Series([80.0, 96.0, 97.0, 98.0, 99.0])
    days, direction = consecutive_extreme_days(pct, 0.95, 0.05)
    assert days == 4 and direction == "high"
    # 中断后重新连续
    pct2 = pd.Series([80.0, 99.0, 60.0, 97.0, 98.0])
    days2, direction2 = consecutive_extreme_days(pct2, 0.95, 0.05)
    assert days2 == 2 and direction2 == "high"
    # 低分位极端
    pct3 = pd.Series([50.0, 3.0, 2.0, 4.0])
    days3, direction3 = consecutive_extreme_days(pct3, 0.95, 0.05)
    assert days3 == 3 and direction3 == "low"
    # 末值不极端 → 0
    pct4 = pd.Series([99.0, 99.0, 50.0])
    days4, direction4 = consecutive_extreme_days(pct4, 0.95, 0.05)
    assert days4 == 0 and direction4 is None
    # 末值 NaN → 0
    pct5 = pd.Series([99.0, 99.0, float("nan")])
    assert consecutive_extreme_days(pct5, 0.95, 0.05) == (0, None)


def _trending_close(n: int, daily_ret: float) -> pd.Series:
    return pd.Series(100.0 * (1.0 + daily_ret) ** np.arange(n), index=_idx(n))


def test_build_reading_overheat_extreme_triggers():
    """末段持续加速上涨 → 偏离高分位 + 连续极端天数达标 → 提醒。"""
    params = _params()
    # 前 400 天温和，后 30 天每天 +1.5%（脱离历史分布 → 高分位）
    close = pd.concat([
        _trending_close(400, 0.0005),
        _trending_close(30, 0.015) * _trending_close(400, 0.0005).iloc[-1] / 100.0,
    ])
    close.index = _idx(len(close))
    reading = build_reading(
        close, symbol="000300.SS", name_cn="沪深300", ma_window=60, params=params
    )
    assert reading.deviation_pct is not None and reading.deviation_pct > 0
    assert reading.percentile_3y is not None and reading.percentile_3y >= 95.0
    assert reading.extreme_direction == "high"
    assert reading.consecutive_extreme_days >= 3

    alerts = evaluate_alerts([reading], params)
    assert len(alerts) == 1
    assert alerts[0].direction == "overheat"
    assert "仅预警" in alerts[0].message_cn
    assert "不是卖点" in alerts[0].message_cn


def test_build_reading_oversold_direction():
    """末段持续暴跌 → 低分位极端 → oversold 提醒。"""
    params = _params()
    close = pd.concat([
        _trending_close(400, -0.0002),
        _trending_close(30, -0.012) * _trending_close(400, -0.0002).iloc[-1] / 100.0,
    ])
    close.index = _idx(len(close))
    reading = build_reading(
        close, symbol="000001.SS", name_cn="上证指数", ma_window=200, params=params
    )
    alerts = evaluate_alerts([reading], params)
    assert len(alerts) == 1
    assert alerts[0].direction == "oversold"
    assert "不是买点" in alerts[0].message_cn


def test_build_reading_insufficient_data():
    close = _trending_close(50, 0.001)  # 少于 200+1 根
    reading = build_reading(
        close, symbol="X", name_cn="X", ma_window=200, params=_params()
    )
    assert reading.data_status == "unavailable"
    assert reading.deviation_pct is None
    assert evaluate_alerts([reading], _params()) == []


def test_no_alert_in_normal_range():
    """普通温和走势：分位不极端 → 无提醒。"""
    rng = np.random.default_rng(11)
    close = pd.Series(100.0 * np.cumprod(1.0 + rng.normal(0.0003, 0.008, 500)),
                      index=_idx(500))
    reading = build_reading(
        close, symbol="X", name_cn="X", ma_window=60, params=_params()
    )
    alerts = evaluate_alerts([reading], _params())
    # 正常情况不应有多日连续极端（随机游走极端分位难维持 3 天）
    assert all(a.consecutive_days >= 3 for a in alerts)


def test_persist_alerts_dedup_and_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(pd_mod, "ROOT", tmp_path)
    alert = pd_mod.DeviationAlert(
        date="2026-09-04", symbol="000300.SS", name_cn="沪深300", ma_window=60,
        direction="overheat", percentile=98.0, consecutive_days=5,
        message_cn="测试提醒",
    )
    assert persist_alerts([alert]) == 1
    assert persist_alerts([alert]) == 0  # 同 key 去重
    history = load_alert_history()
    assert len(history) == 1
    assert history[0]["message_cn"] == "测试提醒"


def test_full_pipeline_extreme_sample_persists(tmp_path, monkeypatch):
    """验收口径：人为构造极端样本 → get_price_deviation 触发提醒并落库。"""
    monkeypatch.setattr(pd_mod, "ROOT", tmp_path)
    monkeypatch.setattr(pd_mod, "_cache", {})
    monkeypatch.setattr(pd_mod, "_params", lambda: _params(
        ma_windows=[60],
        watch={"000300.SS": "沪深300"},
    ))
    # 伪造本地 bars 缓存：末段加速上涨
    close = pd.concat([
        _trending_close(400, 0.0005),
        _trending_close(30, 0.015) * _trending_close(400, 0.0005).iloc[-1] / 100.0,
    ])
    close.index = _idx(len(close))
    bars_path = tmp_path / "000300.SS.bars.parquet"
    bars_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"close": close.values}, index=close.index).to_parquet(bars_path)

    payload = get_price_deviation(refresh=True)
    assert payload["active_alerts"], "极端样本必须触发提醒"
    alert_file = json.loads((tmp_path / "price_deviation_alerts.json").read_text())
    assert len(alert_file) >= 1
    assert alert_file[0]["direction"] == "overheat"
    assert payload["active_alerts"][0]["consecutive_days"] >= 3
