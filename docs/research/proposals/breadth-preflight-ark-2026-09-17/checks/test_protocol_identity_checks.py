"""R1 返修补件：协议身份合成反例（2026-09-18，S1 execution=2）。

按主控复核 R1（docs/experiments/breadth-preflight-controller-review-2026-09-18.md）：
任务书要求「删必需身份键」的合成反例。本文件用临时合成协议文档直接调用
合同模块的校验函数（不跑完整 CLI、不读真实数据内容、不读冻结协议原件，
协议文件全部写在 pytest 临时目录）。每例断言**实际到达的校验分支与错误
文本**，不允许更早的无关拒绝冒充通过；先有合法正例证明链路可用。

独立性：期望（哪个键必须存在、改成什么必须被拒）来自合同
2026-09-17-breadth-first-description-execution.md §Task 2 的身份要求清单，
不从实现输出抄取。
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[5]
_SRC = REPO / "src"
if not (_SRC / "lei_signal" / "research" / "breadth_description_contract.py").is_file():
    raise RuntimeError(f"repo path guard failed: computed REPO={REPO}")
sys.path.insert(0, str(_SRC))

from lei_signal.research.breadth_description_contract import (  # noqa: E402
    compute_import_closure,
    protocol_document,
    validate_protocol,
    verify_code_manifest,
)

CLI = (REPO / "docs/experiments/raw/breadth-b200-first-description-2026-09-17"
       / "run_breadth.py")


def _write_protocol(tmp_path, doc) -> Path:
    """合同要求的版本原件位置（…/freeze/v1.0.0/protocol-v1.0.0.json），临时目录内。"""
    freeze = tmp_path / "freeze" / "v1.0.0"
    freeze.mkdir(parents=True, exist_ok=True)
    path = freeze / "protocol-v1.0.0.json"
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def good_doc_and_path(tmp_path_factory):
    """合法合成分支协议：合成代码引用（64 位假哈希），临时合成路径。"""
    doc = protocol_document(
        code={"src/lei_signal/research/breadth_description.py": "a" * 64},
        mode="synthetic_test",
    )
    path = _write_protocol(tmp_path_factory.mktemp("proto"), doc)
    return doc, path


def test_valid_synthetic_protocol_passes(good_doc_and_path, tmp_path):
    # 正例：合法文档必须零错误——证明后续反例的拒绝来自对应校验，而非一律拒绝。
    doc, path = good_doc_and_path
    assert validate_protocol(doc, mode="synthetic_test", protocol_path=path) == []


def test_delete_required_identity_key_object_rejected(good_doc_and_path, tmp_path):
    doc, path = good_doc_and_path
    bad = copy.deepcopy(doc)
    del bad["object"]  # 删必需身份键：对象卡引用
    errors = validate_protocol(bad, mode="synthetic_test", protocol_path=path)
    assert any("protocol object != frozen identity" in e for e in errors), errors


def test_delete_required_identity_key_family_rejected(good_doc_and_path, tmp_path):
    doc, path = good_doc_and_path
    bad = copy.deepcopy(doc)
    del bad["family"]  # 删必需身份键：研究家族
    errors = validate_protocol(bad, mode="synthetic_test", protocol_path=path)
    assert any("protocol family != frozen identity" in e for e in errors), errors


def test_alter_object_reference_rejected(good_doc_and_path, tmp_path):
    doc, path = good_doc_and_path
    bad = copy.deepcopy(doc)
    bad["object"] = dict(bad["object"], reference="breadth.csi300.b50.common@1.0.0")
    errors = validate_protocol(bad, mode="synthetic_test", protocol_path=path)
    assert any("protocol object != frozen identity" in e for e in errors), errors


def test_alter_use_rejected(good_doc_and_path, tmp_path):
    doc, path = good_doc_and_path
    bad = copy.deepcopy(doc)
    bad["use"] = "prediction"  # 改用途：受限事后描述 → 预测，必须被拒
    errors = validate_protocol(bad, mode="synthetic_test", protocol_path=path)
    assert any("protocol use != frozen identity" in e for e in errors), errors


def test_delete_spec_entry_rejected(good_doc_and_path):
    doc, _ = good_doc_and_path
    bad = copy.deepcopy(doc)
    del bad["specs"]["definitions.v1.json"]  # 删必需规范键
    errors = validate_protocol(bad, mode="synthetic_test", protocol_path=Path("x"))
    assert any("missing or altered spec hash: definitions.v1.json" in e
               for e in errors), errors


def test_alter_spec_hash_rejected(good_doc_and_path):
    doc, _ = good_doc_and_path
    bad = copy.deepcopy(doc)
    bad["specs"]["definitions.v1.json"]["sha256"] = "0" * 64
    errors = validate_protocol(bad, mode="synthetic_test", protocol_path=Path("x"))
    assert any("missing or altered spec hash: definitions.v1.json" in e
               for e in errors), errors


def test_synthetic_inputs_without_fixture_declaration_rejected(good_doc_and_path):
    doc, _ = good_doc_and_path
    bad = copy.deepcopy(doc)
    bad["inputs"] = {"mode": "real_data"}  # 合成分支必须声明 synthetic_fixtures
    errors = validate_protocol(bad, mode="synthetic_test", protocol_path=Path("x"))
    assert any("synthetic protocol must declare inputs.mode=synthetic_fixtures" in e
               for e in errors), errors


def test_code_entry_not_sha256_rejected(good_doc_and_path):
    doc, _ = good_doc_and_path
    bad = copy.deepcopy(doc)
    key = next(iter(bad["code"]))
    bad["code"][key] = "z" * 63  # 非 sha256 长度
    errors = validate_protocol(bad, mode="synthetic_test", protocol_path=Path("x"))
    assert any(f"code entry not a sha256: {key}" in e for e in errors), errors


def test_mode_mismatch_rejected(good_doc_and_path):
    doc, path = good_doc_and_path
    # 请求 restricted_historical 但文档是 synthetic_test：到达 mode 一致性校验。
    errors = validate_protocol(doc, mode="restricted_historical", protocol_path=path)
    assert any("protocol mode 'synthetic_test' != requested 'restricted_historical'" in e
               for e in errors), errors


def test_pointer_file_cannot_act_as_protocol(good_doc_and_path, tmp_path):
    doc, _ = good_doc_and_path
    pointer = tmp_path / "current-protocol.json"  # 不在 freeze/v1.0.0/ 原件位置
    pointer.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    errors = validate_protocol(doc, mode="synthetic_test", protocol_path=pointer)
    assert any("protocol file must be a version original" in e for e in errors), errors


def test_code_manifest_missing_actual_key_rejected():
    # 双向核对之一：实际闭包有、协议未声明 → missing required code key。
    real = compute_import_closure(CLI)
    probe = sorted(real)[0]
    errors = verify_code_manifest({probe: real[probe]}, {})
    assert errors == [f"missing required code key: {probe}"], errors


def test_code_manifest_hash_drift_rejected_both_directions():
    # 双向核对之二：同一声明键，实际哈希与声明哈希不同 → 两个方向都报错
    # （实际→声明方向 "code hash mismatch"；声明→磁盘方向 "declared code file drifted"）。
    real = compute_import_closure(CLI)
    probe = sorted(real)[0]
    errors = verify_code_manifest({probe: real[probe]}, {probe: "0" * 64})
    assert any(f"code hash mismatch: {probe}" in e for e in errors), errors
    assert any(f"declared code file drifted: {probe}" in e for e in errors), errors


def test_code_manifest_declared_missing_file_rejected():
    # 双向核对之三：声明了一个仓库中不存在的文件 → declared code file missing。
    errors = verify_code_manifest({}, {"no/such/file.py": "0" * 64})
    assert errors == ["declared code file missing: no/such/file.py"], errors
