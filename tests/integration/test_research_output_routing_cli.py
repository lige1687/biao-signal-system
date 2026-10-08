import json
from pathlib import Path

import pytest

from lei_signal.research import output_storage


def test_new_child_writes_result_logs_and_pointer_without_changing_source(tmp_path, monkeypatch):
    root = tmp_path.resolve() / "repo"
    parent = tmp_path.resolve() / "disk/run"
    (root / "configs").mkdir(parents=True)
    (root / "scripts").mkdir()
    parent.parent.mkdir(parents=True)
    source = root / "scripts/probe.py"
    source.write_text(
        "import argparse,json,pathlib\n"
        "p=argparse.ArgumentParser();p.add_argument('--out');a=p.parse_args()\n"
        "d=pathlib.Path(a.out);d.mkdir()\n"
        "(d/'result.json').write_text(json.dumps({'synthetic':True}))\n"
        "print('probe complete')\n"
    )
    before = source.read_bytes()
    (root / "configs/research-output-policy.v1.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "mode": "external-for-new-results",
                "external_results_directory": "results",
                "entrypoints": {"scripts/probe.py": {"output_flag": "--out"}},
            }
        )
    )
    (root / "configs/storage-policy.v1.json").write_text("{}")
    plan = {
        "task_id": "synthetic-probe",
        "estimated_bytes": 1000,
        "internal_metadata_bytes": 1000,
        "run_directory": str(parent),
        "output": str(parent / "result"),
        "external_mount": str(parent.parent),
        "external_device": parent.parent.stat().st_dev,
        "run_id": "synthetic-probe",
    }
    monkeypatch.setattr(output_storage, "_still_mounted", lambda _: True)
    monkeypatch.setattr(output_storage, "recheck_saved_plan", lambda root, saved, *a: saved)
    receipt = output_storage.execute_new(root, "scripts/probe.py", [], plan)
    assert receipt["exit_code"] == 0
    assert json.loads((parent / "result/result.json").read_text()) == {"synthetic": True}
    assert "probe complete" in (parent / "stdout.log").read_text()
    assert not (root / "result").exists()
    pointer = json.loads(
        (root / "data/cache/research-output-index/synthetic-probe.json").read_text()
    )
    assert pointer["output"] == str(parent / "result")
    assert pointer["scientific_result_verified"] is False
    assert source.read_bytes() == before


def test_disconnect_prevents_launch_and_directory_creation(tmp_path, monkeypatch):
    monkeypatch.setattr(output_storage, "recheck_saved_plan", lambda root, saved, *a: saved)
    monkeypatch.setattr(output_storage, "build_command", lambda *_: ["unused"])
    monkeypatch.setattr(output_storage, "_still_mounted", lambda _: False)
    called = []
    monkeypatch.setattr(output_storage.subprocess, "Popen", lambda *a, **k: called.append(a))
    with pytest.raises(output_storage.OutputStorageError, match="lost"):
        output_storage.execute_new(
            tmp_path,
            "unused",
            [],
            {
                "run_directory": str(tmp_path / "new"),
                "task_id": "probe",
                "estimated_bytes": 1000,
                "internal_metadata_bytes": 1000,
            },
        )
    assert called == []
    assert not (tmp_path / "new").exists()


def test_policy_covers_all_ten_discovered_output_entrypoints():
    root = Path(__file__).resolve().parents[2]
    policy = json.loads((root / "configs/research-output-policy.v1.json").read_text())
    assert len(policy["entrypoints"]) == 10
    for path, spec in policy["entrypoints"].items():
        assert (root / path).is_file()
        assert spec["output_flag"] in {"--out", "--output"}


def test_runtime_disconnect_stops_only_new_child_and_preserves_partial_logs(tmp_path, monkeypatch):
    parent = tmp_path.resolve() / "disk/task/new-run"
    parent.parent.parent.mkdir(parents=True)
    plan = {
        "task_id": "synthetic-probe",
        "estimated_bytes": 1000,
        "internal_metadata_bytes": 1000,
        "run_directory": str(parent),
        "output": str(parent / "result"),
        "external_mount": str(parent.parent.parent),
        "external_device": parent.parent.parent.stat().st_dev,
    }
    monkeypatch.setattr(output_storage, "build_command", lambda *_: ["synthetic-only"])
    monkeypatch.setattr(output_storage, "recheck_saved_plan", lambda root, saved, *a: saved)
    checks = iter([True, True, True, False])
    monkeypatch.setattr(output_storage, "_still_mounted", lambda _: next(checks))

    class Child:
        status = None

        def poll(self):
            return self.status

    child = Child()
    stopped = []
    monkeypatch.setattr(output_storage.subprocess, "Popen", lambda *a, **k: child)

    def stop(actual):
        stopped.append(actual)
        actual.status = -15

    monkeypatch.setattr(output_storage, "_stop_child", stop)
    with pytest.raises(output_storage.OutputStorageError, match="only this newly launched child"):
        output_storage.execute_new(tmp_path, "synthetic-only", [], plan)
    assert stopped == [child]
    assert (parent / "stdout.log").exists()
    assert (parent / "storage-plan.json").exists()
    assert not (tmp_path / "data/cache/research-output-index").exists()
