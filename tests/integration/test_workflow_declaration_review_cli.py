"""Declaration review boundary; artificial contracts, no research execution."""

from __future__ import annotations

import builtins
import importlib.util
import io
import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from types import ModuleType

import pytest

from lei_signal.research import question_contract as native

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts/run_factor_lab.py"
FIXTURE = (
    ROOT
    / "docs/experiments/raw/research-workflow-engineering-2026-09-29"
    / "demos-final/continuous/run/contract.json"
)
DYNAMIC_FIXTURE = (
    ROOT / "docs/experiments/raw/session-composition-information-2026-10-04/draft-main.json"
)


def contract(version="research-workflow/1.1"):
    c = json.loads(FIXTURE.read_text(encoding="utf-8"))
    c["schema_version"] = version
    c["data"]["path"] = "unavailable-panel.json"
    c["data"]["sha256"] = "a" * 64
    c["research_design"] = {
        "claim_mapping": {
            "original_statement": "Artificial declaration review example",
            "source_section": "engineering fixture",
            "proxy_definition": "Existing synthetic distance adapter",
            "preserved_conditions": ["after close"],
            "omitted_conditions": [],
            "decision_use": "Engineering review only",
            "observation_time": "after close",
            "intended_action_time": "next session",
            "application_scope": "artificial example",
            "tested_scope": "no computation",
            "unresolved_uses": [],
        },
        "sample_fit": {
            "qualification_artifact": "unavailable-qualification.json",
            "qualification_sha256": "b" * 64,
            "outcome_values_used_for_design": False,
            "unit": "asset-date",
            "assets": 2,
            "observations": 100,
            "dates": 50,
            "episodes": None,
            "paired_support": "same artificial rows",
            "dependence": "shared dates",
            "model_feature_count": 2,
            "rationale": "Declared counts are not checked here",
            "decision": "estimate",
        },
    }
    for key in c["controller_review"]:
        c["controller_review"][key]["reason"] = f"Artificial review reason for {key}"
    return c


def load_cli():
    spec = importlib.util.spec_from_file_location("declaration_review_cli", CLI)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def forbidden(*args, **kwargs):
    raise AssertionError("declaration review entered a forbidden operation")


def guard_review(mp, path):
    """Fail on research imports, data/feature calls, locks or file mutations."""
    blocked = (
        "lei_signal.research.workflow",
        "lei_signal.research.workflow_evaluation",
        "lei_signal.research.input_preflight",
        "lei_signal.research.factor_lab.runner",
        "lei_signal.research.factor_lab.benchmark_pilot",
        "lei_signal.research.factor_lab.classic_attribution",
    )
    original_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        resolved = (
            importlib.util.resolve_name("." * level + name, globals["__package__"])
            if level
            else name
        )
        candidates = [resolved] + [resolved + "." + item for item in fromlist or ()]
        assert not any(p == b or p.startswith(b + ".") for p in candidates for b in blocked)
        return original_import(name, globals, locals, fromlist, level)

    # Imported adapters may expose builders; none may be called by review.
    from lei_signal.research import workflow_inputs

    for name in ("prepare_observations", "_label"):
        mp.setattr(workflow_inputs, name, forbidden)
    for module_name in blocked:
        fake = ModuleType(module_name)
        for name in (
            "preflight",
            "inspect_workflow_input",
            "execute_workflow",
            "run_workflow",
            "freeze_workflow",
            "family_execution_lock",
            "locked_journal",
            "family_ledger",
            "_record_gate_failure",
            "_reserve",
            "publish",
            "evaluate_observations",
            "run_protocol",
            "run_pilot",
            "run_attribution",
        ):
            setattr(fake, name, forbidden)
        mp.setitem(sys.modules, module_name, fake)
    mp.setattr(builtins, "__import__", guarded_import)
    original_read = Path.read_text
    original_open = io.open

    def guarded_read(self, *args, **kwargs):
        assert self == path, f"unexpected read: {self}"
        return original_read(self, *args, **kwargs)

    def guarded_open(file, mode="r", *args, **kwargs):
        assert Path(file) == path and mode == "r", f"unexpected open: {file}, {mode}"
        return original_open(file, mode, *args, **kwargs)

    mp.setattr(Path, "read_text", guarded_read)
    mp.setattr(Path, "read_bytes", forbidden)
    for name in ("mkdir", "write_text", "write_bytes", "rename", "replace", "unlink", "touch"):
        mp.setattr(Path, name, forbidden)
    mp.setattr(builtins, "open", guarded_open)
    mp.setattr(io, "open", guarded_open)


def invoke_review(path, mp, capsys):
    with mp.context() as guard:
        guard_review(guard, path)
        cli = load_cli()  # Covers import-time runner regressions too.
        guard.setattr(sys, "argv", [str(CLI), "--review-workflow-contract", str(path)])
        code = cli.main()
    output = capsys.readouterr()
    assert output.err == ""
    return code, json.loads(output.out)


@pytest.mark.parametrize("version", ["research-workflow/1.0", "research-workflow/1.1"])
def test_review_passes_native_contract_unchanged_without_side_effects(
    version, tmp_path, monkeypatch, capsys
):
    c = contract(version)
    c.update(mode="plan_only", unrecognized_marker={"target": None})
    c["budget"]["real_runs"] = 0
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(c), encoding="utf-8")
    before = path.read_bytes()
    real_validator = native.validate_workflow_contract
    received = []

    def spy(value):
        received.append(deepcopy(value))
        real_validator(value)
        assert value == c  # The validator and CLI may not fill or rewrite it.

    monkeypatch.setattr(native, "validate_workflow_contract", spy)
    code, result = invoke_review(path, monkeypatch, capsys)
    assert code == 0 and result["declaration_valid"] is True
    assert result["execution_authorized"] is False
    assert result["scope"] == "contract_declarations_only"
    assert received == [c]
    assert path.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["contract.json"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("target", None),
        ("baseline", None),
        ("split", None),
        ("observations", None),
        ("decision", "qualification_only"),
        ("schema_version", []),
        ("assets", [{}]),
    ],
)
def test_unknown_or_invalid_fields_are_rejected_without_defaults(
    field, value, tmp_path, monkeypatch, capsys
):
    c = contract()
    if field == "baseline":
        c["question"][field] = value
    elif field in {"observations", "decision"}:
        c["research_design"]["sample_fit"][field] = value
    elif field == "assets":
        c["universe"][field] = value
    else:
        c[field] = value
    c["mode"] = "plan_only"
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(c), encoding="utf-8")
    before = path.read_bytes()
    code, result = invoke_review(path, monkeypatch, capsys)
    assert code == 3 and result["declaration_valid"] is False
    assert result["execution_authorized"] is False and result["error"]
    assert path.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["contract.json"]


@pytest.mark.parametrize(
    "raw", [None, b"{", b"{}", b"null", b"\xff", b"[" * 1200 + b"0" + b"]" * 1200]
)
def test_file_and_json_failures_are_stdout_rejections(raw, tmp_path, monkeypatch, capsys):
    path = tmp_path / "contract.json"
    if raw is not None:
        path.write_bytes(raw)
    before = list(tmp_path.iterdir())
    code, result = invoke_review(path, monkeypatch, capsys)
    assert code == 3 and result["declaration_valid"] is False
    assert result["execution_authorized"] is False
    assert list(tmp_path.iterdir()) == before


def test_explicit_empty_contract_path_is_a_read_rejection(monkeypatch, capsys):
    with monkeypatch.context() as guard:
        guard_review(guard, Path(""))
        guard.setattr(sys, "argv", [str(CLI), "--review-workflow-contract", ""])
        assert load_cli().main() == 3
    output = capsys.readouterr()
    assert output.err == "" and json.loads(output.out)["declaration_valid"] is False


def test_nonfinite_large_integer_declaration_is_rejected(tmp_path, monkeypatch, capsys):
    c = contract()
    c["budget"]["execution_seconds"] = 10**1000
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(c), encoding="utf-8")
    code, result = invoke_review(path, monkeypatch, capsys)
    assert code == 3 and result["declaration_valid"] is False
    assert result["execution_authorized"] is False


@pytest.mark.parametrize("signal", [KeyboardInterrupt, SystemExit])
def test_process_control_exceptions_are_not_swallowed(signal, tmp_path, monkeypatch, capsys):
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(contract()), encoding="utf-8")

    def interrupted(value):
        raise signal()

    monkeypatch.setattr(native, "validate_workflow_contract", interrupted)
    with pytest.raises(signal):
        invoke_review(path, monkeypatch, capsys)
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    "extra",
    [
        ["--out", "output"],
        ["--out", ""],
        ["--register-report"],
        ["--reuse-predictions", "prior"],
        ["--reuse-predictions", ""],
        ["--protocol", "p"],
        ["--benchmark-protocol", "p"],
        ["--attribution-protocol", "p"],
        ["--workflow-draft", "p"],
        ["--workflow-contract", "p"],
    ],
)
def test_review_conflicts_stop_before_validator_or_research(extra, monkeypatch, capsys):
    monkeypatch.setattr(native, "validate_workflow_contract", forbidden)
    with monkeypatch.context() as guard:
        guard_review(guard, Path("never-read.json"))
        cli = load_cli()
        guard.setattr(
            sys, "argv", [str(CLI), "--review-workflow-contract", "never-read.json", *extra]
        )
        with pytest.raises(SystemExit) as exc:
            cli.main()
    assert exc.value.code == 2
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    "flag,module_name,function_name,extra,expected",
    [
        ("--protocol", "factor_lab.runner", "run_protocol", [], 1),
        (
            "--benchmark-protocol",
            "factor_lab.benchmark_pilot",
            "run_pilot",
            ["--register-report"],
            0,
        ),
        ("--attribution-protocol", "factor_lab.classic_attribution", "run_attribution", [], 0),
        ("--workflow-draft", "workflow", "freeze_workflow", [], 0),
        (
            "--workflow-contract",
            "workflow",
            "run_workflow",
            ["--register-report", "--reuse-predictions", "prior"],
            3,
        ),
    ],
)
def test_existing_modes_keep_dispatch_arguments_and_exit_codes(
    flag, module_name, function_name, extra, expected, monkeypatch
):
    called = []

    def handler(*args, **kwargs):
        called.append((args, kwargs))
        return expected

    fake = ModuleType("lei_signal.research." + module_name)
    setattr(fake, function_name, handler)
    monkeypatch.setitem(sys.modules, fake.__name__, fake)
    monkeypatch.setattr(sys, "argv", [str(CLI), flag, "input", "--out", "output", *extra])
    assert load_cli().main() == expected
    kwargs = (
        {"register_report": True, "reuse_predictions": "prior"}
        if flag == "--workflow-contract"
        else ({"register_report": True} if flag == "--benchmark-protocol" else {})
    )
    assert called == [(("input", "output"), kwargs)]


@pytest.mark.parametrize(
    "args",
    [
        ["--protocol", "p"],
        ["--benchmark-protocol", "p"],
        ["--attribution-protocol", "p"],
        ["--workflow-draft", "p"],
        ["--workflow-contract", "p"],
        ["--protocol", "p", "--out", "o", "--register-report"],
        ["--protocol", "p", "--out", "o", "--reuse-predictions", "prior"],
        ["--workflow-draft", "p", "--out", "o", "--register-report"],
        ["--attribution-protocol", "p", "--out", "o", "--reuse-predictions", "prior"],
    ],
)
def test_existing_required_output_and_conflict_rules(args, monkeypatch, capsys):
    with monkeypatch.context() as guard:
        guard_review(guard, Path("never-read.json"))
        guard.setattr(sys, "argv", [str(CLI), *args])
        with pytest.raises(SystemExit) as exc:
            load_cli().main()
    assert exc.value.code == 2
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("bad_qualification", [False, True])
def test_fresh_process_dynamic_validator_import_is_readonly(bad_qualification, tmp_path):
    c = json.loads(DYNAMIC_FIXTURE.read_text(encoding="utf-8"))
    c["data"]["mode"] = "synthetic"
    c["data"]["path"] = "unavailable-panel.json"
    if bad_qualification:
        c["data"]["mode"] = "historical_reconstruction"
        c["data"]["qualification"] = []
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(c), encoding="utf-8")
    # Profile every Python research call, including helpers reached on import.
    # Only actual declaration validators and module initialization are permitted.
    bootstrap = """
import os, runpy, sys
contract, cli = sys.argv[1:]
def audit(event, args):
    if event == 'open':
        name, mode, flags = args
        if isinstance(name, (str, bytes)):
            name = os.fsdecode(name)
            writes = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
            assert not flags & writes, (event, args)
            assert not '/docs/experiments/' in name or name == contract, (event, name)
            assert not '/data/' in name and not '/logs/' in name, (event, name)
    assert event not in {'os.mkdir', 'os.rename', 'os.remove', 'os.rmdir',
                         'subprocess.Popen', 'socket.connect'}, event
def profile(frame, event, arg):
    if event == 'call':
        name = frame.f_globals.get('__name__', '')
        if name.startswith('lei_signal.research.'):
            assert name not in {'lei_signal.research.workflow',
                                'lei_signal.research.factor_lab.runner',
                                'lei_signal.research.workflow_evaluation'}, name
            function = frame.f_code.co_name
            declaration = (name == 'lei_signal.research.question_contract'
                           or (name == 'lei_signal.research.hmm_market_state_information'
                               and function == 'validate_feature_contract'))
            # Module/class definitions lack CO_NEWLOCALS; real functions have it.
            definition = (not frame.f_code.co_flags & 0x02
                          or function in {'<genexpr>', '<listcomp>', '<setcomp>', '<dictcomp>'})
            definition = definition or (
                function == '__create_fn__' and frame.f_code.co_filename == '<string>'
                and frame.f_back.f_globals.get('__name__') == 'dataclasses')
            definition = definition or (
                name == 'lei_signal.research.factor_lab.rank_ic_evaluation'
                and function in {'__init__', '__repr__', '__hash__', '__eq__'}
                and frame.f_code.co_filename == '<string>'
                and type(frame.f_locals.get('self')).__name__ == 'RankICColumns'
                and (frame.f_back.f_code.co_name == 'RankICContract'
                     or frame.f_back.f_globals.get('__name__') in {'dataclasses', 'inspect'}))
            assert declaration or definition, (name, function)
sys.addaudithook(audit)
sys.setprofile(profile)
sys.argv = [cli, '--review-workflow-contract', contract]
runpy.run_path(cli, run_name='__main__')
"""
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    env.pop("PYTHONDONTWRITEBYTECODE", None)  # CLI itself must suppress lazy-import caches.
    result = subprocess.run(
        [sys.executable, "-c", bootstrap, str(path), str(CLI)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    assert result.returncode == (3 if bad_qualification else 0), result.stdout + result.stderr
    assert result.stderr == ""
    output = json.loads(result.stdout)
    assert output["execution_authorized"] is False
    assert output["declaration_valid"] is not bad_qualification
    assert sorted(p.name for p in tmp_path.iterdir()) == ["contract.json"]
