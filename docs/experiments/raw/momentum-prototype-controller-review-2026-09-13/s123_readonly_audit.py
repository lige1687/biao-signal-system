"""Independent frozen-key audit; no real dataset generation or research execution."""

import calendar
import csv
import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    raw = ROOT / "docs/experiments/raw/research-fixed-etf-evidence-integration-2026-09-13"
    out = Path(__file__).parent / "s123-readonly-2026-09-14"
    out.mkdir(exist_ok=False)
    protocol = json.loads((raw / "protocol-v1.0.3.json").read_text())
    inputs = protocol["inputs"]
    days = json.loads((ROOT / inputs["calendar"]["path"]).read_text())["days"]
    start, end = inputs["evaluation_start"], inputs["evaluation_end"]
    months = sorted({d[:7] for d in days if start <= d <= end})
    observations = []
    for month in months:
        y, m = map(int, month.split("-"))
        expected_days = {f"{month}-{n:02d}" for n in range(1, calendar.monthrange(y, m)[1] + 1)}
        if not expected_days.issubset(days):
            continue
        trade_days = [d for d in expected_days if start <= d <= end and days[d]["is_trading_day"]]
        if trade_days:
            observations.append(max(trade_days))
    calculated = {}
    for p in (raw / "run-08/snapshot/normalized").glob("*.csv"):
        f = pd.read_csv(p)
        f = f[f.close.notna() & (f.close > 0)].reset_index(drop=True)
        by_date = {d: i for i, d in enumerate(f.date)}
        for d in observations:
            i = by_date.get(d)
            if i is not None and i >= 252:
                calculated[(p.stem, d)] = (
                    float(f.loc[i - 21, "economic_index"]) / float(f.loc[i - 252, "economic_index"])
                    - 1
                )
    old = ROOT / "docs/experiments/raw/research-momentum-prototype-2026-09-13/run-04/values.csv"
    with old.open() as f:
        rows = list(csv.DictReader(f))
    reference = {(r["symbol"], r["date"]): float(r["momentum"]) for r in rows}
    protected_path = (
        ROOT
        / "docs/experiments/raw/research-data-provenance-round2-2026-09-10/protected-baseline.json"
    )
    protected = json.loads(protected_path.read_text())["files"]
    manifest = json.loads((raw / "run-08/manifest.json").read_text())
    checks = {
        "observations": len(observations),
        "keys_calculated": len(calculated),
        "reference_rows": len(rows),
        "reference_unique": len(reference),
        "missing_reference": sorted(calculated.keys() - reference.keys()),
        "missing_calculated": sorted(reference.keys() - calculated.keys()),
        "max_abs_diff": max(
            abs(calculated[k] - reference[k]) for k in calculated.keys() & reference.keys()
        ),
        "protected_count": len(protected),
        "protected_changed": [p for p, h in protected.items() if sha(ROOT / p) != h],
        "run08_outputs_changed": [
            p for p, h in manifest["outputs"].items() if sha(raw / "run-08" / p) != h
        ],
        "fingerprints": {
            p.name: sha(p)
            for p in [
                raw / "protocol-v1.0.3.json",
                raw / "protocol-v1.0.4.json",
                raw / "evidence-bundle-v1.1.json",
                raw / "evidence-bundle-v1.2.json",
                raw / "task2-extraction-v1.1.json",
                old,
            ]
        },
    }
    (out / "summary.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(checks, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
