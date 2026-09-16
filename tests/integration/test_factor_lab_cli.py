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
CLOSEOUT_RAW = REPO / "docs/experiments/raw/factor-lab-final-closeout-2026-09-15"
PROTOCOLS = sorted(CLOSEOUT_RAW.glob("protocol-*.json"))
CLI = REPO / "scripts/run_factor_lab.py"


def run_cli(protocol: Path, out: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), "--protocol", str(protocol), "--out", str(out)],
        capture_output=True, text=True, cwd=REPO,
    )


def mirror_repair_raw(tmp_path: Path) -> Path:
    """在临时目录镜像终版raw与其引用的同级输入目录（相对路径保持有效）。"""
    base = tmp_path / "mirror" / "docs" / "experiments" / "raw"
    shutil.copytree(CLOSEOUT_RAW, base / CLOSEOUT_RAW.name,
                    ignore=shutil.ignore_patterns("runs", "__pycache__",
                                                  "reproduce-output",
                                                  "source-snapshot"))
    shutil.copytree(RAW / "synthetic_inputs",
                    base / RAW.name / "synthetic_inputs")
    return base / CLOSEOUT_RAW.name


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
        removed = sorted(protocol["expectations"])[0]
        del protocol["expectations"][removed]
        (raw_copy / "protocol-del.json").write_text(json.dumps(protocol, ensure_ascii=False))
        assert run_cli(raw_copy / "protocol-del.json", tmp_path / "out").returncode == 3
        protocol2 = self._load_protocol1(raw_copy)
        protocol2["required_checks"] = sorted(protocol2["expectations"])
        (raw_copy / "protocol-rc.json").write_text(json.dumps(protocol2, ensure_ascii=False))
        assert run_cli(raw_copy / "protocol-rc.json", tmp_path / "out2").returncode == 3

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


class TestS2S4FinalCloseout:
    """最后一轮 S2/S4：必查集合来自独立期望产物；JSON 严格可解析。"""

    def test_s2_reduced_checks_rejected_at_contract_verification(self, tmp_path):
        # 主控反例：required_checks与expectations同删到1项必须被拒；
        # 另测改单项期望、多项期望也被拒；含required_checks键即拒。
        import copy

        from lei_signal.research.factor_lab import runner as runner_mod
        raw_copy = mirror_repair_raw(tmp_path)
        protocol = json.loads(
            (raw_copy / "protocol-1-numerical.json").read_text())

        def attempt(mutate):
            reduced = copy.deepcopy(protocol)
            mutate(reduced)
            try:
                runner_mod.verify_frozen_contract(reduced, REPO, raw_copy)
            except runner_mod.IdentityFormatError:
                return True
            return False

        def reduce_both(p):
            keep = sorted(p["expectations"])[0]
            p["required_checks"] = [keep]
            p["expectations"] = {keep: p["expectations"][keep]}

        def drop_one(p):
            p["expectations"].pop(sorted(p["expectations"])[0])

        def change_one(p):
            key = sorted(p["expectations"])[0]
            p["expectations"][key] = "<<tampered>>"

        assert attempt(reduce_both), "同删必须拒绝"
        assert attempt(drop_one), "缺项必须拒绝"
        assert attempt(change_one), "改值必须拒绝"
        with_required = copy.deepcopy(protocol)
        with_required["required_checks"] = sorted(protocol["expectations"])
        assert attempt(lambda p: p.update(required_checks=with_required.pop(
            "required_checks"))), "协议携带required_checks必须拒绝"

    def test_s4_dump_json_strict_roundtrip(self):
        import json as json_mod

        from lei_signal.research.factor_lab import runner as runner_mod
        payload = {"value": float("nan"), "inf": float("inf"),
                   "ninf": float("-inf"), "nested": [{"x": float("nan")}],
                   "ok": 1.5, "name": "合成"}
        text, warnings = runner_mod._dump_json(payload)
        parsed = json_mod.loads(text)  # 标准读回，不允许注释/Extra data
        assert parsed["ok"] == 1.5
        assert parsed["name"] == "合成"
        assert parsed["value"] is None and parsed["inf"] is None
        assert len(warnings) == 4
        text2, warnings2 = runner_mod._dump_json({"a": 1.0})
        json_mod.loads(text2)
        assert warnings2 == []
