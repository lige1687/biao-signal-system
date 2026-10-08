import argparse
import ast
import json
import sys
from pathlib import Path

import pytest

from lei_signal.research import output_storage


def _literal_assignment(path, name):
    for node in ast.parse(path.read_text()).body:
        target = node.target if isinstance(node, ast.AnnAssign) else None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
        if isinstance(target, ast.Name) and target.id == name:
            return ast.literal_eval(node.value)
    raise AssertionError(f"literal assignment missing: {name}")


def _actual_parser_only(root, entry):
    """Extract only actual parser construction; never import or execute a runner.

    Description/default-path labels and callback objects cannot trigger research.
    Option declarations, groups, subparsers and abbreviation settings stay exact.
    """
    tree = ast.parse((root / entry).read_text())
    for function in tree.body:
        if not isinstance(function, ast.FunctionDef):
            continue
        prefix = []
        for statement in function.body:
            calls = [
                node
                for node in ast.walk(statement)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "parse_args"
            ]
            if calls:
                prefix.append(
                    ast.Assign(
                        targets=[ast.Name(id="actual_parser", ctx=ast.Store())],
                        value=calls[0].func.value,
                    )
                )
                break
            if not isinstance(statement, ast.Global):
                prefix.append(statement)
        else:
            continue
        break
    else:
        raise AssertionError(f"actual parser construction not found: {entry}")
    custom_source = root / "scripts/run_momentum_research_prototype.py"
    if entry == "scripts/check_research_input.py":
        custom_source = root / entry
    custom = next(
        n
        for n in ast.parse(custom_source.read_text()).body
        if isinstance(n, ast.ClassDef) and n.name == "_Parser"
    )
    namespace = {
        "argparse": argparse,
        "sys": sys,
        "Path": Path,
        "EXIT_FAILED": 3,
        "__doc__": "parser-only storage regression",
        "DEFAULT_OUT": Path("unused-default"),
        "MODES": _literal_assignment(root / "scripts/run_momentum_research_prototype.py", "MODES"),
        "USES": _literal_assignment(root / "src/lei_signal/research/data_quality.py", "USES"),
        **{f"cmd_{name}": None for name in ("import", "acquire", "verify", "diff", "bind")},
    }
    module = ast.fix_missing_locations(ast.Module(body=[custom, *prefix], type_ignores=[]))
    exec(compile(module, str(root / entry), "exec"), namespace)
    return namespace["actual_parser"]


_ACTUAL_ARGUMENTS = {
    "scripts/run_factor_lab.py": ["--protocol", "frozen.json"],
    "scripts/run_factor_library_v0.py": ["prepare"],
    "scripts/run_factor_evidence_reliability.py": ["--protocol", "frozen.json"],
    "scripts/run_b1_dual_ma_description.py": ["--protocol", "frozen.json"],
    "scripts/run_momentum_research_prototype.py": [
        "--protocol",
        "frozen.json",
        "--mode",
        "synthetic",
    ],
    "scripts/run_research_data_snapshot.py": ["import", "--csv", "frozen.csv"],
    "scripts/prepare_momentum_qualified_inputs.py": [
        "--protocol",
        "frozen.json",
        "--evidence-bundle",
        "bundle.json",
        "--run04-values",
        "prior.csv",
    ],
    "scripts/check_factor_unit_readiness.py": ["--contract", "frozen.json"],
    "scripts/check_research_input.py": [
        "--snapshot",
        "snapshot",
        "--start",
        "2020-01-01",
        "--end",
        "2020-02-01",
        "--use",
        "description",
    ],
    "scripts/verify_research_definitions.py": [],
}


def test_all_actual_registered_parsers_protected_prefixes_and_complete_args():
    root = Path(__file__).resolve().parents[2]
    policy = json.loads((root / "configs/research-output-policy.v1.json").read_text())
    checked = set()
    invocations = [
        *_ACTUAL_ARGUMENTS.items(),
        ("scripts/run_factor_library_v0.py", ["run", "--protocol", "frozen.json"]),
        ("scripts/run_research_data_snapshot.py", ["acquire", "--symbols", "test"]),
    ]
    for entry, arguments in invocations:
        spec = policy["entrypoints"][entry]
        parser = _actual_parser_only(root, entry)
        active = parser
        if spec.get("subcommands"):
            sub = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
            active = sub.choices[arguments[0]]
        protected = {spec["output_flag"], *spec.get("readonly_flags", []), "--root", "--repo-root"}
        for full in protected & active._option_string_actions.keys():
            for length in range(3, len(full) + 1):
                flag = full[:length]
                matches = active._get_option_tuples(flag)
                if flag != full and (len(matches) != 1 or matches[0][1] != full):
                    continue  # Ambiguous prefixes are already refused by the actual parser.
                for equal in (False, True):
                    value = "frozen.json" if full in spec.get("readonly_flags", []) else "other"
                    override = [f"{flag}={value}"] if equal else [flag, value]
                    baseline = [] if full in spec.get("readonly_flags", []) else arguments
                    suffix = (
                        [] if full == spec["output_flag"] else [spec["output_flag"], "external"]
                    )
                    parsed = parser.parse_args([*baseline, *override, *suffix])
                    action = active._option_string_actions[full]
                    assert str(getattr(parsed, action.dest)) == value
                    with pytest.raises(output_storage.OutputStorageError):
                        output_storage.build_command(
                            root, entry, [*baseline, *override], {"output": "external"}
                        )
                    checked.add((entry, full, flag, equal))
        # Every actual complete unrelated option must remain available to its owner.
        for full in active._option_string_actions.keys() - protected - {"--help", "-h"}:
            supplied = [*arguments, full, "value"]
            command = output_storage.build_command(root, entry, supplied, {"output": "external"})
            assert command[2:-2] == supplied
        command = output_storage.build_command(root, entry, arguments, {"output": "external"})
        assert command[2:-2] == arguments
        parser.parse_args(command[2:])
    assert (
        "scripts/run_factor_evidence_reliability.py",
        "--repo-root",
        "--repo-r",
        True,
    ) in checked
    assert ("scripts/run_factor_lab.py", "--review-workflow-contract", "--rev", False) in checked
    assert {case[0] for case in checked} == set(policy["entrypoints"])


@pytest.mark.parametrize(
    "entry,arguments",
    [
        ("scripts/run_factor_evidence_reliability.py", ["--protocol", "frozen", "--repo-r=other"]),
        (
            "scripts/run_factor_evidence_reliability.py",
            ["--protocol", "frozen", "--repo-r", "other"],
        ),
        ("scripts/run_factor_lab.py", ["--review-workflow", "frozen"]),
        ("scripts/run_factor_lab.py", ["--review-workflow=frozen"]),
        ("scripts/run_b1_dual_ma_description.py", ["--protocol", "frozen", "--o", "other"]),
        ("scripts/run_b1_dual_ma_description.py", ["--protocol", "frozen", "--o=other"]),
    ],
)
def test_protected_abbreviation_refuses_before_directory_or_launch(
    tmp_path, monkeypatch, entry, arguments
):
    root = Path(__file__).resolve().parents[2]
    parent = tmp_path / "new-run"
    plan = {
        "task_id": "parser-only",
        "estimated_bytes": 1000,
        "internal_metadata_bytes": 1000,
        "run_directory": str(parent),
        "output": str(parent / "result"),
    }
    monkeypatch.setattr(output_storage, "recheck_saved_plan", lambda root, saved, *a: saved)

    def unexpected(*args, **kwargs):
        pytest.fail("protected argument reached mount check or process launch")

    monkeypatch.setattr(output_storage, "_still_mounted", unexpected)
    monkeypatch.setattr(output_storage.subprocess, "Popen", unexpected)
    with pytest.raises(output_storage.OutputStorageError):
        output_storage.execute_new(root, entry, arguments, plan)
    assert not parent.exists()


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
