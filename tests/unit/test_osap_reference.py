"""Synthetic local vintages exercise the OSAP reference boundary."""

import csv
import hashlib
import json
from pathlib import Path

import pytest

from lei_signal.research import osap_reference as osap


def _write_csv(path: Path, header, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def _vintage(root: Path, name="v1", *, catalog_rows=None, return_rows=None,
             return_header=None):
    root.mkdir()
    catalog_rows = catalog_rows or [{"Acronym": "AAA", "Sign": "-1"},
                                    {"Acronym": "BBB", "Sign": "1"}]
    header = list(osap.CATALOG_FIELDS)
    _write_csv(root / "catalog.csv", header,
               [[row.get(field, "") for field in header] for row in catalog_rows])
    _write_csv(root / "returns.csv", return_header or ["date", "AAA", "BBB"],
               return_rows or [["1926-01-30", "2.5", "NA"],
                               ["1926-02-27", "-1", "3"]])
    spec = {"schema": osap.SCHEMA, "vintage": name, "market": "US",
            "retrieved_at": "2026-10-20T10:00:00+08:00", "published_at": None,
            "catalog": {"path": "catalog.csv", "sha256": hashlib.sha256((root / "catalog.csv").read_bytes()).hexdigest()},
            "returns": {"path": "returns.csv", "sha256": hashlib.sha256((root / "returns.csv").read_bytes()).hexdigest()},
            "return_unit": "percent", "return_direction": "published_long_short"}
    manifest = root / "manifest.json"
    manifest.write_text(json.dumps(spec), encoding="utf-8")
    return manifest


def test_catalog_and_series_preserve_raw_fields_and_sign(tmp_path):
    ref = osap.load_reference(_vintage(tmp_path / "v1"))
    card = osap.catalog(ref, signal="AAA")
    assert card["rows"][0]["Sign"] == "-1"
    assert card["columns"] == list(osap.CATALOG_FIELDS)
    assert osap.catalog(ref, term="aaa")["count"] == 1
    result = osap.series(ref, ["AAA", "BBB"])
    assert result["date_range"] == ["1926-01-30", "1926-02-27"]
    assert result["rows"][0]["returns"]["AAA"] == {"percent": 2.5, "decimal": 0.025}
    assert result["rows"][0]["returns"]["BBB"] == {"percent": None, "decimal": None}
    assert result["missing_count"] == {"AAA": 0, "BBB": 1}
    assert result["execution_authorized"] is False
    assert result["market"] == "US"
    assert result["bindings"]["returns"]["sha256"]
    assert result["manifest_path"] == ref["manifest_path"]
    assert "stock-level" in " ".join(result["limitations"])


def test_revisions_compare_catalog_dates_values_and_missing(tmp_path):
    old = osap.load_reference(_vintage(tmp_path / "old"))
    new = osap.load_reference(_vintage(
        tmp_path / "new", name="v2",
        catalog_rows=[{"Acronym": "AAA", "Sign": "1"}, {"Acronym": "CCC"}],
        return_header=["date", "AAA", "CCC"],
        return_rows=[["1926-01-29", "NA", "4"], ["1926-02-27", "5", "6"]]))
    change = osap.diff(old, new)
    assert change["catalog_changed"]["AAA"]["Sign"] == {"old": "-1", "new": "1"}
    assert change["catalog_added"] == ["CCC"]
    assert change["catalog_removed"] == ["BBB"]
    assert change["dates_added"] == ["1926-01-29"]
    assert change["dates_removed"] == ["1926-01-30"]
    assert change["return_signals_added"] == ["CCC"]
    assert change["return_signals_removed"] == ["BBB"]
    assert change["return_changes"] == [{"date": "1926-02-27", "signal": "AAA",
                                         "old_percent": -1.0, "new_percent": 5.0}]


@pytest.mark.parametrize("overrides,error", [
    ({"return_unit": None}, "unit/direction"),
    ({"return_direction": "sign_adjusted"}, "unit/direction"),
    ({"retrieved_at": "2026-10-20"}, "timezone"),
    ({"market": "CN"}, "market"),
])
def test_invalid_manifest(tmp_path, overrides, error):
    manifest = _vintage(tmp_path / "v1")
    spec = json.loads(manifest.read_text())
    spec.update(overrides)
    manifest.write_text(json.dumps(spec))
    with pytest.raises(ValueError, match=error):
        osap.load_reference(manifest)


@pytest.mark.parametrize("rows,error", [
    ([["1926-01-30", "1", "NA"], ["1926-01-31", "2", "NA"]], "duplicate"),
    ([["1926-02-30", "1", "NA"]], "invalid ISO date"),
    ([["1926-01-30", "inf", "NA"]], "non-finite"),
    ([["1926-01-30", "oops", "NA"]], "non-numeric"),
])
def test_invalid_return_rows(tmp_path, rows, error):
    with pytest.raises(ValueError, match=error):
        osap.load_reference(_vintage(tmp_path / "v1", return_rows=rows))


def test_duplicate_columns_catalog_and_hash(tmp_path):
    manifest = _vintage(tmp_path / "v1", return_header=["date", "AAA", "AAA"])
    with pytest.raises(ValueError, match="duplicate CSV column"):
        osap.load_reference(manifest)
    (manifest.parent / "returns.csv").write_text("changed")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        osap.load_reference(manifest)
    second = _vintage(tmp_path / "v2", catalog_rows=[{"Acronym": "AAA"}, {"Acronym": "AAA"}])
    with pytest.raises(ValueError, match="duplicate Acronym"):
        osap.load_reference(second)


def test_missing_transition_and_cli_json(tmp_path, capsys):
    old_manifest = _vintage(tmp_path / "old")
    new_manifest = _vintage(tmp_path / "new", name="v2",
                            return_rows=[["1926-01-30", "NA", "4"],
                                         ["1926-02-27", "-1", "3"]])
    old = osap.load_reference(old_manifest)
    new = osap.load_reference(new_manifest)
    assert len(osap.diff(old, new)["missing_changes"]) == 2
    assert osap.main(["--manifest", str(old_manifest), "series", "--signal", "AAA"]) == 0
    assert json.loads(capsys.readouterr().out)["rows"][0]["returns"]["AAA"]["percent"] == 2.5


def test_absolute_source_bindings_reuse_existing_files_without_copy(tmp_path):
    original_manifest = _vintage(tmp_path / "sources")
    manifest_dir = tmp_path / "manifest"
    manifest_dir.mkdir()
    spec = json.loads(original_manifest.read_text())
    spec["catalog"]["path"] = str(original_manifest.parent / "catalog.csv")
    spec["returns"]["path"] = str(original_manifest.parent / "returns.csv")
    manifest = manifest_dir / "manifest.json"
    manifest.write_text(json.dumps(spec))
    before = {name: (original_manifest.parent / name).read_bytes()
              for name in ("catalog.csv", "returns.csv")}
    result = osap.series(osap.load_reference(manifest), ["AAA"])
    assert result["rows"][0]["returns"]["AAA"]["percent"] == 2.5
    assert sorted(path.name for path in manifest_dir.iterdir()) == ["manifest.json"]
    assert all((original_manifest.parent / name).read_bytes() == data for name, data in before.items())
    (original_manifest.parent / "returns.csv").write_text("tampered")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        osap.load_reference(manifest)


@pytest.mark.parametrize("source", ["catalog", "returns"])
def test_header_only_csv_is_rejected(tmp_path, source):
    manifest = _vintage(tmp_path / "v1")
    path = manifest.parent / f"{source}.csv"
    _write_csv(path, list(osap.CATALOG_FIELDS) if source == "catalog" else ["date", "AAA", "BBB"], [])
    spec = json.loads(manifest.read_text())
    spec[source]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(spec))
    with pytest.raises(ValueError, match=f"empty {source} rows"):
        osap.load_reference(manifest)
