"""Fixed one-shot close-MAE20 research evaluation from the accepted real X.

No import of the archived synthetic executor.  This file cannot run without a
separate parent Y grant bound to its final bytes and the completed X receipt.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import plistlib
import shutil
import statistics
import subprocess
import sys
from collections import Counter
from contextlib import suppress
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

WORKTREE = Path(
    "/Users/yongbiaoli/Desktop/lei-signal-lab/.codex/worktrees/research-direct-20261008"
)
MAIN_REPO = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
SOURCE_PATH = WORKTREE / "src/lei_signal/research/native_risk_d_mae_real_y.py"
STAGE_A_PATH = WORKTREE / "src/lei_signal/research/native_risk_d_mae_inputs.py"
STAGE_A_SHA = "5404b52f1e9ca2dc103eff37cabf51e52656d2737a8244bbb11fc2aeb63decb7"
STAGE_X_PATH = WORKTREE / "src/lei_signal/research/native_risk_d_mae_real_x.py"
STAGE_X_SHA = "1a716db72ee4ba760926fd5a7734e0deaa0cf4dd6a3d0f32543c8c0ce9e4c00b"
DESIGN_PATH = (
    MAIN_REPO
    / "docs/experiments/raw/native-risk-d-mae-2026-10-07/immutable-handoff/PROPOSED-CONTRACT.json"
)
DESIGN_SHA = "ace132ddb89de3e45951148d9673524fa9fe448f662f2576221d216bbe9717c6"
RECORD_DIR = (
    WORKTREE
    / "docs/experiments/raw/research-dispatch-controller-2026-10-07/real-y-evaluation-20261009"
)
CONTRACT_PATH = RECORD_DIR / "executor-contract.json"
CONTRACT_SHA = "2cabfc4f614921fa4cc80161e2ebabebd36c1eb74944ef20c1ba32fde59183a3"
PLAN_PATH = RECORD_DIR / "output-plan.json"
PLAN_SHA = "1f814e526bda5559299b93f8a672cf014e402e7d96fd840fa41fb5a2e938bd98"
GRANT_PATH = RECORD_DIR / "real-y-grant.json"
LEDGER_PATH = RECORD_DIR / "real-y-attempt.jsonl"
X_RECORD_DIR = (
    WORKTREE / "docs/experiments/raw/research-dispatch-controller-2026-10-07/real-x-seal-20261009"
)
X_GRANT_PATH = X_RECORD_DIR / "real-x-grant.json"
X_LEDGER_PATH = X_RECORD_DIR / "real-x-attempt.jsonl"
X_DIR = Path(
    "/Volumes/win+mac通用/LeiSignal-新实验结果/research-dispatch-controller/research-dispatch-controller-20261009T121052-8c15af8c4cb6/result/real-x"
)
X_PATH = X_DIR / "x-rows.json"
X_RECEIPT_PATH = X_DIR / "receipt.json"
X_SHA = "6ae79d580fa98ba81b8f071d73e9eac0e3127ea8e66275967fecb1f218aa989a"
X_RECEIPT_SHA = "41ad1a478bc9e4f92566453d87bbff7c77c55f4cdcb5a39e2bdd5a652cbedac8"
X_GRANT_SHA = "9e4be95562ac5f7a338ce00380328ec32532ace695177a5b25713e3a7fb2bcce"
X_MEMBERSHIP_SHA = "476bb769ba1556e8fdf76d7300ae6001f5760750fbf1db9c36be0c0e14ef6418"
PRICE_PATH = (
    MAIN_REPO / "docs/experiments/raw/six-etf-x-only-input-package-2026-10-06/raw-six-ohlcv.json"
)
PRICE_SHA = "4e350efea9403dccb4bc4f7fcc66e22ea6bf3d6e72b0c044b9f44d631c78415f"
CALENDAR_PATH = (
    MAIN_REPO
    / "docs/experiments/raw/research-calendar-completion-2026-09-10/calendar-merged/calendar.json"
)
CALENDAR_SHA = "aa43736b67bbcee04fc21eedf8d510b184b764adf138456c8bce93a3155eb6c1"
MOUNT = Path("/Volumes/win+mac通用")
MOUNT_UUID = "DEBA1C85-6059-3865-B50A-A8EE1F80E4D9"
MOUNT_DEVICE = 16777238
OUTPUT = Path(
    "/Volumes/win+mac通用/LeiSignal-新实验结果/research-dispatch-controller/research-dispatch-controller-20261009T122325-87e142670e36/result"
)
REAL_Y_DIR = OUTPUT / "real-y"
CUTOFF = "2026-06-26"
UNKNOWN_ID = "case:ded0d0c43677a76957f4"
ASSETS = ("510050.SS", "510300.SS", "510500.SS", "512400.SS", "512800.SS", "588000.SS")
MATURE_COUNTS = {"510050.SS": 15, "510300.SS": 17, "510500.SS": 12, "512400.SS": 5, "512800.SS": 26}
PERMISSIONS = {
    "real_Y_passes": 1,
    "max_label_cases": 75,
    "max_future_close_observations": 1575,
    "fits": 0,
    "searches": 0,
    "extra_windows": 0,
    "auto_retries": 0,
}
GRANT_KEYS = {
    "schema",
    "approved",
    "stage",
    "design_sha256",
    "executor_contract_sha256",
    "stage_a_sha256",
    "stage_x_sha256",
    "executable_sha256",
    "x_sha256",
    "x_receipt_sha256",
    "x_grant_sha256",
    "x_ledger_sha256",
    "membership_sha256",
    "original_sha256",
    "prices_sha256",
    "calendar_sha256",
    "output_plan_sha256",
    "output",
    "real_y_directory",
    "external_mount",
    "external_device",
    "external_uuid",
    "ledger_path",
    "permissions",
}


class RealYError(ValueError):
    """A frozen input, path, grant, label, or result check failed."""


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise RealYError(message)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _encode(value: Any) -> bytes:
    return (
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        + "\n"
    ).encode("utf-8")


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        _need(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise RealYError(f"nonfinite JSON constant: {value}")


def _json(raw: bytes, name: str) -> Any:
    try:
        value = json.loads(raw, object_pairs_hook=_unique_pairs, parse_constant=_reject_constant)
    except (ValueError, UnicodeError) as exc:
        raise RealYError(f"invalid JSON in {name}: {exc}") from exc

    def finite(node: Any) -> None:
        if isinstance(node, float):
            _need(math.isfinite(node), f"nonfinite JSON number in {name}")
        elif isinstance(node, dict):
            for child in node.values():
                finite(child)
        elif isinstance(node, list):
            for child in node:
                finite(child)

    finite(value)
    return value


def _plain(path: Path) -> None:
    _need(path.is_absolute() and ".." not in path.parts, f"unsafe path: {path}")
    for item in (path, *path.parents):
        if item == Path("/"):
            break
        _need(not item.is_symlink(), f"unexpected symlink: {item}")


def _read_fixed(path: Path, expected: str) -> bytes:
    _plain(path)
    _need(path.is_file(), f"missing fixed file: {path}")
    raw = path.read_bytes()
    _need(_sha(raw) == expected, f"fixed file SHA mismatch: {path}")
    return raw


def _membership_sha(rows: list[dict[str, Any]]) -> str:
    members = [
        {
            key: row[key]
            for key in (
                "case_id",
                "asset",
                "signal_date",
                "lifecycle",
                "event_ids",
                "event_ma_period",
            )
        }
        for row in rows
    ]
    _need(
        len(members) == 76
        and len({r["case_id"] for r in members}) == 76
        and sum(len(r["event_ids"]) for r in members) == 84,
        "X membership count or identity mismatch",
    )
    return _sha(_encode(sorted(members, key=lambda r: r["case_id"])))


def _load_x(grant: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Bind accepted X, receipt, parent grant, and completed one-shot ledger."""
    _read_fixed(STAGE_A_PATH, STAGE_A_SHA)
    _read_fixed(STAGE_X_PATH, STAGE_X_SHA)
    _read_fixed(X_GRANT_PATH, X_GRANT_SHA)
    x = _json(_read_fixed(X_PATH, X_SHA), "sealed X")
    receipt = _json(_read_fixed(X_RECEIPT_PATH, X_RECEIPT_SHA), "X receipt")
    ledger_raw = _read_fixed(X_LEDGER_PATH, grant["x_ledger_sha256"])
    entries = [_json(line, "X ledger line") for line in ledger_raw.splitlines()]
    _need(
        len(entries) == 2
        and entries[0].get("status") == "started"
        and entries[1].get("status") == "completed"
        and entries[0].get("grant_sha256") == X_GRANT_SHA
        and entries[1].get("x_sha256") == X_SHA
        and entries[1].get("receipt_sha256") == X_RECEIPT_SHA,
        "X one-shot ledger not completed or differs",
    )
    _need(
        x.get("schema") == "native-risk-d-mae-real-x/1"
        and x.get("status") == "real_x_only_no_y"
        and x.get("design_sha256") == DESIGN_SHA
        and x.get("adapter_sha256") == STAGE_A_SHA
        and x.get("executable_sha256") == STAGE_X_SHA
        and x.get("grant_sha256") == X_GRANT_SHA
        and x.get("membership_sha256") == X_MEMBERSHIP_SHA
        and x.get("real_Y_passes") == 0
        and receipt.get("schema") == "native-risk-d-mae-real-x-receipt/1"
        and receipt.get("status") == "x_sealed_only"
        and receipt.get("x_sha256") == X_SHA
        and receipt.get("grant_sha256") == X_GRANT_SHA
        and receipt.get("membership_sha256") == X_MEMBERSHIP_SHA,
        "X/receipt binding differs",
    )
    _need(
        isinstance(x.get("original_sha256"), dict)
        and x["original_sha256"] == receipt.get("original_sha256")
        and x["original_sha256"] == grant["original_sha256"]
        and x.get("window_metadata_sha256") == receipt.get("window_metadata_sha256"),
        "X original six-source or window binding differs",
    )
    rows = x.get("rows")
    _need(
        isinstance(rows, list)
        and len(rows) == 76
        and _membership_sha(rows) == X_MEMBERSHIP_SHA
        and len({(r["asset"], r["lifecycle"]) for r in rows}) == 33
        and sum(r["case_id"] == UNKNOWN_ID for r in rows) == 1,
        "X population differs",
    )
    _need(
        all(
            r["price_basis_id"] == "economic_price"
            and r["source_sha256"][0] == PRICE_SHA
            and r["source_sha256"][1] == CALENDAR_SHA
            for r in rows
        ),
        "X source or price basis differs",
    )
    _need(
        receipt.get("row_count") == 76
        and receipt.get("event_memberships") == 84
        and receipt.get("asset_lifecycle_groups") == 33
        and receipt.get("unknown_case_id") == UNKNOWN_ID,
        "X receipt counts differ",
    )
    return x, receipt, _sha(ledger_raw)


def _validate_grant(grant: Any, plan: dict[str, Any], code_sha: str) -> None:
    _need(isinstance(grant, dict) and set(grant) == GRANT_KEYS, "Y grant fields differ")
    _need(
        grant["schema"] == "native-risk-d-mae-real-y-grant/1"
        and grant["approved"] is True
        and grant["stage"] == "real_y",
        "missing or invalid Y grant",
    )
    fixed = {
        "design_sha256": DESIGN_SHA,
        "executor_contract_sha256": CONTRACT_SHA,
        "stage_a_sha256": STAGE_A_SHA,
        "stage_x_sha256": STAGE_X_SHA,
        "executable_sha256": code_sha,
        "x_sha256": X_SHA,
        "x_receipt_sha256": X_RECEIPT_SHA,
        "x_grant_sha256": X_GRANT_SHA,
        "membership_sha256": X_MEMBERSHIP_SHA,
        "prices_sha256": PRICE_SHA,
        "calendar_sha256": CALENDAR_SHA,
        "output_plan_sha256": PLAN_SHA,
        "output": str(OUTPUT),
        "real_y_directory": str(REAL_Y_DIR),
        "external_mount": str(MOUNT),
        "external_uuid": MOUNT_UUID,
        "ledger_path": str(LEDGER_PATH),
    }
    _need(
        all(grant[key] == value for key, value in fixed.items())
        and isinstance(grant["x_ledger_sha256"], str)
        and len(grant["x_ledger_sha256"]) == 64
        and plan["output"] == str(OUTPUT)
        and plan["external_uuid"] == MOUNT_UUID
        and type(grant["external_device"]) is int
        and grant["external_device"] == plan["external_device"] == MOUNT_DEVICE,
        "Y grant code/source/X/output binding differs",
    )
    permissions = grant["permissions"]
    _need(
        isinstance(permissions, dict)
        and set(permissions) == set(PERMISSIONS)
        and all(
            type(permissions[k]) is int and permissions[k] == v for k, v in PERMISSIONS.items()
        ),
        "Y grant permissions differ",
    )


def _storage_preflight(plan: dict[str, Any]) -> None:
    _need(
        plan["schema_version"] == 1
        and plan["task_id"] == "research-dispatch-controller"
        and plan["run_id"] == "research-dispatch-controller-20261009T122325-87e142670e36"
        and plan["run_directory"] == str(OUTPUT.parent)
        and plan["output"] == str(OUTPUT)
        and plan["execution_authorized"] is False
        and plan["quota_enforced"] is False,
        "fixed Y output plan differs; plan-only is not research authority",
    )
    for path in (
        MOUNT,
        OUTPUT,
        REAL_Y_DIR,
        OUTPUT.parent,
        OUTPUT.parent.parent,
        X_PATH,
        X_RECEIPT_PATH,
        LEDGER_PATH,
    ):
        _plain(path)
    _need(os.path.ismount(MOUNT), "registered external mount missing")
    try:
        info = plistlib.loads(
            subprocess.check_output(
                ["/usr/sbin/diskutil", "info", "-plist", str(MOUNT)], timeout=10
            )
        )
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        raise RealYError(f"external disk identity unavailable: {exc}") from exc
    _need(
        info.get("MountPoint") == str(MOUNT)
        and info.get("VolumeUUID") == MOUNT_UUID
        and info.get("Internal") is False
        and info.get("Writable") is True,
        "external UUID or writable state mismatch",
    )
    _need(
        MOUNT.stat().st_dev == MOUNT_DEVICE
        and OUTPUT.parent.parent.stat().st_dev == MOUNT_DEVICE
        and X_PATH.stat().st_dev == MOUNT_DEVICE
        and MAIN_REPO.stat().st_dev != MOUNT_DEVICE,
        "external device mismatch",
    )
    _need(not REAL_Y_DIR.exists(), "real Y output directory already exists")
    _need(
        shutil.disk_usage(MOUNT).free >= plan["external_reserve_bytes"] + plan["estimated_bytes"]
        and shutil.disk_usage(MAIN_REPO).free
        >= plan["internal_reserve_bytes"] + plan["internal_metadata_bytes"],
        "insufficient external or internal space",
    )


def _iso(value: Any, label: str) -> str:
    _need(isinstance(value, str), f"invalid date: {label}")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise RealYError(f"invalid date: {label}") from exc
    _need(parsed.isoformat() == value, f"noncanonical date: {label}")
    return value


def _parse_sources(
    price_raw: bytes, calendar_raw: bytes
) -> tuple[list[str], dict[tuple[str, str], Any]]:
    """Parse exact original shapes; skip post-cutoff price values before path selection."""
    prices = _json(price_raw, "raw-six-ohlcv")
    calendar = _json(calendar_raw, "retained calendar")
    _need(isinstance(prices, dict) and isinstance(calendar, dict), "original source schema differs")
    bars = prices.get("bars") if isinstance(prices, dict) else None
    days = calendar.get("days") if isinstance(calendar, dict) else None
    _need(
        isinstance(bars, list) and len(bars) == 8022,
        "original price schema or 8022-row count differs",
    )
    _need(
        calendar.get("schema_version") == "research-trading-calendar/1.1"
        and isinstance(days, dict)
        and len(days) == 2495,
        "original calendar schema or 2495-day count differs",
    )
    retained = []
    for day, record in days.items():
        _iso(day, "calendar day")
        _need(
            isinstance(record, dict)
            and type(record.get("is_trading_day")) is bool
            and isinstance(record.get("source_flag"), str)
            and isinstance(record.get("source_month"), str),
            f"calendar record invalid: {day}",
        )
        if day <= CUTOFF and record["is_trading_day"]:
            retained.append(day)
    retained.sort()
    _need(retained and retained == sorted(set(retained)), "retained calendar invalid")
    closes: dict[tuple[str, str], Any] = {}
    all_keys = set()
    for row in bars:
        _need(
            isinstance(row, dict)
            and all(k in row for k in ("asset", "date", "open", "high", "low", "close", "volume")),
            "original price row schema differs",
        )
        asset, day = row["asset"], _iso(row["date"], "bar date")
        _need(
            asset in ASSETS and (asset, day) not in all_keys,
            f"duplicate/invalid asset-date bar: {asset}/{day}",
        )
        all_keys.add((asset, day))
        if day <= CUTOFF:
            closes[(asset, day)] = row["close"]
    return retained, closes


def _positive(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def _finite(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _validate_paths(
    rows: list[dict[str, Any]], retained: list[str], closes: dict[tuple[str, str], Any]
) -> tuple[dict[str, dict[str, Any]], str]:
    """Qualify ALL 75 paths before a caller may calculate any Y."""
    _need(
        len(rows) == 76
        and retained == sorted(set(retained))
        and all(d <= CUTOFF for d in retained),
        "X or calendar population invalid",
    )
    positions = {day: i for i, day in enumerate(retained)}
    paths: dict[str, dict[str, Any]] = {}
    unknown: list[str] = []
    seen = set()
    for row in rows:
        cid, asset, signal = row["case_id"], row["asset"], row["signal_date"]
        _need(
            (asset, signal) not in seen and signal in positions,
            f"duplicate X asset/date or absent signal calendar: {cid}",
        )
        seen.add((asset, signal))
        meta = row["window_metadata"]
        _need(
            isinstance(meta, dict) and type(meta.get("calendar_mature_by_20260626")) is bool,
            f"window metadata invalid: {cid}",
        )
        future = retained[positions[signal] + 1 : positions[signal] + 22]
        _need(
            bool(future) and future[0] == meta.get("label_start"),
            f"t+1 window start differs: {cid}",
        )
        if not meta["calendar_mature_by_20260626"]:
            _need(
                cid == UNKNOWN_ID
                and asset == "588000.SS"
                and signal == "2026-06-16"
                and meta.get("label_end") is None
                and meta.get("reason") == "end_beyond_frozen_calendar"
                and len(future) < 21,
                f"unknown cutoff identity contradicts calendar: {cid}",
            )
            unknown.append(cid)
            continue
        _need(
            len(future) == 21 and future[-1] == meta.get("label_end") and future[-1] <= CUTOFF,
            f"21-session end/cutoff differs: {cid}",
        )
        values = [closes.get((asset, day)) for day in future]
        _need(
            all(_positive(value) for value in values),
            f"missing/nonfinite/nonpositive full 21-close path: {cid}",
        )
        paths[cid] = {"asset": asset, "signal_date": signal, "dates": future, "closes": values}
    counts = dict(Counter(path["asset"] for path in paths.values()))
    _need(
        len(paths) == 75
        and unknown == [UNKNOWN_ID]
        and counts == MATURE_COUNTS
        and sum(len(path["closes"]) for path in paths.values()) == 1575,
        "fixed 75-path/1575-close population differs",
    )
    return paths, unknown[0]


def _mae(closes: list[float]) -> float:
    _need(
        len(closes) == 21 and all(_positive(v) for v in closes),
        "MAE needs exactly 21 positive finite closes",
    )
    return max(0.0, 100.0 * (1.0 - min(closes) / closes[0]))


def _ranks(values: list[float]) -> list[float]:
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


def _rho(x: list[float], y: list[float]) -> float | None:
    if len(x) != len(y) or len(x) < 2:
        return None
    a, b = _ranks(x), _ranks(y)
    am, bm = statistics.mean(a), statistics.mean(b)
    aa, bb = sum((v - am) ** 2 for v in a), sum((v - bm) ** 2 for v in b)
    if not aa or not bb:
        return None
    return sum((v - am) * (w - bm) for v, w in zip(a, b, strict=True)) / math.sqrt(aa * bb)


def _per_asset(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {}
    for asset in ASSETS:
        selected = [r for r in rows if r["asset"] == asset]
        complete = [
            r
            for r in selected
            if all(_finite(r.get(k)) for k in ("D_frozen", "V_volatility_pct", "Y"))
        ]
        d, v, y = ([r[k] for r in complete] for k in ("D_frozen", "V_volatility_pct", "Y"))
        rd, rv = _rho(d, y), _rho(v, y)
        result[asset] = {
            "all_cases": len(selected),
            "complete_cases": len(complete),
            "complete_case_ids": [r["case_id"] for r in complete],
            "asset_lifecycle_groups": len({r["lifecycle"] for r in selected}),
            "complete_asset_lifecycle_groups": len({r["lifecycle"] for r in complete}),
            "distinct_D": len(set(d)),
            "distinct_V": len(set(v)),
            "distinct_Y": len(set(y)),
            "mae_mean": statistics.mean(y) if y else None,
            "mae_median": statistics.median(y) if y else None,
            "mae_zero_count": sum(value == 0 for value in y),
            "rho_D_Y": rd,
            "rho_V_Y": rv,
            "rho_D_minus_V": rd - rv if rd is not None and rv is not None else None,
            "n2_degenerate": len(complete) == 2,
            "reason": "n_lt_2"
            if len(complete) < 2
            else "constant_rank"
            if rd is None or rv is None
            else None,
        }
    return result


def _fixed_global(per_asset: dict[str, dict[str, Any]], fixed: tuple[str, ...]) -> dict[str, Any]:
    if not fixed:
        return {
            "fixed_assets": [],
            "asset_count": 0,
            "case_count": 0,
            "rho_D_Y": None,
            "rho_V_Y": None,
            "rho_D_minus_V": None,
            "reason": "no_common_computable_asset",
        }
    if any(per_asset[a]["rho_D_Y"] is None or per_asset[a]["rho_V_Y"] is None for a in fixed):
        return {
            "fixed_assets": list(fixed),
            "asset_count": len(fixed),
            "case_count": sum(per_asset[a]["complete_cases"] for a in fixed),
            "rho_D_Y": None,
            "rho_V_Y": None,
            "rho_D_minus_V": None,
            "reason": "fixed_asset_became_uncomputable",
        }
    rd = statistics.mean(per_asset[a]["rho_D_Y"] for a in fixed)
    rv = statistics.mean(per_asset[a]["rho_V_Y"] for a in fixed)
    return {
        "fixed_assets": list(fixed),
        "asset_count": len(fixed),
        "case_count": sum(per_asset[a]["complete_cases"] for a in fixed),
        "rho_D_Y": rd,
        "rho_V_Y": rv,
        "rho_D_minus_V": rd - rv,
        "reason": None,
    }


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    _need(
        len(rows) == 76 and len({r["case_id"] for r in rows}) == 76,
        "statistics require original 76 cases",
    )
    groups = sorted({(r["asset"], r["lifecycle"]) for r in rows})
    _need(len(groups) == 33, "statistics require original 33 groups")
    per_asset = _per_asset(rows)
    fixed = tuple(
        a
        for a in ASSETS
        if per_asset[a]["rho_D_Y"] is not None and per_asset[a]["rho_V_Y"] is not None
    )
    primary = _fixed_global(per_asset, fixed)
    deleted = []
    for asset, lifecycle in groups:
        removed = [r["case_id"] for r in rows if (r["asset"], r["lifecycle"]) == (asset, lifecycle)]
        rest = [r for r in rows if (r["asset"], r["lifecycle"]) != (asset, lifecycle)]
        per = _per_asset(rest)
        deleted.append(
            {
                "deleted_asset": asset,
                "deleted_lifecycle": lifecycle,
                "deleted_case_ids": removed,
                "per_asset": per,
                "fixed_asset_summary": _fixed_global(per, fixed),
            }
        )
    return {
        "per_asset": per_asset,
        "primary": primary,
        "leave_one_lifecycle": deleted,
        "interpretation": (
            "signed rank association difference; not conditional increment or trading performance"
        ),
    }


def _evaluate(
    rows: list[dict[str, Any]], paths: dict[str, dict[str, Any]], unknown: str
) -> dict[str, Any]:
    _need(len(paths) == 75 and unknown == UNKNOWN_ID, "Y paths not fully qualified")
    result = []
    for row in rows:
        cid = row["case_id"]
        path = paths.get(cid)
        y = _mae(path["closes"]) if path is not None else None
        _need(path is not None or cid == unknown, f"missing qualified path: {cid}")
        result.append(
            {
                **row,
                "Y": y,
                "label_reason": None if path else "end_beyond_frozen_calendar",
                "label_start": path["dates"][0] if path else row["window_metadata"]["label_start"],
                "label_end": path["dates"][-1] if path else None,
            }
        )
    return {
        "rows": result,
        "paths": [dict(case_id=cid, **paths[cid]) for cid in sorted(paths)],
        "unknown_case_id": unknown,
        "mature_count": 75,
        "statistics": _summarize(result),
    }


def _start_ledger(path: Path, entry: dict[str, Any]) -> None:
    _plain(path)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise RealYError("Y pass already consumed; no retry or alternate output") from exc
    with os.fdopen(fd, "wb", buffering=0) as handle:
        handle.write(_encode(entry))
        os.fsync(handle.fileno())


def _append(entry: dict[str, Any]) -> None:
    with LEDGER_PATH.open("ab", buffering=0) as handle:
        handle.write(_encode(entry))
        os.fsync(handle.fileno())


def _write(path: Path, raw: bytes) -> None:
    _plain(path)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise RealYError(f"output already exists: {path}") from exc
    with os.fdopen(fd, "wb", buffering=0) as handle:
        handle.write(raw)
        os.fsync(handle.fileno())


def _readback(path: Path, expected: str) -> None:
    _plain(path)
    _need(
        path.is_file()
        and path.stat().st_dev == MOUNT_DEVICE
        and _sha(path.read_bytes()) == expected,
        f"written result readback differs: {path}",
    )


def run_real_y() -> dict[str, Any]:
    """Only production entry; all source bytes and authority fixed before one start."""
    _need(Path(__file__).absolute() == SOURCE_PATH, "executable path differs")
    code_sha = _sha(SOURCE_PATH.read_bytes())
    _read_fixed(DESIGN_PATH, DESIGN_SHA)
    _read_fixed(CONTRACT_PATH, CONTRACT_SHA)
    plan = _json(_read_fixed(PLAN_PATH, PLAN_SHA), "Y output plan")
    _plain(GRANT_PATH)
    _need(GRANT_PATH.is_file(), "missing parent Y grant")
    grant_raw = GRANT_PATH.read_bytes()
    grant = _json(grant_raw, "Y grant")
    _validate_grant(grant, plan, code_sha)
    x, x_receipt, x_ledger_sha = _load_x(grant)
    _need(x_ledger_sha == grant["x_ledger_sha256"], "X ledger hash differs")
    _storage_preflight(plan)
    price_raw = _read_fixed(PRICE_PATH, PRICE_SHA)
    calendar_raw = _read_fixed(CALENDAR_PATH, CALENDAR_SHA)
    _need(_sha(GRANT_PATH.read_bytes()) == _sha(grant_raw), "Y grant changed before start")
    _need(not LEDGER_PATH.exists(), "Y pass already consumed")
    started = {
        "status": "started",
        "at": datetime.now(UTC).isoformat(),
        "grant_sha256": _sha(grant_raw),
        "code_sha256": code_sha,
        "x_sha256": X_SHA,
        "x_receipt_sha256": X_RECEIPT_SHA,
        "x_ledger_sha256": x_ledger_sha,
        "membership_sha256": X_MEMBERSHIP_SHA,
        "prices_sha256": PRICE_SHA,
        "calendar_sha256": CALENDAR_SHA,
        "output": str(REAL_Y_DIR),
        "pass": 1,
    }
    _start_ledger(LEDGER_PATH, started)
    try:
        retained, closes = _parse_sources(price_raw, calendar_raw)
        paths, unknown = _validate_paths(x["rows"], retained, closes)
        evaluated = _evaluate(x["rows"], paths, unknown)
        _storage_preflight(plan)
        payload = {
            "schema": "native-risk-d-mae-real-y/1",
            "status": "descriptive_y_only",
            "design_sha256": DESIGN_SHA,
            "executor_contract_sha256": CONTRACT_SHA,
            "executable_sha256": code_sha,
            "grant_sha256": _sha(grant_raw),
            "output_plan_sha256": PLAN_SHA,
            "stage_a_sha256": STAGE_A_SHA,
            "stage_x_sha256": STAGE_X_SHA,
            "x_sha256": X_SHA,
            "x_receipt_sha256": X_RECEIPT_SHA,
            "x_grant_sha256": X_GRANT_SHA,
            "x_ledger_sha256": x_ledger_sha,
            "membership_sha256": X_MEMBERSHIP_SHA,
            "original_sha256": x["original_sha256"],
            "window_metadata_sha256": x["window_metadata_sha256"],
            "prices_sha256": PRICE_SHA,
            "calendar_sha256": CALENDAR_SHA,
            "price_basis": "saved_economic_price_current_vintage",
            "source_arrival": "unknown",
            "calendar_limit": "SZSE proxy for SSE unverified",
            "label": "close_MAE20_t_plus_1_to_21_21_closes_20_intervals",
            "fits": 0,
            "trading_claim": False,
            **evaluated,
        }
        OUTPUT.parent.mkdir(exist_ok=True)
        OUTPUT.mkdir(exist_ok=True)
        REAL_Y_DIR.mkdir(exist_ok=False)
        _plain(REAL_Y_DIR)
        _need(REAL_Y_DIR.stat().st_dev == MOUNT_DEVICE, "external device changed after start")
        result_raw = _encode(payload)
        _write(REAL_Y_DIR / "y-result.json", result_raw)
        _readback(REAL_Y_DIR / "y-result.json", _sha(result_raw))
        receipt = {
            "schema": "native-risk-d-mae-real-y-receipt/1",
            "status": "descriptive_y_sealed_pending_independent_review",
            "sealed_at": datetime.now(UTC).isoformat(),
            "result_path": str(REAL_Y_DIR / "y-result.json"),
            "result_sha256": _sha(result_raw),
            "grant_sha256": _sha(grant_raw),
            "executable_sha256": code_sha,
            "design_sha256": DESIGN_SHA,
            "executor_contract_sha256": CONTRACT_SHA,
            "output_plan_sha256": PLAN_SHA,
            "stage_a_sha256": STAGE_A_SHA,
            "stage_x_sha256": STAGE_X_SHA,
            "x_sha256": X_SHA,
            "x_receipt_sha256": X_RECEIPT_SHA,
            "x_grant_sha256": X_GRANT_SHA,
            "x_ledger_sha256": x_ledger_sha,
            "membership_sha256": X_MEMBERSHIP_SHA,
            "original_sha256": x["original_sha256"],
            "window_metadata_sha256": x["window_metadata_sha256"],
            "prices_sha256": PRICE_SHA,
            "calendar_sha256": CALENDAR_SHA,
            "rows": 76,
            "mature_paths": 75,
            "future_closes": 1575,
            "unknown_case_id": UNKNOWN_ID,
            "fits": 0,
            "effect_or_trading_claim": False,
        }
        receipt_raw = _encode(receipt)
        _write(REAL_Y_DIR / "receipt.json", receipt_raw)
        _readback(REAL_Y_DIR / "receipt.json", _sha(receipt_raw))
        _append(
            {
                "status": "completed",
                "at": datetime.now(UTC).isoformat(),
                "result_sha256": _sha(result_raw),
                "receipt_sha256": _sha(receipt_raw),
            }
        )
        return receipt
    except BaseException as exc:
        # The exclusive started record still prevents replay if this append fails.
        with suppress(OSError):
            _append(
                {
                    "status": "failed",
                    "at": datetime.now(UTC).isoformat(),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
        raise


def main() -> int:
    _need(len(sys.argv) == 1, "fixed Y entry accepts no override arguments")
    receipt = run_real_y()
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "receipt": str(REAL_Y_DIR / "receipt.json"),
                "result_sha256": receipt["result_sha256"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
