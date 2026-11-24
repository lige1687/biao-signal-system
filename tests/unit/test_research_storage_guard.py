"""Real tiny child processes exercise stop/retention without market data."""
import json
from pathlib import Path
import sys

import pytest
from lei_signal.research import storage_guard

from lei_signal.research.storage_guard import (
    StoragePolicy, StorageStop, check_space, cleanup_plan, fingerprint,
    output_usage, supervise, verify_cache, write_chunks,
)


def ample(_):
    return 1024 * 1024 * 1024


def command(code):
    return [sys.executable, "-c", code]


def test_low_space_before_launch_has_no_side_effects(tmp_path):
    out = tmp_path / "out"
    with pytest.raises(StorageStop, match="low space"):
        supervise(command("raise AssertionError('must not run')"), out,
                  StoragePolicy(8192, 100), execute=True, free_bytes=lambda _: 99)
    assert not out.exists()


def test_dry_run_does_not_launch_or_create_output(tmp_path):
    out = tmp_path / "out"
    result = supervise(command("raise AssertionError('must not run')"), out,
                       StoragePolicy(8192, 100), free_bytes=ample)
    assert result["status"] == "dry_run"
    assert not out.exists()


def test_macos_tmp_system_alias_is_accepted():
    out = Path("/tmp/lei-storage-guard-unused-alias-check-20261007")
    if out.exists():
        pytest.skip("reserved check name already exists")
    result = supervise(command("raise AssertionError('must not run')"), out,
                       StoragePolicy(8192, 100), free_bytes=ample)
    assert result["status"] == "dry_run"
    assert not out.exists()


def test_unified_runner_cannot_write_to_a_different_output(tmp_path):
    runner = Path(storage_guard.__file__).resolve().parents[3] / "scripts/run_factor_lab.py"
    cmd = [sys.executable, str(runner), "--out", str(tmp_path / "different")]
    with pytest.raises(StorageStop, match="must match"):
        supervise(cmd, tmp_path / "guarded", StoragePolicy(8192), free_bytes=ample)
    cmd[-1] = str(tmp_path / "guarded")
    assert supervise(cmd, tmp_path / "guarded", StoragePolicy(8192), free_bytes=ample)["status"] == "dry_run"


def test_cli_executes_tiny_command_and_reports_exit(tmp_path, monkeypatch, capsys):
    out = tmp_path / "cli-out"
    code = f"from pathlib import Path;p=Path({str(out)!r});p.mkdir();(p/'receipt').write_text('done')"
    monkeypatch.setattr(sys, "argv", ["storage_guard", "--output", str(out),
                        "--max-output-bytes", "8192", "--reserve-bytes", "0",
                        "--execute", "--", *command(code)])
    assert storage_guard.main() == 0
    assert json.loads(capsys.readouterr().out)["status"] == "completed"
    assert (out / "receipt").read_text() == "done"


def test_success_and_command_failure_are_distinct(tmp_path):
    out = tmp_path / "success"
    code = f"from pathlib import Path;p=Path({str(out)!r});p.mkdir();(p/'report').write_text('done')"
    result = supervise(command(code), out, StoragePolicy(8192, 100),
                       execute=True, free_bytes=ample, interval=0.01)
    assert result["status"] == "completed"
    assert (out / "report").read_text() == "done"
    failed = supervise(command("raise SystemExit(7)"), tmp_path / "failed",
                       StoragePolicy(8192, 100), execute=True, free_bytes=ample)
    assert failed["status"] == "failed" and failed["returncode"] == 7


def test_output_quota_stops_writer_and_preserves_evidence(tmp_path):
    out = tmp_path / "out"
    code = (f"from pathlib import Path;import time;p=Path({str(out)!r});p.mkdir();"
            "(p/'partial').write_bytes(b'x'*16384);time.sleep(10);"
            "(p/'should_not_exist').write_text('bad')")
    result = supervise(command(code), out, StoragePolicy(8192, 100),
                       execute=True, free_bytes=ample, interval=0.01)
    assert result["status"] == "paused_storage" and "quota" in result["reason"]
    assert (out / "partial").stat().st_size == 16384
    assert not (out / "should_not_exist").exists()


def test_other_disk_consumption_stops_run(tmp_path):
    out = tmp_path / "out"
    reads = iter([10000, 10000, 99])
    result = supervise(command("import time;time.sleep(10)"), out,
                       StoragePolicy(8192, 100), execute=True,
                       free_bytes=lambda _: next(reads, 99), interval=0.01)
    assert result["status"] == "paused_storage" and "low space" in result["reason"]


def test_existing_output_and_symlinks_rejected(tmp_path):
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(StorageStop, match="already exist"):
        supervise(command("pass"), existing, StoragePolicy(8192), free_bytes=ample)
    link = tmp_path / "link"
    link.symlink_to(existing, target_is_directory=True)
    with pytest.raises(StorageStop, match="symlink"):
        check_space(link / "new", StoragePolicy(8192), free_bytes=ample)
    (existing / "symlink").symlink_to(tmp_path / "absent")
    with pytest.raises(StorageStop, match="symlink"):
        output_usage(existing)


def test_bounded_scan_and_quota_at_checkpoint(tmp_path):
    (tmp_path / "a").write_bytes(b'a')
    (tmp_path / "b").write_bytes(b'b')
    with pytest.raises(StorageStop, match="entries"):
        output_usage(tmp_path, max_entries=2)
    with pytest.raises(StorageStop, match="quota"):
        check_space(tmp_path, StoragePolicy(1), free_bytes=ample)


def test_cooperative_writer_refuses_chunk_before_output_quota(tmp_path):
    out = tmp_path / "out"
    destination = out / "partial"
    with pytest.raises(StorageStop, match="quota"):
        write_chunks(destination, [b"x" * 4096, b"y" * 8192], output=out,
                     policy=StoragePolicy(8192, 100), free_bytes=ample)
    assert destination.read_bytes() == b"x" * 4096
    with pytest.raises(FileExistsError):
        write_chunks(destination, [b"overwrite"], output=out,
                     policy=StoragePolicy(8192, 100), free_bytes=ample)


def test_cooperative_writer_success_low_space_and_escape(tmp_path):
    out = tmp_path / "out"
    result = write_chunks(out / "report", [b"done"], output=out,
                          policy=StoragePolicy(8192, 100), free_bytes=ample)
    assert result["output_bytes"] >= 4
    with pytest.raises(StorageStop, match="inside"):
        write_chunks(tmp_path / "escaped", [b"bad"], output=out,
                     policy=StoragePolicy(8192, 100), free_bytes=ample)
    with pytest.raises(StorageStop, match="low space"):
        write_chunks(out / "low", [b"bad"], output=out,
                     policy=StoragePolicy(8192, 100), free_bytes=lambda _: 99)
    assert not (out / "low").exists()


def test_cache_reuses_exact_dependencies_and_unchanged_bytes(tmp_path):
    source = tmp_path / "input"
    cache = tmp_path / "feature"
    source.write_text("input")
    cache.write_text("feature")
    deps = {"definition_ref": "test@1", "adapter_sha256": "abc",
            "inputs": {str(source): fingerprint(source)}, "parameters": {},
            "date_range": ["2026-01-01", "2026-01-02"]}
    manifest = {"dependencies": deps, "artifacts": [
        {"path": str(cache), "sha256": fingerprint(cache)}]}
    assert verify_cache(manifest, deps)["copied_bytes"] == 0
    changed = json.loads(json.dumps(deps))
    changed["definition_ref"] = "test@2"
    with pytest.raises(StorageStop, match="dependencies differ"):
        verify_cache(manifest, changed)
    source.write_text("changed input")
    with pytest.raises(StorageStop, match="input fingerprint"):
        verify_cache(manifest, deps)
    source.write_text("input")
    cache.write_text("corrupt cache")
    with pytest.raises(StorageStop, match="artifact fingerprint"):
        verify_cache(manifest, deps)


def test_cleanup_blocks_references_protected_evidence_and_unknown_retirement(tmp_path):
    temp = tmp_path / "temp"
    temp.mkdir()
    artifact = temp / "result"
    artifact.write_text("preserve")
    candidates = [{"path": str(temp), "kind": "temporary", "retired": True}]
    options = dict(references=[], protected_roots=[], quarantine=tmp_path / "quarantine")
    plan = cleanup_plan(candidates, **options)
    assert plan[0]["status"] == "blocked"
    options["reference_inventory_complete"] = True
    options["references"] = [artifact]
    assert "protected_or_referenced" in cleanup_plan(candidates, **options)[0]["reasons"]
    options["references"] = []
    options["protected_roots"] = [tmp_path]
    assert cleanup_plan(candidates, **options)[0]["status"] == "blocked"
    options["protected_roots"] = []
    plan = cleanup_plan(candidates, **options)
    assert plan[0]["status"] == "reversible_move_candidate"
    assert plan[0]["expected_freed_bytes"] == 0
    assert artifact.read_text() == "preserve"
    candidates[0]["retired"] = False
    assert cleanup_plan(candidates, **options)[0]["status"] == "blocked"


def test_cleanup_does_not_overwrite_destination(tmp_path):
    temp = tmp_path / "temp"
    temp.write_text("keep")
    quarantine = tmp_path / "quarantine"
    quarantine.mkdir()
    (quarantine / "temp").write_text("also keep")
    plan = cleanup_plan([{"path": str(temp), "kind": "temporary", "retired": True}],
                        references=[], protected_roots=[], quarantine=quarantine,
                        reference_inventory_complete=True)
    assert "destination_exists" in plan[0]["reasons"]


def test_cleanup_multiple_candidates_cannot_share_destination(tmp_path):
    candidates = []
    for name in ["first", "second"]:
        root = tmp_path / name
        root.mkdir()
        path = root / "same-name"
        path.write_text("keep")
        candidates.append({"path": str(path), "kind": "temporary", "retired": True})
    plan = cleanup_plan(candidates, references=[], protected_roots=[],
                        quarantine=tmp_path / "quarantine",
                        reference_inventory_complete=True)
    assert all("duplicate_destination_name" in p["reasons"] for p in plan)


def test_orphan_child_group_cannot_continue_writing(tmp_path):
    out = tmp_path / "out"
    child_code = f"import time;from pathlib import Path;time.sleep(10);Path({str(out)!r}).mkdir()"
    parent_code = f"import subprocess,sys;subprocess.Popen([sys.executable,'-c',{child_code!r}])"
    result = supervise(command(parent_code), out, StoragePolicy(8192, 100),
                       execute=True, free_bytes=ample, interval=0.01)
    assert result["status"] == "failed_descendants"
    assert not out.exists()


def test_signal_permission_denial_is_an_unconfirmed_stop(monkeypatch):
    class Child:
        pid = 123

    def denied(*_):
        raise PermissionError("sandbox denies signal")

    monkeypatch.setattr(storage_guard.os, "killpg", denied)
    errors = storage_guard._stop_group(Child())
    assert errors and "denied" in errors[0]
