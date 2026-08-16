"""行业板块趋势工作台 · 预计算层单元测试（P1）。

全部为纯函数 / 网络隔离测试，照 plan P1.3 的必测用例：
- 等权指数：停牌 ffill 收益=0 / 新股中途上市前段不进分母 / 1 只翻倍≈+20%
- 层级与去重：A⊃B⊃C 三层 + 同集合 Ⅱ/Ⅲ 别名合并 + 其他电源设备 反例（Ⅲ 是 Ⅱ 真子集不合并）
- 阶段判定：四阶段各造数据，stage_basis 可追溯
- RS：两板块一强一弱，排名互换、rs_above_ma20 方向正确
- 落盘隔离：monkeypatch LEI_CACHE_ROOT
- 网络零依赖：monkeypatch lei_signal.fundamentals.sources
"""
from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from lei_signal.market_context import sector_trend as st


# ── helpers ────────────────────────────────────────────────────────────────
def _wide(sym_data: dict[str, list[float]], start: str = "2025-04-23", periods: int | None = None):
    periods = periods or max(len(v) for v in sym_data.values())
    idx = pd.date_range(start, periods=periods, freq="B")
    return pd.DataFrame(sym_data, index=idx)


def _mk(close_vals, start="2025-01-01"):
    return pd.Series(
        close_vals, index=pd.date_range(start, periods=len(close_vals), freq="B")
    )


# ════════════════════════════════════════════════════════════════════════════
# 1) 等权指数合成
# ════════════════════════════════════════════════════════════════════════════
class TestEqualWeightIndex:
    def test_suspended_stock_ffill_returns_zero(self):
        """停牌（后段持平）收益 ≈ 0，不拖累指数。"""
        n = 200
        a = 100 + np.arange(n) * 0.0  # 持平
        d = np.ones(n) * 100.0
        d[-50:] = d[-51]  # 后 50 天持平（停牌）
        wide = _wide({"A": a.tolist(), "D": d.tolist()})
        idx = st.build_equal_weight_index(wide)
        last_ret = idx.pct_change().dropna().iloc[-1]
        assert abs(last_ret) < 1e-6

    def test_new_ipo_excluded_before_listing(self):
        """新股中途上市：前段不进分母，上市日无假跳空。"""
        n = 200
        base = np.ones(n) * 100.0
        wide = _wide({"A": base.tolist(), "B": base.tolist()})
        # E 第 100 天上市，价格与前相同 → 指数应平滑（无跳空）
        e = np.full(n, np.nan)
        e[100:] = 100.0
        wide["E"] = e
        idx = st.build_equal_weight_index(wide)
        # 上市日前后指数连续
        assert abs(float(idx.iloc[100]) - float(idx.iloc[99])) < 1e-6
        # 首位因无前一日收益为 NaN（约定：idx = 1000*cumprod(1+daily_ret.dropna())），
        # 其后应全有效（新股在上市前不进分母，无假跳空）。
        assert pd.isna(idx.iloc[0])
        assert idx.iloc[1:].notna().all()

    def test_one_double_returns_about_20pct(self):
        """5 只中等权；4 只持平、1 只最后一天翻倍 → 指数 ≈ +20%。"""
        n = 120
        flat = np.ones(n) * 100.0
        pop = np.ones(n) * 100.0
        pop[-1] = 200.0
        wide = _wide({
            "A": flat.tolist(), "B": flat.tolist(),
            "C": flat.tolist(), "D": flat.tolist(), "E": pop.tolist(),
        })
        idx = st.build_equal_weight_index(wide)
        ret = float(idx.dropna().iloc[-1]) / 1000.0 - 1.0
        assert 0.18 < ret < 0.22

    def test_denominator_is_daily_valid_count(self):
        """分母=当日有效成分股数（固定分母会假跳空，这里验证用可变分母）。"""
        n = 100
        # 两只均在；第三只中途上市，验证前面 days 分母=2
        wide = _wide({"A": (np.ones(n) * 10).tolist(), "B": (np.ones(n) * 10).tolist()})
        c = np.full(n, np.nan)
        c[50:] = 10.0
        wide["C"] = c
        idx = st.build_equal_weight_index(wide)
        # 上市前指数基于 2 只、上市后基于 3 只，但都持平 → 指数恒=1000
        assert float(idx.dropna().iloc[10]) == pytest.approx(1000.0)
        assert float(idx.dropna().iloc[-1]) == pytest.approx(1000.0)


# ════════════════════════════════════════════════════════════════════════════
# 2) 层级与去重
# ════════════════════════════════════════════════════════════════════════════
class TestHierarchy:
    def test_three_level_chain(self):
        boards = {
            "A": {"x", "y", "z", "w"},
            "B": {"x", "y"},          # A 真子集
            "C": {"x"},               # B 真子集
        }
        names = {"A": "父", "B": "子", "C": "孙"}
        h = st.classify_hierarchy(boards, names)
        assert h["A"]["level"] == 1 and h["A"]["parent"] is None
        assert h["B"]["level"] == 2 and h["B"]["parent"] == "A"
        assert h["C"]["level"] == 3 and h["C"]["parent"] == "B"

    def test_same_set_alias_merged_ii_iii(self):
        """同集合重复板块：无后缀 > Ⅱ > Ⅲ 取 canonical，其余记 alias。"""
        boards = {
            "P": {"a", "b", "c"},
            "P2": {"a", "b", "c"},
            "P3": {"a", "b", "c"},
        }
        names = {"P": "电源设备", "P2": "其他电源设备Ⅱ", "P3": "其他电源设备Ⅲ"}
        h = st.classify_hierarchy(boards, names)
        # canonical = 无后缀 P
        assert h["P"]["canonical"] is True
        assert set(h["P"]["canonical_of"]) == {"P2", "P3"}
        # 别名标记
        assert h["P2"]["canonical"] is False
        assert h["P3"]["canonical"] is False

    def test_subset_not_merged(self):
        """反例：其他电源设备Ⅲ 是 Ⅱ 的真子集 → 不合并，父=Ⅱ（不同集合）。"""
        boards = {
            "II": {"a", "b", "c"},
            "III": {"a", "b"},          # 真子集
        }
        names = {"II": "其他电源设备Ⅱ", "III": "其他电源设备Ⅲ"}
        h = st.classify_hierarchy(boards, names)
        assert h["II"]["canonical"] is True
        assert h["III"]["canonical"] is True
        assert h["III"]["parent"] == "II"
        assert h["III"]["level"] == 2

    def test_validate_hierarchy_no_violation(self):
        # 父 == 子之并：A = B∪C，无告警
        boards = {"A": {"x", "y", "z"}, "B": {"x", "y"}, "C": {"z"}}
        h = st.classify_hierarchy(boards, {"A": "a", "B": "b", "C": "c"})
        warns = st.validate_hierarchy(boards, h)
        assert warns == []
        # 父 ≠ 子之并：A={x,y,z}，子只有 B={x,y} → 应告警
        boards2 = {"A": {"x", "y", "z"}, "B": {"x", "y"}}
        h2 = st.classify_hierarchy(boards2, {})
        assert st.validate_hierarchy(boards2, h2) != []


# ════════════════════════════════════════════════════════════════════════════
# 3) 阶段判定（四阶段 + stage_basis 可追溯）
# ════════════════════════════════════════════════════════════════════════════
class TestStage:
    def _sma60(self, s):
        return s.rolling(60, min_periods=60).mean()

    def test_markup(self):
        idx = _mk(np.linspace(100, 200, 300))
        st_, basis = st.classify_stage(
            idx_close=idx, sma60_series=self._sma60(idx), sma60_slope_sign=1,
            ema20_slope_sign=1, rs_above_ma20=True, breadth_divergence=False, hit_count=10,
        )
        assert st_ == "markup"
        assert len(basis) >= 2

    def test_distribution(self):
        idx = _mk(np.linspace(100, 200, 300))
        st_, basis = st.classify_stage(
            idx_close=idx, sma60_series=self._sma60(idx), sma60_slope_sign=-1,
            ema20_slope_sign=-1, rs_above_ma20=True, breadth_divergence=False, hit_count=10,
        )
        assert st_ == "distribution"
        assert any("派发" in b or "SMA60 斜率走平" in b or "宽度背离" in b for b in basis)

    def test_accumulation(self):
        # 价格在 SMA60 下方，但 RS 强于基准且 EMA20 未转弱
        idx = _mk(np.linspace(200, 100, 300))
        st_, _ = st.classify_stage(
            idx_close=idx, sma60_series=self._sma60(idx), sma60_slope_sign=-1,
            ema20_slope_sign=0, rs_above_ma20=True, breadth_divergence=False, hit_count=10,
        )
        assert st_ == "accumulation"

    def test_decline(self):
        idx = _mk(np.linspace(200, 100, 300))
        st_, _ = st.classify_stage(
            idx_close=idx, sma60_series=self._sma60(idx), sma60_slope_sign=-1,
            ema20_slope_sign=-1, rs_above_ma20=False, breadth_divergence=False, hit_count=10,
        )
        assert st_ == "decline"

    def test_insufficient_sample(self):
        idx = _mk(np.linspace(100, 200, 300))
        st_, basis = st.classify_stage(
            idx_close=idx, sma60_series=self._sma60(idx), sma60_slope_sign=1,
            ema20_slope_sign=1, rs_above_ma20=True, breadth_divergence=False, hit_count=3,
        )
        assert st_ is None
        assert basis == ["样本不足（命中成分股 < 5 只）"]


# ════════════════════════════════════════════════════════════════════════════
# 4) RS 相对强度
# ════════════════════════════════════════════════════════════════════════════
class TestRS:
    def test_strong_weak_ranking(self):
        n = 320
        dates = pd.date_range("2025-04-23", periods=n, freq="B")
        bench = pd.Series(100 + np.arange(n) * 0.1, index=dates)
        # 强板块：最近显著且单调强于基准（rs_norm 末段仍在上行）
        strong = bench * (1 + np.maximum(0, np.arange(n) - 280) * 0.002)
        weak = bench * (1 - np.maximum(0, np.arange(n) - 280) * 0.002)
        boards_idx = {"STR": strong, "WEAK": weak}
        levels = {"STR": 1, "WEAK": 1}
        rs = st.compute_rs_panel(boards_idx, bench, levels)
        # 强板块 pctile 应高于弱板块
        assert rs["STR"]["rs_pctile"].dropna().iloc[-1] > rs["WEAK"]["rs_pctile"].dropna().iloc[-1]
        # rs_above_ma20 方向与强度一致
        assert rs["STR"]["rs_above_ma20"].dropna().iloc[-1] == True
        assert rs["WEAK"]["rs_above_ma20"].dropna().iloc[-1] == False

    def test_rs_normalized_to_100(self):
        n = 200
        dates = pd.date_range("2025-04-23", periods=n, freq="B")
        bench = pd.Series(np.linspace(100, 110, n), index=dates)
        idx = pd.Series(np.linspace(100, 121, n), index=dates)  # +10%
        rs = st.compute_rs_panel({"X": idx}, bench, {"X": 1})
        rn = rs["X"]["rs_norm"].dropna()
        # 相对基准 +10% → 归一化后 ≈ 110
        assert rn.iloc[-1] == pytest.approx(110.0, abs=0.5)


# ════════════════════════════════════════════════════════════════════════════
# 5) 趋势读出（复用 4 个轻入口）
# ════════════════════════════════════════════════════════════════════════════
class TestTrendReadout:
    def test_green_uptrend(self):
        close = _mk(np.linspace(100, 200, 300))
        out = st.read_trend_from_close(close)
        assert out["signal_color"] == "green"
        assert out["signal_color_cn"] == "绿"
        assert out["ema20_slope_pct"] is not None
        assert out["macd_status"] is not None  # MACD 与三色同屏（已算出）
        assert out["provenance"] == "research_proxy"
        assert out["alignment_cn"] in ("多头排列", "均线纠结")

    def test_short_series_only_color(self):
        close = _mk(np.linspace(100, 110, 15))  # <21 根
        out = st.read_trend_from_close(close)
        assert out["signal_color"] is None
        assert out["macd_status"] is None


# ════════════════════════════════════════════════════════════════════════════
# 6) 落盘隔离 + 网络零依赖
# ════════════════════════════════════════════════════════════════════════════
class TestPersistenceAndNetwork:
    def test_atomic_write_isolated_to_tmp_cache(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LEI_CACHE_ROOT", str(tmp_path))
        import lei_signal.market_context.sector_trend as mod
        import importlib
        importlib.reload(mod)
        payload = {"hello": "world", "boards": {}}
        mod._save_atomic(payload, mod._snapshot_path())
        p = mod._snapshot_path()
        assert p.exists()
        assert not p.with_name(p.name + ".tmp").exists()
        loaded = mod.load_snapshot()
        assert loaded["hello"] == "world"
        # reload 还原模块，避免污染其他测试
        importlib.reload(mod)

    def test_fetch_sector_members_uses_monkeypatched_sources(self, monkeypatch, tmp_path):
        """网络零依赖：monkeypatch fundamentals.sources 取数函数。"""
        from lei_signal.fundamentals import sources

        # 隔离落盘，避免污染真实缓存
        monkeypatch.setattr(st, "ROOT", tmp_path)

        def fake_boards():
            return [
                {"code": "BK1", "name": "板块一", "pct_change": 1.0, "pe_ttm": 20.0,
                 "main_net_inflow_yi": 1.0, "up_count": 5, "down_count": 2, "total_mv_yi": 100.0},
            ]

        def fake_get_json(urls, params):
            # 返回 3 个成分股
            return {"data": {"total": 3, "diff": [
                {"f12": "600001", "f13": 1, "f14": "股票一"},
                {"f12": "000002", "f13": 0, "f14": "股票二"},
                {"f12": "300003", "f13": 0, "f14": "股票三"},
            ]}}

        monkeypatch.setattr(sources, "fetch_industry_boards", fake_boards)
        monkeypatch.setattr(sources, "_get_json", fake_get_json)

        members = st.fetch_sector_members(force=True)
        assert "BK1" in members
        ms = members["BK1"]["members"]
        # 前缀规则：6→sh, 0→sz, 3→sz
        assert "sh600001" in ms
        assert "sz000002" in ms
        assert "sz300003" in ms

    def test_prefix_rules(self):
        assert st._prefix("600001") == "sh"
        assert st._prefix("688001") == "sh"
        assert st._prefix("000001") == "sz"
        assert st._prefix("300001") == "sz"
        assert st._prefix("830001") == "bj"
        assert st._prefix("920001") == "bj"
