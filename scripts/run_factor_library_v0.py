"""Single entry point for the small factor library v0 controlled study.

Modes:
  prepare --output DIR   Freeze sources, identities, protocol; no accounts run.
  run     --protocol P --output DIR   (added in a later task) replay 8 paths.

Read-only with respect to every frozen input. New output directories must not
exist; the next numeric sibling is used instead of overwriting anything.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.dont_write_bytecode = True
from lei_signal.research import definitions as d  # noqa: E402 -- standalone entry point

STUDY = "research-factor-library-v0-2026-09-09"
RAW_ROOT = ROOT / "docs/experiments/raw" / STUDY

# Sources this study actually consumes (registry source keys).
CONSUMED_SOURCES = [
    "mixed_prices",
    "mixed_actions",
    "mixed_pool",
    "defense_code",
    "defense_protocol",
    "defense_results",
    "concentration_code",
]

VARIANTS = {
    "E00": {"rank_top3": False, "volatility_filter": False, "allocation": "eligible_equal"},
    "E01": {"rank_top3": False, "volatility_filter": True, "allocation": "eligible_equal"},
    "E10": {"rank_top3": True, "volatility_filter": False, "allocation": "top3_equal"},
    "E11": {"rank_top3": True, "volatility_filter": True, "allocation": "top3_equal"},
}
FEES = [0.001, 0.002]
MAX_PATHS = 8

BASELINE_TESTS = [
    "tests/unit/test_research_definitions.py",
    "tests/unit/test_experiment_reports.py",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fresh_dir(requested: Path) -> Path:
    """Never overwrite: bump the final -NN suffix to the first free sibling."""
    if not requested.exists():
        return requested
    stem = requested.name
    parent = requested.parent
    if "-" in stem and stem.rsplit("-", 1)[1].isdigit():
        base, _ = stem.rsplit("-", 1)
    else:
        base = stem
    n = 1
    while True:
        candidate = parent / f"{base}-{n:02d}"
        if not candidate.exists():
            return candidate
        n += 1


def save_json(path: Path, obj) -> None:
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8"
    )


def source_status(reg: dict) -> dict:
    rows = {}
    consumed_objects = _objects_by_source(reg)
    for key, src in reg["sources"].items():
        p = ROOT / src["path"]
        actual = sha256(p) if p.is_file() else None
        rows[key] = {
            "path": src["path"],
            "registered_sha256": src["sha256"],
            "actual_sha256": actual,
            "match": actual == src["sha256"],
            "consumed_in_study": key in CONSUMED_SOURCES,
            "objects_referencing_source": consumed_objects.get(key, []),
        }
    return rows


def _objects_by_source(reg: dict) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    profiles = reg.get("profiles", {})

    def expand(obj):
        card = dict(profiles.get(obj.get("profile"), {}))
        for k, v in obj.items():
            card[k] = v
        return card

    for obj in reg["objects"]:
        card = expand(obj)
        for key in card.get("sources", []):
            out.setdefault(key, []).append(f"{card['id']}@{card['version']}")
    return out


def completed_months(prices_path: Path, protocol_end: str) -> dict:
    """Last union quote date per calendar month; completeness declared, not guessed."""
    p = pd.read_csv(prices_path, dtype={"symbol": str, "date": str})
    union = sorted(p.date.unique())
    frame = pd.DataFrame({"date": pd.to_datetime(union)})
    frame["month"] = frame.date.dt.strftime("%Y-%m")
    last_by_month = frame.groupby("month").date.max().dt.strftime("%Y-%m-%d").to_dict()
    month_index = pd.period_range("2020-11", protocol_end[:7], freq="M").strftime("%Y-%m")
    months = {m: last_by_month.get(m) for m in month_index}
    missing_months = [m for m, d in months.items() if d is None]
    observed_last = union[-1]
    return {
        "decision_months": months,
        "months_without_any_union_quote": missing_months,
        "observed_last_input_date": observed_last,
        "declared_end_from_frozen_protocol": protocol_end,
        "final_month_complete_by_protocol_declaration": observed_last == protocol_end,
        "calendar_limitation": (
            "Union dates are those with at least one quote among the 14 products; "
            "a session missing for the whole pool cannot be distinguished from a non-session. "
            "Historical real-exchange calendar qualification is not certified here."
        ),
    }


def data_layers(actions_path: Path) -> dict:
    events = json.loads(actions_path.read_text(encoding="utf-8"))["events"]
    with_available_at = sum(1 for e in events if e.get("available_at"))
    return {
        "numerical_reconstruction": (
            "qualified: nominal prices and normalized actions match frozen source hashes"
        ),
        "historical_point_in_time_availability": (
            f"not_certified: {with_available_at}/{len(events)} events carry available_at; "
            "strict economic_index availability checks cannot be satisfied; "
            "historical reconstruction only"
        ),
        "actual_execution_capacity": (
            "not_accepted: frozen protocol evidence limits apply "
            "(surviving pool, duplicated exposures)"
        ),
        "reconstruction_time": datetime.now(UTC).isoformat(),
        "reconstruction_time_note": (
            "this run time labels today's historical rebuild, "
            "not a historical availability claim"
        ),
    }


def run_prepare(output: Path) -> Path:
    out = fresh_dir(output)
    out.mkdir(parents=True)

    reg = d.load_registry()
    sources = source_status(reg)
    drifted = {k: v for k, v in sources.items() if not v["match"]}
    blocked = []
    for key, v in drifted.items():
        blocked.append(
            {
                "source": key,
                "path": v["path"],
                "affected_objects": v["objects_referencing_source"],
                "consumed_in_study": v["consumed_in_study"],
                "reason": "registered sha256 does not match current file",
            }
        )

    # Workspace state (the plan knows the tree has unrelated uncommitted work).
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--short"], cwd=ROOT, capture_output=True, text=True
    ).stdout
    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip()
    (out / "workspace-status.txt").write_text(
        f"HEAD={head}\nbranch={branch}\n\ngit status --short:\n{status}",
        encoding="utf-8",
    )

    # Baseline regression run with full evidence (the 32 tests current at planning).
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", *BASELINE_TESTS, "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    (out / "baseline-tests.txt").write_text(
        f"command: {sys.executable} -m pytest {' '.join(BASELINE_TESTS)} -q\n"
        "--- stdout ---\n"
        f"{proc.stdout}\n--- stderr ---\n{proc.stderr}",
        encoding="utf-8",
    )
    if proc.returncode != 0:
        blocked.append({"reason": "baseline regression failed", "see": "baseline-tests.txt"})

    save_json(out / "source-inventory.json", {"sources": sources, "drifted": list(drifted)})

    # Byte-for-byte snapshot of the single registry; hash recorded in protocol.
    registry_path = ROOT / "docs/research/definitions.v1.json"
    snapshot = out / "frozen-definitions.v1.0.0.json"
    snapshot.write_bytes(registry_path.read_bytes())
    registry_sha = sha256(snapshot)

    src = reg["sources"]
    prices_path = ROOT / src["mixed_prices"]["path"]
    actions_path = ROOT / src["mixed_actions"]["path"]
    defense_protocol = json.loads((ROOT / src["defense_protocol"]["path"]).read_text())

    protocol = {
        "study": "factor-library-v0",
        "prepared_at": datetime.now(UTC).isoformat(),
        "plan": "docs/superpowers/plans/2026-09-09-factor-library-v0.md@1.0.0",
        "principles_version": "1.0",
        "definition_standard_version": reg["standard_version"],
        "registry": {
            "path": "docs/research/definitions.v1.json",
            "version": reg["version"],
            "object_count": len(reg["objects"]),
            "frozen_snapshot": snapshot.name,
            "frozen_snapshot_sha256": registry_sha,
        },
        "accounts": {
            "symbols": defense_protocol["symbols"],
            "start": defense_protocol["start"],
            "end": defense_protocol["end"],
            "initial_cash": defense_protocol["initial_cash"],
            "external_flows": 0,
            "cash_interest": 0,
            "lot": defense_protocol["lot"],
            "fees": FEES,
            "max_new_paths": MAX_PATHS,
            "monthly_rebalance": True,
            "inter_month_rebalance": False,
            "sma_exit": False,
            "fast_reentry": False,
            "warmup": (
                "original full14 preparation inputs; dynamic 273 valid-quote "
                "eligibility; 252/21 momentum"
            ),
        },
        "variants": VARIANTS,
        "variant_rules": {
            "eligibility": (
                "current valid quote AND valid_count>=273 AND finite momentum"
            ),
            "negative_momentum": "allowed",
            "ties": (
                "exact score equality, symbol code ascending"
            ),
            "nan_rv_percentile": "pass_legacy with explicit count output",
            "rv_exclusion": "exclude rv_percentile >= 0.8 exactly",
            "no_candidates": "all cash, empty selection, zero weights",
            "duplicate_economic_directions": "allowed; not removed",
            "filter_then_rank": (
                "volatility filter applied before top3; "
                "filtered products never backfilled"
            ),
        },
        "comparisons": {
            "primary": "E11-E10: adding the volatility filter inside the existing strength policy",
            "secondary": "E01-E00: filter effect without ranking; interaction description only",
            "label_rule": (
                "E10-E00 changes both ranking and concentration; label as policy "
                "difference, never pure momentum premium"
            ),
        },
        "frozen_sources": {k: src[k] for k in CONSUMED_SOURCES},
        "defense_baseline_results": src["defense_results"],
        "compatibility_replays": (
            "at most 2 (E11 at each fee), legacy function replay for compatibility "
            "only, not new evidence"
        ),
        "stop_conditions": [
            "source fingerprint drift",
            "E11 legacy compatibility mismatch",
            "account reconciliation beyond CNY 0.01",
        ],
        "phases": [
            {"label": "2020Dec-2024", "start": "2020-12-01", "end": "2024-12-31"},
            {"label": "2025-2026Jun", "start": "2025-01-01", "end": "2026-06-30"},
        ],
        "phase_rule": (
            "cut one continuous path only; no fresh cash injection or position "
            "reset at phase start"
        ),
        "completed_months": completed_months(prices_path, defense_protocol["end"]),
        "data_layers": data_layers(actions_path),
        "production_authorization": "not_authorized",
        "okr_update": False,
    }
    save_json(out / "protocol.json", protocol)

    status_word = "blocked_items" if blocked else "preparation_complete"
    try:
        output_name = str(out.relative_to(ROOT))
    except ValueError:
        output_name = str(out)
    result = {
        "status": status_word,
        "output": output_name,
        "blocked_items": blocked,
        "baseline_exit_code": proc.returncode,
    }
    save_json(out / "preparation-result.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return out


# ---------------------------------------------------------------------------
# run mode
# ---------------------------------------------------------------------------

from lei_signal.research import factor_account_adapter as fa  # noqa: E402
from lei_signal.research import factor_diagnostics as fd  # noqa: E402
from lei_signal.research import factor_runtime as fr  # noqa: E402

CODE_FILES = [
    ROOT / "src/lei_signal/research/definitions.py",
    ROOT / "src/lei_signal/research/factor_runtime.py",
    ROOT / "src/lei_signal/research/factor_account_adapter.py",
    ROOT / "src/lei_signal/research/factor_diagnostics.py",
    ROOT / "scripts/run_factor_library_v0.py",
]
TEST_FILES = [
    "tests/unit/test_research_definitions.py",
    "tests/unit/test_factor_runtime.py",
    "tests/unit/test_factor_account_adapter.py",
    "tests/unit/test_factor_diagnostics.py",
    "tests/unit/test_experiment_reports.py",
]
BOUND_REFS = [
    "mixed.price.economic@1.0.0",
    "mixed.asset.total_return@1.0.0",
    "cash.zero@1.0.0",
    "mixed.momentum.raw@1.0.0",
    "mixed.rv20@1.0.0",
    "mixed.rv_percentile@1.0.0",
    "mixed.volatility_allowed@1.0.0",
    "mixed.eligible@1.0.0",
    "mixed.momentum.rank@1.0.0",
    "mixed.top3@1.0.0",
    "mixed.target.equal@1.0.0",
    "trend.sma200@1.0.0",
    "trend.distance200@1.0.0",
    "trend.above200@1.0.0",
    "risk.product_account_weight@1.0.0",
    "risk.direction_account_weight@1.0.0",
    "risk.product_invested_weight@1.0.0",
    "risk.profit_direction_share@1.0.0",
]
VARIANT_POLICY_PROPOSAL = {
    "E00": "policy.mixed.eligible_equal@1.0.0",
    "E01": "policy.mixed.eligible_equal_rv_filtered@1.0.0",
    "E10": "policy.mixed.top3_equal@1.0.0",
    "E11": "mixed.no_exit_100@1.0.0",
}
VALUE_REFS = {
    "selected": "mixed.momentum.rank@1.0.0 / mixed.eligible@1.0.0",
    "scores": "mixed.momentum.raw@1.0.0",
    "weights": "mixed.target.equal@1.0.0",
    "exclusion_reasons": "mixed.volatility_allowed@1.0.0 (rv_percentile>=0.8 exact)",
}


def _load_snapshot_registry(prepare_dir: Path):
    snapshot = prepare_dir / "frozen-definitions.v1.0.0.json"
    registry = json.loads(snapshot.read_text(encoding="utf-8"))
    d.validate_registry(registry)
    return registry, snapshot


def _compatibility_gate(key_to_account, exec_dir: Path) -> dict:
    """E11 at both fees must reproduce frozen no_exit_100 paths exactly."""
    report = {"checked": [], "passed": True}
    for fee in FEES:
        key = f"E11-fee{fee:.3f}"
        legacy_id = f"no_exit_100-fee{fee:.3f}"
        out = key_to_account[key]
        frozen_eq = pd.read_csv(exec_dir / "equity.csv", dtype={"date": str})
        frozen_eq = frozen_eq[frozen_eq.account_id == legacy_id].drop(columns=["account_id"])
        got_eq = out["equity"].drop(columns=["account_id"]).reset_index(drop=True)
        frozen_eq = frozen_eq.reset_index(drop=True)
        diff = got_eq.select_dtypes("number") - frozen_eq.select_dtypes("number")
        max_eq_err = float(diff.abs().max().max())
        frozen_tr = pd.read_csv(exec_dir / "trades.csv", dtype={"date": str, "symbol": str})
        frozen_tr = frozen_tr[frozen_tr.account_id == legacy_id].reset_index(drop=True)
        got_tr = out["trades"].reset_index(drop=True)
        trades_match = (
            len(got_tr) == len(frozen_tr)
            and (got_tr.date.astype(str) == frozen_tr.date).all()
            and (got_tr.symbol.astype(str) == frozen_tr.symbol).all()
            and (got_tr.side == frozen_tr.side).all()
            and (got_tr.qty.astype(float) == frozen_tr.qty.astype(float)).all()
            and (got_tr.price.astype(float) == frozen_tr.price.astype(float)).all()
        )
        frozen_sig = pd.read_csv(exec_dir / "signals.csv", dtype=str)
        frozen_sig = frozen_sig[frozen_sig.account_id == legacy_id].reset_index(drop=True)
        got_sig = out["signals"].reset_index(drop=True)
        signals_match = (
            len(got_sig) == len(frozen_sig)
            and (got_sig.eligible_date == frozen_sig.eligible_date).all()
            and (got_sig.selected == frozen_sig.selected).all()
            and (got_sig.weights == frozen_sig.weights).all()
        )
        ok = bool(max_eq_err <= 1e-6 and trades_match and signals_match)
        report["passed"] = bool(report["passed"]) and ok
        report["checked"].append(
            dict(
                key=key,
                legacy_id=legacy_id,
                max_equity_abs_error=max_eq_err,
                trades_row_exact=bool(trades_match),
                signals_row_exact=bool(signals_match),
                passed=ok,
            )
        )
    return report


def _phase_frames(acc, raw_events, prices, groups, phase_start, phase_end, initial):
    equity = acc["equity"]
    if phase_start == "2020-12-01":
        opening = pd.DataFrame([{**{c: 0.0 for c in equity.columns if c.startswith("units_")},
                                 "date": "2020-11-30", "equity": initial,
                                 "cash": initial, "receivable": 0.0,
                                 "market_value": 0.0, "exposure": 0.0, "fees": 0.0}])
    else:
        opening = equity[equity.date < phase_start].tail(1)
    after_open = opening.iloc[0].date
    window = acc["trades"][(acc["trades"].date > after_open) & (acc["trades"].date <= phase_end)]
    events = acc["actions"][(acc["actions"].date > after_open) & (acc["actions"].date <= phase_end)]
    contrib = fd.phase_contributions(
        equity=equity[(equity.date >= phase_start) & (equity.date <= phase_end)],
        opening_equity=opening,
        trades=window,
        events=events,
        actions=raw_events,
        prices=prices,
        phase_start=phase_start,
        phase_end=phase_end,
    )
    end_equity = float(equity[equity.date <= phase_end].iloc[-1].equity)
    start_equity = float(opening.iloc[0].equity)
    error = float(contrib.net_contribution.sum()) - (end_equity - start_equity)
    by_direction = (
        contrib.assign(direction=contrib.symbol.map(groups))
        .groupby("direction", as_index=False)
        .net_contribution.sum()
    )
    by_direction["profit_direction_share"] = (
        by_direction.net_contribution / (end_equity - initial) if end_equity != initial else np.nan
    )
    return contrib, by_direction, dict(
        phase_start=phase_start,
        phase_end=phase_end,
        start_equity=start_equity,
        end_equity=end_equity,
        sum_contribution=float(contrib.net_contribution.sum()),
        abs_error=abs(error),
        passed=abs(error) <= fd.RECONCILE_TOLERANCE,
    )


def run_study(
    protocol_path: Path,
    output: Path,
    *,
    run_tests: bool,
    extra_attempts=None,
) -> Path:
    protocol_path = protocol_path.resolve()
    prepare_dir = protocol_path.parent
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if protocol["accounts"]["max_new_paths"] != MAX_PATHS or protocol["accounts"]["fees"] != FEES:
        raise ValueError("protocol fees/path cap differ from the frozen study constants")
    if set(protocol["variants"]) != set(VARIANTS):
        raise ValueError("protocol variants differ from E00-E11")

    out = fresh_dir(output)
    out.mkdir(parents=True)
    (out / "paths").mkdir()
    attempts = list(extra_attempts or [])

    registry, snapshot = _load_snapshot_registry(prepare_dir)
    snapshot_sha = sha256(snapshot)
    if snapshot_sha != protocol["registry"]["frozen_snapshot_sha256"]:
        raise ValueError("registry snapshot hash does not match protocol freeze")
    d.verify_sources(registry)

    if run_tests:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", *TEST_FILES, "-q"],
            cwd=ROOT, capture_output=True, text=True,
        )
        (out / "test-results.txt").write_text(
            "--- stdout ---\n"
            f"{proc.stdout}\n--- stderr ---\n{proc.stderr}\n"
            f"exit_code: {proc.returncode}",
            encoding="utf-8",
        )
        if proc.returncode != 0:
            save_json(out / "summary.json", {"status": "blocked", "reason": "tests failed"})
            return out

    src = registry["sources"]
    prices = pd.read_csv(ROOT / src["mixed_prices"]["path"], dtype={"symbol": str, "date": str})
    raw_actions = json.loads((ROOT / src["mixed_actions"]["path"]).read_text())["events"]
    symbols = protocol["accounts"]["symbols"]
    months = sorted(protocol["completed_months"]["decision_months"].values())

    fa.load_frozen_defense(registry)  # import-side hash verification
    groups = fd.load_direction_groups(registry)
    if set(groups) != set(symbols):
        raise ValueError("frozen direction groups do not cover the protocol pool")

    identity = {
        "currency": "CNY",
        "price_basis": "nominal_close",
        "symbols": symbols,
        "historical_reconstruction_only": True,
    }
    batch = fr.build_mixed_batch(prices, raw_actions, registry=registry, input_identity=identity)

    # global mark table for weights/diagnostics
    equity_dates = pd.date_range(
        protocol["accounts"]["start"], protocol["accounts"]["end"], freq="D"
    ).strftime("%Y-%m-%d")
    all_marks = fd.build_marks(equity_dates, symbols, prices, raw_actions)

    # E11 gate first; no E00/E01/E10 interpretation until it closes.
    gate_decisions = fr.monthly_decisions(
        batch, variant="E11", completed_months=months, symbols=symbols
    )
    gate_accounts = {}
    for fee in FEES:
        gate_accounts[f"E11-fee{fee:.3f}"] = fa.replay_account(
            registry=registry, batch=batch, decisions=gate_decisions,
            prices=prices, actions=raw_actions, fee=fee, variant="E11",
        )
    exec_dir = ROOT / src["defense_results"]["path"]
    exec_dir = exec_dir.parent
    gate = _compatibility_gate(gate_accounts, exec_dir)
    save_json(out / "compatibility.json", gate)
    if not gate["passed"]:
        save_json(
            out / "summary.json",
            {"status": "blocked", "reason": "E11 compatibility gate failed"},
        )
        return out

    accounts = dict(gate_accounts)
    for variant in ("E00", "E01", "E10"):
        decisions = fr.monthly_decisions(
            batch, variant=variant, completed_months=months, symbols=symbols
        )
        for fee in FEES:
            accounts[f"{variant}-fee{fee:.3f}"] = fa.replay_account(
                registry=registry, batch=batch, decisions=decisions,
                prices=prices, actions=raw_actions, fee=fee, variant=variant,
            )
    if len(accounts) != MAX_PATHS:
        raise ValueError("path cap violated")

    now = pd.Timestamp.now(tz="Asia/Shanghai")
    initial = protocol["accounts"]["initial_cash"]
    quality = {"paths": {}}
    summaries = {}
    for key in sorted(accounts):
        variant, fee_text = key.split("-fee")
        fee = float(fee_text)
        acc = accounts[key]
        pdir = out / "paths" / key
        pdir.mkdir()
        for table in ("equity", "trades", "orders", "signals", "actions", "annual",
                      "per_symbol_legacy", "reentry_events", "periods", "reentry_diagnostics"):
            frame = acc[table]
            if table == "signals" and len(frame):
                frame = frame.copy()
                frame["definition_refs"] = json.dumps(VALUE_REFS, ensure_ascii=False)
            frame.to_csv(pdir / f"{table}.csv", index=False)

        contrib = fd.capital_contributions(
            equity=acc["equity"], trades=acc["trades"], events=acc["actions"],
            actions=raw_actions, prices=prices, initial=initial,
        )
        recon = fd.reconcile(contributions=contrib, equity=acc["equity"], initial=initial)
        contrib.to_csv(pdir / "capital-contributions.csv", index=False)

        phases = []
        phase_blocks = []
        for label, lo, hi in (
            ("2020Dec-2024", "2020-12-01", "2024-12-31"),
            ("2025-2026Jun", "2025-01-01", "2026-06-30"),
        ):
            pc, direction_share, pcheck = _phase_frames(
                acc, raw_actions, prices, groups, lo, hi, initial
            )
            pc = pc.assign(phase=label)
            phases.append(pc)
            phase_blocks.append({**pcheck, "label": label})
            direction_share.to_csv(pdir / f"direction-profit-{label}.csv", index=False)
        pd.concat(phases).to_csv(pdir / "phase-contributions.csv", index=False)

        product_weights = fd.daily_product_weights(acc["equity"], all_marks)
        product_weights.to_csv(pdir / "product-weights.csv", index=False)
        direction_weights = fd.direction_weights_from_product(product_weights, groups)
        direction_weights.to_csv(pdir / "direction-weights.csv", index=False)

        holdings = _holdings_description(acc, batch, months, symbols)
        holdings.to_csv(pdir / "holdings-description.csv", index=False)

        direction_profit = (
            contrib.assign(direction=contrib.symbol.map(groups))
            .groupby("direction", as_index=False)
            .agg(net_contribution=("net_contribution", "sum"))
        )
        total_pnl = float(acc["equity"].iloc[-1].equity) - initial
        direction_profit["profit_direction_share"] = (
            direction_profit.net_contribution / total_pnl if total_pnl else np.nan
        )
        direction_profit.to_csv(pdir / "direction-profit-full.csv", index=False)

        manifest = d.make_manifest(
            registry=registry,
            registry_path=snapshot,
            references=BOUND_REFS + (["mixed.no_exit_100@1.0.0"] if variant == "E11" else []),
            code_files=CODE_FILES + [ROOT / src["defense_code"]["path"]],
            input_files=[
                ROOT / src["mixed_prices"]["path"],
                ROOT / src["mixed_actions"]["path"],
                ROOT / src["mixed_pool"]["path"],
                protocol_path,
            ],
            data_cutoff="2026-06-30T15:00:00+08:00",
            available_at=now.isoformat(),
            decision_at=(now + pd.Timedelta(seconds=1)).isoformat(),
            protocol=protocol_path,
            pool_version=f"full14 reconstructed; pool sha256 {src['mixed_pool']['sha256'][:12]}",
            quality={
                "historical_point_in_time_availability": "not_certified",
                "execution_capacity": "not_accepted",
                "reconciliation": recon,
                "phase_reconciliation": phase_blocks,
            },
        )
        manifest.update(
            {
                "variant": variant,
                "fee": fee,
                "account_id": key,
                "legacy_account_id": acc["summary"]["legacy_account_id"],
                "policy_ref": VARIANT_POLICY_PROPOSAL[variant],
                "policy_status": (
                    "executed_compatibility_reference" if variant == "E11" else "proposal"
                ),
                "production_authorization": "not_authorized",
            }
        )
        save_json(pdir / "manifest.json", manifest)

        quality["paths"][key] = {"full_window": recon, "phases": phase_blocks}
        summaries[key] = acc["summary"]

    comparison = fd.compare_accounts(accounts)
    comparison.to_csv(out / "decision-comparisons.csv", index=False)

    quality["worst_full_window_error"] = max(
        v["full_window"]["max_abs_error"] for v in quality["paths"].values()
    )
    quality["worst_phase_error"] = max(
        ph["abs_error"] for v in quality["paths"].values() for ph in v["phases"]
    )
    quality["tolerance_cny"] = fd.RECONCILE_TOLERANCE
    quality["passed"] = bool(
        quality["worst_full_window_error"] <= fd.RECONCILE_TOLERANCE
        and quality["worst_phase_error"] <= fd.RECONCILE_TOLERANCE
    )
    save_json(out / "quality-report.json", quality)

    save_json(
        out / "summary.json",
        {
            "status": "run_complete",
            "protocol": (
                str(protocol_path.relative_to(ROOT))
                if protocol_path.is_relative_to(ROOT) else str(protocol_path)
            ),
            "registry_version": registry["version"],
            "registry_snapshot_sha256": snapshot_sha,
            "paths": len(accounts),
            "compatibility_gate": gate,
            "accounts": summaries,
            "primary_question": "E11-E10: what does the volatility filter change?",
            "evidence_rule": (
                "positive filter result in ranked paths and negative result in "
                "equal paths are both reported; no variant is deleted"
            ),
            "production_authorization": "not_authorized",
        },
    )
    save_json(
        out / "attempts.json",
        {
            "attempts": attempts
            + [
                dict(
                    attempt=(
                        str(out.relative_to(ROOT))
                        if out.is_relative_to(ROOT) else str(out)
                    ),
                    status="run_complete",
                    gate_passed=gate["passed"],
                    reconciliation_passed=quality["passed"],
                )
            ]
        },
    )
    _write_artifact_manifest(out)
    try:
        output_name = str(out.relative_to(ROOT))
    except ValueError:
        output_name = str(out)
    print(json.dumps({"status": "run_complete", "output": output_name}, indent=2))
    return out


def _holdings_description(acc, batch, months, symbols):
    eq = acc["equity"]
    unit_cols = {s: f"units_{s}" for s in symbols}
    rows = []
    values = batch.values
    for day in months:
        if day < eq.date.min() or day > eq.date.max():
            continue
        er = eq[eq.date == day]
        if not len(er):
            continue
        er = er.iloc[0]
        snap = values[values.date == day].set_index("symbol")
        for s in symbols:
            units = float(er.get(unit_cols[s], 0.0) or 0.0)
            if units <= 0:
                continue
            r = snap.loc[s] if s in snap.index else None
            rows.append(
                dict(
                    date=day,
                    symbol=s,
                    units=units,
                    above_sma200=None if r is None else float(r.above200),
                    distance200=None if r is None else float(r.distance200),
                    momentum=None if r is None or not pd.notna(r.momentum) else float(r.momentum),
                    role="holding_description_only_not_entry_signal",
                )
            )
    return pd.DataFrame(rows)


def _write_artifact_manifest(out: Path):
    files = []
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name != "artifact-manifest.json":
            files.append({"path": str(p.relative_to(out)), "sha256": sha256(p)})
    save_json(out / "artifact-manifest.json", {"files": files})


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    p_prep = sub.add_parser("prepare")
    p_prep.add_argument("--output", required=True)
    p_run = sub.add_parser("run")
    p_run.add_argument("--protocol", required=True)
    p_run.add_argument("--output", required=True)
    p_run.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args(argv)

    def resolve(value: str) -> Path:
        p = Path(value)
        return p if p.is_absolute() else ROOT / p

    if args.mode == "prepare":
        run_prepare(resolve(args.output))
        return 0
    if args.mode == "run":
        run_study(
            resolve(args.protocol),
            resolve(args.output),
            run_tests=not args.skip_tests,
        )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
