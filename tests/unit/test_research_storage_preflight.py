"""Synthetic documents exercise the readonly storage gate, never science."""

import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from lei_signal.research import storage_preflight as storage


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False))
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def case(tmp_path):
    root = tmp_path.resolve()
    source = root / "draft.json"
    digest = write_json(source, {"history": {"family": "new-family"}})
    plan = {
        "schema_version": "research-storage-plan/1.0",
        "binding": {
            "mode": "workflow-draft",
            "input": {"path": str(source), "sha256": digest},
            "out": str(root / "output"),
            "register_report": False,
            "reuse_predictions": None,
        },
        "growth_bytes": {"output": 100, "current_journal": 100, "current_lock": 100},
        "volumes": [
            {
                "id": "internal",
                "kind": "internal",
                "mount_path": str(root),
                "device": root.stat().st_dev,
                "reserve_bytes": 100,
            }
        ],
    }
    return root, source, plan


def check(case, *, free=400, **overrides):
    root, source, plan = case
    plan_path = root / "plan.json"
    write_json(plan_path, plan)
    probes = {"is_mount": lambda path: True, "disk_usage": lambda path: SimpleNamespace(free=free)}
    probes.update(overrides)
    return storage.check_storage_plan(
        plan_path,
        mode=plan["binding"]["mode"],
        input_path=source,
        output_dir=root / "output",
        register_report=plan["binding"]["register_report"],
        reuse_predictions=(plan["binding"]["reuse_predictions"] or {}).get("path"),
        root=root,
        **probes,
    )


def snapshot(root):
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file() and not p.is_symlink()
    }


def test_all_same_device_growth_and_reserve_accumulate(case):
    result = check(case)
    assert result["devices"][0]["required_bytes"] == 400
    assert set(result["targets"]) == {"output", "current_journal", "current_lock"}
    assert not (case[0] / "docs").exists()
    # Each 100-byte role fits separately, but their sum plus reserve does not.
    before = snapshot(case[0])
    with pytest.raises(storage.StoragePreflightError, match="insufficient"):
        check(case, free=399)
    assert snapshot(case[0]) == before


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p["growth_bytes"].pop("current_lock"),
        lambda p: p["growth_bytes"].update(current_lock=0),
        lambda p: p["growth_bytes"].update(current_lock=True),
        lambda p: p["volumes"][0].pop("reserve_bytes"),
        lambda p: p["volumes"][0].update(reserve_bytes=True),
        lambda p: p["volumes"].append(dict(p["volumes"][0], id="duplicate")),
        lambda p: p["binding"].update(mode="workflow-contract"),
        lambda p: p["binding"]["input"].update(sha256="0" * 64),
        lambda p: p["binding"]["input"].update(path="relative.json"),
        lambda p: p["binding"].update(out="/unknown/output"),
        lambda p: p["binding"].update(out="//Volumes/unknown/output"),
        lambda p: p["binding"].update(register_report=0),
    ],
)
def test_malformed_or_missing_budget_and_binding_refused(case, change):
    # Invoke with the actual requested arguments, independently of changed binding.
    change(case[2])
    root, source, plan = case
    path = root / "plan.json"
    write_json(path, plan)
    before = snapshot(root)
    with pytest.raises(storage.StoragePreflightError):
        storage.check_storage_plan(
            path,
            mode="workflow-draft",
            input_path=source,
            output_dir=root / "output",
            root=root,
            is_mount=lambda path: True,
            disk_usage=lambda path: SimpleNamespace(free=9999),
        )
    assert snapshot(root) == before


@pytest.mark.parametrize("kind", ["symlink", "dangling", "fifo", "existing_out", "ancestor_file"])
def test_unsafe_output_path_refused_without_writes(case, kind):
    root, _, plan = case
    output = root / "output"
    if kind == "symlink":
        output.symlink_to(root, target_is_directory=True)
    elif kind == "dangling":
        output.symlink_to(root / "missing", target_is_directory=True)
    elif kind == "fifo":
        os.mkfifo(output)
    elif kind == "existing_out":
        output.mkdir()
    else:
        (root / "parent").write_text("regular file")
        plan["binding"]["out"] = str(root / "parent/output")
    with pytest.raises(storage.StoragePreflightError):
        check(case)
    assert not (root / "docs").exists()


def test_input_and_ledger_symlink_refused(case):
    root, source, _ = case
    actual = root / "actual.json"
    actual.write_bytes(source.read_bytes())
    source.unlink()
    source.symlink_to(actual)
    with pytest.raises(storage.StoragePreflightError, match="symlink"):
        check(case)


@pytest.mark.parametrize("role", ["current_journal", "current_lock"])
@pytest.mark.parametrize("kind", ["directory", "symlink", "fifo"])
def test_unsafe_existing_ledger_or_lock_refused(case, role, kind):
    root = case[0]
    family_digest = hashlib.sha256(b'"new-family"').hexdigest()[:24]
    directory = root / "docs/experiments/raw/research-workflow-ledgers-2026-09-29" / family_digest
    directory.mkdir(parents=True)
    target = directory / ("attempts.jsonl" if role == "current_journal" else "execution.lock")
    if kind == "directory":
        target.mkdir()
    elif kind == "symlink":
        target.symlink_to(root / "missing")
    else:
        os.mkfifo(target)
    # Include the plan before capturing the snapshot (the helper writes it).
    write_json(root / "plan.json", case[2])
    before = sorted(str(p.relative_to(root)) for p in root.rglob("*"))
    with pytest.raises(storage.StoragePreflightError):
        check(case)
    assert sorted(str(p.relative_to(root)) for p in root.rglob("*")) == before
    assert not (root / "output").exists()


def test_volume_unknown_device_and_unknown_capacity_refused(case):
    case[2]["volumes"][0]["device"] += 1
    with pytest.raises(storage.StoragePreflightError, match="device"):
        check(case)
    case[2]["volumes"][0]["device"] -= 1
    with pytest.raises(storage.StoragePreflightError, match="capacity"):
        check(case, disk_usage=lambda path: SimpleNamespace(free=None))


def test_unknown_external_path_never_falls_back_to_internal(case):
    root, source, plan = case
    output = "/Volumes/lei-storage-test-missing-8d687a0c/output"
    plan["binding"]["out"] = output
    path = root / "plan.json"
    write_json(path, plan)
    with pytest.raises(storage.StoragePreflightError, match="volume"):
        storage.check_storage_plan(
            path,
            mode="workflow-draft",
            input_path=source,
            output_dir=output,
            root=root,
            is_mount=lambda path: True,
            disk_usage=lambda path: SimpleNamespace(free=9999),
        )
    assert not Path(output).exists()


def test_double_root_alias_is_rejected_before_volume_matching(case):
    root, source, plan = case
    output = "//Volumes/lei-storage-test-missing-8d687a0c/output"
    plan["binding"]["out"] = output
    path = root / "plan.json"
    write_json(path, plan)
    with pytest.raises(storage.StoragePreflightError, match="canonical"):
        storage.check_storage_plan(
            path,
            mode="workflow-draft",
            input_path=source,
            output_dir=output,
            root=root,
            is_mount=lambda path: True,
            disk_usage=lambda path: SimpleNamespace(free=9999),
        )


def test_registration_and_cross_family_reuse_cannot_omit_roles(case):
    root, source, plan = case
    previous = root / "previous"
    previous.mkdir()
    old_sha = write_json(previous / "contract.json", {"history": {"family": "old-family"}})
    plan["binding"].update(
        mode="workflow-contract",
        register_report=True,
        reuse_predictions={"path": str(previous), "contract_sha256": old_sha},
    )
    plan["binding"]["input"]["sha256"] = write_json(
        source,
        {
            "history": {"family": "new-family"},
            "publication": {"report_path": "docs/experiments/synthetic-2026-10-08.md"},
        },
    )
    (root / "docs/experiments").mkdir(parents=True)
    write_json(root / "docs/experiments/registry.json", {"categories": {}, "entries": {}})
    with pytest.raises(storage.StoragePreflightError, match="roles"):
        check(case, free=9999)
    plan["growth_bytes"].update(
        reuse_journal=100, reuse_lock=100, publication_report=100, publication_registry=100
    )
    result = check(case, free=800)
    assert result["devices"][0]["required_bytes"] == 800
    assert result["targets"]["reuse_journal"] != result["targets"]["current_journal"]
    plan["binding"]["reuse_predictions"]["contract_sha256"] = "0" * 64
    with pytest.raises(storage.StoragePreflightError, match="SHA"):
        check(case, free=9999)


def test_unknown_or_missing_volume_and_capacity_refused(case):
    with pytest.raises(storage.StoragePreflightError, match="mount"):
        check(case, is_mount=lambda path: False)


def test_external_identity_and_second_device_budget(case, monkeypatch):
    root, _, plan = case
    mount = root / "external"
    mount.mkdir()
    plan["binding"]["out"] = str(mount / "out")
    (root / "configs").mkdir()
    policy_path = root / "configs/storage-policy.v1.json"
    policy_sha = write_json(
        policy_path,
        {
            "external_mount": str(mount),
            "external_volume_uuid": "EXPECTED",
            "external_filesystem": "exfat",
        },
    )
    plan["external_policy"] = {"path": str(policy_path), "sha256": policy_sha}
    plan["volumes"].append(
        {
            "id": "external",
            "kind": "external",
            "mount_path": str(mount),
            "device": 987654321,
            "reserve_bytes": 100,
        }
    )
    real_lstat = os.lstat

    def lstat(path):
        st = real_lstat(path)
        if Path(path).is_relative_to(mount):
            return SimpleNamespace(st_mode=st.st_mode, st_dev=987654321)
        return st

    info = {
        "MountPoint": str(mount),
        "VolumeUUID": "EXPECTED",
        "FilesystemType": "exfat",
        "Internal": False,
        "Writable": True,
    }
    path = root / "plan.json"
    write_json(path, plan)

    def run(free, identity, internal_free=300):
        return storage.check_storage_plan(
            path,
            mode="workflow-draft",
            input_path=case[1],
            output_dir=mount / "out",
            root=root,
            stat=lstat,
            is_mount=lambda path: True,
            disk_usage=lambda path: SimpleNamespace(
                free=free if Path(path) == mount else internal_free
            ),
            disk_info=lambda path: identity,
        )

    result = run(200, info)
    assert sorted(d["required_bytes"] for d in result["devices"]) == [200, 300]
    with pytest.raises(storage.StoragePreflightError, match="insufficient"):
        run(199, info)
    with pytest.raises(storage.StoragePreflightError, match="insufficient"):
        run(200, info, internal_free=299)
    for key, wrong in [
        ("VolumeUUID", "WRONG"),
        ("Internal", True),
        ("Writable", False),
        ("MountPoint", str(root)),
        ("FilesystemType", "apfs"),
    ]:
        with pytest.raises(storage.StoragePreflightError):
            run(200, dict(info, **{key: wrong}))
    assert not (mount / "out").exists()
