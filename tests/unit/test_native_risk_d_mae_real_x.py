"""Artificial-only checks for the separate real X seal authority boundary."""

from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


real_x = _load(
    "native_risk_d_mae_real_x", ROOT / "src/lei_signal/research/native_risk_d_mae_real_x.py"
)
stage_a_tests = _load(
    "stage_a_artificial_fixture", ROOT / "tests/unit/test_native_risk_d_mae_inputs.py"
)


def _artificial_identity():
    docs, metadata = stage_a_tests.artificial_documents()
    return stage_a_tests.adapter._validate_identity(docs, metadata)


def _grant(identity):
    plan = {
        "output": str(real_x.OUTPUT_PATH),
        "external_mount": str(real_x.EXTERNAL_MOUNT),
        "external_device": real_x.EXTERNAL_DEVICE,
        "external_uuid": real_x.EXTERNAL_UUID,
    }
    grant = {
        "schema": "native-risk-d-mae-real-x-grant/1",
        "approved": True,
        "stage": "real_x",
        "design_sha256": real_x.DESIGN_SHA256,
        "executor_contract_sha256": real_x.CONTRACT_SHA256,
        "adapter_sha256": real_x.ADAPTER_SHA256,
        "executable_sha256": "artificial-code-sha",
        "input_sha256": copy.deepcopy(identity["original_sha256"]),
        "membership_sha256": real_x._membership_sha(identity),
        "output_plan_sha256": real_x.PLAN_SHA256,
        "output": str(real_x.OUTPUT_PATH),
        "real_x_directory": str(real_x.REAL_X_DIR),
        "external_mount": str(real_x.EXTERNAL_MOUNT),
        "external_device": real_x.EXTERNAL_DEVICE,
        "external_uuid": real_x.EXTERNAL_UUID,
        "ledger_path": str(real_x.LEDGER_PATH),
        "permissions": copy.deepcopy(real_x.PERMISSIONS),
    }
    return grant, plan


def test_artificial_x_preserves_all_members_and_d():
    identity = _artificial_identity()
    rows = real_x._derive_x(identity)
    assert len(rows) == 76
    assert sum(len(row["event_ids"]) for row in rows) == 84
    assert len({(row["asset"], row["lifecycle"]) for row in rows}) == 33
    assert all(row["D_frozen"] == 1.0 and row["V_volatility_pct"] == 50.0 for row in rows)
    assert rows[-1]["case_id"] == real_x.UNKNOWN_CASE_ID
    assert rows[-1]["window_metadata"]["calendar_mature_by_20260626"] is False


@pytest.mark.parametrize(
    "change,pattern",
    [
        (lambda g, p: g.update(approved=False), "missing or invalid X grant"),
        (lambda g, p: g.update(stage="real_y"), "missing or invalid X grant"),
        (lambda g, p: g.update(executable_sha256="changed"), "code or contract hash"),
        (lambda g, p: g.update(adapter_sha256="changed"), "code or contract hash"),
        (
            lambda g, p: g["input_sha256"].update({"deduplicated-cases.json": "changed"}),
            "input or member hash",
        ),
        (lambda g, p: g.update(membership_sha256="changed"), "input or member hash"),
        (lambda g, p: g.update(output_plan_sha256="changed"), "output, device, plan or ledger"),
        (
            lambda g, p: g.update(output=str(real_x.OUTPUT_PATH / "other")),
            "output, device, plan or ledger",
        ),
        (
            lambda g, p: g.update(real_x_directory=str(real_x.OUTPUT_PATH / "other")),
            "output, device, plan or ledger",
        ),
        (
            lambda g, p: g.update(external_device=float(real_x.EXTERNAL_DEVICE)),
            "output, device, plan or ledger",
        ),
        (
            lambda g, p: g.update(ledger_path=str(real_x.LEDGER_PATH) + "-2"),
            "output, device, plan or ledger",
        ),
        (lambda g, p: g["permissions"].update(real_Y_passes=1), "permissions differ"),
        (lambda g, p: g["permissions"].update(real_X_passes=True), "permissions differ"),
        (lambda g, p: g["permissions"].update(real_Y_passes=False), "permissions differ"),
        (lambda g, p: g["permissions"].update(V_passes=1.0), "permissions differ"),
    ],
)
def test_grant_mutations_rejected(change, pattern):
    identity = _artificial_identity()
    grant, plan = _grant(identity)
    change(grant, plan)
    with pytest.raises(real_x.RealXError, match=pattern):
        real_x._validate_grant(grant, plan=plan, identity=identity, code_sha="artificial-code-sha")


def test_missing_grant_rejected_without_starting():
    identity = _artificial_identity()
    _, plan = _grant(identity)
    with pytest.raises(real_x.RealXError, match="grant fields differ"):
        real_x._validate_grant(None, plan=plan, identity=identity, code_sha="artificial-code-sha")


def test_member_change_rejected_even_with_unchanged_grant():
    identity = _artificial_identity()
    grant, plan = _grant(identity)
    identity["cases"][0]["event_ids"][0] = "altered-member"
    with pytest.raises(real_x.RealXError, match="input or member hash"):
        real_x._validate_grant(grant, plan=plan, identity=identity, code_sha="artificial-code-sha")


def test_nonfinite_v_rejected_before_x_output():
    identity = _artificial_identity()
    identity["cases"][0]["A"] = 1e-308
    identity["cases"][0]["C"] = 1e-309
    identity["cases"][0]["ATR20_SMA"] = 1e308
    with pytest.raises(real_x.RealXError, match="nonfinite V"):
        real_x._derive_x(identity)


def test_one_shot_ledger_rejects_replay_and_different_output(tmp_path):
    path = tmp_path / "artificial-ledger.jsonl"
    real_x._start_ledger(path, {"status": "started", "output": "first"})
    with pytest.raises(real_x.RealXError, match="already consumed"):
        real_x._start_ledger(path, {"status": "started", "output": "different"})
    assert path.read_text().count("started") == 1


def test_written_readback_detects_changed_bytes(tmp_path):
    path = tmp_path / "artificial-result.json"
    path.write_bytes(b'{"artificial":true}')
    real_x._verify_written(path, real_x._sha(path.read_bytes()))
    path.write_bytes(b'{"artificial":false}')
    with pytest.raises(real_x.RealXError, match="readback mismatch"):
        real_x._verify_written(path, real_x._sha(b'{"artificial":true}'))


def test_public_main_refuses_injected_arguments(monkeypatch):
    monkeypatch.setattr(sys, "argv", [str(real_x.SOURCE_PATH), "--grant", "alternate.json"])
    with pytest.raises(real_x.RealXError, match="accepts no path"):
        real_x.main()
