"""momentum_prototype.py 的独立算术/时间/缺失/价格尺度测试。

严格独立期望：手算边界、独立手算 rank 值、删除端点不顺延、未来信息隔离。
容差 atol=rtol=1e-12；日期/身份/缺失原因精确相等。
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from lei_signal.research import momentum_prototype as mp

ATOL = 1e-12
RTOL = 1e-12


def _series(values, start="2020-01-01"):
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=idx, dtype=float)


# ---------------------------------------------------------------------------
# Task 2：compute_momentum
# ---------------------------------------------------------------------------


def test_compute_momentum_boundary_first_253_and_254():
    """手算边界：I=1..254。前 252 个 NaN；第 253 个 = 232/1-1=231；第 254 个 = 233/2-1=115.5。"""
    n = 254
    values = np.arange(1, n + 1, dtype=float)
    s = _series(values)
    mom = mp.compute_momentum(s)
    # 前 252 个（位置 0..251）缺失
    assert np.isnan(mom.iloc[:252]).all()
    # 第 253 个（0-索引 252）= 232/1 - 1
    assert math.isclose(mom.iloc[252], 232 / 1 - 1, abs_tol=ATOL, rel_tol=RTOL)
    # 第 254 个（0-索引 253）= 233/2 - 1
    assert math.isclose(mom.iloc[253], 233 / 2 - 1, abs_tol=ATOL, rel_tol=RTOL)


def test_compute_momentum_matches_quote_features():
    rng = np.random.default_rng(20260913)
    values = rng.uniform(1, 200, size=400)
    s = _series(values)
    mom = mp.compute_momentum(s)
    from lei_signal.research.definitions import quote_features

    ref = quote_features(s)["momentum"]
    assert np.allclose(
        mom.to_numpy(), ref.to_numpy(), atol=ATOL, rtol=RTOL, equal_nan=True
    )


def test_compute_momentum_rejects_non_unique_dates():
    idx = pd.to_datetime(["2020-01-01", "2020-01-01"])
    s = pd.Series([1.0, 2.0], index=idx)
    with pytest.raises(ValueError, match="unique increasing"):
        mp.compute_momentum(s)


def test_compute_momentum_rejects_non_monotonic():
    idx = pd.to_datetime(["2020-01-02", "2020-01-01"])
    s = pd.Series([1.0, 2.0], index=idx)
    with pytest.raises(ValueError, match="unique increasing"):
        mp.compute_momentum(s)


def test_compute_momentum_rejects_nonpositive():
    s = _series([1.0, 2.0, -1.0, 4.0])
    with pytest.raises(ValueError, match="finite positive"):
        mp.compute_momentum(s)


def test_compute_momentum_allows_nan_quotes():
    rng = np.random.default_rng(7)
    values = rng.uniform(1, 200, size=300)
    values[100] = np.nan  # 缺报价：按原定义剔除出有效报价序列，不当作零或前填
    s = _series(values)
    mom = mp.compute_momentum(s)  # 不应抛错；NaN 报价按原定义缺失处理
    # 输出补齐回原索引；缺报价行自身为 NaN，位移只在有效报价位置上计算
    assert len(mom) == 300
    assert np.isnan(mom.iloc[100])
    assert mom.drop(mom.index[100]).notna().any()


def test_compute_momentum_price_scale_invariant():
    """等比例缩放全部价格（不含现金分红）：所有动量值不变。"""
    rng = np.random.default_rng(1)
    values = rng.uniform(1, 200, size=400)
    base = mp.compute_momentum(_series(values))
    scaled = mp.compute_momentum(_series(values * 5.0))
    # 末位缺失由两端缩放保持，数值完全一致
    assert np.allclose(
        base.dropna().to_numpy(), scaled.dropna().to_numpy(), atol=ATOL, rtol=RTOL
    )


# ---------------------------------------------------------------------------
# Task 3：build_targets
# ---------------------------------------------------------------------------


def _sessions(n, start="2022-01-03"):
    return pd.date_range(start, periods=n, freq="B")  # 仅工作日，唯一有序


def test_build_targets_synthetic_position_300_to_322():
    sessions = _sessions(400)
    values = np.ones(400)
    values[301] = 100.0
    values[322] = 110.0
    index = pd.Series(values, index=sessions)
    t = sessions[300]
    out = mp.build_targets(index, sessions, [t])
    row = out.iloc[0]
    assert row["observation_date"] == pd.Timestamp(t).normalize()
    assert row["entry_date"] == sessions[301]
    assert row["exit_date"] == sessions[322]
    assert math.isclose(row["target"], 110 / 100 - 1, abs_tol=ATOL, rel_tol=RTOL)
    assert row["reason"] is None


def test_build_targets_missing_endpoint_no_forward_fill():
    sessions = _sessions(400)
    values = np.ones(400)
    values[301] = 100.0
    values[322] = 110.0
    index = pd.Series(values, index=sessions)
    t = sessions[300]
    # 删除 exit 端点 => 缺失，不得顺延到下一个报价
    index.loc[sessions[322]] = np.nan
    out = mp.build_targets(index, sessions, [t])
    assert np.isnan(out.iloc[0]["target"])
    assert out.iloc[0]["reason"] == "endpoint_missing_or_invalid"
    assert out.iloc[0]["exit_date"] == sessions[322]


def test_build_targets_missing_entry_endpoint():
    sessions = _sessions(400)
    values = np.ones(400)
    values[301] = 100.0
    values[322] = 110.0
    index = pd.Series(values, index=sessions)
    t = sessions[300]
    index.loc[sessions[301]] = np.nan
    out = mp.build_targets(index, sessions, [t])
    assert np.isnan(out.iloc[0]["target"])
    assert out.iloc[0]["reason"] == "endpoint_missing_or_invalid"


def test_build_targets_future_incomplete():
    sessions = _sessions(50)
    index = pd.Series(np.arange(1, 51, dtype=float), index=sessions)
    # 位置 27 => x = 27+22 = 49 < 50 可算；位置 28 => x = 50 >= 50 不足
    t_ok = sessions[27]
    t_bad = sessions[28]
    out = mp.build_targets(index, sessions, [t_ok, t_bad])
    assert out.iloc[0]["reason"] is None
    assert np.isfinite(out.iloc[0]["target"])
    assert out.iloc[1]["reason"] == "future_incomplete"
    assert np.isnan(out.iloc[1]["target"])


def test_build_targets_observation_not_session():
    sessions = _sessions(40)
    index = pd.Series(np.arange(1, 41, dtype=float), index=sessions)
    missing = pd.Timestamp("2022-06-06")  # 大概率不在工作日序列里
    out = mp.build_targets(index, sessions, [missing])
    assert out.iloc[0]["reason"] == "observation_not_session"
    assert out.iloc[0]["entry_date"] is None


def test_build_targets_duplicate_or_unordered_sessions_rejected():
    sessions = _sessions(30)
    dup = list(sessions[:10]) + list(sessions[:10])
    index = pd.Series(np.arange(1, 21, dtype=float), index=pd.DatetimeIndex(dup))
    with pytest.raises(ValueError, match="unique"):
        mp.build_targets(index, dup, [sessions[5]])
    rev = list(reversed(sessions[:10]))
    with pytest.raises(ValueError, match="increasing"):
        mp.build_targets(index, rev, [sessions[5]])


# ---------------------------------------------------------------------------
# Task 3：rank_diagnostic（并列平均名次的 Spearman 等价）
# ---------------------------------------------------------------------------


def _diag_frame(momentum, target):
    return pd.DataFrame({"momentum": momentum, "target": target})


def test_rank_diagnostic_anticorrelated():
    frame = _diag_frame([1, 2, 3], [3, 2, 1])
    res = mp.rank_diagnostic(frame)
    assert res["n"] == 3
    assert math.isclose(res["value"], -1.0, abs_tol=ATOL, rel_tol=RTOL)
    assert res["reason"] is None


def test_rank_diagnostic_tied_momentum():
    # 手算：momentum 平均名次 [1.5,1.5,3]，target [1,2,3] => sqrt(3)/2
    frame = _diag_frame([1, 1, 3], [1, 2,3 ])
    res = mp.rank_diagnostic(frame)
    assert res["n"] == 3
    assert math.isclose(res["value"], math.sqrt(3) / 2, abs_tol=ATOL, rel_tol=RTOL)


def test_rank_diagnostic_fewer_than_three_pairs():
    frame = _diag_frame([1, 2], [2, 1])
    res = mp.rank_diagnostic(frame)
    assert res["n"] == 2
    assert res["value"] is None
    assert res["reason"] == "fewer_than_three_pairs"


def test_rank_diagnostic_empty_frame_is_missing_result_not_crash():
    """Task 0 T1：全标签被排除后的空集合是缺失结果，不是程序崩溃。"""
    empty = pd.DataFrame(columns=["momentum", "target"])
    assert mp.rank_diagnostic(empty) == {
        "n": 0, "value": None, "reason": "fewer_than_three_pairs"
    }
    # 连列都没有的空帧（_rank_stage 从空 dict 构造）同样不崩溃
    assert mp.rank_diagnostic(pd.DataFrame()) == {
        "n": 0, "value": None, "reason": "fewer_than_three_pairs"
    }


def test_rank_diagnostic_constant_rank():
    frame = _diag_frame([5, 5, 5], [1, 2, 3])
    res = mp.rank_diagnostic(frame)
    assert res["value"] is None
    assert res["reason"] == "constant_rank"


def test_rank_diagnostic_constant_target_rank():
    frame = _diag_frame([1, 2, 3], [4, 4, 4])
    res = mp.rank_diagnostic(frame)
    assert res["value"] is None
    assert res["reason"] == "constant_rank"


def test_rank_diagnostic_nan_or_inf_pairs_excluded():
    # 第二个配对 momentum=inf，第三个 target=nan => 仅剩 1 个有效配对
    frame = _diag_frame([1.0, np.inf, 2.0], [1.0, 2.0, np.nan])
    res = mp.rank_diagnostic(frame)
    assert res["n"] == 1
    assert res["reason"] == "fewer_than_three_pairs"


def test_rank_diagnostic_excludes_nan_rows_only():
    # 三个有限配对 + 一个 NaN 行；NaN 行不计入
    frame = _diag_frame([1.0, 2.0, 3.0, 4.0], [3.0, 2.0, 1.0, np.nan])
    res = mp.rank_diagnostic(frame)
    assert res["n"] == 3
    assert math.isclose(res["value"], -1.0, abs_tol=ATOL, rel_tol=RTOL)


# ---------------------------------------------------------------------------
# Task 3：未来信息隔离——追加 t 之后的报价/行动不应改写 M(t)
# ---------------------------------------------------------------------------


def test_future_information_does_not_rewrite_momentum():
    # 仅构造到观察日 + 足够窗口；t 之前的报价足以计算 M(t)
    sessions = _sessions(340)
    values = np.arange(1, 341, dtype=float)
    index = pd.Series(values, index=sessions)
    t = sessions[300]
    mom_before = mp.compute_momentum(index)
    target_before = mp.build_targets(index, sessions, [t]).iloc[0]["target"]

    # 追加 t 之后的报价（不改变 t 之前的任何值）
    extra = _sessions(400)[340:]
    full_index = index.copy()
    for day in extra:
        full_index.loc[day] = full_index.get(day - pd.Timedelta(days=1), 1.0) + 1.0
    mom_after = mp.compute_momentum(full_index)

    # M(t) 完全不变（依赖 t-21、t-252，均在 t 之前）
    assert math.isclose(mom_before.loc[t], mom_after.loc[t], abs_tol=ATOL, rel_tol=RTOL)
    # Y(t) 若此前因 x 超出可得数据而缺失，追加后可能由缺失变可算，但不回写 M
    full_sessions = pd.DatetimeIndex(sorted(full_index.index))
    target_after = mp.build_targets(full_index, full_sessions, [t]).iloc[0]
    # 当 x 仍在可得范围内时两者一致；若此前缺失则现在可算，但 M(t) 不变是被检验的核心
    if np.isfinite(target_before) and np.isfinite(target_after["target"]):
        assert math.isclose(target_before, target_after["target"], abs_tol=ATOL, rel_tol=RTOL)
    assert math.isclose(mom_before.loc[t], mom_after.loc[t], abs_tol=ATOL, rel_tol=RTOL)


def test_target_id_constant_is_protocol_measurement_only():
    assert mp.TARGET_ID == "protocol:momentum-next-close-21-session@1.0.0"


# ---------------------------------------------------------------------------
# Task 5 前置：行动字段适配与价格/现金同步缩放的经济含义
# ---------------------------------------------------------------------------


def test_adapt_company_events_maps_actual_fields():
    events = [
        {"event_id": "d1", "symbol": "510300", "type": "cash_dividend",
         "cash_per_unit": 0.059, "effective_date": "2019-01-16"},
        {"event_id": "s1", "symbol": "512400", "type": "split",
         "split_ratio": 2.0, "ex_date": "2021-01-01"},
        {"event_id": "h1", "symbol": "515050", "type": "trading_halt",
         "effective_date": "2020-02-03"},
    ]
    adapted = mp.adapt_company_events(events)
    assert adapted == [
        {"event_id": "d1", "type": "cash_dividend", "effective_date": "2019-01-16",
         "available_at": None, "cash": 0.059},
        {"event_id": "s1", "type": "split", "effective_date": "2021-01-01",
         "available_at": None, "ratio": 2.0},
    ]  # 停牌不进经济指数；ex_date 回退生效；字段名逐项映射


def test_adapt_company_events_rejects_missing_required_field():
    with pytest.raises(ValueError, match="生效日"):
        mp.adapt_company_events([
            {"event_id": "d", "type": "cash_dividend", "cash_per_unit": 0.1}
        ])
    with pytest.raises(ValueError, match="现金"):
        mp.adapt_company_events([
            {"event_id": "d", "type": "cash_dividend", "effective_date": "2020-01-01"}
        ])
    with pytest.raises(ValueError, match="比例"):
        mp.adapt_company_events([
            {"event_id": "s", "type": "split", "effective_date": "2020-01-01"}
        ])


# ---------------------------------------------------------------------------
# 返修 A：参与计算的原料必须独立满足结构/身份/数值条件（主控复核 §2）
# ---------------------------------------------------------------------------


def test_adapt_rejects_foreign_account_field():
    """混入账户字段（fee）的记录不得进入重建。"""
    with pytest.raises(ValueError, match="fee"):
        mp.adapt_company_events([
            {"event_id": "d1", "type": "cash_dividend", "cash": 0.05,
             "effective_date": "2024-01-03", "fee": 1.0}
        ])


def test_adapt_rejects_negative_or_nonfinite_cash():
    with pytest.raises(ValueError, match="非法"):
        mp.adapt_company_events([
            {"event_id": "d1", "type": "cash_dividend", "cash": -0.05,
             "effective_date": "2024-01-03"}
        ])
    with pytest.raises(ValueError, match="非法"):
        mp.adapt_company_events([
            {"event_id": "d1", "type": "cash_dividend", "cash": float("nan"),
             "effective_date": "2024-01-03"}
        ])


def test_adapt_rejects_conflicting_synonymous_cash_fields():
    with pytest.raises(ValueError, match="冲突"):
        mp.adapt_company_events([
            {"event_id": "d1", "type": "cash_dividend", "cash": 0.05,
             "cash_per_unit": 0.06, "effective_date": "2024-01-03"}
        ])
    # 同义字段取值一致不算冲突，正常通过
    adapted = mp.adapt_company_events([
        {"event_id": "d1", "type": "cash_dividend", "cash": 0.05,
         "cash_per_unit": 0.05, "effective_date": "2024-01-03"}
    ])
    assert adapted[0]["cash"] == 0.05


def test_adapt_rejects_conflicting_or_nonpositive_ratio():
    with pytest.raises(ValueError, match="冲突"):
        mp.adapt_company_events([
            {"event_id": "s1", "type": "split", "ratio": 2.0,
             "split_ratio": 3.0, "effective_date": "2024-01-03"}
        ])
    with pytest.raises(ValueError, match="非法"):
        mp.adapt_company_events([
            {"event_id": "s1", "type": "split", "ratio": 0.0,
             "effective_date": "2024-01-03"}
        ])


def test_adapt_rejects_duplicate_event_ids_entirely():
    with pytest.raises(ValueError, match="重复"):
        mp.adapt_company_events([
            {"event_id": "d1", "type": "cash_dividend", "cash": 0.05,
             "effective_date": "2024-01-03"},
            {"event_id": "d1", "type": "cash_dividend", "cash": 0.06,
             "effective_date": "2024-02-03"},
        ])


def test_adapt_rejects_illegal_date():
    with pytest.raises(ValueError, match="日历日"):
        mp.adapt_company_events([
            {"event_id": "d1", "type": "cash_dividend", "cash": 0.05,
             "effective_date": "2024-02-30"}
        ])


def test_adapt_allows_missing_available_at_and_halt_passthrough():
    """单纯缺 available_at 不是不合法：照常适配并保留 None；停牌不进经济指数。"""
    adapted = mp.adapt_company_events([
        {"event_id": "d1", "type": "cash_dividend", "cash": 0.05,
         "effective_date": "2024-01-03"},
        {"event_id": "h1", "type": "trading_halt", "effective_date": "2024-01-04"},
    ])
    assert adapted == [{
        "event_id": "d1", "type": "cash_dividend",
        "effective_date": "2024-01-03", "available_at": None, "cash": 0.05,
    }]


# ---------------------------------------------------------------------------
# 返修 C2：重叠计数按相邻两期真实 [e,x] 区间相交（含端点接触）
# ---------------------------------------------------------------------------


def test_count_window_overlaps_hand_cases():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "run_cli", str(__import__("pathlib").Path(
            __file__).resolve().parents[2] / "scripts/run_momentum_research_prototype.py"))
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    def row(sym, obs, entry, exit_, reason=""):
        return [cli.mp.TARGET_ID, sym, obs, entry, exit_, "0.1", reason]

    obs = ["2024-01-31", "2024-02-29", "2024-03-29"]
    # 完全分离：1月窗口 02-01→03-01，2月窗口 03-04→04-01 → 不相交
    separated = [
        row("S", obs[0], "2024-02-01", "2024-03-01"),
        row("S", obs[1], "2024-03-04", "2024-04-01"),
        row("S", obs[2], "2024-04-01", "2024-04-30"),  # 与上期 04-01 端点接触
    ]
    got = cli.count_window_overlaps(separated, obs)
    assert got[obs[0]] == 0
    assert got[obs[1]] == 1  # 端点接触（共用 04-01 一个交易日）按定义计 1
    # 真正交叠：下一期入口早于本期结束
    overlapping = [
        row("S", obs[0], "2024-02-01", "2024-03-15"),
        row("S", obs[1], "2024-03-04", "2024-04-01"),
    ]
    assert cli.count_window_overlaps(overlapping, obs[:2])[obs[0]] == 1
    # 缺端点/缺失窗口不参与计数
    broken = [
        row("S", obs[0], "2024-02-01", ""),
        row("S", obs[1], "2024-03-04", "2024-04-01"),
    ]
    assert cli.count_window_overlaps(broken, obs[:2])[obs[0]] == 0


def _econ_index(closes, events):
    idx = pd.date_range("2024-01-01", periods=len(closes), freq="D")
    s = pd.Series([float(c) for c in closes], index=idx)
    econ, _ = mp.reconstruct_symbol_economic_index(s, events)
    return econ


def test_price_scale_must_include_cash_dividend_per_unit():
    """10→9 加每份分红 1 与 100→90 加分红 10 的连接都应是 1；
    只缩放价格不缩放现金会把经济含义改掉（连接 0.91）。"""
    div_a = [{"event_id": "d", "type": "cash_dividend",
              "effective_date": "2024-01-03", "cash": 1.0}]
    econ_a = _econ_index([10.0, 10.0, 9.0], div_a)
    div_b = [{"event_id": "d", "type": "cash_dividend",
              "effective_date": "2024-01-03", "cash": 10.0}]
    econ_b = _econ_index([100.0, 100.0, 90.0], div_b)
    # 两个场景的经济指数同比例（首值均为 1，连接均为 1）
    assert math.isclose(econ_a.iloc[-1] / econ_a.iloc[0],
                        econ_b.iloc[-1] / econ_b.iloc[0], abs_tol=ATOL, rel_tol=RTOL)
    assert math.isclose(econ_b.iloc[-1] / econ_b.iloc[0], 1.0, abs_tol=ATOL, rel_tol=RTOL)
    # 错误输入：价格 ×10 而现金不缩放 → 连接变为 0.91，经济含义确已改变
    div_wrong = [{"event_id": "d", "type": "cash_dividend",
                  "effective_date": "2024-01-03", "cash": 1.0}]
    econ_wrong = _econ_index([100.0, 100.0, 90.0], div_wrong)
    assert math.isclose(econ_wrong.iloc[-1] / econ_wrong.iloc[0],
                        0.91, abs_tol=ATOL, rel_tol=RTOL)


def test_split_ratio_is_not_price_scaled():
    """比例拆分系数不随价格缩放：10→5（1拆2）与 100→50（1拆2）连接同为 1。"""
    split_small = [{"event_id": "s", "type": "split",
                    "effective_date": "2024-01-03", "ratio": 2.0}]
    econ_small = _econ_index([10.0, 10.0, 5.0], split_small)
    split_large = [{"event_id": "s", "type": "split",
                    "effective_date": "2024-01-03", "ratio": 2.0}]
    econ_large = _econ_index([100.0, 100.0, 50.0], split_large)
    assert math.isclose(econ_small.iloc[-1] / econ_small.iloc[0],
                        econ_large.iloc[-1] / econ_large.iloc[0],
                        abs_tol=ATOL, rel_tol=RTOL)
    assert math.isclose(econ_large.iloc[-1] / econ_large.iloc[0],
                        1.0, abs_tol=ATOL, rel_tol=RTOL)
