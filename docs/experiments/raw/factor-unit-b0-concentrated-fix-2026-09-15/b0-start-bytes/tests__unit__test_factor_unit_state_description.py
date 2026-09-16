"""factor_unit.state_description 合成描述测试（期望全部手算）。"""
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


def contract():
    return {
        "object_ref": "candidate:lei.dual_ma.bull_state@draft-1",
        "data_mode": "synthetic",
        "lookback": 20, "e_offset": 1, "x_offset": 22,
        "sparse_anchor_days": 23,
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

    # B：全false，I恒100
    b_rows = pd.DataFrame({"symbol": "B", "session": sessions,
                           "state": [False] * len(sessions),
                           "I": np.full(len(sessions), 100.0)})
    # C：全unknown
    c_rows = pd.DataFrame({"symbol": "C", "session": sessions,
                           "state": [None] * len(sessions),
                           "I": np.full(len(sessions), 100.0)})
    # D：false@0..9，I(10)=NaN → t=0..8路径缺失、t=9 e缺失
    d_I = np.full(len(sessions), 100.0)
    d_I[10] = np.nan
    states_d = [False if i <= 9 else None for i in range(len(sessions))]
    d_rows = pd.DataFrame({"symbol": "D", "session": sessions, "state": states_d, "I": d_I})

    # E：单true@2，全上涨路径（下行值0的专设例）
    e_I = np.full(len(sessions), 100.0)
    e_I[24] = 101.0
    states_e = [True if i == 2 else None for i in range(len(sessions))]
    e_rows = pd.DataFrame({"symbol": "E", "session": sessions, "state": states_e, "I": e_I})
    return sched, pd.concat([a_rows, b_rows, c_rows, d_rows, e_rows], ignore_index=True)


def test_hand_computed_groups_and_targets():
    sched, values = build_fixture()
    out = describe_states(values, sched, contract())
    a = out["symbols"]["A"]
    # 手算：true@2(101/100-1=0.01,全上涨aux=0),5(121/110-1=0.10),8(115.5/105-1=0.10)
    assert a["state_true"] == 4 and a["state_false"] == 2 and a["state_unknown"] == 41
    tg = a["true_group"]
    assert tg["n"] == 3
    assert abs(tg["mean"] - 0.07) < 1e-12
    assert abs(tg["median"] - 0.10) < 1e-12
    assert tg["up_ratio"] == 1.0
    # true组aux：t2=0(全上涨下行0)，t5=-0.0909(基准价回落)，t8=-0.0476
    assert abs(tg["aux_worst"] - (-0.09090909090909094)) < 1e-12
    assert abs(tg["aux_mean"] - (-(0.09090909090909094 + 0.04761904761904767) / 3)) < 1e-12
    # 专设全上涨窗口 E：aux=0
    e_sym = out["symbols"]["E"]
    assert e_sym["true_group"]["n"] == 1
    assert e_sym["true_group"]["aux_mean"] == 0.0 and e_sym["true_group"]["aux_worst"] == 0.0
    fg = a["false_group"]
    assert fg["n"] == 2
    assert abs(fg["mean"] - 0.005) < 1e-12
    assert abs(fg["median"] - 0.005) < 1e-12
    assert fg["up_ratio"] == 0.5
    assert abs(fg["aux_mean"] - (-0.03)) < 1e-12  # 两false窗口均含 I(33)=97
    assert abs(fg["aux_worst"] - (-0.03)) < 1e-12
    # 无条件参照=同一可评价日期全集（t=0..24全部25个观察，含unknown行）；
    # 期望用测试内独立循环复算（与被测模块不同实现）
    v_a = values[values["symbol"] == "A"].set_index("session")
    sess = pd.to_datetime(sched["session"])
    indep = [v_a["I"].get(sess.iloc[t + 22]) / v_a["I"].get(sess.iloc[t + 1]) - 1
             for t in range(25)]
    un = a["unconditional"]
    assert un["n"] == 25
    assert abs(un["mean"] - float(np.mean(indep))) < 1e-12
    assert abs(un["median"] - float(np.median(indep))) < 1e-12
    assert abs(un["up_ratio"] - float(np.mean([m > 0 for m in indep]))) < 1e-12
    assert a["tail_immature"] == 22  # t=25..46 超出47格时刻表
    assert (a["target_missing"].get("path_missing") is None
            and a["target_missing"].get("e_missing") is None)
    d = out["symbols"]["D"]
    assert (d["target_missing"].get("path_missing") == 9
            and d["target_missing"].get("e_missing") == 1)
    assert d["tail_immature"] == 22
    assert d["false_group"]["n"] == 9 and d["false_group"]["mean"] == 0.0
    assert d["false_group"]["aux_mean"] is None


def test_year_and_segments_and_sparse():
    sched, values = build_fixture()
    out = describe_states(values, sched, contract())
    a = out["symbols"]["A"]
    assert a["by_year"]["2021"]["true"]["n"] == 0 and a["by_year"]["2021"]["true"]["mean"] is None
    assert a["by_year"]["2020"]["true"]["n"] == 3
    seg = a["state_segments"]
    # true段：@2、@5、@8各成段 + @30（尾部）= 4段
    assert seg["true_segments"] == 4 and seg["false_segments"] == 2 and seg["longest_true"] == 1
    sv = a["sparse_view"]
    # 锚点=index2（首个已知状态观察），此后每23格无已知状态 → 只有1格
    assert len(sv["slots"]) == 1
    assert abs(sv["slots"][0]["main"] - 0.01) < 1e-12
    assert sv["true_slots_up"] == 1
    assert out["overlapping_windows"] is True


def test_all_false_all_unknown_empty_groups_no_crash():
    sched, values = build_fixture()
    out = describe_states(values, sched, contract())
    b = out["symbols"]["B"]
    assert b["true_group"]["n"] == 0 and b["true_group"]["mean"] is None
    assert b["false_group"]["n"] == 25 and b["false_group"]["mean"] == 0.0
    c = out["symbols"]["C"]
    assert c["state_unknown"] == 47
    assert c["true_group"]["n"] == 0 and c["false_group"]["n"] == 0
    assert c["unconditional"]["n"] == 25
    json.dumps(out, allow_nan=False)  # 输出可被严格JSON序列化


def test_target_by_calendar_position_not_row_position():
    # G：true@5和true@6两条观察，I(27)=110,I(28)=121
    # t=5: e=6,x=27 → 0.10；t=6: e=7,x=28 → 0.21
    sched, _ = build_fixture()
    sessions = pd.to_datetime(sched["session"])
    g_I = np.full(len(sessions), 100.0)
    g_I[27] = 110.0
    g_I[28] = 121.0
    g_states = [True if i in (5, 6) else None for i in range(len(sessions))]
    g_full = pd.DataFrame({"symbol": "G", "session": sessions, "state": g_states, "I": g_I})
    out_full = describe_states(g_full, sched, contract())
    g = out_full["symbols"]["G"]
    assert g["true_group"]["n"] == 2
    assert abs(g["true_group"]["median"] - 0.155) < 1e-12
    # 删除窗口中间行(index 10，非端点)后：t=5 主目标仍按时刻表第6/27格定位=0.10
    # （若按删行后剩余行的第22行定位，端点会错位；路径目标则如实缺失）
    v2 = g_full[g_full["session"] != sessions.iloc[10]].copy()
    out2 = describe_states(v2, sched, contract())
    g2 = out2["symbols"]["G"]
    assert g2["true_group"]["n"] == 2
    assert abs(g2["true_group"]["mean"] - (0.10 + 0.21) / 2) < 1e-12


def test_contract_and_input_validation():
    sched, values = build_fixture()
    with pytest.raises(ValueError, match="synthetic"):
        describe_states(values, sched, {**contract(), "data_mode": "real"})
    with pytest.raises(ValueError, match="lookback"):
        describe_states(values, sched, {**contract(), "lookback": 25})
    with pytest.raises(ValueError, match="object_ref"):
        describe_states(values, sched, {**contract(), "object_ref": "other@1.0.0"})
    with pytest.raises(ValueError, match="缺字段"):
        describe_states(values.drop(columns=["I"]), sched, contract())
    bad_sched = sched.copy()
    bad_sched["close_at"] = bad_sched["close_at"].str.replace("+08:00", "", regex=False)
    with pytest.raises(ValueError, match="时区"):
        describe_states(values, bad_sched, contract())
    dup = pd.concat([sched, sched.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="唯一递增"):
        describe_states(values, dup, contract())
