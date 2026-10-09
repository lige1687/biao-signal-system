"""C-F01 targeted engineering check; no historical ratios/account paths."""
from __future__ import annotations

import json
from pathlib import Path

from execution_guard import now, sha256
from input_adapter import load_bound_dataset, validate_open_references

HERE = Path(__file__).resolve().parent
DAY = "2026-01-05"


def case(name, opening="10", lower="9", upper="11", reason="ordinary_reference",
         restriction=None, refused=False, expected=None):
    # These other prices deliberately cannot rescue an invalid opening price.
    quote = {"date": DAY, "open": opening, "high": "10.5", "low": "9.5", "close": "10"}
    reference = {"date": DAY, "lower_limit": lower, "upper_limit": upper,
                 "reason": reason, "restriction": restriction}
    account_path_calls = 0
    try:
        restrictions, rows = validate_open_references([quote], [reference])
        # A sentinel counts reaching the downstream account boundary; no
        # account simulator is invoked in this targeted check.
        account_path_calls += 1
        assert not refused, "expected rejection did not occur"
        assert restrictions.get(DAY) == expected
        return {"name": name, "passed": True, "input": {"quote": quote, "reference": reference},
                "downstream_boundary_reached": account_path_calls, "opening_validation": rows}
    except ValueError as exc:
        assert refused, str(exc)
        assert account_path_calls == 0
        return {"name": name, "passed": True, "input": {"quote": quote, "reference": reference},
                "downstream_boundary_reached": account_path_calls, "rejection": str(exc)}


def main():
    output = HERE/"targeted-opening-reference-evidence.json"
    receipt_path = HERE/"opening-source-consumption-receipt.json"
    assert not output.exists() and not receipt_path.exists(), "do not overwrite prior check"
    cases = [case("inside_original_bounds"),
             case("lower_touch_preserves_block", "9", reason="touch_limit", restriction="blocked", expected="blocked"),
             case("upper_touch_preserves_block", "11", reason="touch_limit", restriction="blocked", expected="blocked"),
             case("above_upper_rejected_before_path", "12", refused=True),
             case("below_lower_rejected_before_path", "8", refused=True),
             case("missing_lower_rejected", lower=None, refused=True),
             case("nonfinite_upper_rejected", upper="NaN", refused=True),
             case("equal_bounds_rejected", lower="10", upper="10", refused=True),
             case("reversed_bounds_rejected", lower="11", upper="9", refused=True),
             case("nonpositive_bound_rejected", lower="0", refused=True),
             case("touch_missing_source_block_rejected", "9", refused=True),
             case("original_abnormal_flag_rejected", reason="abnormal_outside_limit", refused=True),
             case("ex_reference_unknown_original_block", "12", None, None, "reference_unknown", "blocked", expected="blocked"),
             case("halt_original_halt", "12", None, None, "known_halt", "halt", expected="halt"),
             case("unblocked_special_rejected", reason="reference_unknown", refused=True),
             case("missing_open_remains_wait", opening=None)]
    evidence = {"dataset": "ARTIFICIAL_ONLY", "scope": "C-F01 original opening-reference guard",
                "generated_at": now(), "checks": cases, "passed": len(cases), "failed": [],
                "historical_account_path_calls": 0, "account_simulator_calls": 0,
                "core_full_groups_rerun": 0, "C_acceptance": False,
                "check_code_sha256": sha256(Path(__file__)),
                "adapter_sha256": sha256(HERE/"input_adapter.py")}
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2)+"\n")
    # Exact A data consumption checks the new adapter compatibility only;
    # neither monthly_targets nor any account simulator is called.
    binding = json.loads((HERE/"consumption-binding.json").read_text())
    data = load_bound_dataset(binding)
    rows = data["opening_validation"]
    receipt = {"scope": "B exact A input consumption through repaired opening guard",
               "generated_at": now(), "A_manifest_sha256": binding["A_manifest"]["sha256"],
               "A_result_commit": binding["A_result_commit"], "original_files_hash_checked": len(binding["source_closure"]),
               "checked_openings": len(rows), "validation": rows, "restrictions": data["restrictions"],
               "source_execution_reference": binding["files"]["execution_reference"],
               "source_quotes": binding["files"]["quotes"], "adapter_sha256": sha256(HERE/"input_adapter.py"),
               "historical_ratios_computed": 0, "historical_account_path_calls": 0, "A_qualification_replaced": False,
               "C_acceptance": False}
    assert len(rows) == 116 and data["restrictions"] == {"2026-01-19": "blocked"}
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps({"artificial_checks_passed": len(cases), "A_openings_consumed": len(rows),
                      "special_blocks_preserved": len(data["restrictions"]), "historical_path_calls": 0}))


if __name__ == "__main__":
    main()
