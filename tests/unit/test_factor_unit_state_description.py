"""factor_unit.state_description 合成描述测试（B0集中修复版）。

手算期望+合同消费边界；主控30日例在 test_factor_unit_b0_controller_cases.py。
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from lei_signal.research.factor_unit.state_description import describe_states

TZ = "+08:00"


def make_schedule(n: int, start="2020-01-01"):
    days = pd.date_range(start, periods=n, freq="D")
    return pd.DataFrame({
        "session": days,
        "close_at": days.tz_localize("Asia/Shanghai").strftime(f"%Y-%m-%dT%H:%M:%S{TZ}"),
    })


def contract(window=("2020-01-01", "2021-02-05")):
    return {
        "data_mode": "synthetic",
        "object_ref": "candidate:lei.dual_ma.bull_state@draft-1",
        "lookback": 20, "e_offset": 1, "x_offset": 22,
        "evaluation_window": {"start": window[0], "end": window[1]},
        "research_cutoff": "2030-01-01T15:00:00+08:00",
        "sparse_step": 23,
    }


def build_fixture():
    sched = pd.concat([
        make_schedule(42), make_schedule(5, start="2021-01-01"),
    ], ignore_index=True)
    sessions = pd.to_datetime(sched["session"])

    def I_vector(spec: dict, base=100.0):
        v = np.full(len(sessions), float(base))
        for idx, val in spec.items():
            v[idx] = val
        return v

    # A：true@2,5,8,30(尾部)；false@12,15；unknown@20及2021
    # x = 观察日+22格：t=2→24, t=5→27, t=8→30, t=12→34, t=15→37, t=20→42
    a_I = I_vector({24: 101.0, 6: 110.0, 27: 121.0, 9: 105.0, 30: 115.5,
                    20: 115.0, 34: 99.0, 33: 97.0, 37: 102.0, 41: 103.0})
    states_a = [None] * len(sessions)
    for i in (2, 5, 8, 30):
        states_a[i] = True
    for i in (12, 15):
        states_a[i] = False
    a_rows = pd.DataFrame({"symbol": "A", "session": sessions, "state": states_a, "I": a_I})

    # B：全false；C：全unknown；D：false@0..9且I(10)=NaN；E：单true@2全上涨
    b_rows = pd.DataFrame({"symbol": "B", "session": sessions,
                           "state": [False] * len(sessions),
                           "I": np.full(len(sessions), 100.0)})
    c_rows = pd.DataFrame({"symbol": "C", "session": sessions,
                           "state": [None] * len(sessions),
                           "I": np.full(len(sessions), 100.0)})
    d_I = np.full(len(sessions), 100.0)
    d_I[10] = np.nan
    d_rows = pd.DataFrame({"symbol": "D", "session": sessions,
                           "state": [False if i <= 9 else None
                                     for i in range(len(sessions))], "I": d_I})
    e_I = np.full(len(sessions), 100.0)
    e_I[24] = 101.0
    e_rows = pd.DataFrame({"symbol": "E", "session": sessions,
                           "state": [True if i == 2 else None
                                     for i in range(len(sessions))], "I": e_I})
    anchors = {sym: "2020-01-03" for sym in ("A", "B", "C", "D", "E")}
    return sched, pd.concat([a_rows, b_rows, c_rows, d_rows, e_rows],
                            ignore_index=True), anchors


def full_contract(anchors):
    c = contract()
    c["sparse_anchor_session"] = anchors
    return c


def test_hand_computed_groups_and_targets():
    sched, values, anchors = build_fixture()
    out = describe_states(values, sched, full_contract(anchors))
    a = out["symbols"]["A"]
    assert a["state_true"] == 4 and a["state_false"] == 2 and a["state_unknown"] == 41
    tg = a["true_group"]
    assert tg["n"] == 3
    assert abs(tg["mean"] - 0.07) < 1e-12
    assert abs(tg["median"] - 0.10) < 1e-12
    assert tg["up_ratio"] == 1.0
    assert abs(tg["aux_worst"] - (-0.09090909090909094)) < 1e-12
    assert abs(tg["aux_mean"] - (-(0.09090909090909094 + 0.04761904761904767) / 3)) < 1e-12
    assert tg["aux_n"] == 3
    fg = a["false_group"]
    assert fg["n"] == 2
    assert abs(fg["mean"] - 0.005) < 1e-12
    assert abs(fg["median"] - 0.005) < 1e-12
    assert fg["up_ratio"] == 0.5
    assert abs(fg["aux_mean"] - (-0.03)) < 1e-12
    assert fg["aux_n"] == 2
    comp = a["comparison"]
    assert comp["n"] == 5
    assert a["true_group"]["n"] + a["false_group"]["n"] == comp["n"]
    bg = a["background"]
    assert bg["n"] == 25 and bg["n_unknown_state"] == 20
    assert bg["stat"]["n"] == 25
    assert a["tail_immature"] == 22  # t=25..46 超出47格
    d = out["symbols"]["D"]
    assert (d["target_missing"].get("path_missing") == 9
            and d["target_missing"].get("e_missing") == 1)
    assert d["false_group"]["n"] == 9 and d["false_group"]["mean"] == 0.0
    assert d["false_group"]["aux_n"] == 0 and d["false_group"]["aux_mean"] is None
    e_sym = out["symbols"]["E"]
    assert e_sym["true_group"]["n"] == 1
    assert e_sym["true_group"]["aux_mean"] == 0.0


def test_year_and_segments_and_sparse():
    sched, values, anchors = build_fixture()
    out = describe_states(values, sched, full_contract(anchors))
    a = out["symbols"]["A"]
    assert a["by_year"]["2021"]["true"]["n"] == 0 and a["by_year"]["2021"]["true"]["mean"] is None
    assert a["by_year"]["2020"]["true"]["n"] == 3
    seg = a["state_segments"]
    assert seg["true_segments"] == 4 and seg["false_segments"] == 2 and seg["longest_true"] == 1
    sv = a["sparse_view"]
    assert sv["anchor_session"] == "2020-01-03"  # 来自合同，不动态改选
    assert [s["session"] for s in sv["slots"]] == ["2020-01-03", "2020-01-26"]
    assert sv["slots"][0]["skipped"] is False
    assert abs(sv["slots"][0]["main"] - 0.01) < 1e-12
    assert sv["slots"][1]["skipped"] is True  # 未知状态格跳过
    assert sv["true_slots_up"] == 1
    assert out["overlapping_windows"] is True


def test_missing_whole_day_breaks_segment():
    sched, values, anchors = build_fixture()
    a_vals = values[values["symbol"] == "A"]
    v2 = a_vals[a_vals["session"] != pd.Timestamp("2020-01-10")]
    out = describe_states(v2, sched, full_contract({"A": "2020-01-03"}))
    seg = out["symbols"]["A"]["state_segments"]
    # true@5..9 与 true@11..17 之间缺整行(01-10) → 断开
    assert seg["true_segments"] >= 3


def test_all_false_all_unknown_empty_groups_no_crash():
    sched, values, anchors = build_fixture()
    out = describe_states(values, sched, full_contract(anchors))
    b = out["symbols"]["B"]
    assert b["true_group"]["n"] == 0 and b["true_group"]["mean"] is None
    assert b["false_group"]["n"] == 25 and b["false_group"]["mean"] == 0.0
    c = out["symbols"]["C"]
    assert c["state_unknown"] == 47
    assert c["comparison"]["n"] == 0
    assert c["true_group"]["n"] == 0 and c["false_group"]["n"] == 0
    assert c["background"]["n"] == 25 and c["background"]["n_unknown_state"] == 25
    json.dumps(out, allow_nan=False)


def test_target_by_calendar_position_not_row_position():
    sched, _, _ = build_fixture()
    sessions = pd.to_datetime(sched["session"])
    g_I = np.full(len(sessions), 100.0)
    g_I[27] = 110.0
    g_I[28] = 121.0
    g_states = [True if i in (5, 6) else None for i in range(len(sessions))]
    g_full = pd.DataFrame({"symbol": "G", "session": sessions, "state": g_states, "I": g_I})
    out_full = describe_states(g_full, sched, full_contract({"G": "2020-01-03"}))
    g = out_full["symbols"]["G"]
    assert g["true_group"]["n"] == 2
    assert abs(g["true_group"]["median"] - 0.155) < 1e-12
    # 删除窗口中间行(index 10)后：t=5 主目标仍按时刻表第6/27格定位=0.10
    v2 = g_full[g_full["session"] != sessions.iloc[10]].copy()
    out2 = describe_states(v2, sched, full_contract({"G": "2020-01-03"}))
    g2 = out2["symbols"]["G"]
    assert g2["true_group"]["n"] == 2
    assert abs(g2["true_group"]["mean"] - (0.10 + 0.21) / 2) < 1e-12


def test_contract_and_input_validation():
    sched, values, anchors = build_fixture()
    base = full_contract(anchors)
    with pytest.raises(ValueError, match="synthetic"):
        describe_states(values, sched, {**base, "data_mode": "real"})
    with pytest.raises(ValueError, match="lookback"):
        describe_states(values, sched, {**base, "lookback": 25})
    with pytest.raises(ValueError, match="object_ref"):
        describe_states(values, sched, {**base, "object_ref": "other@1.0.0"})
    with pytest.raises(ValueError, match="缺字段"):
        describe_states(values.drop(columns=["I"]), sched, base)
    bad_sched = sched.copy()
    bad_sched["close_at"] = bad_sched["close_at"].str.replace("+08:00", "", regex=False)
    with pytest.raises(ValueError, match="时区"):
        describe_states(values, bad_sched, base)
    dup = pd.concat([sched, sched.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="唯一递增"):
        describe_states(values, dup, base)
    # 必填字段不允许默认掩盖
    for key in ("research_cutoff", "evaluation_window", "sparse_anchor_session",
                "sparse_step"):
        c2 = {k: v for k, v in base.items() if k != key}
        with pytest.raises(ValueError):
            describe_states(values, sched, c2)
    # 步长固定23：0/负/1拒绝
    for step in (0, -1, 1, 24):
        with pytest.raises(ValueError, match="sparse_step"):
            describe_states(values, sched, {**base, "sparse_step": step})
    # 空输入结构化返回
    empty = pd.DataFrame({"symbol": [], "session": [], "state": [], "I": []})
    out = describe_states(empty, sched, base)
    assert out["symbols"] == {}
    # 全部日期在窗外 → 结构化零计数，不KeyError
    v5 = values.copy()
    v5["session"] = v5["session"] + pd.DateOffset(years=5)
    out5 = describe_states(v5, sched, base)
    assert out5["symbols"]["A"]["observations_outside_window"] == 47
    assert out5["symbols"]["A"]["comparison"]["n"] == 0
