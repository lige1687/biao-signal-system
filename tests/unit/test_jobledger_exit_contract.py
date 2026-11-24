"""包装器退出时序契约测试矩阵（GPT 第 22 轮，2026-09-20，G3a/G3d）。

- a) 普通进程：TERM/INT 转发 + 真实同信号退出（父进程断言负返回码）；
     配合清理的直接子进程完成标记；忽略信号的子进程不无限拖住包装器；
- d) 非干扰回归：被杀路径台账写失败仍按序同信号退出、终态不重复；
     停止预算可参数化且预算耗尽如实标注。
- 真实 launchd 双场景证据（G3b/G3c）不进 pytest，见
  docs/ops/job-ledger-diagnosis-2026-09-19.md 的探针记录。
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from lei_signal.jobledger.ledger import read_records
from lei_signal.jobledger.wrap import DEFAULT_STOP_BUDGET_S, _resolve_stop_budget

REPO_ROOT = Path(__file__).resolve().parents[2]


def _spawn(ledger: Path, command: list[str], *extra_args: str) -> subprocess.Popen:
    return subprocess.Popen(
        [
            sys.executable, "-m", "lei_signal.jobledger.wrap",
            "--job-name", "fixture.exit-contract", "--operation-type", "test",
            "--ledger", str(ledger), *extra_args,
            "--", *command,
        ],
        cwd=REPO_ROOT,
        env={"PYTHONPATH": str(REPO_ROOT / "src"), "PATH": "/usr/bin:/bin"},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


COOPERATIVE_CHILD = (
    "import signal, sys, time\n"
    "def _done(*a):\n"
    "    open(sys.argv[1], 'w').write('cleaned')\n"
    "    sys.exit(0)\n"
    "signal.signal(signal.SIGTERM, _done)\n"
    "print('ready', flush=True)\n"
    "time.sleep(60)\n"
)

IGNORING_CHILD = (
    "import os, signal, time\n"
    "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
    "print(os.getpid(), flush=True)\n"
    "# 转走自己的 stdio，避免测试父进程的管道被这个不肯退出的子进程占住\n"
    "devnull = os.open(os.devnull, os.O_WRONLY)\n"
    "os.dup2(devnull, 1)\n"
    "os.dup2(devnull, 2)\n"
    "time.sleep(600)\n"
)


class TestForwardAndRealSignalExit:
    def test_sigterm_forward_cooperative_child_completes(self, tmp_path):
        """SIGTERM：转发→配合的子进程完成清理标记→一条终态→包装器 -SIGTERM。"""
        ledger = tmp_path / "l.jsonl"
        marker = tmp_path / "child_cleaned"
        proc = _spawn(ledger, [sys.executable, "-c", COOPERATIVE_CHILD, str(marker)])
        assert proc.stdout is not None
        assert proc.stdout.readline().strip() == "ready"
        proc.send_signal(signal.SIGTERM)
        proc.communicate(timeout=15)
        # 父进程观察到的是被信号杀死，不是 exit(143)
        assert proc.returncode == -signal.SIGTERM
        assert marker.read_text() == "cleaned"
        records = read_records(ledger)
        assert len(records) == 1
        assert records[0]["status"] == "failed"
        assert records[0]["error_class"] == "killed_by_signal:SIGTERM"
        assert records[0]["exit_code"] is None

    def test_sigint_forward_real_signal_exit(self, tmp_path):
        """SIGINT 路径同序：配合的子进程退出→一条终态→包装器 -SIGINT。
        （注：/bin/sh 等前台等待中的 shell 会推迟 INT 信号的处理，
        这属于子进程不配合的情形，由预算耗尽路径覆盖。）"""
        ledger = tmp_path / "l.jsonl"
        child = (
            "import signal, sys, time\n"
            "signal.signal(signal.SIGINT, lambda *a: sys.exit(0))\n"
            "print('ready', flush=True)\n"
            "time.sleep(60)\n"
        )
        proc = _spawn(ledger, [sys.executable, "-c", child])
        assert proc.stdout is not None
        proc.stdout.readline()
        proc.send_signal(signal.SIGINT)
        proc.communicate(timeout=15)
        assert proc.returncode == -signal.SIGINT
        records = read_records(ledger)
        assert len(records) == 1
        assert records[0]["error_class"] == "killed_by_signal:SIGINT"

    def test_ignoring_child_does_not_hang_wrapper(self, tmp_path):
        """忽略 SIGTERM 的子进程：预算耗尽后包装器照常退出，不无限等待。"""
        ledger = tmp_path / "l.jsonl"
        proc = _spawn(
            ledger,
            [sys.executable, "-c", IGNORING_CHILD],
            "--stop-budget", "0.5",
        )
        assert proc.stdout is not None
        child_pid = int(proc.stdout.readline().strip())
        t0 = time.monotonic()
        try:
            proc.send_signal(signal.SIGTERM)
            proc.communicate(timeout=15)
        finally:
            # 子进程自己不理信号，测试负责收拾（模拟监督环境清扫）
            try:
                os.kill(child_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        elapsed = time.monotonic() - t0
        assert proc.returncode == -signal.SIGTERM
        assert elapsed < 10  # 0.5s 预算 + 余量，远小于 60s 挂起
        records = read_records(ledger)
        assert len(records) == 1
        rec = records[0]
        assert rec["status"] == "failed"
        assert rec["error_class"] == "killed_by_signal:SIGTERM"
        # 预算耗尽如实标注，不伪装成"子进程已配合退出"
        assert rec.get("stop_budget_exhausted") is True
        assert rec["exit_code"] is None


class TestStopBudget:
    def test_budget_resolution_cli_env_default(self, monkeypatch):
        assert _resolve_stop_budget(None) == DEFAULT_STOP_BUDGET_S == 5.0
        monkeypatch.setenv("LEI_WRAP_STOP_BUDGET", "1.5")
        assert _resolve_stop_budget(None) == 1.5
        assert _resolve_stop_budget(0.25) == 0.25
        monkeypatch.setenv("LEI_WRAP_STOP_BUDGET", "not-a-number")
        assert _resolve_stop_budget(None) == 5.0  # 坏值回默认，不崩

    def test_no_budget_exhausted_when_child_cooperates(self, tmp_path):
        """子进程在预算内配合退出：终态不标 stop_budget_exhausted。"""
        ledger = tmp_path / "l.jsonl"
        marker = tmp_path / "m"
        proc = _spawn(ledger, [sys.executable, "-c", COOPERATIVE_CHILD, str(marker)],
                      "--stop-budget", "5")
        assert proc.stdout is not None
        proc.stdout.readline()
        proc.send_signal(signal.SIGTERM)
        proc.communicate(timeout=15)
        rec = read_records(ledger)[0]
        assert rec.get("stop_budget_exhausted") is None


class TestKilledPathLedgerWriteFailure:
    def test_killed_path_write_failure_keeps_order_and_signal_exit(self, tmp_path):
        """被杀路径台账写失败：不破坏顺序、不重复终态、仍真实信号退出。"""
        ro = tmp_path / "ro"
        ro.mkdir()
        os.chmod(ro, 0o500)
        ledger = ro / "l.jsonl"
        marker = tmp_path / "child_cleaned"
        proc = _spawn(ledger, [sys.executable, "-c", COOPERATIVE_CHILD, str(marker)])
        try:
            assert proc.stdout is not None
            proc.stdout.readline()
            proc.send_signal(signal.SIGTERM)
            _, err = proc.communicate(timeout=15)
        finally:
            os.chmod(ro, 0o700)
        assert proc.returncode == -signal.SIGTERM
        assert marker.read_text() == "cleaned"  # 转发/等待顺序未被写失败破坏
        assert "台账写入失败" in err
        assert not ledger.exists()  # 没有重复终态、没有续写
