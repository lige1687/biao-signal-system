"""``scripts/run_research_data_snapshot.py`` 的端到端集成测试。

覆盖「导入 → 快照 → 校验 → 离线复用」完整闭环，以及输出目录防覆盖。
全程离线；联网子命令只测它默认关闭这一行为，不真的发请求。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/run_research_data_snapshot.py"


def _run(*args, expect: int = 0):
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert proc.returncode == expect, (
        f"exit={proc.returncode}\nstdout={proc.stdout}\nstderr={proc.stderr}"
    )
    return proc


@pytest.fixture
def small_csv(tmp_path) -> Path:
    """两只标的、各 3 行的最小合法输入（手写，不依赖仓库数据）。"""
    rows = []
    for symbol, base in (("510300.SS", 4.0), ("512890.SS", 1.0)):
        for i, day in enumerate(("2026-09-01", "2026-09-02", "2026-09-03")):
            close = base + i * 0.1
            rows.append(
                {
                    "date": day,
                    "symbol": symbol,
                    "open": close,
                    "high": close + 0.1,
                    "low": close - 0.1,
                    "close": close,
                    "volume": 1000 + i,
                }
            )
    path = tmp_path / "prices.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def test_full_loop_import_snapshot_validate_offline_reuse(small_csv, tmp_path):
    out = tmp_path / "snap"

    # 1) 导入 → 快照 → 校验
    proc = _run("import", "--csv", str(small_csv), "--out", str(out))
    assert "snapshot:" in proc.stdout

    snapshot = json.loads((out / "snapshot.json").read_text(encoding="utf-8"))
    assert snapshot["mode"] == "import"
    assert snapshot["transform_version"] == "research-data-snapshot/1.0"
    # 手算：2 只 × 3 行 = 6 行
    assert sum(i["rows"] for i in snapshot["instruments"]) == 6
    # 源文件指纹被记录，且标为只读
    assert snapshot["source"]["import_source"]["read_only"] is True
    assert len(snapshot["source"]["import_source"]["sha256"]) == 64
    # 四类时间语义齐备，且导入模式不冒充「本次取得」
    for ref in snapshot["market_data_refs"].values():
        assert ref["available_at"] is None
        assert ref["fetched_at"] is None
        assert ref["health"] == "unknown"

    quality = json.loads((out / "quality-report.json").read_text(encoding="utf-8"))
    assert quality["blocked_instruments"] == []

    # 2) 完全离线复用：不读源 CSV，只读快照目录
    small_csv.unlink()
    verify = _run("verify", "--snapshot", str(out))
    assert "verified: True" in verify.stdout


def test_output_directory_is_never_overwritten(small_csv, tmp_path):
    out = tmp_path / "snap"
    _run("import", "--csv", str(small_csv), "--out", str(out))
    first = json.loads((out / "snapshot.json").read_text(encoding="utf-8"))

    _run("import", "--csv", str(small_csv), "--out", str(out))
    bumped = out.parent / "snap-01"
    assert bumped.is_dir(), "第二次运行必须落到新目录"
    # 旧目录内容原封不动
    assert json.loads((out / "snapshot.json").read_text(encoding="utf-8")) == first


def test_verify_fails_on_tampered_snapshot(small_csv, tmp_path):
    out = tmp_path / "snap"
    _run("import", "--csv", str(small_csv), "--out", str(out))
    target = out / "normalized" / "510300.SS.csv"
    original = target.read_text(encoding="utf-8")
    tampered = original.replace("4.0", "9.9")
    assert tampered != original, "测试自身必须真的改到内容"
    target.write_text(tampered, encoding="utf-8")
    _run("verify", "--snapshot", str(out), expect=1)


def test_diff_reports_identical_for_two_equal_imports(small_csv, tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    _run("import", "--csv", str(small_csv), "--out", str(a))
    _run("import", "--csv", str(small_csv), "--out", str(b))
    proc = _run("diff", "--old", str(a), "--new", str(b))
    assert json.loads(proc.stdout)["identical"] is True


def test_network_branch_is_off_by_default():
    """联网必须显式确认，默认不发任何请求。"""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "acquire", "--symbols", "510300.SS"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert proc.returncode == 2
    assert "--yes-network" in proc.stderr


def test_bind_rejects_unknown_and_wrong_version():
    proc = _run(
        "bind", "--refs", "mixed.momentum.raw@1.0.0", "mixed.momentum.raw@9.9.9",
        "--purpose", "description",
    )
    payload = json.loads(proc.stdout)
    good = payload["bindings"]["mixed.momentum.raw@1.0.0"]
    bad = payload["bindings"]["mixed.momentum.raw@9.9.9"]
    assert good["resolved"] is True
    assert bad["resolved"] is False
    # 名义价不能直接满足需要 economic_index 的对象——如实报告，不贴「已接入」
    assert good["directly_satisfiable"] is False
    assert "economic_index" in good["missing_fields"]


def test_bind_requires_exact_version():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "bind", "--refs", "mixed.momentum.raw"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert proc.returncode != 0
    assert "id@version" in (proc.stderr + proc.stdout)
