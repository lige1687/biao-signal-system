"""description_core 提取验收：手算算术期望 + 旧入口行为深度相等。

两类证据分开：
- 算术正确性：独立手算期望（50日夹具 comparison=28、稀疏格、main 数值、
  2019截止全跳过），不从旧输出反推；
- 行为一致性：提取后 describe_states 与 Task0 保存的旧输出基线逐字段深度
  相等（计数/原因/日期/布尔/null 严格相等，浮点容差 1e-12），旧 real 拒绝保持。
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lei_signal.research.factor_unit.description_core import (
    build_observation_rows,
    summarize_observation_rows,
)
from lei_signal.research.factor_unit.state_description import describe_states

BASELINE = Path(
    "docs/experiments/raw/b1-dual-ma-first-real-description-2026-09-16/"
    "baseline/old-behavior-baseline.json")


def sched(n, start="2020-01-01", tz="Asia/Shanghai"):
    days = pd.date_range(start, periods=n, freq="D")
    return pd.DataFrame({"session": days,
                         "close_at": days.tz_localize(tz) + pd.Timedelta(hours=15)})


def run_core(values, schedule, window, anchors, cutoff="2030-01-01T15:00:00+08:00"):
    built = build_observation_rows(
        values, schedule, eval_start=pd.Timestamp(window[0]),
        eval_end=pd.Timestamp(window[1]), cutoff=pd.Timestamp(cutoff),
        e_offset=1, x_offset=22)
    return summarize_observation_rows(
        built, values, schedule, eval_start=pd.Timestamp(window[0]),
        eval_end=pd.Timestamp(window[1]), anchors=anchors, sparse_step=23)


def test_core_hand_computed_50d_all_true():
    """50个合成日，I=100..149、state全真、完整评价、2030截止。"""
    s50 = sched(50)
    sess = pd.to_datetime(s50["session"])
    values = pd.DataFrame({"symbol": "SYN", "session": sess,
                           "state": [True] * 50,
                           "I": [float(100 + i) for i in range(50)]})
    out = run_core(values, s50, ("2020-01-01", "2020-02-19"), {"SYN": "2020-01-01"})
    row = out["SYN"]
    assert row["comparison"]["n"] == 28
    assert row["true_group"]["n"] == 28 and row["false_group"]["n"] == 0
    sv = row["sparse_view"]
    valid = [i for i, s in enumerate(sv["slots"]) if not s["skipped"]]
    assert valid == [0, 1]  # 第0/23日
    assert [sv["slots"][i]["session"] for i in valid] == ["2020-01-01", "2020-01-24"]
    assert abs(sv["slots"][0]["main"] - (122 / 101 - 1)) <= 1e-12
    assert abs(sv["slots"][1]["main"] - (145 / 124 - 1)) <= 1e-12
    assert sv["slots"][2]["skipped"] is True
    assert sv["slots"][2]["skipped_reason"] == "tail_immature"


def test_core_2019_cutoff_nothing_displayed():
    """同一资料2019截止：comparison_n==0，所有稀疏目标不得展示。"""
    s50 = sched(50)
    sess = pd.to_datetime(s50["session"])
    values = pd.DataFrame({"symbol": "SYN", "session": sess,
                           "state": [True] * 50,
                           "I": [float(100 + i) for i in range(50)]})
    out = run_core(values, s50, ("2020-01-01", "2020-02-19"),
                   {"SYN": "2020-01-01"}, cutoff="2019-01-01T15:00:00+08:00")
    row = out["SYN"]
    assert row["comparison"]["n"] == 0
    assert row["sparse_view"]["true_slots_up"] == 0
    assert all(s["skipped"] and s["main"] is None and s["aux"] is None
               for s in row["sparse_view"]["slots"])


def test_core_no_license_concept():
    """core 不做合同/身份校验：缺 anchors 键等由调用方责任（此处只锁核心语义）。"""
    s50 = sched(50)
    sess = pd.to_datetime(s50["session"])
    values = pd.DataFrame({"symbol": "SYN", "session": sess,
                           "state": ["false"] * 50, "I": [100.0] * 50})
    with pytest.raises(ValueError, match="state"):
        build_observation_rows(values, s50, eval_start=pd.Timestamp("2020-01-01"),
                               eval_end=pd.Timestamp("2020-02-19"),
                               cutoff=pd.Timestamp("2030-01-01T15:00:00+08:00"),
                               e_offset=1, x_offset=22)


# ── 旧入口行为深度相等（与Task0基线对照） ─────────────────────────────

def _values(symbol, sessions, states, levels):
    return pd.DataFrame({"symbol": symbol, "session": sessions,
                         "state": states, "I": levels})


def _contract(window, anchors, cutoff="2030-01-01T15:00:00+08:00"):
    return {"data_mode": "synthetic",
            "object_ref": "candidate:lei.dual_ma.bull_state@draft-1",
            "lookback": 20, "e_offset": 1, "x_offset": 22,
            "evaluation_window": {"start": window[0], "end": window[1]},
            "research_cutoff": cutoff,
            "sparse_anchor_session": anchors, "sparse_step": 23}


def _deep_equal(a, b, path="root"):
    if isinstance(a, (int, float)) and not isinstance(a, bool) \
            and isinstance(b, (int, float)) and not isinstance(b, bool):
        assert a == b or abs(a - b) <= 1e-12, f"{path}: {a!r} vs {b!r}"
    elif isinstance(a, dict) and isinstance(b, dict):
        assert set(a) == set(b), f"{path}: 键集合差异 {set(a) ^ set(b)}"
        for k in a:
            _deep_equal(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list) and isinstance(b, list):
        assert len(a) == len(b), f"{path}: 长度 {len(a)} vs {len(b)}"
        for i, (x, y) in enumerate(zip(a, b, strict=True)):
            _deep_equal(x, y, f"{path}[{i}]")
    else:
        assert type(a) is type(b) and a == b, f"{path}: {a!r} vs {b!r}"


def _recompute_cases():
    """与 capture_old_behavior.py 同一批夹具（构造逐行对应）。"""
    cases = {}
    s50 = sched(50)
    sess = pd.to_datetime(s50["session"])
    cases["flat_50d"] = describe_states(
        _values("SYN", sess, [True] * 50, [100.0] * 50), s50,
        _contract(("2020-01-01", "2020-02-19"), {"SYN": "2020-01-01"}))
    s100 = sched(100)
    sess100 = pd.to_datetime(s100["session"])
    cases["up_100d_short_window"] = describe_states(
        _values("SYN", sess100, [True] * 100, [float(100 + i) for i in range(100)]),
        s100, _contract(("2020-01-01", "2020-02-09"), {"SYN": "2020-01-01"}))
    sessions30 = pd.to_datetime(sched(30)["session"])
    d_I = [100.0] * 30
    d_I[10] = np.nan
    cases["mixed_unknown_aux_missing"] = describe_states(
        _values("D", sessions30, [False] * 10 + [None] * 5 + [True] * 15, d_I),
        sched(30), _contract(("2020-01-01", "2020-01-30"), {"D": "2020-01-01"}))
    v_out = _values("SYN", sess, [True] * 50, [100.0] * 50).copy()
    v_out["session"] = v_out["session"] + pd.DateOffset(years=5)
    cases["all_outside_window"] = describe_states(
        v_out, s50, _contract(("2020-01-01", "2020-02-19"), {"SYN": "2020-01-01"}))
    empty = pd.DataFrame({"symbol": [], "session": [], "state": [], "I": []})
    cases["empty_input"] = describe_states(
        empty, s50, _contract(("2020-01-01", "2020-02-19"), {"SYN": "2020-01-01"}))
    s40 = sched(40, start="2019-12-15")
    sess40 = pd.to_datetime(s40["session"])
    cases["cross_year"] = describe_states(
        _values("SYN", sess40, [True] * 40, [float(100 + i) for i in range(40)]),
        s40, _contract(("2019-12-15", "2020-01-23"), {"SYN": "2019-12-15"}))
    return cases


def test_old_entry_deep_equal_baseline():
    baseline = json.loads(BASELINE.read_text())
    now = _recompute_cases()
    for name, out in now.items():
        assert "ok" in baseline[name], f"{name} 基线不是ok案例"
        _deep_equal(out, baseline[name]["ok"], path=name)


def test_real_mode_still_rejected_after_extraction():
    baseline = json.loads(BASELINE.read_text())
    assert baseline["real_mode_rejected"]["error"].startswith("ValueError")
    s50 = sched(50)
    sess = pd.to_datetime(s50["session"])
    c = _contract(("2020-01-01", "2020-02-19"), {"SYN": "2020-01-01"})
    c["data_mode"] = "real"
    with pytest.raises(ValueError, match="synthetic"):
        describe_states(_values("SYN", sess, [True] * 50, [100.0] * 50), s50, c)
