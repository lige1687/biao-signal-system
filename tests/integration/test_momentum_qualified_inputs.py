"""证据 → 派生快照 → 现有研究入口的完整测试（Task 4/5；R1–R4 返修版）。

夹具期望值**独立手算**，不调用被测重建/动量函数生成参考再自证：

- 260 个交易日；前 99 天收盘 10.0；第 100 天每股分红 0.5（收盘同步降为
  9.5）；第 200 天 1 拆 2（收盘同步减半为 4.75）；第 250 天每股分红 0.25
  （拆分后每份分红等比缩放 0.5→0.25，收盘同步降为 4.5）。
- 手算经济指数：每天 I *= (P_t×mult + cash)/P_{t-1}，
  分红日 (9.5+0.5)/10=1、(4.5+0.25)/4.75=1，拆分日 (4.75×2)/9.5=1
  → I 恒等于 1.0（260 行）。
- 手算动量 M(t)=I(t−21)/I(t−252)−1：0 基位置 ≥252 才有值；12 个月末
  观察日中仅 2025-12-31（位置 259）满足 → 每产品 1 个正式键、共 2 个，
  每个值恒为 0.0（返修 S2：正式观察键集合由窗口/日历/池独立推导）。

任何系数方向错误（拆分误除）、现金未随拆分缩放、价格未同步调整，都会
使 I 偏离 1、动量偏离 0 而被抓住。
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
TASK_DIR = (ROOT / "docs/experiments/raw/"
            "research-fixed-etf-evidence-integration-2026-09-13")

sys.path.insert(0, str(ROOT / "src"))

SNAP_SCHEMA = "research-data-snapshot/1.0"

N_SESSIONS = 260
DIV1_POS, SPLIT_POS, DIV2_POS = 100, 200, 250  # 1 基位置
HAND_DIV1, HAND_RATIO, HAND_DIV2 = 0.5, 2.0, 0.25
HAND_REF_KEYS = 2  # 每产品 1 个（2025-12-31），共 2 个正式键


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _run(script, *args):
    return subprocess.run([sys.executable, str(script), *args],
                          capture_output=True, text=True, timeout=300)


def _sessions(n=N_SESSIONS, start="2025-01-02"):
    return [d.strftime("%Y-%m-%d")
            for d in pd.bdate_range(start, periods=n)]


def _hand_rows(days):
    """手算价格路径：与三个行动同步的阶梯价（见模块 docstring）。"""
    out = []
    for i, d in enumerate(days, start=1):
        if i < DIV1_POS:
            c = 10.0
        elif i < SPLIT_POS:
            c = 10.0 - HAND_DIV1
        elif i < DIV2_POS:
            c = (10.0 - HAND_DIV1) / HAND_RATIO
        else:
            c = (10.0 - HAND_DIV1) / HAND_RATIO - HAND_DIV2
        c = round(c, 4)
        out.append({"date": d, "open": c, "high": round(c * 1.01, 4),
                    "low": round(c * 0.99, 4), "close": c, "volume": 100.0})
    return out


def _flat_rows(days, c=10.0):
    """无事件产品的恒定价格路径（手算：I 恒为 1.0、动量恒为 0.0）。"""
    out = []
    for d in days:
        out.append({"date": d, "open": c, "high": round(c * 1.01, 4),
                    "low": round(c * 0.99, 4), "close": c, "volume": 100.0})
    return out


def _hand_events(days):
    """手算夹具的三个行动：分红、1拆2、拆分后每份分红缩放。"""
    return [
        {"event_id": "hand-div-1", "symbol": "510300.SS",
         "type": "cash_dividend", "cash": HAND_DIV1,
         "effective_date": days[DIV1_POS - 1],
         "available_at": "2025-06-16T16:00:00+08:00"},
        {"event_id": "hand-split-1", "symbol": "510300.SS",
         "type": "split", "ratio": HAND_RATIO,
         "effective_date": days[SPLIT_POS - 1],
         "available_at": "2025-11-14T16:00:00+08:00"},
        {"event_id": "hand-div-2", "symbol": "510300.SS",
         "type": "cash_dividend", "cash": HAND_DIV2,
         "effective_date": days[DIV2_POS - 1],
         "available_at": "2026-02-02T16:00:00+08:00"},
    ]


def _hand_momentum_dates(days):
    """位置 253..260（0 基 252..259）的正式键日期，手算推导。"""
    return [days[i] for i in range(252, N_SESSIONS)]


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


def _bind_records(base: Path, records: list[dict]) -> None:
    """为已核记录生成抽取输出文件与事实绑定（测试夹具用；含已核时间值）。"""
    from lei_signal.research.qualification_bundle import fact_tuple_fingerprint

    def field_value(rec: dict, field: str):
        if field.startswith("time_evidence."):
            return (rec.get("time_evidence") or {}).get(field.split(".", 1)[1])
        return rec["facts"][field]

    extraction: dict[str, dict] = {}
    for rec in records:
        if not rec.get("facts_verified"):
            continue
        fields = rec.setdefault("_bound_fields", ["listing_trade_date"])
        if "time_evidence.published_date" not in fields:
            fields = fields + ["time_evidence.published_date"]
            rec["_bound_fields"] = fields
        entry = {f: field_value(rec, f) for f in fields}
        extraction[rec["record_id"]] = entry
    extraction_path = base / "extraction-output.json"
    extraction_path.write_text(json.dumps(
        {"schema_version": "task2-extraction/1.2", "records": extraction},
        ensure_ascii=False), encoding="utf-8")
    for rec in records:
        if not rec.get("facts_verified"):
            continue
        fields = rec.pop("_bound_fields")
        rec["fact_binding"] = {
            "method": "测试夹具抽取（独立测试上下文，synthetic 数据）",
            "extraction_output": {"path": str(extraction_path),
                                  "sha256": _sha(extraction_path.read_bytes())},
            "fields": fields,
            "fingerprint": fact_tuple_fingerprint(
                rec["instrument_id"], rec["event_id"], rec["fact_type"],
                {f: field_value(rec, f) for f in fields}),
        }


def _write_test_protocol(base: Path, snap: Path, cal: Path, pub: Path,
                         act: Path, start: str, end: str, *,
                         bundle: Path | None = None,
                         values: Path | None = None) -> Path:
    protocol = json.loads(PROTOCOL.read_text())
    protocol["inputs"] = {
        "snapshot_dir": {"path": str(snap),
                         "sha256": _sha((snap / "snapshot.json").read_bytes())},
        "calendar": {"path": str(cal), "sha256": _sha(cal.read_bytes())},
        "publication": {"path": str(pub), "sha256": _sha(pub.read_bytes())},
        "actions": {"path": str(act), "sha256": _sha(act.read_bytes())},
        "evaluation_start": start, "evaluation_end": end,
    }
    # 派生入口实际执行的两文件 + 两个声明输入（返修 R4）；
    # 测试协议固定它实际运行的当前代码（CLI/模块随返修变化）
    for key, rel in (
        ("run_momentum_research_prototype",
         "scripts/run_momentum_research_prototype.py"),
        ("momentum_prototype",
         "src/lei_signal/research/momentum_prototype.py"),
        ("qualification_bundle",
         "src/lei_signal/research/qualification_bundle.py"),
        ("prepare_momentum_qualified_inputs",
         "scripts/prepare_momentum_qualified_inputs.py"),
    ):
        protocol["codes"][key] = {
            "path": rel, "sha256": _sha((ROOT / rel).read_bytes())}
    if bundle is not None:
        protocol["research_evidence"] = {
            "path": str(bundle), "sha256": _sha(bundle.read_bytes())}
    if values is not None:
        protocol["derived_reference"] = {
            "path": str(values), "sha256": _sha(values.read_bytes())}
    p = base / "protocol-test.json"
    p.write_text(json.dumps(protocol, ensure_ascii=False), encoding="utf-8")
    return p


def _write_bundle(base: Path, records, *, synthetic=False) -> Path:
    _bind_records(base, records)
    p = base / "evidence-bundle.json"
    p.write_text(json.dumps({
        "schema_version": "fixed-etf-evidence-bundle/1.2",
        "synthetic": synthetic, "records": records,
        "conflicts": [],
    }, ensure_ascii=False), encoding="utf-8")
    return p


def _write_reference_values(base: Path, days, symbols) -> Path:
    """手算正式参考键：正式观察键 = 完整月最后交易日 × 池产品。

    260 个交易日、预热 253 条（0 基位置 ≥252）→ 12 个月末观察日中只有
    2025-12-31（0 基位置 259）有动量，且手算动量恒为 0.0。
    每产品 1 个正式键，共 2 个（手算推导，不调用动量函数）。
    """
    month_last: dict[str, tuple[str, int]] = {}
    for i, d in enumerate(days):
        month_last[d[:7]] = (d, i)
    keys = [(d, i) for d, i in sorted(month_last.values()) if i >= 252]
    p = base / "run04-values.csv"
    lines = ["symbol,date,momentum,unit"]
    for d, _ in keys:
        for s in symbols:
            lines.append(f"{s},{d},0.0,fraction")
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def _build_fixture(tmp_path: Path, *, bundle_records=None):
    from lei_signal.research.momentum_prototype import (
        reconstruct_symbol_economic_index,
    )

    sessions = _sessions()
    symbols = ["510300.SS", "159915.SZ"]
    rows = _hand_rows(sessions)
    events = _hand_events(sessions)
    snap = _write_original_snapshot(tmp_path, {symbols[0]: rows,
                                               symbols[1]: _flat_rows(sessions)})
    cal = _write_calendar(tmp_path, sessions)
    pub = tmp_path / "publication.json"
    pub.write_text(json.dumps({"authority": "exchange_official",
                               "publisher": "合成测试", "months": {}}),
                   encoding="utf-8")
    act = _write_actions(tmp_path, events)
    values_path = _write_reference_values(tmp_path, sessions, symbols)

    src = tmp_path / "listing-orig.txt"
    listing_note = f"于 {sessions[30]} 上市（合成测试）"
    src.write_text(f"上市公告原文：{listing_note}", encoding="utf-8")
    records = bundle_records if bundle_records is not None else [{
        "record_id": "listing-510300",
        "instrument_id": "510300.SS",
        "fact_type": "listing",
        "event_id": "510300-listing",
        "facts": {"listing_trade_date": sessions[30],
                  "note": "上市交易日，非成立日"},
        "source": {"path": str(src), "sha256": _sha(src.read_bytes())},
        "locator": {"page": 1, "section": "上市公告书"},
        "short_supporting_text": listing_note,
        "source_fragments": [listing_note],
        "time_evidence": {
            "kind": "in_document_date_bound", "available_at": None,
            "published_date": "2025-02-01", "not_before": None,
            "not_after": None, "date_field": "公告日期（合成）",
            "refers_to": "本合成上市公告", "bound": "document_dated",
            "timezone": "Asia/Shanghai", "basis": "合成测试文内日期"},
        "facts_verified": True,
        "historical_availability_verified": False,
        "allowed_for": ["listing_evidence_bridge"],
        "limitations": [],
    }]
    bundle = _write_bundle(tmp_path, records)

    # 独立自检：手算期望与被测实现一致性由本测试**结果**验证，参考值本身
    # 只来自上面手算的 0.0；此处不生成参考值。
    protocol = _write_test_protocol(
        tmp_path, snap, cal, pub, act, sessions[0], sessions[-1],
        bundle=bundle, values=values_path)

    # 手算核对基准（供断言）：economic_index 恒为 1.0、动量恒为 0.0
    close = pd.Series([r["close"] for r in rows],
                      index=pd.DatetimeIndex(sessions))
    econ_hand, _ = reconstruct_symbol_economic_index(close, events)
    assert abs(float(econ_hand.iloc[-1]) - 1.0) < 1e-12, (
        "夹具价格路径与行动不同步（手算前提被破坏）")
    return protocol, bundle, values_path


def test_prepare_derives_snapshot_with_hand_computed_values(tmp_path):
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
    # 手算断言：经济指数恒为 1.0（任何系数/缩放错误都会打破）
    ecol = [line.split(",")[-1] for line in csv_text.splitlines()[1:]]
    assert len(ecol) == N_SESSIONS
    assert all(v and abs(float(v) - 1.0) < 1e-12 for v in ecol), (
        "经济指数偏离手算值 1.0")
    result = json.loads((out / "result.json").read_text())
    # 字段绑定：两个对象直接可满足（missing_fields 清空）
    assert all(v["directly_satisfiable"] for v in result["binding"].values())
    # 手算正式键双向核对：观察全集 22 组合（2 产品 × 11 个完整月末——
    # 夹具日历自 2025-01-02 起登记，1 月逐日不完整被正确排除）、
    # 派生有值仅 2025-12-31 的 2 键，参考表须精确等于这 2 键且值全 0.0
    mk = result["momentum_key_check"]
    assert mk["complete_consistent"] is True
    assert mk["expected_observation_combinations"] == 22
    assert mk["derivable_keys"] == 2
    assert mk["unique_reference_keys"] == 2
    assert mk["checked"] == 2
    assert mk["mismatch"] == 0
    assert mk["duplicate_reference_rows"] == []
    assert mk["invalid_reference_values"] == []
    assert mk["reference_missing_expected_key"] == []
    assert mk["reference_out_of_scope"] == []
    assert mk["reference_without_derived_value"] == []
    # 事后重建标记保留；非正/缺失收盘价计数留痕
    derived_meta = json.loads(
        (out / "snapshot/snapshot.json").read_text())
    assert derived_meta["semantics"]["historical_reconstruction_only"] is True
    assert all(v["close_dropped_nonpositive_or_nan"] == 0
               for v in result["econ_stats"].values())
    # manifest 登记全部输出哈希（含排他冻结的协议副本）
    manifest = json.loads((out / "manifest.json").read_text())
    for name, digest in manifest["outputs"].items():
        p = out / name
        assert _sha(p.read_bytes()) == digest, name
    assert manifest["protocol"]["frozen_copy"]["path"].endswith(
        "protocol-frozen.json")
    # 协议冻结副本是排他创建的不可变锚点：输入版本文件内容逐字节一致
    frozen_bytes = Path(manifest["protocol"]["frozen_copy"]["path"]).read_bytes()
    assert _sha(frozen_bytes) == manifest["protocol"]["sha256"]


def test_prepare_rejects_existing_frozen_protocol_copy(tmp_path):
    """排他创建：冻结副本已存在即失败，不覆盖（返修 R4 覆盖尝试反例）。"""
    protocol, bundle, values_path = _build_fixture(tmp_path)
    out = tmp_path / "derived-frozen-exists"
    out.mkdir()
    (out / "protocol-frozen.json").write_text("预置内容，不得被覆盖",
                                              encoding="utf-8")
    proc = _run(PREPARE, "--protocol", str(protocol),
                "--evidence-bundle", str(bundle),
                "--run04-values", str(values_path), "--out", str(out))
    assert proc.returncode == 3, proc.stdout
    assert (out / "protocol-frozen.json").read_text(
        encoding="utf-8") == "预置内容，不得被覆盖"
    assert not (out / "manifest.json").exists()


def test_prepare_rejects_pointer_protocol(tmp_path):
    """current 指针（protocol.json）不能作为运行协议身份（返修 R4）。"""
    protocol, bundle, values_path = _build_fixture(tmp_path)
    pointer = tmp_path / "protocol.json"
    pointer.write_text(protocol.read_text(), encoding="utf-8")
    out = tmp_path / "derived-pointer"
    proc = _run(PREPARE, "--protocol", str(pointer),
                "--evidence-bundle", str(bundle),
                "--run04-values", str(values_path), "--out", str(out))
    assert proc.returncode == 3, proc.stdout
    assert "指针" in proc.stderr


def test_prepare_rejects_reference_row_missing_from_observation_set(tmp_path):
    """S2 反例：正式参考键少一行（协议声明哈希合法更新）→ 退出 2，
    reference_missing_expected_key=1；不得宣称完整一致。"""
    protocol, bundle, values_path = _build_fixture(tmp_path)
    lines = values_path.read_text().splitlines()
    del lines[1]  # 删一个正式观察键
    values_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    protocol2 = json.loads(protocol.read_text())
    protocol2["derived_reference"] = {
        "path": str(values_path), "sha256": _sha(values_path.read_bytes())}
    protocol2_path = tmp_path / "protocol-missing-row.json"
    protocol2_path.write_text(json.dumps(protocol2, ensure_ascii=False),
                              encoding="utf-8")
    out = tmp_path / "derived-missing-row"
    proc = _run(PREPARE, "--protocol", str(protocol2_path),
                "--evidence-bundle", str(bundle),
                "--run04-values", str(values_path), "--out", str(out))
    assert proc.returncode == 2, proc.stdout
    assert "reference_missing=1" in proc.stderr
    assert not (out / "manifest.json").exists()


def test_prepare_rejects_tampered_reference_values(tmp_path):
    """R2 反例：额外不存在的参考键 → 退出 2，不写完成 manifest。"""
    protocol, bundle, values_path = _build_fixture(tmp_path)
    lines = values_path.read_text().splitlines()
    lines.append("510300.SS,2030-01-01,0.5,fraction")
    values_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # 协议声明的参考值哈希也要同步失效前先改协议？——不改：哈希不一致
    # 本身就该拒绝；本测试用未声明哈希的旧协议路径验证键集检查，
    # 因此这里重建协议使声明与文件一致，单独验证键集逻辑。
    protocol2 = json.loads(protocol.read_text())
    protocol2["derived_reference"] = {
        "path": str(values_path), "sha256": _sha(values_path.read_bytes())}
    protocol2_path = tmp_path / "protocol-extra-key.json"
    protocol2_path.write_text(json.dumps(protocol2, ensure_ascii=False),
                              encoding="utf-8")
    out = tmp_path / "derived-extra-key"
    proc = _run(PREPARE, "--protocol", str(protocol2_path),
                "--evidence-bundle", str(bundle),
                "--run04-values", str(values_path), "--out", str(out))
    assert proc.returncode == 2, proc.stdout
    assert not (out / "manifest.json").exists()


def test_prepare_rejects_nan_reference_value(tmp_path):
    """R2 反例：参考值 NaN → 退出 2，不写完成 manifest。"""
    protocol, bundle, values_path = _build_fixture(tmp_path)
    lines = values_path.read_text().splitlines()
    parts = lines[1].split(",")
    parts[2] = "NaN"
    lines[1] = ",".join(parts)
    values_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    protocol2 = json.loads(protocol.read_text())
    protocol2["derived_reference"] = {
        "path": str(values_path), "sha256": _sha(values_path.read_bytes())}
    protocol2_path = tmp_path / "protocol-nan.json"
    protocol2_path.write_text(json.dumps(protocol2, ensure_ascii=False),
                              encoding="utf-8")
    out = tmp_path / "derived-nan"
    proc = _run(PREPARE, "--protocol", str(protocol2_path),
                "--evidence-bundle", str(bundle),
                "--run04-values", str(values_path), "--out", str(out))
    assert proc.returncode == 2, proc.stdout
    assert not (out / "manifest.json").exists()


def test_prepare_rejects_reference_hash_mismatch(tmp_path):
    """R4：参考值与协议声明哈希不一致 → 输入身份失败（退出 3）。"""
    protocol, bundle, values_path = _build_fixture(tmp_path)
    values_path.write_text(
        values_path.read_text() + "510300.SS,2026-01-01,0.0,fraction\n",
        encoding="utf-8")  # 声明哈希失效
    out = tmp_path / "derived-hash-mismatch"
    proc = _run(PREPARE, "--protocol", str(protocol),
                "--evidence-bundle", str(bundle),
                "--run04-values", str(values_path), "--out", str(out))
    assert proc.returncode == 3, proc.stdout
    assert "derived_reference" in proc.stderr


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
        "510300.SS": _hand_rows(late_sessions),
        "159915.SZ": _hand_rows(sessions),
    })
    cal = _write_calendar(tmp_path, sessions)
    pub = tmp_path / "publication.json"
    pub.write_text(json.dumps({"authority": "exchange_official",
                               "publisher": "合成测试", "months": {}}),
                   encoding="utf-8")
    act = _write_actions(tmp_path, [])
    values_path = tmp_path / "values-bridge.csv"
    values_path.write_text("symbol,date,momentum,unit\n", encoding="utf-8")
    src = tmp_path / "listing-510300.txt"
    listing_note = f"于 {late_sessions[0]} 上市（合成测试）"
    src.write_text(f"510300 上市公告原文：{listing_note}", encoding="utf-8")
    records = [{
        "record_id": "listing-510300", "instrument_id": "510300.SS",
        "fact_type": "listing", "event_id": "510300-listing",
        "facts": {"listing_trade_date": late_sessions[0],
                  "note": "上市交易日，非成立日"},
        "source": {"path": str(src), "sha256": _sha(src.read_bytes())},
        "locator": {"page": 1, "section": "上市公告书"},
        "short_supporting_text": listing_note,
        "source_fragments": [listing_note],
        "time_evidence": {
            "kind": "in_document_date_bound", "available_at": None,
            "published_date": "2025-02-01", "not_before": None,
            "not_after": None, "date_field": "公告日期（合成）",
            "refers_to": "本合成上市公告", "bound": "document_dated",
            "timezone": "Asia/Shanghai", "basis": "合成测试文内日期"},
        "facts_verified": True, "historical_availability_verified": False,
        "allowed_for": ["listing_evidence_bridge"], "limitations": [],
    }]
    bundle = _write_bundle(tmp_path, records)
    protocol = _write_test_protocol(
        tmp_path, snap, cal, pub, act, sessions[0], sessions[-1],
        bundle=bundle, values=values_path)
    protocol_dict = json.loads(protocol.read_text())

    # 对照组（无 research_evidence）：同一发现是"缺上市资格证据"
    ctrl_dict = {k: v for k, v in protocol_dict.items()
                 if k not in ("research_evidence", "derived_reference")}
    ctrl_dict["codes"] = {
        k: v for k, v in protocol_dict["codes"].items()
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
    proc = _run(MOMENTUM_CLI, "--protocol", str(protocol),
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
    # 消费映射与排除留痕记录在 manifest
    manifest = json.loads((out / "manifest.json").read_text())
    lb = manifest["research_evidence"]["listing_bridge"]
    assert lb["products"] == ["510300.SS"]
    assert lb["consumed"][0]["record_id"] == "listing-510300"
    assert lb["excluded_purpose"] == [] and lb["excluded_conflict"] == []


def _load_task2():
    """导入抽取脚本模块（重构后导入不写任何文件）。"""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "task2_extract_facts_v2",
        TASK_DIR / "task2_extract_facts_v2.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_s3_extraction_writes_are_exclusive_and_reproducible(tmp_path):
    """S3：抽取脚本排他写——新目录生成、同字节复现不覆盖、异字节拒绝；
    v1.1 历史格式与被协议引用的正式产物逐字节一致；跨进程生成稳定。"""
    import subprocess as sp

    mod = _load_task2()
    out1 = tmp_path / "gen-1"
    assert mod.build(out1, "1.2") == 0
    bundle_bytes = (out1 / "evidence-bundle-v1.2.json").read_bytes()
    extract_bytes = (out1 / "task2-extraction-v1.2.json").read_bytes()
    # 同内容再生成：复现成功，字节不变
    assert mod.build(out1, "1.2") == 0
    assert (out1 / "evidence-bundle-v1.2.json").read_bytes() == bundle_bytes
    # 篡改后再生成：拒绝覆盖，被篡改字节保持原样
    p = out1 / "evidence-bundle-v1.2.json"
    p.write_bytes(bundle_bytes + b"tampered\n")
    raised = False
    try:
        mod.build(out1, "1.2")
    except SystemExit as exc:  # 拒绝覆盖
        raised = True
        assert "拒绝覆盖" in str(exc)
    assert raised, "异字节覆盖必须失败"
    assert p.read_bytes() == bundle_bytes + b"tampered\n"
    # v1.1 历史格式：与正式（协议曾引用）产物逐字节一致，不写正式位置
    official = TASK_DIR / "evidence-bundle-v1.1.json"
    out2 = tmp_path / "gen-11"
    assert mod.build(out2, "1.1") == 0
    assert (out2 / "evidence-bundle-v1.1.json").read_bytes() == \
        official.read_bytes()
    # 跨进程生成稳定：独立子进程产出与进程内逐字节一致
    out3 = tmp_path / "gen-sub"
    proc = sp.run([sys.executable, str(TASK_DIR / "task2_extract_facts_v2.py"),
                   "--schema", "1.2", "--out-dir", str(out3)],
                  capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, proc.stderr
    assert (out3 / "evidence-bundle-v1.2.json").read_bytes() == bundle_bytes
    assert (out3 / "task2-extraction-v1.2.json").read_bytes() == extract_bytes


def test_listing_bridge_excludes_records_without_purpose(tmp_path):
    """R1 反例：已核上市记录未声明 listing_evidence_bridge 用途 →
    事实可以保持已核，但不得生成桥接（排除逐条留痕）。"""
    sessions = _sessions()
    snap = _write_original_snapshot(tmp_path, {
        "510300.SS": _hand_rows(sessions),
        "159915.SZ": _hand_rows(sessions),
    })
    cal = _write_calendar(tmp_path, sessions)
    pub = tmp_path / "publication.json"
    pub.write_text(json.dumps({"authority": "exchange_official",
                               "publisher": "合成测试", "months": {}}),
                   encoding="utf-8")
    act = _write_actions(tmp_path, [])
    values_path = tmp_path / "values-nopurpose.csv"
    values_path.write_text("symbol,date,momentum,unit\n", encoding="utf-8")
    src = tmp_path / "listing-nopurpose.txt"
    listing_note = f"于 {sessions[0]} 上市（合成测试）"
    src.write_text(listing_note, encoding="utf-8")
    records = [{
        "record_id": "listing-no-purpose", "instrument_id": "510300.SS",
        "fact_type": "listing", "event_id": "510300-listing",
        "facts": {"listing_trade_date": sessions[0], "note": "已核但无桥接用途"},
        "source": {"path": str(src), "sha256": _sha(src.read_bytes())},
        "locator": {"page": 1, "section": "上市公告书"},
        "short_supporting_text": listing_note,
        "source_fragments": [listing_note],
        "time_evidence": {
            "kind": "in_document_date_bound", "available_at": None,
            "published_date": "2025-02-01", "not_before": None,
            "not_after": None, "date_field": "公告日期（合成）",
            "refers_to": "本合成上市公告", "bound": "document_dated",
            "timezone": "Asia/Shanghai", "basis": "合成测试文内日期"},
        "facts_verified": True, "historical_availability_verified": False,
        "allowed_for": ["description"], "limitations": [],
    }]
    bundle = _write_bundle(tmp_path, records)
    protocol = _write_test_protocol(
        tmp_path, snap, cal, pub, act, sessions[0], sessions[-1],
        bundle=bundle, values=values_path)
    out = tmp_path / "run-hist-nopurpose"
    proc = _run(MOMENTUM_CLI, "--protocol", str(protocol),
                "--mode", "historical-diagnostic", "--out", str(out))
    assert proc.returncode == 0, proc.stderr
    manifest = json.loads((out / "manifest.json").read_text())
    lb = manifest["research_evidence"]["listing_bridge"]
    assert lb["products"] == []
    assert lb["excluded_purpose"] and lb["excluded_purpose"][0][
        "record_id"] == "listing-no-purpose"
    assert not (out / "listing-bridge").exists() or not any(
        (out / "listing-bridge").iterdir())
