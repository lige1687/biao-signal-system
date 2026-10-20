"""``scripts/run_momentum_research_prototype.py`` 的组合边界测试。

覆盖：合成闭环完整调用与产物契约、目录/协议/输入篡改拒绝、断网守卫自证、
输出写盘失败出口、真实模式的资格分支（historical-diagnostic 放行与拒绝、
qualified-research 预期拒绝）。期望独立构造，不从被测输出生成。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/run_momentum_research_prototype.py"
PROTOCOL = ROOT / "docs/experiments/raw/research-momentum-prototype-2026-09-13/protocol.json"

EXPECTED_FILES = {
    "values.csv", "missing.csv", "targets.csv", "rank-diagnostic.csv",
    "quality.json", "report.md", "manifest.json",
}


def _run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, timeout=300,
    )


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _runnable_protocol_copy(tmp_path: Path) -> Path:
    """真实协议内容 + 当前代码哈希的版本名副本（指针拒绝后的合法直跑入口）。"""
    protocol = json.loads(PROTOCOL.read_text())
    for key, rel in (
        ("run_momentum_research_prototype",
         "scripts/run_momentum_research_prototype.py"),
        ("momentum_prototype",
         "src/lei_signal/research/momentum_prototype.py"),
    ):
        protocol["codes"][key] = {
            "path": rel, "sha256": _sha((ROOT / rel).read_bytes())}
    p = tmp_path / "protocol-run-v1.0.7-refreshed.json"
    p.write_text(json.dumps(protocol, ensure_ascii=False), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# 合成闭环（synthetic=true）
# ---------------------------------------------------------------------------


def test_synthetic_mode_completes_with_full_contract(tmp_path):
    out = tmp_path / "syn-01"
    proc = _run("--protocol", str(_runnable_protocol_copy(tmp_path)),
                "--mode", "synthetic", "--out", str(out))
    assert proc.returncode == 0, proc.stderr
    assert {p.name for p in out.iterdir()} == EXPECTED_FILES
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["synthetic"] is True
    assert manifest["historical_reconstruction_only"] is False
    assert manifest["offline_guard"]["self_check_blocked"] is True
    assert manifest["statuses"]["production"] == "not_authorized"
    assert manifest["statuses"]["policy"] == "not_applicable_no_account_policy"
    # 输出指纹逐文件核对，不以文件存在代替内容核验
    for name, digest in manifest["outputs"].items():
        assert _sha((out / name).read_bytes()) == digest, name
    # 合成例既有正常输出也演示缺失，不得以一律拒绝假通过
    values = (out / "values.csv").read_text().strip().splitlines()
    missing = (out / "missing.csv").read_text().strip().splitlines()
    assert len(values) > 1 and len(missing) > 1
    targets = (out / "targets.csv").read_text().strip().splitlines()
    rank = (out / "rank-diagnostic.csv").read_text().strip().splitlines()
    assert len(targets) > 1 and len(rank) > 1
    # 至少一期排序诊断有数值；全部行带统一观察目标 ID
    value_rows = [r for r in rank[1:] if r.split(",")[3]]
    assert value_rows, "至少一期排名诊断应有数值"
    target_id = "protocol:momentum-next-close-21-session@1.0.0"
    assert all(r.split(",")[0] == target_id for r in rank[1:])
    # 不足预热与缺报价两类缺失原因必须实际出现
    reasons = {line.split(",")[4] for line in missing[1:]}
    assert "insufficient_warmup" in reasons
    assert {"no_quote_at_observation"} & reasons
    # 报告含大白话结论小节
    assert "一句话结论" in (out / "report.md").read_text()


def test_synthetic_momentum_values_recomputable_by_position_formula(tmp_path):
    """第三方可用独立位置公式复算：M = I(valid_pos-21)/I(valid_pos-252)-1。"""
    import pandas as pd

    sys.path.insert(0, str(ROOT / "scripts"))
    sys.path.insert(0, str(ROOT / "src"))
    import run_momentum_research_prototype as cli

    fixture = cli.build_synthetic_fixture()
    product = fixture["products"]["SYN.C"]  # 含拆分与缺报价的最难情形
    close = product["close"].astype(float)
    events = [e for e in product["events"] if e["type"] in {"split", "cash_dividend"}]
    econ, unknown = cli.mp.reconstruct_symbol_economic_index(close, events)
    momentum = cli.mp.compute_momentum(econ)
    assert unknown == []  # 合成行动都带合成可得时间
    # 独立复算：按有效报价位置直接取数
    valid = list(econ.index)
    for i in range(252, len(valid)):
        expect = econ.iloc[i - 21] / econ.iloc[i - 252] - 1
        got = momentum.iloc[i]
        assert abs(got - expect) <= 1e-12 * max(1.0, abs(expect))
    # 观察日数值与 CLI 产物一致（SYN.C 在 2024-12-31 有值）
    out = tmp_path / "syn-02"
    proc = _run("--protocol", str(_runnable_protocol_copy(tmp_path)),
                "--mode", "synthetic", "--out", str(out))
    assert proc.returncode == 0, proc.stderr
    rows = (out / "values.csv").read_text().strip().splitlines()
    hit = [r for r in rows if r.startswith("mixed.momentum.raw@1.0.0,SYN.C,2024-12-31")]
    assert len(hit) == 1
    cli_value = float(hit[0].split(",")[3])
    day = pd.Timestamp("2024-12-31")
    assert abs(float(momentum.loc[day]) - cli_value) <= 1e-12


# ---------------------------------------------------------------------------
# 拒绝与失败出口
# ---------------------------------------------------------------------------


def test_existing_out_dir_rejected(tmp_path):
    out = tmp_path / "syn-03"
    out.mkdir()
    proc = _run("--protocol", str(PROTOCOL), "--mode", "synthetic", "--out", str(out))
    assert proc.returncode == 3
    assert "拒绝覆盖" in proc.stderr


def test_bad_mode_is_argument_error_exit_3(tmp_path):
    proc = _run("--protocol", str(PROTOCOL), "--mode", "bogus", "--out",
                str(tmp_path / "x"))
    assert proc.returncode == 3


def test_missing_protocol_file_exits_3_without_outputs(tmp_path):
    out = tmp_path / "syn-04"
    proc = _run("--protocol", str(tmp_path / "nope.json"), "--mode", "synthetic",
                "--out", str(out))
    assert proc.returncode == 3
    assert not out.exists()
    assert "不存在" in proc.stderr


def test_tampered_protocol_code_hash_exits_3(tmp_path):
    protocol = json.loads(PROTOCOL.read_text())
    protocol["codes"]["definitions"]["sha256"] = "0" * 64
    bad = tmp_path / "protocol-bad.json"
    bad.write_text(json.dumps(protocol), encoding="utf-8")
    out = tmp_path / "syn-05"
    proc = _run("--protocol", str(bad), "--mode", "synthetic", "--out", str(out))
    assert proc.returncode == 3
    assert not out.exists()
    assert "代码指纹" in proc.stderr


def test_manifest_write_failure_exits_3_with_failure_marker(tmp_path):
    """manifest 写出前失败：rc=3、无 manifest、目录可写时必须留 FAILED.txt。"""
    run_protocol = _runnable_protocol_copy(tmp_path)
    runner = tmp_path / "runner.py"
    runner.write_text(
        "import importlib.util, sys\n"
        f"spec = importlib.util.spec_from_file_location('cli', {str(SCRIPT)!r})\n"
        "cli = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(cli)\n"
        "def broken_write_all(out, files, manifest_text):\n"
        "    out.mkdir(parents=True)\n"
        "    for name, text in files:\n"
        "        (out / name).write_text(text, encoding='utf-8')\n"
        "    raise OSError('SYNTHETIC manifest disk failure')\n"
        "cli._write_all = broken_write_all\n"
        "sys.exit(cli.main(['--protocol', %r, '--mode', 'synthetic', "
        "'--out', sys.argv[1]]))\n" % str(run_protocol),
        encoding="utf-8",
    )
    out = tmp_path / "syn-06"
    proc = subprocess.run([sys.executable, str(runner), str(out)],
                          capture_output=True, text=True, timeout=300)
    assert proc.returncode == 3, proc.stderr
    assert "失败" in proc.stderr
    assert not (out / "manifest.json").exists()
    assert (out / "FAILED.txt").exists()
    # 前序产物在，但不构成完成证明
    assert (out / "values.csv").exists()


def test_offline_guard_self_verifies_before_run(tmp_path):
    """守卫先自证拦截（本地自检连接必须被拒），然后才完整运行。"""
    out = tmp_path / "syn-07"
    proc = _run("--protocol", str(_runnable_protocol_copy(tmp_path)),
                "--mode", "synthetic", "--out", str(out))
    assert proc.returncode == 0, proc.stderr
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["offline_guard"] == {
        "self_check_blocked": True, "blocked_with": "RuntimeError",
    }


# ---------------------------------------------------------------------------
# 真实模式分支：合成 tmp 输入（不伪装真实资料，仅走同一检查管道）
# ---------------------------------------------------------------------------

SNAP_SCHEMA = "research-data-snapshot/1.0"


def _rows(days, base=10.0):
    out = []
    for i, d in enumerate(days):
        c = round(base * (1.0 + 0.0008 * i), 4)
        out.append({"date": d, "open": c, "high": round(c * 1.01, 4),
                    "low": round(c * 0.99, 4), "close": c, "volume": 100.0})
    return out


def _write_snapshot(base: Path, instruments: dict[str, list[dict]], *,
                    uses=("description", "ranking", "research_signal"),
                    econ_events: dict[str, list[dict]] | None = None) -> Path:
    """写合成快照。econ_events 给出时，为相应产品附加按合成分红独立计算的
    economic_index 列（夹具数据，供字段绑定；管道本身仍从 close+events 重建）。"""
    snap = base / "snapshot"
    (snap / "normalized").mkdir(parents=True)
    fields = ["date", "open", "high", "low", "close", "volume"]
    if econ_events:
        import pandas as pd

        sys.path.insert(0, str(ROOT / "src"))
        from lei_signal.research.momentum_prototype import (
            reconstruct_symbol_economic_index,
        )

        fields = fields + ["economic_index"]
    items = []
    for symbol, rows in instruments.items():
        out_rows = rows
        if econ_events and symbol in econ_events:
            close = pd.Series(
                [r["close"] for r in rows],
                index=pd.DatetimeIndex([r["date"] for r in rows]),
            )
            econ, _ = reconstruct_symbol_economic_index(
                close, econ_events[symbol])
            out_rows = [
                dict(r, economic_index=float(econ.loc[pd.Timestamp(r["date"])]))
                for r in rows
            ]
        cols = list(fields)
        text = ",".join(cols) + "\n" + "".join(
            ",".join(str(r[c]) for c in cols) + "\n" for r in out_rows
        )
        rel = f"normalized/{symbol}.csv"
        (snap / rel).write_text(text, encoding="utf-8")
        items.append({
            "instrument_id": symbol,
            "rows": len(out_rows),
            "first_date": out_rows[0]["date"],
            "last_date": out_rows[-1]["date"],
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
            "fields": fields,
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


def _sessions_14m() -> list[str]:
    import pandas as pd

    days = pd.bdate_range("2025-01-02", "2026-02-27")
    return [d.strftime("%Y-%m-%d") for d in days]


def _write_calendar(base: Path, sessions: list[str]) -> Path:
    import calendar as _cal
    from datetime import date

    months = sorted({d[:7] for d in sessions})
    session_set = set(sessions)
    lo, hi = sessions[0], sessions[-1]
    days = {}
    for ym in months:
        y, m = (int(x) for x in ym.split("-"))
        for d in range(1, _cal.monthrange(y, m)[1] + 1):
            day = date(y, m, d).isoformat()
            if not (lo <= day <= hi):
                continue  # 日历只声明数据窗口内的日期，不冒充窗口外的知识
            days[day] = {
                "is_trading_day": day in session_set,
                "source_flag": "1" if day in session_set else "0",
                "source_month": ym,
            }
    p = base / "calendar.json"
    p.write_text(json.dumps({
        "authority": "exchange_official", "publisher": "合成测试日历",
        "months_requested": months, "months_failed": [], "days": days,
    }), encoding="utf-8")
    return p


def _write_publication(base: Path) -> Path:
    p = base / "publication.json"
    p.write_text(json.dumps({
        "authority": "exchange_official", "publisher": "合成测试日历",
        "evidence": "synthetic test fixture", "months": {},
    }), encoding="utf-8")
    return p


def _write_actions(base: Path, events) -> Path:
    p = base / "actions.json"
    p.write_text(json.dumps({"schema_version": 1, "events": events},
                            ensure_ascii=False), encoding="utf-8")
    return p


def _write_test_protocol(base: Path, snap: Path, cal: Path, pub: Path,
                         act: Path, start: str, end: str,
                         *, registry_override: dict | None = None) -> Path:
    protocol = json.loads(PROTOCOL.read_text())
    # 测试协议固定它实际运行的当前代码（CLI/模块随返修变化，协议模板里的
    # 旧冻结哈希会漂移）
    for key, rel in (
        ("run_momentum_research_prototype",
         "scripts/run_momentum_research_prototype.py"),
        ("momentum_prototype",
         "src/lei_signal/research/momentum_prototype.py"),
    ):
        protocol["codes"][key] = {
            "path": rel, "sha256": _sha((ROOT / rel).read_bytes())}
    protocol["inputs"] = {
        "snapshot_dir": {"path": str(snap),
                         "sha256": _sha((snap / "snapshot.json").read_bytes())},
        "calendar": {"path": str(cal), "sha256": _sha(cal.read_bytes())},
        "publication": {"path": str(pub), "sha256": _sha(pub.read_bytes())},
        "actions": {"path": str(act), "sha256": _sha(act.read_bytes())},
        "evaluation_start": start,
        "evaluation_end": end,
        "pool_expectation": {"symbols": 2, "rows": 0, "verify_by_reading": False},
    }
    if registry_override is not None:
        protocol["specs"]["registry"] = registry_override
    p = base / "protocol-test.json"
    p.write_text(json.dumps(protocol, ensure_ascii=False), encoding="utf-8")
    return p


def _real_fixture(tmp_path, *, uses=("description", "ranking", "research_signal"),
                 events=None, registry_override=None):
    sessions = _sessions_14m()
    snap = _write_snapshot(tmp_path, {
        "510300.SS": _rows(sessions),
        "159915.SZ": _rows(sessions),
    }, uses=uses)
    cal = _write_calendar(tmp_path, sessions)
    pub = _write_publication(tmp_path)
    act = _write_actions(tmp_path, events if events is not None else [
        {"event_id": "div-510300-1", "symbol": "510300.SS",
         "type": "cash_dividend", "cash": 0.05,
         "effective_date": "2025-06-16"},
    ])
    protocol = _write_test_protocol(
        tmp_path, snap, cal, pub, act, sessions[0], sessions[-1],
        registry_override=registry_override)
    return protocol


def test_historical_diagnostic_runs_description_only_artifacts(tmp_path):
    protocol = _real_fixture(tmp_path, uses=("description",))
    out = tmp_path / "run-hist-01"
    proc = _run("--protocol", str(protocol), "--mode", "historical-diagnostic",
                "--out", str(out))
    assert proc.returncode == 0, proc.stderr
    assert (out / "values.csv").exists()
    assert (out / "missing.csv").exists()
    assert not (out / "targets.csv").exists()
    assert not (out / "rank-diagnostic.csv").exists()
    skipped = json.loads((out / "skipped-stages.json").read_text())
    assert "targets" in skipped and "rank-diagnostic" in skipped
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["synthetic"] is False
    assert manifest["historical_reconstruction_only"] is True
    assert any(u["event_id"] == "div-510300-1"
               for u in manifest["unknown_available_at"])
    for name, digest in manifest["outputs"].items():
        assert _sha((out / name).read_bytes()) == digest, name


def test_historical_diagnostic_rejected_when_description_blocked(tmp_path):
    protocol = _real_fixture(tmp_path, uses=("ranking",))
    out = tmp_path / "run-hist-02"
    proc = _run("--protocol", str(protocol), "--mode", "historical-diagnostic",
                "--out", str(out))
    assert proc.returncode == 2, proc.stdout
    assert not (out / "values.csv").exists()
    skipped = json.loads((out / "skipped-stages.json").read_text())
    assert "描述用途未获允许" in skipped["economic-reconstruction"]
    quality = json.loads((out / "quality.json").read_text())
    assert quality["uses"]["description"]["default_accepted"] is False
    assert quality["policy"] == "not_applicable_no_account_policy"


def test_qualified_research_rejected_without_signal_use(tmp_path):
    protocol = _real_fixture(tmp_path, uses=("description", "ranking"))
    out = tmp_path / "run-qual-01"
    proc = _run("--protocol", str(protocol), "--mode", "qualified-research",
                "--out", str(out))
    assert proc.returncode == 2, proc.stdout
    assert not (out / "values.csv").exists()
    assert not (out / "rank-diagnostic.csv").exists()
    skipped = json.loads((out / "skipped-stages.json").read_text())
    assert "研究信号用途未获允许" in skipped["rank-diagnostic"]
    report = (out / "report.md").read_text()
    assert "拒绝" in report


def test_qualified_research_rejected_on_missing_economic_index_field(tmp_path):
    """即使三用途都声明，对象缺 economic_index 字段也必须拒绝（当前预期路径）。"""
    protocol = _real_fixture(tmp_path)
    out = tmp_path / "run-qual-02"
    proc = _run("--protocol", str(protocol), "--mode", "qualified-research",
                "--out", str(out))
    assert proc.returncode == 2, proc.stdout
    quality = json.loads((out / "quality.json").read_text())
    momentum_obj = quality["objects"]["mixed.momentum.raw@1.0.0"]
    assert momentum_obj["directly_satisfiable"] is False
    assert "economic_index" in (momentum_obj["missing_fields"] or [])
    skipped = json.loads((out / "skipped-stages.json").read_text())
    assert "对象字段检查未满足" in skipped["targets"]


def test_tampered_quote_file_rejected_by_integrity(tmp_path):
    """协议冻结后篡改报价 CSV：快照内部哈希失配 → 完整性拒绝（2），不进入计算。"""
    protocol = _real_fixture(tmp_path)
    csv_path = tmp_path / "snapshot/normalized/510300.SS.csv"
    lines = csv_path.read_text().splitlines()
    parts = lines[1].split(",")
    parts[4] = "999.0"
    lines[1] = ",".join(parts)
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out = tmp_path / "run-hist-03"
    proc = _run("--protocol", str(protocol), "--mode", "historical-diagnostic",
                "--out", str(out))
    assert proc.returncode == 2, proc.stdout
    quality = json.loads((out / "quality.json").read_text())
    assert quality["integrity"]["verified"] is False
    assert not (out / "values.csv").exists()


def test_tampered_snapshot_json_exits_3_by_protocol_hash(tmp_path):
    """协议冻结后篡改 snapshot.json 本体：协议输入哈希失配 → 输入失败（3）。"""
    protocol = _real_fixture(tmp_path)
    snap_json = tmp_path / "snapshot/snapshot.json"
    payload = json.loads(snap_json.read_text())
    payload["semantics"]["currency"] = "USD"
    snap_json.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "run-hist-06"
    proc = _run("--protocol", str(protocol), "--mode", "historical-diagnostic",
                "--out", str(out))
    assert proc.returncode == 3
    assert not out.exists()
    assert "哈希不一致" in proc.stderr


def test_sources_verification_failure_rejects_research(tmp_path):
    """登记表来源哈希核验失败：研究请求被拒（2），不进入计算。"""
    registry_src = ROOT / "docs/research/definitions.v1.json"
    registry = json.loads(registry_src.read_text())
    first_key = sorted(registry["sources"])[0]
    registry["sources"][first_key]["sha256"] = "0" * 64
    reg_copy = tmp_path / "registry-bad.json"
    reg_copy.write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")
    protocol = _real_fixture(
        tmp_path,
        registry_override={"path": str(reg_copy), "version": "1.2.0",
                           "sha256": _sha(reg_copy.read_bytes())},
    )
    out = tmp_path / "run-hist-04"
    proc = _run("--protocol", str(protocol), "--mode", "historical-diagnostic",
                "--out", str(out))
    assert proc.returncode == 2, proc.stdout
    quality = json.loads((out / "quality.json").read_text())
    assert quality["sources_verified"] is False
    assert not (out / "values.csv").exists()
    skipped = json.loads((out / "skipped-stages.json").read_text())
    assert "来源哈希核验未通过" in skipped["economic-reconstruction"]


def test_bare_code_actions_attach_via_snapshot_mapping(tmp_path):
    """行动记录用裸码（如 510300）时按快照侧既有明确映射挂接；
    unknown available_at 必须如实上报，不得静默丢弃后宣称完整。"""
    protocol = _real_fixture(tmp_path, uses=("description",), events=[
        {"event_id": "div-510300-bare", "symbol": "510300",
         "type": "cash_dividend", "cash_per_unit": 0.059,
         "effective_date": "2025-06-16"},
    ])
    out = tmp_path / "run-hist-07"
    proc = _run("--protocol", str(protocol), "--mode", "historical-diagnostic",
                "--out", str(out))
    assert proc.returncode == 0, proc.stderr
    manifest = json.loads((out / "manifest.json").read_text())
    assert any(u["event_id"] == "div-510300-bare" and u["symbol"] == "510300.SS"
               for u in manifest["unknown_available_at"])


def test_unmappable_action_symbol_rejects_run(tmp_path):
    """行动记录身份完全无法映射：整个研究请求按质量限制拒绝（2）。"""
    protocol = _real_fixture(tmp_path, uses=("description",), events=[
        {"event_id": "div-ghost", "symbol": "999999",
         "type": "cash_dividend", "cash_per_unit": 0.1,
         "effective_date": "2025-06-16"},
    ])
    out = tmp_path / "run-hist-08"
    proc = _run("--protocol", str(protocol), "--mode", "historical-diagnostic",
                "--out", str(out))
    assert proc.returncode == 2, proc.stdout
    assert not (out / "values.csv").exists()
    report = (out / "report.md").read_text()
    assert "999999" in report


# ---------------------------------------------------------------------------
# 返修 A：非法行动记录不得进入重建（主控复核 §2）
# ---------------------------------------------------------------------------


def test_action_with_account_field_rejected_from_computation(tmp_path):
    """混入账户字段 fee 的分红：不得消费该记录，运行不留下完成产物。"""
    protocol = _real_fixture(tmp_path, uses=("description",), events=[
        {"event_id": "div-fee", "symbol": "510300.SS",
         "type": "cash_dividend", "cash": 0.05,
         "effective_date": "2025-06-16", "fee": 1.0},
    ])
    out = tmp_path / "run-hist-a1"
    proc = _run("--protocol", str(protocol), "--mode", "historical-diagnostic",
                "--out", str(out))
    assert proc.returncode == 2, proc.stdout
    assert not (out / "values.csv").exists()
    report = (out / "report.md").read_text()
    assert "div-fee" in report
    quality = json.loads((out / "quality.json").read_text())
    assert quality["policy"] == "not_applicable_no_account_policy"


def test_negative_dividend_rejected_from_computation(tmp_path):
    """负金额分红：拒绝，不得改变数值后仍宣称完整。"""
    protocol = _real_fixture(tmp_path, uses=("description",), events=[
        {"event_id": "div-neg", "symbol": "510300.SS",
         "type": "cash_dividend", "cash": -0.05,
         "effective_date": "2025-06-16"},
    ])
    out = tmp_path / "run-hist-a2"
    proc = _run("--protocol", str(protocol), "--mode", "historical-diagnostic",
                "--out", str(out))
    assert proc.returncode == 2, proc.stdout
    assert not (out / "values.csv").exists()
    report = (out / "report.md").read_text()
    assert "div-neg" in report


# ---------------------------------------------------------------------------
# 返修 B：协议身份必须与实际算法绑定（主控复核 §3）
# ---------------------------------------------------------------------------


def _tamper_protocol(tmp_path, mutate):
    protocol = json.loads(_runnable_protocol_copy(tmp_path).read_text())
    mutate(protocol)
    p = tmp_path / "protocol-tampered.json"
    p.write_text(json.dumps(protocol, ensure_ascii=False), encoding="utf-8")
    return p


def test_protocol_unknown_primary_object_rejected(tmp_path):
    """objects.primary 指向不存在的对象：拒绝（3），不得照抄身份产出完成假象。"""
    bad = _tamper_protocol(
        tmp_path, lambda p: p["objects"].__setitem__("primary", "nosuch.object@9.9.9"))
    out = tmp_path / "syn-b1"
    proc = _run("--protocol", str(bad), "--mode", "synthetic", "--out", str(out))
    assert proc.returncode == 3, proc.stdout
    assert not out.exists()
    assert "身份" in proc.stderr or "对象" in proc.stderr


def test_protocol_unsupported_target_rejected(tmp_path):
    """target_id 改为不支持的窗口：拒绝（3），targets 不得按固定算法照抄错误 ID。"""
    bad = _tamper_protocol(
        tmp_path,
        lambda p: p.__setitem__("target_id", "protocol:unsupported-999-session@9.9.9"))
    out = tmp_path / "syn-b2"
    proc = _run("--protocol", str(bad), "--mode", "synthetic", "--out", str(out))
    assert proc.returncode == 3
    assert not out.exists()


def test_protocol_card_snapshot_mismatch_rejected(tmp_path):
    """协议里存的卡快照与登记表实际解析不一致：拒绝（3）。"""
    def mutate(p):
        card = p["objects"]["cards"]["mixed.momentum.raw@1.0.0"]["card"]
        card["definition"]["parameters"]["long_lag"] = 100
    bad = _tamper_protocol(tmp_path, mutate)
    out = tmp_path / "syn-b3"
    proc = _run("--protocol", str(bad), "--mode", "synthetic", "--out", str(out))
    assert proc.returncode == 3
    assert not out.exists()


def test_protocol_missing_required_code_key_rejected(tmp_path):
    """删掉必需代码键（如 momentum_prototype）不能免核：拒绝（3）。"""
    def mutate(p):
        p["codes"].pop("momentum_prototype")
    bad = _tamper_protocol(tmp_path, mutate)
    out = tmp_path / "syn-b4"
    proc = _run("--protocol", str(bad), "--mode", "synthetic", "--out", str(out))
    assert proc.returncode == 3
    assert not out.exists()


def test_protocol_wrong_cli_hash_rejected(tmp_path):
    """协议绑定的新 CLI 自身哈希被改：拒绝（3）。"""
    def mutate(p):
        p["codes"]["run_momentum_research_prototype"]["sha256"] = "0" * 64
    bad = _tamper_protocol(tmp_path, mutate)
    out = tmp_path / "syn-b5"
    proc = _run("--protocol", str(bad), "--mode", "synthetic", "--out", str(out))
    assert proc.returncode == 3
    assert not out.exists()


def test_protocol_registry_version_mismatch_rejected(tmp_path):
    """协议声明的登记表容器版本与实际文件不符：拒绝（3）。"""
    def mutate(p):
        p["specs"]["registry"]["version"] = "v0.0.1"
    bad = _tamper_protocol(tmp_path, mutate)
    out = tmp_path / "syn-b6"
    proc = _run("--protocol", str(bad), "--mode", "synthetic", "--out", str(out))
    assert proc.returncode == 3
    assert not out.exists()


# ---------------------------------------------------------------------------
# 返修 R1：时间资格——非空可得时间不等于历史时点合格（主控复核 §9.2）
# ---------------------------------------------------------------------------


def _time_fixture(tmp_path, *, available_at, effective_date="2025-06-16",
                  event_id="div-time-1", window_end="2026-02-27",
                  both_products_late=False):
    """合成时间夹具：economic_index 列使对象字段绑定真实通过（不 patch 检查），
    唯一合成分红的 available_at/effective_date 可配置。纯合成，非市场资料。
    window_end 截断研究窗口（默认 2026-02-27）；both_products_late 使两只
    产品各自带一条同条件事件（全标签排除场景）。"""
    import pandas as pd

    sessions = [d.strftime("%Y-%m-%d")
                for d in pd.bdate_range("2025-01-02", window_end)]
    events = [{
        "event_id": event_id, "symbol": "510300.SS",
        "type": "cash_dividend", "cash": 0.05,
        "effective_date": effective_date,
        **({"available_at": available_at} if available_at is not None else {}),
    }]
    econ_events = {"510300.SS": list(events), "159915.SZ": []}
    if both_products_late:
        ev2 = dict(events[0], symbol="159915.SZ", event_id=event_id + "-b")
        events = events + [ev2]
        econ_events = {"510300.SS": [events[0]], "159915.SZ": [ev2]}
    snap = _write_snapshot(tmp_path, {
        "510300.SS": _rows(sessions),
        "159915.SZ": _rows(sessions),
    }, uses=("description", "ranking", "research_signal"), econ_events=econ_events)
    cal = _write_calendar(tmp_path, sessions)
    pub = _write_publication(tmp_path)
    act = _write_actions(tmp_path, events)
    return _write_test_protocol(
        tmp_path, snap, cal, pub, act, sessions[0], sessions[-1])


def test_time_qualified_early_available_passes(tmp_path):
    """正向控制：行动在生效前已知 → qualified 真实放行并产出 targets/rank。
    替换旧的强制放行路由测试——时间条件真实满足，不经 patch。"""
    protocol = _time_fixture(tmp_path, available_at="2025-06-15T10:00:00+08:00")
    out = tmp_path / "run-time-early"
    proc = _run("--protocol", str(protocol), "--mode", "qualified-research",
                "--out", str(out))
    assert proc.returncode == 0, proc.stderr
    assert (out / "targets.csv").exists()
    assert (out / "rank-diagnostic.csv").exists()
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["historical_reconstruction_only"] is False
    assert manifest["statuses"]["research_qualification"] == "qualified_for_this_mode"
    quality = json.loads((out / "quality.json").read_text())
    assert quality["target_label_status"]["counts"]["action_not_knowable"] == 0
    assert "observation_cutoff_assumption" in quality


def test_time_late_available_rejected_in_qualified(tmp_path):
    """主控反例复现：2030 年才可得的分红不得计入 2025–2026 研究并标合格。"""
    protocol = _time_fixture(tmp_path, available_at="2030-01-01T10:00:00+08:00")
    out = tmp_path / "run-time-late"
    proc = _run("--protocol", str(protocol), "--mode", "qualified-research",
                "--out", str(out))
    assert proc.returncode == 2, proc.stdout
    assert not (out / "values.csv").exists()
    assert not (out / "targets.csv").exists()
    report = (out / "report.md").read_text()
    assert "div-time-1" in report and "2030-01-01" in report
    quality = json.loads((out / "quality.json").read_text())
    assert quality["policy"] == "not_applicable_no_account_policy"


def test_time_null_available_rejected_in_qualified(tmp_path):
    protocol = _time_fixture(tmp_path, available_at=None)
    out = tmp_path / "run-time-null"
    proc = _run("--protocol", str(protocol), "--mode", "qualified-research",
                "--out", str(out))
    assert proc.returncode == 2, proc.stdout
    assert not (out / "targets.csv").exists()
    report = (out / "report.md").read_text()
    assert "available_at" in report


def test_time_same_day_close_boundary_tz_aware(tmp_path):
    """同日时区边界：生效日即观察日时，收盘 15:00 前可知才可用于该日信号；
    严格带时区比较，无时区时间戳不能冒充可知。"""
    early = _time_fixture(tmp_path / "ok", available_at="2025-06-30T14:00:00+08:00",
                          effective_date="2025-06-30")
    out = tmp_path / "run-time-boundary-ok"
    proc = _run("--protocol", str(early), "--mode", "qualified-research",
                "--out", str(out))
    assert proc.returncode == 0, proc.stderr

    late = _time_fixture(tmp_path / "late", available_at="2025-06-30T16:00:00+08:00",
                         effective_date="2025-06-30")
    out2 = tmp_path / "run-time-boundary-late"
    proc2 = _run("--protocol", str(late), "--mode", "qualified-research",
                 "--out", str(out2))
    assert proc2.returncode == 2, proc2.stdout

    naive = _time_fixture(tmp_path / "naive", available_at="2025-06-30T14:00:00",
                          effective_date="2025-06-30")
    out3 = tmp_path / "run-time-boundary-naive"
    proc3 = _run("--protocol", str(naive), "--mode", "qualified-research",
                 "--out", str(out3))
    assert proc3.returncode == 2, proc3.stdout


def test_time_target_not_yet_knowable_excluded_from_rank(tmp_path):
    """目标本用于事后评价：生效日在所有观察日之后、但落在某个完整目标窗
    [e,x] 内的行动，不构成信号泄漏（不拒绝研究）；但该目标标签在 x 决策
    时点尚不可知，须从排序配对中剔除并留痕。窗口延至 2026-03-06（3 月为
    不完整月，不产生观察日），使 2026-01-30 观察日的目标窗 x=2026-03-03
    完整覆盖事件生效日 2026-03-02。"""
    protocol = _time_fixture(tmp_path, available_at="2026-04-01T10:00:00+08:00",
                             effective_date="2026-03-02", window_end="2026-03-06")
    out = tmp_path / "run-time-target"
    proc = _run("--protocol", str(protocol), "--mode", "qualified-research",
                "--out", str(out))
    assert proc.returncode == 0, proc.stderr
    assert (out / "targets.csv").exists()
    quality = json.loads((out / "quality.json").read_text())
    detail = quality["target_label_status"]["action_not_knowable_detail"]
    assert len(detail) == 1
    assert detail[0]["product"] == "510300.SS"
    assert detail[0]["observation_date"] == "2026-01-30"
    assert detail[0]["events"][0]["event_id"] == "div-time-1"
    counts = quality["target_label_status"]["counts"]
    assert counts["action_not_knowable"] == 1 and counts["available"] >= 1
    assert sum(counts.values()) == quality["target_label_status"]["total"]


def test_time_late_marked_reconstruction_in_historical(tmp_path):
    """同一 2030 反例在历史诊断中：可诚实计算但必须标晚取得/事后重建，
    不能标为历史已知。"""
    protocol = _time_fixture(tmp_path, available_at="2030-01-01T10:00:00+08:00")
    out = tmp_path / "run-time-hist"
    proc = _run("--protocol", str(protocol), "--mode", "historical-diagnostic",
                "--out", str(out))
    assert proc.returncode == 0, proc.stderr
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["historical_reconstruction_only"] is True
    late = manifest["late_available_at"]
    assert any(e["event_id"] == "div-time-1" and "2030-01-01" in str(e["available_at"])
               for e in late)
    assert (out / "values.csv").exists()


def test_time_mid_window_late_marked_reconstruction_in_historical(tmp_path):
    """Task 0 T2（主控 closeout 反例）：生效 2025-06-16、2026-01-01 才可得、
    评价期至 2026-02-27——晚于 2025-06-30/07-31 等历史观察时点，必须标
    事后重建；不得因早于评价期末而漏标。"""
    protocol = _time_fixture(tmp_path, available_at="2026-01-01T10:00:00+08:00")
    out = tmp_path / "run-time-midlate"
    proc = _run("--protocol", str(protocol), "--mode", "historical-diagnostic",
                "--out", str(out))
    assert proc.returncode == 0, proc.stderr
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["historical_reconstruction_only"] is True
    late = manifest["late_available_at"]
    hit = [e for e in late if e["event_id"] == "div-time-1"]
    assert hit, "期内晚取得的行动必须出现在 late_available_at"
    assert "观察日" in hit[0]["reason"]


def test_all_labels_unavailable_keeps_date_rows_not_crash(tmp_path):
    """Task 0 T1（主控 closeout 反例）：同一期全部产品标签不可知时，
    保留日期行（n=0、value 缺失、原因），不得 KeyError 退出 3。"""
    protocol = _time_fixture(
        tmp_path, available_at="2026-04-01T10:00:00+08:00",
        effective_date="2026-03-02", window_end="2026-03-06",
        both_products_late=True)
    out = tmp_path / "run-time-alldark"
    proc = _run("--protocol", str(protocol), "--mode", "qualified-research",
                "--out", str(out))
    assert proc.returncode == 0, proc.stderr
    rank = (out / "rank-diagnostic.csv").read_text().strip().splitlines()
    hit = [r for r in rank if ",2026-01-30," in r]
    assert len(hit) == 1
    parts = hit[0].split(",")
    assert parts[2] == "0" and parts[3] == "" and "fewer_than_three_pairs" in parts[4]
    quality = json.loads((out / "quality.json").read_text())
    counts = quality["target_label_status"]["counts"]
    assert counts["action_not_knowable"] == 2
    assert sum(counts.values()) == quality["target_label_status"]["total"]


def test_recovered_and_misnamed_protocol_v103_hashes_locked():
    """Task 0 T3：锁定两个文件的字节身份——主控重构件才是 §9 核验过的
    v1.0.3（7d7562f7…）；现存 protocol-v1.0.3.json（1c8d99c1…）不是原件。"""
    recovered = (ROOT / "docs/experiments/raw/momentum-prototype-controller-review"
                 "-2026-09-13/closeout-run-01/recovered-protocol-v1.0.3.json")
    misnamed = (ROOT / "docs/experiments/raw/research-momentum-prototype"
                "-2026-09-13/protocol-v1.0.3.json")
    assert _sha(recovered.read_bytes()) == (
        "7d7562f7d350038643ce4d099254d7bcc2c95ffdc137e1707e843b30eca8da1f")
    assert _sha(misnamed.read_bytes()) == (
        "1c8d99c1c72cd71ac0cd4dd030c4fe6de86cfc03fb94fc1136131833b8fe108f")


@pytest.mark.parametrize("stage", ["preflight_json", "report"])
def test_real_mode_rejection_outputs_keep_hashes_consistent(tmp_path, stage):
    protocol = _real_fixture(tmp_path, uses=("ranking",))
    out = tmp_path / f"run-hist-05-{stage}"
    proc = _run("--protocol", str(protocol), "--mode", "historical-diagnostic",
                "--out", str(out))
    assert proc.returncode == 2
    manifest = json.loads((out / "manifest.json").read_text())
    for name, digest in manifest["outputs"].items():
        assert _sha((out / name).read_bytes()) == digest, name
    assert manifest["statuses"]["research_qualification"] == "rejected"
