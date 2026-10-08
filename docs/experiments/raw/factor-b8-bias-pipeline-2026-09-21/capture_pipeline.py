"""Exercise real raw-close -> compute_features -> _bias_ema120, synthetic only.

First run writes a new output exclusively; --check recomputes in memory and
compares to the frozen output without modifying it.
"""
import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from lei_signal.features.indicators import compute_features
from lei_signal.rules.two_b_reversal import _bias_ema120

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
MANIFEST = HERE / "fixture-manifest.json"
SOURCES = ["src/lei_signal/features/indicators.py", "src/lei_signal/rules/two_b_reversal.py"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def actual(closes):
    frame = pd.DataFrame({k: closes for k in ("open", "high", "low", "close")})
    frame["volume"] = 1.0
    features = compute_features(frame, {"ema_periods": [120], "sma_periods": [120], "lag_periods": [20], "atr_period": 14})
    values = []
    for _, row in features.iterrows():
        b = _bias_ema120(row)
        values.append({"ema120": None if pd.isna(row["ema120"]) else float(row["ema120"]),
                       "bias": None if b is None or pd.isna(b) else float(b)})
    return values


def run():
    spec = json.loads(MANIFEST.read_text())
    cases = []
    for source in spec["old_fixtures"]:
        path = ROOT / source["path"]
        assert digest(path) == source["sha256"], source["name"]
        closes = [bar["close"] for bar in json.loads(path.read_text())["bars"]]
        cases.append((source["name"], closes))
    for case in spec["new_cases"]:
        cases.append((case["name"], [value for value, count in case["segments"] for _ in range(count)]))
    outputs = []
    for name, closes in cases:
        full = actual(closes)
        prefix = actual(closes[:min(125, len(closes))])
        assert prefix == full[:len(prefix)], (name, "future append changed prefix")
        scaled = actual([None if x is None else x * 7 for x in closes])
        for row, other in zip(full, scaled):
            assert (row["bias"] is None and other["bias"] is None) or (
                row["bias"] is not None and other["bias"] is not None and abs(row["bias"] - other["bias"]) <= 1e-6
            ), (name, "scale changed bias")
        outputs.append({"name": name, "closes": closes, "rows": full, "prefix_invariant": True, "scale_invariant": True})
    return {"factor_id": spec["factor_id"], "synthetic": True,
            "manifest_sha256": digest(MANIFEST), "source_sha256": {p: digest(ROOT / p) for p in SOURCES},
            "cases": outputs}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    output = run()
    path = HERE / "implementation-output.json"
    if args.check:
        assert json.loads(path.read_text()) == output
    else:
        with path.open("x") as stream:
            json.dump(output, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
    print(f"actual pipeline: {len(output['cases'])} cases, {sum(len(c['rows']) for c in output['cases'])} rows; prefix and scale checks passed")
