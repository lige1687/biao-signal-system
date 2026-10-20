"""Append only this study's card to its published branch's canonical registry."""
import hashlib
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from lei_signal.research.definitions import resolve, validate_registry

HERE = Path(__file__).resolve().parent
BASE = "cd2b634476bad2a2cc67a605aeaee860b9ce2b28"
REF = "research.rebalancing.calendar_drift_60_40"


def main():
    original = subprocess.check_output(
        ["git", "show", BASE + ":docs/research/definitions.v1.json"], cwd=ROOT)
    registry = json.loads(original)
    validate_registry(registry)
    previous = deepcopy(registry)
    design = HERE / "design.json"
    source = "month_end_rebalancing_design_20261020"
    registry["sources"][source] = {
        "path": str(design.relative_to(ROOT)),
        "sha256": hashlib.sha256(design.read_bytes()).hexdigest(),
    }
    registry["objects"].append({
        "id": REF, "version": "1.0.0",
        "name": "月内60比40股债配置偏离（外部机制研究）", "type": "feature",
        "uses": ["description", "comparison"],
        "not_for": ["production_trade", "causal_claim", "complete_lei_strategy",
                    "independent_raw_information"],
        "scope": "美国SPY/IEF当前取得历史总回报、月末事件；非ES/TY期货复现",
        "definition": {
            "formula": "w*Gs/(w*Gs+(1-w)*Gb)-w", "parameters": {"w": 0.6},
            "endpoints": "previous month last close to sixth-last close",
            "unit": "fraction of portfolio equity weight",
            "direction": "positive hypothesizes stock selling and bond buying",
            "transforms": "cash-dividend economic index; no fitting in signal",
        },
        "input": {
            "fields": ["date", "SPY_close", "IEF_close", "SPY_dividend", "IEF_dividend"],
            "price_basis": "raw close plus ex-date dividend reinvestment; payment lag ignored",
            "currency": "USD", "frequency": "daily inputs, monthly observations",
            "calendar": "matching observed US quote dates; next month required; no fill",
        },
        "universe": {
            "version": "SPY-IEF-fixed-20261020",
            "eligibility": "both valid quotes, complete shared observed month; prespecified pair",
            "warmup": "previous month endpoint; predictions require 60 mature months",
            "missing": "reject asymmetric dates/nonfinite/nonpositive prices",
            "quality_gate": "source hashes, OHLC checks, cash-action events, common dates",
            "degrade": "limited retrospective, not tradability certification",
        },
        "time": {
            "observation_time": "sixth-last trading-day close",
            "available_at": "historical arrival unknown; retrieved 2026-10-20",
            "decision_at": "after signal close, hypothetical diagnosis",
            "execution_at": "next open observation only; not an order",
            "timezone": "America/New_York", "effective_from": "2026-10-20 research",
        },
        "dependencies": [],
        "validation": {
            "method": "synthetic arithmetic/dividends/calendar/prefix; independent numbers",
            "tolerance": {"absolute": 1e-10, "relative": 1e-10, "integer": 0},
            "tests": ["tests/unit/test_month_end_rebalancing.py"],
            "limitations": "no institutional flow identification, full account or forward proof",
        },
        "status": {
            "definition_clarity": "explicit", "data_qualification": "limited_vendor_snapshot",
            "implementation": "synthetic_checked", "effectiveness": "not_yet_evaluated",
            "production": "not_authorized",
        },
        "sources": [source],
        "lifecycle": {
            "state": "exists", "basis": [str(design.relative_to(ROOT))],
            "verification_scope": "study definition; effectiveness assessed separately",
        },
        "research_owner": "mechanism-rebalancing-review-20261020",
    })
    card = resolve(registry, REF + "@1.0.0")
    recovered = deepcopy(registry)
    recovered["objects"].pop()
    del recovered["sources"][source]
    assert recovered == previous
    snapshot = HERE / "definitions-registry.snapshot.json"
    assert not snapshot.exists()
    snapshot.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n")
    try:
        validate_registry(json.loads((ROOT / "docs/research/definitions.v1.json").read_text()))
        shared_error = None
    except ValueError as exc:
        shared_error = str(exc)
    receipt = {
        "reference": REF + "@1.0.0", "resolved_card": card,
        "base_commit": BASE,
        "canonical_path_on_work_branch": "docs/research/definitions.v1.json",
        "snapshot_path": str(snapshot.relative_to(ROOT)),
        "snapshot_sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
        "base_registry_sha256": hashlib.sha256(original).hexdigest(),
        "existing_branch_cards_unchanged": True,
        "shared_registry_modified": False, "shared_registry_error": shared_error,
        "reason": "Shared registry has unrelated invalid French source metadata. Preserve its bytes; use valid canonical registry on our own branch, append only our card. No validator bypass.",
    }
    (HERE / "definition-binding.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in receipt.items() if k != "resolved_card"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
