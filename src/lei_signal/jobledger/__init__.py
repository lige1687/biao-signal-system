"""任务运行台账（Job Execution Provenance）。

目标：让每个定时任务的运行成为可查事实——谁/何时/多久/成败/输入截止/
输出指向。只追加 JSONL，落仓库 ``logs/job-ledger.jsonl``（已 gitignore），
绝不写 ``~/.lei_signal_lab/`` 生产目录。

本包自包含：不 import copilot / agent / storage 等在办线模块。
"""
from lei_signal.jobledger.ledger import (
    JobRecord,
    append_record,
    classify_error,
    default_ledger_path,
)

__all__ = [
    "JobRecord",
    "append_record",
    "classify_error",
    "default_ledger_path",
]
