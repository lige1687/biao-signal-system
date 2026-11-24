"""包装器三路径演练：正常退出 / 非零退出 / 被信号杀死。"""
from __future__ import annotations

import json
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from lei_signal.jobledger.ledger import read_records
from lei_signal.jobledger.wrap import main as wrap_main

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(tmp_path: Path) -> list[dict]:
    return read_records(tmp_path / "job-ledger.jsonl")


class TestWrapperHappyPath:
    def test_exit_zero_success_record(self, tmp_path, capfd):
        code = wrap_main([
            "--job-name", "fixture.echo", "--operation-type", "test",
            "--input-basis", "test:none", "--output-reference", "stdout",
            "--ledger", str(tmp_path / "job-ledger.jsonl"),
            "--", sys.executable, "-c", "print('hello')",
        ])
        assert code == 0
        records = _read(tmp_path)
        assert len(records) == 1
        rec = records[0]
        assert rec["status"] == "success"
        assert rec["error_class"] == "none"
        assert rec["exit_code"] == 0
        assert rec["job_name"] == "fixture.echo"
        assert rec["input_basis"] == "test:none"
        assert isinstance(rec["duration_ms"], int)
        # stdout 透传
        assert "hello" in capfd.readouterr().out


class TestWrapperNonZero:
    def test_exit_3_failed_record(self, tmp_path):
        code = wrap_main([
            "--job-name", "fixture.fail", "--operation-type", "test",
            "--ledger", str(tmp_path / "job-ledger.jsonl"),
            "--", sys.executable, "-c",
            "import sys; print('boom', file=sys.stderr); sys.exit(3)",
        ])
        assert code == 3
        rec = _read(tmp_path)[0]
        assert rec["status"] == "failed"
        assert rec["error_class"] == "exit_3"
        assert rec["exit_code"] == 3


class TestWrapperKilled:
    def test_sigterm_records_killed_by_signal(self, tmp_path):
        """子进程（模拟长任务）被 SIGTERM 杀死：台账落 killed_by_signal。"""
        ledger = tmp_path / "job-ledger.jsonl"
        proc = subprocess.Popen(
            [
                sys.executable, "-m", "lei_signal.jobledger.wrap",
                "--job-name", "fixture.sleep", "--operation-type", "test",
                "--ledger", str(ledger),
                "--", sys.executable, "-c",
                "import time, signal, sys\n"
                "signal.signal(signal.SIGTERM, lambda *a: sys.exit(143))\n"
                "print('ready', flush=True)\n"
                "time.sleep(60)\n",
            ],
            cwd=REPO_ROOT,
            env={"PYTHONPATH": str(REPO_ROOT / "src"), "PATH": "/usr/bin:/bin"},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert proc.stdout is not None
        assert proc.stdout.readline().strip() == "ready"
        proc.send_signal(signal.SIGTERM)
        proc.communicate(timeout=10)
        # 包装器写完台账后以同信号自杀（观测语义与被杀一致）
        assert proc.returncode == -signal.SIGTERM
        records = _read(tmp_path)
        assert len(records) == 1
        rec = records[0]
        assert rec["status"] == "failed"
        assert rec["error_class"] == "killed_by_signal:SIGTERM"

    def test_wrapper_self_terminated_respects_signal(self, tmp_path):
        """直接杀包装器进程组语义：包装器转发并同信号退出，返回码非零。"""
        ledger = tmp_path / "job-ledger.jsonl"
        proc = subprocess.Popen(
            [
                sys.executable, "-m", "lei_signal.jobledger.wrap",
                "--job-name", "fixture.kill", "--operation-type", "test",
                "--ledger", str(ledger),
                "--", "/bin/sleep", "60",
            ],
            cwd=REPO_ROOT,
            env={"PYTHONPATH": str(REPO_ROOT / "src"), "PATH": "/usr/bin:/bin"},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(1.0)
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=10)
        assert proc.returncode == -signal.SIGTERM
        rec = _read(tmp_path)[0]
        assert rec["status"] == "failed"
        assert rec["error_class"] == "killed_by_signal:SIGTERM"


class TestAppendOnly:
    def test_repeated_runs_append_distinct_lines(self, tmp_path):
        ledger = str(tmp_path / "job-ledger.jsonl")
        for i in range(3):
            wrap_main([
                "--job-name", "fixture.loop", "--ledger", ledger,
                "--", sys.executable, "-c", f"print({i})",
            ])
        lines = (tmp_path / "job-ledger.jsonl").read_text().splitlines()
        assert len(lines) == 3
        ids = [json.loads(line)["operation_id"] for line in lines]
        assert len(set(ids)) == 3


def test_missing_command_returns_2_no_ledger(tmp_path):
    ledger = tmp_path / "l.jsonl"
    code = wrap_main(["--ledger", str(ledger), "--"])
    assert code == 2
    assert not ledger.exists()  # 缺命令：报错退出，不落台账
