"""Standard library reference: closed weighted sum, not system EMA recurrence.

Consumes independently reconstructed original inputs, not captured close values
as the authority. No lei_signal, numpy or pandas imports. --write-report creates
an exclusive report; default rechecks without changing any artifact.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reference(closes):
    first = next((i for i, x in enumerate(closes) if x is not None), len(closes))
    out = []
    decay = 119 / 121
    for t, close in enumerate(closes):
        ema = None
        if t >= first + 119 and all(x is not None for x in closes[first:t + 1]):
            seed = math.fsum(closes[first:first + 120]) / 120
            k = t - first - 119
            ema = seed * decay**k + math.fsum(
                (2 / 121) * closes[j] * decay**(t - j) for j in range(first + 120, t + 1)
            )
        bias = None if close is None or ema is None or ema == 0 else close / ema - 1
        out.append({"ema120": ema, "bias": bias})
    return out


def check():
    manifest_path = HERE / "fixture-manifest.json"
    spec = json.loads(manifest_path.read_text())
    actual_path = HERE / "implementation-output.json"
    actual = json.loads(actual_path.read_text())
    assert actual["factor_id"] == spec["factor_id"] == "mixed.bias_ema120_pct@1.0.0"
    assert actual["manifest_sha256"] == digest(manifest_path)
    for path, fingerprint in actual["source_sha256"].items():
        assert digest(ROOT / path) == fingerprint, path
    expected_inputs = {}
    for source in spec["old_fixtures"]:
        p = ROOT / source["path"]
        assert digest(p) == source["sha256"]
        expected_inputs[source["name"]] = [bar["close"] for bar in json.loads(p.read_text())["bars"]]
    for case in spec["new_cases"]:
        expected_inputs[case["name"]] = sum(([v] * n for v, n in case["segments"]), [])
    assert set(expected_inputs) == {c["name"] for c in actual["cases"]}
    observations = []
    for case in actual["cases"]:
        closes = expected_inputs[case["name"]]
        assert closes == case["closes"]
        wanted = reference(closes)
        assert len(wanted) == len(case["rows"])
        maximum = {"ema120": 0.0, "bias": 0.0}
        for i, (expected, observed) in enumerate(zip(wanted, case["rows"])):
            for field in maximum:
                e, a = expected[field], observed[field]
                if e is None:
                    assert a is None, (case["name"], i, field, e, a)
                else:
                    assert a is not None and math.isfinite(a)
                    error = abs(e - a)
                    maximum[field] = max(maximum[field], error)
                    assert error <= spec["tolerance_absolute"], (case["name"], i, field, error)
        observations.append({"case": case["name"], "rows": len(wanted), "mismatches": 0, "maximum_absolute_error": maximum})
    return {"factor_id": spec["factor_id"], "synthetic_only": True, "method": "closed_form_weighted_sum",
            "observations": observations, "all_ok": True, "actual_sha256": digest(actual_path),
            "manifest_sha256": digest(manifest_path), "checker_sha256": digest(Path(__file__))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    report = check()
    if args.write_report:
        with (HERE / "independent-report.json").open("x") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    print(json.dumps(report, ensure_ascii=False))
