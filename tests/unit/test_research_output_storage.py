import json
from pathlib import Path

import pytest

from lei_signal.research.output_storage import OutputStorageError, build_command, plan_output


def test_below_cleanup_target_allows_actual_local_bytes_without_deleting(storage_root):
    root, mount, snapshot = storage_root
    protected = root / "frozen-input.txt"
    protected.write_text("must survive capacity check")
    snapshot["internal_free"] = 60
    before = sorted(p.relative_to(mount) for p in mount.rglob("*"))
    plan = plan_output(root, "sample", 30, probe=lambda *_: snapshot)
    assert plan["internal_reserve_bytes"] == 50
    assert plan["internal_metadata_bytes"] == 20
    assert plan["internal_cleanup_advisory"] == {
        "status": "below_target",
        "available_bytes": 60,
        "cleanup_target_bytes": 70,
        "planned_internal_bytes": 20,
        "gap_to_target_bytes": 10,
    }
    assert protected.read_text() == "must survive capacity check"
    assert sorted(p.relative_to(mount) for p in mount.rglob("*")) == before
    assert not Path(plan["run_directory"]).exists()


def test_actual_local_bytes_insufficient_requests_recovery_without_deleting(storage_root):
    from lei_signal.research.output_storage import StorageRecoveryRequired

    root, mount, snapshot = storage_root
    protected = root / "frozen-input.txt"
    protected.write_text("must survive capacity recovery")
    snapshot["internal_free"] = 19
    with pytest.raises(StorageRecoveryRequired) as exc:
        plan_output(root, "sample", 30, probe=lambda *_: snapshot)
    assert exc.value.recovery["required_bytes"] == 20
    assert exc.value.recovery["shortfall_bytes"] == 1
    assert exc.value.recovery["action"].endswith("recheck_and_resume")
    assert exc.value.recovery["automatic_deletion_performed"] is False
    assert protected.read_text() == "must survive capacity recovery"
    assert not (mount / "results/sample").exists()
    snapshot["internal_free"] = 20  # exact planned local bytes now fit
    plan = plan_output(root, "sample", 30, probe=lambda *_: snapshot)
    assert plan["internal_reserve_bytes"] == 50
    assert plan["internal_cleanup_advisory"]["status"] == "below_target"
    assert not Path(plan["run_directory"]).exists()


def test_cli_reports_actionable_recovery_without_internal_fallback(monkeypatch, capsys):
    from lei_signal.research import output_storage

    def low_space(*args, **kwargs):
        raise output_storage.StorageRecoveryRequired(40, 70)

    monkeypatch.setattr(output_storage, "plan_output", low_space)
    status = output_storage.main([
        "--task", "test", "--entry", "scripts/probe.py", "--estimated-bytes", "30", "--plan-only",
    ])
    result = json.loads(capsys.readouterr().out)
    assert status == 3
    assert result["status"] == "storage_recovery_required"
    assert result["shortfall_bytes"] == 30
    assert result["fallback_to_internal"] is False
    assert result["automatic_deletion_performed"] is False


@pytest.fixture
def storage_root(tmp_path):
    root = tmp_path.resolve() / "repo"
    mount = tmp_path.resolve() / "disk"
    root.mkdir()
    (root / "configs").mkdir()
    (root / "scripts").mkdir()
    (mount / "results").mkdir(parents=True)
    policy = {
        "schema_version": 1,
        "mode": "external-for-new-results",
        "external_results_directory": "results",
        "external_reserve_bytes": 100,
        "default_internal_metadata_bytes": 20,
        "entrypoints": {"scripts/probe.py": {"output_flag": "--out", "subcommands": ["run"]}},
    }
    core = {
        "external_mount": str(mount),
        "external_volume_uuid": "uuid-1",
        "external_filesystem": "exfat",
        "internal_critical_bytes": 50,
    }
    (root / "configs/research-output-policy.v1.json").write_text(json.dumps(policy))
    (root / "configs/storage-policy.v1.json").write_text(json.dumps(core))
    (root / "scripts/probe.py").write_text("# synthetic command only\n")
    info = {
        "MountPoint": str(mount),
        "VolumeUUID": "uuid-1",
        "FilesystemType": "exfat",
        "Internal": False,
        "Writable": True,
    }
    snapshot = {
        "info": info,
        "mounted": True,
        "external_device": mount.stat().st_dev,
        "internal_device": mount.stat().st_dev + 1,
        "external_free": 1000,
        "internal_free": 1000,
    }
    return root, mount, snapshot


def test_default_is_new_external_path_without_any_write(storage_root):
    root, mount, snapshot = storage_root
    before = sorted(p.relative_to(mount) for p in mount.rglob("*"))
    one = plan_output(root, "sample", 30, probe=lambda *_: snapshot)
    two = plan_output(root, "sample", 30, probe=lambda *_: snapshot)
    assert Path(one["output"]).is_relative_to(mount)
    assert one["output"] != two["output"]
    assert not Path(one["run_directory"]).exists()
    assert sorted(p.relative_to(mount) for p in mount.rglob("*")) == before
    assert one["execution_authorized"] is False


@pytest.mark.parametrize(
    "field,value",
    [("VolumeUUID", "wrong"), ("Internal", True), ("Writable", False), ("FilesystemType", "apfs")],
)
def test_wrong_external_identity_refuses_without_write(storage_root, field, value):
    root, mount, snapshot = storage_root
    snapshot["info"][field] = value
    with pytest.raises(OutputStorageError):
        plan_output(root, "sample", 30, probe=lambda *_: snapshot)
    assert not (mount / "results/sample").exists()


@pytest.mark.parametrize(
    "field,value", [("mounted", False), ("external_free", 129), ("internal_free", 19)]
)
def test_missing_disk_or_insufficient_space_refuses(storage_root, field, value):
    root, mount, snapshot = storage_root
    snapshot[field] = value
    with pytest.raises(OutputStorageError):
        plan_output(root, "sample", 30, probe=lambda *_: snapshot)
    assert not (mount / "results/sample").exists()


@pytest.mark.parametrize(
    "task,estimate",
    [("../bad", 30), ("x/y", 30), ("", 30), ("valid", 0), ("valid", -1), ("valid", True)],
)
def test_invalid_task_or_budget_refuses(storage_root, task, estimate):
    root, _, snapshot = storage_root
    with pytest.raises(OutputStorageError):
        plan_output(root, task, estimate, probe=lambda *_: snapshot)


def test_symlinked_external_base_cannot_redirect_to_internal(storage_root):
    root, mount, snapshot = storage_root
    (mount / "results").rmdir()
    (mount / "results").symlink_to(root, target_is_directory=True)
    with pytest.raises(OutputStorageError, match="symlink"):
        plan_output(root, "sample", 30, probe=lambda *_: snapshot)


@pytest.mark.parametrize(
    "args",
    [["run", "--out", "local"], ["run", "--output=x"], ["verify"], ["run", "--repo-root", "other"]],
)
def test_conflicting_or_readonly_commands_refuse(storage_root, args):
    root, _, snapshot = storage_root
    plan = plan_output(root, "sample", 30, probe=lambda *_: snapshot)
    with pytest.raises(OutputStorageError):
        build_command(root, "scripts/probe.py", args, plan)


def test_command_keeps_input_args_and_old_source_bytes(storage_root):
    root, _, snapshot = storage_root
    before = (root / "scripts/probe.py").read_bytes()
    plan = plan_output(root, "sample", 30, probe=lambda *_: snapshot)
    command = build_command(root, "scripts/probe.py", ["run", "--protocol", "frozen.json"], plan)
    assert command[2:] == ["run", "--protocol", "frozen.json", "--out", plan["output"]]
    assert (root / "scripts/probe.py").read_bytes() == before


@pytest.mark.parametrize(
    "flag,reason",
    [
        ("--o", "explicit output"),
        ("--ou", "explicit output"),
        ("--outp", "explicit output"),
        ("--output-d", "explicit output"),
        ("--r", "repository root"),
        ("--roo", "repository root"),
        ("--repo", "repository root"),
        ("--repo-r", "repository root"),
        ("--rev", "read-only review"),
        ("--review-workflow", "read-only review"),
        ("--review-b", "read-only review"),
    ],
)
@pytest.mark.parametrize("equal", [False, True])
def test_protected_option_prefixes_refuse_both_value_forms(storage_root, flag, reason, equal):
    root, mount, snapshot = storage_root
    policy_path = root / "configs/research-output-policy.v1.json"
    policy = json.loads(policy_path.read_text())
    # Isolate each refusal: --r can prefix both a root and a review option.
    policy["entrypoints"]["scripts/probe.py"]["readonly_flags"] = (
        ["--review-workflow-contract", "--review-baselines"] if reason == "read-only review" else []
    )
    policy_path.write_text(json.dumps(policy))
    plan = plan_output(root, "sample", 30, probe=lambda *_: snapshot)
    arguments = [f"{flag}=other"] if equal else [flag, "other"]
    with pytest.raises(OutputStorageError, match=reason):
        build_command(root, "scripts/probe.py", ["run", *arguments], plan)
    assert not (mount / "results/sample").exists()


def test_complete_unrelated_options_and_equals_values_stay_unchanged(storage_root):
    root, _, snapshot = storage_root
    plan = plan_output(root, "sample", 30, probe=lambda *_: snapshot)
    arguments = [
        "run",
        "--protocol=--repo-r",
        "--refs",
        "id@v1",
        "--reuse-predictions",
        "prior",
        "--register-report",
        "--run04-values",
        "frozen.csv",
    ]
    assert build_command(root, "scripts/probe.py", arguments, plan)[2:-2] == arguments


def test_saved_plan_keeps_same_directory_and_rejects_changed_budget_or_route(
    storage_root, monkeypatch
):
    from lei_signal.research import output_storage

    root, _, snapshot = storage_root
    saved = plan_output(root, "sample", 30, internal_bytes=25, probe=lambda *_: snapshot)
    original = output_storage.plan_output
    monkeypatch.setattr(
        output_storage, "plan_output", lambda *a, **k: original(*a, **k, probe=lambda *_: snapshot)
    )
    assert output_storage.recheck_saved_plan(root, saved, "sample", 30)["output"] == saved["output"]
    legacy = {key: value for key, value in saved.items() if key != "internal_cleanup_advisory"}
    snapshot["internal_free"] = 40
    refreshed = output_storage.recheck_saved_plan(root, legacy, "sample", 30)
    assert refreshed["run_directory"] == saved["run_directory"]
    assert refreshed["output"] == saved["output"]
    assert refreshed["internal_metadata_bytes"] == 25
    assert refreshed["internal_cleanup_advisory"]["available_bytes"] == 40
    assert refreshed["internal_cleanup_advisory"]["cleanup_target_bytes"] == 75
    assert refreshed["internal_cleanup_advisory"]["gap_to_target_bytes"] == 35
    snapshot["internal_free"] = 24
    with pytest.raises(output_storage.StorageRecoveryRequired) as exc:
        output_storage.recheck_saved_plan(root, legacy, "sample", 30)
    assert exc.value.recovery["required_bytes"] == 25
    assert not Path(saved["run_directory"]).exists()
    snapshot["internal_free"] = 1000
    with pytest.raises(OutputStorageError, match="mismatch"):
        output_storage.recheck_saved_plan(root, saved, "sample", 31)
    with pytest.raises(OutputStorageError, match="mismatch"):
        output_storage.recheck_saved_plan(root, saved, "sample", 30, 26)
    forged = {
        **saved,
        "run_directory": str(root / saved["run_id"]),
        "output": str(root / saved["run_id"] / "result"),
    }
    with pytest.raises(OutputStorageError, match="directory mismatch"):
        output_storage.recheck_saved_plan(root, forged, "sample", 30)
    Path(saved["run_directory"]).mkdir(parents=True)
    with pytest.raises(OutputStorageError, match="exists"):
        output_storage.recheck_saved_plan(root, saved, "sample", 30)
