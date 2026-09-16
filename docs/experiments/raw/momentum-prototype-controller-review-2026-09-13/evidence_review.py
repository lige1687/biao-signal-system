"""Read-only controller audit; mutations confined to new synthetic fixture directories."""

import copy
import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from lei_signal.research.qualification_bundle import (  # noqa: E402
    listing_evidence_from_validated,
    validate_evidence_bundle,
)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    out = (
        ROOT
        / "docs/experiments/raw/momentum-prototype-controller-review-2026-09-13/evidence-run-02"
    )
    out.mkdir(exist_ok=False)
    raw = ROOT / "docs/experiments/raw/research-fixed-etf-evidence-integration-2026-09-13"
    bundle = json.loads((raw / "evidence-bundle.json").read_text())
    universe = {r["instrument_id"] for r in bundle["records"]}
    results = {"synthetic_probe_only": True, "validation": {}, "prepare": {}}
    listing = next(r for r in bundle["records"] if r["record_id"] == "515050-listing-announcement")
    cases = {}
    rec = copy.deepcopy(listing)
    rec["facts"]["listing_trade_date"] = "2020-01-02"
    cases["changed_fact_same_original"] = rec
    rec = copy.deepcopy(listing)
    rec["allowed_for"] = []
    cases["no_bridge_use"] = rec
    rec = copy.deepcopy(bundle["records"][0])
    rec["facts"]["cash_per_10_shares_announced"] = "NaN"
    rec["facts"]["cash_per_share_computed"] = "NaN"
    cases["nan_cash"] = rec
    rec = copy.deepcopy(listing)
    rec["time_evidence"]["not_before"] = "2026-01-01"
    rec["time_evidence"]["not_after"] = "2019-01-01"
    cases["reversed_bounds"] = rec
    rec = copy.deepcopy(bundle["records"][0])
    rec["source"]["pdf_sha256"] = "0" * 64
    cases["bad_original_pdf_sha"] = rec
    for name, rec in cases.items():
        b = {
            "schema_version": "fixed-etf-evidence-bundle/1.0",
            "synthetic": False,
            "records": [rec],
        }
        r = validate_evidence_bundle(b, root=ROOT, universe=universe)
        result = {"validated": len(r["validated"]), "rejected": r["rejected"]}
        if rec["fact_type"] == "listing":
            result["bridge_products"] = list(
                listing_evidence_from_validated(r["validated"], out_dir=out / name)
            )
        results["validation"][name] = result
    spec = importlib.util.spec_from_file_location(
        "fixtures", ROOT / "tests/integration/test_momentum_qualified_inputs.py"
    )
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    for name in ["control", "missing_key", "nan_expected"]:
        base = out / name
        base.mkdir()
        protocol, evidence, values = fixture._build_fixture(base)
        if name == "missing_key":
            with values.open("a") as f:
                f.write("510300.SS,2030-01-01,0.123,fraction\n")
        elif name == "nan_expected":
            lines = values.read_text().splitlines()
            parts = lines[1].split(",")
            parts[2] = "nan"
            lines[1] = ",".join(parts)
            values.write_text("\n".join(lines) + "\n")
        p = subprocess.run(
            [
                sys.executable,
                str(fixture.PREPARE),
                "--protocol",
                str(protocol),
                "--evidence-bundle",
                str(evidence),
                "--run04-values",
                str(values),
                "--out",
                str(base / "output"),
            ],
            capture_output=True,
            text=True,
        )
        (base / "stdout.txt").write_text(p.stdout)
        (base / "stderr.txt").write_text(p.stderr)
        rp = base / "output/result.json"
        results["prepare"][name] = {
            "exit": p.returncode,
            "result": json.loads(rp.read_text())["momentum_key_check"] if rp.exists() else None,
        }
    # Independent key and finite value comparison on frozen outputs, no new real run.
    old = ROOT / "docs/experiments/raw/research-momentum-prototype-2026-09-13/run-04/values.csv"

    def rows(p):
        with p.open() as f:
            return list(csv.DictReader(f))

    a, b = rows(old), rows(raw / "run-05/values.csv")
    aa = {(r["symbol"], r["date"]): float(r["momentum"]) for r in a}
    bb = {(r["symbol"], r["date"]): float(r["momentum"]) for r in b}
    results["real_values"] = {
        "old_rows": len(a),
        "new_rows": len(b),
        "missing": len(aa.keys() - bb.keys()),
        "extra": len(bb.keys() - aa.keys()),
        "max_abs": max(abs(aa[k] - bb[k]) for k in aa.keys() & bb.keys()),
        "old_sha": sha(old),
    }
    protected = json.loads(
        (
            ROOT
            / "docs/experiments/raw/research-data-provenance-round2-2026-09-10"
            / "protected-baseline.json"
        ).read_text()
    )["files"]
    results["protected"] = {
        "count": len(protected),
        "changed": [
            p for p, h in protected.items() if not (ROOT / p).exists() or sha(ROOT / p) != h
        ],
    }
    results["manifests"] = {}
    for name in ["run-02", "run-05", "run-06"]:
        m = json.loads((raw / name / "manifest.json").read_text())
        results["manifests"][name] = {
            "output_mismatches": [
                p
                for p, h in m["outputs"].items()
                if not (raw / name / p).exists() or sha(raw / name / p) != h
            ],
            "protocol": m["protocol"],
        }
    (out / "summary.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
