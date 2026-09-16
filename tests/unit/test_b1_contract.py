"""b1_contract 测试：协议逐值绑定 + 输入包逐项核验（合成反例为主）。

合法合成输入仅用于单元测试内部：load_verified_input 的合同参数即"期望身份"，
正式 CLI 只接受经 validate_b1_protocol 绑定到模块常量的协议——没有可向正式
CLI 注入任意文件的"跳过资格"选项，本文件同时锁定这一点。
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from lei_signal.research.factor_unit.b1_contract import (
    CARD_PATH,
    CARD_SHA256,
    FIXED_DATA_DECLARATIONS,
    FIXED_INPUT_IDENTITY,
    FIXED_NO_CLAIMS,
    FIXED_PARAMS,
    FIXED_TOLERANCE,
    REQUIRED_CODE_KEYS,
    REQUIRED_OUTPUT_FIELDS,
    REQUIRED_STANDARDS,
    SPEC_VERSION,
    TASK_BOOK,
    B1IncompleteError,
    load_verified_input,
    validate_b1_protocol,
)

REPO = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
REAL_PACK = REPO / FIXED_INPUT_IDENTITY["package"]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _protocol(**over):
    p = {
        "spec_status": "frozen",
        "spec_version": SPEC_VERSION,
        **FIXED_PARAMS,
        **FIXED_DATA_DECLARATIONS,
        "candidate_card": {"path": CARD_PATH, "sha256": CARD_SHA256},
        "task_book": dict(TASK_BOOK),
        "standards": [{"path": path, "version": version, "sha256": sha}
                      for path, version, sha in REQUIRED_STANDARDS],
        "tolerance": dict(FIXED_TOLERANCE),
        "output_fields": list(REQUIRED_OUTPUT_FIELDS),
        "no_claims": list(FIXED_NO_CLAIMS),
        "input_identity": dict(FIXED_INPUT_IDENTITY),
        "code_identity": {rel: _sha(REPO / rel) for rel in REQUIRED_CODE_KEYS},
    }
    p.update(over)
    return p


def _write_protocol(tmp: Path, proto: dict, name=None) -> Path:
    p = tmp / (name or f"protocol-v{SPEC_VERSION}.json")
    p.write_text(json.dumps(proto, ensure_ascii=False))
    return p


# ── 协议校验：正例与逐值反例 ─────────────────────────────────────────

def test_valid_frozen_protocol_passes(tmp_path):
    contract = validate_b1_protocol(_write_protocol(tmp_path, _protocol()), REPO)
    assert contract["symbol"] == "510300"
    assert contract["input_identity"] == FIXED_INPUT_IDENTITY


def test_draft_protocol_rejected(tmp_path):
    p = _write_protocol(tmp_path, _protocol(spec_status="draft_pending_controller_freeze"))
    with pytest.raises(ValueError, match="草案|冻结|frozen"):
        validate_b1_protocol(p, REPO)


def test_self_granted_approval_rejected(tmp_path):
    p = _write_protocol(tmp_path, _protocol(approval=True))
    with pytest.raises(ValueError, match="approval"):
        validate_b1_protocol(p, REPO)


def test_fixed_params_cannot_change(tmp_path):
    for i, (key, bad) in enumerate((
            ("symbol", "159915"), ("object_ref", "other@1.0.0"),
            ("evaluation_window", {"start": "2020-01-01", "end": "2025-12-31"}),
            ("x_offset", 21), ("sparse_anchor_session", "2019-10-09"),
            ("sparse_step", 22),
            ("label_maturity_cutoff", "2026-02-04T15:00:00+08:00"),
            ("target_basis", "total_return_wealth"))):
        sub = tmp_path / str(i)
        sub.mkdir()
        p = _write_protocol(sub, _protocol(**{key: bad}))
        with pytest.raises(ValueError, match="逐值|不符"):
            validate_b1_protocol(p, REPO)


def test_standards_cannot_trim_or_drift(tmp_path):
    proto = _protocol()
    proto["standards"] = []  # 主控R1反例：删空standards必须拒绝
    with pytest.raises(ValueError, match="standards"):
        validate_b1_protocol(_write_protocol(tmp_path, proto), REPO)
    proto = _protocol()
    proto["standards"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="指纹"):
        validate_b1_protocol(_write_protocol(tmp_path, proto), REPO)
    proto = _protocol()
    proto["standards"].append({"path": "docs/extra.md", "version": "1",
                               "sha256": "0" * 64})
    with pytest.raises(ValueError, match="裁剪|扩项"):
        validate_b1_protocol(_write_protocol(tmp_path, proto), REPO)


def test_tolerance_outputs_no_claims_cannot_change(tmp_path):
    proto = _protocol()
    proto["tolerance"]["float"] = 1  # 主控R1反例：容差改1必须拒绝
    with pytest.raises(ValueError, match="tolerance"):
        validate_b1_protocol(_write_protocol(tmp_path, proto), REPO)
    proto = _protocol()
    proto["output_fields"] = proto["output_fields"][:-1]
    with pytest.raises(ValueError, match="output_fields"):
        validate_b1_protocol(_write_protocol(tmp_path, proto), REPO)
    proto = _protocol()
    proto["no_claims"] = proto["no_claims"][:-1]
    with pytest.raises(ValueError, match="no_claims"):
        validate_b1_protocol(_write_protocol(tmp_path, proto), REPO)


def test_current_and_renamed_entry_rejected(tmp_path):
    proto = _protocol()
    p = _write_protocol(tmp_path, proto, name="current.json")
    with pytest.raises(ValueError, match="文件名|current"):
        validate_b1_protocol(p, REPO)
    p = _write_protocol(tmp_path, proto, name="protocol-v9.9.9.json")
    with pytest.raises(ValueError, match="spec_version|文件名"):
        validate_b1_protocol(p, REPO)


def test_forged_synthetic_mode_rejected(tmp_path):
    p = _write_protocol(tmp_path, _protocol(data_mode="synthetic"))
    with pytest.raises(ValueError):
        validate_b1_protocol(p, REPO)


def test_code_keys_cannot_shrink_or_drift(tmp_path):
    proto = _protocol()
    del proto["code_identity"]["src/lei_signal/rules/dual_ma.py"]
    with pytest.raises(ValueError, match="裁剪"):
        validate_b1_protocol(_write_protocol(tmp_path, proto), REPO)
    proto = _protocol()
    proto["code_identity"]["scripts/run_b1_dual_ma_description.py"] = "0" * 64
    with pytest.raises(ValueError, match="哈希不符"):
        validate_b1_protocol(_write_protocol(tmp_path, proto), REPO)
    proto = _protocol()
    proto["code_identity"]["src/lei_signal/extra.py"] = "0" * 64
    with pytest.raises(ValueError, match="未登记"):
        validate_b1_protocol(_write_protocol(tmp_path, proto), REPO)


def test_input_identity_cannot_repoint(tmp_path):
    proto = _protocol()
    proto["input_identity"]["prices_csv_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="input_identity"):
        validate_b1_protocol(_write_protocol(tmp_path, proto), REPO)


def test_card_and_taskbook_must_match(tmp_path):
    proto = _protocol()
    proto["candidate_card"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="candidate_card"):
        validate_b1_protocol(_write_protocol(tmp_path, proto), REPO)
    proto = _protocol()
    proto["task_book"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="task_book"):
        validate_b1_protocol(_write_protocol(tmp_path, proto), REPO)


def test_module_constants_match_real_package_on_disk():
    """模块固定身份必须等于真实 run-02 包当前文件（防真实包被替换后自证）。"""
    assert _sha(REAL_PACK / "manifest.json") == FIXED_INPUT_IDENTITY["manifest_sha256"]
    assert _sha(REAL_PACK / "prices.csv") == FIXED_INPUT_IDENTITY["prices_csv_sha256"]
    assert _sha(REAL_PACK / "calendar.json") == FIXED_INPUT_IDENTITY["calendar_sha256"]
    assert _sha(REAL_PACK / "fetch-manifest.json") == \
        FIXED_INPUT_IDENTITY["fetch_manifest_sha256"]


# ── 合成输入包构造与 load_verified_input 反例 ────────────────────────

def _make_package(base: Path, dates: list[str], closes: list[str] | None = None,
                  tamper: dict | None = None) -> dict:
    """合成临时包（结构同 run-02）；返回其 input_identity（单元测试内部用）。"""
    pack = base / "pack"
    (pack / "originals").mkdir(parents=True)
    closes = closes or ["1.000"] * len(dates)
    with (pack / "prices.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "open", "close", "high", "low", "volume"])
        for d, c in zip(dates, closes, strict=True):
            w.writerow([d, c, c, c, c, "1000.000"])
    cal = {"market": "CN", "months_requested": sorted({d[:7] for d in dates}),
           "months_failed": [],
           "days": {d: {"is_trading_day": True, "source_flag": "1",
                        "source_month": d[:7]} for d in dates}}
    (pack / "calendar.json").write_text(json.dumps(cal))
    originals = []
    for i in range(7):
        name = f"sh510300-{2013 + 2 * i}.json"
        (pack / "originals" / name).write_text(json.dumps({"i": i}))
        originals.append({"symbol": "sh510300", "file": name,
                          "sha256": _sha(pack / "originals" / name),
                          "retrieved_at": "2026-09-08T03:34:17.8+00:00"})
    (pack / "fetch-manifest.json").write_text(json.dumps(originals))
    quality = {"declarations": {**FIXED_DATA_DECLARATIONS,
                                "assembled_at": "2026-09-15T00:00:00+08:00",
                                "retrieved_at": "继承"}}
    (pack / "quality.json").write_text(json.dumps(quality))
    if tamper:
        for rel, content in tamper.items():
            (pack / rel).write_text(content)
    files = {str(f.relative_to(pack)) for f in pack.rglob("*") if f.is_file()}
    manifest = {"complete": True,
                "file_hashes": {rel: _sha(pack / rel) for rel in sorted(files)}}
    (pack / "manifest.json").write_text(json.dumps(manifest))
    return {"package": str(pack), "manifest_sha256": _sha(pack / "manifest.json"),
            "prices_csv_sha256": _sha(pack / "prices.csv"),
            "calendar_sha256": _sha(pack / "calendar.json"),
            "fetch_manifest_sha256": _sha(pack / "fetch-manifest.json")}


def _contract_for(identity: dict) -> dict:
    return {**FIXED_PARAMS, **FIXED_DATA_DECLARATIONS,
            "candidate_card": {"path": CARD_PATH, "sha256": CARD_SHA256},
            "input_identity": identity}


def test_synthetic_package_loads(tmp_path):
    dates = ["2020-01-02", "2020-01-03", "2020-01-06"]
    identity = _make_package(tmp_path, dates, ["1.0", "1.1", "1.2"])
    prices, schedule, audit = load_verified_input(identity["package"],
                                                  _contract_for(identity))
    assert list(prices["close"]) == [1.0, 1.1, 1.2]
    assert [d.strftime("%Y-%m-%d") for d in schedule["session"]] == dates
    assert all(ts.tzinfo is not None for ts in schedule["close_at"])
    assert audit["rows"] == 3 and audit["sessions"] == 3
    assert len(audit["retrieved_at"]) == 7
    assert all("+00:00" in v for v in audit["retrieved_at"].values())


def test_tampered_price_self_rewritten_manifest_rejected(tmp_path):
    dates = ["2020-01-02", "2020-01-03", "2020-01-06"]
    identity = _make_package(tmp_path, dates)
    pack = Path(identity["package"])
    # 篡改价格并重写自制 manifest 自证 → manifest 哈希必然脱离原固定身份
    with (pack / "prices.csv").open("a", newline="") as f:
        csv.writer(f).writerow(["2020-01-06", "9.9", "9.9", "9.9", "9.9", "1.0"])
    files = {str(f.relative_to(pack)) for f in pack.rglob("*") if f.is_file()}
    (pack / "manifest.json").write_text(json.dumps(
        {"complete": True, "file_hashes": {rel: _sha(pack / rel)
                                           for rel in sorted(files)}}))
    with pytest.raises(ValueError, match="manifest"):
        load_verified_input(str(pack), _contract_for(identity))


def test_calendar_missing_day_incomplete(tmp_path):
    dates = ["2020-01-02", "2020-01-03", "2020-01-06"]
    identity = _make_package(tmp_path, dates)
    pack = Path(identity["package"])
    cal = json.loads((pack / "calendar.json").read_text())
    cal["days"]["2020-01-07"] = {"is_trading_day": True, "source_flag": "1",
                                 "source_month": "2020-01"}
    cal["months_requested"] = sorted({d[:7] for d in cal["days"]})
    (pack / "calendar.json").write_text(json.dumps(cal))
    files = {str(f.relative_to(pack)) for f in pack.rglob("*")
             if f.is_file() and f.name != "manifest.json"}
    (pack / "manifest.json").write_text(json.dumps(
        {"complete": True, "file_hashes": {rel: _sha(pack / rel)
                                           for rel in sorted(files)}}))
    identity["calendar_sha256"] = _sha(pack / "calendar.json")
    identity["manifest_sha256"] = _sha(pack / "manifest.json")
    with pytest.raises(B1IncompleteError, match="缺交易日"):
        load_verified_input(str(pack), _contract_for(identity))


def test_bad_price_rows_rejected(tmp_path):
    dates = ["2020-01-02", "2020-01-03"]
    for bad in ("0", "-1.0", "NaN", "garbage"):
        identity = _make_package(tmp_path / bad.replace(".", "_"),
                                 dates, ["1.0", bad])
        with pytest.raises(ValueError):
            load_verified_input(identity["package"], _contract_for(identity))


def test_duplicate_and_unsorted_dates_rejected(tmp_path):
    identity = _make_package(tmp_path / "dup",
                             ["2020-01-02", "2020-01-02"], ["1.0", "1.1"])
    with pytest.raises(ValueError, match="重复"):
        load_verified_input(identity["package"], _contract_for(identity))
    identity = _make_package(tmp_path / "unsorted",
                             ["2020-01-06", "2020-01-02"], ["1.0", "1.1"])
    with pytest.raises(ValueError, match="乱序"):
        load_verified_input(identity["package"], _contract_for(identity))


def test_wrong_header_and_empty_package_rejected(tmp_path):
    identity = _make_package(
        tmp_path / "hdr", ["2020-01-02"],
        tamper={"prices.csv": "date,close\n2020-01-02,1.0\n"})
    # 篡改后 manifest 已失真，先修 manifest 使其自洽（绕过manifest层，专测列头）
    pack = Path(identity["package"])
    files = {str(f.relative_to(pack)) for f in pack.rglob("*")
             if f.is_file() and f.name != "manifest.json"}
    (pack / "manifest.json").write_text(json.dumps(
        {"complete": True, "file_hashes": {rel: _sha(pack / rel)
                                           for rel in sorted(files)}}))
    identity["prices_csv_sha256"] = _sha(pack / "prices.csv")
    identity["manifest_sha256"] = _sha(pack / "manifest.json")
    with pytest.raises(ValueError, match="列头"):
        load_verified_input(str(pack), _contract_for(identity))
    with pytest.raises(ValueError, match="不存在|缺 manifest"):
        load_verified_input(str(tmp_path / "empty-dir"), _contract_for(identity))
