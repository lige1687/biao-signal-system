"""Synthetic boundaries for the read-only multiple-loss adapter."""
from pathlib import Path
import sys

import pytest
from datetime import date, timedelta

SCRIPTS = Path(__file__).resolve().parents[2] / ".agents/skills/lei-quant-tools/scripts"
sys.path.insert(0, str(SCRIPTS))
import multiple_comparison as mc


def packet():
    days = [f"2025-01-0{i}" for i in range(1, 7)]
    return {
        "schema_version": mc.SCHEMA, "unit": "percentage_point_squared",
        "frequency": "qualified_session", "calendar": days,
        "benchmark_id": "B0", "candidate_ids": ["good", "bad"],
        "block_size": 2, "reps": 40, "seed": 7,
        "rows": [
            {"date": d, "benchmark_loss": float(b),
             "models": {"good": float(g), "bad": float(w)}}
            for d, b, g, w in zip(days,
                                  [5, 7, 3, 8, 4, 6],
                                  [3, 6, 1, 7, 3, 5],
                                  [7, 8, 6, 9, 5, 9])
        ],
    }


def test_joint_comparison_is_reproducible_and_retains_negative_candidate():
    data = packet()
    first = mc.compare_losses(data)
    second = mc.compare_losses(data)
    assert first == second
    assert first["status"] == "computed"
    assert first["studentize"] is False and first["primary_pvalue"] == "upper"
    assert 0 <= first["upper_pvalue"] <= 1
    assert first["mean_improvements"]["good"] > 0
    assert first["mean_improvements"]["bad"] < 0
    assert first["daily_rows"] == len(data["calendar"])


@pytest.mark.parametrize("change", [
    lambda d: d["rows"].pop(),
    lambda d: d["rows"][1].update(date=d["rows"][0]["date"]),
    lambda d: d["rows"][0]["models"].pop("bad"),
    lambda d: d.update(candidate_ids=["good", "good"]),
    lambda d: d["rows"][2]["models"].update(good=True),
    lambda d: d["rows"][2].update(benchmark_loss=-1),
    lambda d: d["rows"][2].update(benchmark_loss=float("inf")),
    lambda d: d["rows"][2].update(benchmark_loss=1e308),
    lambda d: d["rows"][2].update(benchmark_loss=10**1000),
    lambda d: d.update(block_size=7),
    lambda d: d.update(reps=mc.MAX_REPS + 1),
    lambda d: d.update(seed=-1),
    lambda d: d.update(unit="return"),
    lambda d: d.update(frequency="weekly"),
])
def test_packet_rejections(change):
    data = packet()
    change(data)
    with pytest.raises(ValueError):
        mc.compare_losses(data)


def test_identical_distinct_candidates_rejected():
    data = packet()
    for row in data["rows"]:
        row["models"]["bad"] = row["models"]["good"]
    with pytest.raises(ValueError, match="identical losses"):
        mc.compare_losses(data)


def test_nonconstant_alternating_losses_cannot_produce_zero_tie_pvalue():
    days = [(date(2020, 1, 1) + timedelta(days=i)).isoformat() for i in range(120)]
    data = {"schema_version": mc.SCHEMA, "unit": "percentage_point_squared",
            "frequency": "qualified_session", "calendar": days,
            "benchmark_id": "reference", "candidate_ids": ["alternating"],
            "block_size": 20, "reps": 1000, "seed": 20261002,
            "rows": [{"date": day, "benchmark_loss": 10.,
                      "models": {"alternating": 9. if i % 2 else 11.}}
                     for i, day in enumerate(days)]}
    with pytest.raises(ValueError, match="degenerate resampled maximum"):
        mc.compare_losses(data)


@pytest.mark.parametrize("offset", [0.0, 1.0, -1.0])
def test_constant_difference_rejected_including_exact_tie(offset):
    data = packet()
    for row in data["rows"]:
        row["models"]["good"] = row["benchmark_loss"] + offset
    with pytest.raises(ValueError, match="constant loss differential"):
        mc.compare_losses(data)


def _fake_run(name, dates, *, bad_identity=False, bad_baseline=False, not_ready=False):
    contract = {"question": {"primary_metric": "MSE"}, "universe": {"assets": ["A", "B"]}}
    rows = []
    for index, day in enumerate(dates):
        for asset in ("A", "B"):
            rows.append({"asset": asset, "date": day, "id": f"{asset}-{day}" + ("x" if bad_identity else ""),
                         "fold": "f1", "y": 1.0, "label_end": day,
                         "B0": 2.0 if bad_baseline else 0.0,
                         "B1": 0.0, "B2": 0.3 + index * 0.07 + (0.1 if name == "second" else 0.0)})
    result = {"predictions": rows}
    source = {"run_dir": name}
    summary = {"status": "not_applicable" if not_ready else "ready",
               "reasons": ["missing planned dates"] if not_ready else []}
    ready = None if not_ready else {"calendar": dates, "unit": "percentage_point_squared"}
    return (contract, result, {}, source), (summary, ready)


def test_workflow_pairing_and_not_applicable(monkeypatch):
    days = packet()["calendar"]
    runs = {name: _fake_run(name, days) for name in ("first", "second")}
    monkeypatch.setattr(mc, "read_archived_run", lambda name: runs[name][0])
    monkeypatch.setattr(mc, "prepare_workflow_input", lambda contract, result, proof, **kw:
                        next(v[1] for v in runs.values() if v[0][1] is result))
    result = mc.compare_workflows(["first", "second"], days[0], days[-1], "B0", 2, 40, 7)
    assert result["status"] == "computed" and result["fits"] == 0
    assert result["asset_count"] == 2
    runs["second"] = _fake_run("second", days, bad_identity=True)
    result = mc.compare_workflows(["first", "second"], days[0], days[-1], "B0", 2, 40, 7)
    assert result["status"] == "not_applicable"
    runs["second"] = _fake_run("second", days, bad_baseline=True)
    result = mc.compare_workflows(["first", "second"], days[0], days[-1], "B0", 2, 40, 7)
    assert result["status"] == "not_applicable"
    runs["second"] = _fake_run("second", days, not_ready=True)
    result = mc.compare_workflows(["first", "second"], days[0], days[-1], "B0", 2, 40, 7)
    assert result["status"] == "not_applicable" and result["fits"] == 0


def test_workflow_target_and_asset_date_mismatch(monkeypatch):
    days = packet()["calendar"]
    runs = {name: _fake_run(name, days) for name in ("first", "second")}
    monkeypatch.setattr(mc, "read_archived_run", lambda name: runs[name][0])
    monkeypatch.setattr(mc, "prepare_workflow_input", lambda contract, result, proof, **kw:
                        next(v[1] for v in runs.values() if v[0][1] is result))
    for field, value in [("y", 4.0), ("label_end", days[-1]), ("asset", "C"), ("date", days[-1])]:
        runs["second"] = _fake_run("second", days)
        runs["second"][0][1]["predictions"][0][field] = value
        result = mc.compare_workflows(["first", "second"], days[0], days[-1], "B0", 2, 40, 7)
        assert result["status"] == "not_applicable", field
