"""Readonly, stdlib-only write-space gate for the opt-in research CLI.

This module deliberately does not import research implementations. Plan budgets
are explicit anticipated growth, not quotas or scientific execution permission.
The output role includes all output/failure files; journal and lock roles include
new parent-directory allocation. A reused family's lock is budgeted conservatively.
"""

from __future__ import annotations

import hashlib
import json
import os
import plistlib
import shutil
import stat as stat_types
import subprocess
from pathlib import Path


class StoragePreflightError(ValueError):
    """Refusal before project imports, directories, journals or locks."""


def _require(condition, message):
    if not condition:
        raise StoragePreflightError(message)


def _keys(value, required, label, optional=()):
    _require(isinstance(value, dict), f"{label} must be an object")
    _require(
        set(required) <= value.keys() <= set(required) | set(optional),
        f"{label} has missing or unknown fields",
    )


def _absolute(value):
    _require(isinstance(value, (str, Path)), "path must be an absolute string")
    text = str(value)
    path = Path(text)
    _require(
        path.is_absolute()
        and path.anchor == "/"
        and str(path) == text
        and os.path.normpath(text) == text
        and ".." not in path.parts,
        f"path must be canonical absolute without aliases: {text}",
    )
    return path


def _inspect(value, stat, *, kind=None, must_exist=False, must_be_new=False):
    """Inspect lexical components before any resolution; never follow symlinks."""
    path = _absolute(value)
    ancestor = Path(path.anchor)
    ancestor_info = stat(ancestor)
    _require(stat_types.S_ISDIR(ancestor_info.st_mode), "path root is not a directory")
    exists = True
    for index, part in enumerate(path.parts[1:], 1):
        current = ancestor / part
        try:
            info = stat(current)
        except FileNotFoundError:
            exists = False
            break
        _require(not stat_types.S_ISLNK(info.st_mode), f"symlink component forbidden: {current}")
        last = index == len(path.parts) - 1
        _require(
            stat_types.S_ISDIR(info.st_mode) or (last and stat_types.S_ISREG(info.st_mode)),
            f"special file or nondirectory ancestor forbidden: {current}",
        )
        ancestor, ancestor_info = current, info
    _require(not must_exist or exists, f"required path missing: {path}")
    _require(not must_be_new or not exists, f"output/report already exists: {path}")
    if exists and kind:
        expected = stat_types.S_ISDIR if kind == "directory" else stat_types.S_ISREG
        _require(expected(ancestor_info.st_mode), f"path must be a {kind}: {path}")
    # A missing file/dir must have a real directory as its nearest ancestor.
    _require(
        exists or stat_types.S_ISDIR(ancestor_info.st_mode), f"ancestor is not a directory: {path}"
    )
    return path, ancestor, ancestor_info.st_dev


def _json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            _require(key not in result, f"duplicate JSON field: {key}")
            result[key] = value
        return result

    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=unique,
        parse_constant=lambda value: (_ for _ in ()).throw(
            StoragePreflightError("nonfinite JSON number")
        ),
    )


def _fingerprint(path, expected):
    _require(
        isinstance(expected, str)
        and len(expected) == 64
        and all(c in "0123456789abcdef" for c in expected),
        "invalid SHA-256 declaration",
    )
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    _require(digest.hexdigest() == expected, f"SHA-256 mismatch: {path}")


def _journal(root, contract):
    _require(
        isinstance(contract, dict) and isinstance(contract.get("history"), dict),
        "input must declare history.family",
    )
    family = contract["history"].get("family")
    _require(
        isinstance(family, str) and bool(family.strip()), "history.family must be a nonempty string"
    )
    encoded = json.dumps(
        family, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    return (
        root
        / "docs/experiments/raw/research-workflow-ledgers-2026-09-29"
        / hashlib.sha256(encoded).hexdigest()[:24]
        / "attempts.jsonl"
    )


def _disk_info(path):
    result = subprocess.run(
        ["/usr/sbin/diskutil", "info", "-plist", str(path)],
        check=True,
        capture_output=True,
        timeout=10,
    )
    return plistlib.loads(result.stdout)


def _positive(value, label):
    _require(type(value) is int and value > 0, f"{label} must be an explicit positive integer")
    return value


def check_storage_plan(
    plan_path,
    *,
    mode,
    input_path,
    output_dir,
    register_report=False,
    reuse_predictions=None,
    root=None,
    stat=os.lstat,
    is_mount=os.path.ismount,
    disk_usage=shutil.disk_usage,
    disk_info=_disk_info,
):
    """Return a readonly snapshot, or refuse; injectable probes support tests.

    Schema research-storage-plan/1.0 binds mode/input SHA/out/register/reuse.
    growth_bytes must contain exactly every derived role with positive integers.
    Each device has one volume declaration and one positive reserve. External
    identity is pinned to root/configs/storage-policy.v1.json plus its plan SHA.
    Scientific data dependencies remain qualified by the existing workflow.
    """
    try:
        return _check(
            plan_path,
            mode=mode,
            input_path=input_path,
            output_dir=output_dir,
            register_report=register_report,
            reuse_predictions=reuse_predictions,
            root=root,
            stat=stat,
            is_mount=is_mount,
            disk_usage=disk_usage,
            disk_info=disk_info,
        )
    except StoragePreflightError:
        raise
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        RecursionError,
        OverflowError,
        subprocess.SubprocessError,
    ) as exc:
        raise StoragePreflightError(f"cannot verify storage: {exc}") from exc


def _check(
    plan_path,
    *,
    mode,
    input_path,
    output_dir,
    register_report,
    reuse_predictions,
    root,
    stat,
    is_mount,
    disk_usage,
    disk_info,
):
    _require(mode in {"workflow-draft", "workflow-contract"}, "unsupported storage-plan mode")
    _require(type(register_report) is bool, "register_report must be boolean")
    _require(
        mode != "workflow-draft" or (not register_report and reuse_predictions is None),
        "draft cannot register or reuse predictions",
    )
    root = Path(__file__).resolve().parents[3] if root is None else root
    root, _, root_device = _inspect(root, stat, kind="directory", must_exist=True)
    plan_path, _, _ = _inspect(plan_path, stat, kind="file", must_exist=True)
    source, _, _ = _inspect(input_path, stat, kind="file", must_exist=True)
    out, _, _ = _inspect(output_dir, stat, kind="directory", must_be_new=True)
    plan = _json(plan_path)
    _keys(
        plan,
        {"schema_version", "binding", "growth_bytes", "volumes"},
        "storage plan",
        {"external_policy"},
    )
    _require(plan["schema_version"] == "research-storage-plan/1.0", "unknown storage-plan schema")
    binding = plan["binding"]
    _keys(binding, {"mode", "input", "out", "register_report", "reuse_predictions"}, "binding")
    _keys(binding["input"], {"path", "sha256"}, "input binding")
    _require(
        binding["mode"] == mode
        and binding["input"]["path"] == str(source)
        and binding["out"] == str(out)
        and type(binding["register_report"]) is bool
        and binding["register_report"] == register_report,
        "CLI binding mismatch",
    )
    _fingerprint(source, binding["input"]["sha256"])
    contract = _json(source)
    journal = _journal(root, contract)
    targets = {
        "output": out,
        "current_journal": journal,
        "current_lock": journal.with_name("execution.lock"),
    }
    reads = [root, plan_path, source]
    if reuse_predictions is None:
        _require(binding["reuse_predictions"] is None, "reuse binding mismatch")
    else:
        reuse = binding["reuse_predictions"]
        _keys(reuse, {"path", "contract_sha256"}, "reuse binding")
        previous, _, _ = _inspect(reuse_predictions, stat, kind="directory", must_exist=True)
        _require(reuse["path"] == str(previous), "reuse binding mismatch")
        old, _, _ = _inspect(previous / "contract.json", stat, kind="file", must_exist=True)
        _fingerprint(old, reuse["contract_sha256"])
        old_journal = _journal(root, _json(old))
        targets.update(
            reuse_journal=old_journal, reuse_lock=old_journal.with_name("execution.lock")
        )
        reads.extend([previous, old])
    if register_report:
        relative = contract.get("publication", {}).get("report_path")
        _require(isinstance(relative, str), "publication report path missing")
        relative = Path(relative)
        _require(
            not relative.is_absolute()
            and relative.parent == Path("docs/experiments")
            and relative.suffix == ".md",
            "publication report must be in docs/experiments",
        )
        targets.update(
            publication_report=root / relative,
            publication_registry=root / "docs/experiments/registry.json",
        )
    growth = plan["growth_bytes"]
    _require(
        isinstance(growth, dict) and growth.keys() == targets.keys(),
        "growth budgets must cover exact derived roles",
    )
    for role, value in growth.items():
        _positive(value, f"growth_bytes.{role}")
    volumes = plan["volumes"]
    _require(isinstance(volumes, list) and bool(volumes), "volumes must be a nonempty list")
    devices, ids = {}, set()
    external_mount = None
    for volume in volumes:
        _keys(volume, {"id", "kind", "mount_path", "device", "reserve_bytes"}, "volume")
        _require(
            isinstance(volume["id"], str) and bool(volume["id"]) and volume["id"] not in ids,
            "volume id missing or duplicate",
        )
        ids.add(volume["id"])
        device = volume["device"]
        _require(
            type(device) is int and device >= 0 and device not in devices,
            "volume device missing or duplicate",
        )
        reserve = _positive(volume["reserve_bytes"], "reserve_bytes")
        mount, _, actual_device = _inspect(
            volume["mount_path"], stat, kind="directory", must_exist=True
        )
        _require(
            is_mount(mount) and actual_device == device, f"volume mount/device mismatch: {mount}"
        )
        if volume["kind"] == "internal":
            _require(
                device == root_device and not mount.is_relative_to(Path("/Volumes")),
                "unknown internal volume",
            )
        elif volume["kind"] == "external":
            _require(
                external_mount is None and device != root_device,
                "duplicate/invalid external volume",
            )
            policy_binding = plan.get("external_policy")
            _keys(policy_binding, {"path", "sha256"}, "external policy")
            _require(
                policy_binding["path"] == str(root / "configs/storage-policy.v1.json"),
                "external policy must use canonical root config",
            )
            policy_path, _, _ = _inspect(policy_binding["path"], stat, kind="file", must_exist=True)
            _fingerprint(policy_path, policy_binding["sha256"])
            policy = _json(policy_path)
            _require(
                policy.get("external_mount") == str(mount),
                "external mount differs from configured identity",
            )
            expected_uuid, expected_fs = (
                policy.get("external_volume_uuid"),
                policy.get("external_filesystem"),
            )
            _require(
                isinstance(expected_uuid, str)
                and bool(expected_uuid)
                and isinstance(expected_fs, str)
                and bool(expected_fs),
                "configured external identity missing",
            )
            info = disk_info(mount)
            _require(
                isinstance(info, dict)
                and info.get("MountPoint") == str(mount)
                and info.get("VolumeUUID") == expected_uuid
                and info.get("FilesystemType") == expected_fs
                and info.get("Internal") is False
                and info.get("Writable") is True,
                "external volume identity/writability mismatch",
            )
            external_mount = mount
            reads.append(policy_path)
        else:
            raise StoragePreflightError("unknown volume kind")
        capacity = disk_usage(mount).free
        _require(type(capacity) is int and capacity >= 0, "volume capacity unknown")
        devices[device] = {
            "id": volume["id"],
            "device": device,
            "mount_path": str(mount),
            "free_bytes": capacity,
            "reserve_bytes": reserve,
            "growth_bytes": 0,
        }
    if external_mount is None:
        _require("external_policy" not in plan, "unused external policy")

    def locate(path, *, role=None):
        kind = "directory" if role == "output" else "file" if role else None
        inspected, _, device = _inspect(
            path,
            stat,
            kind=kind,
            must_exist=role == "publication_registry",
            must_be_new=role in {"output", "publication_report"},
        )
        _require(device in devices, f"unknown volume for path: {inspected}")
        external_route = external_mount is not None and inspected.is_relative_to(external_mount)
        _require(
            (external_route and device != root_device)
            or (
                not external_route
                and device == root_device
                and not inspected.is_relative_to(Path("/Volumes"))
            ),
            f"missing or unknown volume route: {inspected}",
        )
        if role == "publication_registry":
            _inspect(inspected, stat, kind="file", must_exist=True)
        if role:
            devices[device]["growth_bytes"] += growth[role]

    for path in reads:
        locate(path)
    for role, path in targets.items():
        locate(path, role=role)
    for device in devices.values():
        _require(device["growth_bytes"] > 0, "unused volume declaration")
        device["required_bytes"] = device["growth_bytes"] + device["reserve_bytes"]
        _require(
            device["free_bytes"] >= device["required_bytes"],
            f"insufficient storage on {device['id']}: need {device['required_bytes']}, "
            f"free {device['free_bytes']}",
        )
    return {
        "schema_version": "research-storage-preflight/1.0",
        "targets": {k: str(v) for k, v in targets.items()},
        "devices": list(devices.values()),
        "execution_authorized": False,
    }
