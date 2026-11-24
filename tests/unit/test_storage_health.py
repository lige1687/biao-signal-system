"""Offline fake-volume checks for the read-only storage preflight."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from lei_signal.integrations.storage_health import (
    VideoStorageRejected,
    collect_storage_health,
    preflight_video_storage,
)

GIB = 1024**3
UUID = "DEBA1C85-6059-3865-B50A-A8EE1F80E4D9"


class FakeProbe:
    def __init__(self, root: Path, mount: Path, audio: Path, model: Path):
        self.root, self.mount, self.audio, self.model = root, mount, audio, model
        self.internal_free = 20 * GIB
        self.external_free = 20 * GIB
        self.mounted = True
        self.missing = False
        self.uuid = UUID
        self.audio_target = mount / "recordings"
        self.model_target = model
        self.info_calls = 0
        self.internal_device = False
        self.internal_usage_unknown = False
        self.external_usage_unknown = False

    def disk_usage(self, path):
        if path == self.root and self.internal_usage_unknown:
            raise OSError("simulated unavailable / noisy command details")
        if path == self.mount and self.external_usage_unknown:
            raise OSError("simulated unavailable external capacity")
        free = self.external_free if path == self.mount else self.internal_free
        return SimpleNamespace(total=100 * GIB, used=100 * GIB - free, free=free)

    def is_mount(self, path):
        return path == self.mount and self.mounted

    def diskutil_info(self, path):
        self.info_calls += 1
        return {
            "MountPoint": str(self.mount),
            "VolumeUUID": self.uuid,
            "FilesystemType": "exfat",
            "Writable": True,
            "Internal": self.internal_device,
            "DeviceNode": "/dev/disk-test",
        }

    def resolve(self, path):
        if path == self.audio:
            return self.audio_target
        if path == self.model:
            return self.model_target
        if path == self.mount and self.missing:
            raise FileNotFoundError(str(path))
        return path

    def is_dir(self, path):
        return path.is_dir()

    def is_file(self, path):
        return path.is_file()

    def lexists(self, path):
        return path.exists() or path.is_symlink()

    def is_symlink(self, path):
        return path.is_symlink()

    def same_device(self, left, right):
        def volume(path):
            return "external" if path == self.mount or self.mount in path.parents else "internal"

        return volume(left) == volume(right)


@pytest.fixture
def setup(tmp_path):
    root, mount = tmp_path / "repo", tmp_path / "external"
    audio = root / "data/cache/portfolio-chat-briefing/video-content/audio"
    model = root / "data/cache/video-models/whisper-small-mlx"
    mount.mkdir()
    (mount / "recordings").mkdir()
    model.mkdir(parents=True)
    (model / "weights.npz").write_bytes(b"test weights")
    (root / "configs").mkdir()
    policy = {
        "schema_version": 1,
        "external_mount": str(mount),
        "external_volume_uuid": UUID,
        "external_filesystem": "exfat",
        "internal_warning_bytes": 15 * GIB,
        "internal_critical_bytes": 5 * GIB,
        "video_internal_min_bytes": 2 * GIB,
        "video_external_reserve_bytes": GIB,
        "video_audio_budget_bytes": 100 * 1024 * 1024,
        "video_audio_logical_path": "data/cache/portfolio-chat-briefing/video-content/audio",
        "video_model_logical_path": "data/cache/video-models/whisper-small-mlx",
    }
    (root / "configs/storage-policy.v1.json").write_text(json.dumps(policy))
    return root, mount, audio, model, FakeProbe(root, mount, audio, model)


def test_healthy_snapshot_and_exact_paths_allow_new_audio(setup):
    root, mount, audio, model, probe = setup
    health = collect_storage_health(root, probe=probe)
    assert health["severity"] == "healthy" and health["status"] == "ok"
    assert health["internal"]["status"] == "ok"
    assert health["external"]["status"] == "ok"
    checked = datetime.fromisoformat(health["checked_at"])
    assert checked.tzinfo is not None
    assert checked.utcoffset() == ZoneInfo("Asia/Shanghai").utcoffset(checked)
    assert health["external"]["identity_ok"]
    result = preflight_video_storage(audio, model, root, probe=probe)
    assert result["allowed"] and result["audio_dir"] == str(mount / "recordings")
    assert result["external_uuid"] == UUID


@pytest.mark.parametrize("free,severity", [(10 * GIB, "warning"), (4 * GIB, "critical")])
def test_internal_warning_and_critical_are_reported(setup, free, severity):
    root, _, _, _, probe = setup
    probe.internal_free = free
    snapshot = collect_storage_health(root, probe=probe)
    assert snapshot["severity"] == severity
    assert snapshot["internal"]["status"] == severity


@pytest.mark.parametrize("state", ["missing", "ordinary_directory", "wrong_uuid"])
def test_missing_fake_or_wrong_external_volume_rejects(setup, state):
    root, _, audio, model, probe = setup
    if state == "missing":
        probe.missing = True
    elif state == "ordinary_directory":
        probe.mounted = False
    else:
        probe.uuid = "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"
    health = collect_storage_health(root, probe=probe)
    assert health["status"] == "blocked" and not health["external"]["identity_ok"]
    assert health["external"]["status"] in {"unavailable", "identity_mismatch"}
    with pytest.raises(VideoStorageRejected, match="外盘"):
        preflight_video_storage(audio, model, root, probe=probe)


@pytest.mark.parametrize(
    "internal,external",
    [
        (GIB, 20 * GIB),
        (20 * GIB, GIB),
    ],
)
def test_video_budget_rejects_low_space(setup, internal, external):
    root, _, audio, model, probe = setup
    probe.internal_free, probe.external_free = internal, external
    with pytest.raises(VideoStorageRejected) as caught:
        preflight_video_storage(audio, model, root, probe=probe)
    assert caught.value.reasons
    if external == GIB:
        assert caught.value.snapshot["external"]["status"] == "low_space"
        assert caught.value.snapshot["severity"] == "critical"
        assert caught.value.snapshot["status"] == "blocked"


def test_unknown_internal_capacity_is_stable_and_sanitized(setup):
    root, _, audio, model, probe = setup
    probe.internal_usage_unknown = True
    health = collect_storage_health(root, probe=probe)
    assert health["internal"]["status"] == "unknown"
    assert health["severity"] == "critical"
    assert health["status"] == "blocked"
    assert not any("simulated" in reason for reason in health["reasons"])
    with pytest.raises(VideoStorageRejected, match="内置盘不足"):
        preflight_video_storage(audio, model, root, probe=probe)


def test_diskutil_internal_true_rejects_even_if_uuid_matches(setup):
    root, _, audio, model, probe = setup
    probe.internal_device = True
    health = collect_storage_health(root, probe=probe)
    assert health["external"]["status"] == "identity_mismatch"
    assert health["severity"] == "critical"
    with pytest.raises(VideoStorageRejected, match="外盘"):
        preflight_video_storage(audio, model, root, probe=probe)


def test_wrong_logical_or_resolved_audio_path_rejected(setup):
    root, _, audio, model, probe = setup
    with pytest.raises(VideoStorageRejected, match="固定路径"):
        preflight_video_storage(root / "other/audio", model, root, probe=probe)
    probe.audio_target = root / "data/cache/fallback"
    probe.audio_target.mkdir(parents=True)
    with pytest.raises(VideoStorageRejected, match="音频实际目录不在"):
        preflight_video_storage(audio, model, root, probe=probe)


def test_model_must_resolve_inside_approved_volume_with_weights(setup):
    root, _, audio, model, probe = setup
    outside = root.parent / "unapproved-model"
    outside.mkdir()
    (outside / "weights.npz").write_bytes(b"test")
    probe.model_target = outside
    with pytest.raises(VideoStorageRejected, match="模型实际路径"):
        preflight_video_storage(audio, model, root, probe=probe)


@pytest.mark.parametrize(
    "damage",
    ["missing", "bad_json", "missing_uuid", "negative_limit", "bool_limit"],
)
def test_invalid_policy_degrades_health_and_blocks_video_without_fallback(setup, damage):
    root, _, audio, model, probe = setup
    path = root / "configs/storage-policy.v1.json"
    if damage == "missing":
        path.unlink()
    elif damage == "bad_json":
        path.write_text("{invalid", encoding="utf-8")
    else:
        policy = json.loads(path.read_text(encoding="utf-8"))
        if damage == "missing_uuid":
            del policy["external_volume_uuid"]
        elif damage == "negative_limit":
            policy["video_audio_budget_bytes"] = -1
        else:
            policy["video_audio_budget_bytes"] = True
        path.write_text(json.dumps(policy), encoding="utf-8")
    health = collect_storage_health(root, probe=probe)
    assert health["severity"] == "unknown"
    assert health["status"] == "unavailable"
    assert health["reasons"]
    assert health["internal"]["status"] == "unknown"
    assert health["external"]["status"] == "unknown"
    assert health["external"]["expected_uuid"] is None
    assert probe.info_calls == 0
    with pytest.raises(VideoStorageRejected, match="存储策略") as caught:
        preflight_video_storage(audio, model, root, probe=probe)
    assert caught.value.snapshot["status"] == "unavailable"
    assert probe.info_calls == 0


class ResourceProbe(FakeProbe):
    def __init__(self, *args):
        super().__init__(*args)
        self.resolved_paths = []

    def resolve(self, path):
        self.resolved_paths.append(path)
        if path in {self.mount, self.audio, self.model}:
            return super().resolve(path)
        return path.resolve(strict=True)


@pytest.fixture
def resource_setup(setup):
    root, mount, audio, model, _ = setup
    target = mount / "saved-model"
    target.mkdir()
    (target / "config.json").write_text('{"model_type": "whisper"}')
    logical = root / "data/cache/ai-resource"
    logical.symlink_to(target, target_is_directory=True)
    registry = {
        "schema_version": 1,
        "external_volume_uuid": UUID,
        "resources": [
            {
                "id": "saved-model",
                "name": "保存的模型",
                "logical_path": "data/cache/ai-resource",
                "external_path": str(target),
                "role": "static_input",
            }
        ],
    }
    registry_path = root / "configs/storage-resources.v1.json"
    registry_path.write_text(json.dumps(registry))
    return root, target, logical, registry_path, ResourceProbe(root, mount, audio, model)


def test_registered_resource_is_readable_and_query_does_not_write(resource_setup, monkeypatch):
    root, target, _, _, probe = resource_setup

    def reject_write(*args, **kwargs):
        raise AssertionError("read-only resource query attempted a filesystem mutation")

    for method in ("mkdir", "symlink_to", "write_text", "write_bytes", "unlink", "rename"):
        monkeypatch.setattr(Path, method, reject_write)
    health = collect_storage_health(root, probe=probe)
    assert health["resources_status"] == "ok"
    resource = health["resources"][0]
    assert resource["available"] and resource["read_path"] == str(target)
    assert resource["logical_mapping_state"] == "linked"
    assert resource["access"] == "existing_files_read_only"
    assert json.loads((Path(resource["read_path"]) / "config.json").read_text()) == {
        "model_type": "whisper"
    }


def test_other_worktree_without_link_can_read_external_resource_without_setup(resource_setup):
    root, target, logical, _, probe = resource_setup
    logical.unlink()
    health = collect_storage_health(root, probe=probe)
    resource = health["resources"][0]
    assert resource["available"] and resource["read_path"] == str(target)
    assert resource["logical_mapping_state"] == "not_configured"
    assert not logical.exists() and not logical.is_symlink()


@pytest.mark.parametrize("state", ["wrong_link", "ordinary_directory", "broken_link"])
def test_conflicting_local_path_is_not_replaced_or_used(resource_setup, state):
    root, _, logical, _, probe = resource_setup
    logical.unlink()
    if state == "ordinary_directory":
        logical.mkdir()
    else:
        logical.symlink_to(root / "wrong-target", target_is_directory=True)
        if state == "wrong_link":
            (root / "wrong-target").mkdir()
    resource = collect_storage_health(root, probe=probe)["resources"][0]
    assert not resource["available"] and resource["read_path"] is None
    assert resource["logical_mapping_state"] == "conflict"
    assert logical.is_dir() if state == "ordinary_directory" else logical.is_symlink()


@pytest.mark.parametrize("state", ["missing", "wrong_uuid", "fake_mount"])
def test_resource_directory_is_not_probed_before_external_identity(resource_setup, state):
    root, target, logical, _, probe = resource_setup
    if state == "missing":
        probe.missing = True
    elif state == "wrong_uuid":
        probe.uuid = "wrong"
    else:
        probe.mounted = False
    resource = collect_storage_health(root, probe=probe)["resources"][0]
    assert not resource["available"] and resource["read_path"] is None
    assert target not in probe.resolved_paths and logical not in probe.resolved_paths


def test_low_space_blocks_new_audio_but_keeps_cached_resource_readable(resource_setup):
    root, _, _, _, probe = resource_setup
    probe.external_free = GIB
    health = collect_storage_health(root, probe=probe)
    assert health["external"]["status"] == "low_space"
    assert health["resources"][0]["available"]
    with pytest.raises(VideoStorageRejected):
        preflight_video_storage(probe.audio, probe.model, root, probe=probe)


def test_external_target_symlink_escape_is_unavailable(resource_setup):
    root, target, _, _, probe = resource_setup
    probe.resolve = lambda path: root if path == target else ResourceProbe.resolve(probe, path)
    resource = collect_storage_health(root, probe=probe)["resources"][0]
    assert not resource["available"] and resource["read_path"] is None


def test_unknown_capacity_with_verified_identity_allows_reads_and_rejects_writes(resource_setup):
    root, _, _, _, probe = resource_setup
    probe.external_usage_unknown = True
    health = collect_storage_health(root, probe=probe)
    assert health["external"]["identity_ok"]
    assert health["external"]["capacity"] is None
    assert health["external"]["status"] == "unknown"
    assert health["resources"][0]["available"]
    with pytest.raises(VideoStorageRejected, match="外盘不足"):
        preflight_video_storage(probe.audio, probe.model, root, probe=probe)


def test_video_preflight_does_not_probe_unrelated_registered_resources(resource_setup):
    root, target, logical, _, probe = resource_setup
    checked = preflight_video_storage(probe.audio, probe.model, root, probe=probe)
    assert checked["allowed"]
    assert target not in probe.resolved_paths and logical not in probe.resolved_paths


@pytest.mark.parametrize(
    "damage",
    ["missing", "bad_json", "wrong_uuid", "absolute_logical", "parent", "outside", "overlap"],
)
def test_invalid_resource_registry_keeps_disk_health_without_usable_paths(resource_setup, damage):
    root, _, _, registry_path, probe = resource_setup
    registry = json.loads(registry_path.read_text())
    if damage == "missing":
        registry_path.unlink()
    elif damage == "bad_json":
        registry_path.write_text("{invalid")
    else:
        entry = registry["resources"][0]
        if damage == "wrong_uuid":
            registry["external_volume_uuid"] = "wrong"
        elif damage == "absolute_logical":
            entry["logical_path"] = "/tmp/resource"
        elif damage == "parent":
            entry["logical_path"] = "data/cache/../../outside"
        elif damage == "outside":
            entry["external_path"] = str(root / "outside")
        else:
            registry["resources"].append({**entry, "id": "overlapping"})
        registry_path.write_text(json.dumps(registry))
    health = collect_storage_health(root, probe=probe)
    assert health["external"]["identity_ok"] and health["severity"] == "healthy"
    assert health["resources_status"] == "unavailable"
    assert health["resources"] == [] and health["resource_errors"]
