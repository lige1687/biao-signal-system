"""Real saved-source read-back; no fitting, new download or portfolio backtest."""
from collections import Counter
from copy import deepcopy
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
RAW = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from lei_signal.research import financial_revisions as financial
from lei_signal.research import osap_reference as osap


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    output = Path(json.loads((RAW / "storage-plan.json").read_text())["output"])
    manifest = RAW / "osap-2025-manifest.json"
    reference = osap.load_reference(manifest)
    signals = ["Mom12m", "STreversal", "Size", "BM", "EP", "Beta", "AssetGrowth",
               "ShareIss1Y", "ShareIss5Y", "NetEquityFinance", "GP", "CBOperProf"]
    raw_rows = list(csv.DictReader(open(reference["manifest"]["returns"]["path"])))
    extracted = osap.series(reference, signals)
    all_pairs, maximum = 0, 0.0
    by_day = {row["date"]: row for row in raw_rows}
    for row in extracted["rows"]:
        for signal in signals:
            value = by_day[row["date"]][signal]
            parsed = row["returns"][signal]
            if value in ("NA", ""):
                assert parsed == {"percent": None, "decimal": None}
            else:
                expected = Decimal(value) / Decimal(100)
                difference = abs(float(expected) - parsed["decimal"])
                maximum = max(maximum, difference)
                assert difference < 1e-14
                assert parsed["percent"] == float(value)
            all_pairs += 1
    coverage = {}
    for signal in signals:
        nonempty = [row for row in extracted["rows"] if row["returns"][signal]["percent"] is not None]
        coverage[signal] = {"observations": len(nonempty), "first": nonempty[0]["date"],
                            "last": nonempty[-1]["date"],
                            "missing_months": extracted["missing_count"][signal],
                            "raw_score_sign": reference["catalog"][signal]["Sign"],
                            "published_returns_not_flipped": True}
    (output / "selected-osap-series.json").write_text(json.dumps(extracted, ensure_ascii=False))
    # Real command-line entry, not just importing the helper.
    command = [sys.executable, "-m", "lei_signal.research.osap_reference",
               "--manifest", str(manifest), "catalog", "--signal", "ShareIss1Y"]
    actual = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    assert actual.returncode == 0, actual.stderr
    assert json.loads(actual.stdout)["rows"][0] == reference["catalog"]["ShareIss1Y"]
    bundle_path = RAW / "hekang-financial-versions.json"
    bundle = financial.load_bundle(bundle_path)
    original_only = deepcopy(bundle)
    original_only["records"] = original_only["records"][:4]
    prior = "2024-06-28T15:00:00+08:00"
    before = financial.select_versions(original_only, prior)
    after = financial.select_versions(bundle, prior)
    assert before["selected"] == after["selected"]
    cases = {}
    for label, at, basis, expected_status in (
        ("before_any_release", "2024-03-26T15:00:00+08:00", "public", False),
        ("original_release_day", "2024-03-27T15:00:00+08:00", "public", False),
        ("historical_original", prior, "public", True),
        ("revision_release_day", "2025-03-26T15:00:00+08:00", "public", False),
        ("after_revision", "2025-03-27T09:30:00+08:00", "public", True),
        ("vendor_arrival_unknown", "2025-03-27T09:30:00+08:00", "vendor", False),
    ):
        command = [sys.executable, "-m", "lei_signal.research.financial_revisions",
                   "--bundle", str(bundle_path), "--decision-at", at,
                   "--availability-basis", basis]
        process = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        assert process.returncode == (0 if expected_status else 2), process.stderr
        result = json.loads(process.stdout)
        assert result["qualified_for_declared_time_basis"] == expected_status
        cases[label] = result
    (output / "financial-time-cases.json").write_text(json.dumps(cases, ensure_ascii=False, indent=2))
    values = [{r["metric"]: Decimal(r["value"]) for r in cases[label]["selected"]}
              for label in ("historical_original", "after_revision")]
    metrics = []
    for value in values:
        gross_profit = value["revenue"] - value["cost_of_goods_sold"]
        metrics.append({"gross_profit_CNY": str(gross_profit),
                        "gross_margin_percent": str(gross_profit / value["revenue"] * 100),
                        "cost_plus_selling_CNY": str(value["cost_of_goods_sold"] + value["selling_expense"]),
                        "operating_profit_CNY": str(value["operating_profit"])})
    assert metrics[0]["cost_plus_selling_CNY"] == metrics[1]["cost_plus_selling_CNY"]
    assert metrics[0]["operating_profit_CNY"] == metrics[1]["operating_profit_CNY"]
    for binding in reference["manifest"]["catalog"], reference["manifest"]["returns"]:
        assert digest(binding["path"]) == binding["sha256"]
    financial.load_bundle(bundle_path)
    summary = {"catalog_records": len(reference["catalog"]),
               "catalog_categories": dict(Counter(row["Cat.Signal"] for row in reference["catalog"].values())),
               "return_series": len(reference["return_columns"]), "date_rows": len(reference["rows"]),
               "series_checked": coverage, "independent_cell_checks": all_pairs,
               "max_decimal_conversion_difference": maximum,
               "original_files_unchanged": True, "future_revision_prefix_invariant": True,
               "financial_case_results": {k: v["qualified_for_declared_time_basis"] for k, v in cases.items()},
               "original_and_revised_financial_metrics": metrics,
               "source_bundle_sha256": digest(bundle_path), "manifest_sha256": digest(manifest),
               "outputs": {p.name: {"path": str(p), "sha256": digest(p), "bytes": p.stat().st_size}
                           for p in output.iterdir() if p.is_file()},
               "market_performance_runs": 0, "data_downloads": 0,
               "scope": "source reading, unit and revision qualification only"}
    (RAW / "actual-verification.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: summary[key] for key in ("catalog_records", "return_series", "date_rows",
                                                  "independent_cell_checks", "financial_case_results",
                                                  "original_and_revised_financial_metrics")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
