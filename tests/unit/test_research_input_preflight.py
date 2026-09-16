"""``research/input_preflight.py`` 的单元测试。

期望值全部独立手算，不用被测输出生成期望值。
"""
from __future__ import annotations

import json
from pathlib import Path

from lei_signal.research.input_preflight import combine_checks, inspect_input

# ---------------------------------------------------------------------------
# combine_checks：独立真值表（任务书给定，不得改动语义）
# ---------------------------------------------------------------------------


def test_combination_requires_every_check():
    assert combine_checks(integrity_ok=True, data_use_ok=True,
                          object_checks=(True, True)) is True
    assert combine_checks(integrity_ok=False, data_use_ok=True,
                          object_checks=(True,)) is False
    assert combine_checks(integrity_ok=True, data_use_ok=False,
                          object_checks=(True,)) is False
    assert combine_checks(integrity_ok=True, data_use_ok=True,
                          object_checks=(True, False)) is False


def test_combination_with_no_objects():
    """refs 为空时只检查数据，不声称因子接入。"""
    assert combine_checks(integrity_ok=True, data_use_ok=True,
                          object_checks=()) is True
    assert combine_checks(integrity_ok=True, data_use_ok=False,
                          object_checks=()) is False


# ---------------------------------------------------------------------------
# inspect_input：结构、身份与失败边界
# ---------------------------------------------------------------------------


def _make_snapshot_dir(tmp_path: Path, rows=None, *, tamper=False) -> Path:
    """构造最小合法快照（手写，不依赖被测代码的产物）。"""
    import hashlib

    snap = tmp_path / "snap"
    (snap / "normalized").mkdir(parents=True)
    if rows is None:
        rows = [
            {"date": "2026-06-01", "open": 10.0, "high": 11.0, "low": 9.0,
             "close": 10.0, "volume": 100.0},
            {"date": "2026-06-02", "open": 10.0, "high": 11.0, "low": 9.0,
             "close": 10.0, "volume": 100.0},
        ]
    text = "date,open,high,low,close,volume\n" + "".join(
        f"{r['date']},{r['open']},{r['high']},{r['low']},{r['close']},{r['volume']}\n"
        for r in rows
    )
    if tamper:
        text = text.replace("10.0", "99.9", 1)
    (snap / "normalized" / "510300.SS.csv").write_text(text, encoding="utf-8")
    payload = {
        "schema_version": "research-data-snapshot/1.0",
        "transform_version": "research-data-snapshot/1.0",
        "mode": "import",
        "semantics": {
            "fields": ["date", "open", "high", "low", "close", "volume"],
            "currency": "CNY",
            "price_basis": "nominal_close",
            "trading_calendar": {"authority": "none"},
        },
        "instruments": [{
            "instrument_id": "510300.SS",
            "rows": len(rows),
            "first_date": rows[0]["date"],
            "last_date": rows[-1]["date"],
            "normalized": {
                "path": "normalized/510300.SS.csv",
                "sha256": hashlib.sha256(text.encode()).hexdigest(),
            },
            "raw_responses": [],
            "provider_report": {"provider": "t", "adjusted": False,
                                "duplicates_removed": 0, "warnings": []},
        }],
        "uses": ["description", "diagnostic"],
        "not_for": ["production_trade"],
        "market_data_refs": {},
    }
    if tamper:
        # 篡改后快照里仍记旧哈希——新入口必须靠自己读出来
        payload["instruments"][0]["normalized"]["sha256"] = (
            hashlib.sha256(b"the-original-bytes").hexdigest()
        )
    (snap / "snapshot.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return snap


def _make_calendar(tmp_path: Path, months=("2026-06",)) -> Path:
    import calendar as _cal
    from datetime import date

    days = {}
    for ym in months:
        y, m = (int(x) for x in ym.split("-"))
        for d in range(1, _cal.monthrange(y, m)[1] + 1):
            day = date(y, m, d)
            tr = day.weekday() < 5
            days[day.isoformat()] = {
                "is_trading_day": tr, "source_flag": "1" if tr else "0",
                "source_month": ym,
            }
    p = tmp_path / "calendar.json"
    p.write_text(json.dumps({
        "authority": "exchange_official", "publisher": "合成测试日历",
        "months_requested": list(months), "months_failed": [], "days": days,
    }), encoding="utf-8")
    return p


def test_missing_snapshot_dir_fails_loudly(tmp_path):
    """文件缺失必须明确失败，不得吞异常返回空成功。"""
    report = inspect_input(
        snapshot_dir=tmp_path / "does-not-exist",
        calendar_path=_make_calendar(tmp_path),
        publication_path=None,
        actions_path=None,
        registry_path=None,
        refs=(),
        use="description",
        evaluation_start="2026-06-01",
        evaluation_end="2026-06-30",
    )
    assert report["request_satisfied"] is False
    assert any("snapshot" in e["stage"] for e in report["errors"])
    assert report["integrity"]["verified"] is False


def test_tampered_csv_is_caught_by_fresh_read(tmp_path):
    """快照目录里的旧报告说 verified，新入口重读必须自己发现篡改。"""
    snap = _make_snapshot_dir(tmp_path, tamper=True)
    report = inspect_input(
        snapshot_dir=snap,
        calendar_path=_make_calendar(tmp_path),
        publication_path=None,
        actions_path=None,
        registry_path=None,
        refs=(),
        use="description",
        evaluation_start="2026-06-01",
        evaluation_end="2026-06-30",
    )
    assert report["integrity"]["verified"] is False
    assert report["request_satisfied"] is False
    assert report["data_uses"]["description"]["default_accepted"] is False


def test_legal_snapshot_satisfies_description(tmp_path):
    """合法完整输入 + 只请求 description + 无 refs：成功正向路径，不得一律拒绝。"""
    snap = _make_snapshot_dir(tmp_path)
    report = inspect_input(
        snapshot_dir=snap,
        calendar_path=_make_calendar(tmp_path),
        publication_path=None,
        actions_path=None,
        registry_path=None,
        refs=(),
        use="description",
        evaluation_start="2026-06-01",
        evaluation_end="2026-06-30",
    )
    assert report["integrity"]["verified"] is True
    assert report["integrity"]["instruments"] == ["510300.SS"]
    assert report["integrity"]["rows"] == 2
    assert report["errors"] == []
    assert report["data_uses"]["description"]["default_accepted"] is True
    assert report["request_satisfied"] is True
    assert report["calculation_run"] is False
    assert report["production_authorized"] is False


def test_undeclared_use_is_rejected_even_when_quality_allows(tmp_path):
    """快照声明的 uses 不含 ranking 时，质量再好也不得放行。"""
    snap = _make_snapshot_dir(tmp_path)   # uses 只有 description/diagnostic
    report = inspect_input(
        snapshot_dir=snap,
        calendar_path=_make_calendar(tmp_path),
        publication_path=None,
        actions_path=None,
        registry_path=None,
        refs=(),
        use="ranking",
        evaluation_start="2026-06-01",
        evaluation_end="2026-06-30",
    )
    du = report["data_uses"]["ranking"]
    assert du["declared"] is False
    assert du["default_accepted"] is False
    assert "not_declared" in du["reason"]
    assert report["request_satisfied"] is False


def test_report_is_json_serializable_and_stable(tmp_path):
    """结果可 JSON 序列化；同一输入重复运行的稳定字段一致。"""
    snap = _make_snapshot_dir(tmp_path)
    cal = _make_calendar(tmp_path)
    kwargs = dict(
        snapshot_dir=snap, calendar_path=cal, publication_path=None,
        actions_path=None, registry_path=None, refs=(), use="description",
        evaluation_start="2026-06-01", evaluation_end="2026-06-30",
    )
    a = inspect_input(**kwargs)
    b = inspect_input(**kwargs)
    json.dumps(a)
    stable = ["integrity", "data_uses", "objects", "findings", "request_satisfied", "errors"]
    for key in stable:
        assert a[key] == b[key], f"{key} 在重复运行间不稳定"
