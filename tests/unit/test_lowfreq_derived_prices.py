import hashlib
import json
import sys
import types
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import pytest

from lei_signal.research import lowfreq_derived_prices as derived


FIELDS = ["date", "code", "open", "high", "low", "close", "preclose", "volume", "amount", "adjustflag", "tradestatus", "isST"]
PRICE = ("open", "high", "low", "close", "preclose")


def _write(tmp, name, value):
    path = tmp / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def _replace(binding, payload):
    path = Path(binding["path"])
    path.write_text(json.dumps(payload), encoding="utf-8")
    binding["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()


def _setup(tmp, monkeypatch):
    monkeypatch.setattr(derived, "EXPECTED_ROWS", 1)
    monkeypatch.setattr(derived, "EXPECTED_SOURCES", 1)
    monkeypatch.setattr(derived, "EXPECTED_BASE_ROWS", 1)
    evaluator_path = tmp / "evaluator.py"
    evaluator_path.write_text("# frozen evaluator stub")
    evaluator = {"path": str(evaluator_path), "sha256": hashlib.sha256(evaluator_path.read_bytes()).hexdigest()}
    monkeypatch.setattr(derived, "find_spec", lambda _: types.SimpleNamespace(origin=str(evaluator_path)))
    monkeypatch.setitem(sys.modules, "lei_signal.research.lowfreq_discovery",
                        types.SimpleNamespace(_cohort=lambda *_: ([derived.TARGET], 1, {derived.TARGET: {"ipo": "2000-01-01", "out": None}}),
                                              _calendar=lambda *_: ["2013-01-04"]))
    monkeypatch.setattr(derived, "inspect_contract", lambda *_: {"status": "blocked", "source_count": 1,
        "row_count": 1, "blockers": {"returned_adjustflag": {"count": 1, "by_code": {derived.TARGET: 1}}}})
    original_fields = ["code", "date"] + FIELDS[2:]
    original_values = [derived.TARGET, "2013-01-04", "10", "11", "9", "10", "9", "100", "1000", "3", "1", "0"]
    legacy_values = ["2013-01-04", derived.LEGACY, "8", "9", "7", "8", "7", "100", "1000", "2", "1", "0"]
    original = _write(tmp, "original.json", {"fields": original_fields, "error_code": "0", "data": [original_values]})
    original.update({"code": derived.TARGET, "status": "ok", "request": {"code": derived.TARGET, "frequency": "d", "adjustflag": "2"}})
    legacy = _write(tmp, "legacy.json", {"method": "query_history_k_data_plus", "kwargs": {},
        "status": "ok", "fields": FIELDS, "error_code": "0", "rows": [legacy_values],
        "error_msg": "success", "exception": None})
    old_prices = dict(zip(PRICE, legacy_values[2:7]))
    source_prices = dict(zip(PRICE, original_values[2:7]))
    derived_prices = {key: str(Decimal(value) * derived.FACTOR) for key, value in old_prices.items()}
    change = {"date": "2013-01-04", "canonical_code": derived.TARGET, "source_adjustflag": "3",
              "source_price_values": source_prices, "legacy_code": derived.LEGACY,
              "legacy_adjusted_values": old_prices, "derived_adjusted_values": derived_prices,
              "formula": "legacy_adjusted_value * 0.91352"}
    overlay_payload = {"schema": "research.price-correction-overlay/1", "vendor_original": False,
                       "source": original, "original_source_adjustflag_preserved": True,
                       "normalization": "0.91352", "allowed_fields": list(PRICE),
                       "derived_price_basis": "historical derived", "changes": [change]}
    overlay = _write(tmp, "overlay.json", overlay_payload)
    design = _write(tmp, "design.json", {"universe": {"asof": "2014-12-31", "sample_size": 1}})
    cohort = _write(tmp, "cohort.json", {"fields": ["code"], "data": [[derived.TARGET]]})
    calendar = _write(tmp, "calendar.json", {"fields": ["calendar_date"], "data": [["2013-01-04"]]})
    base = _write(tmp, "base.json", {"schema": "lowfreq-evaluator-contract/1", "design": design,
        "cohort": cohort, "calendar": calendar, "sources": [original]})
    review = _write(tmp, "review.json", {"status": "derived_source_consistency_checked_evaluator_integration_required",
                                  "market_statistics_calls": 0})
    manifest = {"schema": "lowfreq-derived-price-input/1", "base_contract": base, "overlay": overlay,
                "legacy_adjusted": legacy, "evaluator": evaluator, "prior_review": review}
    return manifest, overlay_payload, original, legacy


def test_clean_load_only_changes_five_in_memory_prices(tmp_path, monkeypatch):
    manifest, overlay, original, _ = _setup(tmp_path, monkeypatch)
    original_sha = original["sha256"]
    design, selected, membership, calendar, sources, qualification = derived.load_derived_sources(manifest)
    assert selected == [derived.TARGET]
    assert calendar == ["2013-01-04"]
    assert qualification["status"] == "conditional_derived_historical_only"
    assert qualification["source_count"] == 1 and qualification["row_count"] == 1
    assert qualification["provenance"]["legacy_adjusted_sha256"] == manifest["legacy_adjusted"]["sha256"]
    assert qualification["provenance"]["guard_sha256"]
    assert qualification["source_adjustflag_preserved"]
    row = dict(zip(sources[derived.TARGET]["data"]["fields"], sources[derived.TARGET]["data"]["data"][0]))
    assert row["adjustflag"] == "3" and row["amount"] == "1000"
    assert row["close"] == overlay["changes"][0]["derived_adjusted_values"]["close"]
    assert hashlib.sha256(Path(original["path"]).read_bytes()).hexdigest() == original_sha


@pytest.mark.parametrize("mutate", [
    lambda x: x["changes"][0].update(source_adjustflag="2"),
    lambda x: x["changes"][0].update(date="2013-01-05"),
    lambda x: x["changes"][0]["derived_adjusted_values"].update(close="999"),
    lambda x: x["changes"][0]["legacy_adjusted_values"].update(close="999"),
    lambda x: x["changes"][0]["source_price_values"].update(close="999"),
    lambda x: x["changes"][0]["derived_adjusted_values"].update(volume="1"),
    lambda x: x["changes"][0]["derived_adjusted_values"].update(close="nan"),
    lambda x: x["changes"][0]["derived_adjusted_values"].update(close="-1"),
])
def test_overlay_mutations_fail_closed(tmp_path, monkeypatch, mutate):
    manifest, payload, _, _ = _setup(tmp_path, monkeypatch)
    altered = deepcopy(payload)
    mutate(altered)
    _replace(manifest["overlay"], altered)
    with pytest.raises(ValueError):
        derived.load_derived_sources(manifest)


def test_legacy_source_and_extra_base_blocker_fail(tmp_path, monkeypatch):
    manifest, _, _, legacy = _setup(tmp_path, monkeypatch)
    payload = json.loads(Path(legacy["path"]).read_text())
    payload["rows"][0][5] = "999"
    _replace(legacy, payload)
    with pytest.raises(ValueError, match="source price mismatch"):
        derived.load_derived_sources(manifest)
    monkeypatch.setattr(derived, "inspect_contract", lambda *_: {"status": "blocked", "source_count": 1,
        "row_count": 1, "blockers": {"returned_adjustflag": {"count": 1, "by_code": {derived.TARGET: 1}},
                                      "invalid_number": {"count": 1}}})
    with pytest.raises(ValueError, match="sole known flag break"):
        derived.load_derived_sources(manifest)
