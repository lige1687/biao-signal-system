#!/usr/bin/env python3
"""Deterministic provider fixture; it never contacts a model or network."""

from __future__ import annotations

import json
import re
import signal
import sys
import time
from pathlib import Path


def emit(value: dict[str, object], *, partial: bool = False) -> None:
    encoded = json.dumps(value)
    if partial:
        midpoint = len(encoded) // 2
        sys.stdout.write(encoded[:midpoint])
        sys.stdout.flush()
        time.sleep(0.05)
        sys.stdout.write(encoded[midpoint:] + "\n")
    else:
        sys.stdout.write(encoded + "\n")
    sys.stdout.flush()


def main() -> int:
    task = sys.stdin.read()
    match = re.search(r"scenario:\s*([a-z-]+)", task)
    scenario = match.group(1) if match else "normal"
    emit({"type": "progress", "message": "fixture started"})

    if scenario == "empty":
        return 0
    if scenario == "fail":
        sys.stderr.write("fixture failed\n")
        return 7
    if scenario == "stderr-flood":
        sys.stderr.write("x" * (1024 * 1024) + "\n")
        sys.stderr.flush()
    if scenario == "partial-json":
        emit({"type": "result", "result": "partial line assembled"}, partial=True)
        return 0
    if scenario == "ignore-term":
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        while True:
            time.sleep(0.1)
    if scenario == "write-inside":
        allowed = Path("allowed")
        allowed.mkdir(exist_ok=True)
        (allowed / "generated.txt").write_text("inside", encoding="utf-8")
    if scenario == "write-outside":
        outside = Path("outside")
        outside.mkdir(exist_ok=True)
        (outside / "forbidden.txt").write_text("changed", encoding="utf-8")
    if scenario == "secret":
        sys.stderr.write("OPENAI_API_KEY=sk-fixture-secret\n")
        sys.stderr.flush()

    emit({"type": "result", "result": f"fixture completed: {scenario}"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
