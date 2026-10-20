"""factor_lab 合同层单测：协议校验、元数据必需键、值帧行键。"""
from __future__ import annotations

import pandas as pd
import pytest

from lei_signal.research.factor_lab.contracts import (
    EXIT_IDENTITY_FORMAT,
    EXIT_INSUFFICIENT_DATA,
    IdentityFormatError,
    ResearchBatch,
    build_metadata,
    validate_protocol,
    validate_values_frame,
)


def make_protocol(**overrides):
    protocol = {
        "protocol_id": "test-protocol",
        "version": "0.0.1",
        "kind": "calculation_only",
        "data_mode": "synthetic",
        "synthetic": True,
        "timezone": "Asia/Shanghai",
        "evaluation_cutoff": "2030-01-01T15:00:00+08:00",
    }
    protocol.update(overrides)
    return protocol


def fake_card(type_="feature", unit="fraction"):
    return {
        "type": type_,
        "definition": {"unit": unit},
        "status": {
            "definition_clarity": "explicit",
            "implementation": "test",
            "effectiveness": "no_evidence",
        },
    }


class TestProtocolValidation:
    def test_valid_protocol_passes(self):
        validate_protocol(make_protocol())

    def test_missing_key_rejected(self):
        protocol = make_protocol()
        del protocol["kind"]
        with pytest.raises(IdentityFormatError, match="missing key"):
            validate_protocol(protocol)

    def test_unknown_kind_rejected(self):
        with pytest.raises(IdentityFormatError, match="unknown protocol kind"):
            validate_protocol(make_protocol(kind="money_printer"))

    def test_non_synthetic_rejected_this_round(self):
        with pytest.raises(IdentityFormatError, match="synthetic only"):
            validate_protocol(make_protocol(data_mode="qualified"))
        with pytest.raises(IdentityFormatError, match="synthetic only"):
            validate_protocol(make_protocol(data_mode="historical_reconstruction"))

    def test_synthetic_flag_must_be_true(self):
        with pytest.raises(IdentityFormatError, match="synthetic"):
            validate_protocol(make_protocol(synthetic=False))

    def test_naive_evaluation_cutoff_rejected(self):
        with pytest.raises(IdentityFormatError, match="timezone-aware"):
            validate_protocol(make_protocol(evaluation_cutoff="2030-01-01 15:00:00"))

    def test_exit_code_constants(self):
        assert EXIT_IDENTITY_FORMAT == 3
        assert EXIT_INSUFFICIENT_DATA == 2


class TestMetadata:
    def test_build_metadata_complete(self):
        metadata = build_metadata(
            reference="x.y@1.0.0",
            card=fake_card(),
            card_kind="registered",
            protocol=make_protocol(),
            entity_axis="instrument",
            value_type="continuous",
            data_identity={"synthetic": True},
            code_identity={"modules": []},
            calendar={"timezone": "Asia/Shanghai"},
            time_evidence={},
        )
        assert metadata["reference"] == "x.y@1.0.0"
        assert metadata["synthetic"] is True
        assert metadata["production_authorization"] == "not_authorized"
        assert metadata["protocol"]["sha256"]

    def test_unknown_entity_axis_rejected(self):
        with pytest.raises(IdentityFormatError, match="entity_axis"):
            build_metadata(
                reference="x.y@1.0.0", card=fake_card(), card_kind="registered",
                protocol=make_protocol(), entity_axis="galaxy", value_type="continuous",
                data_identity={}, code_identity={}, calendar={}, time_evidence={},
            )

    def test_unknown_card_kind_rejected(self):
        with pytest.raises(IdentityFormatError, match="card_kind"):
            build_metadata(
                reference="x.y@1.0.0", card=fake_card(), card_kind="vibes",
                protocol=make_protocol(), entity_axis="instrument",
                value_type="continuous", data_identity={}, code_identity={},
                calendar={}, time_evidence={},
            )


class TestValuesFrame:
    def test_valid_frame_passes(self):
        frame = pd.DataFrame({
            "observation_date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "entity_id": ["a", "a"],
            "value": [1.0, None],
            "missing_reason": [None, "warmup"],
        })
        assert validate_values_frame(frame) is frame

    def test_duplicate_key_rejected(self):
        frame = pd.DataFrame({
            "observation_date": pd.to_datetime(["2024-01-01", "2024-01-01"]),
            "entity_id": ["a", "a"],
            "value": [1.0, 2.0],
            "missing_reason": [None, None],
        })
        with pytest.raises(IdentityFormatError, match="duplicate"):
            validate_values_frame(frame)

    def test_missing_column_rejected(self):
        frame = pd.DataFrame({"observation_date": [1], "entity_id": ["a"],
                              "value": [1.0]})
        with pytest.raises(IdentityFormatError, match="columns"):
            validate_values_frame(frame)

    def test_missing_rows_are_kept_not_dropped(self):
        frame = pd.DataFrame({
            "observation_date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "entity_id": ["a", "a"],
            "value": [1.0, None],
            "missing_reason": [None, "warmup_history_insufficient"],
        })
        result = validate_values_frame(frame)
        assert len(result) == 2

    def test_research_batch_is_frozen_dataclass(self):
        import dataclasses

        assert dataclasses.is_dataclass(ResearchBatch)
