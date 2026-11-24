"""二次写失败闭环测试（GPT 第 24 轮，2026-09-20，W1-S1d）。

进程级故障注入矩阵：台账与诊断流（stderr）**同时**不可写时，包装器进程
的最终状态必须只由业务结果决定——
- 业务退出 0 → 父进程观察到 0；
- 业务退出 3 → 父进程观察到 3；
- 收到 SIGTERM → 仍真实同信号终止（父进程观察到 -SIGTERM）；
- 正常路径退出码不受诊断流故障影响（防解释器收尾 flush 失败变 120）。

stderr 故障注入：把包装器的 stderr 接到一段读端已关闭的管道上，写它
即 BrokenPipeError（同一资源故障让台账与诊断流同时不可用的场景）。
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path

from lei_signal.jobledger.wrap import main

REPO_ROOT = Path(__file__).resolve().parents[2]


def _spawn_broken_stderr(
    ledger: Path, command: list[str], *extra_args: str
) -> subprocess.Popen:
    r, w = os.pipe()
    os.close(r)  # 读端关闭：子进程写 stderr 即 BrokenPipeError
    try:
        return subprocess.Popen(
            [
                sys.executable, "-m", "lei_signal.jobledger.wrap",
                "--job-name", "fixture.second-failure",
                "--operation-type", "test",
                "--ledger", str(ledger), *extra_args,
                "--", *command,
            ],
            cwd=REPO_ROOT,
            env={"PYTHONPATH": str(REPO_ROOT / "src"), "PATH": "/usr/bin:/bin"},
            stdout=subprocess.DEVNULL,
            stderr=w,
        )
    finally:
        os.close(w)


def _unwritable_ledger(tmp_path: Path) -> Path:
    ro = tmp_path / "ro"
    ro.mkdir()
    os.chmod(ro, 0o500)
    return ro / "l.jsonl"


class TestProcessLevelFailureMatrix:
    def test_exit0_ledger_and_stderr_both_dead_parent_sees_0(self, tmp_path):
        """业务退出 0 + 台账与诊断流均写失败：父进程观察到 0，不是 120/1。"""
        ledger = _unwritable_ledger(tmp_path)
        try:
            proc = _spawn_broken_stderr(ledger, [sys.executable, "-c", "raise SystemExit(0)"])
            proc.communicate(timeout=30)
        finally:
            os.chmod(ledger.parent, 0o700)
        assert proc.returncode == 0
        assert not ledger.exists()

    def test_exit3_ledger_and_stderr_both_dead_parent_sees_3(self, tmp_path):
        """业务退出 3 + 同上：父进程观察到 3，业务结果不被二次失败改写。"""
        ledger = _unwritable_ledger(tmp_path)
        try:
            proc = _spawn_broken_stderr(ledger, [sys.executable, "-c", "raise SystemExit(3)"])
            proc.communicate(timeout=30)
        finally:
            os.chmod(ledger.parent, 0o700)
        assert proc.returncode == 3

    def test_sigterm_ledger_and_stderr_both_dead_real_signal_exit(self, tmp_path):
        """收到 SIGTERM + 同上：仍真实同信号终止（父进程观察 -SIGTERM），
        诊断输出失败不阻断 returncode 重发路径。"""
        ledger = _unwritable_ledger(tmp_path)
        child = (
            "import signal, sys, time\n"
            "signal.signal(signal.SIGTERM, lambda *a: sys.exit(0))\n"
            "print('ready', flush=True)\n"
            "time.sleep(60)\n"
        )
        proc = None
        try:
            # 这个用例需要读子进程 stdout（ready 标记），单独起一个管道版 spawn
            r_err, w_err = os.pipe()
            os.close(r_err)
            r_out, w_out = os.pipe()
            try:
                proc = subprocess.Popen(
                    [
                        sys.executable, "-m", "lei_signal.jobledger.wrap",
                        "--job-name", "fixture.second-failure",
                        "--operation-type", "test",
                        "--ledger", str(ledger),
                        "--", sys.executable, "-c", child,
                    ],
                    cwd=REPO_ROOT,
                    env={"PYTHONPATH": str(REPO_ROOT / "src"), "PATH": "/usr/bin:/bin"},
                    stdout=w_out,
                    stderr=w_err,
                )
            finally:
                os.close(w_out)
                os.close(w_err)
            with os.fdopen(r_out, "r") as out:
                assert out.readline().strip() == "ready"  # 转发/等待顺序未破坏
            proc.send_signal(signal.SIGTERM)
            proc.communicate(timeout=30)
        finally:
            os.chmod(ledger.parent, 0o700)
            if proc is not None and proc.poll() is None:
                proc.kill()
        assert proc.returncode == -signal.SIGTERM
        assert not ledger.exists()


class TestNormalExitFlushGuard:
    def test_normal_path_broken_stderr_keeps_exit_code(self, tmp_path):
        """台账可写、诊断流坏：正常退出码不受影响（防 120）。"""
        ledger = tmp_path / "l.jsonl"
        proc = _spawn_broken_stderr(ledger, [sys.executable, "-c", "raise SystemExit(0)"])
        proc.communicate(timeout=30)
        assert proc.returncode == 0
        from lei_signal.jobledger.ledger import read_records

        assert len(read_records(ledger)) == 1  # 台账照常落账


class TestDiagnosticGuardUnit:
    def test_ledger_write_failure_diagnostic_is_best_effort(self, tmp_path, monkeypatch, capsys):
        """单元级：台账写失败 + stderr 也写失败 → 无提示但不改退出码。"""

        class _BrokenStderr:
            def write(self, *a):
                raise BrokenPipeError()

            def flush(self):
                raise BrokenPipeError()

            def close(self):
                pass

        import lei_signal.jobledger.wrap as wrap_mod

        monkeypatch.setattr(wrap_mod.sys, "stderr", _BrokenStderr())
        ro = tmp_path / "ro"
        ro.mkdir()
        os.chmod(ro, 0o500)
        ledger = ro / "l.jsonl"  # 目录只读 → append OSError
        try:
            rc = main([
                "--job-name", "fixture.second-failure",
                "--ledger", str(ledger), "--", sys.executable, "-c", "raise SystemExit(7)",
            ])
        finally:
            os.chmod(ro, 0o700)
        assert rc == 7
        assert not ledger.exists()
