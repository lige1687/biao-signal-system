"""factor_evidence CLI 与失败保护集成测试（合成，不触真实观察分析）。

子进程负路由覆盖：协议缺失/草案/删规范键/坏日期窗口/假版本文件名/输出
已存在/导入不写盘。合法完成与写盘中途失败用进程内合成入口
``runner.run_analysis``（显式传入合成观察表），不经真实输入身份，也不
运行真实 B1 统计；真实 CLI 的首次正式运行属于 Task 5 预算，不在测试内。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lei_signal.research.factor_evidence import runner
from lei_signal.research.factor_evidence.contract import (
    CARD,
    FIXED_INPUT_IDENTITY,
    FIXED_NO_CLAIMS,
    FIXED_PARAMS,
    FIXED_TOLERANCE,
    FIXED_USE,
    IDENTITY,
    OBJECT_REF,
    REQUIRED_CODE_KEYS,
    REQUIRED_OUTPUT_FIELDS,
    REQUIRED_STANDARDS,
    SPEC_VERSION,
    TASK_BOOK,
)

REPO = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
SCRIPT = REPO / "scripts/run_factor_evidence_reliability.py"
CLI = [sys.executable, str(SCRIPT)]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _protocol(**over):
    p = {
        "identity": IDENTITY, "spec_status": "frozen",
        "spec_version": SPEC_VERSION,
        "object_ref": OBJECT_REF, "use": FIXED_USE,
        "fixed_params": json.loads(json.dumps(FIXED_PARAMS)),
        "standards": [{"path": a, "version": b, "sha256": c}
                      for a, b, c in REQUIRED_STANDARDS],
        "task_book": dict(TASK_BOOK), "candidate_card": dict(CARD),
        "input_identity": dict(FIXED_INPUT_IDENTITY),
        "code_identity": {rel: _sha(REPO / rel) for rel in REQUIRED_CODE_KEYS},
        "tolerance": dict(FIXED_TOLERANCE),
        "output_fields": list(REQUIRED_OUTPUT_FIELDS),
        "no_claims": list(FIXED_NO_CLAIMS), "approval": None,
    }
    p.update(over)
    return p


# ── 子进程负路由（身份/合同错误一律 exit 3；无真实计算） ───────────

def _run_cli(args, cwd):
    return subprocess.run(CLI + args, cwd=cwd, capture_output=True,
                          text=True, timeout=120)


def test_cli_help_imports_without_writing(tmp_path):
    r = _run_cli(["--help"], tmp_path)
    assert r.returncode == 0
    assert list(tmp_path.iterdir()) == []  # 导入/帮助不写盘


def test_cli_missing_protocol_exit3(tmp_path):
    r = _run_cli(["--protocol", str(tmp_path / "none.json"),
                  "--out", str(tmp_path / "run-x")], tmp_path)
    assert r.returncode == 3


def test_cli_draft_protocol_exit3(tmp_path):
    p = tmp_path / "protocol-v1.0.0.json"
    p.write_text(json.dumps(_protocol(spec_status="draft")), encoding="utf-8")
    r = _run_cli(["--protocol", str(p), "--out", str(tmp_path / "run-x")],
                 tmp_path)
    assert r.returncode == 3


def test_cli_trimmed_standards_exit3(tmp_path):
    proto = _protocol()
    proto["standards"] = proto["standards"][:2]
    p = tmp_path / "protocol-v1.0.0.json"
    p.write_text(json.dumps(proto), encoding="utf-8")
    r = _run_cli(["--protocol", str(p), "--out", str(tmp_path / "run-x")],
                 tmp_path)
    assert r.returncode == 3


def test_cli_bad_date_window_exit3(tmp_path):
    proto = _protocol()
    proto["fixed_params"]["evaluation_window"] = {"start": "2019/10/08",
                                                  "end": "2025-12-31"}
    p = tmp_path / "protocol-v1.0.0.json"
    p.write_text(json.dumps(proto), encoding="utf-8")
    r = _run_cli(["--protocol", str(p), "--out", str(tmp_path / "run-x")],
                 tmp_path)
    assert r.returncode == 3


def test_cli_fake_version_filename_exit3(tmp_path):
    p = tmp_path / "protocol-v9.9.9.json"
    p.write_text(json.dumps(_protocol(spec_version="9.9.9")), encoding="utf-8")
    r = _run_cli(["--protocol", str(p), "--out", str(tmp_path / "run-x")],
                 tmp_path)
    assert r.returncode == 3


def test_cli_output_exists_refused_before_compute(tmp_path):
    out = tmp_path / "run-exists"
    out.mkdir()
    (out / "keep.txt").write_text("user data", encoding="utf-8")
    dummy = tmp_path / "protocol-v1.0.0.json"
    dummy.write_text("{}", encoding="utf-8")
    r = _run_cli(["--protocol", str(dummy), "--out", str(out)], tmp_path)
    assert r.returncode == 3
    assert (out / "keep.txt").read_text(encoding="utf-8") == "user data"


# ── 合法完成（进程内合成入口；不触真实观察分析） ───────────────────

N_WINDOW, N_TAIL = 40, 30
DAYS = [d.strftime("%Y-%m-%d")
        for d in pd.bdate_range("2019-10-08", periods=N_WINDOW + N_TAIL)]
COLS = ["symbol", "session", "state", "main", "aux", "legal",
        "legal_reason", "e_date", "x_date"]


def _synthetic():
    schedule = pd.DataFrame({"session": DAYS,
                             "in_window": [i < N_WINDOW
                                           for i in range(len(DAYS))]})
    rows = []
    for i in range(N_WINDOW):
        state = bool(i % 2)
        rows.append({"symbol": "SYN", "session": DAYS[i], "state": state,
                     "main": 0.01 * (1 if state else -1) + 0.001 * i,
                     "aux": -0.01, "legal": True, "legal_reason": None,
                     "e_date": DAYS[i + 1], "x_date": DAYS[i + 22]})
    frame = pd.DataFrame(rows, columns=COLS)
    params = json.loads(json.dumps(FIXED_PARAMS))
    params["resampling"] = {**params["resampling"], "reps": 12,
                            "block_lengths": [5, 10]}
    return frame, schedule, params


_SYN_META = {"mode": "synthetic", "symbol": "SYN",
             "object_ref": "synthetic:example@0"}


def test_run_analysis_synthetic_complete_manifest(tmp_path):
    frame, schedule, params = _synthetic()
    out = tmp_path / "run-s"
    summary = runner.run_analysis(frame, schedule, params, out_dir=out,
                                  source_meta=dict(_SYN_META))
    assert summary["full_delta"] is not None
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["completed"] is True and manifest["exit_code"] == 0
    # 文件集合双向一致（只排除顶层 manifest 本身）
    actual = {str(f.relative_to(out)) for f in out.rglob("*") if f.is_file()}
    listed = set(manifest["files"]) | {"manifest.json"}
    assert actual == listed
    for rel, meta in manifest["files"].items():
        assert hashlib.sha256((out / rel).read_bytes()).hexdigest() \
            == meta["sha256"]
    # 合成输出不得冒用真实身份（主控R1）：标的/来源/参数逐项对账
    card = json.loads((out / "evidence-card.json").read_text(encoding="utf-8"))
    assert card["synthetic"] is True
    assert card["symbol"] == "SYN"
    assert card["object_ref"] == "synthetic:example@0"
    assert card["use"] == FIXED_USE
    assert card["input"]["mode"] == "synthetic"
    assert card["resampling"]["block_lengths"] == [5, 10]
    assert card["resampling"]["reps"] == 12
    assert card["resampling"]["seed"] == 20260916
    card_text = json.dumps(card, ensure_ascii=False)
    assert "510300" not in card_text and "b1-dual-ma" not in card_text
    assert manifest["metadata"]["mode"] == "synthetic"
    assert manifest["metadata"]["symbol"] == "SYN"
    # 合成运行没有正式协议：占位说明而非冻结协议副本
    proto_note = json.loads((out / "protocol.source.json")
                            .read_text(encoding="utf-8"))
    assert proto_note["mode"] == "synthetic"
    # 标准 JSON：合法缺失为 null，不出现 NaN/Infinity
    text = (out / "uncertainty.json").read_text(encoding="utf-8")
    assert "NaN" not in text and "Infinity" not in text
    starts = np.load(out / "resampling-L5-starts.npy")
    assert starts.shape == (12, 8)  # n=40, L=5 → k=8
    assert manifest["metadata"]["unit"]


def test_run_analysis_real_mode_identity_conflict_rejected(tmp_path):
    # 主控R1反例：真实模式 + 合成标的 = 身份冲突，必须在写盘前拒绝
    frame, schedule, params = _synthetic()
    out = tmp_path / "run-conflict"
    with pytest.raises(ValueError, match="身份|symbol|冲突|标的"):
        runner.run_analysis(frame, schedule, FIXED_PARAMS, out_dir=out,
                            source_meta={
                                "mode": "real",
                                "input_identity": dict(FIXED_INPUT_IDENTITY)})
    assert not out.exists()


def test_run_analysis_requires_explicit_mode(tmp_path):
    frame, schedule, params = _synthetic()
    out = tmp_path / "run-nomode"
    with pytest.raises(ValueError, match="mode|synthetic|real"):
        runner.run_analysis(frame, schedule, params, out_dir=out,
                            source_meta={"protocol_path": tmp_path / "x"})
    assert not out.exists()


def test_run_analysis_single_group_completes_not_estimable(tmp_path):
    # 主控R2反例：单组资料必须完成诚实的"不可估计"报告，不得在渲染崩溃
    schedule = pd.DataFrame({"session": DAYS,
                             "in_window": [i < N_WINDOW
                                           for i in range(len(DAYS))]})
    rows = [{"symbol": "SYN", "session": DAYS[i], "state": True,
             "main": 0.01 * i, "aux": -0.01, "legal": True,
             "legal_reason": None, "e_date": DAYS[i + 1],
             "x_date": DAYS[i + 22]} for i in range(N_WINDOW)]
    frame = pd.DataFrame(rows, columns=COLS)
    params = json.loads(json.dumps(FIXED_PARAMS))
    params["resampling"] = {**params["resampling"], "reps": 4,
                            "block_lengths": [5]}
    out = tmp_path / "run-single"
    runner.run_analysis(frame, schedule, params, out_dir=out,
                        source_meta=dict(_SYN_META))
    stab = json.loads((out / "stability.json").read_text(encoding="utf-8"))
    assert stab["full_period"]["delta"] is None
    assert stab["full_period"]["null_reason"]
    unc = json.loads((out / "uncertainty.json").read_text(encoding="utf-8"))
    assert unc["resampling"]["L5"]["valid_reps"] == 0
    assert unc["resampling"]["L5"]["quantile_lower"] is None
    assert unc["resampling"]["L5"]["range_withheld_reason"]
    report = (out / "report.md").read_text(encoding="utf-8")
    assert "not_estimable" in report or "null" in report
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["completed"] is True  # 工程完成＝诚实写出不可估计


def test_run_analysis_refuses_existing_output(tmp_path):
    frame, schedule, params = _synthetic()
    out = tmp_path / "run-dup"
    out.mkdir()
    with pytest.raises(ValueError, match="已存在|拒绝"):
        runner.run_analysis(frame, schedule, params, out_dir=out,
                            source_meta=dict(_SYN_META))


def test_run_analysis_midwrite_failure_leaves_no_completed_manifest(
        tmp_path, monkeypatch):
    frame, schedule, params = _synthetic()
    out = tmp_path / "run-fail"
    real_save = np.save

    def failing_save(file, arr, **kw):
        raise OSError("disk full (synthetic injection)")

    monkeypatch.setattr(runner.np, "save", failing_save)
    with pytest.raises(OSError):
        runner.run_analysis(frame, schedule, params, out_dir=out,
                            source_meta=dict(_SYN_META))
    monkeypatch.setattr(runner.np, "save", real_save)
    assert not (out / "manifest.json").exists()
    # 恢复后同目录不得复用（已存在拒绝），换新目录可完整完成
    out2 = tmp_path / "run-retry"
    runner.run_analysis(frame, schedule, params, out_dir=out2,
                        source_meta=dict(_SYN_META))
    assert json.loads((out2 / "manifest.json").read_text(
        encoding="utf-8"))["completed"] is True


def test_main_returns_2_for_not_estimable_real_data(tmp_path, monkeypatch):
    # 资料不足（单组）走原合同出口 2；不产生输出目录、不写 completed
    proto = tmp_path / "protocol-v1.0.0.json"
    proto.write_text(json.dumps(_protocol(), ensure_ascii=False),
                     encoding="utf-8")
    schedule = pd.DataFrame({"session": DAYS,
                             "in_window": [i < N_WINDOW
                                           for i in range(len(DAYS))]})
    rows = [{"symbol": "SYN", "session": DAYS[i], "state": True,
             "main": 0.01 * i, "aux": -0.01, "legal": True,
             "legal_reason": None, "e_date": DAYS[i + 1],
             "x_date": DAYS[i + 22]} for i in range(N_WINDOW)]
    frame = pd.DataFrame(rows, columns=COLS)

    def fake_load(root, contract):
        return frame, schedule, {"hashes_verified": 6}

    monkeypatch.setattr(runner, "load_b1_observations", fake_load)
    out = tmp_path / "run-2"
    rc = runner.main(proto, out, REPO)
    assert rc == 2
    assert not out.exists()
