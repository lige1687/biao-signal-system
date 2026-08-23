"""收盘简报 · 构建层单元测试（纯函数，网络零依赖）。

覆盖：宽度异常检测（分位/标签）、自选状态 diff（色变/维度翻转/条件增删）、
verdict 档位排序、观察池连续天数、模板渲染禁用词、落盘幂等合并。
"""
from __future__ import annotations

from lei_signal import dailybrief as db


# ── 宽度异常 ────────────────────────────────────────────────────────────────
class TestBreadthAnomalies:
    def _a_hist(self, n: int = 300, b20=50.0, b50=50.0, b200=50.0):
        # 真实形态：历史在 30~70 区间波动，避免常数序列的退化分位
        out = []
        for i in range(n):
            wave = 50.0 + 20.0 * ((i % 20) - 10) / 10.0
            out.append({
                "date": f"2026-01-{(i % 28) + 1:02d}",
                "ma20_pct": wave if b20 == 50.0 else b20,
                "ma50_pct": wave if b50 == 50.0 else b50,
                "ma200_pct": wave if b200 == 50.0 else b200,
            })
        return out

    def test_labels_are_b20_b50_b200(self):
        # 回归：标签曾错位为 b21/b22，必须修死
        anomalies, context = db.detect_breadth_anomalies(
            self._a_hist(300, b200=10.0), []
        )
        assert {c["metric"] for c in context} == {"b20", "b50", "b200"}
        assert any(a["metric"] == "b200" and a["market"] == "A股" for a in anomalies)

    def test_us_extreme_high(self):
        us = [{"date": f"d{i}", "breadth_20": 60.0, "breadth_50": 60.0,
               "breadth_200": 60.0} for i in range(300)]
        us[-1]["breadth_50"] = 95.0
        anomalies, _ = db.detect_breadth_anomalies([], us)
        assert any(a["metric"] == "b50" and a["market"] == "美股" and "高位" in a["note_cn"]
                   for a in anomalies)

    def test_normal_range_no_anomaly(self):
        hist = self._a_hist()
        for row in hist[-2:]:  # 末日锚定中位，避免波峰被误判极端
            row["ma20_pct"] = row["ma50_pct"] = row["ma200_pct"] = 50.0
        anomalies, context = db.detect_breadth_anomalies(hist, [])
        assert anomalies == []
        assert len(context) == 3

    def test_short_history_skipped(self):
        anomalies, context = db.detect_breadth_anomalies(self._a_hist(1), [])
        assert anomalies == [] and context == []


# ── 自选 diff 与排序 ────────────────────────────────────────────────────────
class TestSymbolDiff:
    def _state(self, color="green", dims=None, sup=("lei_color",), con=()):
        color_cn = {"green": "绿", "black": "黑"}[color]
        return {
            "color": color, "color_cn": color_cn,
            "stage_cn": None, "risk_state_cn": None,
            "dimensions": dims if dims is not None else {"结构": "支持"},
            "support_rules": sorted(sup), "conflict_rules": sorted(con),
            "new_event_count": 0,
        }

    def test_no_baseline_marks_new(self):
        d = db.diff_symbol_state(None, self._state())
        assert d["is_new"] and "首次纳入" in d["changes"][0]

    def test_color_change(self):
        d = db.diff_symbol_state(self._state("green"), self._state("black"))
        assert any("色变" in ch for ch in d["changes"])

    def test_dimension_flip_and_rule_changes(self):
        prev = self._state(
            dims={"结构": "支持", "量价": "中性"}, sup=("lei_color", "macd_strength")
        )
        curr = self._state(
            dims={"结构": "冲突", "量价": "中性"}, sup=("lei_color",), con=("resistance_b1",)
        )
        d = db.diff_symbol_state(prev, curr)
        joined = " ".join(d["changes"])
        assert "维度翻转：结构" in joined
        assert "新增冲突条件：resistance_b1" in joined
        assert "支持条件消失：macd_strength" in joined

    def test_unchanged(self):
        s = self._state()
        d = db.diff_symbol_state(s, dict(s))
        assert d["n_changes"] == 0 and d["changes"] == []

    def test_rank_by_verdict_tier_then_changes(self):
        items = [
            {"symbol": "C", "verdict": "waiting", "n_changes": 3},
            {"symbol": "A", "verdict": "actionable", "n_changes": 0},
            {"symbol": "B", "verdict": "waiting", "n_changes": 5},
            {"symbol": "D", "verdict": "none", "n_changes": 9},
        ]
        order = [it["symbol"] for it in db.rank_watchlist_changes(items)]
        assert order == ["A", "B", "C", "D"]


# ── 板块观察池 ──────────────────────────────────────────────────────────────
class TestSectorPool:
    def _snap(self):
        def board(code, name, stage, unmet, delta=0.0, confirm=False):
            cps = [{"met": unmet == 0}] * 3 if unmet in (0, 3) else [
                {"met": False}, {"met": True}, {"met": True},
            ]
            return {
                "code": code, "name": name, "stage": stage, "parent": None,
                "rs_pctile": 50.0, "rs_pctile_delta_20": delta, "pe_ttm": 20.0,
                "flow_20d_main_yi": 1.0, "flow_vs_stage": "confirm" if confirm else None,
                "flow_vs_stage_cn": "资金印证" if confirm else None,
                "next_watch": "观察", "checkpoints": cps,
            }
        return {"boards": [
            board("BK1", "甲", "accumulation", unmet=1, delta=5.0),   # 临近升级+动能
            board("BK2", "乙", "markup", unmet=0, confirm=True),       # 资金印证
            board("BK3", "丙", "decline", unmet=3),                    # 不入池
        ]}

    def test_pool_membership(self):
        pool = db.today_sector_pool(self._snap())
        assert set(pool) == {"BK1", "BK2"}
        assert set(pool["BK1"]["tags"]) == {"临近升级", "动能前五"}
        assert pool["BK2"]["tags"] == ["资金印证"]
        assert db.today_sector_pool(None) == {}

    def test_streaks_count_back(self):
        today = {"BK1": {}, "BK2": {}}
        recent = [
            {"codes": ["BK1"]},        # 4 天前：只有 BK1
            {"codes": ["BK1", "BK2"]}, # 3 天前
            {"codes": ["BK9"]},        # 2 天前：断档
            {"codes": ["BK1", "BK2"]}, # 1 天前
        ]
        s = db.pool_streaks(today, recent)
        assert s["BK1"] == 2  # 今日 + 1 天前（再往前断档）
        assert s["BK2"] == 2


# ── 表达层 ──────────────────────────────────────────────────────────────────
class TestRendering:
    def test_template_has_no_banned_words(self):
        payload = {
            "date": "2026-08-23", "slot": "1445",
            "env": {"anomalies": [], "macro": {"line_cn": "VIX 15"}},
            "watchlist": {"items": [], "unchanged_count": 3, "sector_watch_count": 20},
            "pool": {"items": [], "codes": []},
        }
        text = db.render_template(payload)
        assert not db.check_banned(text)
        assert "盘中预判" in text
        assert db.RESEARCH_NOTE in text

    def test_check_banned(self):
        assert db.check_banned("建议买入")
        assert not db.check_banned("条件成立，参考")


# ── 落盘幂等 ────────────────────────────────────────────────────────────────
class TestPersistence:
    def test_save_and_merge_slots(self, tmp_path, monkeypatch):
        monkeypatch.setattr(db, "BRIEF_DIR", tmp_path)
        db.save_brief_version("2026-08-23", "1445", {"slot": "1445"})
        db.save_brief_version("2026-08-23", "1645", {"slot": "1645"})
        doc = db.load_brief("2026-08-23")
        assert set(doc["versions"]) == {"1445", "1645"}
        # 覆盖同槽位
        db.save_brief_version("2026-08-23", "1645", {"slot": "1645-v2"})
        assert db.load_brief("2026-08-23")["versions"]["1645"]["slot"] == "1645-v2"

    def test_baseline_before(self, tmp_path, monkeypatch):
        monkeypatch.setattr(db, "BRIEF_DIR", tmp_path)
        db.save_brief_version("2026-08-21", "1645", {"id": "d21-close"})
        db.save_brief_version("2026-08-22", "1445", {"id": "d22-intraday"})
        db.save_brief_version("2026-08-22", "1645", {"id": "d22-close"})
        base = db.load_baseline_before("2026-08-23", "1445")
        assert base["id"] == "d22-close"
        base2 = db.load_baseline_before("2026-08-22", "1645")
        assert base2["id"] == "d22-intraday"
