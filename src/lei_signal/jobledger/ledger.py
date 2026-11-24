"""台账核心：字段规范 + 只追加 JSONL 写入器（纯函数，可单测）。"""
from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

#: status 固定枚举
STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"
STATUS_PARTIAL = "partial"
VALID_STATUSES = frozenset({STATUS_SUCCESS, STATUS_FAILED, STATUS_PARTIAL})

#: ISO-8601 带时区（本机时区），可排序、可解析
_TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)$"
)

#: 环境变量可覆盖台账路径（测试用）；默认仓库 logs/job-ledger.jsonl
ENV_LEDGER_PATH = "LEI_JOB_LEDGER_PATH"

#: 生产红线目录：台账绝不写入
FORBIDDEN_DIR = Path.home() / ".lei_signal_lab"

_REPO_ROOT = Path(__file__).resolve().parents[3]


def utcnow_iso() -> str:
    """当前时间 ISO-8601（本机时区偏移）。"""
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")


def new_operation_id() -> str:
    return uuid.uuid4().hex


def default_ledger_path() -> Path:
    """台账落盘位置：环境变量优先，否则仓库 logs/job-ledger.jsonl。"""
    env = os.environ.get(ENV_LEDGER_PATH)
    if env:
        return Path(env)
    return _REPO_ROOT / "logs" / "job-ledger.jsonl"


@dataclass
class JobRecord:
    """一次任务运行的一条台账事实。

    字段规范（W1-S1 冻结）：
    - operation_id: 本次运行的唯一标识（uuid4 hex）
    - operation_type: 运行形态（launchd_job / manual / test 等）
    - started_at / finished_at: ISO-8601 带时区
    - status: success | failed | partial
    - input_basis: 输入截止说明（数据截至哪天/哪个时点，如 "close:2026-09-18"）
    - output_reference: 输出指向（表名或文件路径）
    - error_class: 失败归类（成功固定 "none"）
    - job_name: 任务名（如 launchd label "com.lei.daily_scan"）
    """

    operation_id: str
    operation_type: str
    started_at: str
    finished_at: str
    status: str
    input_basis: str = ""
    output_reference: str = ""
    error_class: str = "none"
    job_name: str = ""
    extra: dict = field(default_factory=dict)

    def validate(self) -> None:
        missing = [
            name
            for name in (
                "operation_id",
                "operation_type",
                "started_at",
                "finished_at",
                "status",
                "error_class",
                "job_name",
            )
            if not getattr(self, name)
        ]
        if missing:
            raise ValueError(f"字段缺失: {missing}")
        if self.status not in VALID_STATUSES:
            raise ValueError(f"status 非法: {self.status!r}，允许 {sorted(VALID_STATUSES)}")
        for name in ("started_at", "finished_at"):
            if not _TIMESTAMP_RE.match(getattr(self, name)):
                raise ValueError(f"{name} 不是带时区的 ISO-8601: {getattr(self, name)!r}")
        if self.finished_at < self.started_at:
            raise ValueError("finished_at 早于 started_at")
        if self.status == STATUS_SUCCESS and self.error_class != "none":
            raise ValueError("success 记录的 error_class 必须为 'none'")
        if self.status != STATUS_SUCCESS and self.error_class == "none":
            raise ValueError("非 success 记录必须给出 error_class")


def classify_error(*, returncode: int | None = None, signal: str | None = None) -> str:
    """纯函数：由退出码 / 致命信号归类失败原因。

    - 被信号杀死：``killed_by_signal:<SIGTERM>`` 等
    - 退出码 1：``exit_1``（脚本自身异常，最常见）
    - 其余：``exit_<code>``
    """
    if signal:
        return f"killed_by_signal:{signal}"
    if returncode is None:
        return "unknown"
    return f"exit_{returncode}"


def append_record(record: JobRecord, path: Path | None = None) -> Path:
    """校验后只追加写入一行 JSON，返回台账路径。

    - 只追加，绝不改写既有行；
    - 目标目录不存在则创建；
    - 红线：目标在 ~/.lei_signal_lab/ 下直接拒绝。
    """
    record.validate()
    target = Path(path) if path is not None else default_ledger_path()
    resolved = target.resolve()
    forbidden = FORBIDDEN_DIR.resolve()
    if resolved == forbidden or forbidden in resolved.parents:
        raise PermissionError(f"台账禁止写入生产目录: {resolved}")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    payload = {k: v for k, v in asdict(record).items() if k != "extra"}
    payload.update(record.extra)
    with resolved.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return resolved


def read_records(path: Path) -> list[dict]:
    """读回台账（测试/巡检用）；坏行跳过但不静默：记到 ``_parse_errors`` 尾项。"""
    out: list[dict] = []
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as exc:  # noqa: PERF203
            out.append({"_parse_errors": str(exc)})
    return out
