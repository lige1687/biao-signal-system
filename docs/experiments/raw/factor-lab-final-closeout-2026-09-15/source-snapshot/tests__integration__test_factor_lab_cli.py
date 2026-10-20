"""factor_lab CLI 集成测试：从正式协议经 CLI 调用真实函数，不 mock 资格判断。

不联网、不加载 API 服务、不读真实交易数据库；正式输出目录只写在 pytest 临时目录。
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "docs/experiments/raw/factor-research-workbench-v1-2026-09-14"
REPAIR_RAW = REPO / "docs/experiments/raw/factor-lab-concentrated-repair-2026-09-14"
PROTOCOLS = sorted(REPAIR_RAW.glob("protocol-*.json"))
CLI = REPO / "scripts/run_factor_lab.py"


def run_cli(protocol: Path, out: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), "--protocol", str(protocol), "--out", str(out)],
        capture_output=True, text=True, cwd=REPO,
    )


def mirror_repair_raw(tmp_path: Path) -> Path:
    """在临时目录镜像返修raw与其引用的同级输入目录（相对路径保持有效）。"""
    base = tmp_path / "mirror" / "docs" / "experiments" / "raw"
    shutil.copytree(REPAIR_RAW, base / REPAIR_RAW.name,
                    ignore=shutil.ignore_patterns("runs", "__pycache__",
                                                  "reproduce-output"))
    shutil.copytree(RAW / "synthetic_inputs",
                    base / RAW.name / "synthetic_inputs")
    shutil.copy2(RAW / "independent-expectations.json",
                 base / RAW.name / "independent-expectations.json")
    return base / REPAIR_RAW.name


@pytest.mark.parametrize("protocol", PROTOCOLS, ids=lambda p: p.name)
def test_formal_protocol_exits_zero(protocol: Path, tmp_path: Path):
    out = tmp_path / f"run-{protocol.stem}"
    result = run_cli(protocol, out)
    assert result.returncode == 0, result.stderr + "\n" + (out / "run.log").read_text()
    # 产物合同
    for name in ("manifest.json", "quality.json", "run.log", "summary.md"):
        assert (out / name).is_file(), name
    quality = json.loads((out / "quality.json").read_text())
    assert quality["all_passed"] is True
    assert all(check["passed"] for check in quality["checks"])
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["synthetic"] is True
    assert manifest["production_authorization"] == "not_authorized"
    summary = (out / "summary.md").read_text()
    assert "合成算法验证" in summary
    assert "非真实收益/有效性证据" in summary


def test_refuses_existing_output_dir(tmp_path: Path):
    out = tmp_path / "already-exists"
    out.mkdir()
    result = run_cli(PROTOCOLS[0], out)
    assert result.returncode == 3


def test_refuses_tampered_input_hash(tmp_path: Path):
    # 复制输入并篡改一行 → 协议哈希不符 → 退出3，不产出任何研究结论
    raw_copy = tmp_path / "raw"
    shutil.copytree(RAW, raw_copy,
                    ignore=shutil.ignore_patterns("runs", "__pycache__"))
    prices = raw_copy / "synthetic_inputs/numerical_prices_3.csv"
    lines = prices.read_text().splitlines()
    lines[-1] = lines[-1].rsplit(",", 1)[0] + ",999.0"
    prices.write_text("\n".join(lines) + "\n")
    out = tmp_path / "run-tampered"
    result = run_cli(raw_copy / "protocol-1-numerical.json", out)
    assert result.returncode == 3
    assert "hash mismatch" in result.stderr


def test_refuses_naive_evaluation_cutoff(tmp_path: Path):
    raw_copy = mirror_repair_raw(tmp_path)
    protocol = json.loads((raw_copy / "protocol-1-numerical.json").read_text())
    protocol["evaluation_cutoff"] = "2030-01-01 15:00:00"
    protocol_path = raw_copy / "protocol-naive.json"
    protocol_path.write_text(json.dumps(protocol, ensure_ascii=False, indent=2))
    out = tmp_path / "run-naive"
    result = run_cli(protocol_path, out)
    assert result.returncode == 3
    assert "timezone-aware" in result.stderr


def test_refuses_current_pointer(tmp_path: Path):
    protocol = json.loads(PROTOCOLS[0].read_text())
    protocol["current"] = "protocol-1-numerical.json"
    protocol_path = tmp_path / "protocol-current.json"
    protocol_path.write_text(json.dumps(protocol, ensure_ascii=False, indent=2))
    out = tmp_path / "run-current"
    result = run_cli(protocol_path, out)
    assert result.returncode == 3
    assert "current" in result.stderr


class TestFrozenContractR2R4:
    """集中返修 R2/R4：运行前核对冻结合同；验收证据不可空转。"""

    def _copy_raw(self, tmp_path: Path) -> Path:
        return mirror_repair_raw(tmp_path)

    def _load_protocol1(self, raw_copy: Path) -> dict:
        return json.loads((raw_copy / "protocol-1-numerical.json").read_text())

    def test_empty_expectations_rejected(self, tmp_path):
        raw_copy = self._copy_raw(tmp_path)
        protocol = self._load_protocol1(raw_copy)
        protocol["expectations"] = {}
        (raw_copy / "protocol-empty.json").write_text(json.dumps(protocol, ensure_ascii=False))
        assert run_cli(raw_copy / "protocol-empty.json", tmp_path / "out").returncode == 3

    def test_required_check_deletion_rejected(self, tmp_path):
        raw_copy = self._copy_raw(tmp_path)
        protocol = self._load_protocol1(raw_copy)
        removed = protocol["required_checks"][0]
        del protocol["expectations"][removed]
        (raw_copy / "protocol-del.json").write_text(json.dumps(protocol, ensure_ascii=False))
        assert run_cli(raw_copy / "protocol-del.json", tmp_path / "out").returncode == 3

    def test_illegal_tolerance_rejected(self, tmp_path):
        raw_copy = self._copy_raw(tmp_path)
        protocol = self._load_protocol1(raw_copy)
        protocol["expectation_tolerance_abs"] = 0.5
        (raw_copy / "protocol-tol.json").write_text(json.dumps(protocol, ensure_ascii=False))
        assert run_cli(raw_copy / "protocol-tol.json", tmp_path / "out").returncode == 3

    def test_missing_required_code_key_rejected(self, tmp_path):
        raw_copy = self._copy_raw(tmp_path)
        protocol = self._load_protocol1(raw_copy)
        del protocol["code_identity"]["scripts/run_factor_lab.py"]
        (raw_copy / "protocol-code.json").write_text(json.dumps(protocol, ensure_ascii=False))
        assert run_cli(raw_copy / "protocol-code.json", tmp_path / "out").returncode == 3

    def test_wrong_code_hash_rejected(self, tmp_path):
        raw_copy = self._copy_raw(tmp_path)
        protocol = self._load_protocol1(raw_copy)
        protocol["code_identity"]["scripts/run_factor_lab.py"] = "0" * 64
        (raw_copy / "protocol-hash.json").write_text(json.dumps(protocol, ensure_ascii=False))
        assert run_cli(raw_copy / "protocol-hash.json", tmp_path / "out").returncode == 3

    def test_wrong_target_offsets_rejected(self, tmp_path):
        raw_copy = self._copy_raw(tmp_path)
        protocol = self._load_protocol1(raw_copy)
        protocol["targets"]["entry_offset"] = 10
        (raw_copy / "protocol-tgt.json").write_text(json.dumps(protocol, ensure_ascii=False))
        assert run_cli(raw_copy / "protocol-tgt.json", tmp_path / "out").returncode == 3

    def test_wrong_registry_version_rejected(self, tmp_path):
        raw_copy = self._copy_raw(tmp_path)
        protocol = self._load_protocol1(raw_copy)
        protocol["registry"]["version"] = "9.9.9"
        (raw_copy / "protocol-reg.json").write_text(json.dumps(protocol, ensure_ascii=False))
        assert run_cli(raw_copy / "protocol-reg.json", tmp_path / "out").returncode == 3

    def test_changed_card_fingerprint_rejected(self, tmp_path):
        raw_copy = self._copy_raw(tmp_path)
        protocol = self._load_protocol1(raw_copy)
        ref = next(iter(protocol["definition_cards_sha256"]))
        protocol["definition_cards_sha256"][ref] = "1" * 64
        (raw_copy / "protocol-card.json").write_text(json.dumps(protocol, ensure_ascii=False))
        assert run_cli(raw_copy / "protocol-card.json", tmp_path / "out").returncode == 3

    def test_insufficient_data_exits_2_with_reasons(self, tmp_path):
        # 真实缺数据输入：价格只剩10行 → 目标全部无法成熟 → 退出2，不是模拟异常
        raw_copy = self._copy_raw(tmp_path)
        import hashlib
        inputs_dir = (raw_copy.parent / RAW.name / "synthetic_inputs")
        short = inputs_dir / "numerical_prices_3.csv"
        lines = short.read_text().splitlines()
        short.write_text("\n".join([lines[0]] + lines[1:11]) + "\n")
        protocol = self._load_protocol1(raw_copy)
        for _name, spec in protocol["inputs"].items():
            path = raw_copy / spec["path"]
            if path.name == "numerical_prices_3.csv":
                spec["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        (raw_copy / "protocol-short.json").write_text(json.dumps(protocol, ensure_ascii=False))
        result = run_cli(raw_copy / "protocol-short.json", tmp_path / "out-short")
        assert result.returncode == 2
        log = (tmp_path / "out-short" / "run.log").read_text()
        assert "INSUFFICIENT" in log

    def test_values_sidecar_metadata_saved(self, tmp_path):
        raw_copy = self._copy_raw(tmp_path)
        out = tmp_path / "out-meta"
        assert run_cli(raw_copy / "protocol-1-numerical.json", out).returncode == 0
        meta = json.loads((out / "values_mom3.meta.json").read_text())
        assert meta["metadata"]["reference"] == "mixed.momentum.raw@1.0.0"
        assert meta["findings"]
        assert meta["declared_inputs"]["prices_3"]["sha256"]

    def test_protocol_byte_copy_and_dual_sha(self, tmp_path):
        raw_copy = self._copy_raw(tmp_path)
        out = tmp_path / "out-copy"
        assert run_cli(raw_copy / "protocol-1-numerical.json", out).returncode == 0
        source = (raw_copy / "protocol-1-numerical.json").read_bytes()
        assert (out / "protocol.source.json").read_bytes() == source
        manifest = json.loads((out / "manifest.json").read_text())
        import hashlib
        assert manifest["protocol"]["file_sha256"] == hashlib.sha256(source).hexdigest()
        assert manifest["protocol"]["canonical_sha256"]
        assert manifest["protocol"]["file_sha256"] != manifest["protocol"]["canonical_sha256"]

    def test_write_failure_leaves_no_completed_manifest(self, tmp_path, monkeypatch):
        # 写盘故障注入必须发生在被测进程内（子进程不受 monkeypatch 影响）
        raw_copy = self._copy_raw(tmp_path)
        out = tmp_path / "out-fail"
        import lei_signal.research.factor_lab.runner as runner_mod

        def broken_write(*args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(runner_mod, "_write_manifest", broken_write)
        code = runner_mod.run_protocol(raw_copy / "protocol-1-numerical.json", out)
        assert code == 1
        assert not (out / "manifest.json").exists()
        assert "WRITE_FAILURE" in (out / "run.log").read_text()
