"""Read-only implementation review; writes only new isolated review artifacts."""
import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    out = Path(parser.parse_args().out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    cli = module("review_cli", "scripts/run_momentum_research_prototype.py")
    fixtures = module("review_fixtures", "tests/integration/test_momentum_prototype_cli.py")
    raw = ROOT / "docs/experiments/raw/research-momentum-prototype-2026-09-13"
    protocol = json.loads((raw / "protocol.json").read_text())
    result = {"scope": "synthetic counterexamples plus independent frozen-output arithmetic"}

    def run(name, pp, mode):
        dest = out / name
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/run_momentum_research_prototype.py"),
             "--protocol", str(pp), "--mode", mode, "--out", str(dest)],
            capture_output=True, text=True, cwd=ROOT, timeout=120,
        )
        (out / f"{name}.stdout.txt").write_text(proc.stdout)
        (out / f"{name}.stderr.txt").write_text(proc.stderr)
        return {"exit": proc.returncode, "manifest_exists": (dest / "manifest.json").exists()}

    result["synthetic_control"] = run("synthetic-control", raw / "protocol.json", "synthetic")
    for name, changes in [
        ("unknown-object", {"objects": dict(protocol["objects"], primary="nosuch.object@9.9.9")}),
        ("wrong-target", {"target_id": "protocol:unsupported-999-session@9.9.9"}),
    ]:
        pp = out / f"{name}.json"
        save(pp, protocol | changes)
        result[name] = run(name, pp, "synthetic")

    ev = {"event_id": "SYNTH-DIV", "symbol": "510300.SS",
          "type": "cash_dividend", "cash": 0.05, "effective_date": "2025-06-16"}
    for name, event in [("legal-action", ev), ("account-action", ev | {"fee": 1.0}),
                        ("negative-dividend", ev | {"cash": -0.05})]:
        base = out / f"fixture-{name}"
        base.mkdir()
        pp = fixtures._real_fixture(base, uses=("description",), events=[event])
        result[name] = run(name, pp, "historical-diagnostic")
        if (out / name / "values.csv").exists():
            result[name]["values_sha"] = sha(out / name / "values.csv")
    # Synthetic isolated control of the post-qualification routing, not market evidence.
    pp = out / "fixture-legal-action/protocol-test.json"
    p = json.loads(pp.read_text())
    paths = cli._verify_protocol_inputs(p)
    checks = cli._check_real_inputs(p, paths)
    for v in checks["uses"].values():
        v["default_accepted"] = True
    for v in checks["objects"].values():
        v["directly_satisfiable"] = True
        v["missing_fields"] = []
    with patch.object(cli, "_check_real_inputs", return_value=checks):
        r = cli.run_real_mode(p, paths, "qualified-research")
    result["qualified-routing-mocked-checks"] = {
        "synthetic_mock_only": True, "exit": r["exit_code"],
        "targets": len(r["target_rows"]), "skipped": r["skipped"],
        "unknown_available_at": r["unknown_available_at"],
        "reject_reasons": r["reject_reasons"],
    }

    targets = pd.read_csv(out / "synthetic-control/targets.csv")
    ranks = pd.read_csv(out / "synthetic-control/rank-diagnostic.csv")
    overlap = []
    for _, rec in ranks.iterrows():
        day = rec.observation_date
        future = sorted(d for d in ranks.observation_date if d > day)
        expected = 0
        if future:
            now = targets[targets.observation_date == day].set_index("symbol")
            nxt = targets[targets.observation_date == future[0]].set_index("symbol")
            for sym in now.index.intersection(nxt.index):
                a, b = now.loc[sym], nxt.loc[sym]
                if pd.notna(a.exit_date) and pd.notna(b.entry_date):
                    expected += int(a.entry_date <= b.exit_date and b.entry_date <= a.exit_date)
        if expected != rec.windows_overlapping_next:
            overlap.append({"date": day, "actual": rec.windows_overlapping_next,
                            "expected_interval_intersections": expected})
    result["overlap_mismatches"] = overlap

    # Independent forward-share/cash arithmetic, without importing either economic engine.
    from lei_signal.research.data_snapshot import load_snapshot
    loaded = load_snapshot(protocol["inputs"]["snapshot_dir"]["path"])
    assert loaded.verified
    events = json.loads(Path(protocol["inputs"]["actions"]["path"]).read_text())["events"]
    observed = pd.read_csv(raw / "run-04/values.csv")
    expected_values = {}
    attached = set()
    for sym, frame in loaded.frames.items():
        prices = frame.close.dropna()
        prices = prices[prices > 0]
        evs = [e for e in events if str(e["symbol"]).split(".")[0] == sym.split(".")[0]
               and e["type"] in {"split", "cash_dividend"}]
        attached.update(e["event_id"] for e in evs)
        levels = [1.0]
        days = [d.strftime("%Y-%m-%d") for d in prices.index]
        for k in range(1, len(prices)):
            shares, cash = 1.0, 0.0
            for e in sorted(evs, key=lambda e: (e["effective_date"], e["event_id"])):
                if days[k - 1] < e["effective_date"] <= days[k]:
                    if e["type"] == "split":
                        shares *= e.get("split_ratio", e.get("ratio"))
                    else:
                        cash += shares * e.get("cash_per_unit", e.get("cash"))
            levels.append(levels[-1] * (shares * prices.iloc[k] + cash) / prices.iloc[k - 1])
        for k in range(252, len(prices)):
            expected_values[(sym, days[k])] = levels[k - 21] / levels[k - 252] - 1
    differences = []
    for row in observed.itertuples():
        expected = expected_values[(row.symbol, row.date)]
        differences.append(abs(row.momentum - expected))
        assert np.isclose(row.momentum, expected, atol=1e-12, rtol=1e-12)
    result["run04_independent_values"] = {
        "rows": len(observed), "unique_keys": len(observed.drop_duplicates(["symbol", "date"])),
        "attached_action_ids": len(attached), "max_abs_difference": max(differences),
        "all_within_tolerance": True,
    }
    manifest_checks = {}
    for name in ["run-04", "run-05"]:
        man = json.loads((raw / name / "manifest.json").read_text())
        manifest_checks[name] = {
            "outputs_match": all(sha(raw / name / f) == h for f, h in man["outputs"].items()),
            "protocol_matches": man["protocol"]["sha256"] == sha(raw / "protocol.json"),
        }
    result["manifest_checks"] = manifest_checks
    baseline_path = ROOT / (
        "docs/experiments/raw/research-data-provenance-round2-2026-09-10/protected-baseline.json"
    )
    baseline = json.loads(baseline_path.read_text())["files"]
    changed = [p for p, h in baseline.items() if not (ROOT / p).exists() or sha(ROOT / p) != h]
    result["protected"] = {"count": len(baseline), "changed": changed}
    save(out / "summary.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
