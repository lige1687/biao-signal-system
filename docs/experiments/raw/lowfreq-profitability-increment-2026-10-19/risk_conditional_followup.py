#!/usr/bin/env python3
"""Post-core, source-bound uncertainty for the original P-down paired quote gaps.

Contract example (all paths absolute; SHA256 values are exact file bytes)::

  {"schema":"financial-risk-followup-run/1",
   "inputs":{"design":{"path":".../risk-followup-design.json","sha256":"..."},
             "monthly":{"path":".../core-01/monthly.json","sha256":"..."},
             "core_manifest":{"path":".../core-01/manifest.json","sha256":"..."},
             "runner":{"path":".../risk_conditional_followup.py","sha256":"..."}},
   "output":{"path":".../result/risk-followup-01","mount":"/Volumes/win+mac通用",
             "external_device":12345,"external_uuid":"DEBA1C85-6059-3865-B50A-A8EE1F80E4D9",
             "minimum_free_bytes":1048576}}

The core manifest supplies the separately SHA-bound paired and uncertainty files.
Neither this script nor its tests import the original evaluator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import plistlib
import random
import shutil
import statistics
import struct
import subprocess
from datetime import datetime, timezone
from pathlib import Path

DESIGN_SHA256 = "261c2fa8b321e6990e16f250e8bd20234d3eb14cc0f8ef6733784a438a8f0093"
SCOPES = ("gp", "common_gp", "common_cfo")
SCENARIOS = ("unknown_minus_one", "unknown_zero")
COMPARISONS = ("F-P", "B-M", "B-D", "B-P", "B-F")
BLOCKS = (6, 12)
CONFIDENCES = (0.95, 0.975)
N_MONTHS = 132
DRAWS = 10000
SEED = 20261019


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_bound(binding: dict) -> tuple[Path, object]:
    path = Path(binding["path"])
    if not path.is_absolute() or not path.is_file() or sha256(path) != binding["sha256"]:
        raise ValueError(f"missing or changed bound input: {path}")
    return path, json.loads(path.read_text(encoding="utf-8"))


def months() -> tuple[str, ...]:
    return tuple(f"{year}-{month:02d}" for year in range(2015, 2026) for month in range(1, 13))


def _quantile(values: list[float], q: float) -> float:
    position = (len(values) - 1) * q
    lo, hi = math.floor(position), math.ceil(position)
    return values[lo] * (hi - position) + values[hi] * (position - lo) if hi != lo else values[lo]


def draw_positions(n: int, block: int, rng: random.Random) -> list[int]:
    positions: list[int] = []
    for _ in range(math.ceil(n / block)):
        start = rng.randrange(n)
        positions.extend((start + j) % n for j in range(block))
    return positions[:n]


def make_series(monthly: list[dict], dated_months: tuple[str, ...] = months()) -> dict[tuple[str, str, str], dict]:
    indexed: dict[tuple[str, str], dict] = {}
    allowed = set(dated_months)
    for row in monthly:
        key = (row["scope"], row["month"])
        if key in indexed or key[0] not in SCOPES or key[1] not in allowed:
            raise ValueError(f"duplicate or unexpected month/scope: {key}")
        indexed[key] = row
    series = {}
    for scope in SCOPES:
        for scenario in SCENARIOS:
            p = [indexed.get((scope, month), {}).get("methods", {}).get("P", {}).get(scenario)
                 for month in dated_months]
            down = [value is not None and value < 0 for value in p]
            for comparison in COMPARISONS:
                left, right = comparison.split("-")
                values = []
                for month, is_down in zip(dated_months, down):
                    methods = indexed.get((scope, month), {}).get("methods", {})
                    a = methods.get(left, {}).get(scenario)
                    b = methods.get(right, {}).get(scenario)
                    if a is not None and not math.isfinite(a):
                        raise ValueError("nonfinite monthly quote")
                    if b is not None and not math.isfinite(b):
                        raise ValueError("nonfinite monthly quote")
                    values.append(a - b if is_down and a is not None and b is not None else None)
                selected = [v for v in values if v is not None]
                series[(scope, scenario, comparison)] = {
                    "values": values, "p_down_months": sum(down), "paired_down_months": len(selected),
                    "original_difference": statistics.fmean(selected) if selected else None,
                }
    return series


def _sample_mean(values: list[float | None], positions: list[int]) -> float | None:
    selected = [values[pos] for pos in positions if values[pos] is not None]
    return statistics.fmean(selected) if selected else None


def calculate(series: dict[tuple[str, str, str], dict], *, n: int = N_MONTHS,
              draws: int = DRAWS, blocks: tuple[int, ...] = BLOCKS,
              confidences: tuple[float, ...] = CONFIDENCES,
              seed: int = SEED) -> tuple[list[dict], dict[int, str]]:
    if len(series) != len(SCOPES) * len(SCENARIOS) * len(COMPARISONS):
        raise ValueError("incomplete original comparison set")
    if any(len(item["values"]) != n for item in series.values()):
        raise ValueError("monthly position count mismatch")
    rows: list[dict] = []
    hashes: dict[int, str] = {}
    for block in blocks:
        rng = random.Random(seed)  # Deliberately reset for each original block length.
        digest = hashlib.sha256()
        samples = {key: [] for key in series}
        for _ in range(draws):
            positions = draw_positions(n, block, rng)
            for pos in positions:
                digest.update(struct.pack(">H", pos))
            for key, item in series.items():
                mean = _sample_mean(item["values"], positions)
                if mean is not None:  # No down month: missing draw, never zero.
                    samples[key].append(mean)
        hashes[block] = digest.hexdigest()
        for key, values in samples.items():
            values.sort()
            for confidence in confidences:
                tail = (1 - confidence) / 2
                rows.append({"scope": key[0], "scenario": key[1], "comparison": key[2],
                             "block_months": block, "confidence": confidence,
                             "original_difference": series[key]["original_difference"],
                             "p_down_months": series[key]["p_down_months"],
                             "paired_down_months": series[key]["paired_down_months"],
                             "draws_requested": draws, "draws_valid": len(values),
                             "lower": _quantile(values, tail) if values else None,
                             "upper": _quantile(values, 1 - tail) if values else None,
                             "status": "evaluated" if values else "no_down_month_draws",
                             "shared_index_sha256": hashes[block],
                             "interpretation": "post_core_exploratory_same_original_P_down_dates"})
    return rows, hashes


def verify_core(series: dict, paired: list[dict], uncertainty: list[dict], hashes: dict[int, str]) -> None:
    for block in BLOCKS:
        recorded = {r["shared_index_sha256"] for r in uncertainty if r["block_months"] == block}
        if recorded != {hashes[block]}:
            raise ValueError(f"shared original resampling index differs for {block} months")
    index = {(r["scope"], r["scenario"], r["comparison"]): r for r in paired if r["period"] == "all"}
    for key, item in series.items():
        original = index.get(key)
        if original is None or original["p_down_common_months"] != item["paired_down_months"]:
            raise ValueError(f"original paired conditional count differs: {key}")
        a, b = original["p_down_common_mean"], item["original_difference"]
        if (a is None) != (b is None) or (a is not None and not math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)):
            raise ValueError(f"original paired conditional mean differs: {key}")


def _volume_uuid(mount: Path) -> str:
    process = subprocess.run(["diskutil", "info", "-plist", str(mount)],
                             check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    info = plistlib.loads(process.stdout)
    if info.get("MountPoint") != str(mount):
        raise ValueError("diskutil mount identity differs")
    return info["VolumeUUID"]


def validate_output(out: Path, binding: dict, source: Path, needed: int) -> None:
    mount = Path(binding["mount"])
    if (not mount.is_absolute() or not os.path.ismount(mount) or
            mount.stat().st_dev != binding["external_device"] or
            source.stat().st_dev != binding["external_device"] or
            _volume_uuid(mount) != binding["external_uuid"] or
            out != Path(binding["path"]) or not out.is_absolute() or
            not out.is_relative_to(mount) or out.exists() or
            not out.parent.is_dir() or out.parent.stat().st_dev != binding["external_device"] or
            shutil.disk_usage(mount).free < max(needed, binding.get("minimum_free_bytes", 0))):
        raise ValueError("external output identity, path, create-only, or capacity preflight failed")


def _write_new(path: Path, value: object) -> dict:
    payload = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    with path.open("xb") as fh:
        fh.write(payload)
        fh.flush()
        os.fsync(fh.fileno())
    return {"path": str(path), "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}


def run(contract_path: Path, out: Path) -> None:
    contract_path = contract_path.resolve()
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("schema") != "financial-risk-followup-run/1":
        raise ValueError("unsupported run contract")
    inputs = contract["inputs"]
    if set(inputs) != {"design", "monthly", "core_manifest", "runner"}:
        raise ValueError("run contract input set differs")
    design_path, design = load_bound(inputs["design"])
    if inputs["design"]["sha256"] != DESIGN_SHA256:
        raise ValueError("design is not frozen version")
    monthly_path, monthly = load_bound(inputs["monthly"])
    core_path, core = load_bound(inputs["core_manifest"])
    runner_path = Path(inputs["runner"]["path"])
    if runner_path.resolve() != Path(__file__).resolve() or sha256(runner_path) != inputs["runner"]["sha256"]:
        raise ValueError("runner does not match bound code")
    if core.get("schema") != "financial-evaluation-result/1" or core["outputs"]["monthly.json"]["sha256"] != inputs["monthly"]["sha256"]:
        raise ValueError("monthly input differs from original core manifest")
    if monthly_path != Path(design["input_monthly"]["path"]) or inputs["monthly"]["sha256"] != design["input_monthly"]["sha256"]:
        raise ValueError("monthly input differs from frozen followup design")
    if core_path != Path(design["core_manifest"]["path"]) or inputs["core_manifest"]["sha256"] != design["core_manifest"]["sha256"]:
        raise ValueError("core manifest differs from frozen followup design")
    if (tuple(design["scopes"]) != SCOPES or tuple(design["scenarios"]) != SCENARIOS or
            tuple(design["comparisons"]) != COMPARISONS or
            tuple(design["resampling"]["block_months"]) != BLOCKS or
            tuple(design["resampling"]["intervals"]) != CONFIDENCES or
            design["resampling"]["draws"] != DRAWS or design["resampling"]["seed"] != SEED or
            design["output_directory"] != str(out)):
        raise ValueError("run definitions differ from frozen followup design")
    if not isinstance(monthly, list) or core.get("monthly_positions") != N_MONTHS:
        raise ValueError("original 132 dated positions unavailable")
    validate_output(out, contract["output"], monthly_path, design["estimated_new_external_bytes"])
    def core_output(name: str) -> object:
        path = core_path.parent / name
        if sha256(path) != core["outputs"][name]["sha256"]:
            raise ValueError(f"changed original core output: {name}")
        return json.loads(path.read_text(encoding="utf-8"))
    paired = core_output("paired.json")
    uncertainty = core_output("uncertainty.json")
    series = make_series(monthly)
    rows, hashes = calculate(series)
    verify_core(series, paired, uncertainty, hashes)
    if len(rows) != 120:
        raise ValueError("incomplete risk followup grid")
    out.mkdir(mode=0o700)
    result_binding = _write_new(out / "conditional_intervals.json", rows)
    manifest = {"schema": "financial-risk-followup-result/1", "status": "completed_post_core_exploratory",
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "contract": {"path": str(contract_path), "sha256": sha256(contract_path)},
                "inputs": inputs, "core_original_outputs": {name: core["outputs"][name]
                                                    for name in ("monthly.json", "paired.json", "uncertainty.json")},
                "output": result_binding, "rows": len(rows), "draws": DRAWS,
                "shared_index_sha256_by_block": {str(k): v for k, v in hashes.items()},
                "python_version": platform.python_version(),
                "limitations": design["limitations"]}
    _write_new(out / "manifest.json", manifest)
    dirfd = os.open(out, os.O_RDONLY)
    try:
        os.fsync(dirfd)
    finally:
        os.close(dirfd)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    run(args.contract, args.out)


if __name__ == "__main__":
    main()
