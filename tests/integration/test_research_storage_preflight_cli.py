"""Storage refusal must precede research imports and every workflow write."""

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from lei_signal.research import storage_preflight as storage

CLI = Path(__file__).resolve().parents[2] / "scripts/run_factor_lab.py"


def test_refusal_subprocess_has_no_project_import_or_write(tmp_path):
    root = tmp_path.resolve()
    # Shadow packages make any early research import visible (and fail loudly).
    package = root / "lei_signal"
    package.mkdir()
    (package / "__init__.py").write_text("raise RuntimeError('PROJECT_IMPORTED')\n")
    source = root / "input.json"
    source.write_text(json.dumps({"history": {"family": "storage-test"}}))
    plan = root / "plan.json"
    plan.write_text("{}")
    before = sorted(str(p.relative_to(root)) for p in root.rglob("*"))
    env = dict(os.environ, PYTHONPATH=str(root))
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--workflow-contract",
            str(source),
            "--out",
            str(root / "out"),
            "--storage-plan",
            str(plan),
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 3, result.stderr
    assert "storage preflight rejected" in result.stderr
    assert "PROJECT_IMPORTED" not in result.stderr
    assert sorted(str(p.relative_to(root)) for p in root.rglob("*")) == before
    assert not list(root.rglob("*.pyc"))


def load_cli():
    spec = importlib.util.spec_from_file_location("storage_cli_test", CLI)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_preflight_precedes_injected_execution(tmp_path):
    calls = []
    root = tmp_path.resolve()

    def check(*args, **kwargs):
        calls.append(("check", kwargs))

    def execute(args):
        calls.append(("execute", args.workflow_draft))
        return 0

    assert (
        load_cli().main(
            [
                "--workflow-draft",
                str(root / "draft.json"),
                "--out",
                str(root / "out"),
                "--storage-plan",
                str(root / "plan.json"),
            ],
            root=root,
            storage_checker=check,
            workflow_executor=execute,
        )
        == 0
    )
    assert [item[0] for item in calls] == ["check", "execute"]
    assert calls[0][1]["mode"] == "workflow-draft"
    assert not list(root.iterdir())


@pytest.mark.parametrize("free", [400, 399])
def test_real_preflight_controls_safe_callback(tmp_path, free, capsys):
    root = tmp_path.resolve()
    source = root / "new-synthetic-input.json"
    source.write_text(json.dumps({"history": {"family": "new-safe-callback"}}))
    output = root / "output"
    plan = root / "plan.json"
    plan.write_text(
        json.dumps(
            {
                "schema_version": "research-storage-plan/1.0",
                "binding": {
                    "mode": "workflow-draft",
                    "input": {
                        "path": str(source),
                        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                    },
                    "out": str(output),
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
        )
    )
    before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    calls, checked = [], {}

    def checker(*args, **kwargs):
        result = storage.check_storage_plan(
            *args,
            **kwargs,
            is_mount=lambda path: True,
            disk_usage=lambda path: SimpleNamespace(free=free),
        )
        checked.update(result)
        calls.append("checked")

    def execute(args):
        assert calls == ["checked"]
        calls.append("execute")
        Path(args.out).mkdir()
        (Path(args.out) / "safe-sentinel.txt").write_text("engineering callback only")
        journal = Path(checked["targets"]["current_journal"])
        journal.parent.mkdir(parents=True)
        journal.write_text("safe callback journal\n")
        return 0

    result = load_cli().main(
        ["--workflow-draft", str(source), "--out", str(output), "--storage-plan", str(plan)],
        root=root,
        storage_checker=checker,
        workflow_executor=execute,
    )
    if free == 400:
        assert result == 0 and calls == ["checked", "execute"]
        assert (output / "safe-sentinel.txt").read_text() == "engineering callback only"
        assert Path(checked["targets"]["current_journal"]).read_text() == "safe callback journal\n"
    else:
        assert result == 3 and calls == []
        assert "insufficient" in capsys.readouterr().err
        assert {
            str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()
        } == before
        assert not output.exists() and not (root / "docs").exists()


def test_structurally_valid_missing_external_subprocess_refuses_before_import(tmp_path):
    root = tmp_path.resolve()
    source, plan = root / "source.json", root / "plan.json"
    source.write_text(json.dumps({"history": {"family": "new-missing-volume"}}))
    missing = "/Volumes/lei-storage-test-missing-8d687a0c"
    assert not Path(missing).exists()
    plan.write_text(
        json.dumps(
            {
                "schema_version": "research-storage-plan/1.0",
                "binding": {
                    "mode": "workflow-contract",
                    "input": {
                        "path": str(source),
                        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                    },
                    "out": missing + "/output",
                    "register_report": False,
                    "reuse_predictions": None,
                },
                "growth_bytes": {"output": 100, "current_journal": 100, "current_lock": 100},
                "volumes": [
                    {
                        "id": "external",
                        "kind": "external",
                        "mount_path": missing,
                        "device": 987654321,
                        "reserve_bytes": 100,
                    }
                ],
                "external_policy": {
                    "path": str(CLI.parents[1] / "configs/storage-policy.v1.json"),
                    "sha256": "0" * 64,
                },
            }
        )
    )
    package = root / "lei_signal"
    package.mkdir()
    (package / "__init__.py").write_text("raise RuntimeError('PROJECT_IMPORTED')\n")
    before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    project_pyc_before = set(CLI.parents[1].glob("src/lei_signal/research/__pycache__/*"))
    env = dict(os.environ, PYTHONPATH=str(root))
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--workflow-contract",
            str(source),
            "--out",
            missing + "/output",
            "--storage-plan",
            str(plan),
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 3, result.stderr
    assert "required path missing" in result.stderr and "PROJECT_IMPORTED" not in result.stderr
    assert {
        str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()
    } == before
    assert not list(root.rglob("*.pyc")) and not Path(missing).exists()
    assert set(CLI.parents[1].glob("src/lei_signal/research/__pycache__/*")) == project_pyc_before


def test_legacy_workflow_without_plan_uses_execution_only(tmp_path):
    def forbidden(*args, **kwargs):
        pytest.fail("legacy CLI acquired a storage dependency")

    seen = []
    assert (
        load_cli().main(
            ["--workflow-contract", "old.json", "--out", "old-out"],
            storage_checker=forbidden,
            workflow_executor=lambda args: seen.append(args.workflow_contract) or 0,
        )
        == 0
    )
    assert seen == ["old.json"]


@pytest.mark.parametrize(
    "mode",
    ["--protocol", "--benchmark-protocol", "--attribution-protocol", "--review-workflow-contract"],
)
def test_unsupported_mode_rejects_plan_without_checking(mode):
    def forbidden(*args, **kwargs):
        pytest.fail("unsupported mode must not probe storage")

    with pytest.raises(SystemExit) as error:
        load_cli().main(
            [mode, "input.json", "--storage-plan", "plan.json"], storage_checker=forbidden
        )
    assert error.value.code == 2
