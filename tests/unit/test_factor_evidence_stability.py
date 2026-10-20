"""factor_evidence stability 测试：全期/逐年/留一年 + 区间重叠审计。

固定教学例与手算常数来自任务书 §2.2 与 Task 2；真实数据交叉值来自
raw/expectations.json（stdlib 独立推导，非被测函数输出）。
"""
from __future__ import annotations

import pandas as pd
import pytest

from lei_signal.research.factor_evidence.stability import (
    overlap_audit,
    state_summary,
    year_stability,
)

EPS = 1e-12


def _canon(rows):
    cols = ["symbol", "session", "state", "main", "aux", "legal",
            "legal_reason", "e_date", "x_date"]
    return pd.DataFrame(rows, columns=cols)


def _row(session, state, main, e, x, legal=True, reason=None, aux=0.0):
    return {"symbol": "510300", "session": session, "state": state,
            "main": main, "aux": aux, "legal": legal, "legal_reason": reason,
            "e_date": e, "x_date": x}


# ── 教学例：A/B 两年（任务书手算常数） ─────────────────────────────

def _teaching_frame():
    """A年 true=[.10,.10] false=[.20]；B年 true=[-.10] false=[0,0]。"""
    return _canon([
        _row("2020-01-02", True, 0.10, "2020-01-03", "2020-02-03"),
        _row("2020-01-03", True, 0.10, "2020-01-06", "2020-02-04"),
        _row("2020-01-06", False, 0.20, "2020-01-07", "2020-02-05"),
        _row("2021-01-04", True, -0.10, "2021-01-05", "2021-02-05"),
        _row("2021-01-05", False, 0.0, "2021-01-06", "2021-02-08"),
        _row("2021-01-06", False, 0.0, "2021-01-07", "2021-02-09"),
    ])


def test_teaching_example_full_period_delta():
    s = state_summary(_teaching_frame())
    assert s["true"]["n"] == 3 and s["false"]["n"] == 3
    assert s["delta"] == pytest.approx(-1 / 30, abs=EPS)
    assert s["true"]["mean"] == pytest.approx(1 / 30, abs=EPS)
    assert s["false"]["mean"] == pytest.approx(0.2 / 3, abs=EPS)
    # 辅助：中位数差与上涨比例差（只描述，不选赢家）
    assert s["median_diff"] == pytest.approx(0.10 - 0.0, abs=EPS)
    assert s["up_ratio_diff"] == pytest.approx(2 / 3 - 1 / 3, abs=EPS)


def test_teaching_example_year_and_loo_and_equal_weight():
    y = year_stability(_teaching_frame())
    assert y["years"]["2020"]["delta"] == pytest.approx(-0.10, abs=EPS)
    assert y["years"]["2021"]["delta"] == pytest.approx(-0.10, abs=EPS)
    assert y["sign_counts"] == {"positive": 0, "zero": 0, "negative": 2}
    # 留一年：去A/去B 都是 -0.10
    assert y["leave_one_year_out"]["2020"]["delta"] == pytest.approx(-0.10, abs=EPS)
    assert y["leave_one_year_out"]["2021"]["delta"] == pytest.approx(-0.10, abs=EPS)
    # 等权年度差 = -0.10（另一视角，不替代全期 -1/30）
    assert y["equal_weight_year_delta"]["mean_delta"] == pytest.approx(-0.10, abs=EPS)
    assert y["equal_weight_year_delta"]["years"] == ["2020", "2021"]
    assert y["equal_weight_year_delta"]["full_period_delta"] == pytest.approx(
        -1 / 30, abs=EPS)


def test_direction_not_hardcoded_opposite_year_deltas():
    # 反方向年份：A年 delta=+0.10，B年 delta=+0.10，全期也应为正
    rows = [
        _row("2020-01-02", True, 0.20, "2020-01-03", "2020-02-03"),
        _row("2020-01-03", False, 0.10, "2020-01-06", "2020-02-04"),
        _row("2020-01-06", False, 0.10, "2020-01-07", "2020-02-05"),
        _row("2021-01-04", True, 0.0, "2021-01-05", "2021-02-05"),
        _row("2021-01-05", True, 0.0, "2021-01-06", "2021-02-08"),
        _row("2021-01-06", False, -0.10, "2021-01-07", "2021-02-09"),
    ]
    y = year_stability(_canon(rows))
    assert y["years"]["2020"]["delta"] == pytest.approx(0.10, abs=EPS)
    assert y["years"]["2021"]["delta"] == pytest.approx(0.10, abs=EPS)
    assert y["sign_counts"] == {"positive": 2, "zero": 0, "negative": 0}


def test_zero_delta_year_and_mixed_sign_counts():
    rows = [
        _row("2020-01-02", True, 0.10, "2020-01-03", "2020-02-03"),
        _row("2020-01-03", False, 0.10, "2020-01-06", "2020-02-04"),
        _row("2021-01-04", True, 0.05, "2021-01-05", "2021-02-05"),
        _row("2021-01-05", False, -0.05, "2021-01-06", "2021-02-08"),
        _row("2022-01-04", True, -0.05, "2022-01-05", "2022-02-05"),
        _row("2022-01-05", False, 0.05, "2022-01-06", "2022-02-08"),
    ]
    y = year_stability(_canon(rows))
    assert y["years"]["2020"]["delta"] == 0.0
    assert y["sign_counts"] == {"positive": 1, "zero": 1, "negative": 1}


def test_shuffled_rows_sorted_explicitly():
    frame = _teaching_frame()
    shuffled = frame.sample(frac=1.0, random_state=7).reset_index(drop=True)
    a = year_stability(frame)
    b = year_stability(shuffled)
    assert a["years"] == b["years"]
    assert a["leave_one_year_out"] == b["leave_one_year_out"]
    assert state_summary(frame)["delta"] == state_summary(shuffled)["delta"]


def test_single_group_and_empty_year_structured():
    rows = [
        _row("2020-01-02", True, 0.10, "2020-01-03", "2020-02-03"),
        _row("2021-01-04", True, -0.10, "2021-01-05", "2021-02-05"),
    ]
    s = state_summary(_canon(rows))
    assert s["delta"] is None and s["null_reason"]
    y = year_stability(_canon(rows))
    for year in ("2020", "2021"):
        assert y["years"][year]["false"]["n"] == 0
        assert y["years"][year]["delta"] is None
        assert y["years"][year]["null_reason"]
        # 留一年缺组也要 null+原因
        assert y["leave_one_year_out"][year]["delta"] is None
        assert y["leave_one_year_out"][year]["null_reason"]
    assert y["equal_weight_year_delta"]["mean_delta"] is None
    assert y["equal_weight_year_delta"]["years"] == []


def test_illegal_and_missing_rows_excluded_from_stats():
    rows = [
        _row("2020-01-02", True, 0.10, "2020-01-03", "2020-02-03"),
        _row("2020-01-03", False, 0.20, "2020-01-06", "2020-02-04"),
        # 非法行（目标缺失）不进统计
        _row("2020-01-06", True, None, "2020-01-07", "2020-02-05",
             legal=False, reason="target_missing"),
        # 未知状态行不进统计
        _row("2020-01-07", None, 0.5, "2020-01-08", "2020-02-06",
             legal=False, reason="state_unknown"),
    ]
    s = state_summary(_canon(rows))
    assert s["true"]["n"] == 1 and s["false"]["n"] == 1
    assert s["n_legal"] == 2
    assert s["delta"] == pytest.approx(-0.10, abs=EPS)


def test_real_b1_cross_check_against_independent_expectations():
    import json
    from pathlib import Path

    from lei_signal.research.factor_evidence.contract import FIXED_INPUT_IDENTITY
    from lei_signal.research.factor_evidence.observations import (
        load_b1_observations,
    )

    repo = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
    frame, schedule, _audit = load_b1_observations(repo, {
        "input_identity": FIXED_INPUT_IDENTITY})
    exp = json.loads((repo / "docs/experiments/raw/"
                      "factor-evidence-reliability-v1-2026-09-16/"
                      "expectations.json").read_text(encoding="utf-8"))
    s = state_summary(frame)
    assert s["delta"] == pytest.approx(exp["full_period"]["delta"], abs=1e-12)
    assert s["true"]["n"] == 590 and s["false"]["n"] == 926
    assert s["true"]["aux_mean"] == pytest.approx(
        exp["full_period"]["aux"]["true"]["mean"], abs=1e-12)
    assert s["false"]["aux_worst"] == pytest.approx(
        exp["full_period"]["aux"]["false"]["worst"], abs=1e-12)
    y = year_stability(frame)
    for year, expect in exp["yearly"].items():
        got = y["years"][year]
        assert got["delta"] == pytest.approx(expect["delta"], abs=1e-12)
        assert got["true"]["n"] == expect["true"]["n"]
        assert got["false"]["n"] == expect["false"]["n"]
    assert y["sign_counts"] == {"positive": 2, "zero": 0, "negative": 5}
    for year, expect in exp["leave_one_year_out"].items():
        assert y["leave_one_year_out"][year]["delta"] == pytest.approx(
            expect["delta"], abs=1e-12)
    assert y["equal_weight_year_delta"]["mean_delta"] == pytest.approx(
        exp["equal_weight_year_mean"]["mean_delta"], abs=1e-12)
    assert y["equal_weight_year_delta"]["years"] == \
        exp["equal_weight_year_mean"]["years"]
    assert "2019" in y["partial_years"]


# ── 区间重叠审计（教学例：日序位置 0..25+） ─────────────────────────

def _sched_positions(n: int) -> pd.DataFrame:
    days = [d.strftime("%Y-%m-%d")
            for d in pd.bdate_range("2019-10-08", periods=n)]
    return pd.DataFrame({"session": days,
                         "in_window": [i < n - 8 for i in range(n)]})


def _row_by_pos(schedule, t, state, main):
    return _row(schedule["session"].iat[t], state, main,
                schedule["session"].iat[t + 1],
                schedule["session"].iat[t + 22])


def test_overlap_teaching_20_of_21_and_endpoint_only_share_zero():
    sched = _sched_positions(50)
    # 标签[1,22]（观察位置0）与[2,23]（观察位置1）：各21区间，共享20
    frame = _canon([_row_by_pos(sched, 0, True, 0.1),
                    _row_by_pos(sched, 1, False, -0.1)])
    a = overlap_audit(frame, sched, sched["session"].iat[0], 23)
    assert a["per_label_intervals"] == 21
    assert a["adjacent_pairs"] == 1
    assert a["adjacent_shared_histogram"] == {"20": 1}
    assert a["adjacent_shared_ratio"] == pytest.approx(20 / 21, abs=EPS)
    # [1,22] 与 [22,43]：共享价格点（位置22）但共享区间 0——点数≠区间数
    frame = _canon([_row_by_pos(sched, 0, True, 0.1),
                    _row_by_pos(sched, 21, False, -0.1)])
    a = overlap_audit(frame, sched, sched["session"].iat[0], 23)
    # 两行不相邻（位置0与21），相邻审计不存在；但全表统计把两个标签都计入
    assert a["adjacent_pairs"] == 0
    assert a["total_interval_refs"] == 42
    # 唯一区间：2..22 ∪ 23..43 = 42 个（0 共享）
    assert a["unique_intervals"] == 42
    assert a["reuse_ratio"] == pytest.approx(1.0, abs=EPS)


def test_overlap_real_b1_matches_independent_expectations():
    import json
    from pathlib import Path

    from lei_signal.research.factor_evidence.contract import (
        FIXED_INPUT_IDENTITY,
        FIXED_PARAMS,
    )
    from lei_signal.research.factor_evidence.observations import (
        load_b1_observations,
    )

    repo = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
    frame, schedule, _audit = load_b1_observations(repo, {
        "input_identity": FIXED_INPUT_IDENTITY})
    exp = json.loads((repo / "docs/experiments/raw/"
                      "factor-evidence-reliability-v1-2026-09-16/"
                      "expectations.json").read_text(encoding="utf-8"))
    a = overlap_audit(frame, schedule,
                      FIXED_PARAMS["overlap"]["sparse_anchor_session"],
                      FIXED_PARAMS["overlap"]["sparse_step"])
    e = exp["overlap"]
    assert a["total_interval_refs"] == e["total_interval_refs"]
    assert a["unique_intervals"] == e["unique_intervals"]
    assert a["reuse_ratio"] == pytest.approx(e["reuse_ratio"], abs=1e-12)
    assert a["adjacent_shared_histogram"] == {
        k: v for k, v in e["adjacent_shared_histogram"].items()}
    assert a["adjacent_pairs"] == e["adjacent_pairs"]
    # 主结果必须基于共同合法集合；全合法资料的 secondary 与主结果同值
    assert a["rows_audited"] == 1516
    assert a["illegal_rows_excluded"] == 0
    assert a["all_rows_with_endpoints"]["rows_audited"] == 1516
    assert a["sparse"]["expected_points"] == e["sparse"]["grid_points"]
    assert a["sparse"]["auditable_points"] == e["sparse"]["grid_points"]
    assert a["sparse"]["adjacent_shared_max"] == e["sparse"]["adjacent_shared_max"]
    assert a["sparse"]["adjacent_pairs"] == e["sparse"]["adjacent_pairs"]


def test_overlap_sparse_grid_no_shared_intervals_synthetic():
    sched = _sched_positions(80)  # 轴 = 前 72 个位置；网格应有 0/23/46/69
    rows = [_row_by_pos(sched, t, True, 0.1) for t in (0, 23, 46)]
    frame = _canon(rows)
    a = overlap_audit(frame, sched, sched["session"].iat[0], 23)
    assert a["sparse"]["expected_points"] == 4   # 轴上应有格点含 69
    assert a["sparse"]["auditable_points"] == 3  # 帧只给了 0/23/46
    assert a["sparse"]["reasons"] == {"missing_row": 1}
    assert a["sparse"]["adjacent_shared_max"] == 0


def test_overlap_rows_without_dates_and_illegal_rows():
    sched = _sched_positions(50)
    rows = [_row_by_pos(sched, 0, True, 0.1),
            _row_by_pos(sched, 1, False, -0.1)]
    # 非法行（有端点）：主结果排除，secondary 计入
    rows.append(_row_by_pos(sched, 2, True, 0.2).copy())
    rows[2]["legal"] = False
    rows[2]["legal_reason"] = "target_missing"
    frame = _canon(rows)
    a = overlap_audit(frame, sched, sched["session"].iat[0], 23)
    assert a["rows_audited"] == 2
    assert a["illegal_rows_excluded"] == 1
    assert a["legal_missing_endpoints"] == 0
    assert a["all_rows_with_endpoints"]["rows_audited"] == 3
    # 非法行保留原轴位置：pos0-pos1 相邻对进入主结果（都合法）
    assert a["adjacent_shared_histogram"] == {"20": 1}


def test_overlap_primary_legal_set_hand_example():
    """主控R2手算例：合法标签 + 一行排除 + 缺端点 + 仅接触端点。"""
    sched = _sched_positions(80)
    rows = [
        _row_by_pos(sched, 0, True, 0.1),    # 合法标签 [1,22]
        _row_by_pos(sched, 1, True, 0.2),    # 非法行（有端点，被主结果排除）
        _row_by_pos(sched, 2, False, -0.1),  # 合法但缺端点
        _row_by_pos(sched, 21, True, 0.3),   # 合法标签 [22,43]（仅接触端点）
    ]
    rows[1]["legal"] = False
    rows[1]["legal_reason"] = "state_unknown"
    rows[2]["e_date"] = None
    rows[2]["x_date"] = None
    frame = _canon(rows)
    a = overlap_audit(frame, sched, sched["session"].iat[0], 23)
    # 主结果=共同合法集合：只有 pos0 与 pos21
    assert a["rows_audited"] == 2
    assert a["illegal_rows_excluded"] == 1
    assert a["legal_missing_endpoints"] == 1
    assert a["total_interval_refs"] == 42
    assert a["unique_intervals"] == 42  # [1,22] 与 [22,43] 共享价格点但 0 区间
    assert a["reuse_ratio"] == pytest.approx(1.0, abs=1e-12)
    assert a["adjacent_pairs"] == 0  # pos0 与 pos21 不相邻
    # secondary=所有有端点行（含非法行），独立命名不混称
    sec = a["all_rows_with_endpoints"]
    assert sec["rows_audited"] == 3
    assert sec["adjacent_shared_histogram"] == {"20": 1}  # pos0-pos1 相邻


def test_overlap_sparse_classifies_expected_points():
    """稀疏锚点按原轴推进：应有格点 / 可审计格点 / 缺失原因分开。"""
    sched = _sched_positions(120)  # 轴 = 前 112 个位置
    rows = [_row_by_pos(sched, t, True, 0.1) for t in (0, 23, 46, 69, 92)]
    rows[1]["legal"] = False           # 23 号格点非法
    rows[1]["legal_reason"] = "target_missing"
    rows[2]["e_date"] = None           # 46 号格点缺端点
    rows[2]["x_date"] = None
    frame = _canon(rows)
    a = overlap_audit(frame, sched, sched["session"].iat[0], 23)
    sp = a["sparse"]
    assert sp["expected_points"] == 5      # 0,23,46,69,92 沿轴推进
    assert sp["auditable_points"] == 3     # 0,69,92
    assert sp["reasons"] == {"illegal_row": 1, "missing_endpoints": 1}
    assert sp["adjacent_pairs"] == 2       # (0,69),(69,92)
    assert sp["adjacent_shared_max"] == 0


def test_validate_rejects_multiple_symbols():
    f = _teaching_frame()
    f.loc[0, "symbol"] = "OTHER"
    with pytest.raises(ValueError, match="多标的|symbol"):
        from lei_signal.research.factor_evidence.observations import (
            validate_observations,
        )
        validate_observations(f, _sched_positions(60).assign(
            in_window=[True] * 60))
