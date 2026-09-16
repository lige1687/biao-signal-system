"""``scripts/check_research_input.py`` 的组合边界测试。

每项断言到 request_satisfied 或退出码，不只检查字段存在。
期望值独立构造（手写快照/日历/行动并自行算哈希），不从被测输出生成。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/check_research_input.py"
REAL_SNAPSHOT = (
    ROOT / "docs/experiments/raw/research-identity-wiring-2026-09-10"
    / "canonical-snapshot-v2"
)
REAL_CALENDAR = (
    ROOT / "docs/experiments/raw/research-calendar-completion-2026-09-10"
    / "calendar-merged/calendar.json"
)
REAL_PUB = (
    ROOT / "docs/experiments/raw/research-calendar-completion-2026-09-10"
    / "publication-evidence.json"
)
REAL_ACTIONS = (
    ROOT / "docs/experiments/raw/research-rotation-clean-2026-09-09"
    / "full-pool-preparation/action-sources/normalized-actions.json"
)
REAL_REGISTRY = ROOT / "docs/research/definitions.v1.json"
COUNTEREXAMPLES = (
    ROOT / "docs/experiments/raw/research-data-foundation-controller-review-2026-09-13"
)


def _run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, cwd=ROOT,
    )


def _write_snapshot(base: Path, instruments: dict[str, list[dict]], *,
                    uses=("description", "diagnostic"),
                    drop_column_for: str | None = None) -> Path:
    """手写快照目录并自己算哈希。``drop_column_for`` 使某产品缺 close 列。"""
    snap = base / "snap"
    (snap / "normalized").mkdir(parents=True)
    items = []
    for symbol, rows in instruments.items():
        cols = ["date", "open", "high", "low", "close", "volume"]
        if symbol == drop_column_for:
            cols.remove("close")
        text = ",".join(cols) + "\n" + "".join(
            ",".join(str(r[c]) for c in cols) + "\n" for r in rows
        )
        rel = f"normalized/{symbol}.csv"
        (snap / rel).write_text(text, encoding="utf-8")
        items.append({
            "instrument_id": symbol,
            "rows": len(rows),
            "first_date": rows[0]["date"],
            "last_date": rows[-1]["date"],
            "normalized": {"path": rel,
                           "sha256": hashlib.sha256(text.encode()).hexdigest()},
            "raw_responses": [],
            "provider_report": {"provider": "t", "adjusted": False,
                                "duplicates_removed": 0, "warnings": []},
        })
    payload = {
        "schema_version": "research-data-snapshot/1.0",
        "transform_version": "research-data-snapshot/1.0",
        "mode": "import",
        "semantics": {
            "fields": ["date", "open", "high", "low", "close", "volume"],
            "currency": "CNY", "price_basis": "nominal_close",
            "trading_calendar": {"authority": "none"},
        },
        "instruments": items,
        "uses": list(uses),
        "not_for": ["production_trade"],
        "market_data_refs": {},
    }
    (snap / "snapshot.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return snap


def _rows(days, close=10.0):
    return [{"date": d, "open": close, "high": close + 1, "low": close - 1,
             "close": close, "volume": 100.0} for d in days]


def _write_calendar(base: Path, months=("2026-06",), *, drop_day: str | None = None,
                    invalid_key: str | None = None) -> Path:
    import calendar as _cal
    from datetime import date

    days = {}
    for ym in months:
        y, m = (int(x) for x in ym.split("-"))
        for d in range(1, _cal.monthrange(y, m)[1] + 1):
            day = date(y, m, d)
            if str(day) == drop_day:
                continue
            tr = day.weekday() < 5
            days[day.isoformat()] = {
                "is_trading_day": tr, "source_flag": "1" if tr else "0",
                "source_month": ym,
            }
    if invalid_key:
        days[invalid_key] = {"is_trading_day": True, "source_flag": "1",
                             "source_month": "2026-06"}
    p = base / "calendar.json"
    p.write_text(json.dumps({
        "authority": "exchange_official", "publisher": "合成测试日历",
        "months_requested": list(months), "months_failed": [], "days": days,
    }), encoding="utf-8")
    return p


def _write_actions(base: Path, events) -> Path:
    p = base / "actions.json"
    p.write_text(json.dumps({"schema_version": 1, "events": events},
                            ensure_ascii=False), encoding="utf-8")
    return p


def _basic_args(snap, cal, out, **kw):
    args = ["--snapshot", str(snap), "--start", "2026-06-01", "--end", "2026-06-30",
            "--use", kw.pop("use", "description"), "--out", str(out)]
    if cal is not None:
        args += ["--calendar", str(cal)]
    for key, val in kw.items():
        if val is not None:
            args += [f"--{key.replace('_', '-')}", str(val)]
    return args


# ---------------------------------------------------------------------------
# 1. 正向路径
# ---------------------------------------------------------------------------


def test_legal_full_input_description_succeeds(tmp_path):
    snap = _write_snapshot(tmp_path, {"510300.SS": _rows(["2026-06-01", "2026-06-02"])})
    proc = _run(*_basic_args(snap, _write_calendar(tmp_path), tmp_path / "o"))
    assert proc.returncode == 0, proc.stderr
    report = json.loads((tmp_path / "o/preflight.json").read_text())
    assert report["request_satisfied"] is True
    assert report["integrity"]["verified"] is True


# ---------------------------------------------------------------------------
# 2. 产物不声明该用途
# ---------------------------------------------------------------------------


def test_undeclared_use_rejected_with_not_declared(tmp_path):
    snap = _write_snapshot(tmp_path,
                           {"510300.SS": _rows(["2026-06-01", "2026-06-02"])},
                           uses=("description",))
    proc = _run(*_basic_args(snap, _write_calendar(tmp_path), tmp_path / "o",
                             use="ranking"))
    assert proc.returncode == 2
    report = json.loads((tmp_path / "o/preflight.json").read_text())
    assert "not_declared" in report["data_uses"]["ranking"]["reason"]
    assert report["request_satisfied"] is False


# ---------------------------------------------------------------------------
# 3. 篡改 / 删列 / 缺文件：旧报告说 verified 也不信
# ---------------------------------------------------------------------------


def test_tampered_csv_rejected_despite_old_verified_claim(tmp_path):
    snap = _write_snapshot(tmp_path, {"510300.SS": _rows(["2026-06-01", "2026-06-02"])})
    target = snap / "normalized" / "510300.SS.csv"
    original = target.read_bytes()
    tampered = original.replace(b"10.0", b"99.9", 1)
    assert tampered != original
    target.write_bytes(tampered)
    proc = _run(*_basic_args(snap, _write_calendar(tmp_path), tmp_path / "o"))
    assert proc.returncode == 2
    report = json.loads((tmp_path / "o/preflight.json").read_text())
    assert report["integrity"]["verified"] is False


def test_dropped_column_cannot_be_hidden_by_union(tmp_path):
    """单产品缺字段，另一只有该字段：不得用并集宣布全批满足。"""
    snap = _write_snapshot(
        tmp_path,
        {"510300.SS": _rows(["2026-06-01"]), "512890.SS": _rows(["2026-06-01"])},
        drop_column_for="512890.SS",
    )
    proc = _run(*_basic_args(snap, _write_calendar(tmp_path), tmp_path / "o"))
    assert proc.returncode == 2
    report = json.loads((tmp_path / "o/preflight.json").read_text())
    assert report["integrity"]["verified"] is False
    per = report["integrity"]["per_instrument_fields"]
    assert per["512890.SS"]["missing_declared_fields"] == ["close"]
    assert per["510300.SS"]["missing_declared_fields"] == []


def test_missing_snapshot_json_fails(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    proc = _run(*_basic_args(empty, _write_calendar(tmp_path), tmp_path / "o"))
    assert proc.returncode == 3
    report = json.loads((tmp_path / "o/preflight.json").read_text())
    assert any(e["stage"] == "snapshot" for e in report["errors"])
    # 失败时不得留下成功 manifest
    assert not (tmp_path / "o/manifest.json").exists()


# ---------------------------------------------------------------------------
# 4. 命令不得提供口径/币种/字段覆盖参数
# ---------------------------------------------------------------------------


def test_no_override_parameters_exist(tmp_path):
    proc = _run("--snapshot", str(tmp_path), "--start", "2026-06-01",
                "--end", "2026-06-30", "--use", "description",
                "--out", str(tmp_path / "o"), "--price-basis", "adjusted")
    assert proc.returncode != 0
    assert not (tmp_path / "o").exists()


# ---------------------------------------------------------------------------
# 7. 账户 events 冒充停牌 actions：污染必须可见，不得消除缺口
# ---------------------------------------------------------------------------


def test_account_event_cannot_erase_gap(tmp_path):
    days = ["2026-06-01", "2026-06-02", "2026-06-03"]
    snap = _write_snapshot(
        tmp_path,
        {"510300.SS": _rows(days),
         "512890.SS": _rows(["2026-06-01", "2026-06-03"])},   # 缺 06-02
    )
    cal = _write_calendar(tmp_path)
    actions = _write_actions(tmp_path, [{
        "event_id": "fake-halt", "symbol": "512890.SS",
        "type": "trading_halt", "effective_date": "2026-06-02",
        "halt": {"start_date": "2026-06-02", "end_date": "2026-06-02"},
        "account_id": "test-account", "amount": 0,
    }])
    proc = _run(*_basic_args(snap, cal, tmp_path / "o", actions=actions,
                             use="attribution"))
    assert proc.returncode == 2
    text = (tmp_path / "o/preflight.json").read_text(encoding="utf-8")
    assert "events_passed_as_actions" in text, "污染原因必须可见"
    assert '"cause": "unconfirmed"' in text, "缺口不得被非法记录消除"


# ---------------------------------------------------------------------------
# 8. 合法停牌：可追溯 event_id，但不证明当时可交易
# ---------------------------------------------------------------------------


def test_legal_halt_explains_with_event_id(tmp_path):
    snap = _write_snapshot(
        tmp_path,
        {"510300.SS": _rows(["2026-06-01", "2026-06-02", "2026-06-03"]),
         "512890.SS": _rows(["2026-06-01", "2026-06-03"])},
    )
    actions = _write_actions(tmp_path, [{
        "event_id": "512890-halt-2026-06-02", "symbol": "512890",
        "type": "trading_halt", "effective_date": "2026-06-02",
        "halt": {"start_date": "2026-06-02", "end_date": "2026-06-02"},
    }])
    proc = _run(*_basic_args(snap, _write_calendar(tmp_path), tmp_path / "o",
                             actions=actions))
    assert proc.returncode == 0
    text = (tmp_path / "o/preflight.json").read_text(encoding="utf-8")
    assert "512890-halt-2026-06-02" in text
    assert "不等于当时可交易" in text, "解释必须注明不等于当时可交易"


# ---------------------------------------------------------------------------
# 9. 日历异常：缺失 / 漏日 / 非法日期键
# ---------------------------------------------------------------------------


def test_no_calendar_downgrades_not_silent(tmp_path):
    snap = _write_snapshot(tmp_path, {"510300.SS": _rows(["2026-06-01", "2026-06-02"])})
    proc = _run(*_basic_args(snap, None, tmp_path / "o"))
    assert proc.returncode == 0
    report = json.loads((tmp_path / "o/preflight.json").read_text())
    assert report["calendar"]["loaded"] is False
    assert any("未提供日历" in x for x in report["limitations"])
    assert report["data_uses"]["ranking"]["verdict"] == "conditional"


def test_invalid_calendar_key_reported(tmp_path):
    snap = _write_snapshot(tmp_path, {"510300.SS": _rows(["2026-06-01", "2026-06-02"])})
    cal = _write_calendar(tmp_path, invalid_key="2026-06-99")
    proc = _run(*_basic_args(snap, cal, tmp_path / "o"))
    assert proc.returncode == 0
    report = json.loads((tmp_path / "o/preflight.json").read_text())
    assert report["calendar"]["invalid_records"] == 1


# ---------------------------------------------------------------------------
# 10. 非法顶层 JSON / 非法区间
# ---------------------------------------------------------------------------


def test_non_dict_top_level_actions_fails(tmp_path):
    snap = _write_snapshot(tmp_path, {"510300.SS": _rows(["2026-06-01", "2026-06-02"])})
    bad = tmp_path / "actions.json"
    bad.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    proc = _run(*_basic_args(snap, _write_calendar(tmp_path), tmp_path / "o",
                             actions=bad))
    assert proc.returncode == 3
    report = json.loads((tmp_path / "o/preflight.json").read_text())
    assert any(e["stage"] == "actions" for e in report["errors"])


def test_reversed_evaluation_range_fails(tmp_path):
    snap = _write_snapshot(tmp_path, {"510300.SS": _rows(["2026-06-01", "2026-06-02"])})
    proc = _run("--snapshot", str(snap), "--calendar",
                str(_write_calendar(tmp_path)),
                "--start", "2026-06-30", "--end", "2026-06-01",
                "--use", "description", "--out", str(tmp_path / "o"))
    assert proc.returncode == 3
    report = json.loads((tmp_path / "o/preflight.json").read_text())
    assert report["errors"], "起止倒置必须留下明确失败原因"


# ---------------------------------------------------------------------------
# 11. 不存在对象 / 错版本 / 禁用用途
# ---------------------------------------------------------------------------


def test_unknown_object_wrong_version_and_forbidden_use(tmp_path):
    snap = _write_snapshot(tmp_path, {"510300.SS": _rows(["2026-06-01", "2026-06-02"])})
    args = _basic_args(snap, _write_calendar(tmp_path), tmp_path / "o",
                       registry=REAL_REGISTRY)
    proc = _run(*args, "--refs", "nosuch.object@1.0.0",
                "mixed.momentum.raw@9.9.9", "mixed.momentum.raw")
    assert proc.returncode == 2
    report = json.loads((tmp_path / "o/preflight.json").read_text())
    objs = report["objects"]
    assert objs["nosuch.object@1.0.0"]["resolved"] is False
    assert objs["mixed.momentum.raw@9.9.9"]["resolved"] is False
    assert "id@version" in objs["mixed.momentum.raw"]["error"]


def test_purpose_not_allowed_is_separate(tmp_path):
    snap = _write_snapshot(tmp_path, {"510300.SS": _rows(["2026-06-01", "2026-06-02"])})
    proc = _run(*_basic_args(snap, _write_calendar(tmp_path), tmp_path / "o",
                             registry=REAL_REGISTRY, use="attribution"),
                "--refs", "trend.sma200@1.0.0")
    assert proc.returncode == 2
    report = json.loads((tmp_path / "o/preflight.json").read_text())
    obj = report["objects"]["trend.sma200@1.0.0"]
    assert obj["resolved"] is True
    assert obj["purpose_allowed"] is False
    assert "diagnostic" in obj["card_uses"]


# ---------------------------------------------------------------------------
# 12. 真实名义价绑定三个指定对象：economic_index 必须仍缺
# ---------------------------------------------------------------------------


def test_real_nominal_price_still_missing_economic_index(tmp_path):
    out = tmp_path / "o"
    proc = _run(
        "--snapshot", str(REAL_SNAPSHOT), "--calendar", str(REAL_CALENDAR),
        "--publication", str(REAL_PUB), "--actions", str(REAL_ACTIONS),
        "--registry", str(REAL_REGISTRY),
        "--start", "2019-09-02", "--end", "2026-06-30",
        "--use", "description", "--out", str(out),
        "--refs", "mixed.price.economic@1.0.0", "mixed.momentum.raw@1.0.0",
        "trend.sma200@1.0.0",
    )
    assert proc.returncode == 2
    report = json.loads((out / "preflight.json").read_text())
    assert report["integrity"]["instruments"] and len(
        report["integrity"]["instruments"]) == 14
    assert report["integrity"]["rows"] == 18916
    for ref in ("mixed.price.economic@1.0.0", "mixed.momentum.raw@1.0.0",
                "trend.sma200@1.0.0"):
        obj = report["objects"][ref]
        assert obj["resolved"] is True
        assert obj["missing_fields"] == ["economic_index"], (
            f"{ref}：名义价缺 economic_index，不得把 close 改名补足"
        )
        assert obj["directly_satisfiable"] is False


# ---------------------------------------------------------------------------
# 13. 人为改写已保存的通过结果：重跑从原输入读取
# ---------------------------------------------------------------------------


def test_rewritten_old_result_is_not_trusted(tmp_path):
    snap = _write_snapshot(tmp_path,
                           {"510300.SS": _rows(["2026-06-01", "2026-06-02"])},
                           uses=("description",))
    args = _basic_args(snap, _write_calendar(tmp_path), tmp_path / "o", use="ranking")
    first = _run(*args)
    assert first.returncode == 2
    saved = tmp_path / "o/preflight.json"
    payload = json.loads(saved.read_text())
    payload["request_satisfied"] = True          # 人为改写旧结果为"通过"
    saved.write_text(json.dumps(payload), encoding="utf-8")
    # 换输出目录重跑：结论必须来自原输入，而不是被改过的旧文件
    second = _run(*_basic_args(snap, _write_calendar(tmp_path), tmp_path / "o2",
                               use="ranking"))
    assert second.returncode == 2
    rerun = json.loads((tmp_path / "o2/preflight.json").read_text())
    assert rerun["request_satisfied"] is False


# ---------------------------------------------------------------------------
# 14/15. 重复运行稳定；同路径不同输入不同身份
# ---------------------------------------------------------------------------


def test_repeat_run_is_stable(tmp_path):
    snap = _write_snapshot(tmp_path, {"510300.SS": _rows(["2026-06-01", "2026-06-02"])})
    cal = _write_calendar(tmp_path)
    _run(*_basic_args(snap, cal, tmp_path / "o1"))
    _run(*_basic_args(snap, cal, tmp_path / "o2"))
    a = json.loads((tmp_path / "o1/preflight.json").read_text())
    b = json.loads((tmp_path / "o2/preflight.json").read_text())
    for key in ("integrity", "data_uses", "objects", "request_satisfied", "errors"):
        assert a[key] == b[key]


def test_same_path_different_fingerprint_yields_different_identity(tmp_path):
    cal = _write_calendar(tmp_path)
    snap_a = _write_snapshot(tmp_path / "a",
                             {"510300.SS": _rows(["2026-06-01", "2026-06-02"])})
    snap_b = _write_snapshot(tmp_path / "b",
                             {"510300.SS": _rows(["2026-06-01"])})
    _run(*_basic_args(snap_a, cal, tmp_path / "o1"))
    _run(*_basic_args(snap_b, cal, tmp_path / "o2"))
    a = json.loads((tmp_path / "o1/preflight.json").read_text())
    b = json.loads((tmp_path / "o2/preflight.json").read_text())
    assert a["integrity"]["rows"] == 2
    assert b["integrity"]["rows"] == 1
    ma = json.loads((tmp_path / "o1/manifest.json").read_text())
    mb = json.loads((tmp_path / "o2/manifest.json").read_text())
    assert ma["input_hashes"]["snapshot_json"] != mb["input_hashes"]["snapshot_json"]


# ---------------------------------------------------------------------------
# 16. 输出目录存在 / 断网运行
# ---------------------------------------------------------------------------


def test_existing_out_dir_refused_without_touching(tmp_path):
    out = tmp_path / "o"
    out.mkdir()
    sentinel = out / "keep.txt"
    sentinel.write_text("do not touch", encoding="utf-8")
    snap = _write_snapshot(tmp_path, {"510300.SS": _rows(["2026-06-01"])})
    proc = _run(*_basic_args(snap, _write_calendar(tmp_path), out))
    assert proc.returncode == 3
    assert sentinel.read_text(encoding="utf-8") == "do not touch"
    assert not (out / "preflight.json").exists()


def test_offline_run_completes_legal_check(tmp_path):
    """断网（子进程内封锁 socket）仍能完成合法检查。"""
    snap = _write_snapshot(tmp_path, {"510300.SS": _rows(["2026-06-01", "2026-06-02"])})
    cal = _write_calendar(tmp_path)
    guard = tmp_path / "guard.py"
    guard.write_text(
        "import socket, runpy, sys\n"
        "def _blocked(*a, **k):\n"
        "    raise RuntimeError('network blocked by test guard')\n"
        "socket.socket = _blocked\n"
        "socket.create_connection = _blocked\n"
        "socket.getaddrinfo = _blocked\n"
        "sys.argv = ['check', '--snapshot', " + repr(str(snap)) + ","
        " '--calendar', " + repr(str(cal)) + ","
        " '--start', '2026-06-01', '--end', '2026-06-30',"
        " '--use', 'description', '--out', " + repr(str(tmp_path / 'o')) + "]\n"
        "runpy.run_path(" + repr(str(SCRIPT)) + ", run_name='__main__')\n",
        encoding="utf-8",
    )
    proc = subprocess.run([sys.executable, str(guard)],
                          capture_output=True, text=True, cwd=ROOT)
    assert proc.returncode == 0, proc.stderr
    report = json.loads((tmp_path / "o/preflight.json").read_text())
    assert report["request_satisfied"] is True


# ---------------------------------------------------------------------------
# 6. 两份主控固定反例：指纹不变，且本入口不给上市证据通道
# ---------------------------------------------------------------------------


def test_counterexample_files_unchanged_and_no_listing_channel(tmp_path):
    for name in ("listing-explicit-synthetic.json",
                 "listing-qualification-omitted.json"):
        p = COUNTEREXAMPLES / name
        assert p.is_file()
    # 本入口不接受任何上市证据参数；无证据时 starts_after_window 一律未确认
    snap = _write_snapshot(tmp_path, {"510300.SS": _rows(["2026-06-01", "2026-06-02"])})
    proc = _run(*_basic_args(snap, _write_calendar(tmp_path), tmp_path / "o",
                             use="ranking"))
    report = json.loads((tmp_path / "o/preflight.json").read_text())
    assert report["request_satisfied"] is False
    assert proc.returncode == 2
