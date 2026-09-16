"""证据 → 派生快照 → 现有研究入口的完整测试（Task 4/5）。

小合成夹具走 prepare_momentum_qualified_inputs.py 全流程：证据包校验、
派生 CSV（原列逐字节保留 + economic_index）、离线读回、字段绑定、
算术核对；另覆盖篡改检测与证据包被拒分支。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PREPARE = ROOT / "scripts/prepare_momentum_qualified_inputs.py"
MOMENTUM_CLI = ROOT / "scripts/run_momentum_research_prototype.py"
PROTOCOL = ROOT / "docs/experiments/raw/research-momentum-prototype-2026-09-13/protocol.json"

sys.path.insert(0, str(ROOT / "src"))

SNAP_SCHEMA = "research-data-snapshot/1.0"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _run(script, *args):
    return subprocess.run([sys.executable, str(script), *args],
                          capture_output=True, text=True, timeout=300)


def _sessions(n=320, start="2025-01-02"):
    return [d.strftime("%Y-%m-%d")
            for d in pd.bdate_range(start, periods=n)]


def _rows(days):
    out = []
    for i, d in enumerate(days):
        c = round(10.0 * (1.0 + 0.0008 * i), 4)
        out.append({"date": d, "open": c, "high": round(c * 1.01, 4),
                    "low": round(c * 0.99, 4), "close": c, "volume": 100.0})
    return out


def _write_original_snapshot(base: Path, instruments: dict[str, list[dict]]) -> Path:
    snap = base / "orig-snapshot"
    (snap / "normalized").mkdir(parents=True)
    items = []
    for symbol, rows in instruments.items():
        cols = ["date", "open", "high", "low", "close", "volume"]
        text = ",".join(cols) + "\n" + "".join(
            ",".join(str(r[c]) for c in cols) + "\n" for r in rows)
        rel = f"normalized/{symbol}.csv"
        (snap / rel).write_text(text, encoding="utf-8")
        items.append({
            "instrument_id": symbol, "rows": len(rows),
            "first_date": rows[0]["date"], "last_date": rows[-1]["date"],
            "normalized": {"path": rel, "sha256": _sha(text.encode())},
            "raw_responses": [],
            "provider_report": {"provider": "t", "adjusted": False,
                                "duplicates_removed": 0, "warnings": []},
        })
    payload = {
        "schema_version": SNAP_SCHEMA,
        "transform_version": SNAP_SCHEMA,
        "mode": "import",
        "semantics": {
            "fields": {"date": "交易日", "open": "开盘", "high": "最高",
                       "low": "最低", "close": "名义收盘", "volume": "量"},
            "currency": "CNY", "price_basis": "nominal_close",
            "trading_calendar": {"authority": "none"},
        },
        "instruments": items,
        "uses": ["description", "ranking", "research_signal", "attribution",
                 "comparison", "diagnostic"],
        "not_for": ["production_trade"],
        "market_data_refs": {},
        "known_gaps": [],
        "uses_basis": {}, "authorization": {}, "code_identity": {},
    }
    (snap / "snapshot.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return snap


def _write_calendar(base: Path, sessions: list[str]) -> Path:
    import calendar as _cal
    from datetime import date

    months = sorted({d[:7] for d in sessions})
    lo, hi = sessions[0], sessions[-1]
    sset = set(sessions)
    days = {}
    for ym in months:
        y, m = (int(x) for x in ym.split("-"))
        for d in range(1, _cal.monthrange(y, m)[1] + 1):
            day = date(y, m, d).isoformat()
            if not (lo <= day <= hi):
                continue
            days[day] = {"is_trading_day": day in sset,
                         "source_flag": "1" if day in sset else "0",
                         "source_month": ym}
    p = base / "calendar.json"
    p.write_text(json.dumps({
        "authority": "exchange_official", "publisher": "合成测试日历",
        "months_requested": months, "months_failed": [], "days": days,
    }), encoding="utf-8")
    return p


def _write_actions(base: Path, events) -> Path:
    p = base / "actions.json"
    p.write_text(json.dumps({"schema_version": 1, "events": events},
                            ensure_ascii=False), encoding="utf-8")
    return p


def _write_test_protocol(base: Path, snap: Path, cal: Path, pub: Path,
                         act: Path, start: str, end: str) -> Path:
    protocol = json.loads(PROTOCOL.read_text())
    protocol["inputs"] = {
        "snapshot_dir": {"path": str(snap),
                         "sha256": _sha((snap / "snapshot.json").read_bytes())},
        "calendar": {"path": str(cal), "sha256": _sha(cal.read_bytes())},
        "publication": {"path": str(pub), "sha256": _sha(pub.read_bytes())},
        "actions": {"path": str(act), "sha256": _sha(act.read_bytes())},
        "evaluation_start": start, "evaluation_end": end,
    }
    p = base / "protocol-test.json"
    p.write_text(json.dumps(protocol, ensure_ascii=False), encoding="utf-8")
    return p


def _write_bundle(base: Path, records, *, synthetic=False) -> Path:
    p = base / "evidence-bundle.json"
    p.write_text(json.dumps({
        "schema_version": "fixed-etf-evidence-bundle/1.0",
        "synthetic": synthetic, "records": records,
        "conflicts": [],
    }, ensure_ascii=False), encoding="utf-8")
    return p


def _build_fixture(tmp_path: Path, *, bundle_records=None):
    from lei_signal.research.momentum_prototype import (
        reconstruct_symbol_economic_index,
    )

    sessions = _sessions()
    events = [{"event_id": "div-510300-1", "symbol": "510300.SS",
               "type": "cash_dividend", "cash": 0.05,
               "effective_date": "2025-06-16"}]
    snap = _write_original_snapshot(tmp_path, {
        "510300.SS": _rows(sessions),
        "159915.SZ": _rows(sessions),
    })
    cal = _write_calendar(tmp_path, sessions)
    pub = tmp_path / "publication.json"
    pub.write_text(json.dumps({"authority": "exchange_official",
                               "publisher": "合成测试", "months": {}}),
                   encoding="utf-8")
    act = _write_actions(tmp_path, events)
    protocol = _write_test_protocol(
        tmp_path, snap, cal, pub, act, sessions[0], sessions[-1])

    # 独立计算 economic_index（夹具事实），构造值文件与证据记录
    close = pd.Series([r["close"] for r in _rows(sessions)],
                      index=pd.DatetimeIndex(sessions))
    econ, _ = reconstruct_symbol_economic_index(close, events)
    momentum = __import__("lei_signal.research.momentum_prototype",
                          fromlist=["x"]).compute_momentum(econ)
    values = [
        {"symbol": "510300.SS", "date": d,
         "momentum": repr(float(momentum.loc[pd.Timestamp(d)])), "unit": "fraction"}
        for d in sessions
        if pd.Timestamp(d) in momentum.index
        and pd.notna(momentum.loc[pd.Timestamp(d)]) and d.endswith(("30", "31", "27", "28"))
    ]
    values_path = tmp_path / "run04-values.csv"
    values_path.write_text(
        "symbol,date,momentum,unit\n"
        + "".join(f"{v['symbol']},{v['date']},{v['momentum']},{v['unit']}\n"
                  for v in values), encoding="utf-8")

    src = tmp_path / "listing-orig.txt"
    src.write_text("上市公告原文（合成测试）", encoding="utf-8")
    records = bundle_records if bundle_records is not None else [{
        "record_id": "listing-510300",
        "instrument_id": "510300.SS",
        "fact_type": "listing",
        "event_id": "510300-listing",
        "facts": {"listing_trade_date": "2025-02-05",
                  "note": "上市交易日，非成立日"},
        "source": {"path": str(src), "sha256": _sha(src.read_bytes())},
        "locator": {"page": 1, "section": "上市公告书"},
        "short_supporting_text": "于 2025-02-05 上市",
        "time_evidence": {"kind": "published_date_bound", "available_at": None,
                          "published_date": "2025-02-01", "not_before": None,
                          "not_after": None, "timezone": "Asia/Shanghai",
                          "basis": "公告日期下界"},
        "facts_verified": True,
        "historical_availability_verified": False,
        "allowed_for": ["listing_evidence_bridge"],
        "limitations": [],
    }]
    bundle = _write_bundle(tmp_path, records)
    return protocol, bundle, values_path


def test_prepare_derives_snapshot_with_economic_index(tmp_path):
    protocol, bundle, values_path = _build_fixture(tmp_path)
    out = tmp_path / "derived-01"
    proc = _run(PREPARE, "--protocol", str(protocol),
                "--evidence-bundle", str(bundle),
                "--run04-values", str(values_path), "--out", str(out))
    assert proc.returncode == 0, proc.stderr
    # 派生 CSV 含 economic_index 列，名义列逐字节保留
    csv_text = (out / "snapshot/normalized/510300.SS.csv").read_text()
    header = csv_text.splitlines()[0].split(",")
    assert header[-1] == "economic_index"
    assert header[:6] == ["date", "open", "high", "low", "close", "volume"]
    result = json.loads((out / "result.json").read_text())
    # 字段绑定：两个对象直接可满足（missing_fields 清空）
    assert all(v["directly_satisfiable"] for v in result["binding"].values())
    # 算术核对：正式键全查且零差异
    assert result["momentum_key_check"]["mismatch"] == 0
    assert result["momentum_key_check"]["checked"] == len(
        values_path.read_text().splitlines()) - 1
    # 事后重建标记保留
    derived_meta = json.loads(
        (out / "snapshot/snapshot.json").read_text())
    assert derived_meta["semantics"]["historical_reconstruction_only"] is True
    # manifest 登记全部输出哈希
    manifest = json.loads((out / "manifest.json").read_text())
    for name, digest in manifest["outputs"].items():
        p = out / name
        assert _sha(p.read_bytes()) == digest, name


def test_tampered_derived_csv_detected_on_reload(tmp_path):
    protocol, bundle, values_path = _build_fixture(tmp_path)
    out = tmp_path / "derived-02"
    proc = _run(PREPARE, "--protocol", str(protocol),
                "--evidence-bundle", str(bundle),
                "--run04-values", str(values_path), "--out", str(out))
    assert proc.returncode == 0, proc.stderr
    csv_path = out / "snapshot/normalized/510300.SS.csv"
    lines = csv_path.read_text().splitlines()
    parts = lines[1].split(",")
    parts[4] = "999.0"
    lines[1] = ",".join(parts)
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    from lei_signal.research.data_snapshot import load_snapshot

    reloaded = load_snapshot(out / "snapshot")
    assert reloaded.verified is False
    assert reloaded.hash_mismatches


def test_rejected_bundle_record_exits_2(tmp_path):
    bad = [{
        "record_id": "bad-1", "instrument_id": "510300.SZ",  # 错交易所
        "fact_type": "listing", "event_id": "x",
        "facts": {"listing_trade_date": "2025-02-05"},
        "source": {"path": "missing.txt", "sha256": "0" * 64},
        "locator": {"page": 1}, "short_supporting_text": "",
        "time_evidence": {"available_at": None},
        "facts_verified": True, "historical_availability_verified": False,
        "allowed_for": [], "limitations": [],
    }]
    protocol, bundle, values_path = _build_fixture(
        tmp_path, bundle_records=bad)
    out = tmp_path / "derived-03"
    proc = _run(PREPARE, "--protocol", str(protocol),
                "--evidence-bundle", str(bundle),
                "--run04-values", str(values_path), "--out", str(out))
    assert proc.returncode == 2, proc.stdout
    assert not out.exists() or not (out / "manifest.json").exists()


def test_existing_out_dir_rejected(tmp_path):
    protocol, bundle, values_path = _build_fixture(tmp_path)
    out = tmp_path / "derived-04"
    out.mkdir()
    proc = _run(PREPARE, "--protocol", str(protocol),
                "--evidence-bundle", str(bundle),
                "--run04-values", str(values_path), "--out", str(out))
    assert proc.returncode == 3


def test_research_evidence_listing_bridge_changes_specific_finding(tmp_path):
    """Task 5：research_evidence 存在时，已核上市事实经桥接进入
    check_snapshot(listing_evidence=...)；只让证据确实解决的发现改变——
    日期变自洽，但真实资格授予仍由底层闸门拒绝（structural=False）。"""
    sessions = _sessions()
    late_sessions = sessions[30:]  # 510300 首报价晚于评价期起点
    snap = _write_original_snapshot(tmp_path, {
        "510300.SS": _rows(late_sessions),
        "159915.SZ": _rows(sessions),
    })
    cal = _write_calendar(tmp_path, sessions)
    pub = tmp_path / "publication.json"
    pub.write_text(json.dumps({"authority": "exchange_official",
                               "publisher": "合成测试", "months": {}}),
                   encoding="utf-8")
    act = _write_actions(tmp_path, [])
    protocol_path = _write_test_protocol(
        tmp_path, snap, cal, pub, act, sessions[0], sessions[-1])
    protocol = json.loads(protocol_path.read_text())
    # 启用 research_evidence：codes 补 qualification_bundle 键 + 证据文件
    src = tmp_path / "listing-510300.txt"
    src.write_text("510300 上市公告原文（合成测试）", encoding="utf-8")
    records = [{
        "record_id": "listing-510300", "instrument_id": "510300.SS",
        "fact_type": "listing", "event_id": "510300-listing",
        "facts": {"listing_trade_date": late_sessions[0],
                  "note": "上市交易日，非成立日"},
        "source": {"path": str(src), "sha256": _sha(src.read_bytes())},
        "locator": {"page": 1, "section": "上市公告书"},
        "short_supporting_text": f"于 {late_sessions[0]} 上市",
        "time_evidence": {"kind": "published_date_bound", "available_at": None,
                          "published_date": "2025-02-01", "not_before": None,
                          "not_after": None, "timezone": "Asia/Shanghai",
                          "basis": "公告日期下界"},
        "facts_verified": True, "historical_availability_verified": False,
        "allowed_for": ["listing_evidence_bridge"], "limitations": [],
    }]
    bundle = _write_bundle(tmp_path, records)
    protocol["research_evidence"] = {
        "path": str(bundle), "sha256": _sha(bundle.read_bytes())}
    protocol["codes"]["qualification_bundle"] = {
        "path": "src/lei_signal/research/qualification_bundle.py",
        "sha256": _sha((ROOT / "src/lei_signal/research/"
                        "qualification_bundle.py").read_bytes()),
    }
    protocol_path = tmp_path / "protocol-with-evidence.json"
    protocol_path.write_text(json.dumps(protocol, ensure_ascii=False),
                             encoding="utf-8")

    # 对照组（无 research_evidence）：同一发现是"缺上市资格证据"
    ctrl_dict = {k: v for k, v in protocol.items() if k != "research_evidence"}
    ctrl_dict["codes"] = {k: v for k, v in protocol["codes"].items()
                          if k != "qualification_bundle"}
    ctrl_path = tmp_path / "protocol-ctrl.json"
    ctrl_path.write_text(json.dumps(ctrl_dict, ensure_ascii=False),
                         encoding="utf-8")
    out_ctrl = tmp_path / "run-hist-ctrl"
    proc = _run(MOMENTUM_CLI, "--protocol", str(ctrl_path),
                "--mode", "historical-diagnostic", "--out", str(out_ctrl))
    assert proc.returncode == 0, proc.stderr
    q_ctrl = json.loads((out_ctrl / "quality.json").read_text())
    ctrl_hits = [f for f in q_ctrl["price_findings"]
                 if f["code"] == "starts_after_window"
                 and f.get("instrument") == "510300.SS"]
    assert ctrl_hits and "缺少上市资格证据" in ctrl_hits[0]["message"]

    # 实验组（有 research_evidence）：同一发现变为"日期自洽但资格未授予"
    out = tmp_path / "run-hist-bridge"
    proc = _run(MOMENTUM_CLI, "--protocol", str(protocol_path),
                "--mode", "historical-diagnostic", "--out", str(out))
    assert proc.returncode == 0, proc.stderr
    # 桥接文件生成并被消费
    bridge = out / "listing-bridge/listing-bridge-510300.json"
    assert bridge.exists()
    quality = json.loads((out / "quality.json").read_text())
    hits = [f for f in quality["price_findings"]
            if f["code"] == "starts_after_window"
            and f.get("instrument") == "510300.SS"]
    assert hits, "晚首报价发现应仍存在"
    assert "日期算法自洽" in hits[0]["message"]
    assert "资格状态无法确认" in hits[0]["message"]
    # 消费映射记录在 manifest
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["research_evidence"]["listing_bridge"]["products"] == [
        "510300.SS"]
