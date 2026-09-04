"""因子观测台单测：纯函数 + build_panel 落盘 + 路由烟测（无网络）。"""
from __future__ import annotations

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lei_signal.api.factor_service import FactorPanelService
from lei_signal.api.routes import factors as factors_route
from lei_signal.market_context import factor_panel as fp


def _mk_bars(n: int, *, start: float = 100.0, growth: float = 0.001,
             start_date: str = "2024-01-02") -> pd.DataFrame:
    """确定性 OHLCV：close 等比递增，high/low 对称包裹。"""
    closes = [start * ((1.0 + growth) ** i) for i in range(n)]
    rows = []
    for c in closes:
        rows.append({
            "open": c, "high": c * 1.004, "low": c * 0.996, "close": c, "volume": 1_000_000,
        })
    return pd.DataFrame(rows, index=pd.bdate_range(start=start_date, periods=n))


# ── classify_symbol ────────────────────────────────────────────────────
@pytest.mark.parametrize("code,group,subgroup", [
    ("TH881169.SECTOR", "sector", "sector"),
    ("^GSPC", "us", "us_index"),
    ("SOXX", "us", "us_etf"),
    ("159915.SZ", "cn", "cn_etf"),
    ("510300.SS", "cn", "cn_etf"),
    ("000300.SS", "cn", "cn_index"),
    ("600519.SS", "cn", "cn_stock"),
])
def test_classify_symbol(code, group, subgroup):
    assert fp.classify_symbol(code) == (group, subgroup)


# ── 纯函数 ──────────────────────────────────────────────────────────────
def test_realized_vol_constant_series_is_zero():
    s = pd.Series([100.0] * 30)
    assert fp.realized_vol(s) == 0.0


def test_realized_vol_short_series_none():
    assert fp.realized_vol(pd.Series([1.0, 2.0, 3.0])) is None


def test_realized_vol_percentile_needs_min_history():
    assert fp.realized_vol_percentile(pd.Series(range(1, 101), dtype=float)) is None


def test_realized_vol_percentile_high_when_last_vol_extreme():
    n = 400
    base = [100.0] * (n - 1) + [200.0]  # 最后一日暴涨 → 当前 RV 为全史最高
    pct = fp.realized_vol_percentile(pd.Series(base))
    assert pct is not None and pct > 0.99


def test_momentum_skip_formula():
    g, n = 0.001, 300
    s = pd.Series([100.0 * ((1 + g) ** i) for i in range(n)])
    expect = (1 + g) ** ((n - 1) - fp.MOM_SKIP) / (1 + g) ** ((n - 1) - fp.MOM_LONG) - 1
    assert fp.momentum_skip(s) == pytest.approx(expect, rel=1e-9)


def test_momentum_skip_insufficient_history():
    assert fp.momentum_skip(pd.Series([1.0] * 100)) is None


def test_momentum_plain():
    s = pd.Series([110.0] + [121.0] * 20)  # 末 20 日涨幅 10%
    assert fp.momentum_plain(s) == pytest.approx(0.10)


def test_adx14_monotonic_trend_is_high():
    df = _mk_bars(120, growth=0.002)
    adx = fp.adx14(df["high"], df["low"], df["close"])
    assert adx is not None and adx > 25


def test_adx14_flat_series_none():
    s = pd.Series([100.0] * 100)
    assert fp.adx14(s, s, s) is None


def test_adx14_short_series_none():
    df = _mk_bars(20)
    assert fp.adx14(df["high"], df["low"], df["close"]) is None


# ── compute_symbol_factors ─────────────────────────────────────────────
def test_compute_symbol_factors_full_history():
    row = fp.compute_symbol_factors(_mk_bars(400), now=pd.Timestamp("2024-01-02").to_pydatetime())
    assert row["mom_121"] is not None and row["mom_121"] > 0
    assert row["rv_pct"] is not None and 0.0 <= row["rv_pct"] <= 1.0
    assert row["adx14"] is not None
    assert row["above_ema20"] is True and row["above_ema120"] is True
    assert row["notes"] == []


def test_compute_symbol_factors_partial_history_flags_notes():
    row = fp.compute_symbol_factors(_mk_bars(252))  # <253 → 12-1 不可算
    assert row["mom_121"] is None
    assert any("12-1" in n for n in row["notes"])


def test_compute_symbol_factors_stale_note():
    from datetime import datetime

    df = _mk_bars(400)  # 截至约 2025 年中
    row = fp.compute_symbol_factors(df, now=datetime(2026, 8, 27))
    assert any("数据较旧" in n for n in row["notes"])


# ── build_panel / load_panel（tmp 目录 + monkeypatch ROOT）────────────
@pytest.fixture()
def panel_env(tmp_path, monkeypatch):
    monkeypatch.setattr(fp, "ROOT", tmp_path)
    pd.DataFrame({"close": [100.0 * 1.001 ** i for i in range(320)]}).to_parquet(
        tmp_path / "159AAA.SZ.bars.parquet")
    _mk_bars(320, growth=0.002).to_parquet(tmp_path / "510BBB.SS.bars.parquet")
    _mk_bars(320, growth=-0.001).to_parquet(tmp_path / "TH881XXX.SECTOR.bars.parquet")
    _mk_bars(60).to_parquet(tmp_path / "159CCC.SZ.bars.parquet")  # 太短 → 跳过
    return tmp_path


def test_build_panel_structure_and_ranking(panel_env):
    snap = fp.build_panel(cache_dir=panel_env, now=pd.Timestamp("2024-06-03").to_pydatetime())
    codes = [r["code"] for r in snap["symbols"]]
    assert codes == ["159AAA.SZ", "510BBB.SS"]  # 同为 cn_etf，按 code 排序
    assert snap["counts"]["skipped_too_short_or_broken"] == ["159CCC.SZ"]
    assert snap["data_as_of"] is not None
    assert set(snap["factors"]) == {"rv_pct", "mom_121", "mom_20", "adx14", "vol_up", "idio_vol"}
    for meta in snap["factors"].values():
        assert meta["verdict_level"] in ("pass", "weak", "inverse", "fail")

    # vol_ok：close-only 标的 None + note；OHLCV 标的有布尔值
    by_code = {r["code"]: r for r in snap["symbols"]}
    assert by_code["159AAA.SZ"]["vol_ok"] is None
    assert any("量能" in n for n in by_code["159AAA.SZ"]["notes"])
    assert by_code["510BBB.SS"]["vol_ok"] in (True, False)

    # 板块排名：唯一板块 rank=1
    assert len(snap["sectors"]) == 1
    assert snap["sectors"][0]["mom_121_rank"] == 1

    # 快照可回读（原子落盘 + JSON 合法）
    loaded = fp.load_panel()
    assert loaded == snap


def test_build_panel_group_percentile_needs_three(panel_env):
    snap = fp.build_panel(cache_dir=panel_env)
    for r in snap["symbols"]:
        # cn 组只有 2 只 → 不给组内分位
        assert r["mom_20_group_pct"] is None


def test_snapshot_json_has_no_nan(panel_env):
    import json

    snap = fp.build_panel(cache_dir=panel_env)
    text = (panel_env / "factor_panel_snapshot.json").read_text(encoding="utf-8")
    json.loads(text)  # allow_nan=False 序列化成功即无 NaN
    assert snap["provenance"] == "research_proxy"


# ── 路由烟测（只挂 factors 路由的轻量 app，无网络）────────────────────
def _client() -> TestClient:
    app = FastAPI()
    app.state.factor_service = FactorPanelService()
    app.include_router(factors_route.router)
    return TestClient(app)


def test_route_panel_404_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(fp, "ROOT", tmp_path)
    resp = _client().get("/api/factors/panel")
    assert resp.status_code == 404
    assert "precompute_factor_panel" in resp.json()["detail"]


def test_route_panel_serves_snapshot(panel_env):
    fp.build_panel(cache_dir=panel_env)
    resp = _client().get("/api/factors/panel")
    assert resp.status_code == 200
    body = resp.json()
    assert body["provenance"] == "research_proxy"
    assert isinstance(body["symbols"], list) and isinstance(body["sectors"], list)
    assert body["research_proxy_note"]


# ── IVOL（个股层排雷，2026-09-04 落地）──────────────────────────────────
def _mk_osc_bars(n: int, *, up: float = 0.02, down: float = -0.01) -> pd.Series:
    """交替涨跌的收盘序列（收益非常数，供 IVOL std 计算）。"""
    c = 100.0
    closes = []
    for i in range(n):
        c *= 1 + (up if i % 2 == 0 else down)
        closes.append(c)
    return pd.Series(closes, index=pd.bdate_range(start="2024-01-02", periods=n))


def test_idio_vol_60_formula():
    # 等权市场日收益恒定 0；个股超额收益交替 +2%/-1% → 有正的年化 std
    rng = pd.Series([0.0] * 120, index=pd.bdate_range(start="2024-01-02", periods=120))
    stock = _mk_osc_bars(120)
    v = fp.idio_vol_60(stock, rng)
    assert v is not None and v > 0.1  # 年化后显著为正


def test_idio_vol_60_short_none():
    rng = pd.Series([0.0] * 30)
    assert fp.idio_vol_60(pd.Series([100.0] * 31), rng) is None


def test_build_panel_ivol_needs_three_stocks(tmp_path, monkeypatch):
    """个股 <3 只：ivol60 有值、截面分位留空（不排名，等扩池自动生效）。"""
    monkeypatch.setattr(fp, "ROOT", tmp_path)
    for j, g in enumerate((0.002, -0.001, 0.001)):
        _mk_bars(320, growth=g).to_parquet(tmp_path / f"TH881X{j:02d}.SECTOR.bars.parquet")
    pd.DataFrame({"close": _mk_osc_bars(320, up=0.02, down=-0.01)}).to_parquet(
        tmp_path / "600AAA.SS.bars.parquet")
    pd.DataFrame({"close": _mk_osc_bars(320, up=0.012, down=-0.002)}).to_parquet(
        tmp_path / "002BBB.SZ.bars.parquet")
    snap = fp.build_panel(cache_dir=tmp_path, now=pd.Timestamp("2024-06-03").to_pydatetime())
    stocks = [r for r in snap["symbols"] if r["subgroup"] == "cn_stock"]
    assert len(stocks) == 2
    for r in stocks:
        assert r["ivol60_ann"] is not None and r["ivol60_ann"] > 0
        assert r["ivol_pct"] is None  # <3 只不排名
    # ETF/板块不带 IVOL 字段（口径：不适用）
    etfs = [r for r in snap["symbols"] if r["subgroup"] != "cn_stock"]
    assert all("ivol60_ann" not in r for r in etfs)


def test_build_panel_ivol_ranks_when_three_stocks(tmp_path, monkeypatch):
    monkeypatch.setattr(fp, "ROOT", tmp_path)
    for j, g in enumerate((0.002, -0.001, 0.001)):
        _mk_bars(320, growth=g).to_parquet(tmp_path / f"TH881X{j:02d}.SECTOR.bars.parquet")
    pd.DataFrame({"close": _mk_osc_bars(320, up=0.05, down=-0.04)}).to_parquet(
        tmp_path / "600AAA.SS.bars.parquet")  # 高特质波动
    pd.DataFrame({"close": _mk_osc_bars(320, up=0.012, down=-0.002)}).to_parquet(
        tmp_path / "002BBB.SZ.bars.parquet")
    pd.DataFrame({"close": _mk_osc_bars(320, up=0.006, down=-0.001)}).to_parquet(
        tmp_path / "600CCC.SS.bars.parquet")
    snap = fp.build_panel(cache_dir=tmp_path, now=pd.Timestamp("2024-06-03").to_pydatetime())
    by_code = {r["code"]: r for r in snap["symbols"] if r["subgroup"] == "cn_stock"}
    assert by_code["600AAA.SS"]["ivol_pct"] == 1.0  # 最高特质波动 → 分位 1.0（彩票股警示）
    assert by_code["600CCC.SS"]["ivol_pct"] < by_code["002BBB.SZ"]["ivol_pct"]
