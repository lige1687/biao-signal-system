"""Frozen saved-result D association, conditional on ranked volatility.

This describes previously observed opportunities. It is not a signal, forecast,
or implementation of the live strategy's ATR or exit rules.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import plistlib
import statistics
import subprocess
from datetime import UTC, datetime
from pathlib import Path

X_SCHEMA = "native-risk-d-mae-real-x/1"
Y_SCHEMA = "native-risk-d-mae-real-y/1"
ASSETS = ("510050.SS", "510300.SS", "510500.SS", "512400.SS", "512800.SS")
UNKNOWN_ID = "case:ded0d0c43677a76957f4"
CONTRACT_REL = Path("docs/experiments/raw/original-eight-continuation-2026-10-10/d-contract.json")
LEDGER_REL = Path("docs/experiments/raw/native-d-conditional-risk-2026-10-10/attempt-ledger.json")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def finite(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def average_ranks(values: list[float]) -> list[float]:
    """Ranks start at one; exact ties receive their occupied positions' mean."""
    order = sorted(range(len(values)), key=values.__getitem__)
    result = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        rank = (start + 1 + end) / 2.0
        for position in order[start:end]:
            result[position] = rank
        start = end
    return result


def pearson(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    lm, rm = statistics.mean(left), statistics.mean(right)
    numerator = sum((x - lm) * (y - rm) for x, y in zip(left, right, strict=True))
    ll = sum((x - lm) ** 2 for x in left)
    rr = sum((y - rm) ** 2 for y in right)
    if ll <= 0 or rr <= 0:
        return None
    value = numerator / math.sqrt(ll * rr)
    require(abs(value) <= 1 + 1e-12, "rank correlation outside [-1,1]")
    return max(-1.0, min(1.0, value))


def rank_correlation(left: list[float], right: list[float]) -> float | None:
    return pearson(average_ranks(left), average_ranks(right))


def asset_stat(rows: list[dict], asset: str) -> dict:
    complete = [r for r in rows if r["asset"] == asset and finite(r.get("Y"))]
    episodes = {(r["asset"], r["lifecycle"]) for r in complete}
    result = {
        "asset": asset,
        "complete_cases": len(complete),
        "complete_case_ids": [r["case_id"] for r in complete],
        "source_episodes": len(episodes),
        "distinct_D": len({r["D"] for r in complete}),
        "distinct_V": len({r["V"] for r in complete}),
        "distinct_Y": len({r["Y"] for r in complete}),
        "rho_DY": None,
        "rho_DV": None,
        "rho_VY": None,
        "partial_DY_given_V": None,
        "denominator": None,
        "reason": None,
    }
    if len(complete) < 4:
        result["reason"] = "fewer_than_four_complete_cases"
        return result
    if len(episodes) < 2:
        result["reason"] = "fewer_than_two_source_episodes"
        return result
    if min(result[k] for k in ("distinct_D", "distinct_V", "distinct_Y")) < 2:
        result["reason"] = "constant_rank_column"
        return result
    d = [r["D"] for r in complete]
    v = [r["V"] for r in complete]
    y = [r["Y"] for r in complete]
    dy, dv, vy = (rank_correlation(*pair) for pair in ((d, y), (d, v), (v, y)))
    result.update(rho_DY=dy, rho_DV=dv, rho_VY=vy)
    if dy is None or dv is None or vy is None:
        result["reason"] = "constant_rank_column"
        return result
    denominator_squared = (1 - dv * dv) * (1 - vy * vy)
    if denominator_squared <= 1e-12:
        result["reason"] = "nonpositive_partial_denominator"
        return result
    denominator = math.sqrt(denominator_squared)
    value = (dy - dv * vy) / denominator
    require(abs(value) <= 1 + 1e-10, "partial rank correlation outside [-1,1]")
    result["denominator"] = denominator
    result["partial_DY_given_V"] = max(-1.0, min(1.0, value))
    return result


def evaluate(rows: list[dict]) -> dict:
    per_asset = {asset: asset_stat(rows, asset) for asset in ASSETS}
    values = [per_asset[asset]["partial_DY_given_V"] for asset in ASSETS]
    return {
        "per_asset": per_asset,
        "fixed_assets": list(ASSETS),
        "fixed_weights": {asset: 0.2 for asset in ASSETS},
        "equal_asset_mean": statistics.mean(values) if all(v is not None for v in values) else None,
        "reason": None
        if all(v is not None for v in values)
        else "at_least_one_fixed_asset_ineligible",
    }


def analyze_rows(xrows: list[dict], yrows: list[dict]) -> dict:
    require(len(xrows) == 76 and len(yrows) == 76, "frozen case count")
    xby = {r["case_id"]: r for r in xrows}
    yby = {r["case_id"]: r for r in yrows}
    require(len(xby) == len(yby) == 76 and set(xby) == set(yby), "X/Y membership drift")
    groups = {(r["asset"], r["lifecycle"]) for r in xrows}
    require(len(groups) == 33, "frozen source episode count")
    joined = []
    for x in xrows:
        y = yby[x["case_id"]]
        for field in ("asset", "signal_date", "lifecycle"):
            require(y[field] == x[field], f"Y {field} identity drift")
        for field in ("calendar_id", "price_basis_id", "source_sha256"):
            if field in y:
                require(y[field] == x[field], f"Y {field} identity drift")
        for xfield, yfield in (("D_frozen", "D_frozen"), ("V_volatility_pct", "V_volatility_pct")):
            require(y.get(yfield) == x[xfield], f"Y carried {yfield} drift")
        mature = x["window_metadata"]["calendar_mature_by_20260626"] is True
        if mature:
            require(
                y.get("label_reason") is None and finite(y.get("Y")) and y["Y"] >= 0,
                "mature Y missing or invalid",
            )
            value = float(y["Y"])
        else:
            require(
                x["case_id"] == UNKNOWN_ID
                and y.get("Y") is None
                and y.get("label_reason") is not None,
                "original unknown filled",
            )
            value = None
        joined.append(
            {
                "case_id": x["case_id"],
                "asset": x["asset"],
                "signal_date": x["signal_date"],
                "lifecycle": x["lifecycle"],
                "D": float(x["D_frozen"]),
                "V": float(x["V_volatility_pct"]),
                "Y": value,
                "label_reason": y.get("label_reason"),
            }
        )
    require(sum(r["Y"] is not None for r in joined) == 75, "mature count drift")
    main = evaluate(joined)
    deletion = []
    for asset, lifecycle in sorted(groups):
        removed = [
            r["case_id"] for r in joined if (r["asset"], r["lifecycle"]) == (asset, lifecycle)
        ]
        trial = evaluate([r for r in joined if r["case_id"] not in set(removed)])
        deletion.append(
            {
                "asset": asset,
                "lifecycle": lifecycle,
                "removed_case_ids": removed,
                "fixed_assets_preserved": True,
                "result": trial,
            }
        )
    return {
        "schema": "native-d-conditional-risk-result/1",
        "analysis_mode": "describe_only",
        "case_count": 76,
        "mature_count": 75,
        "unknown_case_id": UNKNOWN_ID,
        "cases": joined,
        "main": main,
        "delete_33": deletion,
        "calculation": "within-ETF average-tied-rank partial Pearson; fixed five-ETF mean",
        "budget_actual": {
            "algebraic_association_starts": 1,
            "new_prediction_fits": 0,
            "new_feature_runs": 0,
            "new_label_runs": 0,
            "account_runs": 0,
        },
        "limitations": [
            "already observed historical prices",
            "not a prediction fit",
            "not an independent-information or causal test",
            "overlapping future paths",
            "not an actual trade or account return",
        ],
    }


def validate_x(document: dict) -> list[dict]:
    require(document.get("schema") == X_SCHEMA, "saved X schema")
    rows = document.get("rows")
    require(isinstance(rows, list) and len(rows) == 76, "saved X count")
    require(len({r["case_id"] for r in rows}) == 76, "duplicate X case")
    require(sum(len(r["event_ids"]) for r in rows) == 84, "event alias count")
    require(len({(r["asset"], r["lifecycle"]) for r in rows}) == 33, "source episode count")
    require({r["asset"] for r in rows} == set(ASSETS) | {"588000.SS"}, "asset identity")
    expected_asset_counts = dict(zip(ASSETS, (15, 17, 12, 5, 26), strict=True))
    actual_asset_counts = {asset: sum(r["asset"] == asset for r in rows) for asset in ASSETS}
    require(actual_asset_counts == expected_asset_counts, "frozen per-asset count")
    require(
        sum(r["window_metadata"]["calendar_mature_by_20260626"] is True for r in rows) == 75,
        "mature X count",
    )
    unknown = [r for r in rows if r["window_metadata"]["calendar_mature_by_20260626"] is not True]
    require(
        len(unknown) == 1
        and unknown[0]["case_id"] == UNKNOWN_ID
        and unknown[0]["asset"] == "588000.SS",
        "unknown X identity",
    )
    for row in rows:
        require(row["price_basis_id"] == "economic_price", "price basis drift")
        require(
            all(
                finite(row[key]) for key in ("A", "C", "ATR20_SMA", "D_frozen", "V_volatility_pct")
            ),
            "invalid X values",
        )
        require(row["A"] > 0 and row["ATR20_SMA"] > 0, "invalid X denominator")
        require(
            math.isclose(
                (row["A"] - row["C"]) / row["ATR20_SMA"],
                row["D_frozen"],
                rel_tol=1e-10,
                abs_tol=1e-10,
            ),
            "frozen D drift",
        )
        require(
            math.isclose(
                100 * row["ATR20_SMA"] / row["A"],
                row["V_volatility_pct"],
                rel_tol=1e-10,
                abs_tol=1e-10,
            ),
            "frozen V drift",
        )
        require(
            isinstance(row["source_sha256"], list)
            and row["source_sha256"]
            and all(isinstance(s, str) and len(s) == 64 for s in row["source_sha256"]),
            "source identity missing",
        )
    return rows


def load_contract(contract_path: Path) -> tuple[dict, dict, Path]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    require(contract["schema"] == "saved-result-conditional-association/1.0", "contract schema")
    require(
        contract["analysis_mode"] == "describe_only" and contract["fixed_symbols"] == list(ASSETS),
        "contract analysis/asset drift",
    )
    plan_path = contract_path.with_name("d-output-plan.json")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    require(plan == contract["output_plan"], "external plan identity mismatch")
    require(
        plan["output"] == contract["allowed_output"]
        and plan["external_uuid"] == "DEBA1C85-6059-3865-B50A-A8EE1F80E4D9",
        "output/volume drift",
    )
    mount = Path(plan["external_mount"])
    info = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", str(mount)]))
    require(info.get("VolumeUUID", "").upper() == plan["external_uuid"], "external UUID mismatch")
    require(mount.stat().st_dev == plan["external_device"], "external device mismatch")
    output = Path(plan["output"])
    require(
        output.is_relative_to(mount) and output != mount, "output outside fixed external volume"
    )
    for parent in (output, *output.parents):
        if parent == mount:
            break
        if parent.exists():
            require(
                not parent.is_symlink()
                and parent.is_dir()
                and parent.stat().st_dev == plan["external_device"],
                "output ancestor not bound to fixed external volume",
            )
    return contract, plan, output


def resolve_ledger_path(contract_path: Path, contract: dict) -> Path:
    """Bind the one start marker to this checkout, independent of process cwd."""
    root = Path(__file__).resolve().parents[3]
    require(contract_path.resolve() == root / CONTRACT_REL, "contract location drift")
    require(contract["attempt_ledger"] == str(LEDGER_REL), "ledger location drift")
    return root / LEDGER_REL


def check_input_hashes(contract: dict) -> None:
    for kind in ("x", "y"):
        path = Path(contract["input"][f"{kind}_path"])
        require(
            path.is_file() and sha256_file(path) == contract["input"][f"{kind}_sha256"],
            f"saved {kind.upper()} hash drift",
        )


def exclusive_json(path: Path, data: dict) -> None:
    with path.open("x", encoding="utf-8") as destination:
        json.dump(data, destination, ensure_ascii=False, indent=2, allow_nan=False)
        destination.write("\n")
        destination.flush()
        os.fsync(destination.fileno())


def append_ledger_event(path: Path, event: dict) -> None:
    with path.open("r+", encoding="utf-8") as destination:
        ledger = json.load(destination)
        require(ledger["events"][0]["event"] == "core_start", "start marker missing")
        ledger["events"].append(event)
        ledger["status"] = event["event"]
        destination.seek(0)
        json.dump(ledger, destination, ensure_ascii=False, indent=2, allow_nan=False)
        destination.write("\n")
        destination.truncate()
        destination.flush()
        os.fsync(destination.fileno())


def qualify(contract_path: Path) -> dict:
    contract, plan, output = load_contract(contract_path)
    require(not resolve_ledger_path(contract_path, contract).exists(), "core already started")
    check_input_hashes(contract)  # Y bytes are hashed, never parsed in this stage.
    xrows = validate_x(json.loads(Path(contract["input"]["x_path"]).read_text(encoding="utf-8")))
    receipt = {
        "schema": "native-d-conditional-risk-qualification/1",
        "qualified": True,
        "contract_sha256": sha256_file(contract_path),
        "input_sha256": contract["input"],
        "cases": len(xrows),
        "aliases": sum(len(r["event_ids"]) for r in xrows),
        "source_episodes": len({(r["asset"], r["lifecycle"]) for r in xrows}),
        "mature_cases": 75,
        "unknown_case_id": UNKNOWN_ID,
        "real_y_values_parsed": False,
        "core_analysis_starts": 0,
    }
    require(output.is_dir(), "bound output missing; route the saved plan first")
    require(
        output.resolve().is_relative_to(Path(plan["external_mount"]).resolve())
        and output.stat().st_dev == plan["external_device"],
        "output device changed after routing",
    )
    exclusive_json(output / "qualification.json", receipt)
    return receipt


def analyze(contract_path: Path) -> dict:
    contract, _, output = load_contract(contract_path)
    ledger = resolve_ledger_path(contract_path, contract)
    check_input_hashes(contract)
    qualification_path = output / "qualification.json"
    require(qualification_path.is_file(), "qualification missing")
    qualification = json.loads(qualification_path.read_text(encoding="utf-8"))
    require(
        qualification["qualified"] is True
        and qualification["contract_sha256"] == sha256_file(contract_path)
        and qualification["real_y_values_parsed"] is False,
        "qualification drift",
    )
    xrows = validate_x(json.loads(Path(contract["input"]["x_path"]).read_text(encoding="utf-8")))
    require(not ledger.exists(), "core already started")
    ledger.parent.mkdir(parents=True, exist_ok=True)
    start = {
        "event": "core_start",
        "at": datetime.now(UTC).isoformat(),
        "contract_sha256": sha256_file(contract_path),
        "analysis_mode": "describe_only",
        "prediction_fits": 0,
        "algebraic_association_starts": 1,
    }
    exclusive_json(
        ledger,
        {
            "schema": "native-d-conditional-risk-attempt/1",
            "status": "core_start",
            "events": [start],
        },
    )  # Before parsing real Y.
    try:
        ydoc = json.loads(Path(contract["input"]["y_path"]).read_text(encoding="utf-8"))
        require(
            ydoc.get("schema") == Y_SCHEMA and ydoc.get("mature_count") == 75,
            "saved Y schema/count",
        )
        result = analyze_rows(xrows, ydoc["rows"])
        result["contract_sha256"] = sha256_file(contract_path)
        result["input_sha256"] = {
            "x": contract["input"]["x_sha256"],
            "y": contract["input"]["y_sha256"],
        }
        exclusive_json(output / "conditional-risk-result.json", result)
        append_ledger_event(
            ledger,
            {
                "event": "core_complete",
                "result_sha256": sha256_file(output / "conditional-risk-result.json"),
            },
        )
        return result
    except Exception as error:
        append_ledger_event(
            ledger,
            {"event": "core_failed", "error_type": type(error).__name__, "reason": str(error)},
        )
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    stage = parser.add_mutually_exclusive_group(required=True)
    stage.add_argument("--qualify", action="store_true")
    stage.add_argument("--analyze", action="store_true")
    parser.add_argument("--contract", required=True, type=Path)
    args = parser.parse_args()
    result = qualify(args.contract) if args.qualify else analyze(args.contract)
    print(
        json.dumps(
            {
                "stage": "qualify" if args.qualify else "analyze",
                "result": "passed",
                "cases": result["cases"] if args.qualify else result["case_count"],
                "output": json.loads(args.contract.read_text())["allowed_output"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
