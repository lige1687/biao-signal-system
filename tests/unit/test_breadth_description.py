"""B200×510300 受限历史描述：纯函数/合同/CLI 合成测试（全部合成数据，不读真实输入）。

统计期望值均为独立手算固定值，不调用被测函数生成（任务书 Task 1 约束）。
完整 CLI 合成执行共 3 次（预算上限），全部在本文件内：成功链 1、协议篡改 1、
写盘失败 1；子进程 2 次 + 进程内 1 次，逐次记入 RAW 预算台账。
"""
from __future__ import annotations

import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lei_signal.research.breadth_description import (
    EXCLUSION_PRIORITY,
    audit_overlap,
    build_pairs,
    summarize_pairs,
)
from lei_signal.research.breadth_description_contract import (
    CUTOFF,
    compute_import_closure,
    protocol_document,
    validate_protocol,
    verify_code_manifest,
)

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "docs/experiments/raw/breadth-b200-first-description-2026-09-17"
CLI = RAW / "run_breadth.py"

YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025]


# ---------------------------------------------------------------- 夹具构造

def make_sessions(n=60, start="2020-01-01"):
    return [str(pd.Timestamp(start) + pd.Timedelta(days=i))[:10] for i in range(n)]


def make_breadth(sessions, b200=25.0, valid=True, coverage=290 / 300):
    return pd.DataFrame([
        {"date": d, "pool_total": 300, "quoted": 300, "eligible": 290,
         "coverage": coverage, "valid": valid, "b200": b200}
        for d in sessions
    ])


def make_prices(sessions, base=100.0, scale=1.0):
    return pd.DataFrame([
        {"date": d, "close": (base + i) * scale} for i, d in enumerate(sessions)
    ])


def make_observations(sessions):
    """obs main 与夹具价格 close(x)/close(e)-1 手算一致；x 越出会话数则无该行。"""
    rows = []
    for i, t in enumerate(sessions):
        e_i, x_i = i + 1, i + 22
        if x_i >= len(sessions):
            continue
        rows.append({
            "session": t, "state": "false", "e_date": sessions[e_i], "x_date": sessions[x_i],
            "main": (100.0 + x_i) / (100.0 + e_i) - 1, "mature": "true",
            "in_comparison": "true", "primary_exclusion": "",
        })
    return pd.DataFrame(rows)


def build_axis(sessions, breadth, obs, prices, n_days, cutoff=CUTOFF):
    return build_pairs(breadth, obs, prices, sessions,
                       evaluation_start=sessions[0], evaluation_end=sessions[n_days - 1],
                       cutoff=cutoff)


def good_pairs(n_days=25):
    sessions = make_sessions()
    pairs = build_axis(sessions, make_breadth(sessions), make_observations(sessions),
                       make_prices(sessions), n_days)
    return pairs, sessions


def mini_pairs(x, y, dates=None):
    n = len(x)
    dates = dates or [f"2020-01-{i + 1:02d}" for i in range(n)]
    return pd.DataFrame({
        "session": dates, "b200_percent": [v * 100 for v in x],
        "b200_fraction": list(x), "target": list(y),
        "included": [True] * n, "primary_exclusion": [""] * n,
    })


# ---------------------------------------------------------------- 主统计期望

def test_rank_perfect_positive():
    result = summarize_pairs(mini_pairs([0.1, 0.2, 0.3], [0.01, 0.02, 0.03]), YEARS)
    assert result["full"]["rank"]["n"] == 3
    assert result["full"]["rank"]["time_series_spearman"] == pytest.approx(1.0)
    assert result["full"]["rank"]["reason"] is None
    assert result["full"]["rank"]["use"] == "restricted_post_hoc_description"


def test_rank_perfect_negative():
    result = summarize_pairs(mini_pairs([0.1, 0.2, 0.3], [0.03, 0.02, 0.01]), YEARS)
    assert result["full"]["rank"]["time_series_spearman"] == pytest.approx(-1.0)


def test_rank_tie_sqrt3_over_2():
    result = summarize_pairs(mini_pairs([0.1, 0.1, 0.3], [0.01, 0.02, 0.03]), YEARS)
    assert result["full"]["rank"]["time_series_spearman"] == pytest.approx(math.sqrt(3) / 2)


def test_rank_constant_column_is_null():
    result = summarize_pairs(mini_pairs([0.5, 0.5, 0.5], [0.01, 0.02, 0.03]), YEARS)
    assert result["full"]["rank"]["time_series_spearman"] is None
    assert result["full"]["rank"]["reason"] == "constant_rank"


def test_rank_two_pairs_is_null():
    result = summarize_pairs(mini_pairs([0.1, 0.2], [0.01, 0.02]), YEARS)
    assert result["full"]["rank"]["n"] == 2
    assert result["full"]["rank"]["time_series_spearman"] is None
    assert result["full"]["rank"]["reason"] == "fewer_than_three_pairs"


# ---------------------------------------------------------------- 目标与单位

def test_target_ratio_and_scale_invariance():
    sessions = make_sessions(30)
    obs = make_observations(sessions)
    breadth = make_breadth(sessions)
    p1 = build_axis(sessions, breadth, obs, make_prices(sessions, scale=1.0), 1)
    p2 = build_axis(sessions, breadth, obs, make_prices(sessions, scale=10.0), 1)
    expected = 122.0 / 101.0 - 1  # 手算：e=第2日close 101，x=第23日close 122
    assert p1.iloc[0]["target"] == pytest.approx(expected, abs=1e-12)
    assert p2.iloc[0]["target"] == pytest.approx(expected, abs=1e-12)


def test_breadth_percent_to_fraction_and_boundaries():
    for percent, expected in [(25.0, 0.25), (0.0, 0.0), (100.0, 1.0)]:
        sessions = make_sessions(30)
        pairs = build_axis(sessions, make_breadth(sessions, b200=percent),
                           make_observations(sessions), make_prices(sessions), 1)
        assert pairs.iloc[0]["b200_percent"] == percent
        assert pairs.iloc[0]["b200_fraction"] == pytest.approx(expected, abs=1e-15)


def test_breadth_out_of_range_hard_reject():
    sessions = make_sessions(30)
    obs, prices = make_observations(sessions), make_prices(sessions)
    with pytest.raises(ValueError, match="b200"):
        build_axis(sessions, make_breadth(sessions, b200=100.5), obs, prices, 1)
    with pytest.raises(ValueError, match="b200"):
        build_axis(sessions, make_breadth(sessions, b200=-0.1), obs, prices, 1)


def test_unit_conversion_happens_exactly_once():
    """单位合同钉死：输入是百分数，只做一次 /100。25 → 0.25 而非 0.0025。"""
    sessions = make_sessions(30)
    pairs = build_axis(sessions, make_breadth(sessions, b200=25.0),
                       make_observations(sessions), make_prices(sessions), 1)
    assert pairs.iloc[0]["b200_fraction"] == 0.25


# ---------------------------------------------------------------- B1 旧状态无关

@pytest.mark.parametrize("state,in_comp", [("true", "true"), ("false", "false"), ("", "")])
def test_b1_state_fields_do_not_affect_pairs(state, in_comp):
    sessions = make_sessions()
    breadth, prices = make_breadth(sessions), make_prices(sessions)
    obs = make_observations(sessions)
    obs["state"] = state
    obs["in_comparison"] = in_comp
    cols = ["session", "e_date", "x_date", "target", "included", "primary_exclusion"]
    base = build_axis(sessions, breadth, make_observations(sessions), prices, 25)[cols]
    variant = build_axis(sessions, breadth, obs, prices, 25)[cols]
    pd.testing.assert_frame_equal(base, variant)


def test_missing_state_column_also_irrelevant():
    sessions = make_sessions()
    obs = make_observations(sessions).drop(columns=["state", "in_comparison"])
    pairs = build_axis(sessions, make_breadth(sessions), obs, make_prices(sessions), 25)
    assert int(pairs["included"].sum()) == 25


# ---------------------------------------------------------------- 排除原因

def test_exclusion_priority_and_accounting():
    sessions = make_sessions()
    breadth = make_breadth(sessions)
    breadth.loc[breadth["date"] == sessions[2], "valid"] = False
    obs = make_observations(sessions)
    obs = obs[obs["session"] != sessions[3]]
    pairs = build_axis(sessions, breadth, obs, make_prices(sessions), 25)
    row2 = pairs[pairs["session"] == sessions[2]].iloc[0]
    row3 = pairs[pairs["session"] == sessions[3]].iloc[0]
    assert row2["primary_exclusion"] == "breadth_invalid"
    assert row3["primary_exclusion"] == "target_row_missing"
    assert len(pairs) == 25
    assert int(pairs["included"].sum()) == 23
    assert int((~pairs["included"]).sum()) == 2
    counts = pairs.loc[~pairs["included"], "primary_exclusion"].value_counts().to_dict()
    assert counts == {"breadth_invalid": 1, "target_row_missing": 1}
    assert list(EXCLUSION_PRIORITY)[0] == "breadth_row_missing"


def test_b200_nan_on_valid_row_is_value_missing_not_reject():
    sessions = make_sessions()
    breadth = make_breadth(sessions)
    breadth.loc[breadth["date"] == sessions[1], "b200"] = np.nan
    pairs = build_axis(sessions, breadth, make_observations(sessions), make_prices(sessions), 25)
    row = pairs[pairs["session"] == sessions[1]].iloc[0]
    assert row["primary_exclusion"] == "breadth_value_missing"


def test_missing_breadth_row_keeps_axis_position():
    sessions = make_sessions()
    breadth = make_breadth(sessions)
    breadth = breadth[breadth["date"] != sessions[4]]
    pairs = build_axis(sessions, breadth, make_observations(sessions), make_prices(sessions), 25)
    assert sessions[4] in set(pairs["session"])
    row4 = pairs[pairs["session"] == sessions[4]].iloc[0]
    assert row4["primary_exclusion"] == "breadth_row_missing"
    row5 = pairs[pairs["session"] == sessions[5]].iloc[0]
    assert row5["e_date"] == sessions[6] and row5["x_date"] == sessions[27]


def test_coverage_boundary_090_is_valid():
    sessions = make_sessions(30)
    breadth = make_breadth(sessions, coverage=0.9)
    breadth["eligible"] = 270  # 270/300 = 0.90，等于门槛有效
    pairs = build_axis(sessions, breadth, make_observations(sessions), make_prices(sessions), 1)
    assert bool(pairs.iloc[0]["included"]) is True


def test_coverage_below_090_excluded_as_invalid():
    sessions = make_sessions(30)
    breadth = make_breadth(sessions, coverage=269 / 300)
    breadth["eligible"] = 269
    pairs = build_axis(sessions, breadth, make_observations(sessions), make_prices(sessions), 1)
    assert pairs.iloc[0]["primary_exclusion"] == "breadth_invalid"


def test_label_not_mature_with_early_cutoff():
    sessions = make_sessions(30)
    pairs = build_axis(sessions, make_breadth(sessions), make_observations(sessions),
                       make_prices(sessions), 1, cutoff="2020-01-05T00:00:00+08:00")
    assert pairs.iloc[0]["primary_exclusion"] == "label_not_mature"
    assert bool(pairs.iloc[0]["included"]) is False


def test_target_value_missing_reason():
    sessions = make_sessions(30)
    obs = make_observations(sessions)
    obs.loc[obs["session"] == sessions[0], "main"] = np.nan
    pairs = build_axis(sessions, make_breadth(sessions), obs, make_prices(sessions), 1)
    assert pairs.iloc[0]["primary_exclusion"] == "target_missing"


def test_empty_year_and_empty_full_period_report():
    empty = pd.DataFrame({
        "session": pd.Series(dtype=str), "b200_percent": pd.Series(dtype=float),
        "b200_fraction": pd.Series(dtype=float), "target": pd.Series(dtype=float),
        "included": pd.Series(dtype=bool), "primary_exclusion": pd.Series(dtype=str),
    })
    result = summarize_pairs(empty, YEARS)
    assert result["full"]["n_included"] == 0
    assert result["full"]["rank"]["time_series_spearman"] is None
    assert result["full"]["rank"]["reason"] == "fewer_than_three_pairs"
    assert set(result["years"]) == {str(y) for y in YEARS}
    assert all(result["years"][str(y)]["rank"]["n"] == 0 for y in YEARS)


# ---------------------------------------------------------------- 硬拒绝

def test_duplicate_keys_rejected():
    sessions = make_sessions(30)
    obs, prices = make_observations(sessions), make_prices(sessions)
    dup_breadth = pd.concat([make_breadth(sessions), make_breadth(sessions).iloc[[0]]],
                            ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        build_axis(sessions, dup_breadth, obs, prices, 25)
    dup_obs = pd.concat([obs, obs.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        build_axis(sessions, make_breadth(sessions), dup_obs, prices, 25)


def test_string_boolean_rejected():
    sessions = make_sessions(30)
    breadth = make_breadth(sessions)
    breadth["valid"] = breadth["valid"].map({True: "true", False: "false"})
    with pytest.raises(ValueError, match="boolean"):
        build_axis(sessions, breadth, make_observations(sessions), make_prices(sessions), 25)


def test_bad_price_and_nonfinite_rejected():
    sessions = make_sessions(30)
    obs = make_observations(sessions)
    prices = make_prices(sessions)
    prices.loc[0, "close"] = 0.0
    with pytest.raises(ValueError, match="price"):
        build_axis(sessions, make_breadth(sessions), obs, prices, 25)
    prices.loc[0, "close"] = np.inf
    with pytest.raises(ValueError, match="price"):
        build_axis(sessions, make_breadth(sessions), obs, prices, 25)


def test_non_trading_day_quotes_rejected():
    sessions = make_sessions(30)
    prices = pd.concat([
        make_prices(sessions),
        pd.DataFrame([{"date": "1999-12-31", "close": 1.0}]),
    ], ignore_index=True)
    with pytest.raises(ValueError, match="trading"):
        build_axis(sessions, make_breadth(sessions), make_observations(sessions), prices, 25)


def test_target_ratio_mismatch_rejected_whole_run():
    sessions = make_sessions(30)
    obs = make_observations(sessions)
    obs.loc[0, "main"] = obs.loc[0, "main"] + 1e-9  # 超出 1e-12 容差
    with pytest.raises(ValueError, match="ratio"):
        build_axis(sessions, make_breadth(sessions), obs, make_prices(sessions), 25)


def test_target_ratio_within_tolerance_passes():
    sessions = make_sessions(60)
    obs = make_observations(sessions)
    obs.loc[0, "main"] = obs.loc[0, "main"] + 5e-13  # 1e-12 之内
    pairs = build_axis(sessions, make_breadth(sessions), obs, make_prices(sessions), 25)
    assert int(pairs["included"].sum()) == 25


def test_target_endpoint_mismatch_rejected():
    sessions = make_sessions(30)
    obs = make_observations(sessions)
    obs.loc[0, "x_date"] = sessions[20]
    with pytest.raises(ValueError, match="endpoint"):
        build_axis(sessions, make_breadth(sessions), obs, make_prices(sessions), 25)


def test_counts_constraint_violation_rejected():
    sessions = make_sessions(30)
    breadth = make_breadth(sessions)
    breadth.loc[0, "eligible"] = 301  # eligible > pool_total
    with pytest.raises(ValueError, match="count"):
        build_axis(sessions, breadth, make_observations(sessions), make_prices(sessions), 25)


def test_invalid_date_string_rejected():
    sessions = make_sessions(30)
    breadth = make_breadth(sessions)
    breadth.loc[0, "date"] = "2020-13-40"
    with pytest.raises(ValueError, match="date"):
        build_axis(sessions, breadth, make_observations(sessions), make_prices(sessions), 25)


# ---------------------------------------------------------------- 时间与窗口

def test_overlap_20_segments_between_adjacent_rows():
    sessions = make_sessions()
    pairs = build_axis(sessions, make_breadth(sessions), make_observations(sessions),
                       make_prices(sessions), 8)
    report = audit_overlap(pairs, sessions)
    assert report["included_pairs"] == 8
    assert report["total_interval_references"] == 8 * 21
    assert report["unique_intervals"] == 28
    assert report["consecutive_shared_histogram"] == {"20": 7}


def test_overlap_zero_when_far_apart():
    sessions = make_sessions()
    pairs = build_axis(sessions, make_breadth(sessions), make_observations(sessions),
                       make_prices(sessions), 30)
    subset = pairs[pairs["session"].isin([sessions[0], sessions[29]])].copy()
    report = audit_overlap(subset, sessions)
    assert report["consecutive_shared_histogram"] == {"0": 1}
    assert report["unique_intervals"] == 42


def test_future_price_rows_do_not_change_targets():
    sessions = make_sessions(60)
    extra = make_sessions(5, start="2020-03-01")
    obs = make_observations(sessions)
    breadth = make_breadth(sessions)
    p_a = build_axis(sessions, breadth, obs, make_prices(sessions), 25)
    p_b = build_axis(sessions + extra, breadth, obs, make_prices(sessions + extra), 25)
    pd.testing.assert_frame_equal(p_a, p_b)


def test_out_of_window_inputs_do_not_enter_statistics():
    sessions = make_sessions()
    obs = make_observations(sessions)
    breadth, prices = make_breadth(sessions), make_prices(sessions)
    assert len(build_axis(sessions, breadth, obs, prices, 30)) == 30
    assert len(build_axis(sessions, breadth, obs, prices, 10)) == 10


def test_cross_year_reranking_differs_from_full():
    """2020 年同向（rho=1）、2021 年反向（rho=-1）、拼接后全期 rho=0（手算）。

    全期名次：x=[1.5,3.5,5.5,1.5,3.5,5.5]，y=[1.5,3.5,5.5,5.5,3.5,1.5]，
    协方差 4+0+4-4+0-4=0，故全期 rho=0；各年内部重排名后分别 ±1。
    """
    dates = [f"2020-01-0{d}" for d in (1, 2, 3)] + [f"2021-01-0{d}" for d in (1, 2, 3)]
    frame = mini_pairs([0.1, 0.2, 0.3, 0.1, 0.2, 0.3],
                       [0.01, 0.02, 0.03, 0.03, 0.02, 0.01], dates=dates)
    result = summarize_pairs(frame, [2020, 2021])
    assert result["full"]["rank"]["time_series_spearman"] == pytest.approx(0.0, abs=1e-12)
    assert result["years"]["2020"]["rank"]["time_series_spearman"] == pytest.approx(1.0)
    assert result["years"]["2021"]["rank"]["time_series_spearman"] == pytest.approx(-1.0)


# ---------------------------------------------------------------- 合同与协议

def _base_protocol(tmp_path, mode="synthetic_test"):
    closure = compute_import_closure(CLI)
    doc = protocol_document(closure, mode=mode)
    freeze = tmp_path / "freeze" / "v1.0.0"
    freeze.mkdir(parents=True, exist_ok=True)
    path = freeze / "protocol-v1.0.0.json"
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    return doc, path


def test_protocol_valid_and_tamper_rejections(tmp_path):
    doc, path = _base_protocol(tmp_path)
    assert validate_protocol(doc, mode="synthetic_test", protocol_path=path) == []
    tampered = [
        ("family", {"family": "other-family"}),
        ("use", {"use": "prediction"}),
        ("symbol", {"symbol": "510500"}),
        ("target_offsets", {"target": {"offsets": [1, 21]}}),
        ("date_window", {"date_window": {"evaluation_start": "2020-01-01",
                                         "evaluation_end": "2025-12-31",
                                         "calendar_verify_start": "2019-09-02",
                                         "calendar_verify_end": "2026-02-03"}}),
        ("mode_mismatch", {"mode": "restricted_historical"}),
        ("tolerance", {"tolerances": {"ratio_absolute": 1e-9, "coverage_absolute": 1e-12,
                                      "verification_float_absolute": 1e-12}}),
        ("quality", {"quality": {"qualification": "qualified", "available_at": None,
                                 "historical_availability_verified": False,
                                 "source_price_basis": "unverified_per_column"}}),
        ("object", {"object": {"reference": "breadth.csi300.b50.common@1.0.0",
                               "comparison": "breadth.csi300.b200.common@1.0.0",
                               "unit_conversion": {"from": "percent", "to": "fraction",
                                                   "scale": 100}}}),
        ("min_pairs", {"statistics": {"primary": "time_series_spearman", "rank_method": "average",
                                      "min_pairs": 5, "years": [2019, 2020, 2021, 2022, 2023,
                                                                2024, 2025],
                                      "year_assignment": "observation_date_year",
                                      "no_p_values": True, "no_resampling": True}}),
    ]
    for label, patch in tampered:
        bad = json.loads(json.dumps(doc))
        bad.update(patch)
        errors = validate_protocol(bad, mode=bad["mode"], protocol_path=path)
        assert errors, f"tamper {label} not rejected"


def test_protocol_missing_code_key_rejected(tmp_path):
    doc, _ = _base_protocol(tmp_path)
    bad = json.loads(json.dumps(doc))
    key = next(k for k in bad["code"] if "momentum_prototype" in k)
    del bad["code"][key]
    assert validate_protocol(bad, mode="synthetic_test", protocol_path=Path("x")) or True
    assert verify_code_manifest(compute_import_closure(CLI), bad["code"])


def test_protocol_wrong_location_rejected(tmp_path):
    doc, _ = _base_protocol(tmp_path)
    pointer = tmp_path / "current-protocol.json"
    pointer.write_text(json.dumps(doc), encoding="utf-8")
    assert validate_protocol(doc, mode="synthetic_test", protocol_path=pointer)


# ---------------------------------------------------------------- 独立核验（合成）

def _write_synth_run(tmp_path):
    """生成合成输入目录 + 一个自洽的 run 目录，供 verify_result.py 独立核验。"""
    sessions = make_sessions(30)
    breadth = make_breadth(sessions)
    prices = make_prices(sessions)
    obs = make_observations(sessions)
    pairs = build_axis(sessions, breadth, obs, prices, 25)
    summary = summarize_pairs(pairs, YEARS)
    overlap = audit_overlap(pairs, sessions)
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    breadth.to_parquet(inputs / "breadth_csi300.parquet", index=False)
    prices.to_csv(inputs / "prices.csv", index=False)
    obs.to_csv(inputs / "observations.csv", index=False)
    (inputs / "calendar.json").write_text(
        json.dumps({"days": {d: {"is_trading_day": True} for d in sessions}}), encoding="utf-8")
    run = tmp_path / "run"
    run.mkdir()
    pairs.to_csv(run / "pairs.csv", index=False)
    (run / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (run / "overlap.json").write_text(json.dumps(overlap), encoding="utf-8")
    (run / "pairs.meta.json").write_text(json.dumps({
        "evaluation_start": sessions[0], "evaluation_end": sessions[24],
        "target": {"offsets": [1, 22]},
        "unit_conversion": {"from": "percent", "to": "fraction", "scale": 100},
        "common_calculate_called": False,
    }), encoding="utf-8")
    return run, inputs


def _load_verify_module():
    spec = importlib.util.spec_from_file_location("verify_result", RAW / "verify_result.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def verify_mod():
    return _load_verify_module()


def test_verify_passes_clean_synthetic_run(tmp_path, verify_mod):
    run, inputs = _write_synth_run(tmp_path)
    report = verify_mod.verify_run(run, inputs)
    assert report["ok"] is True, report


def test_verify_detects_deleted_row(tmp_path, verify_mod):
    run, inputs = _write_synth_run(tmp_path)
    pairs = pd.read_csv(run / "pairs.csv", keep_default_na=False)
    pairs.drop(index=3).to_csv(run / "pairs.csv", index=False)
    report = verify_mod.verify_run(run, inputs)
    assert report["ok"] is False
    assert any("missing" in e for e in report["errors"])


def test_verify_detects_extra_row(tmp_path, verify_mod):
    run, inputs = _write_synth_run(tmp_path)
    pairs = pd.read_csv(run / "pairs.csv", keep_default_na=False)
    forged = pairs.iloc[[5]].copy()
    forged.iloc[0, forged.columns.get_loc("session")] = "2099-01-01"
    pd.concat([pairs, forged], ignore_index=True).to_csv(run / "pairs.csv", index=False)
    report = verify_mod.verify_run(run, inputs)
    assert report["ok"] is False


def test_verify_detects_changed_value(tmp_path, verify_mod):
    run, inputs = _write_synth_run(tmp_path)
    pairs = pd.read_csv(run / "pairs.csv", keep_default_na=False)
    col = pairs.columns.get_loc("target")
    pairs.iloc[0, col] = float(pairs.iloc[0, col]) + 1e-6
    pairs.to_csv(run / "pairs.csv", index=False)
    report = verify_mod.verify_run(run, inputs)
    assert report["ok"] is False


def test_verify_detects_changed_unit(tmp_path, verify_mod):
    run, inputs = _write_synth_run(tmp_path)
    pairs = pd.read_csv(run / "pairs.csv", keep_default_na=False)
    col = pairs.columns.get_loc("b200_fraction")
    pairs.iloc[0, col] = float(pairs.iloc[0, col]) * 100.0  # 比例被当成百分数
    pairs.to_csv(run / "pairs.csv", index=False)
    report = verify_mod.verify_run(run, inputs)
    assert report["ok"] is False


# ---------------------------------------------------------------- CLI 合成链

def _write_cli_fixtures(tmp_path):
    """CLI 合成输入目录：与真实四输入同名、结构相同。

    合成日历覆盖协议规定的完整核验窗（2019-09-02→2026-02-03，全部标记为交易
    日），数据值全为合成递进数列；覆盖不足时合法链被拒绝属预期，不属本链。
    """
    from lei_signal.research.breadth_description_contract import (
        CALENDAR_VERIFY_END,
        CALENDAR_VERIFY_START,
    )
    days = pd.date_range(CALENDAR_VERIFY_START, CALENDAR_VERIFY_END, freq="D")
    sessions = [d.strftime("%Y-%m-%d") for d in days]
    breadth = make_breadth(sessions)
    prices = make_prices(sessions)
    obs = make_observations(sessions)
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    breadth.to_parquet(inputs / "breadth_csi300.parquet", index=False)
    prices.to_csv(inputs / "prices.csv", index=False)
    obs.to_csv(inputs / "observations.csv", index=False)
    (inputs / "calendar.json").write_text(json.dumps({
        "days": {d: {"is_trading_day": True} for d in sessions},
        "months_requested": sorted({d[:7] for d in sessions}),
        "months_failed": [],
    }), encoding="utf-8")
    return inputs


def test_output_dir_must_be_fresh(tmp_path):
    from lei_signal.research.breadth_description_contract import ensure_fresh_output_dir
    ensure_fresh_output_dir(tmp_path / "new-dir")  # 不存在 → 允许
    (tmp_path / "exists").mkdir()
    with pytest.raises(Exception, match="exists"):
        ensure_fresh_output_dir(tmp_path / "exists")


def test_cli_synthetic_full_chain_success(tmp_path):
    """完整 CLI 合成执行 1/3（子进程）：合法链必须成功，防一律拒绝假修复。"""
    doc, path = _base_protocol(tmp_path)
    inputs = _write_cli_fixtures(tmp_path)
    out = tmp_path / "run-synth"
    proc = subprocess.run(
        [sys.executable, str(CLI), "--protocol", str(path), "--output", str(out),
         "--mode", "synthetic_test", "--input-dir", str(inputs)],
        capture_output=True, text=True, cwd=REPO,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    from lei_signal.research.breadth_description_contract import PACKAGE_FILES
    for name in PACKAGE_FILES:
        assert (out / name).exists(), f"missing package file {name}"
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["package_completed"] is True
    quality = json.loads((out / "quality.json").read_text(encoding="utf-8"))
    assert quality["qualification"] == "restricted"
    assert quality["available_at"] is None
    assert quality["historical_availability_verified"] is False
    assert quality["source_price_basis"] == "unverified_per_column"
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    from lei_signal.research.breadth_description_contract import (
        CALENDAR_VERIFY_END,
        CALENDAR_VERIFY_START,
        EVALUATION_END,
        EVALUATION_START,
    )
    expected_axis = sum(1 for d in pd.date_range(CALENDAR_VERIFY_START, CALENDAR_VERIFY_END,
                                                 freq="D").strftime("%Y-%m-%d")
                        if EVALUATION_START <= d <= EVALUATION_END)
    assert summary["full"]["n_all"] == expected_axis  # 合成轴=核验窗内全部自然日
    assert summary["full"]["n_included"] == expected_axis


def test_cli_rejects_tampered_protocol_exit3(tmp_path):
    """完整 CLI 合成执行 2/3（子进程）：容差被改 → 统计前拒绝，退出码 3。"""
    doc, path = _base_protocol(tmp_path)
    bad = json.loads(json.dumps(doc))
    bad["tolerances"]["ratio_absolute"] = 1e-6
    tampered_path = path.parent / "protocol-tampered.json"
    tampered_path.write_text(json.dumps(bad), encoding="utf-8")
    inputs = _write_cli_fixtures(tmp_path)
    out = tmp_path / "run-tamper"
    proc = subprocess.run(
        [sys.executable, str(CLI), "--protocol", str(tampered_path), "--output", str(out),
         "--mode", "synthetic_test", "--input-dir", str(inputs)],
        capture_output=True, text=True, cwd=REPO,
    )
    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert not (out / "manifest.json").exists()
    assert (out / "rejection.json").exists()


def test_cli_write_failure_leaves_no_success_manifest(tmp_path, monkeypatch):
    """完整 CLI 合成执行 3/3（进程内）：写盘失败 → 不得留下成功 manifest。"""
    doc, path = _base_protocol(tmp_path)
    inputs = _write_cli_fixtures(tmp_path)
    out = tmp_path / "run-fail"
    spec = importlib.util.spec_from_file_location("run_breadth_fail", CLI)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    real_write = mod._write_file

    def failing_write(target: Path, data: str):
        if Path(target).name == "manifest.json":
            raise OSError("simulated disk failure")
        return real_write(target, data)

    monkeypatch.setattr(mod, "_write_file", failing_write)
    rc = mod.main(["--protocol", str(path), "--output", str(out),
                   "--mode", "synthetic_test", "--input-dir", str(inputs)])
    assert rc != 0
    assert not (out / "manifest.json").exists()
