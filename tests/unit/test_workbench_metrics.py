"""Display metrics must remain tied to frozen, date-complete sources."""

import hashlib
import json
import math
from pathlib import Path

import pytest

from lei_signal.research import workbench_metrics as metrics


def test_sample_dispersion_and_unannualized_icir():
    ratio, sd, reason = metrics._metric([0.1, 0.2, 0.3])
    assert ratio == pytest.approx(2.0)
    assert sd == pytest.approx(0.1)
    assert reason is None
    annual, _, _ = metrics._metric([0.1, 0.2, 0.3], annualize=True)
    assert annual == pytest.approx(2 * math.sqrt(12))
    assert metrics._metric([0.1])[2] == "fewer_than_two_finite_months"
    assert metrics._metric([0.1, 0.1])[2] == "zero_sample_standard_deviation"


def test_twelve_month_window_never_spans_gap():
    points = [(f"2025-{month:02d}", float(month)) for month in range(1, 13)]
    assert metrics._rolling(points, annualize=False)[-1][1:] == pytest.approx([6.5, 6.5 / math.sqrt(13)])
    with_gap = points[:6] + points[7:]
    assert all(row[1:] == [None, None] for row in metrics._rolling(with_gap, annualize=False))
    with_null = points.copy()
    with_null[3] = (with_null[3][0], None)
    assert metrics._rolling(with_null, annualize=True)[-1][1:] == [None, None]
    with pytest.raises(ValueError, match="duplicate month"):
        metrics._unique_months([["2025-01-01"], ["2025-01-31"]])


def test_ir_requires_exact_period_and_preserves_fee_and_unknown_valuation():
    dataset = {"id": "synthetic", "limitations": ["source caveat"]}
    rows = [
        {"month": f"2025-{month:02d}", "return": month / 100 + 0.02,
         "benchmarkReturn": 0.02, "excessReturn": month / 100,
         "unknownMax": month / 1000}
        for month in range(1, 13)
    ]
    record = metrics._ir_record(dataset, "all", ["2025-01", "2025-12"],
                                "all_qualified__momentum__G5__fee25", rows)
    assert record["feeBps"] == 25
    assert record["trackingErrorFrequency"] == "monthly"
    assert record["irAnnualization"] == 12
    assert record["nPeriods"] == 12
    assert record["meanExcess"] == pytest.approx(0.065)
    assert record["ir"] == pytest.approx(0.065 / math.sqrt(0.0013) * math.sqrt(12))
    assert record["points"][-1][2] == pytest.approx(record["ir"])
    assert record["unknownMax"] == pytest.approx(0.012)
    missing = metrics._ir_record(dataset, "all", ["2025-01", "2025-12"],
                                 "all_qualified__momentum__G5__fee25", rows[:-1])
    assert missing["ir"] is None
    assert missing["reason"] == "missing_or_invalid_month_in_period"
    nonfinite = [dict(row) for row in rows]
    nonfinite[3]["excessReturn"] = None
    invalid = metrics._ir_record(dataset, "all", ["2025-01", "2025-12"],
                                 "all_qualified__momentum__G5__fee25", nonfinite)
    assert invalid["ir"] is None
    assert invalid["points"][3][1] is None
    missing_benchmark = [dict(row) for row in rows]
    missing_benchmark[3]["benchmarkReturn"] = None
    invalid_benchmark = metrics._ir_record(dataset, "all", ["2025-01", "2025-12"],
                                           "all_qualified__momentum__G5__fee25", missing_benchmark)
    assert invalid_benchmark["ir"] is None
    assert invalid_benchmark["points"][3][1] is None
    broken = [dict(row) for row in rows]
    broken[3]["excessReturn"] = 0.99
    with pytest.raises(ValueError, match="monthly excess"):
        metrics._ir_record(dataset, "all", ["2025-01", "2025-12"],
                           "all_qualified__momentum__G5__fee25", broken)


def test_g5_return_correlation_sign_counts_and_constant_series():
    def record(factor, values):
        return {"datasetId": "d", "poolId": "p", "periodId": "all", "feeBps": 25,
                "factorId": factor, "returns": [(f"2025-0{i}", value) for i, value in enumerate(values, 1)]}

    result = metrics._correlations([
        record("a", [1, 2, 3]), record("b", [2, 4, 6]),
        record("c", [-1, -2, -3]), record("d", [1, 1, 1]),
    ])[0]
    assert result["factorIds"] == ["a", "b", "c", "d"]
    assert result["matrix"][0][1] == pytest.approx(1)
    assert result["matrix"][0][2] == pytest.approx(-1)
    assert result["matrix"][0][3] is None
    assert result["counts"][0][3] == 3


def test_pinned_source_path_cannot_escape_research_directory():
    with pytest.raises(ValueError, match="escapes research directory"):
        metrics._read_pinned(metrics.REPO_ROOT, "/research/../../../../AGENTS.md", "0" * 64, {})


def test_source_hash_mismatch_stops_generation(monkeypatch):
    original = Path.read_bytes

    def altered(path):
        data = original(path)
        if str(path).endswith("legacy-summary.json"):
            return data + b" "
        return data

    monkeypatch.setattr(Path, "read_bytes", altered)
    with pytest.raises(ValueError, match="source hash mismatch"):
        metrics.build_metrics()


def test_frozen_generation_links_sources_and_keeps_capability_limits():
    output = metrics.build_metrics()
    assert output["schemaVersion"] == 1
    assert len(output["icRecords"]) == 112
    assert len(output["irRecords"]) == 224
    assert len(output["sources"]) == 7
    assert "Pearson IC" in output["missingCapabilities"]
    assert all(record["feeBps"] in (0, 25) for record in output["irRecords"])
    assert all(record["kind"] == "g5_monthly_return" for record in output["correlations"])


def test_emitted_manifest_binds_exact_metric_bytes():
    directory = metrics.REPO_ROOT / "web/public/research/factor-workbench-20261024"
    manifest = json.loads((directory / "manifest.json").read_text())
    payload = (directory / "metrics.json").read_bytes()
    assert manifest["schemaVersion"] == 1
    assert manifest["generatorVersion"] == 1
    assert manifest["dataUrl"] == "/research/factor-workbench-20261024/metrics.json"
    assert manifest["sha256"] == hashlib.sha256(payload).hexdigest()
    assert manifest["sources"] == json.loads(payload)["sources"]
