"""包装器非干扰证据补强（GPT 第 20 轮清单 G1–G5，2026-09-20）。

- G1 台账写失败降级：不重跑业务、不改退出码、stderr 有降级信息、不换目录续写；
- G2 孙进程清理：真实进程组验证，发信号后无遗留存活进程，终态不重复；
- G3 子进程先被信号杀死：负返回码归类 killed_by_signal，不误判数字退出；
- G4 启动上下文等价：同命令有/无包装对比 stdout/stderr/退出码/env/cwd；
- G5 并发追加：多进程共写同一 JSONL，逐行可解析、id 不串、无半行。
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from lei_signal.jobledger.ledger import read_records
from lei_signal.jobledger.wrap import main as wrap_main, run_wrapped

REPO_ROOT = Path(__file__).resolve().parents[2]


def _spawn_wrapper(ledger: Path, command: list[str], **kwargs) -> subprocess.Popen:
    """以独立进程启动包装器（真实信号/进程组语义）。"""
    return subprocess.Popen(
        [
            sys.executable, "-m", "lei_signal.jobledger.wrap",
            "--job-name", "fixture.nondisruption", "--operation-type", "test",
            "--ledger", str(ledger),
            "--", *command,
        ],
        cwd=REPO_ROOT,
        env={"PYTHONPATH": str(REPO_ROOT / "src"), "PATH": "/usr/bin:/bin",
             **kwargs.pop("extra_env", {})},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        **kwargs,
    )


class TestG1LedgerWriteFailureDegrades:
    def test_unwritable_ledger_keeps_exit_code_and_reports(self, tmp_path, capfd):
        """台账目录不可写：业务只跑一次、退出码不变、stderr 报降级、无续写。"""
        ro = tmp_path / "readonly"
        ro.mkdir()
        ledger = ro / "job-ledger.jsonl"
        os.chmod(ro, 0o500)  # 去掉写权限（等效磁盘/权限错误注入）
        marker = tmp_path / "ran.count"
        try:
            code = wrap_main([
                "--job-name", "fixture.g1", "--operation-type", "test",
                "--ledger", str(ledger),
                "--", sys.executable, "-c",
                f"open({str(marker)!r}, 'a').write('x'); print('biz-out'); "
                "import sys; print('biz-err', file=sys.stderr); sys.exit(3)",
            ])
        finally:
            os.chmod(ro, 0o700)
        # 不改原退出码；业务输出照常透传（不吞业务异常/输出）
        assert code == 3
        captured = capfd.readouterr()
        assert "biz-out" in captured.out
        assert "biz-err" in captured.err
        # stderr 有明确降级信息
        assert "台账写入失败" in captured.err
        assert "降级" in captured.err
        # 业务命令只执行了一次（没有重跑）
        assert marker.read_text() == "x"
        # 失败后没有偷偷写出任何台账文件（含换目录续写）
        assert not ledger.exists()
        assert list(tmp_path.glob("**/*.jsonl")) == []

    def test_success_exit_zero_also_preserved_on_ledger_failure(self, tmp_path, capfd):
        ro = tmp_path / "ro"
        ro.mkdir()
        os.chmod(ro, 0o500)
        try:
            code = wrap_main([
                "--job-name", "fixture.g1b", "--operation-type", "test",
                "--ledger", str(ro / "l.jsonl"),
                "--", sys.executable, "-c", "print('ok')",
            ])
        finally:
            os.chmod(ro, 0o700)
        assert code == 0
        assert "台账写入失败" in capfd.readouterr().err

    def test_forbidden_dir_still_rejected_and_degrades_not_redirects(self, tmp_path, capfd):
        """禁止目录写入被拒后降级返回原退出码，不落到其他目录。"""
        from lei_signal.jobledger import ledger as ledger_mod
        fake_home = tmp_path / "fakehome" / ".lei_signal_lab"
        fake_home.mkdir(parents=True)
        original = ledger_mod.FORBIDDEN_DIR
        ledger_mod.FORBIDDEN_DIR = fake_home
        try:
            code = wrap_main([
                "--job-name", "fixture.g1c", "--operation-type", "test",
                "--ledger", str(fake_home / "x.jsonl"),
                "--", sys.executable, "-c", "import sys; sys.exit(7)",
            ])
        finally:
            ledger_mod.FORBIDDEN_DIR = original
        assert code == 7
        err = capfd.readouterr().err
        assert "台账写入失败" in err
        assert "禁止写入生产目录" in err
        assert not (fake_home / "x.jsonl").exists()
        assert list(tmp_path.glob("**/*.jsonl")) == []


class TestG2SameGroupTopology:
    def test_sigterm_wrapper_forwards_then_supervisor_sweeps_group(self, tmp_path):
        """同组口径（GPT 第 22 轮）：包装器只转发直接子进程并同信号退出；
        整组清扫是监督环境（launchd）的职责。本测试用 start_new_session
        模拟 launchd 的"任务独立进程组"拓扑：包装器退出后，测试扮演监督
        者对整组补一刀，验证该拓扑下零遗留 + 终态恰一条。
        真实 launchd 证据见 docs/ops/job-ledger-diagnosis-2026-09-19.md。
        """
        ledger = tmp_path / "job-ledger.jsonl"
        # sh 是直接子进程，sleep 600 是同组孙进程；测试侧 start_new_session
        # 让包装器成为新组长（模拟 launchd 拓扑），pgid = wrapper pid
        proc = _spawn_wrapper(
            ledger,
            ["/bin/sh", "-c", "sleep 600 >/dev/null 2>&1; exit 0"],
            start_new_session=True,  # 测试侧模拟 launchd 拓扑，非包装器行为
        )
        pgid = proc.pid
        time.sleep(1.0)  # 等 sh/sleep 起来
        os.killpg(pgid, 0)  # 组内确有存活成员
        proc.send_signal(signal.SIGTERM)  # 只发给包装器进程本身
        proc.communicate(timeout=10)
        # 包装器：转发→预算内等待→一条终态→真实信号终止（负返回码）
        assert proc.returncode == -signal.SIGTERM
        records = read_records(ledger)
        assert len(records) == 1
        assert records[0]["status"] == "failed"
        assert records[0]["error_class"] == "killed_by_signal:SIGTERM"
        # 监督者（launchd 角色）清扫整组后：零遗留（sleep 600 同组被回收）
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        deadline = time.time() + 5
        while time.time() < deadline:
            try:
                os.killpg(pgid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.1)
        else:
            os.killpg(pgid, signal.SIGKILL)
            pytest.fail("清扫后孙进程仍在进程组内存活")


class TestG3ChildKilledBySignal:
    def test_child_self_sigkill_classified_as_signal(self, tmp_path):
        """子进程先被 SIGKILL 杀死（包装器未收到信号）：归类 killed_by_signal。"""
        ledger = tmp_path / "job-ledger.jsonl"
        proc = _spawn_wrapper(
            ledger,
            [sys.executable, "-c",
             "import os, signal; os.kill(os.getpid(), signal.SIGKILL)"],
        )
        proc.communicate(timeout=10)
        assert proc.returncode != 0
        records = read_records(ledger)
        assert len(records) == 1
        rec = records[0]
        assert rec["status"] == "failed"
        assert rec["error_class"] == "killed_by_signal:SIGKILL"
        assert not str(rec.get("error_class", "")).startswith("exit_-")

    def test_inprocess_negative_returncode_classification(self, tmp_path):
        code = run_wrapped(
            [sys.executable, "-c",
             "import os, signal; os.kill(os.getpid(), signal.SIGKILL)"],
            job_name="fixture.g3b", operation_type="test",
            input_basis="", output_reference="",
            ledger_path=tmp_path / "l.jsonl",
        )
        assert code == -signal.SIGKILL
        rec = read_records(tmp_path / "l.jsonl")[0]
        assert rec["error_class"] == "killed_by_signal:SIGKILL"
        assert rec["exit_code"] is None


class TestG4StartupContextEquivalence:
    def test_same_command_wrapped_and_bare_identical(self, tmp_path, monkeypatch, capfd):
        """同命令有/无包装：stdout/stderr/退出码一致，env 完整继承，cwd 不变。"""
        monkeypatch.setenv("G4_SENTINEL", "marker-42")
        script = (
            "import os, sys\n"
            "print('env=', os.environ.get('G4_SENTINEL'))\n"
            "print('envsize=', len(os.environ))\n"
            "print('cwd=', os.getcwd())\n"
            "print('argv=', sys.argv[1:])\n"
            "print('err-line', file=sys.stderr)\n"
            "sys.exit(5)\n"
        )
        argv = ["--flag", "值 with space"]
        bare = subprocess.run(
            [sys.executable, "-c", script, *argv],
            capture_output=True, text=True,
        )
        wrapped_code = wrap_main([
            "--job-name", "fixture.g4", "--operation-type", "test",
            "--ledger", str(tmp_path / "l.jsonl"),
            "--", sys.executable, "-c", script, *argv,
        ])
        captured = capfd.readouterr()
        assert wrapped_code == bare.returncode == 5
        assert captured.out == bare.stdout
        assert captured.err == bare.stderr
        # env 完整继承：哨兵变量与整体环境规模一致（未替换 env）
        assert "env= marker-42" in captured.out
        assert f"envsize= {len(os.environ)}" in captured.out
        # cwd 未被包装器替换
        assert f"cwd= {os.getcwd()}" in captured.out
        # 参数原样透传
        assert f"argv= {argv}" in captured.out


class TestG5ConcurrentAppend:
    def test_multiprocess_same_ledger_lines_intact(self, tmp_path):
        """多个包装器进程并发写同一台账：逐行可解析、id 不串写、无半行。"""
        ledger = tmp_path / "job-ledger.jsonl"
        n = 6
        procs = [
            _spawn_wrapper(ledger, [sys.executable, "-c", f"print({i})"])
            for i in range(n)
        ]
        for p in procs:
            p.communicate(timeout=30)
        raw = ledger.read_text(encoding="utf-8")
        lines = raw.splitlines()
        assert len(lines) == n
        parsed = [json.loads(line) for line in lines]  # 无半行截断才全过
        ids = [r["operation_id"] for r in parsed]
        assert len(set(ids)) == n  # operation_id 不串写
        assert all(r["status"] == "success" for r in parsed)
        assert raw.endswith("\n")
