#!/usr/bin/env python3
"""隔离调用锁定的旧函数，仅复算 A/B；不调用任一旧脚本的 main。"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "source"
INPUTS = ROOT / "inputs"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    # 先把锁定副本注册为旧模块名，确保组合脚本不会导入仓库外的同名文件。
    load_module("run_siphon_detector", SOURCE / "run_siphon_detector.py")
    rps = load_module("locked_run_portfolio_split", SOURCE / "run_portfolio_split.py")
    rps.SRC = INPUTS
    rps.RAW = ROOT / "blocked_old_output_path"

    before = {str(p.relative_to(ROOT)): sha256(p) for p in sorted((INPUTS).rglob("*")) if p.is_file()}
    before.update({str(p.relative_to(ROOT)): sha256(p) for p in sorted(SOURCE.rglob("*")) if p.is_file()})

    breadth = rps.load_breadth()
    members = [(k, v) for k, v in {**rps.GATED, **rps.TREND}.items()]
    prices, _unused_split, allgate = rps.build_universe(breadth, members)
    ones = pd.DataFrame(1.0, index=prices.index, columns=prices.columns)
    sim_a = rps.simulate(prices, ones)
    sim_b = rps.simulate(prices, allgate)
    metrics = {"A_等权持有": rps.metrics(sim_a["eq"]), "B_全宽度闸": rps.metrics(sim_b["eq"])}

    old = json.loads((Path(__file__).resolve().parents[2] / "portfolio_split" / "portfolio_split_results.json").read_text())
    old_ab = {k: old["arms"][k] for k in metrics}
    stress = json.loads((Path(__file__).resolve().parents[2] / "portfolio_split" / "bform_stress_results.json").read_text())
    stress_ref = stress["S1_fees"]["rows"]["10bp"]

    curve = pd.DataFrame({"A_legacy_equity": sim_a["eq"], "B_legacy_equity": sim_b["eq"]})
    curve.index.name = "date"
    curve.to_csv(ROOT / "legacy-ab-daily-equity.csv", float_format="%.15g")

    def delta(now: dict, ref: dict) -> dict:
        return {k: round(float(now[k]) - float(ref[k]), 12) for k in now if now[k] is not None and ref.get(k) is not None}

    after = {str(p.relative_to(ROOT)): sha256(p) for p in sorted((INPUTS).rglob("*")) if p.is_file()}
    after.update({str(p.relative_to(ROOT)): sha256(p) for p in sorted(SOURCE.rglob("*")) if p.is_file()})
    result = {
        "scope": "locked legacy A/B only; no C, no search, no corrected ledger",
        "source_loading": "importlib loaded locked copies; old main functions were not called",
        "window": [str(prices.index.min().date()), str(prices.index.max().date())],
        "rows": int(len(prices)),
        "instruments": list(prices.columns),
        "metrics": metrics,
        "cost_drag_pct_sum": {"A_等权持有": round(sim_a["cost_drag_total"] * 100, 8), "B_全宽度闸": round(sim_b["cost_drag_total"] * 100, 8)},
        "old_portfolio_split_reference": old_ab,
        "delta_vs_old_portfolio_split": {k: delta(metrics[k], old_ab[k]) for k in metrics},
        "old_bform_stress_10bp_B_reference": stress_ref,
        "delta_B_vs_old_bform_stress_10bp": delta(metrics["B_全宽度闸"], stress_ref),
        "weight_drift_diagnostic": "../weight-drift-check.json",
        "input_hashes_before": before,
        "input_hashes_after": after,
        "inputs_unchanged": before == after,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "parquet_engine_pyarrow": __import__("pyarrow").__version__,
        },
    }
    (ROOT / "legacy-ab-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    (ROOT / "input-hashes.sha256").write_text("".join(f"{h}  {p}\n" for p, h in sorted(after.items())))


if __name__ == "__main__":
    main()
