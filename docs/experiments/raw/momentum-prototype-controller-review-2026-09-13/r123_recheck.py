"""Controller recheck; all probe changes are isolated synthetic/in-memory copies."""

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from lei_signal.research.qualification_bundle import (  # noqa: E402
    fact_tuple_fingerprint,
    validate_evidence_bundle,
)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    raw = ROOT / "docs/experiments/raw/research-fixed-etf-evidence-integration-2026-09-13"
    out = Path(__file__).parent / "r123-recheck-01"
    out.mkdir(exist_ok=False)
    bundle = json.loads((raw / "evidence-bundle-v1.1.json").read_text())
    universe = {r["instrument_id"] for r in bundle["records"]}
    results = {"validation": {}, "synthetic_cli": {}}
    for case in ["control", "date_changed", "date_omitted_from_binding", "time_changed"]:
        b = copy.deepcopy(bundle)
        r = next(r for r in b["records"] if r["record_id"] == "512890-official-split")
        if case in {"date_changed", "date_omitted_from_binding"}:
            r["facts"]["ex_date"] = "2021-10-23"
        if case == "date_omitted_from_binding":
            bind = r["fact_binding"]
            bind["fields"].remove("ex_date")
            bind["fingerprint"] = fact_tuple_fingerprint(
                r["instrument_id"],
                r["event_id"],
                r["fact_type"],
                {f: r["facts"][f] for f in bind["fields"]},
            )
        if case == "time_changed":
            r["time_evidence"]["published_date"] = "2021-10-01"
        v = validate_evidence_bundle(b, root=ROOT, universe=universe)
        results["validation"][case] = {"validated": len(v["validated"]), "rejected": v["rejected"]}
    spec = importlib.util.spec_from_file_location(
        "fixtures", ROOT / "tests/integration/test_momentum_qualified_inputs.py"
    )
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    for case in ["control", "reference_missing_one"]:
        base = out / case
        base.mkdir()
        protocol, evidence, values = fixture._build_fixture(base)
        if case == "reference_missing_one":
            lines = values.read_text().splitlines()
            values.write_text("\n".join([lines[0]] + lines[2:]) + "\n")
            obj = json.loads(protocol.read_text())
            obj["derived_reference"]["sha256"] = sha(values)
            protocol.write_text(json.dumps(obj, ensure_ascii=False))
        proc = subprocess.run(
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
                str(base / "out"),
            ],
            capture_output=True,
            text=True,
        )
        (base / "stdout.txt").write_text(proc.stdout)
        (base / "stderr.txt").write_text(proc.stderr)
        result = base / "out/result.json"
        results["synthetic_cli"][case] = {
            "exit": proc.returncode,
            "check": json.loads(result.read_text())["momentum_key_check"]
            if result.exists()
            else None,
        }
    manifest = json.loads((raw / "run-08/manifest.json").read_text())
    results["run08"] = {
        "outputs_changed": [
            p for p, h in manifest["outputs"].items() if sha(raw / "run-08" / p) != h
        ],
        "protocol": manifest["protocol"],
        "reference_check": manifest["result"]["momentum_key_check"],
    }
    baseline = json.loads(
        (
            ROOT
            / "docs/experiments/raw/research-data-provenance-round2-2026-09-10"
            / "protected-baseline.json"
        ).read_text()
    )["files"]
    results["protected"] = {
        "count": len(baseline),
        "changed": [p for p, h in baseline.items() if sha(ROOT / p) != h],
    }
    (out / "summary.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
