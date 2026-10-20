"""Point-in-time adapter from the eleventh A/C/D events to cash candidates.

This is isolated research glue.  It neither regenerates signals nor runs accounts.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import gzip
import hashlib
import json
import shutil
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
TWELFTH = HERE.parent
RAW_ROOT = TWELFTH.parent
ELEVENTH = RAW_ROOT / "research-eleventh-2026-09-08"
EIGHTH = RAW_ROOT / "research-eighth-2026-09-08"
PACKAGE = ELEVENTH / "research-package"
PRICE_HELPER = EIGHTH / "product-qualification" / "price-helper"
sys.path.insert(0, str(PACKAGE / "src"))
sys.path.insert(0, str(PRICE_HELPER))

import numpy as np
import pandas as pd

from price_basis import PriceBasis
from lei_signal.features.indicators import compute_features
from lei_signal.features.pivots import confirmed_pivots
from lei_signal.rules.reward_risk_filter import _target_b
from lei_signal.rules.resistance_b1 import find_b1
from lei_signal.domain.rules_config import get_rule, load_ruleset

SYMBOLS = ["sh510300", "sh513100", "sh518880", "sz159915"]
FIELDS = ["open", "high", "low", "close", "volume"]
RAW_EVENTS = ELEVENTH / "history-diagnostic" / "raw-events.json.gz"
OLD_CANDIDATES = EIGHTH / "candidate-study" / "candidates.json.gz"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plain(value):
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, np.integer):
        return int(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(plain(value), ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def source_files() -> list[Path]:
    files = [
        Path(__file__), TWELFTH / "protocol.md", TWELFTH / "configurations.json",
        RAW_EVENTS, OLD_CANDIDATES, EIGHTH / "generate_candidates.py",
        EIGHTH / "product-qualification" / "actions.json", PRICE_HELPER / "price_basis.py",
    ]
    files += sorted((EIGHTH / "product-qualification" / "bars-helper-native").glob("*.csv"))
    files += sorted(p for p in PACKAGE.rglob("*") if p.is_file())
    return sorted(set(p.resolve() for p in files))


def load_inputs():
    bars = {}
    base = EIGHTH / "product-qualification" / "bars-helper-native"
    for symbol in SYMBOLS:
        frame = pd.read_csv(base / f"{symbol}-nominal.csv", dtype={"date": str})
        assert frame.date.is_unique and frame.date.is_monotonic_increasing
        bars[symbol] = frame.to_dict("records")
    actions = json.loads((EIGHTH / "product-qualification" / "actions.json").read_text())
    return bars, actions


def raw_asof(symbol: str, bars: dict, actions: list, day: str) -> pd.DataFrame:
    observed = {symbol: [r for r in bars[symbol] if r["date"] <= day]}
    known = [a for a in actions if a["symbol"] == symbol and a["announcement_date"] <= day]
    basis = PriceBasis(observed, known)
    rows = []
    for row in observed[symbol]:
        converted = basis.bar(symbol, row, day, "cash_proportional_v1")
        rows.append({"date": row["date"], **{f: float(converted[f]) for f in FIELDS}})
    frame = pd.DataFrame(rows).set_index("date")
    frame.index = pd.to_datetime(frame.index)
    return frame


def target_for(frame: pd.DataFrame, pivots, pos: int):
    close = float(frame.close.iloc[pos])
    day = frame.index[pos].date()
    lookback = int(get_rule("reward_risk_filter").param("range_lookback", 60))
    target, source = _target_b(frame, position=pos, entry_price=close, pivots=pivots,
                               as_of=day, range_lookback=lookback, gaps=None)
    confirmed_at = source_date = None
    if source == "swing_high":
        b1 = find_b1(pivots, as_of=day, current_close=close)
        assert b1 is not None and b1.available_date <= day
        assert float(b1.price) == float(target)
        confirmed_at, source_date = b1.available_date.isoformat(), b1.pivot_date.isoformat()
    elif source is not None:
        confirmed_at = source_date = day.isoformat()
    return target, source, confirmed_at, source_date


def qualify(ref, stop, target):
    if stop is None or not np.isfinite(stop) or stop >= ref or stop <= 0:
        return None, False, "invalid_structure_risk"
    if target is None or not np.isfinite(target) or target <= ref:
        return None, False, "target_unavailable"
    rr = (target - ref) / (ref - stop)
    return rr, rr >= 3, None if rr >= 3 else "signal_reward_risk_below_3"


def config_for(record: dict) -> str | None:
    event = record["event"]
    evidence = event["evidence"]
    if record["module"] == "A" and evidence.get("sub_rule") == "first_ma_pullback_confirmed":
        suffix = "E" if evidence.get("entry_variant") == "early" else "J"
        return f"A{int(evidence['ma_period'])}{suffix}"
    if record["module"] == "C" and evidence.get("sub_rule", "").endswith("_confirmed"):
        version = str(evidence["version"]).lower()
        assert version in {"v1", "v2", "v3"}
        return "C" + version[1:]
    if record["module"] == "D" and evidence.get("sub_rule") == "module_d_long_confirmed":
        return "D"
    return None


def adapt_event(record: dict, frame: pd.DataFrame) -> dict:
    event = record["event"]
    evidence = event["evidence"]
    config_id = config_for(record)
    assert config_id is not None
    day, symbol = event["available_date"], event["symbol"]
    features = compute_features(frame)
    ts = pd.Timestamp(day)
    assert ts == features.index[-1], (symbol, day, features.index[-1])
    ref = float(features.loc[ts, "close"])
    assert np.isclose(ref, float(evidence["close"]), rtol=0, atol=1e-12), (event["event_id"], ref, evidence["close"])
    stop = evidence.get("stop_price")
    target, source, confirmed_at, source_date = target_for(features, confirmed_pivots(features), len(features) - 1)
    rr, accepted, reason = qualify(ref, stop, target)
    source_id = event["event_id"]
    metadata = {
        "source_event": event,
        "source_event_id": source_id,
        "source_module": record["module"],
        "lifecycle_id": event.get("lifecycle_id"),
        "touch_date": evidence.get("touch_date"),
        "a3_structure_id": evidence.get("a3_structure_id"),
        "original_stop": stop,
        "basis_epoch_start": record["basis_epoch_start"],
        "basis_epoch_end": record["basis_epoch_end"],
        "source_event_record": record,
    }
    return plain({
        "config_id": config_id, "candidate_id": f"{config_id}:{source_id}",
        "source_candidate_id": source_id, "source_config_id": config_id,
        "symbol": symbol, "signal_date": day, "known_at": day + "T15:00:00+08:00",
        "opportunity_key": f"{symbol}:{day}:{source_id}", "kind": source_id,
        "structure_id": event.get("lifecycle_id"), "lifecycle_id": event.get("lifecycle_id"),
        "touch_date": evidence.get("touch_date"), "a3_structure_id": evidence.get("a3_structure_id"),
        "variant": record["module"], "signal_ref": ref, "stop": stop, "target": target,
        "upper": None, "signal_rr": rr, "signal_accepted": bool(accepted),
        "signal_reject_reason": reason, "target_source": source,
        "target_confirmed_at": confirmed_at, "target_source_date": source_date,
        "basis_as_of": day, "metadata": metadata, "source_event": event,
        "source_event_record": record,
        "rule_version": event.get("rule_version"),
        "discipline_scope": "signal-day known stop/target and reward/risk; not all nine disciplines",
    })


def copy_references(old: list[dict]) -> list[dict]:
    mapping = {"P0": "REF_BREAKOUT", "P5": "REF_ROAD"}
    out = []
    for source in old:
        if source.get("config_id") not in mapping:
            continue
        row = dict(source)
        original_id, original_config = row["candidate_id"], row["config_id"]
        row["config_id"] = mapping[original_config]
        row["candidate_id"] = f"{row['config_id']}:{original_id}"
        row["source_candidate_id"] = original_id
        row["source_config_id"] = original_config
        row["metadata"] = {"source_candidate": source, "source_candidate_id": original_id,
                           "source_config_id": original_config}
        out.append(row)
    return out


def generate(events: list[dict], old_candidates: list[dict], bars: dict, actions: list):
    confirmed = [record for record in events if config_for(record) is not None]
    assert len(confirmed) == 891
    adapted = []
    prefix_checks = 0
    epoch_cache = {}
    for index, record in enumerate(confirmed, 1):
        event = record["event"]
        symbol, day = event["symbol"], event["available_date"]
        epoch_key = (symbol, record["basis_epoch_end"])
        if epoch_key not in epoch_cache:
            epoch_cache[epoch_key] = raw_asof(symbol, bars, actions, record["basis_epoch_end"])
        exact = raw_asof(symbol, bars, actions, day)
        pd.testing.assert_frame_equal(epoch_cache[epoch_key].loc[:day], exact, check_exact=True)
        prefix_checks += 1
        adapted.append(adapt_event(record, exact))
        if index % 100 == 0:
            print(f"adapted {index}/{len(confirmed)}", flush=True)
    references = copy_references(old_candidates)
    all_candidates = adapted + references
    all_candidates.sort(key=lambda x: (x["signal_date"], x["symbol"], x["candidate_id"]))
    assert len({c["candidate_id"] for c in all_candidates}) == len(all_candidates)
    assert Counter(c["source_candidate_id"] for c in adapted) == Counter(r["event"]["event_id"] for r in confirmed)
    return all_candidates, adapted, references, prefix_checks


def main() -> None:
    HERE.mkdir(exist_ok=True)
    locked = source_files()
    hashes = {str(path): sha256(path) for path in locked}
    lock = {"started_at_utc": datetime.now(timezone.utc).isoformat(), "files": hashes,
            "ruleset_version": load_ruleset()["ruleset_version"],
            "scope": "A/C/D confirmed-event candidate adaptation plus frozen P0/P5 references; no returns"}
    write_json(HERE / "run-lock.json", lock)
    with gzip.open(RAW_EVENTS, "rt") as handle:
        events = json.load(handle)
    with gzip.open(OLD_CANDIDATES, "rt") as handle:
        old_candidates = json.load(handle)
    bars, actions = load_inputs()
    candidates, adapted, references, prefix_checks = generate(events, old_candidates, bars, actions)
    with gzip.open(HERE / "candidates.json.gz", "wt") as handle:
        json.dump(candidates, handle, ensure_ascii=False, allow_nan=False)
    shutil.copyfile(RAW_EVENTS, HERE / "all-source-events.json.gz")
    reject = Counter(c["signal_reject_reason"] or "accepted" for c in candidates)
    by_config = {}
    for config in sorted({c["config_id"] for c in candidates}):
        rows = [c for c in candidates if c["config_id"] == config]
        by_config[config] = {"rows": len(rows), "accepted": sum(c["signal_accepted"] for c in rows),
                             "rejections": dict(sorted(Counter(c["signal_reject_reason"] or "accepted" for c in rows).items()))}
    write_json(HERE / "summary.json", {
        "status": "completed", "source_event_records": len(events), "confirmed_source_events": len(adapted),
        "reference_candidates": len(references), "candidate_rows": len(candidates),
        "unique_candidate_ids": len({c["candidate_id"] for c in candidates}),
        "unique_confirmed_source_ids": len({c["source_candidate_id"] for c in adapted}),
        "source_mapping_exactly_once": len(adapted) == len({c["source_candidate_id"] for c in adapted}) == 891,
        "prefix_price_checks": prefix_checks, "all_source_events_sha256": sha256(RAW_EVENTS),
        "copied_all_source_events_sha256": sha256(HERE / "all-source-events.json.gz"),
        "rejections": dict(sorted(reject.items())), "by_config": by_config,
    })
    unchanged = all(sha256(Path(path)) == digest for path, digest in hashes.items())
    assert unchanged, "source changed during adaptation"
    write_json(HERE / "completion.json", {"finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_hashes": hashes, "input_hashes_unchanged": True, "candidate_sha256": sha256(HERE / "candidates.json.gz"),
        "all_source_events_sha256": sha256(HERE / "all-source-events.json.gz"), "return_simulation_run": False})
    print("candidate adaptation complete", flush=True)


if __name__ == "__main__":
    main()
