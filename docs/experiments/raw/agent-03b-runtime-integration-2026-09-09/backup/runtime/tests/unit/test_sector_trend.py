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
# 3b) 道路层观察点（stage_checkpoints：条件清单 + 下一观察点）
# ════════════════════════════════════════════════════════════════════════════
class TestStageCheckpoints:
    def _sma60(self, s):
        return s.rolling(60, min_periods=60).mean()

    def test_conditions_and_distance(self):
        idx = _mk(np.linspace(100, 200, 300))
        out = st.stage_checkpoints(
            stage="markup", idx_close=idx, sma60_series=self._sma60(idx),
            sma60_slope_sign=1, ema20_slope_sign=1, rs_above_ma20=True,
            breadth_divergence=False, hit_count=10,
        )
        assert [c["key"] for c in out["conditions"]] == [
            "price_above_sma60", "sma60_slope_up", "rs_above_ma20",
        ]
        assert all(c["met"] for c in out["conditions"])
        # 价格远高于 SMA60 → dist 为正
        assert out["dist_to_sma60_pct"] > 0
        assert out["next_watch_kind"] == "risk"
        assert "跌破 SMA60" in out["next_watch"]

    def test_accumulation_only_price_missing(self):
        # 筑底：SMA60 斜率向上、RS 强，仅价格在 SMA60 下方 → 升级观察点带差距
        idx = _mk(np.linspace(200, 100, 300))
        out = st.stage_checkpoints(
            stage="accumulation", idx_close=idx, sma60_series=self._sma60(idx),
            sma60_slope_sign=1, ema20_slope_sign=1, rs_above_ma20=True,
            breadth_divergence=False, hit_count=10,
        )
        unmet = [c["label"] for c in out["conditions"] if not c["met"]]
        assert unmet == ["价格 > SMA60"]
        assert out["next_watch_kind"] == "upgrade"
        assert "上穿 SMA60" in out["next_watch"] and "还差" in out["next_watch"]
        assert out["dist_to_sma60_pct"] < 0

    def test_accumulation_multiple_missing(self):
        idx = _mk(np.linspace(200, 100, 300))
        out = st.stage_checkpoints(
            stage="accumulation", idx_close=idx, sma60_series=self._sma60(idx),
            sma60_slope_sign=-1, ema20_slope_sign=0, rs_above_ma20=True,
            breadth_divergence=False, hit_count=10,
        )
        unmet = [c["label"] for c in out["conditions"] if not c["met"]]
        assert len(unmet) == 2
        assert out["next_watch_kind"] == "upgrade"
        assert "待补齐" in out["next_watch"]

    def test_distribution_two_sided_watch(self):
        idx = _mk(np.linspace(100, 200, 300))
        out = st.stage_checkpoints(
            stage="distribution", idx_close=idx, sma60_series=self._sma60(idx),
            sma60_slope_sign=-1, ema20_slope_sign=-1, rs_above_ma20=True,
            breadth_divergence=False, hit_count=10,
        )
        assert out["next_watch_kind"] == "watch"
        assert "SMA60 斜率转向上" in out["next_watch"] and "转入下降" in out["next_watch"]

    def test_decline_bottoming_watch(self):
        idx = _mk(np.linspace(200, 100, 300))
        out = st.stage_checkpoints(
            stage="decline", idx_close=idx, sma60_series=self._sma60(idx),
            sma60_slope_sign=-1, ema20_slope_sign=-1, rs_above_ma20=False,
            breadth_divergence=False, hit_count=10,
        )
        assert out["next_watch_kind"] == "upgrade"
        assert "筑底观察" in out["next_watch"]

    def test_undefined_stage_lists_unmet(self):
        idx = _mk(np.linspace(100, 200, 300))
        out = st.stage_checkpoints(
            stage=None, idx_close=idx, sma60_series=self._sma60(idx),
            sma60_slope_sign=-1, ema20_slope_sign=-1, rs_above_ma20=False,
            breadth_divergence=False, hit_count=10,
        )
        assert out["next_watch_kind"] == "watch"
        assert "未定阶段" in out["next_watch"]

    def test_markup_with_breadth_divergence_warns(self):
        idx = _mk(np.linspace(100, 200, 300))
        out = st.stage_checkpoints(
            stage="markup", idx_close=idx, sma60_series=self._sma60(idx),
            sma60_slope_sign=1, ema20_slope_sign=1, rs_above_ma20=True,
            breadth_divergence=True, hit_count=10,
        )
        assert out["next_watch_kind"] == "risk"
        assert "宽度背离" in out["next_watch"]

    def test_insufficient_returns_empty(self):
        out = st.stage_checkpoints(
            stage=None, idx_close=None, sma60_series=None,
            sma60_slope_sign=None, ema20_slope_sign=None, rs_above_ma20=None,
            breadth_divergence=False, hit_count=2,
        )
        assert out["conditions"] == []
        assert out["next_watch"] is None
        assert out["next_watch_kind"] is None
        assert out["dist_to_sma60_pct"] is None


# ════════════════════════════════════════════════════════════════════════════
# 3c) 资金流聚合 + 阶段交叉验证（单据规模代理，sign-only 不设阈值）
# ════════════════════════════════════════════════════════════════════════════
def _flow_pt(main, small, medium, large=0.0, super_large=0.0):
    return {
        "main_yi": main, "small_yi": small, "medium_yi": medium,
        "large_yi": large, "super_large_yi": super_large,
    }


class TestAggregateFlows:
    def test_accumulation_structure(self):
        # 20 日：主力净流入 + 散户净流出 → 吸筹形态
        pts = [_flow_pt(main=1.0, small=-0.4, medium=-0.3) for _ in range(20)]
        out = st.aggregate_flows(pts)
        assert out["flow_20d_main_yi"] == 20.0
        assert out["flow_20d_retail_yi"] == -14.0
        assert out["flow_20d_struct"] == "main_in_retail_out"
        assert "吸筹" in out["flow_note_cn"]

    def test_distribution_structure(self):
        pts = [_flow_pt(main=-1.0, small=0.4, medium=0.3) for _ in range(20)]
        out = st.aggregate_flows(pts)
        assert out["flow_20d_struct"] == "main_out_retail_in"
        assert "派发" in out["flow_note_cn"]

    def test_windows_and_insufficient(self):
        # 60 点：三个窗口都有值；前 5 天单独构造验证 5 日窗口只看尾部
        pts = [_flow_pt(main=1.0, small=1.0, medium=0.0) for _ in range(60)]
        out = st.aggregate_flows(pts)
        assert out["flow_5d_main_yi"] == 5.0
        assert out["flow_20d_main_yi"] == 20.0
        assert out["flow_60d_main_yi"] == 60.0
        assert out["flow_20d_struct"] == "both_in"  # 主力与散户同向流入
        # 不足 20 日 → 20/60 窗口 null（不冒充）
        short = st.aggregate_flows(pts[:10])
        assert short["flow_5d_main_yi"] == 5.0
        assert short["flow_20d_main_yi"] is None
        assert short["flow_60d_main_yi"] is None
        assert st.aggregate_flows(None)["flow_5d_main_yi"] is None
        assert st.aggregate_flows([])["flow_note_cn"] is None

    def test_retail_combines_medium_and_small(self):
        pts = [_flow_pt(main=0.0, small=0.6, medium=0.4) for _ in range(20)]
        out = st.aggregate_flows(pts)
        assert out["flow_20d_retail_yi"] == 20.0  # (0.6+0.4)*20


class TestFlowVsStage:
    def test_markup_and_accumulation_confirm_on_inflow(self):
        assert st.flow_vs_stage("markup", 5.0) == "confirm"
        assert st.flow_vs_stage("accumulation", 5.0) == "confirm"
        assert st.flow_vs_stage("markup", -5.0) == "conflict"

    def test_distribution_and_decline_confirm_on_outflow(self):
        assert st.flow_vs_stage("distribution", -5.0) == "confirm"
        assert st.flow_vs_stage("decline", -5.0) == "confirm"
        assert st.flow_vs_stage("distribution", 5.0) == "conflict"
        assert st.flow_vs_stage("decline", 5.0) == "conflict"

    def test_none_cases(self):
        assert st.flow_vs_stage(None, 5.0) is None
        assert st.flow_vs_stage("markup", None) is None
        assert st.flow_vs_stage("markup", 0.0) is None


class TestFetchSectorFlows:
    def test_network_isolated_backfill_and_increment(
        self, monkeypatch, tmp_path
    ):
        """隔离网络 + 缓存目录：首次走回填、二次走 clist 快照增量、失败保留缓存。"""
        monkeypatch.setattr(st, "ROOT", tmp_path)  # ROOT 是模块级常量，须直接 patch
        from lei_signal.fundamentals import sources

        # _get_json：直连探测成功；clist 请求返回 klines 结构（无 diff → 快照为空）
        monkeypatch.setattr(
            sources, "_get_json",
            lambda *a, **k: {"data": {"klines": ["2026-08-21,1.0,2.0,3.0,4.0,5.0"]}},
        )
        wanted: dict[str, int] = {}

        def fake(code, *, days=60, prefer_direct=True):
            wanted[code] = days
            if code == "B":
                raise sources.FundamentalsSourceError("boom")
            return [
                {
                    "date": (pd.Timestamp("2026-06-01") + pd.Timedelta(days=i)).strftime("%Y-%m-%d"),
                    **_flow_pt(main=1.0, small=-0.5, medium=0.0),
                }
                for i in range(days)
            ]

        monkeypatch.setattr(sources, "fetch_industry_flow", fake)
        out = st.fetch_sector_flows(["A", "B"], days=60, jitter=0)
        assert len(out["A"]) == 60  # 本地无缓存 → push2his 全量回填
        assert wanted["A"] == 60
        assert out["B"] == []  # 单板块失败不阻断
        assert len(st.load_flow_history()["A"]) == 60

        # 第二次运行：缓存已满 → 不回填；走 clist 快照增量（_get_json 返回 diff）
        clist_payload = {
            "data": {
                "total": 1,
                "diff": [
                    {"f12": "A", "f14": "甲", "f62": 8.5e8, "f66": 5e8,
                     "f72": 3.5e8, "f78": -2e8, "f84": -6.5e8},
                ],
            }
        }
        monkeypatch.setattr(sources, "_get_json", lambda *a, **k: clist_payload)

        def fake_date_probe(code, *, days=1, prefer_direct=True):
            return [{"date": "2026-08-21", **_flow_pt(main=9.9, small=-9.9, medium=0.0)}]

        monkeypatch.setattr(sources, "fetch_industry_flow", fake_date_probe)
        out2 = st.fetch_sector_flows(["A", "B"], days=60, jitter=0)
        assert len(out2["A"]) == 61  # 60 历史 + 1 快照日，未重复回填
        assert out2["A"][-1]["date"] == "2026-08-21"
        assert out2["A"][-1]["main_yi"] == 8.5  # clist f62 → 亿
        assert out2["A"][-1]["super_large_yi"] == 5.0
        assert out2["A"][-1]["small_yi"] == -6.5

    def test_merge_flow_points(self):
        cached = [{"date": "2026-08-01", "main_yi": 1.0},
                  {"date": "2026-08-02", "main_yi": 2.0}]
        new = [{"date": "2026-08-02", "main_yi": 9.9},  # 同日覆盖
               {"date": "2026-08-03", "main_yi": 3.0}]
        merged = st._merge_flow_points(cached, new)
        assert [p["date"] for p in merged] == ["2026-08-01", "2026-08-02", "2026-08-03"]
        assert merged[1]["main_yi"] == 9.9
        big = [{"date": f"2026-01-{i:02d}", "main_yi": 1.0} for i in range(1, 10)]
        assert len(st._merge_flow_points(big, [], keep_days=5)) == 5


class TestBackfillHistory:
    def test_backfill_preserves_recorded_and_fills_missing(self, monkeypatch, tmp_path):
        """已有逐日实录同日不覆盖；缺失日期由序列补齐；NaN → None。"""
        import json as _json

        monkeypatch.setattr(st, "ROOT", tmp_path)
        # 预置一条 08-20 实录（point-in-time 真值）
        hist_path = tmp_path / "sector_trend_history.json"
        hist_path.write_text(
            _json.dumps([{"date": "2026-08-20",
                          "boards": {"X": {"close": 111.11, "b50": 50.0}}}]),
            encoding="utf-8",
        )
        dates = pd.date_range("2026-08-18", periods=3, freq="B")  # 18/19/20
        series = {
            "X": {
                "close": pd.Series([10.0, 11.0, 12.0], index=dates),
                "b50": pd.Series([np.nan, 40.0, 60.0], index=dates),
                "rs_pctile": pd.Series([80.0, 85.0, 90.0], index=dates),
                "rs_pctile_delta_20": None,
            }
        }
        stats = st.backfill_history(series)
        assert stats["added"] == 2  # 08-20 已有实录，只补 08-18/08-19
        by_date = {
            r["date"]: r["boards"].get("X", {})
            for r in _json.loads(hist_path.read_text(encoding="utf-8"))
        }
        assert by_date["2026-08-20"]["close"] == 111.11  # 实录未被覆盖
        assert by_date["2026-08-19"]["close"] == 11.0
        assert by_date["2026-08-19"]["b50"] == 40.0
        assert by_date["2026-08-18"]["b50"] is None  # NaN → None 不冒充
        assert by_date["2026-08-18"]["stage"] is None


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
