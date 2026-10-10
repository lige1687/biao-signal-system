"""Synthetic checks only; no saved real Y is read by these tests."""

import json
import math
import sys

import pytest

import lei_signal.research.native_d_conditional_risk as subject
from lei_signal.research.native_d_conditional_risk import (
    ASSETS,
    UNKNOWN_ID,
    analyze_rows,
    asset_stat,
    average_ranks,
    exclusive_json,
    rank_correlation,
    validate_x,
)


def synthetic_documents():
    counts = (15, 17, 12, 5, 26)
    groups = (6, 7, 5, 3, 11)
    xrows, yrows = [], []
    for asset, n, group_count in zip(ASSETS, counts, groups, strict=True):
        for i in range(n):
            # Five-case asset loses eligibility when its two-case episode is deleted.
            episode = (i * group_count) // n
            a, atr = 10.0, 0.2 + (i % 4) * 0.01
            d = 0.8 + (i % 7) * 0.23 + (i // 7) * 0.07
            v = 100 * atr / a
            identity = dict(
                case_id=f"{asset}:{i}",
                asset=asset,
                signal_date=f"2025-01-{i + 1:02d}",
                lifecycle=f"{asset}:episode:{episode}",
            )
            xrows.append(
                {
                    **identity,
                    "A": a,
                    "C": a - d * atr,
                    "ATR20_SMA": atr,
                    "D_frozen": d,
                    "V_volatility_pct": v,
                    "price_basis_id": "economic_price",
                    "source_sha256": ["a" * 64],
                    "event_ids": [f"event:{asset}:{i}"],
                    "window_metadata": {"calendar_mature_by_20260626": True},
                }
            )
            yrows.append(
                {
                    **identity,
                    "D_frozen": d,
                    "V_volatility_pct": v,
                    "Y": float((i * 3 + episode) % 9),
                    "label_reason": None,
                }
            )
    identity = dict(
        case_id=UNKNOWN_ID,
        asset="588000.SS",
        signal_date="2026-06-16",
        lifecycle="588000.SS:episode:0",
    )
    xrows.append(
        {
            **identity,
            "A": 10.0,
            "C": 9.8,
            "ATR20_SMA": 0.2,
            "D_frozen": 1.0,
            "V_volatility_pct": 2.0,
            "price_basis_id": "economic_price",
            "source_sha256": ["b" * 64],
            "event_ids": ["event:unknown"],
            "window_metadata": {"calendar_mature_by_20260626": False},
        }
    )
    yrows.append(
        {
            **identity,
            "D_frozen": 1.0,
            "V_volatility_pct": 2.0,
            "Y": None,
            "label_reason": "calendar_immature",
        }
    )
    # Eight aliases are additional identities of existing cases, not extra rows.
    for row in xrows[:8]:
        row["event_ids"].append(f"alias:{row['case_id']}")
    return xrows, yrows


def test_average_ties_and_partial_confounding_formula():
    assert average_ranks([10, 20, 20, 40]) == [1, 2.5, 2.5, 4]
    rows = [
        dict(asset="510050.SS", lifecycle=f"episode:{i // 2}", case_id=str(i), D=d, V=v, Y=y)
        for i, (d, v, y) in enumerate(
            zip([1, 2, 4, 5, 3, 6], [1, 3, 2, 6, 4, 5], [2, 4, 1, 5, 6, 3], strict=True)
        )
    ]
    result = asset_stat(rows, "510050.SS")
    dy = rank_correlation([r["D"] for r in rows], [r["Y"] for r in rows])
    dv = rank_correlation([r["D"] for r in rows], [r["V"] for r in rows])
    vy = rank_correlation([r["V"] for r in rows], [r["Y"] for r in rows])
    expected = (dy - dv * vy) / math.sqrt((1 - dv * dv) * (1 - vy * vy))
    assert result["partial_DY_given_V"] == pytest.approx(expected)
    assert result["partial_DY_given_V"] != pytest.approx(dy)


def test_constant_denominator_and_episode_support_are_null():
    rows = [
        dict(
            asset="510050.SS",
            lifecycle=f"episode:{i // 2}",
            case_id=str(i),
            D=i,
            V=i,
            Y=[1, 3, 2, 4][i],
        )
        for i in range(4)
    ]
    assert asset_stat(rows, "510050.SS")["reason"] == "nonpositive_partial_denominator"
    for row in rows:
        row["V"] = 1
    assert asset_stat(rows, "510050.SS")["reason"] == "constant_rank_column"
    for i, row in enumerate(rows):
        row["V"] = [1, 3, 2, 4][i]
        row["lifecycle"] = "one_episode"
    assert asset_stat(rows, "510050.SS")["reason"] == "fewer_than_two_source_episodes"


def test_full_population_fixed_weights_and_33_group_deletions():
    xrows, yrows = synthetic_documents()
    assert len(validate_x({"schema": "native-risk-d-mae-real-x/1", "rows": xrows})) == 76
    result = analyze_rows(xrows, yrows)
    assert result["mature_count"] == 75 and result["cases"][-1]["Y"] is None
    assert len(result["delete_33"]) == 33
    assert set(result["main"]["fixed_weights"].values()) == {0.2}
    for trial in result["delete_33"]:
        assert trial["result"]["fixed_assets"] == list(ASSETS)
        assert trial["result"]["fixed_weights"] == result["main"]["fixed_weights"]
    # The five-case ETF becomes under-supported in at least one deletion.
    assert any(
        t["result"]["equal_asset_mean"] is None
        for t in result["delete_33"]
        if t["asset"] == "512400.SS"
    )
    assert all(
        t["result"]["reason"] == "at_least_one_fixed_asset_ineligible"
        for t in result["delete_33"]
        if t["result"]["equal_asset_mean"] is None
    )


def test_identity_and_unknown_cannot_change():
    xrows, yrows = synthetic_documents()
    yrows[0]["asset"] = "wrong"
    with pytest.raises(ValueError, match="identity drift"):
        analyze_rows(xrows, yrows)
    yrows[0]["asset"] = xrows[0]["asset"]
    yrows[-1]["Y"] = 1.0
    with pytest.raises(ValueError, match="unknown filled"):
        analyze_rows(xrows, yrows)


def test_one_start_marker_is_exclusive(tmp_path):
    path = tmp_path / "attempt-ledger.json"
    exclusive_json(path, {"event": "core_start"})
    with pytest.raises(FileExistsError):
        exclusive_json(path, {"event": "second_start"})
    assert path.read_text().count("core_start") == 1


def test_group_and_membership_drift_rejected():
    xrows, yrows = synthetic_documents()
    xrows[0]["lifecycle"] = "extra_episode"
    with pytest.raises(ValueError, match="source episode count"):
        validate_x({"schema": "native-risk-d-mae-real-x/1", "rows": xrows})
    xrows, yrows = synthetic_documents()
    yrows[0]["case_id"] = "new-case"
    with pytest.raises(ValueError, match="membership drift"):
        analyze_rows(xrows, yrows)


def test_qualify_does_not_parse_y_and_analyze_has_one_start(tmp_path, monkeypatch):
    xrows, yrows = synthetic_documents()
    xfile, yfile = tmp_path / "x.json", tmp_path / "y.json"
    xfile.write_text(json.dumps({"schema": subject.X_SCHEMA, "rows": xrows}))
    yfile.write_text(json.dumps({"schema": subject.Y_SCHEMA, "mature_count": 75, "rows": yrows}))
    output = tmp_path / "result"
    output.mkdir()
    contract_path = tmp_path / subject.CONTRACT_REL
    contract_path.parent.mkdir(parents=True)
    ledger_path = tmp_path / subject.LEDGER_REL
    contract = {
        "input": {
            "x_path": str(xfile),
            "y_path": str(yfile),
            "x_sha256": "synthetic-x",
            "y_sha256": "synthetic-y",
        },
        "attempt_ledger": str(subject.LEDGER_REL),
    }
    contract_path.write_text(json.dumps(contract))
    monkeypatch.setattr(
        subject, "__file__", str(tmp_path / "src/lei_signal/research/native_d_conditional_risk.py")
    )
    plan = {"external_mount": str(tmp_path), "external_device": tmp_path.stat().st_dev}
    monkeypatch.setattr(subject, "load_contract", lambda _: (contract, plan, output))
    # This synthetic hash probe is allowed to see bytes but must not parse Y.
    monkeypatch.setattr(subject, "check_input_hashes", lambda _: yfile.read_bytes())
    original_loads = subject.json.loads

    def guard_y_parse(value, *args, **kwargs):
        if '"mature_count"' in value and not ledger_path.exists():
            raise AssertionError("Y parsed before core start")
        return original_loads(value, *args, **kwargs)

    monkeypatch.setattr(subject.json, "loads", guard_y_parse)
    assert subject.qualify(contract_path)["real_y_values_parsed"] is False
    assert not ledger_path.exists()
    assert subject.analyze(contract_path)["case_count"] == 76
    ledger = json.loads(ledger_path.read_text())
    assert [e["event"] for e in ledger["events"]] == ["core_start", "core_complete"]
    monkeypatch.chdir(tmp_path / "docs")
    with pytest.raises(ValueError, match="core already started"):
        subject.analyze(contract_path)


def test_one_ledger_is_bound_across_working_directories(tmp_path, monkeypatch):
    contract_path = tmp_path / subject.CONTRACT_REL
    contract_path.parent.mkdir(parents=True)
    contract = {"attempt_ledger": str(subject.LEDGER_REL)}
    monkeypatch.setattr(
        subject, "__file__", str(tmp_path / "src/lei_signal/research/native_d_conditional_risk.py")
    )
    monkeypatch.chdir(tmp_path)
    first = subject.resolve_ledger_path(contract_path, contract)
    monkeypatch.chdir(tmp_path / "docs")
    assert subject.resolve_ledger_path(contract_path, contract) == first
    first.parent.mkdir(parents=True)
    exclusive_json(first, {"event": "core_start"})
    assert subject.resolve_ledger_path(contract_path, contract).exists()
    with pytest.raises(FileExistsError):
        exclusive_json(subject.resolve_ledger_path(contract_path, contract), {"event": "second"})
    with pytest.raises(ValueError, match="ledger location drift"):
        subject.resolve_ledger_path(contract_path, {"attempt_ledger": "attempt-ledger.json"})
    with pytest.raises(ValueError, match="contract location drift"):
        subject.resolve_ledger_path(tmp_path / "copied-contract.json", contract)


def test_cli_analyze_stdout_is_small_summary(tmp_path, monkeypatch, capsys):
    contract_path = tmp_path / "synthetic-contract.json"
    contract_path.write_text(json.dumps({"allowed_output": str(tmp_path / "result")}))
    secret_case = "case:SECRET-IDENTITY"
    monkeypatch.setattr(
        subject,
        "analyze",
        lambda _: {
            "case_count": 76,
            "cases": [{"case_id": secret_case, "D": 1.23, "V": 4.56, "Y": 7.89}],
        },
    )
    monkeypatch.setattr(sys, "argv", ["native-d", "--contract", str(contract_path), "--analyze"])
    subject.main()
    output = capsys.readouterr().out
    assert json.loads(output) == {
        "stage": "analyze",
        "result": "passed",
        "cases": 76,
        "output": str(tmp_path / "result"),
    }
    assert all(
        value not in output for value in (secret_case, '"D"', '"V"', '"Y"', "1.23", "4.56", "7.89")
    )
