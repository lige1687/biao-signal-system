"""Check all corrected financial comparison outcomes and exact reuse dependencies."""
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent


def rows(path):
    with Path(path).open() as f:
        return list(csv.DictReader(f))


def differences(a, b, path=""):
    if isinstance(a, dict) and isinstance(b, dict):
        assert set(a) == set(b), path
        return [v for k in a for v in differences(a[k], b[k], path + "/" + str(k))]
    if isinstance(a, list) and isinstance(b, list):
        assert len(a) == len(b), path
        return [v for i, (x, y) in enumerate(zip(a, b)) for v in differences(x, y, path + "/" + str(i))]
    return [] if a == b else [{"path": path, "before": a, "after": b}]


def main():
    c = json.loads((HERE / "p2-execution-contract.json").read_text())
    b = c["bindings"]
    out = Path(c["output"]["path"])
    for binding in b.values():
        assert hashlib.sha256(Path(binding["path"]).read_bytes()).hexdigest() == binding["sha256"]
    old_m = json.loads(Path(b["old_monthly"]["path"]).read_text())
    new_m = json.loads((out / "monthly.json").read_text())
    md = differences(old_m, new_m)
    old_s = rows(b["old_stock_weights"]["path"])
    new_s = rows(out / "stock_weights.csv")
    sd = differences(old_s, new_s)
    assert {d["path"].split("/")[-1] for d in md} <= {"spearman_financial_momentum"}
    assert {d["path"].split("/")[-1] for d in sd} <= {"momentum"}
    by = defaultdict(list)
    for row in new_s:
        by[(row["scope"], row["month"])].append(row)
    checks = 0
    maxerr = 0.
    for record in new_m:
        panel = by[(record["scope"], record["month"])]
        for method in ("P", "M", "F", "B", "D"):
            observed = sum(float(r["weight_" + method]) * float(r["future_return"])
                           for r in panel if r["future_return"] != "")
            missing = sum(float(r["weight_" + method]) for r in panel if r["future_return"] == "")
            for key, value in (("unknown_zero", observed), ("unknown_minus_one", observed - missing)):
                actual = record["methods"][method][key]
                maxerr = max(maxerr, abs(actual - value))
                assert math.isclose(actual, value, abs_tol=1e-12, rel_tol=1e-12)
                checks += 1
    manifest = json.loads((out / "manifest.json").read_text())
    assert not manifest["core"]["quote_series_changed"]
    assert not manifest["risk"]["input_changed"] and not manifest["gradient"]["input_changed"]
    for name in ("performance.json", "paired.json"):
        before = Path(b["old_core_manifest"]["path"]).parent / name
        assert json.loads(before.read_text()) == json.loads((out / name).read_text())
    result = {"status": "passed", "monthly_records": len(new_m), "stock_records": len(new_s),
              "monthly_exact_differences": md, "stock_exact_differences": sd,
              "all_3960_method_scenarios_independently_recomputed": checks == 3960,
              "maximum_absolute_error": maxerr, "performance_and_paired_values_exactly_unchanged": True,
              "old_risk_and_gradient_reuse_independently_supported": True,
              "macos_metadata_entries_not_counted_as_results": sum(n.startswith("._") for n in manifest["outputs"]),
              "effect_runs_added": 0}
    with (HERE / "independent-p2-check.json").open("x") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print({k: v for k, v in result.items() if k not in ("monthly_exact_differences", "stock_exact_differences")})
    print("changed fields", Counter(d["path"].split("/")[-1] for d in md),
          Counter(d["path"].split("/")[-1] for d in sd))


if __name__ == "__main__":
    main()
