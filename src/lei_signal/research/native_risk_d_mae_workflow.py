"""Finite, synthetic-only D versus close-MAE20 adapter for Factor Lab.

The fixed arithmetic follows the reviewed study.py (SHA-256 84f4fee2...),
but archived raw code is never imported. Real X/Y remain disabled in this
version. The X file contains no future closes; a separate Y file is opened
only by the Y stage after an X receipt has been verified.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import statistics
import time
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

SCHEMA = "research-workflow/d-mae20/1.0"
FEATURE_KIND = "native_risk_d_mae20"
ASSETS = ("510050.SS", "510300.SS", "510500.SS", "512400.SS", "512800.SS", "588000.SS")
COUNTS = (15, 17, 12, 5, 26, 1)
CUTOFF = "2026-06-26"
DESIGN_SHA = "ace132ddb89de3e45951148d9673524fa9fe448f662f2576221d216bbe9717c6"
STUDY_SHA = "84f4fee2a538a918352bca099ec9c9b4a38f6d6a19dab5faa564b668c0bd8745"
CODE_PATHS = (
    "src/lei_signal/research/native_risk_d_mae_workflow.py",
    "src/lei_signal/research/question_contract.py",
    "src/lei_signal/research/workflow_inputs.py",
    "src/lei_signal/research/workflow.py",
    "scripts/run_factor_lab.py",
)


def is_native(contract):
    return isinstance(contract, dict) and contract.get("schema_version") == SCHEMA


def _fail(message):
    raise ValueError(f"native D-MAE20: {message}")


def _sha(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _positive(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _read_bound(root, relative, expected):
    base = Path(root).resolve()
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        _fail("input path must be project-relative")
    path = (base / relative).resolve()
    if not path.is_relative_to(base) or not path.is_file():
        _fail(f"input path escapes root or is missing: {relative}")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        _fail(f"input SHA-256 mismatch: {relative}")
    return json.loads(raw)


def validate_contract(contract):
    """Declaration check only; it neither opens inputs nor grants execution."""
    if not is_native(contract) or contract.get("study_id") != "frozen_d_close_mae20":
        _fail("unsupported schema/study")
    stage = contract.get("stage")
    if stage not in ("x", "y"):
        _fail("stage must be x or y")
    if contract.get("feature") != {"kind": FEATURE_KIND}:
        _fail("feature must be the one fixed native adapter")
    if contract.get("target") != {"kind": "mae", "start_offset": 1, "end_offset": 21,
                                   "entry_field": "close", "path_field": "close",
                                   "unit": "percentage_point", "cutoff": CUTOFF}:
        _fail("target differs from frozen close-MAE20")
    if contract.get("comparison") != {"candidate": "D", "benchmark": "V",
                                       "evaluator": "signed_spearman_equal_asset_fixed_groups/1.0",
                                       "deletion_groups": 33, "fits": 0}:
        _fail("comparison differs from frozen D/V descriptive design")
    if type(contract["comparison"]["fits"]) is not int or type(contract["comparison"]["deletion_groups"]) is not int:
        _fail("comparison counts must be integers")
    data = contract.get("data")
    if not isinstance(data, dict) or data.get("mode") != "synthetic" or data.get("artificial_only") is not True:
        _fail("this adapter accepts artificial synthetic inputs only; real X/Y remain blocked")
    for key in ("x_path", "x_sha256"):
        if key not in data:
            _fail(f"data.{key} missing")
    if not _sha(data["x_sha256"]):
        _fail("data.x_sha256 invalid")
    if stage == "y":
        for key in ("y_path", "y_sha256"):
            if key not in data:
                _fail(f"data.{key} missing")
        if not _sha(data["y_sha256"]):
            _fail("data.y_sha256 invalid")
        prior = contract.get("x_receipt")
        if not isinstance(prior, dict) or not isinstance(prior.get("path"), str) or not _sha(prior.get("sha256")):
            _fail("Y needs a bound X receipt path and SHA-256")
    elif "y_path" in data or "y_sha256" in data or "x_receipt" in contract:
        _fail("X stage must not name a Y file or prior result")
    sources = contract.get("sources")
    if sources != {"design_sha256": DESIGN_SHA, "synthetic_math_sha256": STUDY_SHA}:
        _fail("design and reviewed arithmetic source identity must be fixed")
    history = contract.get("history")
    if not isinstance(history, dict) or not isinstance(history.get("family"), str) or not history["family"].startswith("native-d-mae20-synthetic-"):
        _fail("dedicated synthetic family is required")
    budget = contract.get("budget")
    if not isinstance(budget, dict) or not _positive(budget.get("execution_seconds")) or type(budget.get("stage_runs")) is not int or budget["stage_runs"] != 2:
        _fail("budget must hold positive seconds and exactly two stage runs")
    permissions = contract.get("permissions")
    if (not isinstance(permissions, dict) or
        set(permissions) != {"real_X", "real_Y", "real_fits", "market_requests", "paid_requests", "production"} or
        any(permissions[key] is not False for key in ("real_X", "real_Y", "production")) or
        any(type(permissions[key]) is not int or permissions[key] != 0 for key in ("real_fits", "market_requests", "paid_requests"))):
        _fail("real-data, fit, paid and production permissions must remain zero")
    publication = contract.get("publication")
    if (not isinstance(publication, dict) or set(publication) != {"conclusion", "register_report"} or
        publication["conclusion"] != "synthetic_engineering_only" or publication["register_report"] is not False):
        _fail("synthetic runs cannot register a market-effect report")


def volatility_scale(anchor_close, atr20_sma):
    if not _positive(anchor_close) or not _positive(atr20_sma):
        _fail("V needs positive finite A and ATR")
    value = 100.0 * atr20_sma / anchor_close
    if not math.isfinite(value):
        _fail("V arithmetic produced a nonfinite result")
    return value


def prepare_x(payload):
    if not isinstance(payload, dict) or payload.get("schema_version") != "native-d-mae-x/1.0" or payload.get("artificial_only") is not True:
        _fail("X payload must be an explicit artificial fixture")
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) != 76:
        _fail("exactly 76 cases required")
    ids, keys, aliases, groups, rows = set(), set(), set(), set(), []
    counts = Counter()
    member_occurrences = 0
    for case in cases:
        if not isinstance(case, dict):
            _fail("case is not an object")
        cid, asset, day, lifecycle = (case.get(k) for k in ("case_id", "asset", "signal_date", "lifecycle"))
        if not all(isinstance(v, str) and v for v in (cid, asset, day, lifecycle)) or asset not in ASSETS:
            _fail("case identity/asset invalid")
        try:
            date.fromisoformat(day)
        except ValueError:
            _fail("signal_date invalid")
        if cid in ids or (asset, day) in keys:
            _fail("duplicate case or asset-date")
        ids.add(cid); keys.add((asset, day)); groups.add((asset, lifecycle)); counts[asset] += 1
        members = case.get("event_ids")
        if not isinstance(members, list) or not members or any(not isinstance(v, str) or not v for v in members):
            _fail("missing/invalid event membership")
        if len(members) != len(set(members)) or any(v in aliases for v in members):
            _fail("missing/duplicate event membership")
        aliases.update(members)
        member_occurrences += len(members)
        A, C, atr, D = (case.get(k) for k in ("A", "C", "ATR20_SMA", "D"))
        if not _positive(A) or not _positive(C) or not _positive(atr) or not _finite(D):
            _fail("case A/C/ATR/D invalid")
        V = volatility_scale(A, atr)
        # D is a frozen input. Check arithmetic identity, but never replace it.
        if not math.isclose(D, (A - C) / atr, rel_tol=1e-9, abs_tol=1e-9):
            _fail("saved D conflicts with its fixed A/C/ATR identity")
        rows.append({"case_id": cid, "asset": asset, "signal_date": day,
                     "lifecycle": lifecycle, "event_ids": list(members),
                     "D": D, "V": V, "A": A, "C": C, "ATR20_SMA": atr})
    if tuple(counts[a] for a in ASSETS) != COUNTS or member_occurrences != 84 or len(aliases) != 84 or len(groups) != 33:
        _fail("frozen 76/84/33 population structure differs")
    return sorted(rows, key=lambda row: row["case_id"])


def path_close(record):
    if isinstance(record, dict):
        if "status" in record and record["status"] != "quoted":
            return None
        if "action_known" in record and (type(record["action_known"]) is not bool or not record["action_known"]):
            return None
        record = record.get("close")
    return record if _positive(record) else None


def validate_y_paths(x_rows, payload):
    """Validate every mature path before returning any closes for Y arithmetic."""
    if not isinstance(payload, dict) or payload.get("schema_version") != "native-d-mae-y/1.0" or payload.get("artificial_only") is not True or payload.get("cutoff") != CUTOFF:
        _fail("Y payload must be a fixed artificial close-path fixture")
    windows, calendars, prices = (payload.get(k) for k in ("windows", "retained_dates", "prices"))
    if not all(isinstance(v, dict) for v in (windows, calendars, prices)):
        _fail("Y windows/calendars/prices must be mappings")
    if set(windows) != {r["case_id"] for r in x_rows}:
        _fail("Y case identity differs from frozen X receipt")
    paths, unknown = {}, []
    for row in x_rows:
        cid, asset, day = row["case_id"], row["asset"], row["signal_date"]
        window = windows[cid]
        if window.get("asset") != asset or window.get("signal_date") != day:
            _fail(f"window identity mismatch: {cid}")
        dates = calendars.get(asset)
        if not isinstance(dates, list) or dates != sorted(set(dates)) or day not in dates:
            _fail(f"calendar missing/unsorted/duplicated: {asset}")
        i = dates.index(day)
        future = dates[i + 1:i + 22]
        if not future or future[0] != window.get("label_start"):
            _fail(f"window start mismatch: {cid}")
        mature = window.get("calendar_mature_by_20260626")
        if type(mature) is not bool:
            _fail(f"maturity flag must be boolean: {cid}")
        if not mature:
            if window.get("label_end") is not None or (len(future) == 21 and future[-1] <= CUTOFF) or (len(future) < 21 and dates[-1] < CUTOFF):
                _fail(f"unknown window contradicts cutoff: {cid}")
            unknown.append(cid)
            continue
        if len(future) != 21:
            _fail(f"mature window needs 21 retained dates: {cid}")
        if future[-1] != window.get("label_end") or future[-1] > CUTOFF:
            _fail(f"mature window end/cutoff mismatch: {cid}")
        asset_prices = prices.get(asset)
        if not isinstance(asset_prices, dict):
            _fail(f"prices missing for asset: {asset}")
        closes = [path_close(asset_prices.get(d)) for d in future]
        if any(not _positive(value) for value in closes):
            _fail(f"full 21-close path missing/invalid: {cid}")
        paths[cid] = {"dates": future, "closes": closes}
    if len(paths) != 75 or len(unknown) != 1:
        _fail("expected 75 complete mature paths and one unknown")
    return paths, unknown[0]


def close_mae20(closes):
    if len(closes) != 21 or any(not _positive(v) for v in closes):
        _fail("MAE20 needs exactly 21 positive finite closes")
    return max(0.0, 100.0 * (1.0 - min(closes) / closes[0]))


def _ranks(values):
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        rank = (i + 1 + j) / 2.0
        for index in order[i:j]:
            ranks[index] = rank
        i = j
    return ranks


def _spearman(x, y):
    if len(x) != len(y) or len(x) < 2:
        return None
    a, b = _ranks(x), _ranks(y)
    am, bm = statistics.mean(a), statistics.mean(b)
    numerator = sum((v - am) * (w - bm) for v, w in zip(a, b))
    aa = sum((v - am) ** 2 for v in a)
    bb = sum((v - bm) ** 2 for v in b)
    return numerator / math.sqrt(aa * bb) if aa and bb else None


def _per_asset(rows):
    result = {}
    for asset in ASSETS:
        all_rows = [r for r in rows if r["asset"] == asset]
        complete = [r for r in all_rows if all(_finite(r.get(k)) for k in ("D", "V", "Y"))]
        d, v, y = ([r[k] for r in complete] for k in ("D", "V", "Y"))
        rd, rv = _spearman(d, y), _spearman(v, y)
        result[asset] = {"all_cases": len(all_rows), "complete_cases": len(complete),
                         "complete_case_ids": [r["case_id"] for r in complete],
                         "rho_D_Y": rd, "rho_V_Y": rv,
                         "rho_D_minus_V": rd - rv if rd is not None and rv is not None else None,
                         "n2_degenerate": len(complete) == 2,
                         "reason": "n_lt_2" if len(complete) < 2 else
                                   "constant_rank" if rd is None or rv is None else None}
    return result


def _fixed_summary(per_asset, fixed=None):
    if fixed is None:
        fixed = tuple(a for a in ASSETS if per_asset[a]["rho_D_Y"] is not None and per_asset[a]["rho_V_Y"] is not None)
    if not fixed:
        return {"fixed_assets": [], "rho_D_Y": None, "rho_V_Y": None,
                "rho_D_minus_V": None, "reason": "no_common_computable_asset"}
    if any(per_asset[a]["rho_D_Y"] is None or per_asset[a]["rho_V_Y"] is None for a in fixed):
        return {"fixed_assets": list(fixed), "rho_D_Y": None, "rho_V_Y": None,
                "rho_D_minus_V": None, "reason": "fixed_asset_became_uncomputable"}
    rd = statistics.mean(per_asset[a]["rho_D_Y"] for a in fixed)
    rv = statistics.mean(per_asset[a]["rho_V_Y"] for a in fixed)
    return {"fixed_assets": list(fixed), "rho_D_Y": rd, "rho_V_Y": rv,
            "rho_D_minus_V": rd - rv, "reason": None}


def summarize(rows):
    if len(rows) != 76 or len({r["case_id"] for r in rows}) != 76:
        _fail("summary requires all 76 original case identities")
    groups = sorted({(r["asset"], r["lifecycle"]) for r in rows})
    if len(groups) != 33:
        _fail("summary requires all 33 fixed lifecycle groups")
    per_asset = _per_asset(rows)
    primary = _fixed_summary(per_asset)
    fixed = tuple(primary["fixed_assets"])
    deleted = []
    for asset, lifecycle in groups:
        remaining = [r for r in rows if (r["asset"], r["lifecycle"]) != (asset, lifecycle)]
        deleted.append({"deleted_asset": asset, "deleted_lifecycle": lifecycle,
                        "deleted_case_ids": [r["case_id"] for r in rows if (r["asset"], r["lifecycle"]) == (asset, lifecycle)],
                        "fixed_asset_summary": _fixed_summary(_per_asset(remaining), fixed),
                        "per_asset": _per_asset(remaining)})
    return {"per_asset": per_asset, "primary": primary, "leave_one_lifecycle": deleted}


def evaluate_y(x_rows, paths, unknown_id):
    rows = []
    for row in x_rows:
        cid = row["case_id"]
        rows.append({**row, "Y": close_mae20(paths[cid]["closes"]) if cid in paths else None,
                     "label_reason": "beyond_frozen_cutoff" if cid == unknown_id else None,
                     "label_start": paths[cid]["dates"][0] if cid in paths else None,
                     "label_end": paths[cid]["dates"][-1] if cid in paths else None})
    return {"schema_version": "native-d-mae-result/1.0", "stage": "y", "rows": rows,
            "unknown_case_id": unknown_id, "mature_count": len(paths),
            "statistics": summarize(rows), "fits": 0,
            "production_authorized": False, "real_X": 0, "real_Y": 0}


def _workflow_helpers():
    # Import lazily after workflow.py has selected this finite adapter. Its
    # existing journal, family lock and exclusive-write helpers remain shared.
    from lei_signal.research import workflow
    return workflow


def _bindings(contract, root):
    workflow = _workflow_helpers()
    config_path = Path(root) / "configs/strategy-documents.v1.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    approved = {entry["file_name"]: entry["approved_sha256"] for entry in config["documents"]}
    if set(approved.values()) != {
        "df92d85b3b04ed3ab71d56bc108d0effe8eb31051b7a1531eda59edcbf0aab20",
        "85e0e3270ff96fe85247756805c58c650a0e83b21ea15c9feccea84d31aaf903",
    }:
        _fail("strategy source approved SHA-256 changed")
    return {"files": {name: workflow.file_hash(Path(root) / name) for name in CODE_PATHS},
            "strategy_config_sha256": workflow.file_hash(config_path),
            "strategy_approved_sha256": approved,
            "x_sha256": contract["data"]["x_sha256"],
            "y_sha256": contract["data"].get("y_sha256"),
            "design_sha256": DESIGN_SHA, "reviewed_math_sha256": STUDY_SHA}


def _receipt_dir(root, relative):
    base = Path(root).resolve()
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        _fail("X receipt path must be project-relative")
    path = (base / relative).resolve()
    if not path.is_relative_to(base):
        _fail("X receipt path escapes project root")
    return path


def preflight(contract, root, *, require_frozen=True):
    workflow = _workflow_helpers()
    validate_contract(contract)
    x_payload = _read_bound(root, contract["data"]["x_path"], contract["data"]["x_sha256"])
    from lei_signal.research.workflow_inputs import prepare_observations
    observations = prepare_observations(x_payload, contract)["observations"]
    if len(observations) != 76:
        _fail("X adapter changed its fixed population")
    proof = {"bindings": _bindings(contract, root), "observations": observations,
             "coverage": {"cases": 76, "events": 84, "asset_lifecycle_groups": 33,
                          "assets": list(ASSETS), "mode": "synthetic"},
             "calculation_run": False, "production_authorized": False,
             "stage": contract["stage"]}
    if contract["stage"] == "y":
        prior = contract["x_receipt"]
        x_out = _receipt_dir(root, prior["path"])
        if workflow.file_hash(x_out / "receipt.json") != prior["sha256"]:
            _fail("X receipt SHA-256 changed")
        x_contract, x_result = verify_receipt(x_out, root)
        if x_contract["stage"] != "x" or x_contract["history"]["family"] != contract["history"]["family"]:
            _fail("Y does not refer to this family's completed X stage")
        if x_contract["data"]["x_sha256"] != contract["data"]["x_sha256"] or x_result["rows"] != observations:
            _fail("Y X identity/membership differs from sealed X receipt")
        y_payload = _read_bound(root, contract["data"]["y_path"], contract["data"]["y_sha256"])
        paths, unknown = validate_y_paths(observations, y_payload)
        proof["validated_paths"] = paths
        proof["unknown_case_id"] = unknown
        proof["x_receipt_sha256"] = prior["sha256"]
        proof["coverage"].update({"mature_valid_paths": 75, "unknown_paths": 1})
    if require_frozen:
        if contract.get("bindings") != proof["bindings"]:
            _fail("source/data bindings changed after freeze")
        freeze = contract.get("freeze", {})
        if freeze.get("proof_sha256") != workflow.digest(proof):
            _fail("frozen proof differs from current input or qualification")
    return proof


def _rehearsal(stage):
    # Fixed, fully artificial arithmetic check. X rehearsal does not evaluate
    # even an artificial Y; the Y stage is the only one that does so.
    example = {"V_example": volatility_scale(100.0, 2.0),
               "rank_tie_example": _ranks([1.0, 1.0, 3.0])}
    if stage == "y":
        example["MAE20_example"] = close_mae20([100.0] + [90.0] * 20)
    return {"schema_version": "workflow-rehearsal/1.0", "data_mode": "synthetic",
            "purpose": "engineering_error_check_only", "stage": stage,
            "examples": example, "fits": 0, "selection_used": False}


def freeze_contract(contract, root):
    workflow = _workflow_helpers()
    frozen = copy.deepcopy(contract)
    frozen["history"]["ledger_path"] = str(workflow.family_ledger(root, frozen["history"]["family"]).relative_to(root))
    proof = preflight(frozen, root, require_frozen=False)
    frozen["bindings"] = proof["bindings"]
    frozen["freeze"] = {"proof_sha256": workflow.digest(proof)}
    with workflow.family_execution_lock(root, frozen):
        journal = workflow.family_ledger(root, frozen["history"]["family"])
        with workflow.locked_journal(journal) as (stream, records):
            headers = [r for r in records if r.get("event") == "family"]
            if headers and headers[0].get("budget") != frozen["budget"]:
                _fail("family budget changed after first freeze")
            if not headers:
                workflow._append(stream, {"event": "family", "family": frozen["history"]["family"],
                                          "budget": frozen["budget"], "adapter": FEATURE_KIND})
        rehearsal = _rehearsal(frozen["stage"])
        with workflow.locked_journal(journal) as (stream, _):
            workflow._append(stream, {"event": "rehearsal", "stage": frozen["stage"],
                                      "purpose": "engineering_error_check_only", "seconds": 0,
                                      "market_fits": 0})
    frozen["rehearsal"] = rehearsal
    return frozen, proof


def freeze_workflow(draft_path, output_dir, root):
    workflow = _workflow_helpers()
    out = Path(output_dir)
    if out.exists():
        _fail("freeze output already exists")
    frozen, proof = freeze_contract(workflow.read_json(draft_path), root)
    out.mkdir(parents=True, exist_ok=False)
    workflow.write_json(out / "contract.json", frozen)
    workflow.write_json(out / "rehearsal.json", frozen["rehearsal"])
    workflow.write_json(out / "preflight.json", proof)
    return out / "contract.json"


def _expected_result(contract, proof):
    if contract["stage"] == "x":
        return {"schema_version": "native-d-mae-result/1.0", "stage": "x",
                "rows": proof["observations"], "coverage": proof["coverage"],
                "fits": 0, "production_authorized": False, "real_X": 0, "real_Y": 0}
    return evaluate_y(proof["observations"], proof["validated_paths"], proof["unknown_case_id"])


def render_report(contract, result):
    if contract["stage"] == "x":
        return ("# D—MAE20 人工输入绑定\n\n## 一句话结论（大白话）\n\n"
                "76个人工案例、84个原事件别名和33组生命周期已按固定结构绑定；"
                "这一阶段没有读取未来价格，也没有计算因子效果。\n\n"
                "执行：completed；证据：synthetic_engineering_only；真实X/Y=0；拟合=0；交易许可：无。\n")
    primary = result["statistics"]["primary"]
    return ("# D—MAE20 人工未来价格比较\n\n## 一句话结论（大白话）\n\n"
            "75条人工成熟价格路径完整、1条按固定截止日未知；这里只验证计算和归档流程，"
            "不能判断真实D因子是否有用。\n\n"
            "| 比较 | D | V | 差值 | 固定共同资产数 |\n|---|---:|---:|---:|---:|\n"
            f"| 人工同样本排序联系 | {primary['rho_D_Y']} | {primary['rho_V_Y']} | "
            f"{primary['rho_D_minus_V']} | {len(primary['fixed_assets'])} |\n\n"
            "33个逐组删除场景、76行案例和未知原因见 result.json。真实X/Y=0；"
            "条件增量、资金收益及交易许可均未测量。\n\n"
            "执行：completed；证据：synthetic_engineering_only；拟合=0；交易许可：无。\n")


def execute_workflow(contract_path, output_dir, root, *, register_report=False, reuse_predictions=None):
    workflow = _workflow_helpers()
    started_at = time.monotonic()
    contract = workflow.read_json(contract_path)
    validate_contract(contract)
    if register_report or reuse_predictions:
        _fail("synthetic D-MAE does not register reports or reuse predictions")
    out = Path(output_dir)
    if out.exists():
        _fail("run output already exists; sealed runs are never overwritten")
    proof = preflight(contract, root)
    if contract.get("rehearsal") != _rehearsal(contract["stage"]):
        _fail("frozen synthetic rehearsal missing or changed")
    journal = workflow.family_ledger(root, contract["history"]["family"])
    run_id = None
    with workflow.family_execution_lock(root, contract):
        with workflow.locked_journal(journal) as (stream, records):
            headers = [r for r in records if r.get("event") == "family"]
            if len(headers) != 1 or headers[0].get("budget") != contract["budget"]:
                _fail("family ledger budget/header does not match frozen contract")
            if any(r.get("event") == "start" and r.get("stage") == contract["stage"] for r in records):
                _fail("stage already started; repeat and automatic retry refused")
            starts = [r for r in records if r.get("event") == "start"]
            if len(starts) >= contract["budget"]["stage_runs"]:
                _fail("family stage run budget exhausted")
            if contract["stage"] == "y" and not any(r.get("event") == "finish" and r.get("stage") == "x" and r.get("status") == "computed" for r in records):
                _fail("Y needs a completed X stage in this family")
            spent = sum(r.get("seconds", 0) for r in records if r.get("event") in ("finish", "gate_attempt"))
            if spent + time.monotonic() - started_at >= contract["budget"]["execution_seconds"]:
                raise workflow.WorkflowPaused("native family time budget exhausted")
            run_id = workflow.uuid.uuid4().hex
            workflow._append(stream, {"event": "start", "stage": contract["stage"],
                                      "run_id": run_id, "data_sha256": contract["data"]["x_sha256"],
                                      "time": datetime.now(timezone.utc).isoformat(),
                                      "out": str(out), "real_effect_run": False})
        out.mkdir(parents=True, exist_ok=False)
        finished = False
        try:
            workflow.write_json(out / "contract.json", contract)
            workflow.write_json(out / "preflight.json", proof)
            result = _expected_result(contract, proof)
            # A checkpoint before result publication charges prior stages plus
            # this stage's calculation time. This is not an OS hard deadline.
            if spent + time.monotonic() - started_at >= contract["budget"]["execution_seconds"]:
                raise workflow.WorkflowPaused("native family time budget exhausted before result publication")
            workflow.write_json(out / "result.json", result)
            (out / "report.md").write_text(render_report(contract, result), encoding="utf-8")
            receipt = {"schema_version": "workflow-receipt/1.0", "entry": "scripts/run_factor_lab.py --workflow-contract",
                       "adapter": FEATURE_KIND, "stage": contract["stage"], "run_id": run_id,
                       "contract_sha256": workflow.file_hash(out / "contract.json"),
                       "outputs": {name: workflow.file_hash(out / name) for name in ("preflight.json", "result.json", "report.md")},
                       "real_X": 0, "real_Y": 0, "fits": 0}
            workflow.write_json(out / "receipt.json", receipt)
            with workflow.locked_journal(journal) as (stream, _):
                workflow._append(stream, {"event": "finish", "stage": contract["stage"],
                                          "run_id": run_id, "status": "computed",
                                          "seconds": time.monotonic() - started_at,
                                          "receipt_sha256": workflow.file_hash(out / "receipt.json"),
                                          "results_seen": contract["stage"] == "y",
                                          "real_effect_run": False})
            finished = True
            state = check_publication(out, root)
            workflow.write_json(out / "state.json", state)
            return out
        except BaseException as error:
            with workflow.locked_journal(journal) as (stream, _):
                workflow._append(stream, {"event": "publication_failed" if finished else "finish", "stage": contract["stage"],
                                          "run_id": run_id, **({} if finished else {"status": "failed_after_start"}),
                                          "seconds": time.monotonic() - started_at,
                                          "error": f"{type(error).__name__}: {error}",
                                          "results_seen": False, "real_effect_run": False})
            if not (out / "failure.json").exists():
                workflow.write_json(out / "failure.json", {"execution": "blocked",
                    "stage": contract["stage"], "error": f"{type(error).__name__}: {error}"})
            raise


def verify_receipt(output_dir, root):
    workflow = _workflow_helpers()
    out = Path(output_dir)
    contract = workflow.read_json(out / "contract.json")
    if not is_native(contract):
        _fail("receipt does not belong to D-MAE20")
    receipt = workflow.read_json(out / "receipt.json")
    if receipt.get("adapter") != FEATURE_KIND or receipt.get("stage") != contract["stage"] or receipt.get("contract_sha256") != workflow.file_hash(out / "contract.json"):
        _fail("receipt identity or contract hash mismatch")
    if set(receipt.get("outputs", {})) != {"preflight.json", "result.json", "report.md"}:
        _fail("receipt output set differs from frozen adapter")
    proof = preflight(contract, root, require_frozen=True) if contract["stage"] == "x" else None
    if contract["stage"] == "y":
        # The Y preflight revalidates the earlier X receipt. That recursion ends
        # at the X stage, never at this Y receipt.
        proof = preflight(contract, root, require_frozen=True)
    if workflow.read_json(out / "preflight.json") != proof:
        _fail("stored preflight differs from current frozen proof")
    for name, expected in receipt.get("outputs", {}).items():
        if name not in ("preflight.json", "result.json", "report.md") or workflow.file_hash(out / name) != expected:
            _fail(f"receipt output changed: {name}")
    journal = workflow.family_ledger(root, contract["history"]["family"])
    with workflow.locked_journal(journal) as (_, records):
        if not any(r.get("event") == "finish" and r.get("run_id") == receipt.get("run_id") and
                   r.get("stage") == contract["stage"] and r.get("status") == "computed" and
                   r.get("receipt_sha256") == workflow.file_hash(out / "receipt.json") for r in records):
            _fail("no matching sealed journal finish")
    return contract, workflow.read_json(out / "result.json")


def check_publication(output_dir, root):
    workflow = _workflow_helpers()
    out = Path(output_dir)
    contract, result = verify_receipt(out, root)
    proof = preflight(contract, root)
    expected = _expected_result(contract, proof)
    if workflow.digest(result) != workflow.digest(expected):
        _fail("saved D/V/Y rows or statistics differ from recomputation")
    if (out / "report.md").read_text(encoding="utf-8") != render_report(contract, result):
        _fail("generated report was altered")
    return {"execution": "completed", "evidence": "synthetic_engineering_only",
            "stage": contract["stage"], "receipt": workflow.read_json(out / "receipt.json")["run_id"],
            "production_authorized": False, "real_X": 0, "real_Y": 0, "fits": 0}
