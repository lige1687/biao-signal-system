"""情绪材料性能修复（2026-09-15 agent-ask-stability）：

- ``_cn_small_flow20`` 向量化后与旧逐点实现输出一致（含「同一 (date, code)
  两文件重复时先出现者为准」的合并语义），真实缓存文件上 10.9s→0.2s；
- ``fetch_margin_history`` 进程内 TTL 记忆化：同一 lookback 复用、
  失败不缓存，日频叙事层指标不再每个提问都翻页联网。
"""
from __future__ import annotations

import json

import pandas as pd
import pytest

from lei_signal.fundamentals import sources
from lei_signal.market_context import market_mood as mm


def _old_cn_small_flow20(cache) -> pd.Series | None:
    """旧实现原样保留为对照基准（逐点 setdefault 合并语义）。"""
    series: dict = {}
    for fname in ("tx_sector_flow_pilot.json", "sector_flow_history.json"):
        p = cache / fname
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        boards = data.get("boards") if "boards" in data else data
        for code, pts in (boards or {}).items():
            for pt in pts:
                v = pt.get("small_yi") if "small_yi" in pt else pt.get("small_yi")
                if v is not None:
                    series.setdefault(pd.to_datetime(pt["date"]), {}).setdefault(code, v)
    if not series:
        return None
    agg = pd.Series({k: sum(v.values()) for k, v in series.items()}).sort_index()
    return agg.rolling(20, min_periods=20).sum()


@pytest.fixture()
def flow_cache(tmp_path, monkeypatch):
    """合成两文件：同一 (date, code) 在两文件重复（先出现者为准）、
    缺 small_yi 的点被跳过、日期跨 25 天让 20 日窗口有输出。"""
    days = [d.strftime("%Y-%m-%d") for d in pd.date_range("2026-07-01", periods=25)]
    pilot = {"boards": {}}
    history = {"boards": {}}
    for bi, code in enumerate(("BK001", "BK002", "BK003")):
        pilot["boards"][code] = [
            {"date": d, "small_yi": float(bi * 10 + i)} for i, d in enumerate(days)
        ]
        # history 重复同一 (date, code) 且值不同——旧语义保留 pilot 的值
        history["boards"][code] = [
            {"date": d, "small_yi": 9999.0} for d in days
        ] + [{"date": days[-1]}]  # 缺 small_yi 的点
    (tmp_path / "tx_sector_flow_pilot.json").write_text(
        json.dumps(pilot), encoding="utf-8")
    (tmp_path / "sector_flow_history.json").write_text(
        json.dumps(history), encoding="utf-8")
    monkeypatch.setattr(mm, "_CACHE", tmp_path)
    return tmp_path


def test_small_flow20_matches_old_implementation(flow_cache):
    new = mm._cn_small_flow20()
    old = _old_cn_small_flow20(flow_cache)
    assert new is not None and old is not None
    pd.testing.assert_series_equal(new, old, check_exact=False, rtol=1e-12)


def test_small_flow20_first_file_wins_on_overlap(flow_cache):
    new = mm._cn_small_flow20()
    # 最后一天三板块 pilot 值 = 0+24, 1*10+24, 2*10+24 = 24+34+44 = 102/天
    # 20 日窗口合计：sum_{i=5..24} (3*i + 30) = 3*sum(5..24) + 20*30
    expected = 3 * sum(range(5, 25)) + 20 * 30
    assert abs(new.iloc[-1] - expected) < 1e-6
    assert new.iloc[-1] != 9999.0 * 3 * 20  # history 的重复值没有覆盖 pilot


def test_small_flow20_missing_files_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(mm, "_CACHE", tmp_path)
    assert mm._cn_small_flow20() is None


def test_mild_double_negative_does_not_create_ice_point(monkeypatch):
    dates = pd.to_datetime(["2026-09-28"])
    monkeypatch.setattr(mm, "_margin_chg20", lambda: pd.Series([-0.001], index=dates))
    monkeypatch.setattr(mm, "_all_a_equal_index", lambda: pd.Series([-0.002], index=dates))
    out = mm.cn_mood()
    assert out["components"]["margin20"]["vote"] == -1
    assert out["components"]["equal_mom20"]["vote"] == -1
    assert out["state"] is None
    assert "冰点" in out["state_cn"] and "不合成" in out["state_cn"]


def test_eighty_percent_strong_zero_weak_is_not_divergence(tmp_path, monkeypatch):
    monkeypatch.setattr(mm, "_CACHE", tmp_path)
    boards = {f"BK{i:03d}": {"b50": 80 if i < 80 else 50} for i in range(100)}
    (tmp_path / "sector_trend_history.json").write_text(
        json.dumps([{"date": "2026-09-28", "boards": boards}]), encoding="utf-8"
    )
    out = mm.market_structure()
    assert out["available"] is True
    assert out["strong_pct"] == 80.0 and out["weak_pct"] == 0.0
    assert out["polar"] is None
    assert "分化" not in out["state_cn"]


@pytest.fixture(autouse=True)
def _clear_margin_memo(monkeypatch):
    monkeypatch.setattr(sources, "_MARGIN_HISTORY_MEMO", {})
    monkeypatch.setattr(sources, "_MARGIN_HISTORY_TTL_SECONDS", 900)
    yield


def _rows(n: int) -> list[dict]:
    return [{
        "DIM_DATE": f"2026-08-{d:02d}", "RZRQYE": 1.5e12, "RZYE": 1.4e12,
        "RQYE": 1.0e11, "RZMRE": 5.0e10, "RZYEZB": 2.1,
    } for d in range(1, n + 1)]


def test_margin_history_memoized_within_ttl(monkeypatch):
    calls = {"n": 0}

    def fake_rows(page_size: int = 1):
        calls["n"] += 1
        return _rows(5)

    monkeypatch.setattr(sources, "_fetch_margin_rows", fake_rows)
    first = sources.fetch_margin_history(lookback_days=60)
    second = sources.fetch_margin_history(lookback_days=60)
    assert calls["n"] == 1  # 第二次复用，不重复联网
    assert first == second  # 原样返回（真实数据日期不变）
    other = sources.fetch_margin_history(lookback_days=900)
    assert calls["n"] == 2  # 不同 lookback 各自缓存
    assert other == first  # 本桩下内容相同


def test_margin_history_failure_not_cached(monkeypatch):
    calls = {"n": 0}

    def flaky(page_size: int = 1):
        calls["n"] += 1
        if calls["n"] == 1:
            raise sources.FundamentalsSourceError("网络失败")
        return _rows(5)

    monkeypatch.setattr(sources, "_fetch_margin_rows", flaky)
    with pytest.raises(sources.FundamentalsSourceError):
        sources.fetch_margin_history(lookback_days=60)
    ok = sources.fetch_margin_history(lookback_days=60)
    assert calls["n"] == 2  # 失败未缓存，真实重试成功
    assert ok


def test_margin_history_ttl_expiry_refetches(monkeypatch):
    monkeypatch.setattr(sources, "_MARGIN_HISTORY_TTL_SECONDS", 0)
    calls = {"n": 0}

    def fake_rows(page_size: int = 1):
        calls["n"] += 1
        return _rows(5)

    monkeypatch.setattr(sources, "_fetch_margin_rows", fake_rows)
    sources.fetch_margin_history(lookback_days=60)
    sources.fetch_margin_history(lookback_days=60)
    assert calls["n"] == 2  # TTL=0 不复用
