"""Read-only declaration and registry checks; no market evaluation."""
import copy
import datetime
import hashlib
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from lei_signal.research.question_contract import validate_workflow_contract
from lei_signal.research.definitions import validate_registry


def outcome(contract):
    try:
        validate_workflow_contract(contract)
    except ValueError as error:
        return {"accepted": False, "reason": str(error)}
    return {"accepted": True}


fixture = runpy.run_path(str(ROOT / "tests/unit/test_workflow_design_review.py"))["valid_contract"]()
missing_design = copy.deepcopy(fixture)
del missing_design["research_design"]
uses_results = copy.deepcopy(fixture)
uses_results["research_design"]["sample_fit"]["outcome_values_used_for_design"] = True
account = copy.deepcopy(fixture)
account["question"]["layer"] = "decision_policy"
registry_path = ROOT / "docs/research/definitions.v1.json"
registry = json.loads(registry_path.read_text())
try:
    validate_registry(registry)
    registry_status = {"accepted": True}
except ValueError as error:
    registry_status = {"accepted": False, "reason": str(error)}
bad_sources = [
    {"source_id": key, "keys": list(value), "absolute_path": Path(value.get("path", "")).is_absolute()}
    for key, value in registry["sources"].items()
    if set(value) != {"path", "sha256"} or Path(value.get("path", "")).is_absolute()
]
result = {
    "as_of": datetime.datetime.now().astimezone().isoformat(),
    "mode": "report_only",
    "market_runs": 0,
    "declaration_checks": {
        "existing_1_1_without_dedicated_mechanism_fields": outcome(fixture),
        "claim_mapping_fields": list(fixture["research_design"]["claim_mapping"]),
        "missing_research_design": outcome(missing_design),
        "design_uses_outcome_values": outcome(uses_results),
        "account_policy_at_information_entry": outcome(account),
    },
    "current_registry": {
        **registry_status,
        "version": registry["version"],
        "object_count": len(registry["objects"]),
        "sha256": hashlib.sha256(registry_path.read_bytes()).hexdigest(),
        "source_mismatches": bad_sources,
    },
    "boundary": "Declaration checks only; no real preflight, freeze, evaluator, ledger write or strategy adoption.",
}
assert result["declaration_checks"]["existing_1_1_without_dedicated_mechanism_fields"]["accepted"]
assert all(not result["declaration_checks"][key]["accepted"] for key in [
    "missing_research_design", "design_uses_outcome_values", "account_policy_at_information_entry"
])
print(json.dumps(result, ensure_ascii=False, indent=2))
