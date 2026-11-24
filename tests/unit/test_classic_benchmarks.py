"""Independent hand calculations; no network and no profitability gate."""

import importlib

import numpy as np
import pandas as pd
import pytest


def library():
    return importlib.import_module("lei_signal.research.factor_lab.benchmarks")


def test_library_available():
    assert importlib.util.find_spec("lei_signal.research.factor_lab.benchmarks") is not None


def test_hand_calculated_operators():
    # n=3: seed=(1+2+3)/3=2; next EMA=.5*4+.5*2=3.
    c = pd.Series([1.0, 2.0, 3.0, 4.0, 3.0], index=pd.date_range("2020-01-01", periods=5))
    f = library().local_features(pd.DataFrame({"close": c}), 3)
    assert np.isnan(f.sma.iloc[1])
    assert f.sma.iloc[2] == 2
    assert f.ema.iloc[3] == 3
    assert f.ema.iloc[4] == 3
    assert f.hist_return.iloc[3] == 3  # 4/1 - 1, n separate from h.
    assert f.volatility.iloc[3] == pytest.approx(np.std([1, 0.5, 1 / 3], ddof=1))
    assert pd.isna(f.S.iloc[2])  # no prior SMA
    assert bool(f.S.iloc[3]) and bool(f.E.iloc[3])
    assert not bool(f.E.iloc[4])  # equality is not confirmation


def test_prefix_and_forbidden_future_fields():
    c = pd.DataFrame({"close": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]})
    pd.testing.assert_frame_equal(
        library().local_features(c.iloc[:5], 3), library().local_features(c, 3).iloc[:5]
    )
    with pytest.raises(ValueError, match="columns"):
        library().local_features(c.assign(future_return=1), 3)


def test_exact_equal_sma_and_missing():
    f = library().local_features(pd.DataFrame({"close": ["0.1", "0.2", "0.3", "0.1"]}), 3)
    assert not bool(f.S.iloc[3])  # c[t]==c[t-n]: slope exactly zero
    f = library().local_features(pd.DataFrame({"close": [1.0, 2.0, 3.0, np.nan, 5.0, 6.0]}), 3)
    assert pd.isna(f.S.iloc[3]) and pd.isna(f.E.iloc[4])


def test_french_units_rf_and_missing():
    raw = (
        "Note\n,Mkt-RF,SMB,HML,RMW,CMA,RF\n196307,1.00,-99.99,-999,2,3,0.25\n"
        "196308,2,3,4,5,6,0.26\n\n Annual Factors\n1963,99,99,99,99,99,99\n"
    )
    f = library().parse_french(raw, "ff5")
    assert len(f) == 2 and f.month.iloc[0] == "1963-07"
    assert f["Mkt-RF"].iloc[0] == 0.01  # already excess: do not subtract RF
    assert f.RF.iloc[0] == 0.0025
    assert pd.isna(f.SMB.iloc[0]) and pd.isna(f.HML.iloc[0])


@pytest.mark.parametrize(
    "raw",
    [
        ",Mom\n202013,1\n",
        ",Mom\n202001,1\n202001,2\n",
        ",Other\n202001,1\n",
        ",Mom\n202001,inf\n",
        ",Mom\n202002,1\n202001,2\n",
    ],
)
def test_bad_french_rejected(raw):
    with pytest.raises(ValueError):
        library().parse_french(raw, "mom")


def test_adaptation_rejects_returns_as_predictive_features():
    record = {
        "kind": "factor_return",
        "market": "US",
        "frequency": "monthly",
        "currency": "USD",
        "uses": ["attribution"],
        "historical_availability": "unknown",
    }
    with pytest.raises(ValueError):
        library().require_adapter(
            record, purpose="prediction", market="CN", frequency="daily", currency="CNY"
        )
    assert library().require_adapter(
        record, purpose="attribution", market="US", frequency="monthly", currency="USD"
    )


def test_split_purges_cross_boundary_labels():
    x = pd.DataFrame(
        {
            "date": ["2020-01-01", "2020-01-02", "2020-01-04"],
            "label_end": ["2020-01-03", "2020-01-05", "2020-01-06"],
        }
    )
    tr, va = library().time_split(x, "2020-01-04")
    assert tr.tolist() == [True, False, False]
    assert va.tolist() == [False, False, True]


def test_train_only_linear_prediction():
    # y=1+2*x solved independently; test x=3 -> 7.
    pred = library().linear_predict(
        np.array([[0.0], [1.0], [2.0]]), np.array([1.0, 3.0, 5.0]), np.array([[3.0]])
    )
    assert pred[0] == pytest.approx(7.0)


def test_old_registry_remains_valid():
    from lei_signal.research import definitions

    registry = definitions.load_registry()
    assert definitions.resolve(registry, "trend.sma50@1.0.0")["type"] == "feature"


def test_real_pipeline_entry_exists():
    assert importlib.util.find_spec("lei_signal.research.factor_lab.benchmark_pilot") is not None


def test_increment_interval_uses_paired_date_losses():
    pilot = importlib.import_module("lei_signal.research.factor_lab.benchmark_pilot")
    # Constant paired improvement 2: any continuous-date resample must give [2,2].
    assert pilot.block_interval(np.full(140, 2.0), length=60, draws=50, seed=7) == [2.0, 2.0]


def test_reference_section_refuses_unresolved_members():
    from lei_signal.research import definitions

    r = definitions.load_registry()
    import copy

    r = copy.deepcopy(r)
    if not r.get("research_references"):
        pytest.skip("registry extension not installed yet")
    r["research_references"][0]["members"] = ["not.registered@1.0.0"]
    with pytest.raises(ValueError, match="member"):
        definitions.validate_registry(r)


def test_ch3_keeps_decimal_excess_and_rf():
    f = pd.DataFrame(
        {
            "mnthdt": [20000131, 20000229],
            "rf_mon": [0.0019, 0.0018],
            "mktrf": [0.1479, 0.1197],
            "SMB": [-0.0161, 0.0134],
            "VMG": [-0.0084, -0.0728],
        }
    )
    x = library().parse_ch3(f)
    assert x.mktrf.iloc[0] == 0.1479 and x.rf_mon.iloc[0] == 0.0019
    assert x.month.tolist() == ["2000-01", "2000-02"]
    with pytest.raises(ValueError):
        library().parse_ch3(pd.concat([f, f]))


def test_load_snapshot_checks_hash_and_adapter(tmp_path):
    import hashlib

    p = tmp_path / "returns.csv"
    p.write_text("month,Mom\n2020-01,0.02\n")
    snapshot = {
        "output_path": p.name,
        "output_sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        "raw_path": p.name,
        "raw_sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        "market": "US",
        "frequency": "monthly",
        "currency": "USD",
    }
    x = library().load_published_returns(
        snapshot, root=tmp_path, market="US", frequency="monthly", currency="USD"
    )
    assert x.Mom.iloc[0] == 0.02
    with pytest.raises(ValueError):
        library().load_published_returns(
            snapshot, root=tmp_path, market="CN", frequency="daily", currency="CNY"
        )
    p.write_text("month,Mom\n2020-01,9\n")
    with pytest.raises(ValueError, match="hash"):
        library().load_published_returns(
            snapshot, root=tmp_path, market="US", frequency="monthly", currency="USD"
        )


def test_pilot_preserves_existing_quote_row_ema_after_calendar_gap():
    import json
    from pathlib import Path

    pilot = importlib.import_module("lei_signal.research.factor_lab.benchmark_pilot")
    root = Path(__file__).resolve().parents[2]
    config = json.loads(
        (
            root / "docs/archive/handoffs-plans/classic-benchmarks-2026-09-28/protocol.json"
        ).read_text()
    )
    panel = pilot.load_panel(config, root)
    rows = panel[panel.symbol == "512100.SS"]
    assert rows.E.notna().sum() == 1083  # 1084 quotes, only first quote after gap protected.
    assert pd.isna(rows.set_index("date").loc["2022-09-05", "E"])


def test_pilot_preserves_accepted_nominal_equality_amendment():
    import json
    from pathlib import Path

    pilot = importlib.import_module("lei_signal.research.factor_lab.benchmark_pilot")
    root = Path(__file__).resolve().parents[2]
    config = json.loads(
        (
            root / "docs/archive/handoffs-plans/classic-benchmarks-2026-09-28/protocol-r2.json"
        ).read_text()
    )
    config["state_snapshot"] = (
        "docs/experiments/raw/dual-ma-correction-2026-09-28/observations-v1.0.1.json"
    )
    x = pilot.load_panel(config, root).set_index(["symbol", "date"])
    assert not bool(x.loc[("510300.SS", "2025-05-29"), "S"])


def test_cli_end_to_end_and_independent_fixed_snapshot(tmp_path):
    import hashlib
    import json
    import os
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    protocol = (
        root
        / "docs/archive/handoffs-plans/classic-benchmarks-2026-09-28"
        / "protocol-complete.json"
    )
    out = tmp_path / "run"
    command = [
        sys.executable,
        "scripts/run_factor_lab.py",
        "--benchmark-protocol",
        str(protocol),
        "--out",
        str(out),
    ]
    run = subprocess.run(
        command,
        cwd=root,
        env={**os.environ, "PYTHONPATH": str(root / "src")},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert run.returncode == 0, run.stderr
    evidence = json.loads(
        (
            root
            / "docs/experiments/raw/classic-benchmarks-2026-09-28"
            / "independent-review-complete.json"
        ).read_text()
    )
    result = json.loads((out / "results.json").read_text())
    for actual, expected in zip(result["increment"], evidence["independent_results"], strict=True):
        assert actual["improvement_pp2"] == pytest.approx(expected["improvement_pp2"], abs=1e-9)
        assert actual["baseline_mse_pp2"] == pytest.approx(expected["baseline_mse_pp2"], abs=1e-9)
    assert (
        hashlib.sha256((out / "predictions.csv").read_bytes()).hexdigest()
        == evidence["engineering_snapshot"]["predictions_sha256"]
    )
    ledger = json.loads((out / "trial-ledger.json").read_text())
    assert ledger["account_runs"] == 0 and ledger["unseen_validation"] is False
    assert (out / "report.md").is_file() and (out / "manifest.json").is_file()
    # Reusing any run directory must fail, even if its results look good.
    again = subprocess.run(
        command,
        cwd=root,
        env={**os.environ, "PYTHONPATH": str(root / "src")},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert again.returncode != 0


def test_changed_input_is_refused_before_output_creation(tmp_path):
    import json
    from pathlib import Path

    from lei_signal.research.factor_lab.benchmark_pilot import run_pilot

    root = Path(__file__).resolve().parents[2]
    c = json.loads(
        (
            root
            / "docs/archive/handoffs-plans/classic-benchmarks-2026-09-28"
            / "protocol-complete.json"
        ).read_text()
    )
    c["source_identity"][c["registry_path"]] = "0" * 64
    protocol = tmp_path / "bad.json"
    protocol.write_text(json.dumps(c))
    with pytest.raises(ValueError, match="hash mismatch"):
        run_pilot(protocol, tmp_path / "bad-out")
    assert not (tmp_path / "bad-out").exists()
