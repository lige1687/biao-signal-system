"""Read real frozen inputs and run minimum synthetic rules; no market study."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

from verify_handoff import verify


def main(root: Path) -> dict:
    root = root.resolve()
    preflight = verify(root)
    assert preflight["integrity"] == "passed", preflight["errors"]
    sys.path.insert(0, str(root / "src"))
    import numpy as np
    import pandas as pd
    from lei_signal.features.indicators import compute_features
    from lei_signal.rules.lei_color import classify_colors
    from lei_signal.rules.first_ma_pullback import detect_first_ma_pullback_events

    relative = "docs/experiments/raw/research-broad-etf-technical-2026-09-08/execution/inputs/bars/sh510300-nominal.csv"
    path = root / relative
    bars = pd.read_csv(path, parse_dates=["date"]).set_index("date")
    assert not bars.empty and bars.index.is_monotonic_increasing and bars.index.is_unique
    frame = classify_colors(compute_features(bars.iloc[:180].copy()))
    assert np.isfinite(frame["sma120"].iloc[-1])
    # Invoke the production detector on the existing deterministic hand fixture.
    test_file = root / "tests/unit/test_first_ma_pullback.py"
    spec = importlib.util.spec_from_file_location("handoff_synthetic_fixture", test_file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # These tests use only generated data and explicitly exercise actual rules.
    tests = ["test_gate_and_first_touch_then_early_and_confirmed_entries"]
    for name in tests:
        getattr(mod, name)()
    raw = root / "docs/experiments/raw/remote-astra-core-acceptance-2026-10-02/runs/population-asof-partitioned"
    result = json.loads((raw / "result.json").read_text(encoding="utf-8"))
    summary = raw / "population-audit-asof.json"
    assert hashlib.sha256(summary.read_bytes()).hexdigest() == result["replayed_sha256"]
    assert result["reproduced"] == result["frozen"] == 504
    assert result["totals"]["no_departure_before_touch"] == 364
    assert sum(result["traded_totals"].values()) == 11
    assert result["traded_totals"]["no_departure_before_touch"] == 9
    return {"exit_code": 0, "integrity_files": preflight["checked_files"],
            "real_csv": relative, "real_csv_rows": len(bars),
            "feature_prefix_rows": len(frame), "finite_sma120": True,
            "synthetic_rule_checks_passed": tests,
            "saved_audit_summary_verified": True,
            "market_experiments_rerun": 0, "account_backtests_rerun": 0,
            "full_research_qualification": preflight["qualification"],
            "platform_claim": "Only the actually executed host platform is verified"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(main(args.root), ensure_ascii=False, indent=2))
