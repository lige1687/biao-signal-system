"""Synthetic mathematical and pre-fit safety checks; never market statistics."""

import hashlib
import importlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

MODULE = "lei_signal.research.factor_lab.classic_attribution"
ROOT = Path(__file__).resolve().parents[2]


def lib():
    return importlib.import_module(MODULE)


def binding(path):
    return {"path": str(path), "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}


@pytest.fixture
def protocol(tmp_path):
    months = pd.period_range("2022-01", "2026-06", freq="M").astype(str)
    rng = np.random.default_rng(12)
    factors = pd.DataFrame(
        {
            "month": months,
            "rf_mon": 0.001,
            "mktrf": rng.normal(0, 0.02, 54),
            "SMB": rng.normal(0, 0.01, 54),
            "VMG": rng.normal(0, 0.01, 54),
        }
    )
    factors.to_csv(tmp_path / "factors.csv", index=False)
    calendar = pd.date_range("2021-12-01", "2026-06-30", freq="B").strftime("%Y-%m-%d").tolist()
    (tmp_path / "calendar.json").write_text(json.dumps({"dates": calendar}))
    dates = (
        pd.Series(pd.to_datetime(calendar))
        .groupby(pd.to_datetime(calendar).to_period("M"))
        .max()
        .dt.strftime("%Y-%m-%d")
        .tolist()
    )
    assets = ["510300.SS", "510050.SS", "510500.SS", "512100.SS", "159915.SZ", "588000.SS"]
    inputs = []
    for symbol in assets:
        y = 0.002 + 1.2 * factors.mktrf + 0.7 * factors.SMB - 0.3 * factors.VMG
        levels = np.r_[1.0, np.cumprod(1 + y.to_numpy() + factors.rf_mon.to_numpy())]
        path = tmp_path / f"{symbol}.csv"
        pd.DataFrame({"date": dates, "economic_index": levels}).to_csv(path, index=False)
        inputs.append(
            {
                "symbol": symbol,
                "files": [binding(path)],
                "date_column": "date",
                "price_column": "economic_index",
            }
        )
    (tmp_path / "qualification.json").write_text(
        json.dumps(
            {"qualified_for": "limited_retrospective_economic_index_month_change_attribution_only"}
        )
    )
    (tmp_path / "strategy-system.md").write_text("Synthetic system source")
    (tmp_path / "strategy-implementation.md").write_text("Synthetic implementation source")
    p = {
        "schema_version": "classic-attribution/1.0",
        "purpose": "retrospective_attribution",
        "root": str(tmp_path),
        "read_only_local": True,
        "market": "CN",
        "currency": "CNY",
        "frequency": "monthly",
        "target": "conditional_economic_index_month_change_minus_rf_once",
        "factor_timing": "same_month_realized_ex_post",
        "unit": "decimal",
        "train_months": months[:24].tolist(),
        "evaluation_months": months[24:].tolist(),
        "assets": assets,
        "economic_inputs": inputs,
        "calendar": binding(tmp_path / "calendar.json"),
        "qualification": binding(tmp_path / "qualification.json"),
        "snapshot": {
            "market": "CN",
            "currency": "CNY",
            "frequency": "monthly",
            "raw_path": "factors.csv",
            "output_path": "factors.csv",
            "raw_sha256": binding(tmp_path / "factors.csv")["sha256"],
            "output_sha256": binding(tmp_path / "factors.csv")["sha256"],
        },
        "registry": binding(ROOT / "docs/research/definitions.v1.json"),
        "definition_refs": [
            "reference.ch3.mktrf@1.0.0",
            "reference.ch3.smb@1.0.0",
            "reference.ch3.vmg@1.0.0",
        ],
        "strategy_files": [
            binding(tmp_path / "strategy-system.md"),
            binding(tmp_path / "strategy-implementation.md"),
        ],
        "code_files": [],
        "source_files": [binding(tmp_path / "factors.csv")],
        "resampling": {"block_lengths": [3, 6], "draws": 2000, "seed": 20261002},
    }
    return p


def write_protocol(p, tmp_path):
    p["code_files"] = [
        binding(Path(lib().__file__)),
        binding(ROOT / "src/lei_signal/research/factor_lab/benchmarks.py"),
        binding(ROOT / "src/lei_signal/research/definitions.py"),
        binding(ROOT / "scripts/run_factor_lab.py"),
    ]
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(p))
    return path


def test_module_available():
    assert importlib.util.find_spec(MODULE) is not None


def test_coefficients_rf_units_and_training_only(protocol, tmp_path):
    path = write_protocol(protocol, tmp_path)
    result = lib().run_attribution(path, tmp_path / "out")
    coef = pd.read_csv(tmp_path / "out" / "coefficients.csv")
    row = coef[(coef.symbol == "510300.SS") & (coef.model == "M3")].iloc[0]
    assert row.intercept == pytest.approx(0.002, abs=1e-12)
    assert row.mktrf == pytest.approx(1.2)
    assert pytest.approx(0.7) == row.SMB
    assert pytest.approx(-0.3) == row.VMG
    assert result["fit_count"] == 24
    assert result["models"]["M3"]["mse_pp2"] < 1e-20
    # Changing only later target cannot change coefficients.
    f = Path(protocol["economic_inputs"][0]["files"][0]["path"])
    data = pd.read_csv(f)
    data.loc[25:, "economic_index"] *= 1.03
    data.to_csv(f, index=False)
    protocol["economic_inputs"][0]["files"] = [binding(f)]
    lib().run_attribution(write_protocol(protocol, tmp_path), tmp_path / "out2")
    pd.testing.assert_frame_equal(coef, pd.read_csv(tmp_path / "out2" / "coefficients.csv"))


@pytest.mark.parametrize(
    "bad",
    [
        "purpose",
        "currency",
        "hash",
        "missing_endpoint",
        "duplicate",
        "unit",
        "rank",
        "existing",
        "timing",
        "refs",
    ],
)
def test_pre_fit_rejections(protocol, tmp_path, monkeypatch, bad):
    path = write_protocol(protocol, tmp_path)
    if bad == "purpose":
        protocol["purpose"] = "prediction"
    if bad == "currency":
        protocol["currency"] = "USD"
    if bad == "hash":
        protocol["calendar"]["sha256"] = "0" * 64
    if bad == "unit":
        protocol["unit"] = "percent"
    if bad == "timing":
        protocol["factor_timing"] = "available_before_decision"
    if bad == "refs":
        protocol["definition_refs"][0] = "reference.ch3.mktrf@9.0.0"
    if bad in {"missing_endpoint", "duplicate"}:
        f = Path(protocol["economic_inputs"][0]["files"][0]["path"])
        d = pd.read_csv(f)
        d = d.iloc[1:] if bad == "missing_endpoint" else pd.concat([d, d.iloc[:1]])
        d.to_csv(f, index=False)
        protocol["economic_inputs"][0]["files"] = [binding(f)]
    if bad == "rank":
        f = tmp_path / "factors.csv"
        d = pd.read_csv(f)
        d["VMG"] = d.SMB
        d.to_csv(f, index=False)
        protocol["snapshot"]["raw_sha256"] = protocol["snapshot"]["output_sha256"] = binding(f)[
            "sha256"
        ]
        protocol["source_files"] = [binding(f)]
    out = tmp_path / "out"
    if bad == "existing":
        out.mkdir()
    path.write_text(json.dumps(protocol))

    def forbidden(*a, **kw):
        raise AssertionError("fit reached before validation")

    monkeypatch.setattr(np.linalg, "lstsq", forbidden)
    with pytest.raises(ValueError):
        lib().run_attribution(path, out)


def test_paired_interval_preserves_month_assets():
    assert lib().block_interval(np.full(30, 2.0), 3, 2000, 20261002) == [2.0, 2.0]


def saved_predictions(tmp_path):
    days = pd.bdate_range("2024-01-01", periods=125).strftime("%Y-%m-%d").tolist()
    rows = []
    for s in lib().ASSETS:
        for d in days:
            for q, b, a in [
                ("已有SMA再加EMA", 0.01, 0.02),
                ("完整信息增加双确认组合表示", 0.03, 0.04),
            ]:
                rows.append(
                    {
                        "date": d,
                        "symbol": s,
                        "target": 0.05,
                        "question_id": q,
                        "baseline": b,
                        "augmented": a,
                    }
                )
    path = tmp_path / "pred.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path, days


def test_old_predictions_zero_fit_and_pp_units(tmp_path, monkeypatch):
    path, days = saved_predictions(tmp_path)
    monkeypatch.setattr(np.linalg, "lstsq", lambda *a, **k: pytest.fail("refitting"))
    r = lib().compare_saved_predictions(path, calendar_dates=days)
    assert r["fit_count"] == 0
    assert r["models"]["fixed_zero"]["mse_pp2"] == pytest.approx(25)
    assert r["models"]["S+E"]["mse_pp2"] == pytest.approx(9)
    assert r["models"]["S+E+X"]["mse_pp2"] == pytest.approx(4)
    assert r["increment"]["improvement_pp2"] == pytest.approx(5)


@pytest.mark.parametrize("bad", ["target", "missing", "duplicate", "gap", "model"])
def test_old_saved_integrity(tmp_path, bad):
    path, days = saved_predictions(tmp_path)
    d = pd.read_csv(path)
    if bad == "target":
        d.loc[0, "target"] = 0.06
    if bad == "missing":
        d = d.iloc[1:]
    if bad == "duplicate":
        d = pd.concat([d, d.iloc[:1]])
    if bad == "gap":
        days.insert(2, "2023-12-31")
    if bad == "model":
        d.loc[len(d)] = {**d.iloc[0].to_dict(), "question_id": "full-again", "augmented": 0.1}
    d.to_csv(path, index=False)
    with pytest.raises(ValueError):
        lib().compare_saved_predictions(
            path, calendar_dates=days, duplicate_models={"S+E": [("full-again", "augmented")]}
        )


def test_cli_rejects_publication_and_reuse(monkeypatch):
    import runpy
    import sys

    for flag in [["--register-report"], ["--reuse-predictions", "x"]]:
        monkeypatch.setattr(
            sys,
            "argv",
            ["run_factor_lab.py", "--attribution-protocol", "no-file", "--out", "unused", *flag],
        )
        with pytest.raises(SystemExit) as e:
            runpy.run_path(str(ROOT / "scripts/run_factor_lab.py"), run_name="__main__")
        assert e.value.code == 2
