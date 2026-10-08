"""Read-only volume health and bounded preflight for this module's video ASR.

This is an advisory snapshot plus a fail-closed preflight for callers that use
it. It does not install a system quota, monitor other processes, or stop jobs.
"""

from __future__ import annotations

import json
import os
import plistlib
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

_REPO = Path(__file__).resolve().parents[3]
_SHANGHAI = ZoneInfo("Asia/Shanghai")


class VideoStorageRejected(RuntimeError):
    def __init__(self, reasons: list[str], snapshot: dict[str, Any]):
        self.reasons = reasons
        self.snapshot = snapshot
        super().__init__("视频存储预检未通过：" + "；".join(reasons))


class _SystemProbe:
    def disk_usage(self, path: Path):
        return shutil.disk_usage(path)

    def is_mount(self, path: Path) -> bool:
        return os.path.ismount(path)

    def diskutil_info(self, path: Path) -> dict:
        completed = subprocess.run(
            ["diskutil", "info", "-plist", str(path)],
            check=True,
            capture_output=True,
            timeout=10,
        )
        return plistlib.loads(completed.stdout)

    def resolve(self, path: Path) -> Path:
        return path.resolve(strict=True)

    def is_dir(self, path: Path) -> bool:
        return path.is_dir()

    def is_file(self, path: Path) -> bool:
        return path.is_file()

    def lexists(self, path: Path) -> bool:
        return os.path.lexists(path)

    def is_symlink(self, path: Path) -> bool:
        return path.is_symlink()

    def same_device(self, left: Path, right: Path) -> bool:
        return left.stat().st_dev == right.stat().st_dev


def _load_policy(repo_root: Path) -> dict:
    path = repo_root / "configs/storage-policy.v1.json"
    policy = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(policy, dict)
        or type(policy.get("schema_version")) is not int
        or policy["schema_version"] != 1
    ):
        raise ValueError("存储策略版本或格式不受支持")
    text_keys = (
        "external_mount",
        "external_volume_uuid",
        "external_filesystem",
        "video_audio_logical_path",
        "video_model_logical_path",
    )
    number_keys = (
        "internal_warning_bytes",
        "internal_critical_bytes",
        "video_internal_min_bytes",
        "video_external_reserve_bytes",
        "video_audio_budget_bytes",
    )
    if any(not isinstance(policy.get(key), str) or not policy[key] for key in text_keys):
        raise ValueError("存储策略缺少必要路径或卷身份")
    if any(type(policy.get(key)) is not int or policy[key] < 0 for key in number_keys):
        raise ValueError("存储策略缺少非负整数空间界限")
    if not Path(policy["external_mount"]).is_absolute():
        raise ValueError("存储策略外盘路径不是绝对路径")
    if any(
        Path(policy[key]).is_absolute() or ".." in Path(policy[key]).parts
        for key in ("video_audio_logical_path", "video_model_logical_path")
    ):
        raise ValueError("存储策略视频路径不是仓库内相对路径")
    return policy


def _unavailable_policy_snapshot(root: Path) -> dict:
    return {
        "schema_version": 1,
        "checked_at": datetime.now(_SHANGHAI).isoformat(),
        "severity": "unknown",
        "status": "unavailable",
        "reasons": ["存储策略缺失或无效，无法核对磁盘身份与空间界限"],
        "internal": {"path": str(root), "status": "unknown", "capacity": None},
        "external": {
            "mount_point": None,
            "expected_uuid": None,
            "available": False,
            "identity_ok": False,
            "status": "unknown",
            "capacity": None,
            "reasons": ["存储策略不可用"],
        },
        "resource_registry": str(root / "configs/storage-resources.v1.json"),
        "access_guide": str(root / "docs/ops/codex-storage-management.md"),
        "resources_status": "unavailable",
        "resource_errors": ["存储策略不可用，不能核对资源路径"],
        "resources": [],
    }


def _usage(probe: Any, path: Path) -> dict:
    disk = probe.disk_usage(path)
    return {
        "total_bytes": int(disk.total),
        "used_bytes": int(disk.used),
        "free_bytes": int(disk.free),
    }


def _inside(path: Path, directory: Path) -> bool:
    return path == directory or directory in path.parents


def _load_resources(root: Path, policy: dict) -> list[dict]:
    registry = json.loads((root / "configs/storage-resources.v1.json").read_text(encoding="utf-8"))
    if (
        not isinstance(registry, dict)
        or type(registry.get("schema_version")) is not int
        or registry["schema_version"] != 1
        or registry.get("external_volume_uuid") != policy["external_volume_uuid"]
        or not isinstance(registry.get("resources"), list)
        or not 1 <= len(registry["resources"]) <= 20
    ):
        raise ValueError("资源清单版本、设备身份或格式不符")
    mount = Path(policy["external_mount"])
    seen: set[str] = set()
    paths: list[tuple[Path, Path]] = []
    for entry in registry["resources"]:
        if not isinstance(entry, dict) or any(
            not isinstance(entry.get(key), str) or not 1 <= len(entry[key]) <= 2048
            for key in ("id", "name", "logical_path", "external_path", "role")
        ):
            raise ValueError("资源清单缺少必要字段")
        logical, target = Path(entry["logical_path"]), Path(entry["external_path"])
        if (
            entry["id"] in seen
            or logical.is_absolute()
            or logical.parts[:2] != ("data", "cache")
            or ".." in logical.parts
            or not target.is_absolute()
            or ".." in target.parts
            or not _inside(target, mount)
            or target == mount
            or entry["role"] not in {"static_input", "existing_audio_cache"}
            or any(
                _inside(logical, prior_logical)
                or _inside(prior_logical, logical)
                or _inside(target, prior_target)
                or _inside(prior_target, target)
                for prior_logical, prior_target in paths
            )
            or any("\x00" in entry[key] for key in ("id", "logical_path", "external_path"))
        ):
            raise ValueError("资源清单含重复身份、不允许的路径或用途")
        recovery = entry.get("recovery_manifest")
        if recovery is not None and (
            not isinstance(recovery, str)
            or not recovery
            or "\x00" in recovery
            or not Path(recovery).is_absolute()
            or ".." in Path(recovery).parts
            or not _inside(Path(recovery), mount)
        ):
            raise ValueError("资源恢复清单路径不在批准外盘内")
        seen.add(entry["id"])
        paths.append((logical, target))
    return registry["resources"]


def _resource_access(root: Path, policy: dict, external: dict, probe: Any) -> dict:
    """Expose verified read paths; never create a directory or configure a link."""
    result: dict[str, Any] = {
        "resource_registry": str(root / "configs/storage-resources.v1.json"),
        "access_guide": str(root / "docs/ops/codex-storage-management.md"),
        "resources_status": "unavailable",
        "resource_errors": [],
        "resources": [],
    }
    try:
        entries = _load_resources(root, policy)
    except (OSError, ValueError, TypeError, KeyError):
        result["resource_errors"].append("资源清单缺失或无效，未提供可读路径")
        return result
    mount = Path(policy["external_mount"])
    for entry in entries:
        logical, target = root / entry["logical_path"], Path(entry["external_path"])
        resource = {
            **entry,
            "logical_path": str(logical),
            "available": False,
            "read_path": None,
            "access": "existing_files_read_only",
            "logical_mapping_state": "unchecked",
            "reason": "",
            "integrity": "本次只核设备与路径；内容指纹需另按恢复清单核对",
        }
        if not external["identity_ok"]:
            resource["reason"] = "批准的外盘未挂载或身份无法核对"
        else:
            try:
                actual = probe.resolve(target)
                if (
                    actual != target
                    or not _inside(actual, mount)
                    or not probe.is_dir(actual)
                    or not probe.same_device(actual, mount)
                ):
                    raise ValueError("资源目录不在已核外盘固定位置")
                if probe.lexists(logical):
                    resource["logical_mapping_state"] = "conflict"
                    if not probe.is_symlink(logical) or probe.resolve(logical) != actual:
                        raise ValueError("仓库原路径与资源清单冲突，不能自动替换")
                    resource["logical_mapping_state"] = "linked"
                else:
                    resource["logical_mapping_state"] = "not_configured"
                resource["available"] = True
                resource["read_path"] = str(actual)
                resource["reason"] = (
                    "原路径可读"
                    if resource["logical_mapping_state"] == "linked"
                    else "此工作目录未配置链接，可直接用外盘只读路径；未创建链接"
                )
            except (OSError, ValueError):
                resource["reason"] = (
                    "仓库原路径与资源清单冲突，不能自动替换"
                    if resource["logical_mapping_state"] == "conflict"
                    else "资源目录缺失、逃逸或设备不符，无法提供可读路径"
                )
        result["resources"].append(resource)
    available = sum(item["available"] for item in result["resources"])
    result["resources_status"] = (
        "ok" if available == len(entries) else ("partial" if available else "unavailable")
    )
    return result


def _external(policy: dict, probe: Any) -> dict:
    mount = Path(policy["external_mount"])
    result = {
        "mount_point": str(mount),
        "expected_uuid": policy["external_volume_uuid"],
        "available": False,
        "identity_ok": False,
        "status": "unknown",
        "capacity": None,
        "reasons": [],
    }
    try:
        resolved = probe.resolve(mount)
    except FileNotFoundError:
        result["status"] = "unavailable"
        result["reasons"].append("批准的外盘未挂载")
        return result
    except (OSError, ValueError):
        result["reasons"].append("外盘挂载路径无法核对")
        return result
    try:
        if resolved != mount or not probe.is_mount(mount):
            result["status"] = "identity_mismatch"
            result["reasons"].append("外盘挂载点被普通目录或链接冒充")
            return result
        info = probe.diskutil_info(mount)
        if (
            info.get("MountPoint") != str(mount)
            or str(info.get("VolumeUUID", "")).upper() != policy["external_volume_uuid"].upper()
            or str(info.get("FilesystemType", "")).lower() != policy["external_filesystem"].lower()
            or info.get("Writable") is not True
            or info.get("Internal") is not False
        ):
            result["status"] = "identity_mismatch"
            result["reasons"].append("外盘 UUID、文件系统、设备类型、挂载路径或可写状态不符")
            return result
        result["identity_ok"] = True
        result["device_node"] = str(info.get("DeviceNode") or "")
        result["capacity"] = _usage(probe, mount)
        result["available"] = True
        required = int(policy["video_external_reserve_bytes"]) + int(
            policy["video_audio_budget_bytes"]
        )
        if result["capacity"]["free_bytes"] < required:
            result["status"] = "low_space"
            result["reasons"].append("外盘不足 1 GiB 保留空间加 100 MiB 音频余量")
        else:
            result["status"] = "ok"
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        result["reasons"].append("外盘信息或容量无法核对")
    return result


def collect_storage_health(
    repo_root: str | Path = _REPO, *, probe: Any = None, include_resources: bool = True
) -> dict:
    """JSON-friendly, read-only current volume snapshot."""
    root = Path(repo_root)
    try:
        policy = _load_policy(root)
    except (OSError, ValueError, TypeError, KeyError):
        return _unavailable_policy_snapshot(root)
    probe = probe or _SystemProbe()
    reasons: list[str] = []
    internal = {"path": str(root), "status": "unknown", "capacity": None}
    try:
        if not probe.is_dir(root):
            raise ValueError("仓库根目录不可用")
        internal["capacity"] = _usage(probe, root)
    except (OSError, ValueError):
        reasons.append("内置盘容量无法核对")
    external = _external(policy, probe)
    reasons.extend(external["reasons"])
    free = (internal["capacity"] or {}).get("free_bytes")
    if free is not None:
        if free < int(policy["internal_critical_bytes"]):
            internal["status"] = "critical"
            reasons.append("内置盘剩余空间低于 5 GiB 严重线")
        elif free < int(policy["internal_warning_bytes"]):
            internal["status"] = "warning"
            reasons.append("内置盘剩余空间低于 15 GiB 警告线")
        else:
            internal["status"] = "ok"
    if internal["status"] in {"critical", "unknown"} or external["status"] != "ok":
        severity = "critical"
    elif internal["status"] == "warning":
        severity = "warning"
    else:
        severity = "healthy"
    snapshot = {
        "schema_version": 1,
        "checked_at": datetime.now(_SHANGHAI).isoformat(),
        "severity": severity,
        "status": "blocked"
        if external["status"] != "ok" or internal["status"] == "unknown"
        else ("attention" if severity != "healthy" else "ok"),
        "reasons": reasons,
        "internal": internal,
        "external": external,
    }
    if include_resources:
        snapshot.update(_resource_access(root, policy, external, probe))
    return snapshot


def _logical(repo_root: Path, path: str | Path) -> Path:
    value = Path(path)
    return Path(os.path.abspath(value if value.is_absolute() else repo_root / value))


def preflight_video_storage(
    audio_dir: str | Path,
    model_path: str | Path,
    repo_root: str | Path = _REPO,
    *,
    probe: Any = None,
) -> dict:
    """Reject new audio work unless the exact intended paths and budgets pass."""
    root = Path(repo_root)
    probe = probe or _SystemProbe()
    snapshot = collect_storage_health(root, probe=probe, include_resources=False)
    if snapshot["status"] == "unavailable":
        raise VideoStorageRejected(snapshot["reasons"], snapshot)
    try:
        policy = _load_policy(root)
    except (OSError, ValueError, TypeError, KeyError):
        snapshot = _unavailable_policy_snapshot(root)
        raise VideoStorageRejected(snapshot["reasons"], snapshot) from None
    reasons: list[str] = []
    internal_free = (snapshot["internal"]["capacity"] or {}).get("free_bytes")
    external_free = (snapshot["external"]["capacity"] or {}).get("free_bytes")
    if internal_free is None or internal_free < int(policy["video_internal_min_bytes"]):
        reasons.append("内置盘不足 2 GiB，新音频任务暂停")
    required_external = int(policy["video_external_reserve_bytes"]) + int(
        policy["video_audio_budget_bytes"]
    )
    if not snapshot["external"]["identity_ok"]:
        reasons.append("批准的外盘未挂载或身份不符")
    elif external_free is None or external_free < required_external:
        reasons.append("外盘不足 1 GiB 保留空间加 100 MiB 音频余量")
    logical_audio = _logical(root, audio_dir)
    logical_model = _logical(root, model_path)
    expected_audio = _logical(root, policy["video_audio_logical_path"])
    expected_model = _logical(root, policy["video_model_logical_path"])
    if logical_audio != expected_audio:
        reasons.append("音频输出路径不是已批准的固定路径")
    if logical_model != expected_model:
        reasons.append("模型路径不是已批准的固定路径")
    mount = Path(policy["external_mount"])
    resolved_audio = resolved_model = None
    try:
        resolved_audio = probe.resolve(logical_audio)
        if (
            not probe.is_dir(resolved_audio)
            or not _inside(resolved_audio, mount)
            or resolved_audio == mount
            or not probe.same_device(resolved_audio, mount)
        ):
            reasons.append("音频实际目录不在已核身份的外盘内")
    except (OSError, ValueError) as exc:
        reasons.append(f"音频实际目录无法核对：{exc}")
    try:
        resolved_model = probe.resolve(logical_model)
        internal_model = _inside(resolved_model, root) and probe.same_device(resolved_model, root)
        external_model = (
            snapshot["external"]["identity_ok"]
            and _inside(resolved_model, mount)
            and probe.same_device(resolved_model, mount)
        )
        if (
            not probe.is_dir(resolved_model)
            or not probe.is_file(resolved_model / "weights.npz")
            or not (internal_model or external_model)
        ):
            reasons.append("模型实际路径或权重不在允许的内置/外盘位置")
    except (OSError, ValueError) as exc:
        reasons.append(f"模型实际路径无法核对：{exc}")
    if reasons:
        raise VideoStorageRejected(reasons, snapshot)
    return {
        "allowed": True,
        "audio_dir": str(resolved_audio),
        "model_path": str(resolved_model),
        "internal_free_bytes": internal_free,
        "external_free_bytes": external_free,
        "external_uuid": policy["external_volume_uuid"],
        "scope": "仅控制显式调用本预检的新视频音频任务",
    }
