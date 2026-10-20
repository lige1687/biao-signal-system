#!/usr/bin/env python3
"""步骤1：复现主控复核 v1.3.0 §11.3/§11.4 的反例（返修前留失败证据）。

只读真实证据包（内存副本上篡改，原文件不动）；R2 用合成夹具走正式
prepare CLI。输出 summary JSON 到本目录 counterexamples-run-01/。
不联网、不覆盖任何旧产物。
"""
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
sys.path.insert(0, str(ROOT / "src"))
sys.dont_write_bytecode = True

_RUN = sys.argv[1] if len(sys.argv) > 1 else "counterexamples-run-01"
_BUNDLE = (sys.argv[2] if len(sys.argv) > 2 else
           "docs/experiments/raw/research-fixed-etf-evidence-integration"
           "-2026-09-13/evidence-bundle.json")
from lei_signal.research.qualification_bundle import (  # noqa: E402
    listing_evidence_from_validated,
    validate_evidence_bundle,
)

OUT = ROOT / ("docs/experiments/raw/research-fixed-etf-evidence-integration"
              "-2026-09-13/rework-r123") / _RUN
OUT.mkdir(parents=True, exist_ok=False)  # 排他：同号重跑即失败

BUNDLE = json.loads((ROOT / _BUNDLE).read_text(encoding="utf-8"))
UNIVERSE = {"159652.SZ", "510300.SS", "512400.SS", "512890.SS", "513870.SS",
            "515050.SS", "515130.SS", "515170.SS", "515300.SS", "515880.SS",
            "516220.SS", "518850.SS", "562590.SS", "588000.SS"}

results: dict[str, dict] = {}


EXPECT_515050 = "515050-listing-announcement"
EXPECT_MO7U = "515300-515300_20231214_MO7U"
EXPECT_512890 = "512890-official-split"
# 每例的通过判据：对照=515050 已核且桥接；篡改例=被拒/不入桥接
CASES = {
    "R1-0-control": lambda v, b: EXPECT_515050 in v and "515050.SS" in b,
    "R1-1-listing-date-tampered": lambda v, b: EXPECT_515050 not in v
    and "515050.SS" not in b,
    "R1-2-listing-without-bridge-purpose": lambda v, b: EXPECT_515050 in v
    and "515050.SS" not in b,
    "R1-3-amounts-string-nan": lambda v, b: EXPECT_MO7U not in v,
    "R1-4-inverted-time-range": lambda v, b: EXPECT_512890 not in v,
    "R1-5-referenced-pdf-hash-zeros": lambda v, b: EXPECT_MO7U not in v,
}


def check(name, validated_ids, bridge_syms):
    """按各例期望判定：反例必须被拒/不入桥接，对照必须继续通过。"""
    ok = CASES[name](set(validated_ids), set(bridge_syms))
    results[name] = {
        "validated_ids": sorted(validated_ids),
        "bridge_products": sorted(bridge_syms),
        "expectation_met": ok,
        "note": ("对照（应通过）" if name.endswith("control")
                 else ("反例已按预期拒绝/排除" if ok else "反例仍被接受——缺陷在")),
    }


def run_case(name, mutate):
    bundle = copy.deepcopy(BUNDLE)
    mutate(bundle)
    res = validate_evidence_bundle(bundle, root=ROOT, universe=UNIVERSE)
    validated_ids = {r["record_id"] for r in res["validated"]}
    rejected_ids = {r["record_id"]: r["reasons"] for r in res["rejected"]}
    bridge_syms: set[str] = set()
    listing = [r for r in res["validated"] if r["fact_type"] == "listing"]
    if listing:
        with tempfile.TemporaryDirectory() as td:
            mapping, bridge_report = listing_evidence_from_validated(
                listing, out_dir=Path(td) / "b")
            bridge_syms = set(mapping)
            results.setdefault("_bridge_report", {})[name] = bridge_report
    check(name, validated_ids, bridge_syms)
    results[name]["rejected_reasons"] = {
        k: v for k, v in rejected_ids.items()
        if k in ("515050-listing-announcement", "515300-515300_20231214_MO7U",
                 "512890-official-split")}


def _rec(bundle, rid):
    return next(r for r in bundle["records"] if r["record_id"] == rid)


# R1-0 对照：真实包原样
run_case("R1-0-control", lambda b: None)

# R1-1 上市日期 2019-10-16 → 2020-01-02（原文/哈希/引文不变）
def m1(b):
    _rec(b, "515050-listing-announcement")["facts"]["listing_trade_date"] = \
        "2020-01-02"
run_case("R1-1-listing-date-tampered", m1)

# R1-2 上市记录 allowed_for=[]（无桥接用途）
def m2(b):
    _rec(b, "515050-listing-announcement")["allowed_for"] = []
run_case("R1-2-listing-without-bridge-purpose", m2)

# R1-3 分红金额每10份与每份都改为字符串 NaN
def m3(b):
    f = _rec(b, "515300-515300_20231214_MO7U")["facts"]
    f["cash_per_10_shares_announced"] = "NaN"
    f["cash_per_share_computed"] = "NaN"
run_case("R1-3-amounts-string-nan", m3)

# R1-4 时间区间倒挂 not_before=2026-01-01 > not_after=2019-01-01
def m4(b):
    te = _rec(b, "512890-official-split")["time_evidence"]
    te["not_before"] = "2026-01-01"
    te["not_after"] = "2019-01-01"
run_case("R1-4-inverted-time-range", m4)

# R1-5 所引用 PDF 的 pdf_sha256 改为全 0（文本哈希保留）
def m5(b):
    _rec(b, "515300-515300_20231214_MO7U")["source"]["pdf_sha256"] = "0" * 64
run_case("R1-5-referenced-pdf-hash-zeros", m5)

# ---------------------------------------------------------------------------
# R2：派生算术核验缺键/非数值（合成夹具 + 正式 prepare CLI）
# ---------------------------------------------------------------------------
spec = importlib.util.spec_from_file_location(
    "tqi", ROOT / "tests/integration/test_momentum_qualified_inputs.py")
tqi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tqi)


def run_r2(name, mutate_values):
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        protocol, bundle, values_path = tqi._build_fixture(tmp)
        if mutate_values(values_path):
            # 值文件变了：同步协议声明哈希，让拒绝可归因于键集/数值检查
            prot = json.loads(protocol.read_text())
            prot["derived_reference"] = {
                "path": str(values_path),
                "sha256": tqi._sha(values_path.read_bytes())}
            protocol = tmp / "protocol-refreshed.json"
            protocol.write_text(json.dumps(prot, ensure_ascii=False),
                                encoding="utf-8")
        out = tmp / "derived"
        proc = subprocess.run(
            [sys.executable, str(tqi.PREPARE), "--protocol", str(protocol),
             "--evidence-bundle", str(bundle), "--run04-values",
             str(values_path), "--out", str(out)],
            capture_output=True, text=True, timeout=300)
        manifest_exists = (out / "manifest.json").exists()
        n_lines = len(values_path.read_text().splitlines()) - 1
        results[name] = {
            "exit_code": proc.returncode,
            "manifest_written": manifest_exists,
            "reference_rows": n_lines,
            "stdout_tail": proc.stdout.strip().splitlines()[-2:],
            "defect_present": (proc.returncode == 0 and manifest_exists
                               and name != "R2-0-control"),
        }


def m_extra(p: Path) -> bool:
    lines = p.read_text().splitlines()
    lines.append("510300.SS,2030-01-01,0.5,fraction")  # 不存在的未来参考键
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def m_nan(p: Path) -> bool:
    lines = p.read_text().splitlines()
    parts = lines[1].split(",")
    parts[2] = "NaN"
    lines[1] = ",".join(parts)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


run_r2("R2-0-control", lambda p: None)
run_r2("R2-1-extra-reference-key", m_extra)
run_r2("R2-2-nan-reference-value", m_nan)

# ---------------------------------------------------------------------------
# R4：协议 codes 删去 prepare/qualification_bundle 两键仍能运行
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as td:
    tmp = Path(td)
    protocol, bundle, values_path = tqi._build_fixture(tmp)
    prot = json.loads(protocol.read_text())
    for k in ("prepare_momentum_qualified_inputs", "qualification_bundle"):
        prot.get("codes", {}).pop(k, None)
    prot2 = tmp / "protocol-codes-deleted.json"
    prot2.write_text(json.dumps(prot, ensure_ascii=False), encoding="utf-8")
    out = tmp / "derived"
    proc = subprocess.run(
        [sys.executable, str(tqi.PREPARE), "--protocol", str(prot2),
         "--evidence-bundle", str(bundle), "--run04-values", str(values_path),
         "--out", str(out)], capture_output=True, text=True, timeout=300)
    results["R4-1-codes-deleted-still-runs"] = {
        "exit_code": proc.returncode,
        "manifest_written": (out / "manifest.json").exists(),
        "defect_present": proc.returncode == 0,
        "note": "实际执行的两文件（prepare CLI/qualification_bundle）不在 "
                "codes 时仍退出 0",
    }

results["_meta"] = {
    "purpose": "R1–R4 反例复现与返修后回归；原文件未动（run-01=返修前，"
               "run-02=返修后/旧包对照，run-03=返修后/v1.1 包）",
    "date": "2026-09-13",
    "bundle_under_test": _BUNDLE,
}
(OUT / "summary.json").write_text(
    json.dumps(results, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
all_ok = True
for k, v in results.items():
    if k.startswith("_"):
        continue
    ok = v.get("expectation_met", not v.get("defect_present", True))
    all_ok &= bool(ok)
    print(f"{'✓' if ok else '✗ 缺陷在'}: {k}")
print("ALL EXPECTATIONS MET" if all_ok else "SOME DEFECTS REMAIN")
