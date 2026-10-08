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

    def disk_usage(self, path):
        if path == self.root and self.internal_usage_unknown:
            raise OSError("simulated unavailable / noisy command details")
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
