"""Fixed-input research runner. Real stages require a separate controller release."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import sys
import traceback

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
WORKTREE = HERE.parents[3]
MAIN = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
DESIGN = WORKTREE / "docs/experiments/raw/research-dispatch-controller-2026-10-07/remaining-opportunity-research-20261009/weekly-input-readiness"
PLAN = DESIGN.parent / "daily-weekly-feature-output-plan.json"
MODULE = WORKTREE / "src/lei_signal/research/daily_weekly_opportunity.py"
SOURCE_BINDINGS = DESIGN / "source-bindings.json"
AMENDMENT = DESIGN.parent / "weekly-definition-binding-amendment.json"
CONTRACT = DESIGN / "proposed-contract.json"
CLOSURE = HERE / "dependency-closure.json"
ATTEMPTS = HERE / "attempts"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_bindings():
    if digest(CONTRACT) != "2c0c49bf807f4b7aee3dca404a9fea7943561716bd6af95e831ff69ec38d37ba":
        raise ValueError("accepted design drift")
    bindings = json.loads(SOURCE_BINDINGS.read_text())
    if len(bindings["sources"]) != 27:
        raise ValueError("expected exactly 27 fixed sources")
    amendment = json.loads(AMENDMENT.read_text())
    if amendment.get("schema") != "one-definition-amendment/1" or len(amendment.get("records", [])) != 2:
        raise ValueError("unexpected definition amendment")
    amended = {r["path"]: r for r in amendment["records"]}
    if any(r.get("old_objects_unchanged") != 173 or
           r.get("new_id") != "research.multitimeframe.daily_stage3_at_completed_week@0.1.0"
           for r in amended.values()):
        raise ValueError("definition amendment exceeds approved single object")
    for item in bindings["sources"]:
        p = Path(item["path"])
        expected = item["sha256"]
        if str(p) in amended:
            record = amended[str(p)]
            if record["old_sha256"] != expected or p.name != "definitions.v1.json":
                raise ValueError("unapproved binding replacement")
            expected = record["new_sha256"]
        if not p.is_file() or (str(p) not in amended and p.stat().st_size != item["bytes"]) or digest(p) != expected:
            raise ValueError(f"source drift: {p}")
    closure = json.loads(CLOSURE.read_text())
    for item in closure["files"]:
        p = Path(item["path"])
        if not p.is_file() or p.stat().st_size != item["bytes"] or digest(p) != item["sha256"]:
            raise ValueError(f"code dependency drift: {p}")
    if sys.version.split()[0] != closure["python"]:
        raise ValueError("Python version drift")
    for name, version in closure["packages"].items():
        if importlib.metadata.version(name) != version:
            raise ValueError(f"package drift: {name}")
    return closure


def load_module():
    sys.path.insert(0, str(MAIN / "src"))
    spec = importlib.util.spec_from_file_location("daily_weekly_opportunity", MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_inputs():
    panel = json.loads((MAIN / "docs/experiments/raw/volume-information-2026-09-30/execution/panel.json").read_text())
    raw_calendar = json.loads((MAIN / "docs/experiments/raw/research-calendar-completion-2026-09-10/calendar-merged/calendar.json").read_text())
    if panel.get("price_series") != "economic_price" or panel.get("data_mode") != "historical_reconstruction":
        raise ValueError("wrong panel mode")
    return panel, raw_calendar


def atomic_json(path, payload):
    temp = path.with_name(path.name + ".tmp")
    with temp.open("x") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


def guard_release(release_path, stage):
    if release_path is None:
        raise ValueError("root release required for real stage")
    release = json.loads(Path(release_path).read_text())
    if release.get("status") != "released" or release.get("stage") != stage or release.get("attempt_id") is None:
        raise ValueError("stage not released")
    if release.get("runner_sha256") != digest(__file__) or release.get("module_sha256") != digest(MODULE):
        raise ValueError("release code fingerprints differ")
    if release.get("closure_sha256") != digest(CLOSURE) or release.get("contract_sha256") != digest(CONTRACT):
        raise ValueError("release contract fingerprints differ")
    if release.get("source_bindings_sha256") != digest(SOURCE_BINDINGS):
        raise ValueError("release source bindings differ")
    if release.get("amendment_sha256") != digest(AMENDMENT):
        raise ValueError("release definition amendment differs")
    attempt = release["attempt_id"]
    if not isinstance(attempt, str) or not attempt or not all(c.isalnum() or c in "-_" for c in attempt):
        raise ValueError("invalid attempt id")
    output = Path(release.get("output", ""))
    if not output.is_absolute():
        raise ValueError("absolute external output required")
    # The fixed feature route is reused exactly. Later stages require their own verified plan.
    plan_path = PLAN if stage == "features" else Path(release.get("route_plan", ""))
    if not plan_path.is_file():
        raise ValueError("missing exact route plan")
    plan = json.loads(plan_path.read_text())
    if stage == "features" and plan_path != PLAN:
        raise ValueError("feature plan differs")
    if output != Path(plan["output"]) or release.get("route_plan_sha256") != digest(plan_path):
        raise ValueError("release does not bind route plan")
    sys.path.insert(0, str(MAIN / "src"))
    from lei_signal.research.output_storage import recheck_saved_plan
    recheck_saved_plan(MAIN, plan, plan["task_id"], plan["estimated_bytes"], plan["internal_metadata_bytes"])
    if output.exists():
        raise ValueError("output already exists")
    ATTEMPTS.mkdir(exist_ok=True)
    marker = ATTEMPTS / (stage + "-" + attempt + ".json")
    with marker.open("x") as f:
        json.dump({"stage": stage, "attempt_id": attempt, "release": str(release_path),
                   "release_sha256": digest(release_path), "started_at": datetime.now(timezone.utc).isoformat(),
                   "output": str(output)}, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    return output, marker


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("qualify-dates", "features", "labels", "effect"))
    parser.add_argument("--release")
    parser.add_argument("--input")
    args = parser.parse_args()
    verify_bindings()  # before import or opening panel/calendar values
    module = load_module()
    if args.mode == "qualify-dates":
        receipt = HERE / "date-qualification.json"
        if receipt.exists():
            raise ValueError("date qualification attempt already consumed")
        panel, source = load_inputs()
        calendar = module.covered_calendar(source["days"])
        result = module.qualify_dates(panel["bars"], calendar)
        atomic_json(receipt, {"attempt": 1, "mode": "date_fields_only", "result": result,
                              "source_bindings_sha256": digest(SOURCE_BINDINGS),
                              "contract_sha256": digest(CONTRACT),
                              "created_at": datetime.now(timezone.utc).isoformat()})
        print(json.dumps({"receipt": str(receipt), "status": result["status"]}))
        return
    date_receipt = json.loads((HERE / "date-qualification.json").read_text())
    if date_receipt["result"]["status"] != "passed":
        raise ValueError("date qualification did not pass")
    output, marker = guard_release(args.release, args.mode)
    try:
        import pandas as pd
        if args.mode == "features":
            panel, source = load_inputs()
            calendar = module.covered_calendar(source["days"])
            rows = []
            for asset in module.ASSETS:
                bars = [r for r in panel["bars"] if r["asset"] == asset]
                daily = pd.DataFrame(bars).set_index("date")
                daily.index = pd.DatetimeIndex(daily.index)
                for row in module.feature_rows(daily, calendar):
                    rows.append({"asset": asset, **row,
                                 "label_dates": module.label_dates(row["observation_at"], calendar)})
            payload = {"mode": "features_only", "support": module.support_cells(rows), "rows": rows}
        elif args.mode == "labels":
            # A separate release binds a stage-1 support file by exact SHA.
            source_file = Path(args.input or "")
            release = json.loads(Path(args.release).read_text())
            if digest(source_file) != release.get("input_sha256"):
                raise ValueError("feature support input drift")
            panel, _ = load_inputs()
            closes = {(r["asset"], r["date"]): r["close"] for r in panel["bars"]}
            features = json.loads(source_file.read_text())["rows"]
            rows = []
            for row in features:
                dates = row.get("label_dates")
                if not row["qualified"] or dates is None or row["phase"] is None:
                    continue
                asset = row["asset"]
                all_dates = sorted(d for a, d in closes if a == asset and dates[0] <= d <= dates[1])
                if len(all_dates) != 21 or all_dates[0] != dates[0] or all_dates[-1] != dates[1]:
                    raise ValueError("label session gap")
                values = [closes[(asset, d)] for d in all_dates]
                rows.append({"asset": asset, "phase": row["phase"], "observation_at": row["observation_at"],
                             "B1": row["B1"], "X": row["X"], "s1": dates[0], "s21": dates[1],
                             "weekly_sma120_direction": row["weekly_sma120_direction"],
                             "weekly_ema120_direction": row["weekly_ema120_direction"],
                             **module.label_values(values)})
            payload = {"mode": "labels_only", "rows": rows}
        else:
            source_file = Path(args.input or "")
            release = json.loads(Path(args.release).read_text())
            if digest(source_file) != release.get("input_sha256"):
                raise ValueError("label input drift")
            rows = json.loads(source_file.read_text())["rows"]
            payload = {"mode": "fixed_descriptive_effect", "groups": module.describe_effect(rows),
                       "rows": rows}
        output.parent.mkdir(parents=True, exist_ok=False)
        plan_file = PLAN if args.mode == "features" else Path(json.loads(Path(args.release).read_text())["route_plan"])
        planned = json.loads(plan_file.read_text())
        if output.parent.stat().st_dev != planned["external_device"]:
            raise ValueError("external output device changed before write")
        atomic_json(output, payload)
        if output.stat().st_dev != planned["external_device"]:
            raise ValueError("external output device changed during write")
        with marker.open("r+") as f:
            status = json.load(f)
            status.update({"finished_at": datetime.now(timezone.utc).isoformat(),
                           "output_sha256": digest(output)})
            f.seek(0)
            json.dump(status, f, indent=2)
            f.truncate()
        print(json.dumps({"output": str(output), "sha256": digest(output)}))
    except Exception:
        with marker.open("a") as f:
            f.write("\nFAILED\n" + traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
