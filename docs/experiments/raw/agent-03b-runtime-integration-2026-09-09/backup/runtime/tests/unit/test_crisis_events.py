"""危机管理状态机（V4/V3）单元测试：临时缓存目录构造宽度史与指数K线。"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from lei_signal.market_context import crisis_events as ce


def _write_cache(tmp_path, breadth: list[float], closes: list[float]) -> None:
    """构造 LEI_CACHE_ROOT：宽度史（ma50_pct 序列）+ 上证指数 K 线。"""
    dates = pd.bdate_range(end="2026-09-03", periods=len(breadth))
    rows = [
        {"date": d.strftime("%Y-%m-%d"), "ma20_pct": v, "ma50_pct": v, "ma200_pct": v}
        for d, v in zip(dates, breadth)
    ]
    (tmp_path / "a_share_ma_breadth_history.json").write_text(
        json.dumps(rows), encoding="utf-8"
    )
    idx_dates = pd.bdate_range(end="2026-09-04", periods=len(closes))
    df = pd.DataFrame({"close": closes, "high": closes, "low": closes, "open": closes,
                       "volume": [1.0] * len(closes)}, index=idx_dates)
    df.to_parquet(tmp_path / "000001.SS.bars.parquet")


def _eval(tmp_path, monkeypatch, breadth, closes):
    _write_cache(tmp_path, breadth, closes)
    monkeypatch.setenv("LEI_CACHE_ROOT", str(tmp_path))
    return ce.evaluate_crisis_states()


def test_normal_state_none(tmp_path, monkeypatch):
    # 宽度稳定 60%，指数沿均线上方 → 无事件
    r = _eval(tmp_path, monkeypatch, [60.0] * 300, list(np.linspace(3000, 4000, 120)))
    assert r is not None
    sse = r["readings"][0]
    assert sse["state"] == "none"
    assert r["alerts"] == []


def test_crash_warning(tmp_path, monkeypatch):
    # 20 日前 95% → 现在 60%（-35pp）；指数深跌 dev60<-5%
    breadth = [95.0] * 251 + [60.0] * 20  # len=271，iloc[-21]=95.0
    closes = list(np.linspace(4000, 3400, 119)) + [3300.0]  # 深跌
    r = _eval(tmp_path, monkeypatch, breadth, closes)
    sse = r["readings"][0]
    assert sse["dev60_pct"] < -5.0
    assert sse["breadth_delta_20"] < -30
    assert sse["state"] == "crash_warning"
    assert r["alerts"][0]["type"] == "crash_warning"
    assert r["alerts"][0]["symbol"] == "000001.SS"


def test_capitulation_rebound(tmp_path, monkeypatch):
    # 常年 40-70% → 20 天前已跌到 10%（20日窗口内无急坠）→ 近 5 日 8.0 走平
    #（|Δ5|=2）∧ 深跌——纯 V3 形态
    base = [40.0 + (i % 30) for i in range(246)]
    breadth = base + [10.0] * 20 + [8.0] * 5  # len=271，iloc[-21]=10.0
    closes = list(np.linspace(4000, 3350, 119)) + [3300.0]
    r = _eval(tmp_path, monkeypatch, breadth, closes)
    sse = r["readings"][0]
    assert sse["state"] == "capitulation_rebound"
    assert sse["breadth_pctile_1y"] <= 5.0
    assert abs(sse["breadth_delta_5"]) <= 3.0
    assert r["alerts"][0]["type"] == "capitulation_rebound"


def test_v4_takes_priority(tmp_path, monkeypatch):
    # 同时满足 V4（20日急坠）与 V3（地底+5日走平）——构造：常年 40-45% →
    # 15 天内跌到 8%（20 日窗口含下跌段 delta_20 < -30）→ 近 5 日 8.0 走平。
    # 两条件并立时 V4 优先（口径选择3）。
    breadth = [40.0 + (i % 6) for i in range(251)] + [45.0] * 15 + [8.0] * 5
    closes = list(np.linspace(4000, 3350, 119)) + [3300.0]
    r = _eval(tmp_path, monkeypatch, breadth, closes)
    sse = r["readings"][0]
    assert sse["state"] == "crash_warning"  # 口径选择3：V4 优先


def test_missing_breadth_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("LEI_CACHE_ROOT", str(tmp_path / "empty"))
    (tmp_path / "empty").mkdir()
    assert ce.evaluate_crisis_states() is None


@pytest.mark.parametrize("delta20", [-29.9, -30.1])
def test_threshold_boundary(tmp_path, monkeypatch, delta20):
    # 阈值邻域：-30pp 是开区间边界（< 才触发）
    breadth = [90.0] * 250 + [90.0] * 20 + [90.0 + delta20]
    closes = list(np.linspace(4000, 3350, 119)) + [3300.0]
    r = _eval(tmp_path, monkeypatch, breadth, closes)
    sse = r["readings"][0]
    expected = "crash_warning" if delta20 < -30.0 else "none"
    assert sse["state"] == expected
