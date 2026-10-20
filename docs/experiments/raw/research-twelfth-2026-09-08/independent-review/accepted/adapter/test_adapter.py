from pathlib import Path
import importlib.util
import sys

sys.dont_write_bytecode = True
MODULE_PATH = Path(__file__).with_name("build_candidates.py")
SPEC = importlib.util.spec_from_file_location("twelfth_build_candidates", MODULE_PATH)
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)


def test_qualify_keeps_success_and_rejection_details():
    rr, accepted, reason = adapter.qualify(10.0, 9.0, 13.0)
    assert (rr, accepted, reason) == (3.0, True, None)
    assert adapter.qualify(10.0, 10.0, 13.0) == (None, False, "invalid_structure_risk")
    assert adapter.qualify(10.0, 9.0, None) == (None, False, "target_unavailable")


def test_config_mapping_preserves_date_and_source_metadata():
    source = {"module": "A", "basis_epoch_start": "2020-01-01", "basis_epoch_end": "2020-12-31",
              "event": {"event_id": "event-1", "symbol": "sh510300", "available_date": "2020-01-03",
                        "lifecycle_id": "life-1", "rule_version": "3", "evidence": {
                            "sub_rule": "first_ma_pullback_confirmed", "ma_period": 60,
                            "entry_variant": "confirmed", "touch_date": "2020-01-02",
                            "a3_structure_id": "bottom-1", "stop_price": 9.0, "close": 10.0}}}
    assert adapter.config_for(source) == "A60J"
    assert source["event"]["available_date"] == "2020-01-03"
    assert source["event"]["evidence"]["touch_date"] == "2020-01-02"
    assert source["event"]["evidence"]["a3_structure_id"] == "bottom-1"
    source["module"] = "C"
    source["event"]["evidence"] = {"sub_rule": "two_b_reversal_v2_confirmed", "version": "v2"}
    assert adapter.config_for(source) == "C2"


def test_reference_copy_changes_identity_only_and_keeps_source():
    source = {"config_id": "P0", "candidate_id": "P0:s:d:k", "symbol": "s",
              "signal_date": "2020-01-01", "signal_ref": 10.0, "stop": 8.0, "target": 16.0,
              "signal_rr": 3.0, "signal_accepted": True, "signal_reject_reason": None, "variant": "breakout"}
    copied = adapter.copy_references([source])[0]
    assert copied["config_id"] == "REF_BREAKOUT"
    assert copied["source_config_id"] == "P0"
    assert copied["source_candidate_id"] == "P0:s:d:k"
    for field in ("symbol", "signal_date", "signal_ref", "stop", "target", "signal_rr",
                  "signal_accepted", "signal_reject_reason"):
        assert copied[field] == source[field]
