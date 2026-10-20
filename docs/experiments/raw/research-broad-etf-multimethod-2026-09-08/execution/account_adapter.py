"""Generic target-signal adapter over the locked first12 cash ledger. No signal invention."""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
FIRST12 = ROOT / "docs/experiments/raw/research-broad-etf-cash-2026-09-08/first12"


def load_json(path):
    return json.loads(Path(path).read_text())


def load_first12_runner():
    path = FIRST12 / "run_accounts.py"
    spec = importlib.util.spec_from_file_location("locked_first12_cash_runner", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def calendar_week_end(day):
    value = date.fromisoformat(day)
    return value + timedelta(days=6-value.weekday())


def qualify_weekly_records(records, research_end):
    """Type terminal partial weeks before any account sees them."""
    end = date.fromisoformat(research_end)
    result = []
    for record in records:
        item = dict(record)
        if calendar_week_end(item["signal_date"]) > end:
            item.update(status="unconfirmed_partial_week", candidate_only=True,
                        eligible_date_is_hypothetical=True, executable_in_window=False)
        else:
            item.update(status="confirmed_completed_week", candidate_only=False,
                        eligible_date_is_hypothetical=False,
                        executable_in_window=item.get("eligible_date", research_end) <= research_end)
        result.append(item)
    return result


def classify_restriction(row):
    """Keep legal suspension separate from delayed open and research conservatism."""
    reason = row.get("reason", "")
    if reason == "official suspension":
        return "official_suspension"
    if "resumes at" in reason and not row.get("open_buy_allowed", True):
        return "delayed_open_no_open_fill"
    if row.get("status", "").startswith("research restriction"):
        return "research_conservative_restriction"
    return "other_dated_restriction"


def validate_candidate_bundle(bundle, gate):
    candidates = bundle.get("candidates", [])
    if not 1 <= len(candidates) <= gate["candidate_count_max"]:
        raise ValueError("candidate count must be between 1 and frozen maximum")
    ids = [c["candidate_id"] for c in candidates]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate candidate_id")
    symbols = set(gate["symbols"])
    for candidate in candidates:
        if candidate.get("provenance") != "research_proxy":
            raise ValueError("candidate must be labelled research_proxy")
        if candidate.get("claims_paper_original") is not False:
            raise ValueError("candidate must explicitly deny paper-original status")
        if candidate.get("execution_policy") not in {"exact_target_transition", "weekly_5pp_target"}:
            raise ValueError("unknown execution policy")
        for signal in candidate.get("signals", []):
            if signal.get("symbol") not in symbols or signal.get("target") not in {"0", "0.5", "1"}:
                raise ValueError("invalid symbol or target")
            for field in ("signal_date", "eligible_date", "reason"):
                if not signal.get(field):
                    raise ValueError(f"missing signal field: {field}")
            if signal["eligible_date"] <= signal["signal_date"]:
                raise ValueError("close-known signal cannot execute on the same date")
            if signal.get("candidate_only") or signal.get("status") == "unconfirmed_partial_week":
                raise ValueError("unconfirmed candidate signal cannot enter cash account")
    return candidates


def load_frozen_inputs():
    runner = load_first12_runner()
    config = load_json(FIRST12 / "config.json")
    settings = load_json(FIRST12 / "inputs/execution-parameters-source.json")
    actions = load_json(FIRST12 / "inputs/actions.json")
    bars = {symbol: runner.read_bars(FIRST12 / "inputs/bars" / f"{symbol}-nominal.csv")
            for symbol in config["symbols"]}
    return runner, config, settings, actions, bars


def execute_candidate_account(candidate, symbol, fee, frozen):
    """Execute one locked candidate; caller owns file writing and run locks."""
    runner, config, settings, actions, bars = frozen
    policy = "breadth_three_tier" if candidate["execution_policy"] == "weekly_5pp_target" else "candidate_exact_target"
    signals = [s for s in candidate["signals"] if s["symbol"] == symbol]
    account_id = f"{symbol}-{candidate['candidate_id']}-fee{fee}"
    return runner.simulate(account_id, symbol, policy, runner.D(str(fee)), bars[symbol], actions,
                           settings, signals, *config["research_window"])

