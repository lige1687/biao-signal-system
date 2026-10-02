"""Replay the unchanged delivery algorithm in four independent product processes.

Only SYMBOLS (work partition) and HERE (new output destination) are rebound.
No detector, lifecycle setting, data input, or candidate selection is replaced.
Run with the same Python used for the other acceptance replays. Outputs and
interrupted attempts are retained; this is acceptance tooling, not production.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CLONE = ROOT / ".biao/remote-astra-acceptance-20261002/checkout"
REL = "docs/experiments/raw/remote-astra-T2-audit-2026-10-02/population_audit.py"
SCRIPT = CLONE / REL
COMMIT = "4155b4db7ccd14674eff2e29dfaf102d2ac3e5f9"
SYMBOLS = ("sh510300", "sz159915", "sh513100", "sh518880")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def worker(symbol, output):
    assert symbol in SYMBOLS and output.resolve().is_relative_to(HERE)
    source = subprocess.check_output(["git", "show", f"{COMMIT}:{REL}"], cwd=CLONE)
    assert SCRIPT.read_bytes() == source, "Delivery source changed"
    namespace = runpy.run_path(str(SCRIPT), run_name="acceptance_partition")
    namespace["main"].__globals__["SYMBOLS"] = (symbol,)
    namespace["main"].__globals__["HERE"] = output
    original = namespace["detect_strict_structures"]
    assert original is namespace["main"].__globals__["detect_strict_structures"]
    sys.argv = [str(SCRIPT), "--asof-structures"]
    started = time.monotonic()
    code = namespace["main"]()
    result = {"symbol": symbol, "exit_code": code,
              "elapsed_seconds": round(time.monotonic() - started, 3),
              "source_sha256": sha(source), "delivery_commit": COMMIT,
              "overrides": {"SYMBOLS": [symbol], "HERE": str(output)},
              "algorithm_overrides": [], "logical_argv": sys.argv}
    write(output / "worker-result.json", result)
    return code


def controller(label):
    assert label.replace("-", "").isalnum()
    target = HERE / "runs" / label
    target.mkdir(exist_ok=False)
    started = time.monotonic()
    processes = []
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONPATH"] = str(CLONE / "src")
    for symbol in SYMBOLS:
        destination = target / symbol
        destination.mkdir()
        log = (destination / "run.log").open("w", encoding="utf-8")
        command = [sys.executable, "-B", str(Path(__file__).resolve()),
                   "--symbol", symbol, "--output", str(destination)]
        process = subprocess.Popen(command, cwd=CLONE, env=environment,
                                   stdout=log, stderr=subprocess.STDOUT)
        processes.append((symbol, process, log, command))
    write(target / "launch.json", {"commands": [x[3] for x in processes],
                                  "pids": {x[0]: x[1].pid for x in processes},
                                  "delivery_commit": COMMIT})
    for symbol, process, log, _ in processes:
        code = process.wait()
        log.close()
        print(symbol, "exit", code, flush=True)
        assert code == 0, f"Failed partition {symbol}; keep all evidence"
    parts = [json.loads((target / symbol / "population-audit-asof.json").read_text())
             for symbol in SYMBOLS]
    keys = ("_note", "frozen_A_candidates", "traded_roundtrips_fee10bp", "structure_mode")
    for part in parts[1:]:
        assert all(part[k] == parts[0][k] for k in keys)
    # Preserve the original main() insertion order and serialization exactly.
    merged = {k: parts[0][k] for k in keys[:3]}
    merged["per_symbol"] = {}
    totals, traded = Counter(), Counter()
    for symbol, part in zip(SYMBOLS, parts):
        assert tuple(part["per_symbol"]) == (symbol,)
        merged["per_symbol"].update(part["per_symbol"])
        totals.update(part["totals"])
        traded.update(part["traded_totals"])
    merged["totals"], merged["traded_totals"] = dict(totals), dict(traded)
    merged["structure_mode"] = parts[0]["structure_mode"]
    payload = (json.dumps(merged, ensure_ascii=False, indent=1) + "\n").encode()
    (target / "population-audit-asof.json").write_bytes(payload)
    expected = subprocess.check_output(["git", "show", f"{COMMIT}:{str(Path(REL).parent / 'population-audit-asof.json')}"], cwd=CLONE)
    result = {"delivery_commit": COMMIT, "exit_code": 0,
              "elapsed_seconds": round(time.monotonic() - started, 3),
              "byte_identical": payload == expected,
              "replayed_sha256": sha(payload), "committed_sha256": sha(expected),
              "reproduced": sum(x["reproduction"].get("reproduced", 0)
                                for x in merged["per_symbol"].values()),
              "frozen": merged["frozen_A_candidates"],
              "totals": merged["totals"], "traded_totals": merged["traded_totals"],
              "partition_elapsed_seconds_sum": sum(json.loads((target / s / "worker-result.json").read_text())["elapsed_seconds"] for s in SYMBOLS),
              "method": "unchanged main/asof_structures/detector; one SYMBOLS item per process; aggregate Counters in original order"}
    write(target / "result.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--label")
    parser.add_argument("--symbol")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.symbol:
        sys.exit(worker(args.symbol, args.output))
    assert args.label and not args.output
    controller(args.label)
