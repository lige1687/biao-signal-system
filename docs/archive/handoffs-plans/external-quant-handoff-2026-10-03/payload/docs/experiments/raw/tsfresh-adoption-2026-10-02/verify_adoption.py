"""Finite engineering batch; keep every attempt, never fit future outcomes."""

from __future__ import annotations

import hashlib
import json
import math
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RAW = Path(__file__).resolve().parent
BINDINGS = {
    "docs/experiments/raw/volume-information-2026-09-30/execution/panel.json": (
        "382d82ff21cb43758bca8e596026284ba2821038a79e1b4c331135119524679b"
    ),
    "docs/experiments/raw/volume-information-2026-09-30/execution/source-manifest.json": (
        "a0c3b15bc56ac34c4538ac9b11e505a83c0f8bed97175459d7eccb74c2b11c94"
    ),
    "docs/experiments/raw/volume-information-2026-09-30/source-recovery/qualification.json": (
        "9d150d608a5e8a88d11021b96f5e2ec5443dddf14c1a98b4ddc2fb4b01bee5f2"
    ),
    "docs/experiments/raw/research-calendar-completion-2026-09-10/calendar-merged/calendar.json": (
        "aa43736b67bbcee04fc21eedf8d510b184b764adf138456c8bce93a3155eb6c1"
    ),
}


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n")


def main():
    manifest = json.loads((RAW / "manifest.json").read_text())
    attempt = manifest["budget"]["test_batches_used"] + 1
    if attempt > manifest["budget"]["test_batches"]:
        raise RuntimeError("predeclared batch budget exhausted")
    destination = RAW / f"attempt-{attempt}.json"
    if destination.exists():
        raise RuntimeError("never overwrite previous attempt")
    record = {
        "attempt": attempt,
        "status": "running",
        "bindings": BINDINGS,
        "new_market_requests": 0,
        "future_outcome_fits": 0,
    }
    manifest["budget"]["test_batches_used"] = attempt
    manifest["tests"].append(record)
    save(RAW / "manifest.json", manifest)
    begin = time.monotonic()
    try:
        for path, expected in BINDINGS.items():
            assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, path
        panel = json.loads((ROOT / list(BINDINGS)[0]).read_text())
        source = json.loads((ROOT / list(BINDINGS)[1]).read_text())
        calendar = json.loads((ROOT / list(BINDINGS)[3]).read_text())
        expected_days = sorted(
            day
            for day, item in calendar["days"].items()
            if panel["calendar"][0] <= day <= panel["calendar"][-1] and item["is_trading_day"]
        )
        assert expected_days == panel["calendar"], (
            "declared calendar must match saved official calendar"
        )
        assert sorted({r["asset"] for r in panel["bars"]}) == sorted(source["assets"])
        packet = {
            **panel,
            "schema": "tsfresh-candidate-input/1.0",
            "assets": source["assets"],
            "source_note": "Existing retrospective economic-price panel; original "
            "historical arrival "
            "and action availability times remain unverified. Source hashes in attempt record; "
            "not newly qualified for predictions or trading.",
        }
        input_path = RAW / f"preview-input-{attempt}.json"
        save(input_path, packet)
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
        check = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests/unit/test_tsfresh_candidates.py",
                "-p",
                "no:cacheprovider",
            ],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
        )
        record["unit_tests"] = {
            "returncode": check.returncode,
            "stdout": check.stdout,
            "stderr": check.stderr,
        }
        assert check.returncode == 0, "unit tests failed"
        command = [
            sys.executable,
            ".agents/skills/lei-quant-tools/scripts/quant_tools.py",
            "candidate-preview",
            str(input_path),
            "--as-of",
            "2026-06-30",
        ]
        run = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True)
        record["cli"] = {"returncode": run.returncode, "stderr": run.stderr}
        assert run.returncode == 0, "CLI preview failed"
        result = json.loads(run.stdout)
        save(RAW / f"preview-output-{attempt}.json", result)
        assert len(result["rows"]) == 4
        independent = []
        for row in result["rows"]:
            assert row["status"] == "available", row
            bars = sorted(
                (r for r in panel["bars"] if r["asset"] == row["asset"]), key=lambda r: r["date"]
            )[-21:]
            closes = [r["close"] for r in bars]
            changes = [100 * math.log(b / a) for a, b in zip(closes, closes[1:], strict=False)]
            mu = statistics.mean(changes)
            variance = statistics.pvariance(changes)
            covariance_sum = sum(
                (a - mu) * (b - mu) for a, b in zip(changes, changes[1:], strict=False)
            )
            expected = {
                "mean_abs_log_change20": statistics.mean(abs(v) for v in changes),
                "return_autocorrelation20_lag1": covariance_sum / (19 * variance),
                "ret20_pct": 100 * (closes[-1] / closes[0] - 1),
                "vol20_annualized_pct": statistics.stdev(changes) * math.sqrt(252),
            }
            actual = {**row["values"], **row["baseline"]}
            errors = {k: abs(expected[k] - actual[k]) for k in expected}
            assert max(errors.values()) < 1e-10, errors
            independent.append(
                {"asset": row["asset"], "expected": expected, "absolute_errors": errors}
            )
        record["independent_recalculation"] = independent
        record["panel_rows"] = len(panel["bars"])
        record["calendar_dates"] = len(panel["calendar"])
        record["preview_assets"] = len(result["rows"])
        for path, expected in BINDINGS.items():
            assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, path
        record["status"] = "passed"
    except Exception as exc:
        record.update(status="failed", error=f"{type(exc).__name__}: {exc}")
    record["elapsed_seconds"] = time.monotonic() - begin
    record["tested_files"] = {
        p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
        for p in [
            ".agents/skills/lei-quant-tools/scripts/tsfresh_candidates.py",
            ".agents/skills/lei-quant-tools/scripts/tsfresh_calculators.py",
            ".agents/skills/lei-quant-tools/scripts/quant_tools.py",
            "tests/unit/test_tsfresh_candidates.py",
        ]
    }
    save(destination, record)
    save(RAW / "manifest.json", manifest)
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0 if record["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
