"""Read-only synthetic probes against exact pinned LEI source bytes.

The binder probe isolates the real bound_reference AFTER resolution. Its real
resolver is separately attempted and reported; missing lifecycle evidence is
never removed or fabricated. No full registry admission claim is made.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date, timedelta
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types
from unittest.mock import patch

import validator as candidate

sys.dont_write_bytecode = True
EXTERNAL_COMMIT = "1ac596f65110e06c286f04707165251328df0962"
TECHNICAL_COMMIT = "d444316817e9330c2d72a4a90c655467b45dd5bb"
EXTERNAL_PINS = {
    "src/lei_signal/research/workflow_inputs.py": "12a97a54b6af579bb42f44f7c8dc4179cd14d24d92ed7b9f047e6d05f7e75f14",
    "src/lei_signal/research/factor_runtime.py": "1f596f29aff27973ea55b55c49efd3c4c6fb1fdd200946a8618c272dad822579",
    "src/lei_signal/research/definitions.py": "84f7b9ba76f4704e81f4f4d0c1784e2ab1ad7e3aa225abeb4796fa10dcbfec94",
    "src/lei_signal/research/key_fluctuation_information.py": "f0c9f769ab608182813eb018ce97d5913cc3e6ff69841811b8757e5626ec1d9d",
    "src/lei_signal/research/top_structure_information.py": "5ce72eb21cc0d56208befd3e2dbb124792abbd3432288a8bf42c4fd42c341ad9",
    "docs/research/definitions.v1.json": "a2219a2d47f2d26b40dc1f57ff2914cefa4a24dce1b006d3b264a42ece0b9f43",
}
TECHNICAL_PINS = {
    "src/lei_signal/research/workflow_inputs.py": "0ff1fe0a3de19680cc9c8800fb62267993cc9f55dab36fbe28a2dd7153ca4691",
    "src/lei_signal/research/factor_runtime.py": EXTERNAL_PINS["src/lei_signal/research/factor_runtime.py"],
    "src/lei_signal/research/key_fluctuation_information.py": EXTERNAL_PINS["src/lei_signal/research/key_fluctuation_information.py"],
}


def snapshot(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


def check_pins(root, pins):
    for relative, expected in pins.items():
        actual = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"source hash mismatch: {relative}: {actual}")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def external_modules(root):
    # Isolated package namespace; no checkout __init__ or unrelated code runs.
    namespace = "_lei_boundary_external"
    for name, directory in ((namespace, root / "src/lei_signal"),
                            (namespace + ".research", root / "src/lei_signal/research")):
        module = types.ModuleType(name)
        module.__path__ = [str(directory)]
        sys.modules[name] = module
    folder = root / "src/lei_signal/research"
    return {name: load_module(f"{namespace}.research.{name}", folder / f"{name}.py")
            for name in ("definitions", "workflow_inputs", "top_structure_information",
                         "key_fluctuation_information", "factor_runtime")}


def synthetic_panel(size=3):
    end = date(2026, 10, 3)
    calendar = [(end - timedelta(days=size - i - 1)).isoformat() for i in range(size)]
    bars = []
    for i, day in enumerate(calendar):
        price = 100.0 + i
        bars.append({"asset": "synthetic-A", "date": day, "status": "quoted",
                     "open": price, "high": price + 1, "low": price - 1, "close": price,
                     "action_known": True, "decision_at": day + "T16:00:00+08:00",
                     "feature_available_at": day + "T15:00:00+08:00"})
    return {"data_mode": "synthetic", "calendar": calendar, "bars": bars}


def basic_contract():
    return {"universe": {"assets": ["synthetic-A"]},
            "feature": {"kind": "sma_distance", "lookback": 2, "warmup": 3, "missing_policy": "segmented"},
            "target": {"kind": "mae", "start_offset": 1, "end_offset": 2,
                       "entry_field": "close", "path_field": "close", "unit": "percentage_point"},
            "question": {"sampling": "daily"}}


def observe(function, payload, contract):
    try:
        result = function(payload, contract)
        final = result["observations"][-1]
        return {"accepted": True, "final_id": final["id"],
                "final_added_feature": final["features"]["added"]}
    except ValueError as exc:
        return {"accepted": False, "error": str(exc)}


def temporal_probe(function, payload, contract):
    local = deepcopy(payload)
    local["bars"][-1]["decision_at"] = "2026-10-03T15:30:00+08:00"
    utc = deepcopy(local)
    utc["bars"][-1]["decision_at"] = "2026-10-03T07:30:00Z"
    early = deepcopy(local)
    early["bars"][-1]["decision_at"] = "2026-10-03T14:30:00+08:00"
    global_cutoff = deepcopy(payload)
    global_cutoff["decision_at"] = "2026-10-03T10:00:00+08:00"
    results = {"local_1530": observe(function, local, contract),
               "same_instant_utc_0730": observe(function, utc, contract),
               "local_before_close_negative_control": observe(function, early, contract),
               "global_1000_cutoff": observe(function, global_cutoff, contract)}
    assert results["local_1530"]["accepted"]
    assert not results["same_instant_utc_0730"]["accepted"]
    assert not results["local_before_close_negative_control"]["accepted"]
    assert results["global_1000_cutoff"]["final_added_feature"] is not None
    results["expected_problem_reproduced"] = True
    results["note"] = "Computed final feature is the cutoff check; label eligibility is a separate question."
    return results


def formula_probe(modules, registry):
    definitions, runtime = modules["definitions"], modules["factor_runtime"]
    reference = "mixed.rv20@1.0.0"
    obj = next(o for o in registry["objects"] if o["id"] + "@" + o["version"] == reference)
    card = definitions._expand(registry, obj)
    lock = candidate.reviewed_binding()
    assert {k: card[k] for k in lock["contract"]} == lock["contract"]
    for dep, expected in lock["dependency_contracts"].items():
        raw = next(o for o in registry["objects"] if o["id"] + "@" + o["version"] == dep)
        expanded = definitions._expand(registry, raw)
        assert {k: expanded[k] for k in expected} == expected
    altered = deepcopy(card)
    altered["definition"]["formula"] = "2*(" + card["definition"]["formula"] + ")"
    normal_passed, doubled_passed = False, False
    # Explicit unit seam: exact real binder, supplied exact expanded card.
    # This does NOT exercise/relax the complete resolver's evidence checks.
    with patch.object(runtime, "resolve", return_value=card):
        normal_passed = runtime.bound_reference(reference, registry=registry) == card
    with patch.object(runtime, "resolve", return_value=altered):
        doubled_passed = runtime.bound_reference(reference, registry=registry) == altered
    try:
        definitions.resolve(registry, reference)
        full_admission = {"status": "pass", "scope": "structural_registry_load_only"}
    except (ValueError, ImportError) as exc:
        full_admission = {"status": "blocked", "reason": str(exc)}

    prices = [100.0]
    for ret in [0.01, -0.02, 0.04, -0.01] * 5:
        prices.append(prices[-1] * (1 + ret))
    series = definitions.pd.Series(prices)
    actual_series = definitions.realized_volatility(series)
    oracle_series = candidate.rv20_reference(prices)
    for actual_value, expected in zip(actual_series, oracle_series):
        assert definitions.pd.isna(actual_value) if expected is None else abs(actual_value - expected) < 1e-12
    actual, oracle = float(actual_series.iloc[-1]), oracle_series[-1]
    assert abs(actual - oracle) < 1e-12
    assert normal_passed and doubled_passed and abs(actual - 2 * oracle) > 1e-3
    c = {k: deepcopy(lock[k]) for k in ("reference", "contract", "dependency_contracts", "semantics")}
    c["contract"]["definition"]["formula"] = altered["definition"]["formula"]
    blocked = candidate.validate_formula(c)
    assert blocked["status"] == "blocked"
    return {"scope": "real_bound_reference_after_resolution; resolver substituted only at named unit seam",
            "normal_card_accepted": normal_passed, "same_id_version_doubled_formula_accepted": doubled_passed,
            "actual_source_rv20": actual, "independent_normal_expected": oracle,
            "doubled_formula_expected": 2 * oracle, "candidate": blocked,
            "full_original_registry_admission": full_admission,
            "expected_problem_reproduced": True}


def run(external_root, technical_root):
    check_pins(external_root, EXTERNAL_PINS)
    check_pins(technical_root, TECHNICAL_PINS)
    before = {"external": snapshot(external_root), "technical": snapshot(technical_root)}
    modules = external_modules(external_root)
    technical_workflow = load_module("_lei_boundary_technical_workflow",
                                    technical_root / "src/lei_signal/research/workflow_inputs.py")
    payload, contract = synthetic_panel(), basic_contract()
    result = {"external_commit": EXTERNAL_COMMIT, "external_registry_version": "1.6.12",
              "technical_commit": TECHNICAL_COMMIT,
              "technical_registry_not_loaded": "1.6.0 is a distinct baseline, not mixed into external registry",
              "external_workflow": temporal_probe(modules["workflow_inputs"].prepare_observations, payload, contract),
              "technical_workflow": temporal_probe(technical_workflow.prepare_observations, payload, contract)}
    key_payload = synthetic_panel(252)
    key_contract = basic_contract()
    key_contract["feature"] = {"kind": "key_fluctuation_information",
                               "definition_ref": "research.key_fluctuation.dual_break20@1.0.0",
                               "lookback": 60, "warmup": 252, "missing_policy": "segmented"}
    key_contract["target"].update(end_offset=21, price_measure="economic_price")
    key_contract["question"]["period"] = [key_payload["calendar"][0], key_payload["calendar"][-1]]
    result["external_key_adapter"] = temporal_probe(modules["key_fluctuation_information"].prepare_key_observations,
                                                     key_payload, key_contract)
    registry = json.loads((external_root / "docs/research/definitions.v1.json").read_text())
    result["formula"] = formula_probe(modules, registry)
    after = {"external": snapshot(external_root), "technical": snapshot(technical_root)}
    assert before == after, "protected source trees changed"
    result["source_integrity"] = {"unchanged": True, "before": before, "after": after}
    result["dependencies"] = {"python": sys.version.split()[0],
                              "numpy": modules["definitions"].np.__version__,
                              "pandas": modules["definitions"].pd.__version__, "new_installs": 0}
    result["scope"] = "Synthetic function probes only; no source writes, market experiments, production integration or result invalidation."
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-root", type=Path, required=True)
    parser.add_argument("--technical-root", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.external_root.resolve(), args.technical_root.resolve()),
                     ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
