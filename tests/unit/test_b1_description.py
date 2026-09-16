"""b1_description 合成算术、边界与兼容验收（Task4 清单）。

独立期望全部手算硬写，不 import 生产函数生成期望，不调用真实数据。
close 常数/递增两组 50 日夹具的预期来自固定构造：前 20 行准备期未知；
常数 close 后 30 行状态假；递增 close 后 30 行状态真；x=t+22<50 →
完整配对 t=20..27 共 8 个。
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lei_signal.research.factor_unit.b1_description import describe_b1
from lei_signal.research.factor_unit.description_core import build_observation_rows

TZ = "+08:00"


def make_schedule(n: int, start="2020-01-01"):
    days = pd.date_range(start, periods=n, freq="D")
    return pd.DataFrame({
        "session": days,
        "close_at": days.tz_localize("Asia/Shanghai").strftime(
            f"%Y-%m-%dT15:00:00{TZ}"),
    })


def make_prices(closes, start="2020-01-01"):
    idx = pd.date_range(start, periods=len(closes), freq="D")
    return pd.DataFrame({"close": [float(c) for c in closes]}, index=idx)


def make_contract(window=("2020-01-01", "2020-02-19"),
                  cutoff="2030-01-01T15:00:00+08:00", anchor="2020-01-01"):
    return {
        "family": "B1-dual-ma-unit",
        "use": "post_hoc_historical_description",
        "object_ref": "candidate:lei.dual_ma.bull_state@draft-1",
        "symbol": "510300",
        "evaluation_window": {"start": window[0], "end": window[1]},
        "e_offset": 1, "x_offset": 22,
        "label_maturity_cutoff": cutoff,
        "warmup_sessions": 20,
        "sparse_anchor_session": anchor, "sparse_step": 23,
        "target_basis": "vendor_adjusted_price_change",
        "target_main": "P_vendor(t+22)/P_vendor(t+1) - 1",
        "target_aux": "min(0, min(P_vendor(s)/P_vendor(t+1) - 1))",
        "data_mode": "real",
        "historical_reconstruction_only": True,
        "adjustment_anchor": "unknown",
    }


def test_constant_close_false_group_hand_computed():
    """50日常数close=100：前20未知、后30假；完整配对中假组8个，目标/辅助均0；
    真组n=0统计null；零目标不算上涨/下跌，仍计分母。"""
    result = describe_b1(make_prices([100.0] * 50), make_schedule(50), make_contract())
    states = result["states"]
    assert states["state"].tolist() == [""] * 20 + ["false"] * 30
    sym = result["summary"]["symbols"]["510300"]
    tg, fg = sym["true_group"], sym["false_group"]
    assert tg["n"] == 0 and tg["mean"] is None and tg["up_ratio"] is None
    assert fg["n"] == 8
    assert fg["mean"] == 0.0 and fg["median"] == 0.0
    assert fg["up_ratio"] == 0.0  # 零目标不算上涨，仍计分母
    assert fg["aux_n"] == 8 and fg["aux_mean"] == 0.0 and fg["aux_worst"] == 0.0
    rec = result["quality"]["reconciliation"]
    assert rec["comparison_n"] == 8 and rec["comparison_false"] == 8
    assert rec["comparison_true"] == 0
    assert rec["states_sum_equals_window"] is True
    assert rec["true_plus_false_equals_comparison"] is True
    assert rec["exclusion_plus_comparison_equals_window"] is True
    # 稀疏组三态合计=组n
    g = sym["sparse_view"]["groups"]
    assert g["false"]["n"] == g["false"]["up"] + g["false"]["down"] + g["false"]["zero"]
    assert g["false"]["zero"] == g["false"]["n"]


def test_rising_close_true_group_hand_computed():
    """50日close前20为100、后为101..130：未知20、后30真、成熟真组8；
    第一完整观察e=102/x=123，main=123/102-1；aux=0。"""
    closes = [100.0] * 20 + list(range(101, 131))
    result = describe_b1(make_prices(closes), make_schedule(50), make_contract())
    states = result["states"]
    assert states["state"].tolist() == [""] * 20 + ["true"] * 30
    obs = result["observations"]
    first = obs.iloc[20]
    assert first["state"] == "true" and bool(first["in_comparison"]) is True
    assert first["e_date"] == "2020-01-22"  # 第21行(index20)的e=index21收盘102
    assert first["x_date"] == "2020-02-12"  # x=index42收盘123
    assert abs(first["main"] - (123.0 / 102.0 - 1.0)) <= 1e-12
    assert first["aux"] == 0.0
    sym = result["summary"]["symbols"]["510300"]
    assert sym["true_group"]["n"] == 8 and sym["false_group"]["n"] == 0
    assert abs(sym["true_group"]["mean"] - np.mean(
        [closes[t + 22] / closes[t + 1] - 1.0 for t in range(20, 28)])) <= 1e-12
    assert sym["true_group"]["up_ratio"] == 1.0
    assert sym["true_group"]["aux_n"] == 8 and sym["true_group"]["aux_worst"] == 0.0


def test_scale_invariance_times_10():
    """合成价格同比缩放×10不改状态和无量纲目标。"""
    closes = [100.0] * 20 + list(range(101, 131))
    base = describe_b1(make_prices(closes), make_schedule(50), make_contract())
    scaled = describe_b1(make_prices([c * 10 for c in closes]),
                         make_schedule(50), make_contract())
    assert base["states"]["state"].tolist() == scaled["states"]["state"].tolist()
    for a, b in zip(base["observations"]["main"].tolist(),
                    scaled["observations"]["main"].tolist(), strict=True):
        if pd.isna(a):
            assert pd.isna(b)
        else:
            assert abs(a - b) <= 1e-12


def test_appending_future_keeps_existing_results():
    """追加未来合法合成资料后，既有状态及已经完整的目标不变。"""
    closes50 = [100.0] * 20 + list(range(101, 131))
    closes70 = closes50 + [130.0 + i for i in range(1, 21)]
    r50 = describe_b1(make_prices(closes50), make_schedule(50), make_contract())
    r70 = describe_b1(make_prices(closes70), make_schedule(70), make_contract())
    assert r50["states"]["state"].tolist() == \
        r70["states"]["state"].tolist()[:50]
    # 已完整（成熟）的目标不变；未成熟目标后来变完整不算泄漏——只比对50日已成熟行
    o50 = r50["observations"]
    o70 = r70["observations"].iloc[:50]
    mature50 = o50[o50["mature"]][["session", "state", "main", "aux",
                                   "mature", "reason"]]
    same70 = o70.iloc[mature50.index][["session", "state", "main", "aux",
                                       "mature", "reason"]]
    pd.testing.assert_frame_equal(mature50.reset_index(drop=True),
                                  same70.reset_index(drop=True), check_exact=False,
                                  atol=1e-12)
    assert int(mature50["main"].notna().sum()) == 28  # 50日时的完整配对数


def test_missing_aux_path_keeps_main():
    """缺辅助路径但e/x齐全：main计数保留、aux缺失（统计层行为，core级验收）。"""
    s50 = make_schedule(50)
    sessions = pd.to_datetime(s50["session"])
    levels = [100.0 + i for i in range(50)]
    values = pd.DataFrame({"symbol": "510300", "session": sessions,
                           "state": [True] * 50, "I": levels})
    values = values[values["session"] != sessions[10]].copy()  # 删中间一日（路径缺）
    built = build_observation_rows(values, s50,
                                   eval_start=pd.Timestamp("2020-01-01"),
                                   eval_end=pd.Timestamp("2020-02-19"),
                                   cutoff=pd.Timestamp("2030-01-01T15:00:00+08:00"),
                                   e_offset=1, x_offset=22)
    rows = built["rows"]
    hit = [r for r in rows if r["reason"] == "path_missing"]
    assert len(hit) == 9  # t=0..8 的路径覆盖缺行；t=9 的 e 恰是缺行（e_missing）
    for r in hit:
        assert r["main"] is not None  # e/x齐全→主目标保留
        assert r["aux"] is None       # 路径缺→aux缺失
    mains = [r for r in rows if r["main"] is not None and r["mature"]
             and r["state"] is not None]
    # 完整资料为28；删行使 t=10 观察本身消失且 t=9 的 e 缺失 → 26
    assert len(mains) == 26


def test_cross_year_grouped_by_observation_year():
    """跨年按状态观察年分组（t.year），跨年目标归观察年。"""
    n = 40
    sched = make_schedule(n, start="2019-12-15")
    closes = [100.0] * 20 + [100.0 + i for i in range(1, 21)]
    result = describe_b1(make_prices(closes, start="2019-12-15"), sched,
                         make_contract(window=("2019-12-15", "2020-01-23"),
                                       anchor="2019-12-15"))
    sym = result["summary"]["symbols"]["510300"]
    obs = result["observations"]
    in_comp = obs[obs["in_comparison"]]
    years = {str(pd.Timestamp(s).year) for s in in_comp["session"]}
    assert set(sym["by_year"]) >= years
    total = sum(sym["by_year"][y]["true"]["n"] + sym["by_year"][y]["false"]["n"]
                for y in sym["by_year"])
    assert total == result["quality"]["reconciliation"]["comparison_n"]


def test_outside_window_not_counted_as_missing():
    """窗外观察不计入窗内对账，也不计缺数据。"""
    closes = [100.0] * 20 + list(range(101, 131))
    result = describe_b1(make_prices(closes), make_schedule(50),
                         make_contract(window=("2020-01-15", "2020-02-19")))
    rec = result["quality"]["reconciliation"]
    assert rec["observations_in_eval_window"] == 36  # 01-15..02-19
    assert rec["outside_window_rows"] == 14
    assert rec["states_sum_equals_window"] is True


def test_cutoff_boundary_exact_1500_vs_145959():
    """截止恰好15:00成熟、14:59:59不成熟；早截止所有目标剔除；无时区拒绝。"""
    closes = [100.0] * 20 + list(range(101, 131))
    prices, sched = make_prices(closes), make_schedule(50)
    # 首个完整观察 t=20 的 x=index42=2020-02-12 15:00
    mature = describe_b1(prices, sched, make_contract(
        cutoff="2020-02-12T15:00:00+08:00"))
    assert mature["quality"]["reconciliation"]["comparison_n"] == 1
    before = describe_b1(prices, sched, make_contract(
        cutoff="2020-02-12T14:59:59+08:00"))
    assert before["quality"]["reconciliation"]["comparison_n"] == 0
    early = describe_b1(prices, sched, make_contract(
        cutoff="2019-01-01T15:00:00+08:00"))
    rec = early["quality"]["reconciliation"]
    assert rec["comparison_n"] == 0
    assert rec["exclusion_plus_comparison_equals_window"] is True
    # 互斥排除全覆盖：未知20 + 已算目标但未成熟8 + 尾部不足22 = 50
    assert rec["primary_exclusion_counts"] == {"not_mature": 8, "state_unknown": 20,
                                               "tail_immature": 22}
    naive = make_contract()
    naive["label_maturity_cutoff"] = "2030-01-01T15:00:00"
    with pytest.raises(ValueError, match="时区"):
        describe_b1(prices, sched, naive)


def test_result_identity_and_no_claims():
    result = describe_b1(make_prices([100.0] * 50), make_schedule(50), make_contract())
    q = result["quality"]
    assert q["result_identity"] == "post_hoc_historical_description"
    assert q["data_mode"] == "real"
    assert q["historical_reconstruction_only"] is True
    assert q["historical_available_at"] is None
    assert q["adjustment_anchor"] == "unknown"
    for banned in ("alpha", "IC", "significance", "total_return_wealth",
                   "point_in_time_verified"):
        assert banned in q["no_claims"]
    assert q["reconciliation"]["warmup_sessions_before_window"] == 20
