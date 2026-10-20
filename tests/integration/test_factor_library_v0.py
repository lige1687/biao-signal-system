"""End-to-end CLI/study tests for the factor library v0 controlled run."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
PREPARE = ROOT / "docs/experiments/raw/research-factor-library-v0-2026-09-09/prepare-02"

spec = importlib.util.spec_from_file_location(
    "run_factor_library_v0", ROOT / "scripts/run_factor_library_v0.py"
)
runner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)

PATH_TABLES = [
    "equity.csv",
    "trades.csv",
    "orders.csv",
    "signals.csv",
    "actions.csv",
    "annual.csv",
    "periods.csv",
    "capital-contributions.csv",
    "phase-contributions.csv",
    "product-weights.csv",
    "direction-weights.csv",
    "direction-profit-full.csv",
    "holdings-description.csv",
    "manifest.json",
]


def test_prepare_cli_runs(tmp_path):
    out = tmp_path / "prep"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_factor_library_v0.py"),
            "prepare",
            "--output",
            str(out),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(out.joinpath("preparation-result.json").read_text())
    assert result["status"] == "preparation_complete"
    assert result["blocked_items"] == []


def test_full_study_runs_with_identities_and_never_overwrites(tmp_path):
    protocol = PREPARE / "protocol.json"
    assert protocol.is_file(), "run prepare-02 first"
    out1 = runner.run_study(
        protocol, tmp_path / "run-01", run_tests=False
    )
    summary = json.loads((out1 / "summary.json").read_text())
    assert summary["status"] == "run_complete"
    assert summary["paths"] == 8
    assert all(c["passed"] for c in summary["compatibility_gate"]["checked"])

    quality = json.loads((out1 / "quality-report.json").read_text())
    assert quality["passed"]
    assert quality["worst_full_window_error"] <= 0.01
    assert quality["worst_phase_error"] <= 0.01

    keys = {p.name for p in (out1 / "paths").iterdir()}
    assert keys == {
        f"{v}-fee{f:.3f}" for v in ("E00", "E01", "E10", "E11") for f in (0.001, 0.002)
    }
    for key in sorted(keys):
        pdir = out1 / "paths" / key
        for name in PATH_TABLES:
            assert (pdir / name).is_file(), (key, name)
        manifest = json.loads((pdir / "manifest.json").read_text())
        assert "mixed.momentum.raw@1.0.0" in manifest["definition_refs"]
        assert manifest["production_authorization"] == "not_authorized"
        variant = key.split("-fee")[0]
        if variant == "E11":
            assert "mixed.no_exit_100@1.0.0" in manifest["definition_refs"]
            assert manifest["policy_status"] == "executed_compatibility_reference"
        else:
            assert manifest["policy_status"] == "proposal"
            assert manifest["policy_ref"].startswith("policy.mixed.")
        signals = pd.read_csv(pdir / "signals.csv")
        if len(signals):
            assert "definition_refs" in signals.columns

    comparison = pd.read_csv(out1 / "decision-comparisons.csv")
    assert set(comparison.kind) == {"path", "difference"}
    assert "E11-E10@fee0.001" in set(
        comparison[comparison.kind == "difference"].comparison
    )

    # anti-overwrite: same target bumps to a new sibling and leaves run-01 intact
    fingerprint_before = (out1 / "summary.json").read_bytes()
    out2 = runner.run_study(protocol, tmp_path / "run-01", run_tests=False)
    assert out2 != out1
    assert out2.name == "run-02"
    assert (out1 / "summary.json").read_bytes() == fingerprint_before


def test_tampered_protocol_is_rejected(tmp_path):
    good = json.loads((PREPARE / "protocol.json").read_text())
    bad_dir = tmp_path / "bad-prepare"
    bad_dir.mkdir()
    (bad_dir / "frozen-definitions.v1.0.0.json").write_bytes(
        (PREPARE / "frozen-definitions.v1.0.0.json").read_bytes()
    )
    bad = dict(good)
    bad["accounts"] = dict(bad["accounts"], fees=[0.001, 0.005])
    (bad_dir / "protocol.json").write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="fees/path cap"):
        runner.run_study(bad_dir / "protocol.json", tmp_path / "run-x", run_tests=False)
