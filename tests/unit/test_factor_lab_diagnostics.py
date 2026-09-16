"""factor_lab 诊断层单测：横截面 IC、二元状态、共同宽度分流、q=2 分组。"""
from __future__ import annotations

import pandas as pd
import pytest

from lei_signal.research.factor_lab.contracts import (
    IdentityFormatError,
    ResearchBatch,
    build_metadata,
)
from lei_signal.research.factor_lab.diagnostics import evaluate_predictive


def make_protocol(**overrides):
    protocol = {
        "protocol_id": "test-protocol",
        "version": "0.0.1",
        "kind": "predictive_diagnostic",
        "data_mode": "synthetic",
        "synthetic": True,
        "timezone": "Asia/Shanghai",
        "evaluation_cutoff": "2030-01-01T15:00:00+08:00",
        "diagnostics": {"type": "cross_section_ic"},
    }
    protocol.update(overrides)
    return protocol


def fake_card(type_="feature", unit="fraction"):
    return {
        "type": type_,
        "definition": {"unit": unit},
        "status": {"definition_clarity": "explicit", "implementation": "test",
                   "effectiveness": "no_evidence"},
    }


def make_batch(values: pd.DataFrame, *, entity_axis="instrument", value_type="continuous",
               type_="feature", unit="fraction") -> ResearchBatch:
    metadata = build_metadata(
        reference="test.ref@1.0.0", card=fake_card(type_, unit), card_kind="registered",
        protocol=make_protocol(), entity_axis=entity_axis, value_type=value_type,
        data_identity={}, code_identity={}, calendar={"timezone": "Asia/Shanghai"},
        time_evidence={},
    )
    return ResearchBatch(values, metadata, [])


def day(n: int) -> pd.Timestamp:
    return pd.Timestamp("2024-01-01") + pd.Timedelta(days=n)


def values_frame(rows: list[tuple[int, str, float | None, str | None]]) -> pd.DataFrame:
    return pd.DataFrame([
        {"observation_date": day(d), "entity_id": e, "value": v, "missing_reason": r}
        for d, e, v, r in rows
    ])


def targets_frame(rows: list[tuple[int, str, float]], *, mature: bool = True,
                  label_offset: int = 1, window: int = 5,
                  naive_available: bool = False) -> pd.DataFrame:
    out = []
    for d, e, t in rows:
        start = day(d + label_offset)
        end = day(d + label_offset + window)
        available = pd.Timestamp(end)
        available = available.tz_localize("Asia/Shanghai") + pd.Timedelta(hours=15)
        if naive_available:
            available = available.tz_localize(None)
        out.append({
            "observation_date": day(d), "entity_id": e, "label_start": start,
            "label_end": end, "label_available_at": available, "target": t,
        })
    return pd.DataFrame(out)


class TestCrossSectionIC:
    def test_perfect_inverse_scores(self):
        values = values_frame([(0, "a", 1.0, None), (0, "b", 2.0, None), (0, "c", 3.0, None)])
        targets = targets_frame([(0, "a", 3.0), (0, "b", 2.0), (0, "c", 1.0)])
        result = evaluate_predictive(make_batch(values), targets, protocol=make_protocol())
        period = result["periods"][0]
        assert period["ic"] == pytest.approx(-1.0)
        assert period["n"] == 3

    def test_perfect_aligned_scores(self):
        values = values_frame([(0, "a", 1.0, None), (0, "b", 2.0, None), (0, "c", 3.0, None)])
        targets = targets_frame([(0, "a", 1.0), (0, "b", 2.0), (0, "c", 3.0)])
        result = evaluate_predictive(make_batch(values), targets, protocol=make_protocol())
        assert result["periods"][0]["ic"] == pytest.approx(1.0)

    def test_constant_scores_return_null_with_reason(self):
        values = values_frame([(0, "a", 5.0, None), (0, "b", 5.0, None), (0, "c", 5.0, None)])
        targets = targets_frame([(0, "a", 1.0), (0, "b", 2.0), (0, "c", 3.0)])
        result = evaluate_predictive(make_batch(values), targets, protocol=make_protocol())
        period = result["periods"][0]
        assert period["ic"] is None
        assert period["reason"] == "constant_rank"
        assert period["n"] == 3

    def test_nan_exclusion_leaving_two_pairs_returns_null(self):
        values = values_frame([
            (0, "a", 1.0, None), (0, "b", None, "price_missing"),
            (0, "c", 3.0, None), (0, "d", 2.0, None),
        ])
        targets = targets_frame([(0, "a", 1.0), (0, "b", 2.0), (0, "c", 3.0), (0, "d", 2.5)])
        result = evaluate_predictive(make_batch(values), targets, protocol=make_protocol())
        period = result["periods"][0]
        assert period["n"] == 3
        assert period["ic"] is not None
        assert period["excluded_counts"] == {"value_missing:price_missing": 1}
        # 只剩2对时为缺失
        values2 = values_frame([
            (0, "a", 1.0, None), (0, "b", 2.0, None), (0, "c", None, "price_missing"),
            (0, "d", None, "price_missing"),
        ])
        targets2 = targets_frame([(0, "a", 1.0), (0, "b", 2.0), (0, "c", 3.0), (0, "d", 4.0)])
        result2 = evaluate_predictive(make_batch(values2), targets2,
                                      protocol=make_protocol())
        period2 = result2["periods"][0]
        assert period2["n"] == 2
        assert period2["ic"] is None
        assert period2["reason"] == "fewer_than_min_pairs"

    def test_empty_date_kept_with_n_zero(self):
        values = values_frame([
            (0, "a", 1.0, None), (0, "b", 2.0, None), (0, "c", 3.0, None),
            (1, "a", None, "price_missing"), (1, "b", None, "price_missing"),
            (1, "c", None, "price_missing"),
        ])
        targets = targets_frame([
            (0, "a", 1.0), (0, "b", 2.0), (0, "c", 3.0),
            (1, "a", 1.0), (1, "b", 2.0), (1, "c", 3.0),
        ])
        result = evaluate_predictive(make_batch(values), targets, protocol=make_protocol())
        assert result["n_periods"] == 2
        empty = result["periods"][1]
        assert empty["n"] == 0
        assert empty["ic"] is None

    def test_ties_use_average_rank(self):
        # 分数 [1,1,2]：并列平均名次后与目标 [10,20,30] 的相关
        values = values_frame([(0, "a", 1.0, None), (0, "b", 1.0, None), (0, "c", 2.0, None)])
        targets = targets_frame([(0, "a", 10.0), (0, "b", 20.0), (0, "c", 30.0)])
        result = evaluate_predictive(make_batch(values), targets, protocol=make_protocol())
        # 名次 v=[1.5,1.5,3]，t=[1,2,3] → Pearson ≈ 0.866
        assert result["periods"][0]["ic"] == pytest.approx(0.8660254, rel=1e-6)

    def test_immature_target_excluded(self):
        protocol = make_protocol(evaluation_cutoff="2024-01-05T15:00:00+08:00")
        values = values_frame([(0, "a", 1.0, None), (0, "b", 2.0, None), (0, "c", 3.0, None)])
        targets = targets_frame([(0, "a", 1.0), (0, "b", 2.0), (0, "c", 3.0)])
        result = evaluate_predictive(make_batch(values), targets, protocol=protocol)
        period = result["periods"][0]
        assert period["ic"] is None
        assert period["excluded_counts"].get("label_not_mature_by_cutoff") == 3

    def test_label_window_must_start_after_observation(self):
        values = values_frame([(0, "a", 1.0, None), (0, "b", 2.0, None), (0, "c", 3.0, None)])
        targets = targets_frame([(0, "a", 1.0), (0, "b", 2.0), (0, "c", 3.0)],
                                label_offset=0)
        result = evaluate_predictive(make_batch(values), targets, protocol=make_protocol())
        period = result["periods"][0]
        assert period["excluded_counts"].get("label_window_not_after_observation") == 3

    def test_naive_label_available_at_rejected(self):
        values = values_frame([(0, "a", 1.0, None), (0, "b", 2.0, None), (0, "c", 3.0, None)])
        targets = targets_frame([(0, "a", 1.0), (0, "b", 2.0), (0, "c", 3.0)],
                                naive_available=True)
        with pytest.raises(IdentityFormatError, match="timezone-aware"):
            evaluate_predictive(make_batch(values), targets, protocol=make_protocol())

    def test_quantile_groups_q2_ties_not_split(self):
        # 分数 [1,1,2,3]：不同分数[1,2,3]中位数=2 → low={a,b}, middle={c}剔除, high={d}
        values = values_frame([
            (0, "a", 1.0, None), (0, "b", 1.0, None), (0, "c", 2.0, None), (0, "d", 3.0, None),
        ])
        targets = targets_frame([
            (0, "a", 1.0), (0, "b", 1.5), (0, "c", 2.0), (0, "d", 4.0),
        ])
        protocol = make_protocol(diagnostics={"type": "cross_section_ic",
                                              "quantiles": {"q": 2}})
        result = evaluate_predictive(make_batch(values), targets, protocol=protocol)
        groups = result["quantile_groups_q2"][0]
        assert groups["status"] == "ok"
        assert groups["groups"]["low"]["entities"] == ["a", "b"]
        assert groups["groups"]["high"]["entities"] == ["d"]
        assert groups["excluded_middle_entities"] == ["c"]
        # q=3 明确拒绝
        with pytest.raises(IdentityFormatError, match="q=2"):
            evaluate_predictive(make_batch(values), targets,
                                protocol=make_protocol(
                                    diagnostics={"type": "cross_section_ic",
                                                 "quantiles": {"q": 3}}))


class TestBranching:
    def test_universe_cross_section_ic_not_applicable(self):
        values = values_frame([(0, "synthetic_idx", 0.67, None)])
        batch = make_batch(values, entity_axis="universe", value_type="fraction_bounded")
        result = evaluate_predictive(batch, pd.DataFrame(columns=[
            "observation_date", "entity_id", "label_start", "label_end",
            "label_available_at", "target"]), protocol=make_protocol())
        assert result["status"] == "not_applicable"

    def test_boolean_cross_section_ic_not_applicable(self):
        values = values_frame([(0, "a", 1, None), (0, "b", 0, None), (0, "c", 1, None)])
        batch = make_batch(values, value_type="boolean")
        targets = targets_frame([(0, "a", 1.0), (0, "b", 2.0), (0, "c", 3.0)])
        result = evaluate_predictive(batch, targets, protocol=make_protocol())
        assert result["status"] == "not_applicable"
        assert "state_outcomes" in result["reason"]

    def test_state_outcomes_on_continuous_not_applicable(self):
        values = values_frame([(0, "a", 1.0, None), (0, "b", 2.0, None), (0, "c", 3.0, None)])
        batch = make_batch(values, value_type="continuous")
        targets = targets_frame([(0, "a", 1.0), (0, "b", 2.0), (0, "c", 3.0)])
        result = evaluate_predictive(
            batch, targets,
            protocol=make_protocol(diagnostics={"type": "state_outcomes"}))
        assert result["status"] == "not_applicable"


class TestStateOutcomes:
    def test_true_false_groups_with_not_ready_listed(self):
        values = values_frame([
            (0, "x", 1, None), (1, "x", 1, None),
            (0, "y", 0, None), (1, "y", 0, None),
            (0, "w", 1, None), (1, "w", 0, None),
            (2, "z", None, "warmup_not_ready"),
        ])
        batch = make_batch(values, value_type="boolean", type_="state_signal", unit="boolean")
        targets = targets_frame([
            (0, "x", 0.10), (1, "x", 0.20),
            (0, "y", 0.02), (1, "y", -0.01),
            (0, "w", 0.10), (1, "w", 0.02),
            (2, "z", 99.0),
        ])
        result = evaluate_predictive(
            batch, targets,
            protocol=make_protocol(kind="state_diagnostic",
                                   diagnostics={"type": "state_outcomes"}))
        entities = {e["entity_id"]: e for e in result["entities"]}
        x = entities["x"]
        assert x["groups"]["state_true"]["n"] == 2
        assert x["groups"]["state_true"]["mean_target"] == pytest.approx(0.15)
        assert x["groups"]["state_false"]["n"] == 0
        assert x["mean_difference_true_minus_false"] is None
        z = entities["z"]
        assert z["n_usable"] == 0
        assert z["excluded_counts"] == {"value_missing:warmup_not_ready": 1}
        # y 只有假状态：差额 None；w 真假都有：差额=0.10-0.02
        assert entities["y"]["mean_difference_true_minus_false"] is None
        w = entities["w"]
        assert w["groups"]["state_true"]["mean_target"] == pytest.approx(0.10)
        assert w["groups"]["state_false"]["mean_target"] == pytest.approx(0.02)
        assert w["mean_difference_true_minus_false"] == pytest.approx(0.08)


class TestUniverseTimeSeries:
    def test_time_series_state_descriptive(self):
        # 宽度序列逐日与单一目标实体的结果对照（跨日期，不是横截面复制）
        values = values_frame([
            (0, "synthetic_idx", 0.5, None),
            (1, "synthetic_idx", 0.6, None),
            (2, "synthetic_idx", 0.7, None),
            (3, "synthetic_idx", 0.8, None),
        ])
        batch = make_batch(values, entity_axis="universe", value_type="fraction_bounded",
                           type_="state_signal")
        targets = targets_frame([
            (0, "m1", 0.01), (1, "m1", 0.02), (2, "m1", 0.03), (3, "m1", 0.04),
        ])
        protocol = make_protocol(
            diagnostics={"type": "time_series_state", "target_entities": ["m1"]})
        result = evaluate_predictive(batch, targets, protocol=protocol)
        entry = result["entities"][0]
        assert entry["status"] == "descriptive_only"
        assert entry["n"] == 4
        assert entry["pearson_over_time"] == pytest.approx(1.0)
        assert (result["summary_caveats"]
                ["correlation_robust_confidence_interval"] == "not_implemented")

    def test_time_series_requires_explicit_entities(self):
        values = values_frame([(0, "synthetic_idx", 0.5, None)])
        batch = make_batch(values, entity_axis="universe", value_type="fraction_bounded")
        with pytest.raises(IdentityFormatError, match="target_entities"):
            evaluate_predictive(batch, pd.DataFrame(columns=[
                "observation_date", "entity_id", "label_start", "label_end",
                "label_available_at", "target"]),
                protocol=make_protocol(diagnostics={"type": "time_series_state"}))

    def test_unknown_target_entity_reported_insufficient(self):
        values = values_frame([(0, "synthetic_idx", 0.5, None)])
        batch = make_batch(values, entity_axis="universe", value_type="fraction_bounded")
        protocol = make_protocol(
            diagnostics={"type": "time_series_state", "target_entities": ["ghost"]})
        targets = targets_frame([(0, "m1", 0.01)])
        result = evaluate_predictive(batch, targets, protocol=protocol)
        assert result["entities"][0]["status"] == "insufficient"


class TestTimeQualificationR1:
    """集中返修 R1：时间资格必须实际控制统计，不能只加警告。"""

    @pytest.mark.parametrize("bad_value", [pd.NaT, None])
    def test_unknown_label_available_at_excluded_from_statistics(self, bad_value):
        values = values_frame([(0, "a", 1.0, None), (0, "b", 2.0, None), (0, "c", 3.0, None)])
        targets = targets_frame([(0, "a", 1.0), (0, "b", 2.0), (0, "c", 3.0)])
        targets["label_available_at"] = bad_value
        result = evaluate_predictive(make_batch(values), targets, protocol=make_protocol())
        period = result["periods"][0]
        assert period["n"] == 0
        assert period["ic"] is None
        assert period["excluded_counts"].get("label_available_unknown") == 3

    def test_label_time_inverted_rejected(self):
        values = values_frame([(0, "a", 1.0, None), (0, "b", 2.0, None), (0, "c", 3.0, None)])
        targets = targets_frame([(0, "a", 1.0), (0, "b", 2.0), (0, "c", 3.0)])
        targets["label_start"] = targets["label_end"] + pd.Timedelta(days=1)
        with pytest.raises(IdentityFormatError, match="inverted"):
            evaluate_predictive(make_batch(values), targets, protocol=make_protocol())

    def test_non_finite_values_excluded(self):
        values = values_frame([(0, "a", float("inf"), None), (0, "b", 2.0, None),
                               (0, "c", 3.0, None)])
        targets = targets_frame([(0, "a", 1.0), (0, "b", 2.0), (0, "c", 3.0)])
        result = evaluate_predictive(make_batch(values), targets, protocol=make_protocol())
        period = result["periods"][0]
        # 一行非有限 → 只剩2个干净行 < min_pairs(3) → 无统计值
        assert period["n"] == 2
        assert period["ic"] is None
        assert period["reason"] == "fewer_than_min_pairs"
        assert period["excluded_counts"].get("value_not_finite") == 1

    def test_same_day_14_vs_16_known_boundary(self):
        values = values_frame([(0, "a", 1.0, None), (0, "b", 2.0, None), (0, "c", 3.0, None)])
        targets = targets_frame([(0, "a", 1.0), (0, "b", 2.0), (0, "c", 3.0)])
        # 标签窗结束于01-07（观察日+1起、5天窗）；评价截止=同日15:00
        protocol = make_protocol(evaluation_cutoff="2024-01-07T15:00:00+08:00")
        # 同日14:00可知 → 参与统计
        targets["label_available_at"] = pd.Timestamp("2024-01-07T14:00:00+08:00")
        ok = evaluate_predictive(make_batch(values), targets, protocol=protocol)
        assert ok["periods"][0]["ic"] is not None
        # 同日16:00可知 → 晚于截止，剔除
        targets["label_available_at"] = pd.Timestamp("2024-01-07T16:00:00+08:00")
        late = evaluate_predictive(make_batch(values), targets, protocol=protocol)
        assert late["periods"][0]["n"] == 0
        assert late["periods"][0]["excluded_counts"].get("label_unknown_at_evaluation") == 3

    def test_declared_min_pairs_actually_applied(self):
        values = values_frame([(0, "a", 1.0, None), (0, "b", 2.0, None), (0, "c", 3.0, None)])
        targets = targets_frame([(0, "a", 1.0), (0, "b", 2.0), (0, "c", 3.0)])
        protocol = make_protocol(diagnostics={"type": "cross_section_ic", "min_pairs": 5})
        result = evaluate_predictive(make_batch(values), targets, protocol=protocol)
        period = result["periods"][0]
        assert result["min_pairs"] == 5
        assert period["n"] == 3
        assert period["ic"] is None
        assert period["reason"] == "fewer_than_min_pairs"

    def test_feature_lag_excluded_from_statistics(self):
        values = values_frame([(0, "a", 1.0, None), (0, "b", 2.0, None), (0, "c", 3.0, None)])
        targets = targets_frame([(0, "a", 1.0), (0, "b", 2.0), (0, "c", 3.0)])
        protocol = make_protocol(diagnostics={
            "type": "cross_section_ic", "feature_available_lag_days": 1})
        result = evaluate_predictive(make_batch(values), targets, protocol=protocol)
        period = result["periods"][0]
        assert period["n"] == 0
        assert period["excluded_counts"].get("feature_not_available_by_decision_time") == 3

    def test_observation_dates_without_targets_kept_with_zero_n(self):
        values = values_frame([
            (0, "a", 1.0, None), (0, "b", 2.0, None), (0, "c", 3.0, None),
            (1, "a", 1.0, None), (1, "b", 2.0, None), (1, "c", 3.0, None),
        ])
        targets = targets_frame([(0, "a", 1.0), (0, "b", 2.0), (0, "c", 3.0)])
        result = evaluate_predictive(make_batch(values), targets, protocol=make_protocol())
        assert result["n_periods"] == 2
        empty = result["periods"][1]
        assert empty["n"] == 0
        assert empty["ic"] is None
        assert empty["excluded_counts"].get("no_target_row") == 3


class TestS3DiagnosticsConsistency:
    """最后一轮 S3：诊断入口与审计共享同一逐行合法集合。"""

    def test_diagnostic_maturity_uses_decision_moment(self):
        values = values_frame([(0, "a", 1.0, None), (0, "b", 2.0, None), (0, "c", 3.0, None)])
        targets = targets_frame([(0, "a", 1.0), (0, "b", 2.0), (0, "c", 3.0)])
        # 标签结束于01-07；截止同日14:00 → 未成熟剔除；15:00 → 成熟
        early = make_protocol(evaluation_cutoff="2024-01-07T14:00:00+08:00")
        r1 = evaluate_predictive(make_batch(values), targets, protocol=early)
        assert r1["periods"][0]["n"] == 0
        assert r1["periods"][0]["excluded_counts"].get("label_not_mature_by_cutoff") == 3
        ontime = make_protocol(evaluation_cutoff="2024-01-07T15:00:00+08:00")
        r2 = evaluate_predictive(make_batch(values), targets, protocol=ontime)
        assert r2["periods"][0]["ic"] is not None
