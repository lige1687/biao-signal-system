"""J2 fixture 备份恢复演练脚本的单元测试（机制验收，不碰生产库）。"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "archive" / "sqlite_backup_restore_drill.py"

_spec = importlib.util.spec_from_file_location("sqlite_backup_restore_drill", SCRIPT)
drill = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(drill)


def test_drill_closes_loop_and_is_idempotent() -> None:
    # 连跑两遍：既验证备份→恢复→校验闭环，也验证重跑不残留脏状态
    for _ in range(2):
        report = drill.run_drill()
        assert report["ok"] is True
        assert report["integrity_check"] == "ok"
        assert report["rows_match"] is True
        assert report["restored_rows"] == report["source_rows_at_backup"]
        # 在线语义：备份期间的并发写入应包含在备份快照里
        assert report["concurrent_write_during_backup"] is True
        # 缺失窗口：备份完成后的写入不应出现在既有备份里
        assert report["late_write_in_backup"] is False


def test_drill_never_touches_production_path(tmp_path: Path) -> None:
    keep = tmp_path / "drill_out"
    report = drill.run_drill(keep_dir=keep)
    assert report["ok"] is True
    produced = [p.name for p in keep.rglob("*") if p.is_file()]
    # 全部产物都在演练目录内；生产路径 ~/.lei_signal_lab 不应出现任何写入
    assert all(str(p).startswith(str(keep)) for p in keep.rglob("*"))
    assert "lab.db" in produced
