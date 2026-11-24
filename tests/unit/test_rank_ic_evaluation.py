"""Synthetic contract tests only: do not evaluate or alter sealed PPO results."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from lei_signal.research.factor_lab import rank_ic_evaluation as module
from lei_signal.research.factor_lab.rank_ic_evaluation import (
    RankICCheckpoint,
    RankICColumns,
    RankICContract,
    RankICLabelWindow,
    RankICModelFold,
    RankICRealBinding,
    RankICScore,
    RankICUniverse,
    frame_sha256,
    session_sequence_sha256,
)
from lei_signal.research.factor_lab.rank_ic_evaluation import (
    evaluate_frozen_rank_ic as run_evaluation,
)


@pytest.fixture
def contract():
    return RankICContract(
        contract_id="synthetic-only/1",
        data_mode="synthetic",
        purpose="return_ranking",
        label_semantics="higher_return",
        scores=(
            RankICScore(
                "raw", "raw_value", "raw_factor", "higher_score_higher_label", "synthetic.raw@1"
            ),
        ),
        universes=(RankICUniverse("stocks", "stock", ("A", "B", "C", "D")),),
        checkpoints=(RankICCheckpoint("2025-02-07T07:00:00Z", "fold1"),),
        window_start="2025-02-01T00:00:00Z",
        window_end="2025-03-31T07:00:00Z",
        evaluation_as_of="2025-03-31T08:00:00Z",
        temporal_basis="timestamp",
        availability_context="strict_point_in_time",
        min_assets=3,
        score_mask_policy="common",
        time_weighting="equal_checkpoint",
        label_horizon="20 trading sessions",
        label_overlap="overlapping",
        label_horizon_session_intervals=20,
    )


def model_fold():
    return RankICModelFold(
        fold="fold1",
        train_start="2023-01-01T07:00:00Z",
        train_end="2025-01-31T07:00:00Z",
        training_labels_end="2025-01-31T07:00:00Z",
        transform_fit_end="2025-01-31T07:00:00Z",
        evaluation_start="2025-02-01T07:00:00Z",
        evaluation_end="2025-03-31T07:00:00Z",
        model_identity="synthetic saved model",
        transform_identity="synthetic saved transform",
    )


def freeze_contract(c):
    """Freeze synthetic expected windows from a declared fake calendar, not labels."""
    if c.label_windows:
        return c
    windows = []
    for point in c.checkpoints:
        timestamp = pd.Timestamp(point.at)
        local_day = (
            timestamp.tz_convert(c.market_timezone).tz_localize(None).normalize()
            if timestamp.tzinfo is not None
            else timestamp
        )
        # Test fixtures only. This is explicitly not an exchange calendar or a real-data adapter.
        days = tuple(pd.bdate_range(local_day, periods=22).strftime("%Y-%m-%d"))

        def boundary(day):
            if c.temporal_basis == "timestamp":
                return (
                    pd.Timestamp(day).tz_localize(c.market_timezone) + pd.Timedelta(hours=15)
                ).isoformat()
            return day

        for universe in c.universes:
            windows.append(
                RankICLabelWindow(
                    checkpoint=point.at,
                    universe=universe.name,
                    start=boundary(days[1]),
                    end=boundary(days[21]),
                    sessions=days,
                    start_session_offset=1,
                    end_session_offset=21,
                    calendar_reference="synthetic fake-calendar fixture",
                    session_sequence_sha256=session_sequence_sha256(days),
                )
            )
    return replace(c, label_windows=tuple(windows))


def evaluate_frozen_rank_ic(scores, labels, c):
    return run_evaluation(scores, labels, freeze_contract(c))


def frames(c, values=None, outcomes=None):
    c = freeze_contract(c)
    scores, labels = [], []
    for point in c.checkpoints:
        date = pd.Timestamp(point.at)
        for universe in c.universes:
            window = next(
                w
                for w in c.label_windows
                if w.checkpoint == point.at and w.universe == universe.name
            )
            for i, asset in enumerate(universe.assets):
                scores.append(
                    {
                        "asset_id": asset,
                        "asset_type": universe.asset_type,
                        "checkpoint_at": point.at,
                        "computed_through_at": point.at,
                        "source_available_at": (
                            (date - pd.Timedelta(minutes=1)).isoformat()
                            if c.temporal_basis == "timestamp"
                            else None
                        ),
                        "raw_value": float(values[i] if values is not None else i + 1),
                        "model_value": float(i + 1),
                    }
                )
                labels.append(
                    {
                        "asset_id": asset,
                        "checkpoint_at": point.at,
                        "forward_return": float(outcomes[i] if outcomes is not None else i + 1),
                        "label_start_at": window.start,
                        "label_end_at": window.end,
                        "label_available_at": (
                            (pd.Timestamp(window.end) + pd.Timedelta(hours=1)).isoformat()
                            if c.temporal_basis == "timestamp"
                            else None
                        ),
                        "label_quality_valid": True,
                    }
                )
    return pd.DataFrame(scores), pd.DataFrame(labels)


def periodic_value(result):
    return result.periodic.iloc[0]["rank_ic"]


@pytest.mark.parametrize("values, expected", [([1, 2, 3, 4], 1), ([4, 3, 2, 1], -1)])
def test_perfect_and_reversed_rankings(contract, values, expected):
    scores, labels = frames(contract, values=values)
    result = evaluate_frozen_rank_ic(scores, labels, contract)
    assert periodic_value(result) == pytest.approx(expected)
    assert result.summary.iloc[0]["mean_rank_ic"] == pytest.approx(expected)
    assert result.summary.iloc[0]["asset_coverage"] == 1
    assert result.metadata["live_qualified"] is False


def test_exact_average_ties_without_jitter(contract):
    scores, labels = frames(contract, values=[1, 1, 3, 4])
    result = evaluate_frozen_rank_ic(scores, labels, contract)
    assert periodic_value(result) == pytest.approx(np.sqrt(0.9))
    assert scores["raw_value"].tolist() == [1, 1, 3, 4]


@pytest.mark.parametrize(
    "field, reason", [("raw_value", "constant_score"), ("forward_return", "constant_label")]
)
def test_constants_are_undefined_not_zero(contract, field, reason):
    scores, labels = frames(contract)
    (scores if field == "raw_value" else labels)[field] = 0.0
    result = evaluate_frozen_rank_ic(scores, labels, contract)
    assert periodic_value(result) is None
    assert result.periodic.iloc[0]["undefined_reason"] == reason
    assert result.summary.iloc[0]["mean_rank_ic"] is None


def test_no_eligible_assets_is_undefined_with_coverage(contract):
    scores, labels = frames(contract)
    result = evaluate_frozen_rank_ic(scores.iloc[:0], labels.iloc[:0], contract)
    row = result.periodic.iloc[0]
    assert row["eligible_assets"] == 0 and row["expected_assets"] == 4
    assert row["asset_coverage"] == 0 and row["rank_ic"] is None
    assert row["undefined_reason"] == "fewer_than_min_assets"
    assert len(result.exclusions) == 4


def test_two_assets_keep_existing_backend_floor_and_explicit_reason(contract):
    c = replace(contract, universes=(RankICUniverse("two", "stock", ("A", "B")),))
    scores, labels = frames(c)
    result = evaluate_frozen_rank_ic(scores, labels, c)
    assert periodic_value(result) is None
    assert result.periodic.iloc[0]["undefined_reason"] == "fewer_than_min_assets"
    assert bool(result.periodic.iloc[0]["thin_cross_section"])
    with pytest.raises(ValueError, match="existing backend floor"):
        evaluate_frozen_rank_ic(scores, labels, replace(c, min_assets=2))


def test_missing_values_are_never_filled(contract):
    scores, labels = frames(contract)
    scores.loc[0, "raw_value"] = np.nan
    labels.loc[1, "forward_return"] = np.nan
    result = evaluate_frozen_rank_ic(scores, labels, contract)
    assert result.periodic.iloc[0]["eligible_assets"] == 2
    assert periodic_value(result) is None
    assert np.isnan(scores.loc[0, "raw_value"])
    assert "score_missing_or_nonfinite" in result.exclusions.iloc[0]["reasons"]


def test_same_asset_different_weeks_never_pools_dates(contract):
    c = replace(
        contract,
        checkpoints=contract.checkpoints + (RankICCheckpoint("2025-02-14T07:00:00Z", "fold1"),),
    )
    scores, labels = frames(c)
    scores.loc[4:, "raw_value"] = [4, 3, 2, 1]
    result = evaluate_frozen_rank_ic(scores, labels, c)
    assert result.periodic["eligible_assets"].tolist() == [4, 4]
    assert result.periodic["rank_ic"].tolist() == pytest.approx([1, -1])
    assert result.summary.iloc[0]["mean_rank_ic"] == pytest.approx(0)


@pytest.mark.parametrize(
    "column,value,reason",
    [
        ("source_available_at", "2025-02-07T07:01:00Z", "source_not_yet_available"),
        ("computed_through_at", "2025-02-10T07:00:00Z", "feature_computed_from_future"),
        ("label_start_at", "2025-02-07T07:00:00Z", "label_not_strictly_forward"),
        ("label_end_at", "2025-04-01T07:00:00Z", "label_not_mature_in_fixed_window"),
        ("label_available_at", "2025-04-01T07:00:00Z", "label_not_yet_available_to_evaluator"),
        ("label_quality_valid", False, "label_quality_invalid"),
    ],
)
def test_leakage_and_maturity_masks(contract, column, value, reason):
    scores, labels = frames(contract)
    (scores if column in scores else labels).loc[0, column] = value
    result = evaluate_frozen_rank_ic(scores, labels, contract)
    assert result.periodic.iloc[0]["eligible_assets"] == 3
    assert reason in result.exclusions.iloc[0]["reasons"]


def test_stock_and_etf_universes_stay_separate(contract):
    c = replace(
        contract,
        universes=contract.universes + (RankICUniverse("etfs", "etf", ("E", "F", "G", "H")),),
    )
    scores, labels = frames(c)
    scores.loc[4:, "raw_value"] = [4, 3, 2, 1]
    result = evaluate_frozen_rank_ic(scores, labels, c)
    assert result.periodic["asset_type"].tolist() == ["stock", "etf"]
    assert result.periodic["eligible_assets"].tolist() == [4, 4]
    assert result.periodic["rank_ic"].tolist() == pytest.approx([1, -1])


def test_class_mismatch_is_explicit(contract):
    scores, labels = frames(contract)
    scores.loc[0, "asset_type"] = "etf"
    result = evaluate_frozen_rank_ic(scores, labels, contract)
    assert result.periodic.iloc[0]["eligible_assets"] == 3
    assert "asset_type_mismatch" in result.exclusions.iloc[0]["reasons"]


def test_future_labels_must_be_separate(contract):
    scores, labels = frames(contract)
    scores["forward_return"] = labels["forward_return"]
    with pytest.raises(ValueError, match="evaluation-only sidecar"):
        evaluate_frozen_rank_ic(scores, labels, contract)


def test_join_is_explicit_keyed_and_inputs_unchanged(contract):
    scores, labels = frames(contract)
    before_scores, before_labels = scores.copy(deep=True), labels.copy(deep=True)
    shuffled = labels.iloc[::-1].set_axis([50, 40, 30, 20])
    result = evaluate_frozen_rank_ic(scores, shuffled, contract)
    assert periodic_value(result) == pytest.approx(1)
    pd.testing.assert_frame_equal(scores, before_scores)
    pd.testing.assert_frame_equal(labels, before_labels)


@pytest.mark.parametrize("which", ["scores", "labels"])
def test_duplicate_keys_fail_before_evaluation(contract, which):
    scores, labels = frames(contract)
    if which == "scores":
        scores = pd.concat([scores, scores.iloc[:1]])
    else:
        labels = pd.concat([labels, labels.iloc[:1]])
    with pytest.raises(ValueError, match="duplicate asset/checkpoint"):
        evaluate_frozen_rank_ic(scores, labels, contract)


def test_unknown_universe_members_fail(contract):
    scores, labels = frames(contract)
    scores.loc[0, "asset_id"] = "unknown"
    with pytest.raises(ValueError, match="outside the frozen universe"):
        evaluate_frozen_rank_ic(scores, labels, contract)


def test_strict_unknown_arrival_is_unverified(contract):
    scores, labels = frames(contract)
    scores["source_available_at"] = None
    result = evaluate_frozen_rank_ic(scores, labels, contract)
    assert result.periodic.iloc[0]["eligible_assets"] == 0
    assert all("source_arrival_unknown" in r for r in result.exclusions["reasons"])


def test_declared_retrospective_context_retains_unknown_arrivals(contract):
    c = replace(
        contract,
        availability_context="retrospective_after_close",
        source_evidence="synthetic approved-source fixture",
        after_close_scenario="completed bar at after-close research checkpoint",
    )
    scores, labels = frames(c)
    scores["source_available_at"] = None
    result = evaluate_frozen_rank_ic(scores, labels, c)
    assert periodic_value(result) == pytest.approx(1)
    assert result.periodic.iloc[0]["unknown_source_arrival_assets"] == 4
    assert result.metadata["live_qualified"] is False
    assert scores["source_available_at"].isna().all()


def test_retrospective_requires_explicit_source_and_scenario(contract):
    c = replace(contract, availability_context="retrospective_after_close")
    scores, labels = frames(c)
    with pytest.raises(ValueError, match="approved source evidence"):
        evaluate_frozen_rank_ic(scores, labels, c)


def test_session_labels_do_not_become_actual_timestamps(contract):
    c = replace(
        contract,
        temporal_basis="session_date_after_close",
        availability_context="retrospective_after_close",
        source_evidence="synthetic approved fixture",
        after_close_scenario="completed bars",
        checkpoints=(RankICCheckpoint("2025-02-07", "fold1"),),
        window_start="2025-02-01",
        window_end="2025-03-31",
        evaluation_as_of="2025-03-31",
    )
    scores, labels = frames(c)
    for field in ("label_start_at", "label_end_at"):
        labels[field] = pd.to_datetime(labels[field]).dt.strftime("%Y-%m-%d")
    labels["label_available_at"] = None
    result = evaluate_frozen_rank_ic(scores, labels, c)
    assert periodic_value(result) == pytest.approx(1)
    assert result.metadata["contract"]["temporal_basis"] == "session_date_after_close"
    assert result.metadata["live_qualified"] is False


def test_naive_timestamp_does_not_silently_acquire_utc(contract):
    scores, labels = frames(contract)
    scores.loc[0, "source_available_at"] = "2025-02-07T06:59:00"
    with pytest.raises(ValueError, match="explicit timezone"):
        evaluate_frozen_rank_ic(scores, labels, contract)


def test_direction_is_frozen_and_not_auto_flipped(contract):
    scores, labels = frames(contract, values=[4, 3, 2, 1])
    higher = evaluate_frozen_rank_ic(scores, labels, contract)
    lower_c = replace(
        contract, scores=(replace(contract.scores[0], direction="lower_score_higher_label"),)
    )
    lower = evaluate_frozen_rank_ic(scores, labels, lower_c)
    assert periodic_value(higher) == pytest.approx(-1)
    assert periodic_value(lower) == pytest.approx(-1)
    assert higher.periodic.iloc[0]["directional_rank_ic"] == pytest.approx(-1)
    assert lower.periodic.iloc[0]["directional_rank_ic"] == pytest.approx(1)
    assert higher.metadata["contract_sha256"] != lower.metadata["contract_sha256"]


def test_common_score_mask_has_explicit_raw_factor_model_score(contract):
    c = replace(
        contract,
        model_folds=(model_fold(),),
        scores=contract.scores
        + (RankICScore("model", "model_value", "model_score", "higher_score_higher_label"),),
    )
    scores, labels = frames(c)
    scores.loc[0, "model_value"] = np.nan
    common = evaluate_frozen_rank_ic(scores, labels, c)
    separate = evaluate_frozen_rank_ic(scores, labels, replace(c, score_mask_policy="per_score"))
    assert common.periodic["score_kind"].tolist() == ["raw_factor", "model_score"]
    assert common.periodic["eligible_assets"].tolist() == [3, 3]
    assert separate.periodic["eligible_assets"].tolist() == [4, 3]
    assert "other_declared_score_missing" in common.exclusions.iloc[0]["reasons"]


def test_exact_time_weighting_and_descriptive_dispersion(contract):
    c = replace(
        contract,
        checkpoints=contract.checkpoints
        + (
            RankICCheckpoint("2025-02-14T07:00:00Z", "fold1"),
            RankICCheckpoint("2025-02-21T07:00:00Z", "fold2"),
        ),
    )
    scores, labels = frames(c)
    scores.loc[8:, "raw_value"] = [4, 3, 2, 1]
    equal_period = evaluate_frozen_rank_ic(scores, labels, c)
    equal_fold = evaluate_frozen_rank_ic(
        scores, labels, replace(c, time_weighting="equal_fold_then_checkpoint")
    )
    assert equal_period.summary.iloc[0]["mean_rank_ic"] == pytest.approx(1 / 3)
    assert equal_fold.summary.iloc[0]["mean_rank_ic"] == pytest.approx(0)
    assert equal_fold.summary.iloc[0]["rank_ic_dispersion"] == pytest.approx(np.sqrt(1.6))
    assert equal_fold.metadata["label_dependence"] == "overlapping"
    assert not any("annual" in k or "significance" in k for k in equal_fold.summary.columns)


def test_constant_across_periods_has_no_infinite_icir(contract):
    c = replace(
        contract,
        checkpoints=contract.checkpoints + (RankICCheckpoint("2025-02-14T07:00:00Z", "fold1"),),
    )
    scores, labels = frames(c)
    result = evaluate_frozen_rank_ic(scores, labels, c)
    assert result.summary.iloc[0]["rank_ic_dispersion"] == pytest.approx(0)
    assert result.summary.iloc[0]["descriptive_icir"] is None


def test_missing_checkpoint_is_counted_in_coverage(contract):
    c = replace(
        contract,
        checkpoints=contract.checkpoints + (RankICCheckpoint("2025-02-14T07:00:00Z", "fold1"),),
    )
    scores, labels = frames(contract)
    result = evaluate_frozen_rank_ic(scores, labels, c)
    assert result.summary.iloc[0]["expected_periods"] == 2
    assert result.summary.iloc[0]["valid_periods"] == 1
    assert result.summary.iloc[0]["period_coverage"] == 0.5
    assert result.summary.iloc[0]["asset_coverage"] == 0.5


def test_risk_ranking_requires_explicit_risk_labels(contract):
    scores, labels = frames(contract)
    with pytest.raises(ValueError, match="explicit higher-risk labels"):
        evaluate_frozen_rank_ic(scores, labels, replace(contract, purpose="risk_ranking"))
    c = replace(contract, purpose="risk_ranking", label_semantics="higher_risk")
    assert periodic_value(evaluate_frozen_rank_ic(scores, labels, c)) == pytest.approx(1)


@pytest.mark.parametrize("purpose", ["trend_switch", "entry_trigger"])
def test_switches_and_entries_are_routed_without_low_ic_rejection(contract, purpose, monkeypatch):
    monkeypatch.setattr(module, "_existing_rank_ic", lambda *args: pytest.fail("must not call IC"))
    result = evaluate_frozen_rank_ic(
        pd.DataFrame(), pd.DataFrame(), replace(contract, purpose=purpose)
    )
    assert result.metadata["status"] == "metric_not_applicable"
    assert result.metadata["recommended_metrics"]
    assert result.periodic.empty


def test_same_week_different_checkpoints_cannot_be_pooled(contract):
    c = replace(
        contract,
        checkpoints=contract.checkpoints + (RankICCheckpoint("2025-02-06T07:00:00Z", "fold1"),),
    )
    scores, labels = frames(contract)
    with pytest.raises(ValueError, match="one fixed checkpoint per market-local ISO week"):
        evaluate_frozen_rank_ic(scores, labels, c)


def test_column_bindings_match_separate_qlib_session_sidecar(contract):
    c = replace(
        contract,
        columns=replace(
            RankICColumns(), asset_type="asset_class", label_checkpoint="observation_session_date"
        ),
    )
    scores, labels = frames(contract)
    scores = scores.rename(columns={"asset_type": "asset_class"})
    labels = labels.rename(columns={"checkpoint_at": "observation_session_date"})
    assert periodic_value(evaluate_frozen_rank_ic(scores, labels, c)) == pytest.approx(1)


def test_real_modes_are_not_synthetic_and_require_frozen_evidence(contract):
    scores, labels = frames(contract)
    real = replace(contract, data_mode="historical_reconstruction")
    with pytest.raises(ValueError, match="qualification, frozen protocol and approval"):
        evaluate_frozen_rank_ic(scores, labels, real)
    binding = RankICRealBinding(
        study_reference="synthetic test of real-mode guard; no real data",
        score_frame_sha256=frame_sha256(scores),
        label_frame_sha256=frame_sha256(labels),
        qualification_reference="synthetic qualification evidence",
        frozen_protocol_reference="synthetic frozen protocol",
        approval_reference="synthetic test authorization evidence",
        qualification_sha256="0" * 64,
        frozen_protocol_sha256="1" * 64,
        approval_sha256="2" * 64,
    )
    result = evaluate_frozen_rank_ic(scores, labels, replace(real, real_binding=binding))
    assert result.metadata["synthetic"] is False
    assert result.metadata["data_mode"] == "historical_reconstruction"
    scores.loc[0, "raw_value"] = 99
    with pytest.raises(ValueError, match="input fingerprint"):
        evaluate_frozen_rank_ic(scores, labels, replace(real, real_binding=binding))


def test_sealed_result_cannot_receive_unfrozen_posthoc_metric(contract):
    scores, labels = frames(contract)
    binding = RankICRealBinding(
        study_reference="synthetic sealed fixture",
        score_frame_sha256=frame_sha256(scores),
        label_frame_sha256=frame_sha256(labels),
        qualification_reference="fixture",
        frozen_protocol_reference="fixture",
        approval_reference="fixture",
        qualification_sha256="0" * 64,
        frozen_protocol_sha256="1" * 64,
        approval_sha256="2" * 64,
        prior_result_sealed=True,
    )
    c = replace(contract, data_mode="qualified", real_binding=binding)
    with pytest.raises(ValueError, match="separately frozen and approved RankIC addendum"):
        evaluate_frozen_rank_ic(scores, labels, c)


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("training_labels_end", "2025-02-01T07:00:00Z", "not mature and purged"),
        ("transform_fit_end", "2025-02-01T07:00:00Z", "fitted after the training cutoff"),
        ("train_end", "2025-02-07T07:00:00Z", "boundaries overlap"),
    ],
)
def test_model_training_and_transform_boundaries(contract, field, value, reason):
    fold = replace(model_fold(), **{field: value})
    c = replace(
        contract,
        scores=(RankICScore("model", "model_value", "model_score", "higher_score_higher_label"),),
        model_folds=(fold,),
    )
    scores, labels = frames(c)
    with pytest.raises(ValueError, match=reason):
        evaluate_frozen_rank_ic(scores, labels, c)


def test_model_score_cannot_skip_fold_provenance(contract):
    c = replace(
        contract,
        scores=(RankICScore("model", "model_value", "model_score", "higher_score_higher_label"),),
    )
    scores, labels = frames(c)
    with pytest.raises(ValueError, match="frozen training binding"):
        evaluate_frozen_rank_ic(scores, labels, c)


def test_equal_fold_weights_do_not_silently_drop_empty_folds(contract):
    c = replace(
        contract,
        time_weighting="equal_fold_then_checkpoint",
        checkpoints=contract.checkpoints + (RankICCheckpoint("2025-02-14T07:00:00Z", "fold2"),),
    )
    scores, labels = frames(contract)
    result = evaluate_frozen_rank_ic(scores, labels, c)
    row = result.summary.iloc[0]
    assert row["expected_folds"] == 2 and row["valid_folds"] == 1
    assert row["mean_rank_ic"] is None
    assert row["summary_undefined_reason"] == "frozen_fold_has_no_defined_period"


def test_public_entrypoint_delegates_existing_kernel(contract, monkeypatch):
    from lei_signal.research.factor_lab import diagnostics
    from lei_signal.research.factor_lab import evaluate_frozen_rank_ic as public_evaluate

    original = diagnostics._cross_section_ic
    calls = []

    def spy(pairs, *, min_pairs):
        calls.append((pairs.copy(deep=True), min_pairs))
        return original(pairs, min_pairs=min_pairs)

    monkeypatch.setattr(diagnostics, "_cross_section_ic", spy)
    scores, labels = frames(contract)
    result = public_evaluate(scores, labels, freeze_contract(contract))
    assert periodic_value(result) == pytest.approx(1)
    assert len(calls) == 1 and calls[0][1] == contract.min_assets
    assert calls[0][0]["value"].tolist() == scores["raw_value"].tolist()
    assert calls[0][0]["exclusion_reason"].isna().all()


def test_legacy_synthetic_only_entrypoint_has_not_been_relaxed():
    from lei_signal.research.factor_lab.contracts import IdentityFormatError
    from lei_signal.research.factor_lab.diagnostics import evaluate_predictive

    protocol = {
        "protocol_id": "real-input-must-not-pass-legacy-entry",
        "version": "1.0",
        "kind": "predictive_diagnostic",
        "data_mode": "qualified",
        "synthetic": False,
        "timezone": "Asia/Shanghai",
        "evaluation_cutoff": "2030-01-01T15:00:00+08:00",
        "diagnostics": {"type": "cross_section_ic"},
    }
    with pytest.raises(IdentityFormatError, match="synthetic"):
        evaluate_predictive(None, pd.DataFrame(), protocol=protocol)


@pytest.mark.parametrize("digest", ["", "abc", "G" * 64, "A" * 64])
def test_sealed_addendum_requires_valid_sha256(contract, digest):
    scores, labels = frames(contract)
    binding = RankICRealBinding(
        study_reference="synthetic sealed guard fixture",
        score_frame_sha256=frame_sha256(scores),
        label_frame_sha256=frame_sha256(labels),
        qualification_reference="fixture",
        frozen_protocol_reference="fixture",
        approval_reference="fixture",
        qualification_sha256="0" * 64,
        frozen_protocol_sha256="1" * 64,
        approval_sha256="2" * 64,
        prior_result_sealed=True,
        frozen_addendum_reference="nonempty fixture addendum",
        frozen_addendum_sha256=digest,
    )
    with pytest.raises(ValueError, match="separately frozen and approved RankIC addendum"):
        evaluate_frozen_rank_ic(
            scores, labels, replace(contract, data_mode="qualified", real_binding=binding)
        )


def test_mixed_horizon_inside_broad_window_is_excluded(contract):
    scores, labels = frames(contract)
    labels.loc[0, "label_end_at"] = (
        pd.Timestamp(labels.loc[0, "label_start_at"]) + pd.Timedelta(minutes=1)
    ).isoformat()
    result = evaluate_frozen_rank_ic(scores, labels, contract)
    assert result.periodic.iloc[0]["eligible_assets"] == 3
    assert "label_endpoint_differs_from_frozen_window" in result.exclusions.iloc[0]["reasons"]


def test_frozen_calendar_and_offsets_must_match(contract):
    c = freeze_contract(contract)
    scores, labels = frames(c)
    bad = replace(c.label_windows[0], end_session_offset=20)
    with pytest.raises(ValueError, match="holding-session intervals"):
        run_evaluation(scores, labels, replace(c, label_windows=(bad,)))
    bad = replace(c.label_windows[0], session_sequence_sha256="0" * 64)
    with pytest.raises(ValueError, match="session-sequence fingerprint"):
        run_evaluation(scores, labels, replace(c, label_windows=(bad,)))


def test_unfrozen_label_schedule_is_not_admitted(contract):
    scores, labels = frames(contract)
    with pytest.raises(ValueError, match="exact label windows must be frozen"):
        run_evaluation(scores, labels, contract)


def test_weekly_checkpoints_use_market_local_week_across_utc_boundary(contract):
    c = replace(
        contract,
        checkpoints=(
            RankICCheckpoint("2025-02-03T00:30:00+08:00", "fold1"),
            RankICCheckpoint("2025-02-07T15:00:00+08:00", "fold1"),
        ),
    )
    scores, labels = frames(c)
    with pytest.raises(ValueError, match="market-local ISO week"):
        evaluate_frozen_rank_ic(scores, labels, c)


def test_distinct_market_local_weeks_remain_distinct(contract):
    c = replace(
        contract,
        checkpoints=(
            RankICCheckpoint("2025-02-03T00:30:00+08:00", "fold1"),
            RankICCheckpoint("2025-02-10T00:30:00+08:00", "fold1"),
        ),
    )
    scores, labels = frames(c)
    result = evaluate_frozen_rank_ic(scores, labels, c)
    assert len(result.periodic) == 2


def test_type_aware_fingerprint_blocks_changed_asset_identity(contract):
    c = replace(contract, universes=(RankICUniverse("stocks", "stock", ("1", "B", "C", "D")),))
    scores, labels = frames(c)
    changed = labels.copy(deep=True)
    changed.loc[0, "asset_id"] = 1
    assert changed["asset_id"].dtype == labels["asset_id"].dtype
    assert frame_sha256(changed) != frame_sha256(labels)
    binding = RankICRealBinding(
        study_reference="synthetic binding guard fixture",
        score_frame_sha256=frame_sha256(scores),
        label_frame_sha256=frame_sha256(labels),
        qualification_reference="fixture",
        frozen_protocol_reference="fixture",
        approval_reference="fixture",
        qualification_sha256="0" * 64,
        frozen_protocol_sha256="1" * 64,
        approval_sha256="2" * 64,
    )
    real_c = replace(c, data_mode="qualified", real_binding=binding)
    with pytest.raises(ValueError, match="input fingerprint"):
        evaluate_frozen_rank_ic(scores, changed, real_c)


def test_completed_date_scope_discloses_intraday_arrival_ordering(contract):
    c = replace(
        contract,
        temporal_basis="session_date_after_close",
        availability_context="retrospective_after_close",
        source_evidence="synthetic approved fixture",
        after_close_scenario="completed-date research",
        checkpoints=(RankICCheckpoint("2025-02-07", "fold1"),),
        window_start="2025-02-01",
        window_end="2025-03-31",
        evaluation_as_of="2025-03-31",
    )
    scores, labels = frames(c)
    scores["source_available_at"] = "2025-02-07T23:59:00+08:00"
    result = evaluate_frozen_rank_ic(scores, labels, c)
    assert result.periodic.iloc[0]["eligible_assets"] == 4
    assert "intraday arrival ordering not evaluated" in result.metadata["session_date_scope"]
    assert result.metadata["live_qualified"] is False


def test_synthetic_mode_is_disclosed_as_caller_declared(contract):
    scores, labels = frames(contract)
    result = evaluate_frozen_rank_ic(scores, labels, contract)
    assert "caller-declared" in result.metadata["synthetic_provenance"]
