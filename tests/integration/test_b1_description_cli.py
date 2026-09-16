"""run_b1_dual_ma_description CLI 集成测试（负路由与故障注入）。

正式正路（合法协议+固定真实输入→真实状态/目标计算）由预算内的正式运行
run-01 覆盖并单独核验，本文件不触发——协议把 input_identity 绑定到模块常量，
任何指向合成临时包的协议都会被拒绝（这本身是被测行为），因此本文件不会
意外消耗真实计算预算。只用合成临时文件，不篡改真实旧包做反例。
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

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
)

REPO = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
CLI = REPO / "scripts/run_b1_dual_ma_description.py"
TMP = Path("/tmp/b1_cli_test")


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


def run_cli(proto: dict, name: str, out=None, make_out_parent_readonly=False):
    import shutil
    shutil.rmtree(TMP, ignore_errors=True)
    sub = TMP / name
    sub.mkdir(parents=True)
    cp = sub / f"protocol-v{SPEC_VERSION}.json"
    cp.write_text(json.dumps(proto, ensure_ascii=False))
    out = out or TMP / f"{name}-out"
    if make_out_parent_readonly:
        ro = TMP / "readonly"
        ro.mkdir()
        os.chmod(ro, 0o500)
        out = ro / "out"
    proc = subprocess.run(["python3", str(CLI), "--protocol", str(cp),
                           "--out", str(out)], capture_output=True, text=True)
    if make_out_parent_readonly:
        os.chmod(TMP / "readonly", 0o700)
    return proc, out


def test_draft_protocol_exit3_no_outputs():
    proto = _protocol(spec_status="draft_pending_controller_freeze")
    proc, out = run_cli(proto, "draft")
    assert proc.returncode == 3
    assert not out.exists()  # 协议拒绝在任何真实计算/写盘之前


def test_deleted_code_key_exit3_no_outputs():
    proto = _protocol()
    del proto["code_identity"]["src/lei_signal/rules/lei_color.py"]
    proc, out = run_cli(proto, "del-key")
    assert proc.returncode == 3
    assert "裁剪" in proc.stderr
    assert not out.exists()


def test_tampered_cli_hash_exit3_no_state_files():
    proto = _protocol()
    proto["code_identity"]["scripts/run_b1_dual_ma_description.py"] = "0" * 64
    proc, out = run_cli(proto, "bad-cli-hash")
    assert proc.returncode == 3
    assert "哈希不符" in proc.stderr
    assert not out.exists()
    assert not (TMP / "bad-cli-hash-out" / "states.csv").exists()


def test_synthetic_package_protocol_rejected():
    # 指向任意合成临时包的协议：input_identity 与模块常量不符 → 拒绝
    proto = _protocol()
    proto["input_identity"] = dict(FIXED_INPUT_IDENTITY, manifest_sha256="0" * 64)
    proc, out = run_cli(proto, "fake-identity")
    assert proc.returncode == 3
    assert not out.exists()


def test_existing_out_dir_refused_no_overwrite():
    import shutil
    shutil.rmtree(TMP, ignore_errors=True)
    (TMP / "occupied").mkdir(parents=True)
    (TMP / "occupied" / "keep.txt").write_text("sentinel")
    cp = TMP / "p.json"
    cp.write_text(json.dumps(_protocol()))
    proc = subprocess.run(["python3", str(CLI), "--protocol", str(cp),
                           "--out", str(TMP / "occupied")],
                          capture_output=True, text=True)
    assert proc.returncode == 3
    assert (TMP / "occupied" / "keep.txt").read_text() == "sentinel"  # 未覆盖


def test_write_failure_no_completed_manifest():
    proto = _protocol()
    proc, out = run_cli(proto, "wf", make_out_parent_readonly=True)
    assert proc.returncode == 3
    # 写盘失败：目录未建成或绝无 completed=true 的 manifest
    if out.exists() and (out / "manifest.json").is_file():
        manifest = json.loads((out / "manifest.json").read_text())
        assert manifest.get("package_completed") is not True


def test_forged_synthetic_identity_rejected():
    proto = _protocol(data_mode="synthetic")
    proc, _ = run_cli(proto, "fake-synthetic")
    assert proc.returncode == 3


# ── 中途写盘故障注入（纯合成、进程内；1批3案例，事先列明） ─────────────
# 案例A：第1次写（protocol.source.json）失败 → 不得存在 manifest；
# 案例B：写到 states.csv 失败（此前已写多份文件）→ 不得存在 manifest；
# 案例C：最终 manifest 第二次写失败 → 只能留下 package_completed=False 的
#        manifest，绝不留 completed=true。全程合成数据，不运行真实输入计算。

def _cli_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location("b1_cli", CLI)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _synthetic_payload():
    import pandas as pd
    group = {"n": 1, "mean": 0.01, "median": 0.01, "up_ratio": 1.0,
             "aux_n": 1, "aux_mean": -0.01, "aux_worst": -0.01}
    sym = {"true_group": group, "false_group": group,
           "state_segments": {"true_segments": 1, "false_segments": 1,
                              "longest_true": 1, "longest_false": 1},
           "sparse_view": {"anchor_session": "2019-10-08", "step": 23,
                           "groups": {"true": {"n": 1, "up": 1, "down": 0,
                                               "zero": 0},
                                      "false": {"n": 1, "up": 0, "down": 1,
                                                "zero": 0}}}}
    rec = {"observations_in_eval_window": 1, "state_true": 1, "state_false": 0,
           "state_unknown": 0, "warmup_sessions_before_window": 20,
           "comparison_n": 1, "comparison_true": 1, "comparison_false": 0,
           "true_plus_false_equals_comparison": True,
           "primary_exclusion_counts": {}}
    result = {"states": pd.DataFrame({"date": ["2020-01-02"], "close": [1.0],
                                      "state": ["true"], "missing_reason": [""]}),
              "observations": pd.DataFrame({"session": ["2020-01-02"],
                                            "state": ["true"], "main": [0.01]}),
              "summary": {"symbols": {"510300": sym}},
              "quality": {"reconciliation": rec,
                          "result_identity": "post_hoc_historical_description",
                          "no_claims": []}}
    contract = {"object_ref": "candidate:lei.dual_ma.bull_state@draft-1",
                "candidate_card": {"path": CARD_PATH, "sha256": CARD_SHA256},
                "input_identity": dict(FIXED_INPUT_IDENTITY),
                "family": "B1-dual-ma-unit",
                "use": "post_hoc_historical_description",
                "symbol": "510300",
                "evaluation_window": {"start": "2019-10-08", "end": "2025-12-31"}}
    return result, contract


def test_mid_write_failure_never_completed_true(tmp_path):
    import shutil
    from datetime import datetime, timedelta, timezone
    from unittest import mock

    mod = _cli_module()
    result, contract = _synthetic_payload()
    now = datetime.now(timezone(timedelta(hours=8)))
    proto = tmp_path / "protocol.source.json"
    proto.write_text("{}")
    real_text, real_to_csv = Path.write_text, type(result["states"]).to_csv

    def run_case(name, fail_predicate):
        out = tmp_path / name
        out.mkdir()
        real_bytes = Path.write_bytes
        with mock.patch.object(Path, "write_text", autospec=True) as w_text, \
                mock.patch.object(Path, "write_bytes", autospec=True) as w_bytes, \
                mock.patch.object(type(result["states"]), "to_csv",
                                  autospec=True) as w_csv:
            w_text.side_effect = lambda self, *a, **k: (
                (_ for _ in ()).throw(OSError(f"injected:{self.name}"))
                if fail_predicate(self) else real_text(self, *a, **k))
            w_bytes.side_effect = lambda self, *a, **k: (
                (_ for _ in ()).throw(OSError(f"injected:{self.name}"))
                if fail_predicate(self) else real_bytes(self, *a, **k))
            w_csv.side_effect = lambda self, p, *a, **k: (
                (_ for _ in ()).throw(OSError(f"injected:{Path(p).name}"))
                if fail_predicate(Path(p)) else real_to_csv(self, p, *a, **k))
            import contextlib
            with contextlib.suppress(OSError):
                mod.write_outputs(out, contract, result, {"rows": 1}, proto,
                                  now, True)
        manifest = out / "manifest.json"
        if manifest.is_file():
            payload = json.loads(manifest.read_text())
            assert payload.get("package_completed") is not True
        return out

    # 案例A：第一次写即失败 → 无 manifest
    a = run_case("case-a", lambda p: p.name == "protocol.source.json")
    assert not (a / "manifest.json").exists()
    # 案例B：写 states.csv 失败（此前已有多份文件）→ 无 manifest
    b = run_case("case-b", lambda p: p.name == "states.csv")
    assert not (b / "manifest.json").exists()
    assert (b / "protocol.source.json").exists()  # 部分文件已写但不置完成
    # 案例C：最终 manifest 定稿写失败 → 仅存 completed=False 的首版 manifest
    state = {"manifest_writes": 0}

    def fail_second_manifest(p):
        if p.name == "manifest.json":
            state["manifest_writes"] += 1
            return state["manifest_writes"] >= 2
        return False
    c = run_case("case-c", fail_second_manifest)
    manifest = json.loads((c / "manifest.json").read_text())
    assert manifest["package_completed"] is False
    assert manifest["exit_code"] is None
    shutil.rmtree(TMP, ignore_errors=True)
