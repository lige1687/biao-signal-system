"""命令包装器：``python -m lei_signal.jobledger.wrap -- <原命令>``。

透传 stdout/stderr 与退出码；结束后写一条完整台账记录（含开始/结束时间、
耗时与 error_class 归类）。被信号杀死（含包装器自身收到 SIGTERM/SIGINT，
先转发仍存活的直接子进程、再在有限停止预算内等其退出）同样落一条
failed 记录，error_class=killed_by_signal:<SIG>，随后包装器恢复默认信号
处理器并向自身重发同信号终止（父进程观察到 returncode=-SIGTERM/-SIGINT，
而非 exit(143)）。

**同组口径（GPT 第 22 轮，2026-09-20）**：子进程不另建会话/进程组，
与包装器同组。该能力**仅在已验证的 launchd 启动拓扑下**成立——launchd
按进程组监督任务，包装器死后剩余同组进程由 launchd 清扫；本包装器不是
通用 Shell 进程树监督器，不保证自行脱离进程组的后代被回收。试点任务
不得启用 AbandonProcessGroup=true。停止预算默认 5 秒（对齐 launchd
ExitTimeOut 默认语义），可用 --stop-budget 或环境变量
LEI_WRAP_STOP_BUDGET 覆盖；预算耗尽后不再等待，剩余进程交监督环境。

用法：
    python -m lei_signal.jobledger.wrap \\
        --job-name com.lei.daily_scan --input-basis close:2026-09-19 \\
        --output-reference table:daily_opportunity_scan -- \\
        /opt/homebrew/bin/python3 scripts/daily_scan.py

可选参数（均可省略）：--job-name / --operation-type / --input-basis /
--output-reference / --ledger <path>（默认走 default_ledger_path）/
--stop-budget <秒>（收到终止信号后等待子进程退出的预算，默认 5.0）。
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from lei_signal.jobledger.ledger import (
    STATUS_FAILED,
    STATUS_SUCCESS,
    JobRecord,
    append_record,
    classify_error,
    new_operation_id,
    utcnow_iso,
)

DEFAULT_STOP_BUDGET_S = 5.0
ENV_STOP_BUDGET = "LEI_WRAP_STOP_BUDGET"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m lei_signal.jobledger.wrap",
        description="包装原命令：透传输出与退出码，运行结束写一条台账记录",
    )
    parser.add_argument("--job-name", default="", help="任务名（launchd label）")
    parser.add_argument(
        "--operation-type", default="launchd_job",
        help="运行形态（launchd_job / manual）",
    )
    parser.add_argument("--input-basis", default="", help="输入截止说明")
    parser.add_argument("--output-reference", default="", help="输出指向（表/文件）")
    parser.add_argument("--ledger", default=None, help="台账路径（默认仓库 logs/）")
    parser.add_argument(
        "--stop-budget", type=float, default=None,
        help="收到终止信号后等待直接子进程退出的秒数预算（默认 5.0，"
             "对齐 launchd ExitTimeOut 默认语义）",
    )
    parser.add_argument(
        "command", nargs=argparse.REMAINDER,
        help="原命令（建议用 -- 分隔）",
    )
    return parser


def _resolve_stop_budget(cli_value: float | None) -> float:
    """停止预算：CLI 优先，其次环境变量，最后默认 5 秒。"""
    if cli_value is not None:
        return max(cli_value, 0.0)
    env = os.environ.get(ENV_STOP_BUDGET)
    if env:
        try:
            return max(float(env), 0.0)
        except ValueError:
            pass
    return DEFAULT_STOP_BUDGET_S


def _flush_quietly() -> None:
    """尽力刷新标准流：解释器退出时的兜底 flush 失败会把退出码改成 120，
    提前刷新并吞掉刷新异常可保住业务退出码（业务输出已透传完毕）。
    flush 失败后缓冲里可能仍留着数据（关闭流丢弃，避免解释器收尾重试
    再失败一次）。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except (OSError, ValueError):
            try:
                stream.close()
            except (OSError, ValueError):
                pass


def run_wrapped(
    argv: list[str],
    *,
    job_name: str,
    operation_type: str,
    input_basis: str,
    output_reference: str,
    ledger_path: Path | None = None,
    stop_budget_s: float = DEFAULT_STOP_BUDGET_S,
) -> int:
    """执行子命令并写台账，返回与子命令一致的退出码（被杀时重发信号）。

    退出时序契约（GPT 第 22 轮冻结）：
    收到 SIGTERM/SIGINT → 转发仍存活的直接子进程 → 在停止预算内等其退出
    （不无限 wait）→ 尽力写一条终态 → 恢复默认处理器后向自身重发同信号
    （父进程观察到负返回码）→ 剩余同组进程交监督环境（launchd）清扫。
    """
    if not argv:
        try:
            print("wrap: 缺少要包装的命令", file=sys.stderr)
        except OSError:
            pass
        return 2
    operation_id = new_operation_id()
    started_at = utcnow_iso()
    t0 = time.monotonic()
    killed_by: str | None = None
    kill_deadline: float | None = None
    budget_exhausted = False

    # 子进程与包装器同组（不 start_new_session）：launchd 按组监督任务，
    # 包装器死后剩余同组成员由 launchd 清扫；包装器自身只负责转发信号给
    # 直接子进程，不做整组监督（同组口径见模块 docstring）。
    proc = subprocess.Popen(argv)

    def _forward(signum: int, _frame: object) -> None:
        nonlocal killed_by, kill_deadline
        if killed_by is None:
            killed_by = signal.Signals(signum).name
            kill_deadline = time.monotonic() + stop_budget_s
        # 只转发给直接子进程；重入（预算内再次收到信号）不重置预算
        if proc.poll() is None:
            try:
                proc.send_signal(signum)
            except (ProcessLookupError, OSError):
                pass

    prev_term = signal.signal(signal.SIGTERM, _forward)
    prev_int = signal.signal(signal.SIGINT, _forward)
    try:
        while True:
            try:
                returncode = proc.wait(timeout=0.2)
                break
            except subprocess.TimeoutExpired:
                if killed_by is not None and time.monotonic() > (kill_deadline or 0.0):
                    # 停止预算耗尽：不再无限等待，剩余进程交监督环境清扫
                    budget_exhausted = True
                    returncode = None
                    break
    finally:
        signal.signal(signal.SIGTERM, prev_term)
        signal.signal(signal.SIGINT, prev_int)

    finished_at = utcnow_iso()
    duration_ms = int((time.monotonic() - t0) * 1000)
    child_signal: str | None = None
    if killed_by is not None:
        status, exit_code = STATUS_FAILED, None
        error_class = classify_error(signal=killed_by)
    elif returncode == 0:
        status, exit_code, error_class = STATUS_SUCCESS, 0, "none"
    elif returncode is not None and returncode < 0:
        # 子进程先被外部信号杀死（包装器未收到信号）：负返回码按信号归类，
        # 不能误记成 "exit_-15" 这类数字退出错误
        child_signal = signal.Signals(-returncode).name
        status, exit_code = STATUS_FAILED, None
        error_class = classify_error(signal=child_signal)
    else:
        status, exit_code = STATUS_FAILED, returncode
        error_class = classify_error(returncode=returncode)

    record = JobRecord(
        operation_id=operation_id,
        operation_type=operation_type,
        started_at=started_at,
        finished_at=finished_at,
        status=status,
        input_basis=input_basis,
        output_reference=output_reference,
        error_class=error_class,
        job_name=job_name,
        extra={
            "command": argv,
            "exit_code": exit_code,
            "duration_ms": duration_ms,
        },
    )
    if budget_exhausted:
        record.extra["stop_budget_exhausted"] = True
    try:
        append_record(record, ledger_path)
    except OSError as exc:
        # 台账写失败降级：不重跑业务命令、不吞业务结果、不改原退出码、
        # 不换目录续写。诊断提示本身独立保护——写不出（如满盘连 stderr 也
        # 不可写）时允许无提示，但必须继续既定退出路径（GPT 第 24 轮）。
        try:
            print(
                f"wrap: 台账写入失败（降级为不记录，业务退出码保持不变）: {exc}",
                file=sys.stderr,
            )
        except OSError:
            pass
    # 退出前尽力刷新：诊断流故障不能把退出码变成 120（提前冲掉缓冲，
    # 解释器收尾的 flush 就没有剩余数据可失败）
    _flush_quietly()
    if killed_by is not None:
        # 真实信号终止：恢复默认处理器后向自身重发同信号，父进程/launchd
        # 观察到的是被信号杀死（returncode=-SIGTERM/-SIGINT），非 exit(143)
        term_sig = signal.Signals[killed_by]
        signal.signal(term_sig, signal.SIG_DFL)
        os.kill(os.getpid(), term_sig.value)
    return returncode


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    cmd = list(args.command)
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    ledger = Path(args.ledger) if args.ledger else None
    return run_wrapped(
        cmd,
        job_name=args.job_name,
        operation_type=args.operation_type,
        input_basis=args.input_basis,
        output_reference=args.output_reference,
        ledger_path=ledger,
        stop_budget_s=_resolve_stop_budget(args.stop_budget),
    )


if __name__ == "__main__":
    raise SystemExit(main())
