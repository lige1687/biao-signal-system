"""Bounded time-label edges and archival verification; synthetic inputs only."""
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
    "closeout_fixture", ROOT / "tests/integration/test_momentum_prototype_cli.py"
)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    out = Path(parser.parse_args().out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    results = {}
    for name in ["historical-mid-window-late", "all-labels-unavailable"]:
        base = out / name
        base.mkdir()
        if name == "historical-mid-window-late":
            pp = fixture._time_fixture(base, available_at="2026-01-01T10:00:00+08:00")
            mode = "historical-diagnostic"
        else:
            pp = fixture._time_fixture(
                base, available_at="2026-04-01T10:00:00+08:00",
                effective_date="2026-03-02", window_end="2026-03-06",
            )
            p = json.loads(pp.read_text())
            ap = Path(p["inputs"]["actions"]["path"])
            actions = json.loads(ap.read_text())
            actions["events"].append(actions["events"][0] | {
                "event_id": "SYNTH-SECOND-LABEL", "symbol": "159915.SZ",
            })
            save(ap, actions)
            snap = Path(p["inputs"]["snapshot_dir"]["path"])
            s = json.loads((snap / "snapshot.json").read_text())
            items = {i["instrument_id"]: i for i in s["instruments"]}
            a = pd.read_csv(snap / items["510300.SS"]["normalized"]["path"])
            second = snap / items["159915.SZ"]["normalized"]["path"]
            b = pd.read_csv(second)
            assert a.close.equals(b.close), "same synthetic nominal path"
            b["economic_index"] = a.economic_index
            b.to_csv(second, index=False)
            items["159915.SZ"]["normalized"]["sha256"] = digest(second)
            save(snap / "snapshot.json", s)
            p["inputs"]["snapshot_dir"]["sha256"] = digest(snap / "snapshot.json")
            p["inputs"]["actions"]["sha256"] = digest(ap)
            save(pp, p)
            mode = "qualified-research"
        run = base / "run"
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/run_momentum_research_prototype.py"),
             "--protocol", str(pp), "--mode", mode, "--out", str(run)],
            capture_output=True, text=True, cwd=ROOT, timeout=120,
        )
        (base / "stdout.txt").write_text(proc.stdout)
        (base / "stderr.txt").write_text(proc.stderr)
        row = {"synthetic": True, "mode": mode, "exit": proc.returncode,
               "stderr": proc.stderr.strip()}
        if (run / "manifest.json").exists():
            m = json.loads((run / "manifest.json").read_text())
            row.update(historical_reconstruction_only=m["historical_reconstruction_only"],
                       late_available_at=m.get("late_available_at"))
        results[name] = row

    # Reconstruct the exact previously observed v1.0.3 bytes, with an explicit audit trail.
    raw = ROOT / "docs/experiments/raw/research-momentum-prototype-2026-09-13"
    saved_copy = Path(__file__).parent / "time-run-01/early/protocol-test.json"
    old = json.loads(saved_copy.read_text())
    old["inputs"] = json.loads((raw / "protocol-v1.0.2.json").read_text())["inputs"]
    data = json.dumps(old, ensure_ascii=False, indent=1)
    actual = hashlib.sha256(data.encode()).hexdigest()
    expected = "7d7562f7d350038643ce4d099254d7bcc2c95ffdc137e1707e843b30eca8da1f"
    assert actual == expected, "must reproduce known original bytes exactly, not invent history"
    (out / "recovered-protocol-v1.0.3.json").write_text(data)
    results["protocol_v103_recovery"] = {
        "method": "saved controller protocol copy; restore fixed_inputs from frozen v1.0.2; "
                  "JSON indent=1, ensure_ascii=False, no trailing newline",
        "recovered_sha256": actual,
        "currently_named_v103_sha256": digest(raw / "protocol-v1.0.3.json"),
        "original_files_modified": False,
    }
    protected = json.loads((ROOT / (
        "docs/experiments/raw/research-data-provenance-round2-2026-09-10/protected-baseline.json"
    )).read_text())["files"]
    results["protected"] = {
        "count": len(protected),
        "changed": [p for p, h in protected.items() if digest(ROOT / p) != h],
    }
    save(out / "summary.json", results)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
