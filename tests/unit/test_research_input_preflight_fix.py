"""主控复核单 F1/F2 的修复守卫（research-input-preflight-2026-09-13-fix-01）。

F1：来源核验失败不能只写进限制——对请求对象所需的来源核验失败，
    必须影响该对象及最终结果。
F2：失败出口合同——参数/日期错误与输出 I/O 失败都返回 3，
    且不留下"完成"假象。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from lei_signal.research.input_preflight import inspect_input

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/check_research_input.py"
REAL_REGISTRY = ROOT / "docs/research/definitions.v1.json"


# ---------------------------------------------------------------------------
# 合成输入（恒定名义价 + 恒定经济指数列，仅算法测试，不是真实资料）
# ---------------------------------------------------------------------------


def _make_economic_snapshot(tmp_path: Path) -> Path:
    snap = tmp_path / "snap"
    (snap / "normalized").mkdir(parents=True)
    rows = [
        {"date": "2026-06-01", "open": 10.0, "high": 11.0, "low": 9.0,
         "close": 10.0, "volume": 100.0, "economic_index": 1.0},
        {"date": "2026-06-02", "open": 10.0, "high": 11.0, "low": 9.0,
         "close": 10.0, "volume": 100.0, "economic_index": 1.0},
    ]
    cols = ["date", "open", "high", "low", "close", "volume", "economic_index"]
    text = ",".join(cols) + "\n" + "".join(
        ",".join(str(r[c]) for c in cols) + "\n" for r in rows
    )
    rel = "normalized/510300.SS.csv"
    (snap / rel).write_text(text, encoding="utf-8")
    payload = {
        "schema_version": "research-data-snapshot/1.0",
        "transform_version": "research-data-snapshot/1.0",
        "mode": "import",
        "semantics": {
            "fields": cols,
            "currency": "CNY", "price_basis": "nominal_close",
            "trading_calendar": {"authority": "none"},
        },
        "instruments": [{
            "instrument_id": "510300.SS", "rows": 2,
            "first_date": "2026-06-01", "last_date": "2026-06-02",
            "normalized": {"path": rel,
                           "sha256": hashlib.sha256(text.encode()).hexdigest()},
            "raw_responses": [],
            "provider_report": {"provider": "t", "adjusted": False,
                                "duplicates_removed": 0, "warnings": []},
        }],
        "uses": ["description", "diagnostic"],
        "not_for": ["production_trade"],
        "market_data_refs": {},
    }
    (snap / "snapshot.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return snap


def _make_calendar(tmp_path: Path) -> Path:
    import calendar as _cal
    from datetime import date

    days = {}
    for d in range(1, _cal.monthrange(2026, 6)[1] + 1):
        day = date(2026, 6, d)
        tr = day.weekday() < 5
        days[day.isoformat()] = {
            "is_trading_day": tr, "source_flag": "1" if tr else "0",
            "source_month": "2026-06",
        }
    p = tmp_path / "calendar.json"
    p.write_text(json.dumps({
        "authority": "exchange_official", "publisher": "合成测试日历",
        "months_requested": ["2026-06"], "months_failed": [], "days": days,
    }), encoding="utf-8")
    return p


def _corrupted_registry(tmp_path: Path) -> Path:
    """复制真实登记表，仅把 mixed_code 来源的 SHA-256 改成 64 个 0。

    原登记表与来源文件不动；这份是隔离测试副本，不是第二份权威登记。
    """
    payload = json.loads(REAL_REGISTRY.read_text(encoding="utf-8"))
    assert payload["sources"]["mixed_code"]["sha256"] != "0" * 64
    payload["sources"]["mixed_code"]["sha256"] = "0" * 64
    out = tmp_path / "registry-corrupted.json"
    out.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return out


def _inspect(snap, cal, registry, refs=("mixed.price.economic@1.0.0",)):
    return inspect_input(
        snapshot_dir=snap, calendar_path=cal, publication_path=None,
        actions_path=None, registry_path=registry, refs=refs,
        use="description", evaluation_start="2026-06-01",
        evaluation_end="2026-06-30",
    )


# ---------------------------------------------------------------------------
# F1：正确指纹控制组必须成功；错指纹必须被拒
# ---------------------------------------------------------------------------


def test_f1_control_group_with_correct_source_fingerprints(tmp_path):
    report = _inspect(_make_economic_snapshot(tmp_path),
                      _make_calendar(tmp_path), REAL_REGISTRY)
    assert report["registry"]["sources_verified"] is True
    assert report["errors"] == []
    obj = report["objects"]["mixed.price.economic@1.0.0"]
    assert obj["resolved"] is True and obj["directly_satisfiable"] is True
    assert report["request_satisfied"] is True


def test_f1_corrupted_source_fingerprint_rejects_object_request(tmp_path):
    """主控反例：mixed_code 指纹错误时不得继续返回满足。"""
    report = _inspect(_make_economic_snapshot(tmp_path),
                      _make_calendar(tmp_path),
                      _corrupted_registry(tmp_path))
    assert report["registry"]["sources_verified"] is False
    assert report["request_satisfied"] is False, (
        "来源核验失败不能只写进限制而照样满足"
    )
    assert report["errors"] or report["registry"].get("sources_error"), (
        "来源失败的具体文件与原因必须可见"
    )
    obj = report["objects"]["mixed.price.economic@1.0.0"]
    assert obj.get("blocked_by") == "sources_unverified"


def test_f1_cli_never_exits_zero_on_source_failure(tmp_path):
    out = tmp_path / "o"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT),
         "--snapshot", str(_make_economic_snapshot(tmp_path)),
         "--calendar", str(_make_calendar(tmp_path)),
         "--registry", str(_corrupted_registry(tmp_path)),
         "--start", "2026-06-01", "--end", "2026-06-30",
         "--use", "description", "--out", str(out),
         "--refs", "mixed.price.economic@1.0.0"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert proc.returncode != 0, "错指纹的对象请求不得退出 0"
    report = json.loads((out / "preflight.json").read_text())
    assert report["request_satisfied"] is False


def test_f1_data_only_path_unaffected_without_refs(tmp_path):
    """显式传了失败登记表但没有对象：对象阶段不可用，独立数据结论保留。"""
    report = _inspect(_make_economic_snapshot(tmp_path),
                      _make_calendar(tmp_path),
                      _corrupted_registry(tmp_path), refs=())
    assert report["registry"]["sources_verified"] is False
    assert report["registry"]["objects_stage"] == "skipped_no_refs"
    # 无对象请求时，数据描述正向路径不被来源失败拖住
    assert report["request_satisfied"] is True
    assert any("对象阶段" in x or "sources" in x for x in report["limitations"])


# ---------------------------------------------------------------------------
# F2：参数/日期错误与输出失败都返回 3
# ---------------------------------------------------------------------------


def test_f2_reversed_range_without_calendar_fails_as_input_error(tmp_path):
    """无日历时区间倒置同样必须是输入错误（errors 非空），不是正常数据拒绝。"""
    snap = _make_economic_snapshot(tmp_path)
    report = inspect_input(
        snapshot_dir=snap, calendar_path=None, publication_path=None,
        actions_path=None, registry_path=None, refs=(),
        use="description", evaluation_start="2026-06-30",
        evaluation_end="2026-06-01",
    )
    assert report["request_satisfied"] is False
    assert report["errors"], "起止倒置必须留下明确失败原因"
    assert any("evaluation" in e["stage"] or "日期" in e["error"]
               or "倒置" in e["error"] for e in report["errors"])


def test_f2_cli_reversed_range_without_calendar_exits_3(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(SCRIPT),
         "--snapshot", str(_make_economic_snapshot(tmp_path)),
         "--start", "2026-06-30", "--end", "2026-06-01",
         "--use", "description", "--out", str(tmp_path / "o")],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert proc.returncode == 3, f"无日历倒置应退出 3，实际 {proc.returncode}"


def test_f2_bad_cli_argument_exits_3_not_2(tmp_path):
    """非法参数属于输入错误（3），不得与'正常检查被拒'(2) 混淆。"""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--no-such-flag"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert proc.returncode == 3, f"非法参数应退出 3，实际 {proc.returncode}"


def test_f2_help_exits_zero(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert proc.returncode == 0


def test_f2_markdown_write_failure_exits_3_with_failure_marker(tmp_path):
    """preflight.json 写成后 preflight.md 写入失败：

    必须退出 3、stderr 明确失败、不得留下 request_satisfied=true 的完整假象。
    """
    snap = _make_economic_snapshot(tmp_path)
    cal = _make_calendar(tmp_path)
    runner = tmp_path / "runner.py"
    runner.write_text(
        "import sys, runpy\n"
        "from pathlib import Path\n"
        "sys.argv = ['check', '--snapshot', " + repr(str(snap)) + ","
        " '--calendar', " + repr(str(cal)) + ","
        " '--start', '2026-06-01', '--end', '2026-06-30',"
        " '--use', 'description', '--out', " + repr(str(tmp_path / 'o')) + "]\n"
        "import scripts.check_research_input as cli\n"  # noqa
        "orig = cli._render_markdown\n"
        "def boom(report):\n"
        "    raise OSError('simulated disk failure')\n"
        "cli._render_markdown = boom\n"
        "raise SystemExit(cli.main())\n",
        encoding="utf-8",
    )
    # 用包方式导入要求 scripts 可导入；改为直接 run_path + 预置模块替换
    runner.write_text(
        "import sys\n"
        "from pathlib import Path\n"
        "sys.path.insert(0, " + repr(str(ROOT)) + ")\n"
        "sys.argv = ['check', '--snapshot', " + repr(str(snap)) + ","
        " '--calendar', " + repr(str(cal)) + ","
        " '--start', '2026-06-01', '--end', '2026-06-30',"
        " '--use', 'description', '--out', " + repr(str(tmp_path / 'o')) + "]\n"
        "sys.path.insert(0, " + repr(str(ROOT / 'scripts')) + ")\n"
        "import check_research_input as cli\n"
        "cli._render_markdown = lambda report: (_ for _ in ()).throw("
        "OSError('simulated disk failure'))\n"
        "raise SystemExit(cli.main())\n",
        encoding="utf-8",
    )
    proc = subprocess.run([sys.executable, str(runner)],
                          capture_output=True, text=True, cwd=ROOT)
    assert proc.returncode == 3, f"写出失败应退出 3，实际 {proc.returncode}\n{proc.stderr}"
    assert "失败" in proc.stderr or "fail" in proc.stderr.lower()
    # 不得留下成功 manifest
    assert not (tmp_path / "o/manifest.json").exists()
    # 能安全记录时保留失败标记
    assert (tmp_path / "o/FAILED.txt").exists()


# ---------------------------------------------------------------------------
# F3/F4 见 tests/integration/test_research_input_preflight_cli.py 的补充用例
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# F4：测试证据校正
# ---------------------------------------------------------------------------


def test_f4_same_path_changed_input_yields_different_identity(tmp_path):
    """真正的同一路径：先后改变输入内容，两次检查的身份必须不同。"""
    import subprocess as _sp

    snap = _make_economic_snapshot(tmp_path)
    cal = _make_calendar(tmp_path)
    csv = snap / "normalized" / "510300.SS.csv"
    before = csv.read_bytes()

    out1 = tmp_path / "o1"
    _sp.run([sys.executable, str(SCRIPT), "--snapshot", str(snap),
             "--calendar", str(cal), "--start", "2026-06-01",
             "--end", "2026-06-30", "--use", "description", "--out", str(out1)],
            capture_output=True, text=True, cwd=ROOT)

    # 改内容并同步哈希（合法修订，不是篡改）
    text = csv.read_text(encoding="utf-8") + "2026-06-03,10.0,11.0,9.0,10.0,100.0,1.0\n"
    csv.write_text(text, encoding="utf-8")
    assert csv.read_bytes() != before, "测试自身必须真的改到内容"
    snap_json = snap / "snapshot.json"
    payload = json.loads(snap_json.read_text(encoding="utf-8"))
    payload["instruments"][0]["normalized"]["sha256"] = hashlib.sha256(
        text.encode()).hexdigest()
    payload["instruments"][0]["rows"] = 3
    payload["instruments"][0]["last_date"] = "2026-06-03"
    snap_json.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    out2 = tmp_path / "o2"
    _sp.run([sys.executable, str(SCRIPT), "--snapshot", str(snap),
             "--calendar", str(cal), "--start", "2026-06-01",
             "--end", "2026-06-30", "--use", "description", "--out", str(out2)],
            capture_output=True, text=True, cwd=ROOT)

    a = json.loads((out1 / "preflight.json").read_text())
    b = json.loads((out2 / "preflight.json").read_text())
    assert a["integrity"]["rows"] == 2
    assert b["integrity"]["rows"] == 3
    ma = json.loads((out1 / "manifest.json").read_text())
    mb = json.loads((out2 / "manifest.json").read_text())
    assert ma["input_hashes"]["snapshot_json"] != mb["input_hashes"]["snapshot_json"]


def test_f4_counterexample_fingerprints_locked():
    """两份主控反例的指纹必须等于主控公布值，不能只查存在。"""
    expected = {
        "listing-explicit-synthetic.json":
            "bdd9348897f388dd573b5cd097579f60ae7448d4627812ca4523bdb15579b1f1",
        "listing-qualification-omitted.json":
            "3b6520db7cc550dc322c5c603604522a029c1b9fa8cad23820fd75e355f2e9cc",
    }
    base = (ROOT / "docs/experiments/raw"
            / "research-data-foundation-controller-review-2026-09-13")
    for name, want in expected.items():
        got = hashlib.sha256((base / name).read_bytes()).hexdigest()
        assert got == want, f"{name} 指纹已变：{got[:16]}…"


def test_f4_offline_guard_self_verifies_then_runs(tmp_path):
    """断网守卫必须先自证：尝试连接必须被它拒绝，然后才能跑入口。"""
    snap = _make_economic_snapshot(tmp_path)
    cal = _make_calendar(tmp_path)
    guard = tmp_path / "guard.py"
    guard.write_text(
        "import socket, runpy, sys\n"
        "def _blocked(*a, **k):\n"
        "    raise RuntimeError('network blocked by test guard')\n"
        "socket.socket = _blocked\n"
        "socket.create_connection = _blocked\n"
        "socket.getaddrinfo = _blocked\n"
        "# 自检：守卫必须先证明自己真的拦得住\n"
        "try:\n"
        "    socket.socket()\n"
        "    print('GUARD_BROKEN', file=sys.stderr); sys.exit(9)\n"
        "except RuntimeError:\n"
        "    print('guard self-check ok', file=sys.stderr)\n"
        "sys.argv = ['check', '--snapshot', " + repr(str(snap)) + ","
        " '--calendar', " + repr(str(cal)) + ","
        " '--start', '2026-06-01', '--end', '2026-06-30',"
        " '--use', 'description', '--out', " + repr(str(tmp_path / 'o')) + "]\n"
        "runpy.run_path(" + repr(str(SCRIPT)) + ", run_name='__main__')\n",
        encoding="utf-8",
    )
    proc = subprocess.run([sys.executable, str(guard)],
                          capture_output=True, text=True, cwd=ROOT)
    assert "guard self-check ok" in proc.stderr, proc.stderr
    assert proc.returncode == 0, proc.stderr
    report = json.loads((tmp_path / "o/preflight.json").read_text())
    assert report["request_satisfied"] is True


def test_f4_empty_snapshot_zero_instruments_is_explicit(tmp_path):
    """空快照（目录合法但零标的）：明确结果，不得空成功。"""
    snap = tmp_path / "snap"
    (snap / "normalized").mkdir(parents=True)
    (snap / "snapshot.json").write_text(json.dumps({
        "schema_version": "research-data-snapshot/1.0",
        "transform_version": "research-data-snapshot/1.0",
        "mode": "import",
        "semantics": {"fields": ["date", "open", "high", "low", "close", "volume"],
                      "currency": "CNY", "price_basis": "nominal_close",
                      "trading_calendar": {"authority": "none"}},
        "instruments": [], "uses": ["description"], "not_for": [],
        "market_data_refs": {},
    }), encoding="utf-8")
    report = inspect_input(
        snapshot_dir=snap, calendar_path=_make_calendar(tmp_path),
        publication_path=None, actions_path=None, registry_path=None,
        refs=(), use="description",
        evaluation_start="2026-06-01", evaluation_end="2026-06-30",
    )
    assert report["integrity"]["instruments"] == []
    assert report["integrity"]["rows"] == 0
    # 空输入不得被当作"满足"放行
    assert report["request_satisfied"] is False


def test_f4_calendar_missing_day_inside_range_is_visible(tmp_path):
    """区间内漏日：含该日报价的输入必须被拦，不被当成正常。"""
    snap = _make_economic_snapshot(tmp_path)
    cal = _make_calendar(tmp_path)
    # 删掉 2026-06-02（快照里有这天的报价）
    payload = json.loads(cal.read_text(encoding="utf-8"))
    assert payload["days"].pop("2026-06-02") is not None
    cal.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    report = inspect_input(
        snapshot_dir=snap, calendar_path=cal, publication_path=None,
        actions_path=None, registry_path=None, refs=(),
        use="description", evaluation_start="2026-06-01",
        evaluation_end="2026-06-30",
    )
    codes = {f["code"] for f in report["findings"]}
    assert "quote_on_unknown_calendar_day" in codes
    assert report["calendar"]["day_incomplete_months"] == ["2026-06"]


# ---------------------------------------------------------------------------
# Task 1（动量样板轮）：manifest 写出与 --protocol 校验
# ---------------------------------------------------------------------------


def _cli_runner(tmp_path: Path, snap, cal, out, monkey_target: str) -> Path:
    """构造一个在指定写出点失败的子进程脚本。"""
    snap, cal, out = str(snap), str(cal), str(out)
    runner = tmp_path / f"runner-{monkey_target}.py"
    patches = {
        "json": "cli._write_json = _boom",
        "markdown": (
            "def _boom_md(report):\n"
            "    raise OSError('simulated md failure')\n"
            "cli._render_markdown = _boom_md\n"
        ),
        "manifest": "cli._write_json = _boom_manifest",
    }
    body = (
        "import sys\n"
        f"sys.path.insert(0, {str(ROOT / 'scripts')!r})\n"
        "import check_research_input as cli\n"
        "def _boom(path, obj):\n"
        "    raise OSError('simulated json failure')\n"
        "def _boom_manifest(path, obj):\n"
        "    if str(path).endswith('manifest.json'):\n"
        "        raise OSError('SYNTHETIC manifest disk failure')\n"
        "    return _orig(path, obj)\n"
        "_orig = cli._write_json\n"
        f"{patches[monkey_target]}\n"
        f"sys.argv = ['check', '--snapshot', {snap!r}, '--calendar', {cal!r},"
        f" '--start', '2026-06-01', '--end', '2026-06-30',"
        f" '--use', 'description', '--out', {out!r}]\n"
        "raise SystemExit(cli.main())\n"
    )
    runner.write_text(body, encoding="utf-8")
    return runner


def _run_cli(args):
    return subprocess.run(args, capture_output=True, text=True, cwd=ROOT)


@pytest.mark.parametrize("point", ["json", "markdown", "manifest"])
def test_t1_each_write_stage_failure_exits_3(tmp_path, point):
    """JSON / Markdown / manifest 三个写出点各自失败：退出 3、
    无 manifest、stderr 明确、可写目录有 FAILED.txt。"""
    snap = _make_economic_snapshot(tmp_path)
    cal = _make_calendar(tmp_path)
    out = tmp_path / "o"
    runner = _cli_runner(tmp_path, snap, cal, out, point)
    proc = _run_cli([sys.executable, str(runner)])
    assert proc.returncode == 3, f"{point} 失败应退出 3，实际 {proc.returncode}\n{proc.stderr}"
    assert "失败" in proc.stderr or "failure" in proc.stderr.lower()
    assert not (out / "manifest.json").exists()
    assert (out / "FAILED.txt").exists()


def test_t1_mkdir_unwritable_exits_3_without_requiring_marker(tmp_path):
    """输出目录不可创建：退出 3；此时不要求 FAILED.txt 能被写出来。"""

    snap = _make_economic_snapshot(tmp_path)
    cal = _make_calendar(tmp_path)
    out = tmp_path / "nowrite" / "o"
    runner = tmp_path / "runner-mkdir.py"
    runner.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(ROOT / 'scripts')!r})\n"
        "import check_research_input as cli\n"
        "from pathlib import Path as _P\n"
        "def _boom_mkdir(self, *a, **k):\n"
        "    raise OSError('simulated mkdir failure')\n"
        "_P.mkdir = _boom_mkdir\n"
        f"sys.argv = ['check', '--snapshot', {str(snap)!r}, '--calendar', {str(cal)!r},"
        f" '--start', '2026-06-01', '--end', '2026-06-30',"
        f" '--use', 'description', '--out', {str(out)!r}]\n"
        "raise SystemExit(cli.main())\n",
        encoding="utf-8",
    )
    proc = _run_cli([sys.executable, str(runner)])
    assert proc.returncode == 3
    assert "失败" in proc.stderr or "不可写" in proc.stderr
    assert not (tmp_path / "nowrite" / "o" / "manifest.json").exists()


def test_t1_protocol_missing_file_exits_3_and_records_no_null(tmp_path):
    """显式 --protocol 指向不存在的文件：退出 3，不得记 null 哈希当已绑定。"""
    snap = _make_economic_snapshot(tmp_path)
    proc = _run_cli([
        sys.executable, str(SCRIPT), "--snapshot", str(snap),
        "--calendar", str(_make_calendar(tmp_path)),
        "--start", "2026-06-01", "--end", "2026-06-30",
        "--use", "description", "--out", str(tmp_path / "o"),
        "--protocol", str(tmp_path / "no-such-protocol.json"),
    ])
    assert proc.returncode == 3, f"协议缺失应退出 3，实际 {proc.returncode}"
    out = tmp_path / "o"
    # 退出 3 时不得产出被当成已绑定的 manifest
    assert not (out / "manifest.json").exists()


def test_t1_protocol_valid_file_is_bound_with_real_hash(tmp_path):
    """显式提供合法协议文件：记录其真实哈希。"""
    snap = _make_economic_snapshot(tmp_path)
    proto = tmp_path / "protocol.json"
    proto.write_text(json.dumps({"id": "synthetic-protocol"}), encoding="utf-8")
    out = tmp_path / "o"
    proc = _run_cli([
        sys.executable, str(SCRIPT), "--snapshot", str(snap),
        "--calendar", str(_make_calendar(tmp_path)),
        "--start", "2026-06-01", "--end", "2026-06-30",
        "--use", "description", "--out", str(out),
        "--protocol", str(proto),
    ])
    assert proc.returncode == 0, proc.stderr
    manifest = json.loads((out / "manifest.json").read_text())
    want = hashlib.sha256(proto.read_bytes()).hexdigest()
    assert manifest["protocol"]["sha256"] == want
