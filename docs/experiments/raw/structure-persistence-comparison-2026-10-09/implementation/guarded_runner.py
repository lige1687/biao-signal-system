"""Dedicated, release-gated research runner. No real stage runs by default.

All source and code hashes are verified before pandas, detector or panel load.
The feature stage cannot call target/effect functions. No old raw runner is used.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
import sys
import traceback
from datetime import datetime, timezone
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
WORKTREE = HERE.parents[4]
MAIN = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
MODULE = WORKTREE / "src/lei_signal/research/structure_persistence_comparison.py"
SOURCE_BINDINGS = PACKAGE / "source-bindings.json"
EXECUTION_BINDINGS = WORKTREE / "docs/experiments/raw/research-dispatch-controller-2026-10-07/approved-comparison-20261009/structure-execution-source-bindings.json"
DEFINITIONS = PACKAGE / "definitions.proposed.json"
RESEARCH_CONTRACT = PACKAGE / "research-contract.proposed.json"
CLOSURE = HERE / "dependency-closure.json"
ASSETS = ("510300.SS", "510050.SS", "510500.SS", "588000.SS")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_fixed_sources():
    """Static byte and amendment check, safe before any stage is released."""
    original = json.loads(SOURCE_BINDINGS.read_text())
    bindings = json.loads(EXECUTION_BINDINGS.read_text())
    old_files = {item["path"]: item for item in original["files"]}
    new_files = {item["path"]: item for item in bindings["files"]}
    registry_path = str(MAIN / "docs/research/definitions.v1.json")
    if (set(old_files) != set(new_files) or
            any(old_files[path] != new_files[path] for path in old_files if path != registry_path) or
            old_files[registry_path] != bindings["amendment"]["old_registry_binding"] or
            bindings["amendment"].get("candidate_semantics_changed") is not False):
        raise ValueError("execution binding change exceeds the registered two-definition amendment")
    for item in bindings["files"]:
        path = Path(item["path"])
        if not path.is_file() or path.stat().st_size != item["bytes"] or digest(path) != item["sha256"]:
            raise ValueError(f"source drift: {path}")
    closure = json.loads(CLOSURE.read_text())
    for item in closure["files"]:
        path = Path(item["path"])
        if not path.is_file() or digest(path) != item["sha256"]:
            raise ValueError(f"dependency drift: {path}")
    if sys.version.split()[0] != closure["python"]:
        raise ValueError("Python version drift")
    for package, version in closure["packages"].items():
        if importlib.metadata.version(package) != version:
            raise ValueError(f"package version drift: {package}")
    return bindings


def guard(release_path: Path, stage: str, output_dir: Path):
    release = json.loads(release_path.read_text())
    if release.get("status") != "released" or release.get("stage") != stage:
        raise ValueError("controller stage not released")
    if Path(release.get("output_dir", "")).resolve() != output_dir.resolve() or not output_dir.is_absolute():
        raise ValueError("output path differs from controller release")
    expected = {"runner_sha256": HERE / "guarded_runner.py",
                "module_sha256": MODULE,
                "source_bindings_sha256": SOURCE_BINDINGS,
                "execution_bindings_sha256": EXECUTION_BINDINGS,
                "definitions_sha256": DEFINITIONS,
                "research_contract_sha256": RESEARCH_CONTRACT,
                "dependency_closure_sha256": CLOSURE}
    for key, path in expected.items():
        if digest(path) != release.get(key):
            raise ValueError(f"release hash mismatch: {key}")
    bindings = verify_fixed_sources()
    plan_path = Path(release["output_plan_path"])
    if digest(plan_path) != release.get("output_plan_sha256"):
        raise ValueError("external output plan changed")
    plan = json.loads(plan_path.read_text())
    if plan.get("output") != str(output_dir) or plan.get("external_device") != release.get("external_device"):
        raise ValueError("released output path/device differs from saved plan")
    if plan.get("task_id") != release.get("task_id"):
        raise ValueError("task identity differs from output plan")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("released output directory is not empty")
    return release, bindings, plan


def open_external_output(plan):
    """Anchor all new directories to the mounted external device via dir_fd."""
    mount = Path(plan["external_mount"])
    base = Path(plan["run_directory"]).parent.parent
    target = Path(plan["output"])
    if not mount.is_mount() or mount.stat().st_dev != plan["external_device"]:
        raise RuntimeError("external mount/device unavailable")
    if target != Path(plan["run_directory"]) / "result" or not base.is_relative_to(mount):
        raise RuntimeError("external plan path shape invalid")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fds = []
    try:
        current = os.open(mount, flags)
        fds.append(current)
        if os.fstat(current).st_dev != plan["external_device"]:
            raise RuntimeError("mount device changed")
        for part in base.relative_to(mount).parts:
            current = os.open(part, flags, dir_fd=current)
            fds.append(current)
            if os.fstat(current).st_dev != plan["external_device"]:
                raise RuntimeError("external base crossed device")
        for index, part in enumerate((Path(plan["run_directory"]).parent.name,
                                      Path(plan["run_directory"]).name, "result")):
            try:
                os.mkdir(part, dir_fd=current)
            except FileExistsError:
                if index != 0:  # existing run/result is never reused
                    raise
            current = os.open(part, flags, dir_fd=current)
            fds.append(current)
            if os.fstat(current).st_dev != plan["external_device"]:
                raise RuntimeError("external output crossed device")
        return fds, current
    except BaseException:
        for fd in reversed(fds):
            os.close(fd)
        raise


def durable_json(outfd, name, value, plan):
    if not Path(plan["external_mount"]).is_mount() or os.fstat(outfd).st_dev != plan["external_device"]:
        raise RuntimeError("external device lost before result write")
    payload = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o600, dir_fd=outfd)
    with os.fdopen(fd, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    readfd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=outfd)
    with os.fdopen(readfd, "rb") as stream:
        observed = stream.read()
    if hashlib.sha256(observed).digest() != hashlib.sha256(payload).digest():
        raise RuntimeError("external result readback mismatch")
    return {"sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}


def import_dependencies():
    # The bound detector and indicators must resolve from the read-only main root.
    sys.path.insert(0, str(MAIN / "src"))
    import pandas as pd
    from lei_signal.features.indicators import seeded_ema
    from lei_signal.rules.strict_structure import detect_strict_structures
    spec = importlib.util.spec_from_file_location("structure_persistence_research", MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return pd, seeded_ema, detect_strict_structures, module


def import_pure_module():
    spec = importlib.util.spec_from_file_location("structure_persistence_effect", MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def valid_row(row):
    if row is None:
        return False, "missing_scheduled_row"
    if row.get("status") != "quoted" or row.get("action_known") is not True:
        return False, "unqualified_status_or_action"
    try:
        op, high, low, close = (float(row[key]) for key in ("open", "high", "low", "close"))
    except (ValueError, TypeError, KeyError):
        return False, "missing_or_invalid_ohlc"
    if not all(math.isfinite(v) and v > 0 for v in (op, high, low, close)) or high < max(op, close) or low > min(op, close):
        return False, "missing_or_invalid_ohlc"
    if row.get("decision_at") != row["date"] + "T16:00:00+08:00":
        return False, "decision_time_unbound"
    return True, None


def build_qualification(bindings, dependencies):
    pd, seeded_ema, detect, module = dependencies
    panel = json.loads(Path(bindings["input"]["path"]).read_text())
    calendar, bars = panel["calendar"], panel["bars"]
    if (panel.get("data_mode") != "historical_reconstruction" or panel.get("price_series") != "economic_price"
            or len(calendar) != 1337 or len(bars) != 5348 or calendar != sorted(set(calendar))):
        raise ValueError("panel identity or calendar mismatch")
    indexed = {}
    for row in bars:
        key = (row["asset"], row["date"])
        if row["asset"] not in ASSETS or row["date"] not in calendar or key in indexed:
            raise ValueError("duplicate or unexpected panel row")
        indexed[key] = row
    if len(indexed) != len(ASSETS) * len(calendar):
        raise ValueError("scheduled panel row count mismatch")
    features, excluded = [], []
    segments = Counter()

    def process(asset, number, chunk):
        if not chunk:
            return
        frame = pd.DataFrame(chunk).set_index(pd.to_datetime([row["date"] for row in chunk]))
        frozen = detect(frame[["open", "high", "low", "close"]])
        nodes = [module.Node.published(item) for item in frozen]  # never read future invalidation fields
        ema = seeded_ema(pd.Series([float(row["close"]) for row in chunk]), 20)
        values = [None if pd.isna(value) else float(value) for value in ema]
        features.extend(module.build_segment_features(asset=asset, segment=number,
                                                       bars=chunk, nodes=nodes, ema20=values))
        segments[asset] += 1

    for asset in ASSETS:
        chunk, number = [], 0
        for day in calendar:
            row = indexed.get((asset, day))
            eligible, reason = valid_row(row)
            if eligible:
                chunk.append(row)
            else:
                process(asset, number, chunk)
                chunk = []
                number += 1
                excluded.append({"asset": asset, "date": day, "segment": None,
                                 "exclusion_reason": reason, "bar_value": None, "node_value": None})
        process(asset, number, chunk)
    for asset in ASSETS:
        asset_rows = [row for row in features if row["asset"] == asset]
        module.mark_calendar_maturity(asset_rows)
    support = module.freeze_common_support(features)
    counts = Counter((row["asset"], row["phase"], row["exclusion_reason"], row["bar_value"],
                      row["node_value"], row["node_state"]) for row in features)
    summary = [{"asset": key[0], "phase": key[1], "exclusion_reason": key[2],
                "bar_value": key[3], "node_value": key[4], "node_state": key[5], "rows": count}
               for key, count in sorted(counts.items(), key=lambda item: str(item[0]))]
    coverage = []
    for asset in ASSETS:
        for phase_name in ("early_context", "eval_2025", "eval_2026H1"):
            part = [row for row in features if row["asset"] == asset and row["phase"] == phase_name]
            unknown = [row for row in excluded if row["asset"] == asset and module.phase(row["date"]) == phase_name]
            episodes = {row["episode_id"] for row in part if row["episode_id"]}
            coverage.append({"asset": asset, "phase": phase_name,
                             "scheduled_rows": len(part) + len(unknown), "qualified_rows": len(part),
                             "unknown_rows": len(unknown), "warmup_rows": sum(row["qualified_bars"] < 252 for row in part),
                             "root_days": sum(row["root_day"] for row in part),
                             "post_root_days": sum(row["episode_day"] for row in part),
                             "terminal_days": sum(row["terminal"] for row in part),
                             "calendar_mature_post_root_days": sum(row["episode_day"] and row["calendar_mature"] for row in part),
                             "common_eligible_days": sum(row["exclusion_reason"] is None for row in part),
                             "unique_episodes": len(episodes),
                             "first_qualified": part[0]["date"] if part else None,
                             "last_qualified": part[-1]["date"] if part else None,
                             "bar_active_days": sum(row["bar_value"] == 1 for row in part),
                             "node_active_days": sum(row["node_value"] == 1 for row in part),
                             "node_progress_confirmations": sum(row["top_confirmed"] and
                                 row["episode_day"] and not row["terminal"] and
                                 row["node_state"] == "active" for row in part),
                             "node_active_raw_rebound_days": sum(row["node_value"] == 1 and
                                 row["raw_rebound"] for row in part)})
    return {"features": features, "excluded_scheduled": excluded,
            "summary": summary, "coverage": coverage, "common_support": support,
            "segments_per_asset": dict(segments), "target_values_computed": 0}


def build_effect(release, module):
    mode = release.get("mode")
    if mode not in ("estimate", "describe_only"):
        raise ValueError("effect release mode missing or invalid")
    if mode == "estimate" and release.get("panel_path") != str(MAIN / "docs/experiments/raw/volume-information-2026-09-30/execution/panel.json"):
        raise ValueError("effect calendar input drift")
    source = Path(release["qualification_path"])
    if not source.is_file() or digest(source) != release.get("qualification_sha256"):
        raise ValueError("qualification result changed or missing")
    qualification = json.loads(source.read_text())
    if qualification.get("target_values_computed") != 0:
        raise ValueError("qualification stage contained target values")
    rows = module.attach_matured_targets(qualification["features"])
    table = module.effect_table(rows, qualification["common_support"])
    if mode == "estimate":
        panel = json.loads(Path(release["panel_path"]).read_text())
        intervals = module.moving_block_intervals(rows, qualification["common_support"], panel["calendar"])
    else:
        intervals = {"status": "not_authorized_for_estimation"}
    return {"target_rows": rows, "effects": table, "intervals": intervals,
            "fits": 0, "target_formula": "100*max(0,1-min(C[t+1]..C[t+21])/C[t+1])"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=["feature_qualification", "effect"])
    parser.add_argument("--release", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    release, bindings, plan = guard(args.release, args.stage, args.output_dir)
    sys.path.insert(0, str(MAIN / "src"))
    from lei_signal.research.output_storage import recheck_saved_plan
    recheck_saved_plan(MAIN, plan, plan["task_id"], plan["estimated_bytes"],
                       internal_bytes=plan["internal_metadata_bytes"])
    attempt_path = Path(release["local_attempt_path"])
    if attempt_path.parent != HERE or attempt_path.name != args.stage + "-attempt.json":
        raise ValueError("local attempt path outside fixed implementation scope")
    attempt = {"stage": args.stage, "release_sha256": digest(args.release),
               "runner_sha256": digest(HERE / "guarded_runner.py"),
               "module_sha256": digest(MODULE), "status": "started",
               "started_at": datetime.now(timezone.utc).isoformat(), "attempt_counted": True}
    with attempt_path.open("x") as stream:
        json.dump(attempt, stream, ensure_ascii=False, indent=2)
    fds = []
    try:
        fds, outfd = open_external_output(plan)
        if args.stage == "feature_qualification":
            result = build_qualification(bindings, import_dependencies())
            receipt = durable_json(outfd, "feature-qualification.json", result, plan)
            print("feature qualification saved; 0 target values; controller review required")
        else:
            result = build_effect(release, import_pure_module())
            target_receipt = durable_json(outfd, "target-rows.json", result["target_rows"], plan)
            effect_receipt = durable_json(outfd, "effects.json",
                {k: v for k, v in result.items() if k != "target_rows"}, plan)
            receipt = {"target_rows": target_receipt, "effects": effect_receipt}
            print("one label and effect pass saved; no predictive fit; controller review required")
        attempt.update(status="executed_pending_independent_acceptance",
                       completed_at=datetime.now(timezone.utc).isoformat(), result=receipt)
    except Exception as exc:
        attempt.update(status="failed_no_automatic_retry", error=repr(exc),
                       traceback=traceback.format_exc(), failed_at=datetime.now(timezone.utc).isoformat())
        raise
    finally:
        for fd in reversed(fds):
            os.close(fd)
        attempt_path.write_text(json.dumps(attempt, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
