#!/usr/bin/env python3
"""One source-corrective P2 follow-up on the frozen 600-stock, 132-month panel.

No market requests, financial backfill, parameter change, or modification of old
results. The output is a new create-only evidence directory on the bound disk.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import plistlib
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
SCHEMA = "p2-price-correction-run/1"
REQUIRED = {"old_core_contract", "old_core_manifest", "old_monthly",
            "old_stock_weights", "old_layers", "old_uncertainty", "p1_execution_contract",
            "p1_actual_input", "p1_manifest", "p1_per_stock",
            "old_core_runner", "risk_runner", "gradient_runner", "self",
            "old_risk_manifest", "old_gradient_manifest"}
CONSUMED = {"eligibility_reason", "momentum", "future_return", "outcome_reason",
            "either_halt"}


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1 << 20), b""):
            digest.update(part)
    return digest.hexdigest()


def bound(binding):
    path = Path(binding["path"])
    if not path.is_absolute() or not path.is_file() or sha(path) != binding["sha256"]:
        raise ValueError(f"missing or changed bound input: {path}")
    return path


def read_json(binding):
    return json.loads(bound(binding).read_text(encoding="utf-8"))


def module(binding, name):
    path = bound(binding)
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def csv_rows(path, required):
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames or []
        if len(columns) != len(set(columns)) or not required <= set(columns):
            raise ValueError("corrected price CSV lacks unique required columns")
        return list(reader), columns


def output_preflight(contract, out):
    spec = contract["output"]
    mount = Path(spec["mount"])
    internal = Path(spec["internal_root"])
    out = Path(out).resolve()
    if (str(out) != spec["path"] or out.exists() or not out.parent.is_dir() or
            not os.path.ismount(mount) or mount.stat().st_dev != spec["external_device"] or
            out.parent.stat().st_dev != spec["external_device"] or
            not internal.is_dir() or
            shutil.disk_usage(mount).free < spec["external_reserve_bytes"] + spec["estimated_bytes"] or
            shutil.disk_usage(internal).free < spec["internal_reserve_bytes"] + spec["internal_estimated_bytes"]):
        raise ValueError("create-only output/device/capacity preflight failed")
    info = plistlib.loads(subprocess.run(["/usr/sbin/diskutil", "info", "-plist", str(mount)],
                                    capture_output=True, check=True, timeout=10).stdout)
    if info.get("VolumeUUID") != spec["external_uuid"]:
        raise ValueError("external disk UUID differs")
    return out


def validate_old_lineage(inputs, core, bindings, ev):
    """Repeat the frozen evaluator's source checks before its _load_inputs."""
    expected = {"design", "amendment", "cohort", "prices", "panel", "parser", "runner",
                "panel_manifest", "panel_contract", "qualification_amendment"}
    if set(inputs) != expected:
        raise ValueError("old core input set changed")
    for binding in inputs.values():
        bound(binding)
    if (inputs["design"]["sha256"] != ev.DESIGN_SHA or
            inputs["amendment"]["sha256"] != ev.AMENDMENT_SHA or
            inputs["cohort"]["sha256"] != ev.COHORT_SHA or
            inputs["parser"]["sha256"] != ev.PARSER_SHA or
            inputs["runner"] != bindings["old_core_runner"]):
        raise ValueError("old method/parser/runner identity changed")
    panel_manifest = read_json(inputs["panel_manifest"])
    panel_contract = read_json(inputs["panel_contract"])
    qualification = read_json(inputs["qualification_amendment"])
    if (panel_manifest.get("schema") != "financial-panel-result/1" or
            panel_manifest.get("contract_sha256") != inputs["panel_contract"]["sha256"] or
            panel_manifest.get("outputs", {}).get("panel.csv") != inputs["panel"]["sha256"] or
            Path(inputs["panel"]["path"]).resolve() != Path(panel_contract["output"]["path"]).resolve() / "panel.csv" or
            panel_manifest.get("inputs") != panel_contract.get("inputs") or
            panel_contract["inputs"].get("parser") != inputs["parser"] or
            panel_contract["inputs"].get("design") != inputs["design"] or
            panel_contract["inputs"].get("cohort") != inputs["cohort"] or
            panel_contract["inputs"].get("qualification_amendment") != inputs["qualification_amendment"] or
            qualification.get("root_accepted") is not True or qualification.get("effect_runs_before") != 0 or
            qualification.get("new_rules_sha256") != panel_contract["inputs"]["version_rules"]["sha256"]):
        raise ValueError("old financial panel lineage differs")
    design, amendment = read_json(inputs["design"]), read_json(inputs["amendment"])
    if (amendment["base_design_sha256"] != ev.DESIGN_SHA or
            design["reuse"]["monthly_decisions"] != 132 or
            design["selection"]["fraction"] != 0.2 or
            design["stability"]["uncertainty"]["draws"] != 10000):
        raise ValueError("old financial design parameters changed")
    if core.get("units") != {"momentum": "simple_decimal_return", "future_return": "simple_decimal_return",
                              "gpa": "ratio", "cfoa": "ratio"}:
        raise ValueError("old panel/price units changed")


def validate_old_outputs(bindings, old_manifest, old_contract):
    if (old_manifest.get("schema") != "financial-evaluation-result/1" or
            old_manifest.get("contract_sha256") != bindings["old_core_contract"]["sha256"] or
            old_manifest.get("inputs") != old_contract["inputs"] or
            old_manifest.get("monthly_positions") != 132):
        raise ValueError("old core manifest lineage differs")
    for key, name in (("old_monthly", "monthly.json"),
                      ("old_stock_weights", "stock_weights.csv"),
                      ("old_layers", "qualification_layers.json"),
                      ("old_uncertainty", "uncertainty.json")):
        if (Path(bindings[key]["path"]).resolve() !=
                (Path(bindings["old_core_manifest"]["path"]).parent / name).resolve() or
                old_manifest["outputs"][name]["sha256"] != bindings[key]["sha256"]):
            raise ValueError(f"old core output differs: {name}")


def validate_p1(bindings, p1_contract, p1_manifest):
    if (p1_contract.get("status") != "approved_frozen" or
            p1_contract.get("bindings", {}).get("preflight") != bindings["p1_actual_input"] or
            p1_contract.get("bindings", {}).get("runner", {}).get("sha256") is None or
            p1_manifest.get("status") != "completed_pending_independent_review" or
            p1_manifest.get("contract_sha256") != bindings["p1_execution_contract"]["sha256"] or
            p1_manifest.get("derived_input_sha256") !=
            p1_contract.get("bindings", {}).get("derived_input", {}).get("sha256") or
            p1_manifest.get("outputs", {}).get("per_stock_month.csv", {}).get("sha256") != bindings["p1_per_stock"]["sha256"] or
            Path(bindings["p1_per_stock"]["path"]).resolve() !=
            (Path(bindings["p1_manifest"]["path"]).parent / "per_stock_month.csv").resolve()):
        raise ValueError("P1 derived-source lineage differs")
    actual = read_json(bindings["p1_actual_input"])
    if (actual.get("status") != "conditional_derived_historical_only" or
            actual.get("source_count") != 600 or actual.get("row_count") != 1852185):
        raise ValueError("P1 source preflight identity differs")


def validate_new_prices(ev, old_map, corrected_path, codes, dates):
    rows, columns = csv_rows(corrected_path, ev.PRICE_FIELDS)
    expected = set(old_map)
    if len(rows) != len(expected) or len(rows) != 79200:
        raise ValueError("corrected price row count differs")
    changed = []
    seen = set()
    new_map = dict(old_map)
    for row in rows:
        key = (row["month"], row["code"])
        if key not in expected or key in seen:
            raise ValueError(f"corrected price duplicate or outside frozen cohort: {key}")
        seen.add(key)
        before = old_map[key]
        if any(row[n] != before[n] for n in ("month", "code", "decision_date", "entry_date", "exit_date")):
            raise ValueError(f"price identity or date changed: {key}")
        if (row["decision_date"], row["entry_date"], row["exit_date"]) != dates[key[0]]:
            raise ValueError(f"corrected date tuple inconsistent: {key}")
        ev._bool(row["either_halt"])
        future = ev._number(row["future_return"])
        if ((future is not None and (future < -1 or not row["outcome_reason"].startswith("observed"))) or
                (future is None and row["outcome_reason"].startswith("observed"))):
            raise ValueError(f"corrected outcome guard failed: {key}")
        if row["eligibility_reason"] == "eligible":
            ev._number(row["momentum"], required=True)
        delta = {name: {"old": before[name], "new": row[name]}
                 for name in CONSUMED if row[name] != before[name]}
        if delta:
            if key[1] != "sz.001914":
                raise ValueError(f"corrected P2-consumed field changed outside source repair: {key}")
            changed.append({"month": key[0], "code": key[1], "fields": delta})
            new_map[key] = {**before, **{name: row[name] for name in CONSUMED}}
    if seen != expected or set(codes) != {code for _, code in expected}:
        raise ValueError("corrected source misses frozen code-month")
    return new_map, changed, columns


def normalized_stock_rows(rows):
    return [{key: "" if value is None else str(value) for key, value in row.items()}
            for row in rows]


def json_save(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def csv_save(path, rows):
    if not rows:
        raise ValueError("empty CSV result")
    with Path(path).open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def marker(out, step, status, detail=None):
    json_save(out / f"{step}-{status}.json", {
        "step": step, "status": status, "at_utc": datetime.now(timezone.utc).isoformat(),
        "detail": detail or {}, "no_automatic_retry": True})


def run(contract_path, out):
    contract_path = Path(contract_path).resolve()
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if (contract.get("schema") != SCHEMA or contract.get("execution_authorized") is not True or
            contract.get("market_data_requests") != 0 or contract.get("parameter_search") is not False or
            set(contract.get("bindings", {})) != REQUIRED or
            contract.get("budget") != {"core_used": 1, "followups_before": 2,
                                       "followup_number": 3, "followups_max": 3}):
        raise ValueError("P2 corrective execution contract differs")
    bindings = contract["bindings"]
    for binding in bindings.values():
        bound(binding)
    if Path(bindings["self"]["path"]).resolve() != Path(__file__).resolve():
        raise ValueError("P2 runner identity differs")
    out = output_preflight(contract, out)
    old_contract = read_json(bindings["old_core_contract"])
    old_manifest = read_json(bindings["old_core_manifest"])
    p1_contract = read_json(bindings["p1_execution_contract"])
    p1_manifest = read_json(bindings["p1_manifest"])
    ev = module(bindings["old_core_runner"], "frozen_p2_evaluator")
    risk = module(bindings["risk_runner"], "frozen_p2_risk")
    gradient = module(bindings["gradient_runner"], "frozen_p2_gradient")
    if (old_contract.get("schema") != "financial-evaluation-run/1" or
            old_contract.get("execution_authorized") is not True or
            old_contract.get("market_data_requests") != 0 or
            old_contract.get("parameter_search") is not False):
        raise ValueError("old P2 core contract identity/scope differs")
    validate_old_lineage(old_contract["inputs"], old_contract, bindings, ev)
    validate_old_outputs(bindings, old_manifest, old_contract)
    validate_p1(bindings, p1_contract, p1_manifest)
    old_risk = read_json(bindings["old_risk_manifest"])
    old_gradient = read_json(bindings["old_gradient_manifest"])
    if (old_risk.get("schema") != "financial-risk-followup-result/1" or
            old_risk.get("inputs", {}).get("monthly") != bindings["old_monthly"] or
            old_risk.get("inputs", {}).get("core_manifest") != bindings["old_core_manifest"] or
            old_risk.get("core_original_outputs", {}).get("monthly.json", {}).get("sha256") !=
            bindings["old_monthly"]["sha256"] or
            old_gradient.get("schema") != "selection-gradient-result/1" or
            old_gradient.get("stock_weights_sha256") != bindings["old_stock_weights"]["sha256"] or
            old_gradient.get("core_manifest_sha256") != bindings["old_core_manifest"]["sha256"]):
        raise ValueError("old risk/gradient lineage differs")
    old_prices, panel, dates, codes = ev._load_inputs(old_contract["inputs"])
    new_prices, price_changes, columns = validate_new_prices(
        ev, old_prices, bound(bindings["p1_per_stock"]), codes, dates)
    old_monthly = read_json(bindings["old_monthly"])
    old_layers = read_json(bindings["old_layers"])
    old_stock, _ = csv_rows(bound(bindings["old_stock_weights"]), set(gradient.EXPECTED_COLUMNS))
    output_preflight(contract, out)
    out.mkdir(mode=0o700)
    marker(out, "core", "started", {"changed_price_keys": len(price_changes)})
    try:
        monthly, stock, layers = ev._evaluate(new_prices, panel, dates, codes)
        new_monthly = list(monthly.values())
        new_stock = normalized_stock_rows(stock)
        if not (len(old_monthly) == len(new_monthly) and len(old_stock) == len(new_stock)):
            raise ValueError("core result shape differs from original")
        monthly_changed = old_monthly != new_monthly
        stock_changed = old_stock != new_stock
        layers_changed = old_layers != layers
        old_monthly_map = {(r["scope"], r["month"]): r for r in old_monthly}
        quote_changed = any(
            ev._series(old_monthly_map, scope, scenario, method) !=
            ev._series(monthly, scope, scenario, method)
            for scope, _, _ in ev.SCOPES for scenario in ev.SCENARIOS for method in ev.METHODS)
        gradient_changed = gradient.parse_rows(old_stock) != gradient.parse_rows(new_stock)
        if monthly_changed:
            performance, paired = ev._summaries(monthly)
            uncertainty = ev._bootstrap(monthly) if quote_changed else read_json(bindings["old_uncertainty"])
            other = ev._other(monthly)
            for name, value in (("monthly.json", new_monthly), ("performance.json", performance),
                                ("paired.json", paired), ("other_uses.json", other)):
                json_save(out / name, value)
            if quote_changed:
                json_save(out / "uncertainty.json", uncertainty)
        if stock_changed:
            csv_save(out / "stock_weights.csv", stock)
        if layers_changed:
            json_save(out / "qualification_layers.json", layers)
        marker(out, "core", "completed", {"monthly_changed": monthly_changed,
                                           "stock_changed": stock_changed,
                                           "layers_changed": layers_changed,
                                           "quote_series_changed": quote_changed,
                                           "uncertainty_reused": not quote_changed})
        marker(out, "risk", "started", {"monthly_changed": monthly_changed})
        old_series = risk.make_series(old_monthly)
        new_series = risk.make_series(new_monthly)
        risk_changed = old_series != new_series
        if risk_changed:
            if not monthly_changed:
                raise ValueError("risk input differs without core monthly difference")
            rows, hashes = risk.calculate(new_series)
            risk.verify_core(new_series, paired, uncertainty, hashes)
            json_save(out / "conditional_intervals.json", rows)
        marker(out, "risk", "completed", {"input_changed": risk_changed})
        marker(out, "gradient", "started", {"stock_changed": stock_changed,
                                             "consumed_rows_changed": gradient_changed})
        if gradient_changed:
            gradient_monthly, gradient_support, gradient_summary = gradient.calculate(
                new_stock, expected_months=ev._months())
            csv_save(out / "gradient-monthly.csv", gradient_monthly)
            csv_save(out / "gradient-support.csv", gradient_support)
            json_save(out / "gradient-summary.json", gradient_summary)
        marker(out, "gradient", "completed", {"input_changed": gradient_changed})
        json_save(out / "price-differences.json", price_changes)
        result = {"schema": "p2-price-correction-result/1", "status": "completed_pending_review",
                  "contract_sha256": sha(contract_path), "market_data_requests": 0,
                  "budget": contract["budget"], "factor_ready": False,
                  "old_financial_panel_unchanged": True, "old_165_unqualified_months_not_restored": True,
                  "source_price_columns": columns, "changed_price_keys": len(price_changes),
                  "core": {"monthly_changed": monthly_changed, "stock_changed": stock_changed,
                           "layers_changed": layers_changed, "quote_series_changed": quote_changed,
                           "uncertainty_reused": not quote_changed,
                           "old_uncertainty": bindings["old_uncertainty"] if not quote_changed else None,
                           "old_manifest": bindings["old_core_manifest"]},
                  "risk": {"input_changed": risk_changed,
                           "old_manifest": bindings["old_risk_manifest"]},
                  "gradient": {"input_changed": gradient_changed,
                               "old_manifest": bindings["old_gradient_manifest"]},
                  "outputs": {p.name: {"sha256": sha(p), "bytes": p.stat().st_size}
                              for p in out.iterdir() if p.is_file()}}
        output_preflight_after(out, contract)
        for binding in bindings.values():
            bound(binding)
        json_save(out / "manifest.json", result)
        return result
    except Exception as exc:
        marker(out, "execution", "failed", {"error_type": type(exc).__name__, "message": str(exc)[:500]})
        raise


def output_preflight_after(out, contract):
    """Same disk and capacity gate after create, before final manifest."""
    spec = contract["output"]
    mount = Path(spec["mount"])
    if (not os.path.ismount(mount) or mount.stat().st_dev != spec["external_device"] or
            out.stat().st_dev != spec["external_device"] or
            shutil.disk_usage(mount).free < spec["external_reserve_bytes"] or
            shutil.disk_usage(spec["internal_root"]).free < spec["internal_reserve_bytes"]):
        raise ValueError("output disk/device/reserve changed during P2 correction")
    info = plistlib.loads(subprocess.run(["/usr/sbin/diskutil", "info", "-plist", str(mount)],
                                    capture_output=True, check=True, timeout=10).stdout)
    if info.get("VolumeUUID") != spec["external_uuid"]:
        raise ValueError("output disk UUID changed during P2 correction")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    run(args.contract, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
