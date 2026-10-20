"""Synthetic full-CLI availability controls; no mocked quality decisions or market writes."""
import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location(
    "fixture_helpers", ROOT / "tests/integration/test_momentum_prototype_cli.py"
)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    out = Path(parser.parse_args().out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    results = {}
    for name, available in [
        ("early", "2025-06-15T10:00:00+08:00"),
        ("late", "2030-01-01T10:00:00+08:00"),
        ("unknown", None),
    ]:
        base = out / name
        base.mkdir()
        action = {
            "event_id": "SYNTH-TIME-DIV", "symbol": "510300.SS",
            "type": "cash_dividend", "cash": 0.05,
            "effective_date": "2025-06-16", "available_at": available,
        }
        pp = fixture._real_fixture(base, events=[action])
        protocol = json.loads(pp.read_text())
        snap = Path(protocol["inputs"]["snapshot_dir"]["path"])
        snapshot = json.loads((snap / "snapshot.json").read_text())
        snapshot["synthetic"] = True
        snapshot["semantics"]["fields"].append("economic_index")
        # Supply a real economic_index column, independently derived from this fixture.
        for item in snapshot["instruments"]:
            p = snap / item["normalized"]["path"]
            frame = pd.read_csv(p)
            levels = [1.0]
            for k in range(1, len(frame)):
                cash = 0.05 if (
                    item["instrument_id"] == "510300.SS"
                    and frame.date.iloc[k] == action["effective_date"]
                ) else 0.0
                levels.append(levels[-1] * (frame.close.iloc[k] + cash) / frame.close.iloc[k - 1])
            frame["economic_index"] = levels
            frame.to_csv(p, index=False)
            item["normalized"]["sha256"] = sha(p)
        save(snap / "snapshot.json", snapshot)
        protocol["inputs"]["snapshot_dir"]["sha256"] = sha(snap / "snapshot.json")
        save(pp, protocol)
        dest = base / "run"
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/run_momentum_research_prototype.py"),
             "--protocol", str(pp), "--mode", "qualified-research", "--out", str(dest)],
            cwd=ROOT, capture_output=True, text=True, timeout=120,
        )
        (base / "stdout.txt").write_text(proc.stdout)
        (base / "stderr.txt").write_text(proc.stderr)
        row = {"synthetic_only": True, "available_at": available, "exit": proc.returncode}
        if (dest / "manifest.json").exists():
            man = json.loads((dest / "manifest.json").read_text())
            row.update(statuses=man["statuses"],
                       historical_reconstruction_only=man["historical_reconstruction_only"],
                       targets_written=(dest / "targets.csv").exists())
        results[name] = row
    save(out / "summary.json", results)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
