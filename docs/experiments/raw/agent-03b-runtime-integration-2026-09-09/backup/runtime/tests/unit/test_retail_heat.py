"""散户热度（retail_heat）纯函数单元测试。

覆盖：口径边界（缺数/窗口不足/当日未对上 K 线的点跳过）、横截面分位
（并列平均秩、样本不足不比分位）、情境化警示（过热×阶段组合）、
build_snapshot 集成（快照含 heat 字段与 meta，落盘隔离）。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lei_signal.market_context import retail_heat as rh
from lei_signal.market_context import sector_trend as st


def _idx(close_vals, start="2026-08-25"):
    return pd.Series(close_vals, index=pd.date_range(start, periods=len(close_vals), freq="B"))


def _pt(date, *, small=2.0, medium=1.0, super_large=-3.0):
    return {
        "date": date, "main_yi": super_large + 2.0, "small_yi": small,
        "medium_yi": medium, "large_yi": 2.0, "super_large_yi": super_large,
    }


class TestPointRatios:
    def test_missing_returns_none(self):
        assert rh.point_ratios({"small_yi": 1.0}, 100.0) is None
        assert rh.point_ratios(_pt("2026-09-01"), None) is None
        assert rh.point_ratios(_pt("2026-09-01"), 0.0) is None

    def test_values(self):
        r = rh.point_ratios(_pt("2026-09-01"), 100.0)
        assert r is not None
        assert abs(r["retail"] - 0.03) < 1e-9
        assert abs(r["diverge"] - 0.05) < 1e-9


class TestWindowMetric:
    def test_skips_points_without_kline(self):
        """K 线未到的当日资金流点（如盘后当日快照）跳过，不影响窗口。"""
        idx = _idx([100.0, 101, 102, 103, 104])
        pts = [_pt(str(d.date())) for d in idx.index]
        pts.append(_pt("2026-12-31"))  # 远期异常点
        v = rh.window_metric(pts, idx, 1000.0, metric="diverge", window=5)
        assert v is not None
        # 逐日 diverge = 5 / (1000×close/104)，均值应介于首尾之间
        per_day = [5.0 / (1000.0 * c / 104.0) for c in [100, 101, 102, 103, 104]]
        assert min(per_day) <= v <= max(per_day)

    def test_insufficient_window_returns_none(self):
        idx = _idx([100.0, 101, 102])
        pts = [_pt(str(d.date())) for d in idx.index]
        assert rh.window_metric(pts, idx, 1000.0, metric="diverge", window=5) is None
        assert rh.window_metric(None, idx, 1000.0, metric="diverge", window=1) is None
        assert rh.window_metric(pts, None, 1000.0, metric="diverge", window=1) is None

    def test_unknown_metric_returns_none(self):
        idx = _idx([100.0])
        pts = [_pt(str(d.date())) for d in idx.index]
        assert rh.window_metric(pts, idx, 1000.0, metric="nope", window=1) is None


class TestCrossSectionPctile:
    def test_insufficient_sample(self):
        assert rh.cross_section_pctile(1.0, [1.0] * 10) is None
        assert rh.cross_section_pctile(None, [1.0] * 30) is None

    def test_average_rank_for_ties(self):
        vals = [1.0] * 21  # 全并列 → 50 分位
        assert rh.cross_section_pctile(1.0, vals) == 50.0
        assert rh.cross_section_pctile(0.5, vals) == 0.0
        assert rh.cross_section_pctile(2.0, vals) == 100.0


class TestHeatState:
    CFG = {
        "hot_pctile": 90.0,
        "cold_pctile": 10.0,
        "warn_stages": ("markup", "distribution"),
    }

    def test_warning_only_in_staged_context(self):
        assert rh.heat_state(95.0, "markup", self.CFG)["warning"] is True
        assert rh.heat_state(95.0, "distribution", self.CFG)["warning"] is True
        s = rh.heat_state(95.0, "decline", self.CFG)
        assert s["hot"] is True and s["warning"] is False
        assert rh.heat_state(95.0, None, self.CFG)["warning"] is False
        assert rh.heat_state(50.0, "markup", self.CFG)["hot"] is False
        assert rh.heat_state(None, "markup", self.CFG)["hot"] is False

    def test_cold_zone(self):
        s = rh.heat_state(5.0, "decline", self.CFG)
        assert s["cold"] is True and s["hot"] is False and s["warning"] is False
        assert "散户冰点" in (s["note_cn"] or "")
        assert rh.heat_state(50.0, "markup", self.CFG)["cold"] is False
        # 中性区间既不过热也不过冷
        mid = rh.heat_state(50.0, None, self.CFG)
        assert mid["hot"] is False and mid["cold"] is False


class TestHeatPool:
    def test_l3_excluded_from_pool(self):
        """l1_l2 池：三级细分板块不进分母，但自己仍有 heat_value 可定位。"""
        rows = (
            [{"level": 1, "heat_value": float(i)} for i in range(12)]
            + [{"level": 2, "heat_value": float(20 + i)} for i in range(12)]
            + [{"level": 3, "heat_value": 999.0}, {"level": 3, "heat_value": -999.0}]
        )
        pool = rh.heat_pool_values(rows, "l1_l2")
        assert len(pool) == 24
        assert 999.0 not in pool and -999.0 not in pool
        # L3 极端值按池定位：999 → 满分位，-999 → 0 分位
        assert rh.cross_section_pctile(999.0, pool) == 100.0
        assert rh.cross_section_pctile(-999.0, pool) == 0.0

    def test_all_mode_and_empty_fallback(self):
        rows = [{"level": 3, "heat_value": 1.0}, {"level": 3, "heat_value": 2.0}]
        assert rh.heat_pool_values(rows, "all") == [1.0, 2.0]
        # 全是 L3 时池空回落全量（防御，不冒充）
        assert rh.heat_pool_values(rows, "l1_l2") == [1.0, 2.0]


class TestHeatConfig:
    def test_reads_ledger(self):
        cfg = rh.heat_config()
        assert cfg["metric"] in rh.METRIC_LABELS
        assert cfg["window_days"] > 0
        assert 0 < cfg["hot_pctile"] <= 100
        assert cfg["version"] not in (None, "default")  # rules.v2.yaml 已登记


class TestSnapshotIntegration:
    def test_snapshot_contains_heat_fields(self, monkeypatch, tmp_path):
        """build_snapshot 产出 heat 字段与 meta；数据不足时字段为 null/False 不冒充。"""
        import itertools

        monkeypatch.setenv("LEI_CACHE_ROOT", str(tmp_path))
        # 对齐窗口的 4000 只门槛面向真实全市场宽表，与热度逻辑正交，测试中直通
        monkeypatch.setattr(st, "_align_window", lambda w, **k: w)
        n = 140
        rng = np.random.default_rng(3)
        cols = {f"S{i}": (100 + np.arange(n) * (0.1 * (i % 3 - 1)) + rng.normal(0, 0.5, n)).tolist()
                for i in range(10)}
        wide = pd.DataFrame(cols, index=pd.date_range("2026-01-01", periods=n, freq="B"))
        combos = list(itertools.combinations(list(cols), 5))[:22]  # 每组合 5 只，互不相同
        members = {f"BK9{i:03d}": {"name": f"组{i}", "members": list(c)} for i, c in enumerate(combos)}
        flows, daily_ref = {}, {}
        for i, c in enumerate(members):
            flows[f"BK9{i:03d}"] = [
                _pt(str(d.date()), small=float(i % 5) - 1.5, super_large=1.5)
                for d in wide.index[-25:]
            ]
            daily_ref[f"BK9{i:03d}"] = {"total_mv_yi": 1000.0 + 10 * i}
        snap = st.build_snapshot(members, wide, daily_ref=daily_ref, flows=flows)
        assert "heat" in snap
        assert snap["heat"]["metric"] == rh.heat_config()["metric"]
        assert snap["heat"]["n_valid"] == len(members)  # 全部板块窗口均足
        rows = {r["code"]: r for r in snap["boards"]}
        pct = [r["heat_pctile"] for r in rows.values()]
        assert all(p is not None for p in pct)
        # 平均秩口径：唯一极值分位为 (n-0.5)/n 与 0.5/n，不取 0/100
        assert max(pct) > 95.0 and min(pct) < 5.0
        # 过热板块必须给出布尔警示位（是否亮警示取决于阶段组合）
        hot_rows = [r for r in rows.values() if r["heat_hot"]]
        assert hot_rows, "至少存在一个过热板块"
        for r in hot_rows:
            assert isinstance(r["heat_warning"], bool)

        # 无资金流 → 字段全空不冒充
        snap2 = st.build_snapshot(members, wide, daily_ref=daily_ref, flows={})
        assert snap2["heat"]["n_valid"] == 0
        assert all(r["heat_pctile"] is None and r["heat_warning"] is False
                   for r in snap2["boards"])
