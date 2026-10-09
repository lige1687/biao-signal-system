"""One-shot real D/V X seal.  No Y, future prices, fitting, or trading.

Production has one fixed entry and no caller-supplied files or loaders.  A
separate controller grant must bind this final source before it can run.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import plistlib
import shutil
import subprocess
import sys
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

WORKTREE = Path(
    "/Users/yongbiaoli/Desktop/lei-signal-lab/.codex/worktrees/research-direct-20261008"
)
MAIN_REPO = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
SOURCE_PATH = WORKTREE / "src/lei_signal/research/native_risk_d_mae_real_x.py"
ADAPTER_PATH = WORKTREE / "src/lei_signal/research/native_risk_d_mae_inputs.py"
ADAPTER_SHA256 = "5404b52f1e9ca2dc103eff37cabf51e52656d2737a8244bbb11fc2aeb63decb7"
DESIGN_PATH = (
    MAIN_REPO
    / "docs/experiments/raw/native-risk-d-mae-2026-10-07/immutable-handoff/PROPOSED-CONTRACT.json"
)
DESIGN_SHA256 = "ace132ddb89de3e45951148d9673524fa9fe448f662f2576221d216bbe9717c6"
RECORD_DIR = (
    WORKTREE / "docs/experiments/raw/research-dispatch-controller-2026-10-07/real-x-seal-20261009"
)
CONTRACT_PATH = RECORD_DIR / "executor-contract.json"
CONTRACT_SHA256 = "c1d1689c8657707ad63f1127d9cab0250cf8a6d33cc3e2eec544c4ed03e3c7d2"
PLAN_PATH = RECORD_DIR / "output-plan.json"
PLAN_SHA256 = "91d788d14f38a75350d2bafb6b9154fd6b9f4a9d3fef1128dab590e72fb21dc8"
GRANT_PATH = RECORD_DIR / "real-x-grant.json"
LEDGER_PATH = RECORD_DIR / "real-x-attempt.jsonl"
EXTERNAL_MOUNT = Path("/Volumes/win+mac通用")
EXTERNAL_UUID = "DEBA1C85-6059-3865-B50A-A8EE1F80E4D9"
EXTERNAL_DEVICE = 16777238
OUTPUT_PATH = Path(
    "/Volumes/win+mac通用/LeiSignal-新实验结果/research-dispatch-controller/"
    "research-dispatch-controller-20261009T121052-8c15af8c4cb6/result"
)
REAL_X_DIR = OUTPUT_PATH / "real-x"
UNKNOWN_CASE_ID = "case:ded0d0c43677a76957f4"
EXPECTED_COUNTS = {
    "cases": 76,
    "events": 84,
    "long_rows": 336,
    "D_rows": 84,
    "asset_lifecycle_groups": 33,
    "calendar_mature": 75,
    "calendar_unknown": 1,
}
PERMISSIONS = {
    "real_X_passes": 1,
    "V_passes": 1,
    "real_Y_passes": 0,
    "fits": 0,
    "future_price_reads": 0,
    "external_requests": 0,
}
GRANT_KEYS = {
    "schema",
    "approved",
    "stage",
    "design_sha256",
    "executor_contract_sha256",
    "adapter_sha256",
    "executable_sha256",
    "input_sha256",
    "membership_sha256",
    "output_plan_sha256",
    "output",
    "real_x_directory",
    "external_mount",
    "external_device",
    "external_uuid",
    "ledger_path",
    "permissions",
}


class RealXError(ValueError):
    """A real X safety, source, grant, or one-shot check failed."""


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise RealXError(message)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        + "\n"
    ).encode("utf-8")


def _pairs_unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        _require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise RealXError(f"nonfinite JSON constant: {value}")


def _strict_json(raw: bytes, label: str) -> Any:
    try:
        value = json.loads(raw, object_pairs_hook=_pairs_unique, parse_constant=_reject_constant)
    except (ValueError, UnicodeError) as exc:
        raise RealXError(f"invalid JSON in {label}: {exc}") from exc

    def finite(node: Any) -> None:
        if isinstance(node, float):
            _require(math.isfinite(node), f"nonfinite JSON number in {label}")
        elif isinstance(node, dict):
            for child in node.values():
                finite(child)
        elif isinstance(node, list):
            for child in node:
                finite(child)

    finite(value)
    return value


def _no_symlinks(path: Path) -> None:
    _require(path.is_absolute() and ".." not in path.parts, f"unsafe path: {path}")
    for parent in (path, *path.parents):
        if parent == Path("/"):
            break
        _require(not parent.is_symlink(), f"unexpected symlink: {parent}")


def _read_fixed(path: Path, expected: str) -> bytes:
    _no_symlinks(path)
    _require(path.is_file(), f"missing fixed file: {path}")
    raw = path.read_bytes()
    _require(_sha(raw) == expected, f"fixed file SHA256 mismatch: {path}")
    return raw


def _load_adapter_identity() -> dict[str, Any]:
    """Use only the accepted public loader, after verifying its exact bytes."""
    _read_fixed(ADAPTER_PATH, ADAPTER_SHA256)
    spec = importlib.util.spec_from_file_location("native_risk_d_mae_inputs", ADAPTER_PATH)
    _require(spec is not None and spec.loader is not None, "cannot load accepted adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.load_original_identity()


def _membership_sha(identity: dict[str, Any]) -> str:
    _require(
        identity.get("status") == "identity_qualified_only"
        and identity.get("counts") == EXPECTED_COUNTS
        and identity.get("unknown_case_id") == UNKNOWN_CASE_ID,
        "accepted identity population differs",
    )
    cases = identity["cases"]
    _require(isinstance(cases, list) and len(cases) == 76, "identity cases missing")
    members = [
        {
            key: case[key]
            for key in (
                "case_id",
                "asset",
                "signal_date",
                "lifecycle",
                "event_ids",
                "event_ma_period",
            )
        }
        for case in cases
    ]
    ids = [case["case_id"] for case in members]
    _require(len(set(ids)) == 76, "duplicate case identity")
    _require(
        sum(len(case["event_ids"]) for case in members) == 84, "event membership count differs"
    )
    return _sha(_canonical(sorted(members, key=lambda item: item["case_id"])))


def _validate_grant(
    grant: Any, *, plan: dict[str, Any], identity: dict[str, Any], code_sha: str
) -> None:
    """Pure validation for artificial tests; production supplies fixed verified files."""
    _require(isinstance(grant, dict) and set(grant) == GRANT_KEYS, "grant fields differ")
    _require(
        grant["schema"] == "native-risk-d-mae-real-x-grant/1"
        and grant["approved"] is True
        and grant["stage"] == "real_x",
        "missing or invalid X grant",
    )
    _require(
        grant["design_sha256"] == DESIGN_SHA256
        and grant["executor_contract_sha256"] == CONTRACT_SHA256
        and grant["adapter_sha256"] == ADAPTER_SHA256
        and grant["executable_sha256"] == code_sha,
        "grant code or contract hash mismatch",
    )
    _require(
        grant["input_sha256"] == identity["original_sha256"]
        and grant["membership_sha256"] == _membership_sha(identity),
        "grant input or member hash mismatch",
    )
    _require(
        grant["output_plan_sha256"] == PLAN_SHA256
        and grant["output"] == plan["output"] == str(OUTPUT_PATH)
        and grant["real_x_directory"] == str(REAL_X_DIR)
        and grant["external_mount"] == plan["external_mount"] == str(EXTERNAL_MOUNT)
        and type(grant["external_device"]) is int
        and grant["external_device"] == plan["external_device"] == EXTERNAL_DEVICE
        and grant["external_uuid"] == plan["external_uuid"] == EXTERNAL_UUID
        and grant["ledger_path"] == str(LEDGER_PATH),
        "grant output, device, plan or ledger mismatch",
    )
    permissions = grant["permissions"]
    _require(
        isinstance(permissions, dict)
        and set(permissions) == set(PERMISSIONS)
        and all(
            type(permissions[key]) is int and permissions[key] == value
            for key, value in PERMISSIONS.items()
        ),
        "grant permissions differ",
    )


def _storage_preflight(plan: dict[str, Any]) -> None:
    """Mirror the registered output policy at this fixed route immediately before start."""
    _require(
        plan["schema_version"] == 1
        and plan["task_id"] == "research-dispatch-controller"
        and plan["run_id"] == "research-dispatch-controller-20261009T121052-8c15af8c4cb6"
        and plan["run_directory"] == str(OUTPUT_PATH.parent)
        and plan["output"] == str(OUTPUT_PATH)
        and plan["execution_authorized"] is False
        and plan["quota_enforced"] is False,
        "fixed output plan differs; plan-only is not research authority",
    )
    for path in (
        EXTERNAL_MOUNT,
        OUTPUT_PATH,
        REAL_X_DIR,
        OUTPUT_PATH.parent,
        OUTPUT_PATH.parent.parent,
        LEDGER_PATH,
    ):
        _no_symlinks(path)
    _require(os.path.ismount(EXTERNAL_MOUNT), "registered external mount missing")
    try:
        raw = subprocess.check_output(
            ["/usr/sbin/diskutil", "info", "-plist", str(EXTERNAL_MOUNT)], timeout=10
        )
        info = plistlib.loads(raw)
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        raise RealXError(f"external disk identity unavailable: {exc}") from exc
    _require(
        info.get("MountPoint") == str(EXTERNAL_MOUNT)
        and info.get("VolumeUUID") == EXTERNAL_UUID
        and info.get("Internal") is False
        and info.get("Writable") is True,
        "external mount UUID or writable state mismatch",
    )
    _require(
        EXTERNAL_MOUNT.stat().st_dev == EXTERNAL_DEVICE
        and OUTPUT_PATH.parent.parent.stat().st_dev == EXTERNAL_DEVICE
        and MAIN_REPO.stat().st_dev != EXTERNAL_DEVICE,
        "external device mismatch",
    )
    if OUTPUT_PATH.parent.exists():
        _require(
            OUTPUT_PATH.parent.is_dir() and OUTPUT_PATH.parent.stat().st_dev == EXTERNAL_DEVICE,
            "run directory changed device",
        )
    if OUTPUT_PATH.exists():
        _require(
            OUTPUT_PATH.is_dir() and OUTPUT_PATH.stat().st_dev == EXTERNAL_DEVICE,
            "output directory changed device",
        )
    _require(not REAL_X_DIR.exists(), "real X output directory already exists")
    external_free = shutil.disk_usage(EXTERNAL_MOUNT).free
    internal_free = shutil.disk_usage(MAIN_REPO).free
    _require(
        external_free >= plan["external_reserve_bytes"] + plan["estimated_bytes"],
        "insufficient external space",
    )
    _require(
        internal_free >= plan["internal_reserve_bytes"] + plan["internal_metadata_bytes"],
        "insufficient internal space",
    )


def _positive(value: Any, label: str) -> float:
    _require(
        type(value) in (int, float) and math.isfinite(value) and value > 0,
        f"{label} must be positive finite",
    )
    return float(value)


def _derive_x(identity: dict[str, Any]) -> list[dict[str, Any]]:
    """Pure artificial-test seam. Production calls it only after the ledger starts."""
    _membership_sha(identity)
    result = []
    for case in identity["cases"]:
        cid = case["case_id"]
        a = _positive(case["A"], f"{cid}.A")
        c = _positive(case["C"], f"{cid}.C")
        atr = _positive(case["ATR20_SMA"], f"{cid}.ATR20_SMA")
        d = _positive(case["D_frozen"], f"{cid}.D_frozen")
        v = 100.0 * atr / a
        _require(math.isfinite(v) and v > 0, f"nonfinite V: {cid}")
        _require(
            a > c and math.isclose(d, (a - c) / atr, rel_tol=1e-9, abs_tol=1e-9),
            f"frozen D arithmetic identity mismatch: {cid}",
        )
        result.append(
            {
                "case_id": cid,
                "asset": case["asset"],
                "signal_date": case["signal_date"],
                "lifecycle": case["lifecycle"],
                "event_ids": case["event_ids"],
                "event_ma_period": case["event_ma_period"],
                "A": case["A"],
                "C": case["C"],
                "ATR20_SMA": case["ATR20_SMA"],
                "D_frozen": case["D_frozen"],
                "V_volatility_pct": v,
                "price_basis_id": case["price_basis_id"],
                "calendar_id": case["calendar_id"],
                "source_sha256": case["source_sha256"],
                "window_metadata": case["window_metadata"],
            }
        )
    _require(
        len(result) == 76
        and sum(len(r["event_ids"]) for r in result) == 84
        and len({(r["asset"], r["lifecycle"]) for r in result}) == 33,
        "X population changed",
    )
    return result


def _append_ledger(entry: dict[str, Any]) -> None:
    with LEDGER_PATH.open("ab", buffering=0) as handle:
        handle.write(_canonical(entry))
        os.fsync(handle.fileno())


def _start_ledger(path: Path, entry: dict[str, Any]) -> None:
    """Exclusive creation consumes the single pass, even if subsequent work fails."""
    _no_symlinks(path)
    raw = _canonical(entry)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise RealXError("real X pass already consumed; no retry or alternate output") from exc
    with os.fdopen(fd, "wb", buffering=0) as handle:
        handle.write(raw)
        os.fsync(handle.fileno())


def _write_exclusive(path: Path, raw: bytes) -> None:
    _no_symlinks(path)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise RealXError(f"output already exists: {path}") from exc
    with os.fdopen(fd, "wb", buffering=0) as handle:
        handle.write(raw)
        os.fsync(handle.fileno())


def _verify_written(path: Path, expected_sha: str) -> None:
    _no_symlinks(path)
    _require(
        path.is_file()
        and path.stat().st_dev == EXTERNAL_DEVICE
        and _sha(path.read_bytes()) == expected_sha,
        f"written result readback mismatch: {path}",
    )


def run_real_x() -> dict[str, Any]:
    """Fixed production path; parent grant is separate from the output plan."""
    _require(Path(__file__).absolute() == SOURCE_PATH, "executable path differs")
    code_sha = _sha(SOURCE_PATH.read_bytes())
    _read_fixed(DESIGN_PATH, DESIGN_SHA256)
    _read_fixed(CONTRACT_PATH, CONTRACT_SHA256)
    _read_fixed(ADAPTER_PATH, ADAPTER_SHA256)
    plan = _strict_json(_read_fixed(PLAN_PATH, PLAN_SHA256), "output-plan")
    _no_symlinks(GRANT_PATH)
    _require(GRANT_PATH.is_file(), "missing parent X grant")
    grant_raw = GRANT_PATH.read_bytes()
    grant = _strict_json(grant_raw, "real-x-grant")
    identity = _load_adapter_identity()
    _validate_grant(grant, plan=plan, identity=identity, code_sha=code_sha)
    _storage_preflight(plan)
    _require(_sha(GRANT_PATH.read_bytes()) == _sha(grant_raw), "grant changed before start")
    _require(not LEDGER_PATH.exists(), "real X pass already consumed")
    started = {
        "status": "started",
        "at": datetime.now(UTC).isoformat(),
        "grant_sha256": _sha(grant_raw),
        "code_sha256": code_sha,
        "membership_sha256": _membership_sha(identity),
        "output": str(REAL_X_DIR),
        "pass": 1,
    }
    _start_ledger(LEDGER_PATH, started)
    try:
        rows = _derive_x(identity)
        OUTPUT_PATH.parent.mkdir(exist_ok=True)
        OUTPUT_PATH.mkdir(exist_ok=True)
        REAL_X_DIR.mkdir(exist_ok=False)
        _no_symlinks(REAL_X_DIR)
        _require(REAL_X_DIR.stat().st_dev == EXTERNAL_DEVICE, "external device changed after start")
        payload = {
            "schema": "native-risk-d-mae-real-x/1",
            "status": "real_x_only_no_y",
            "counts": identity["counts"],
            "feature_id": identity["feature_id"],
            "variant_id": identity["variant_id"],
            "design_sha256": DESIGN_SHA256,
            "adapter_sha256": ADAPTER_SHA256,
            "executable_sha256": code_sha,
            "grant_sha256": _sha(grant_raw),
            "output_plan_sha256": PLAN_SHA256,
            "membership_sha256": started["membership_sha256"],
            "original_sha256": identity["original_sha256"],
            "window_metadata_sha256": identity["window_metadata_sha256"],
            "real_Y_passes": 0,
            "fits": 0,
            "future_price_reads": 0,
            "rows": rows,
        }
        x_raw = _canonical(payload)
        _write_exclusive(REAL_X_DIR / "x-rows.json", x_raw)
        _verify_written(REAL_X_DIR / "x-rows.json", _sha(x_raw))
        receipt = {
            "schema": "native-risk-d-mae-real-x-receipt/1",
            "status": "x_sealed_only",
            "sealed_at": datetime.now(UTC).isoformat(),
            "x_path": str(REAL_X_DIR / "x-rows.json"),
            "x_sha256": _sha(x_raw),
            "row_count": 76,
            "event_memberships": 84,
            "asset_lifecycle_groups": 33,
            "unknown_case_id": UNKNOWN_CASE_ID,
            "membership_sha256": started["membership_sha256"],
            "original_sha256": identity["original_sha256"],
            "window_metadata_sha256": identity["window_metadata_sha256"],
            "design_sha256": DESIGN_SHA256,
            "adapter_sha256": ADAPTER_SHA256,
            "executable_sha256": code_sha,
            "grant_sha256": _sha(grant_raw),
            "output_plan_sha256": PLAN_SHA256,
            "real_X_passes": 1,
            "V_passes": 1,
            "real_Y_passes": 0,
            "fits": 0,
            "future_price_reads": 0,
            "effect_or_trading_claim": False,
        }
        receipt_raw = _canonical(receipt)
        _write_exclusive(REAL_X_DIR / "receipt.json", receipt_raw)
        receipt_sha = _sha(receipt_raw)
        _verify_written(REAL_X_DIR / "receipt.json", receipt_sha)
        _append_ledger(
            {
                "status": "completed",
                "at": datetime.now(UTC).isoformat(),
                "x_sha256": receipt["x_sha256"],
                "receipt_sha256": receipt_sha,
            }
        )
        return receipt
    except BaseException as exc:
        # The exclusive started record prevents replay even if this append fails.
        with suppress(OSError):
            _append_ledger(
                {
                    "status": "failed",
                    "at": datetime.now(UTC).isoformat(),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
        raise


def main() -> int:
    _require(len(sys.argv) == 1, "this fixed entry accepts no path or override arguments")
    receipt = run_real_x()
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "receipt": str(REAL_X_DIR / "receipt.json"),
                "x_sha256": receipt["x_sha256"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
