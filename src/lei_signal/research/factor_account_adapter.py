"""Read-only replay of the frozen mixed-pool account engine.

The v0 variants differ only in monthly selection/weights; execution stays with
the frozen ``simulate(method='no_exit_100', ...)`` function. This module imports
that code after verifying its hash, never calls its ``main()`` and never mutates
its module globals. New runs carry E00-E11 identities; the legacy account id is
kept only as a compatibility reference.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd

from .definitions import ROOT
from .factor_runtime import FactorBatch

VARIANTS = {"E00", "E01", "E10", "E11"}
FEES = (0.001, 0.002)
METHOD = "no_exit_100"

_FROZEN_PROTOCOL = (
    ROOT / "docs/experiments/raw/research-mixed-defense-2026-09-09/protocol.json"
)
FROZEN_SYMBOLS = tuple(
    json.loads(_FROZEN_PROTOCOL.read_text(encoding="utf-8"))["symbols"]
)

_MODULE_CACHE: dict = {}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_frozen_defense(registry: dict):
    """Import the frozen defense run.py after hash verification (cached)."""
    src = registry["sources"]["defense_code"]
    path = ROOT / src["path"]
    digest = _sha(path)
    if digest != src["sha256"]:
        raise ValueError(f"frozen defense code drifted: {src['path']}")
    if path in _MODULE_CACHE:
        return _MODULE_CACHE[path]
    spec = importlib.util.spec_from_file_location("_factor_v0_frozen_defense", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _MODULE_CACHE[path] = module
    return module


def _normalize_prices(prices: pd.DataFrame, module) -> pd.DataFrame:
    p = prices.copy()
    p.symbol = p.symbol.str.split(".").str[0].str.zfill(6)
    if set(p.symbol) != set(module.FULL):
        raise ValueError("replay input symbols must be the frozen full14 pool")
    if p.duplicated(["date", "symbol"]).any():
        raise ValueError("duplicate date/symbol rows")
    for c in ["open", "high", "low", "close", "volume"]:
        p[c] = pd.to_numeric(p[c], errors="coerce")
    return p.sort_values(["date", "symbol"])


def _to_engine_decisions(decisions: pd.DataFrame, symbols, variant: str) -> list[dict]:
    """Convert monthly_decisions output to the frozen decisions-row schema."""
    rows = []
    for r in decisions.itertuples(index=False):
        selected = r.selected.split("|") if r.selected else []
        if variant == "E11":
            # exact legacy label keeps E11 signals byte-comparable
            trend = {s: "included_monthly_without_entry_sma_filter" for s in selected}
        else:
            trend = {s: f"{variant}_monthly_selection" for s in selected}
        rows.append(
            dict(
                config="momentum_top3",
                decision_date=r.decision_date,
                selected=r.selected,
                ranked=r.ranked,
                lookback_start="shift252",
                lookback_end="shift21",
                scores=r.scores,
                weights=r.weights,
                trend_states=json.dumps(trend, ensure_ascii=False),
                exclusion_reasons=r.exclusion_reasons,
            )
        )
    return rows


def _batch_index(batch: FactorBatch) -> pd.DataFrame:
    cols = ["date", "symbol", "economic_index", "sma200", "momentum", "rv_rank", "valid_count"]
    return batch.values[cols].copy()


def _rename_account(rows, old, new):
    out = []
    for r in rows:
        rr = dict(r)
        rr["account_id"] = new
        out.append(rr)
    return out


def replay_account(
    *,
    registry: dict,
    batch: FactorBatch,
    decisions: pd.DataFrame,
    prices: pd.DataFrame,
    actions: list[dict],
    fee: float,
    variant: str,
) -> dict:
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant: {variant}")
    if fee not in FEES:
        raise ValueError(f"fee must be one of {FEES}, got {fee}")

    watched = {
        k: registry["sources"][k]["sha256"]
        for k in ("defense_code", "defense_protocol", "mixed_prices", "mixed_actions")
    }
    module = load_frozen_defense(registry)

    p = _normalize_prices(prices, module)
    acts = [module.action_fields(a) for a in actions]
    idx = _batch_index(batch)
    decs = _to_engine_decisions(decisions, module.FULL, variant)

    summary, daily, trades, orders, signals, events, annual, attrib, reentry, periods, diag = (
        module.simulate(METHOD, fee, p, acts, idx, decs)
    )

    # Post-run integrity: frozen sources must not have changed during the call.
    for key, digest in watched.items():
        actual = _sha(ROOT / registry["sources"][key]["path"])
        if actual != digest:
            raise ValueError(f"frozen source changed during replay: {key}")

    new_id = f"{variant}-fee{fee:.3f}"
    old_id = summary["account_id"]
    summary = dict(summary)
    summary["account_id"] = new_id
    summary["legacy_account_id"] = old_id
    summary["variant"] = variant
    summary["method"] = METHOD
    summary["policy_identity"] = f"factor_library_v0.{variant}@1.0.0-proposal"

    def rename(rows):
        return _rename_account(rows, old_id, new_id)

    return {
        "summary": summary,
        "equity": pd.DataFrame(rename(daily)),
        "trades": pd.DataFrame(rename(trades)),
        "orders": pd.DataFrame(rename(orders)),
        "signals": pd.DataFrame(rename(signals)),
        "actions": pd.DataFrame(rename(events)),
        "annual": pd.DataFrame(rename(annual)),
        "per_symbol_legacy": pd.DataFrame(rename(attrib)),
        "reentry_events": pd.DataFrame(rename(reentry)),
        "periods": pd.DataFrame(rename(periods)),
        "reentry_diagnostics": pd.DataFrame(rename(diag)),
    }


def source_hashes_now(registry: dict, keys) -> dict:
    """Helper for callers that must record current frozen-source fingerprints."""
    return {
        k: {
            "path": registry["sources"][k]["path"],
            "sha256": _sha(ROOT / registry["sources"][k]["path"]),
        }
        for k in keys
    }
