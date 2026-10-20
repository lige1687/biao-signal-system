"""factor_lab 验证层单测：切分、标签越界、尝试史、已看过保留段。"""
from __future__ import annotations

import pandas as pd
import pytest

from lei_signal.research.factor_lab.contracts import IdentityFormatError
from lei_signal.research.factor_lab.validation import audit_validation


def make_protocol(**overrides):
    protocol = {
        "protocol_id": "test-protocol",
        "version": "0.0.1",
        "kind": "predictive_diagnostic",
        "data_mode": "synthetic",
        "synthetic": True,
        "timezone": "Asia/Shanghai",
        "evaluation_cutoff": "2030-01-01T15:00:00+08:00",
        "validation": {
            "split": {
                "dev": ["2024-01-01", "2024-01-10"],
                "validation": ["2024-01-11", "2024-01-20"],
                "holdout": ["2024-01-21", "2024-01-31"],
            },
            "seen": {"dev": True, "validation": True, "holdout": False},
            "preprocessing": "none",
            "segment_cutoffs": {
                "dev": "2024-01-10T15:00:00+08:00",
                "validation": "2024-01-20T15:00:00+08:00",
                "holdout": "2024-01-31T15:00:00+08:00",
            },
        },
    }
    protocol.update(overrides)
    return protocol


def pairs_frame(rows: list[tuple[str, str, int, int]], with_labels: bool = True,
                naive_available: bool = False) -> pd.DataFrame:
    """rows: (date, entity, label_offset_days, label_window_days)"""
    out = []
    for date_str, entity, offset, window in rows:
        obs = pd.Timestamp(date_str)
        row = {"observation_date": obs, "entity_id": entity, "value": 1.0,
               "target": 0.01, "exclusion_reason": None}
        if with_labels:
            row["label_start"] = obs + pd.Timedelta(days=offset)
            row["label_end"] = obs + pd.Timedelta(days=offset + window)
            available = (row["label_end"].tz_localize("Asia/Shanghai")
                         + pd.Timedelta(hours=15))
            if naive_available:
                available = available.tz_localize(None)
            row["label_available_at"] = available
        out.append(row)
    columns = ["observation_date", "entity_id", "value", "target", "exclusion_reason"]
    if with_labels:
        columns += ["label_start", "label_end", "label_available_at"]
    return pd.DataFrame(out, columns=columns)


def trial(**overrides):
    record = {
        "trial_id": "t1",
        "definition_reference": "mixed.momentum.raw@1.0.0",
        "parameters": {},
        "pool": "synthetic-3-entity",
        "target": "protocol:t22-price-change@1.0.0",
        "input_identity": {"prices": "synthetic-prices-1"},
        "split_id": "s1",
        "outcome": "success",
        "selection_basis": "predeclared",
        "seen_segments": ["dev"],
        "run_version": "run-01",
    }
    record.update(overrides)
    return record


class TestSplitSanity:
    def test_out_of_order_split_rejected(self):
        protocol = make_protocol(validation={
            "split": {"dev": ["2024-02-01", "2024-02-10"],
                      "validation": ["2024-01-01", "2024-01-20"],
                      "holdout": ["2024-03-01", "2024-03-31"]},
            "seen": {"dev": True, "validation": True, "holdout": False},
            "preprocessing": "none",
        })
        with pytest.raises(IdentityFormatError, match="order or overlapping"):
            audit_validation(pairs_frame([]), [trial()], protocol=protocol)

    def test_overlapping_segments_rejected(self):
        protocol = make_protocol(validation={
            "split": {"dev": ["2024-01-01", "2024-01-15"],
                      "validation": ["2024-01-10", "2024-01-20"],
                      "holdout": ["2024-03-01", "2024-03-31"]},
            "seen": {"dev": True, "validation": True, "holdout": False},
            "preprocessing": "none",
        })
        with pytest.raises(IdentityFormatError, match="order or overlapping"):
            audit_validation(pairs_frame([]), [trial()], protocol=protocol)

    def test_non_none_preprocessing_rejected(self):
        protocol = make_protocol()
        protocol["validation"]["preprocessing"] = "zscore_full_history"
        with pytest.raises(IdentityFormatError, match="none"):
            audit_validation(pairs_frame([]), [trial()], protocol=protocol)

    def test_bad_seen_markers_rejected(self):
        protocol = make_protocol()
        protocol["validation"]["seen"] = {"dev": "yes", "validation": True,
                                          "holdout": False}
        with pytest.raises(IdentityFormatError, match="seen"):
            audit_validation(pairs_frame([]), [trial()], protocol=protocol)


class TestLabelOverlap:
    def test_observation_dates_non_overlapping_but_label_crosses(self):
        # dev 内观察日不重叠，但标签窗跨进验证段：必须逐条点出
        rows = [(f"2024-01-0{d}", "a", 1, 12) for d in range(1, 9)]
        result = audit_validation(pairs_frame(rows), [trial()], protocol=make_protocol())
        crossing = [f for f in result["overlap_findings"]
                    if f["code"] == "label_crosses_segment_boundary"]
        assert crossing, "标签跨段必须被发现"
        assert crossing[0]["segment"] == "dev"
        assert crossing[0]["next_segment"] == "validation"
        assert crossing[0]["n_pairs"] >= 1
        assert result["overfit_risk_status"] == "not_excluded"

    def test_endpoint_contact_counts_as_overlap(self):
        # 标签窗末端正好接触验证段起点（01-11）：边界接触也算重叠
        rows = [("2024-01-09", "a", 1, 1)]  # label_end = 01-11
        result = audit_validation(pairs_frame(rows), [trial()], protocol=make_protocol())
        crossing = [f for f in result["overlap_findings"]
                    if f["code"] == "label_crosses_segment_boundary"]
        assert crossing and crossing[0]["n_pairs"] == 1

    def test_clean_split_no_overlap_findings(self):
        rows = [(f"2024-01-0{d}", "a", 1, 1) for d in range(1, 6)]  # 全在 dev 内闭合
        result = audit_validation(pairs_frame(rows), [trial()], protocol=make_protocol())
        crossing = [f for f in result["overlap_findings"]
                    if f["code"] == "label_crosses_segment_boundary"]
        assert not crossing
        counts = result["sample_counts"]
        assert counts["dev"]["n_usable_clean"] == 5
        assert counts["validation"]["n_pairs"] == 0

    def test_label_known_only_after_cutoff(self):
        # label 可得时刻晚于该段截止：评价时结论不存在 → 剔除且不出现在clean
        rows = [("2024-01-08", "a", 1, 3)]  # label_end=01-12 > dev截止01-10
        result = audit_validation(pairs_frame(rows), [trial()], protocol=make_protocol())
        dev = result["sample_counts"]["dev"]
        assert dev["n_usable_clean"] == 0
        codes = {f["code"] for f in result["overlap_findings"]}
        assert "label_known_after_segment_cutoff" in codes

    def test_naive_label_available_at_rejected(self):
        rows = [("2024-01-08", "a", 1, 5)]
        with pytest.raises(IdentityFormatError, match="timezone-aware"):
            audit_validation(pairs_frame(rows, naive_available=True), [trial()],
                             protocol=make_protocol())

    def test_samples_outside_segments_finding(self):
        rows = [("2024-06-01", "a", 1, 5)]
        result = audit_validation(pairs_frame(rows), [trial()], protocol=make_protocol())
        outside = [f for f in result["split_findings"]
                   if f["code"] == "samples_outside_declared_segments"]
        assert outside and outside[0]["n"] == 1


class TestTrialHistory:
    def test_unknown_history_when_none(self):
        result = audit_validation(pairs_frame([]), None, protocol=make_protocol())
        assert result["trial_history_status"] == "unknown"
        assert any(f["code"] == "trial_history_unknown" for f in result["trial_findings"])

    def test_all_trials_kept_not_only_winner(self):
        trials = [trial(trial_id="t1", outcome="success"),
                  trial(trial_id="t2", outcome="failed"),
                  trial(trial_id="t3", outcome="abandoned")]
        result = audit_validation(pairs_frame([]), trials, protocol=make_protocol())
        assert result["trial_history_status"] == "provided"
        assert len(result["trials_kept"]) == 3
        summary = next(f for f in result["trial_findings"]
                       if f["code"] == "all_trials_kept")
        assert summary["n_success"] == 1
        assert summary["n_failed_or_abandoned"] == 2

    def test_repeated_trial_id_finding(self):
        trials = [trial(trial_id="t1"), trial(trial_id="t1")]
        result = audit_validation(pairs_frame([]), trials, protocol=make_protocol())
        assert any(f["code"] == "duplicate_trial_id" for f in result["trial_findings"])

    def test_seen_holdout_cannot_be_reset(self):
        trials = [trial(seen_segments=["dev", "holdout"])]
        result = audit_validation(pairs_frame([]), trials, protocol=make_protocol())
        used = [f for f in result["trial_findings"] if f["code"] == "holdout_already_used"]
        assert used
        assert result["seen_markers"]["holdout"] is False  # 协议声明未看，但试验史戳穿

    def test_invalid_outcome_rejected(self):
        with pytest.raises(IdentityFormatError, match="outcome"):
            audit_validation(pairs_frame([]), [trial(outcome="lucky")],
                             protocol=make_protocol())

    def test_missing_trial_keys_rejected(self):
        bad = {"trial_id": "t1", "outcome": "success"}
        with pytest.raises(IdentityFormatError, match="missing keys"):
            audit_validation(pairs_frame([]), [bad], protocol=make_protocol())


class TestOutputContract:
    def test_required_fields_present(self):
        result = audit_validation(pairs_frame([("2024-01-05", "a", 1, 3)]),
                                  [trial()], protocol=make_protocol())
        for key in ("split_findings", "overlap_findings", "trial_history_status",
                    "sample_counts", "limitations"):
            assert key in result
        assert result["overfit_risk_status"] == "not_excluded"
        assert result["preprocessing"] == "none"
        # 无绿色默认：limitations 必须明示不能证明没有过拟合
        assert any("过拟合" in text for text in result["limitations"])

    def test_direction_change_detected(self):
        def segment_rows(dates, values, targets):
            frame = pairs_frame([(d, "a", 1, 3) for d in dates])
            frame["value"] = values
            frame["target"] = targets
            return frame
        dev = segment_rows([f"2024-01-0{d}" for d in range(1, 6)],
                           [1.0, 2.0, 3.0, 4.0, 5.0],
                           [0.01, 0.02, 0.03, 0.04, 0.05])
        val = segment_rows([f"2024-01-1{d}" for d in range(1, 6)],
                           [1.0, 2.0, 3.0, 4.0, 5.0],
                           [0.05, 0.04, 0.03, 0.02, 0.01])
        hold = segment_rows(["2024-01-21", "2024-01-23", "2024-01-25"],
                            [1.0, 2.0, 3.0], [0.01, 0.02, 0.03])
        pairs = pd.concat([dev, val, hold], ignore_index=True)
        result = audit_validation(pairs, [trial()], protocol=make_protocol())
        flips = [f for f in result["split_findings"]
                 if f["code"] == "direction_changes_across_segments"]
        assert flips, "分段方向不一致必须被发现"
        assert flips[0]["signs"]["dev"] == 1
        assert flips[0]["signs"]["validation"] == -1


class TestTimeQualificationR1:
    """集中返修 R1：跨段/未成熟/未知必须从clean集合与统计中剔除。"""

    def test_crossing_sample_excluded_from_clean(self):
        # 2024-01-09样本标签触及验证段起点01-11：既跨界又不得计入clean
        result = audit_validation(pairs_frame([("2024-01-09", "a", 1, 1)]),
                                  [trial()], protocol=make_protocol())
        dev = result["sample_counts"]["dev"]
        assert dev["n_usable_clean"] == 0
        assert dev["n_label_crossing_into_next_segment"] == 1
        assert any(f["code"] == "label_crosses_segment_boundary"
                   for f in result["overlap_findings"])

    def test_future_mature_sample_excluded_from_clean(self):
        # 2024-01-23样本结果在02月发生，评价截止01-25：未成熟，clean=0
        protocol = make_protocol(
            evaluation_cutoff="2024-01-25T15:00:00+08:00",
            validation={"split": {"dev": ["2024-01-01", "2024-01-10"],
                                  "validation": ["2024-01-11", "2024-01-20"],
                                  "holdout": ["2024-01-21", "2024-01-31"]},
                        "seen": {"dev": True, "validation": True, "holdout": False},
                        "preprocessing": "none",
                        "segment_cutoffs": {
                            "dev": "2024-01-10T15:00:00+08:00",
                            "validation": "2024-01-20T15:00:00+08:00",
                            "holdout": "2024-01-25T15:00:00+08:00"}})
        result = audit_validation(pairs_frame([("2024-01-23", "a", 1, 20)]),
                                  [trial()], protocol=protocol)
        assert result["sample_counts"]["holdout"]["n_usable_clean"] == 0

    def test_segment_cutoffs_required_tz_aware_ordered(self):
        base = {"split": {"dev": ["2024-01-01", "2024-01-10"],
                          "validation": ["2024-01-11", "2024-01-20"],
                          "holdout": ["2024-01-21", "2024-01-31"]},
                "seen": {"dev": True, "validation": True, "holdout": False},
                "preprocessing": "none"}
        protocol = make_protocol(validation={**base, "segment_cutoffs": {
            "dev": "2024-01-10T15:00:00+08:00", "validation": "2024-01-20T15:00:00+08:00",
            "holdout": "2024-01-31T15:00:00+08:00"}})
        assert audit_validation(pairs_frame([("2024-01-05", "a", 1, 1)]),
                                [trial()], protocol=protocol)["sample_counts"]["dev"][
            "n_usable_clean"] == 1
        # 缺截止 → 格式错误
        with pytest.raises(IdentityFormatError, match="segment_cutoffs"):
            audit_validation(pairs_frame([]), [trial()],
                             protocol=make_protocol(validation=base))
        # 无时区 → 格式错误
        bad = {**base, "segment_cutoffs": {"dev": "2024-01-10 15:00:00",
                                           "validation": "2024-01-20T15:00:00+08:00",
                                           "holdout": "2024-01-31T15:00:00+08:00"}}
        with pytest.raises(IdentityFormatError, match="timezone-aware"):
            audit_validation(pairs_frame([]), [trial()],
                             protocol=make_protocol(validation=bad))
        # 截止晚于全局评价截止 → 格式错误
        late = {**base, "segment_cutoffs": {"dev": "2040-01-10T15:00:00+08:00",
                                            "validation": "2024-01-20T15:00:00+08:00",
                                            "holdout": "2024-01-31T15:00:00+08:00"}}
        with pytest.raises(IdentityFormatError, match="evaluation_cutoff"):
            audit_validation(pairs_frame([]), [trial()],
                             protocol=make_protocol(validation=late))

    def test_naive_and_nat_label_available_in_audit(self):
        # naive（无时区）= 格式错误；NaT/None = 未知 → 剔除
        with pytest.raises(IdentityFormatError, match="timezone-aware"):
            audit_validation(pairs_frame([("2024-01-05", "a", 1, 3)],
                                         naive_available=True),
                             [trial()], protocol=make_protocol())
        rows = pairs_frame([("2024-01-05", "a", 1, 3)])
        rows["label_available_at"] = pd.NaT
        result = audit_validation(rows, [trial()], protocol=make_protocol())
        assert result["sample_counts"]["dev"]["n_usable_clean"] == 0
        assert any(f["code"] == "label_available_unknown"
                   for f in result["overlap_findings"])

    def test_clean_mask_feeds_segment_statistics(self):
        # 合法段：干净样本产生非零统计（防止一律排除）
        frame = pairs_frame([(f"2024-01-0{d}", e, 1, 1)
                             for d, e in zip(range(1, 4), ["a", "b", "c"],
                                             strict=True)])
        frame["value"] = [1.0, 2.0, 3.0]
        frame["target"] = [0.01, 0.02, 0.03]
        ok = audit_validation(frame, [trial()], protocol=make_protocol())
        assert ok["sample_counts"]["dev"]["n_usable_clean"] == 3
        assert ok["sample_counts"]["dev"]["segment_ic"]["n"] == 3
        assert ok["sample_counts"]["dev"]["segment_ic"]["ic_pooled_over_segment"] == \
            pytest.approx(1.0)
        # 同样三行但全部跨段 → 干净集为空，段内统计为缺失
        cross = pairs_frame([("2024-01-09", e, 1, 3) for e in ["a", "b", "c"]])
        cross["value"] = [1.0, 2.0, 3.0]
        cross["target"] = [0.01, 0.02, 0.03]
        bad = audit_validation(cross, [trial()], protocol=make_protocol())
        dev = bad["sample_counts"]["dev"]
        assert dev["n_usable_clean"] == 0
        assert dev["segment_ic"] is None  # 无干净样本 → 无段内统计

    def test_trials_require_pool_target_input_identity(self):
        record = trial()
        for key in ("pool", "target", "input_identity"):
            bad = {k: v for k, v in record.items() if k != key}
            with pytest.raises(IdentityFormatError, match=key):
                audit_validation(pairs_frame([]), [bad], protocol=make_protocol())
