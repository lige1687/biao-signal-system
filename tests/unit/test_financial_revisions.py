import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "financial_revisions", Path(__file__).parents[2] / "src/lei_signal/research/financial_revisions.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


@pytest.fixture
def bundle(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("synthetic boundary fixture")
    common = {"code": "TEST", "metric": "cost", "period_end": "2023-12-31",
              "unit": "CNY", "retrieved_at": "2026-10-20T10:00:00+08:00",
              "vendor_available_at": None,
              "source": {"path": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                         "locator": "synthetic fixture only"}}
    return {"schema": "financial-source-versions/1", "publication_timezone": "Asia/Shanghai",
            "records": [{**common, "version": "original", "value": "100", "published_at": "2024-03-27"},
                        {**common, "version": "revised", "value": "110", "published_at": "2025-03-26"}]}


def test_future_revision_does_not_rewrite_prior_decision(bundle):
    old = copy.deepcopy(bundle)
    old["records"] = old["records"][:1]
    before = module.select_versions(old, "2024-06-01T09:30:00+08:00")
    after = module.select_versions(bundle, "2024-06-01T09:30:00+08:00")
    assert before["selected"] == after["selected"]
    assert after["selected"][0]["value"] == "100"
    assert module.select_versions(bundle, "2025-04-01T09:30:00+08:00")["selected"][0]["value"] == "110"


def test_same_day_and_vendor_unknown_are_not_invented(bundle):
    same = module.select_versions(bundle, "2025-03-26T09:30:00+08:00")
    assert not same["qualified_for_declared_time_basis"]
    assert same["unresolved"][0]["reason"] == "availability_unknown"
    vendor = module.select_versions(bundle, "2025-04-01T09:30:00+08:00", availability_basis="vendor")
    assert not vendor["selected"]


def test_exact_boundary_and_timezone(bundle):
    bundle["records"] = bundle["records"][:1]
    bundle["records"][0]["published_at"] = "2024-03-27T01:30:00+00:00"
    assert not module.select_versions(bundle, "2024-03-27T09:30:00+08:00")["selected"]
    assert module.select_versions(bundle, "2024-03-27T09:30:01+08:00")["selected"]
    with pytest.raises(ValueError, match="timezone"):
        module.select_versions(bundle, "2024-03-28T09:30:00")


def test_different_metrics_and_periods_are_not_collapsed(bundle):
    extra = copy.deepcopy(bundle["records"][0])
    extra.update(metric="sales", value="200")
    bundle["records"].append(extra)
    extra = copy.deepcopy(extra)
    extra.update(period_end="2022-12-31")
    bundle["records"].append(extra)
    assert len(module.select_versions(bundle, "2025-04-01T09:30:00+08:00")["selected"]) == 3


@pytest.mark.parametrize("damage", ["hash", "duplicate", "unit", "infinity", "time"])
def test_invalid_bundle_rejected(bundle, tmp_path, damage):
    if damage == "hash":
        bundle["records"][0]["source"]["sha256"] = "0" * 64
    elif damage == "duplicate":
        bundle["records"].append(bundle["records"][0])
    elif damage == "unit":
        bundle["records"][1]["unit"] = "CNY million"
    elif damage == "infinity":
        bundle["records"][0]["value"] = "Infinity"
    else:
        bundle["records"][0]["retrieved_at"] = "2020-01-01T00:00:00+08:00"
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(bundle))
    with pytest.raises(ValueError):
        module.load_bundle(path)


def test_unknown_version_order_rejected(bundle):
    bundle["records"][1]["published_at"] = bundle["records"][0]["published_at"]
    result = module.select_versions(bundle, "2025-04-01T09:30:00+08:00")
    assert result["unresolved"][0]["reason"] == "version_order_ambiguous"


def test_partial_metric_coverage_does_not_pass(bundle):
    extra = copy.deepcopy(bundle["records"][1])
    extra["metric"] = "assets"
    bundle["records"].append(extra)
    result = module.select_versions(bundle, "2024-06-01T09:30:00+08:00")
    assert result["selected"]
    assert not result["qualified_for_declared_time_basis"]
    assert result["missing_series"] == [("TEST", "assets", "2023-12-31")]


def test_wide_earlier_interval_can_overlap_latest_of_three_versions(bundle):
    first = bundle["records"][0]
    second = copy.deepcopy(first)
    second.update(version="second", published_at="2024-03-27T09:00:00+08:00")
    third = copy.deepcopy(first)
    third.update(version="third", published_at="2024-03-27T10:00:00+08:00")
    bundle["records"] = [first, second, third]
    result = module.select_versions(bundle, "2024-03-28T09:30:00+08:00")
    assert not result["selected"]
    assert result["unresolved"][0]["reason"] == "version_order_ambiguous"
