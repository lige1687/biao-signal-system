#!/usr/bin/env python3
"""S1–S3 反例复现（主控复核 v1.4.0 §12.2/§12.3；返修前留证）。

S1：同一记录绑定不动，(a) 从 fact_binding.fields 删掉 ex_date 并按剩余
字段重算指纹；(b) 只改 time_evidence.published_date。当前接口下两者都
重新通过 → 缺陷在。
S2：合成夹具参考 CSV 删一行并在测试协议中合法更新该文件 SHA → 仍退出 0
且 complete_consistent=true → 缺陷在。
S3：task2_extract_facts_v2.py 以 write_text 直接写正式位置（已被协议
引用）→ 覆盖风险在（以代码事实记录，不实际覆盖）。

输出 summary 到 rework-s123/repro-run-01/。不触碰任何正式文件。
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

_RUN = sys.argv[1] if len(sys.argv) > 1 else "repro-run-01"
SCHEMA = sys.argv[2] if len(sys.argv) > 2 else "1.1"
OUT = ROOT / ("docs/experiments/raw/research-fixed-etf-evidence-integration"
              "-2026-09-13/rework-s123") / _RUN
OUT.mkdir(parents=True, exist_ok=False)  # 排他：同号重跑即失败

from lei_signal.research.qualification_bundle import (  # noqa: E402
    fact_tuple_fingerprint,
    validate_evidence_bundle,
)

BUNDLE = json.loads((ROOT / ("docs/experiments/raw/"
                             "research-fixed-etf-evidence-integration"
                             f"-2026-09-13/evidence-bundle-v{SCHEMA}.json"))
                    .read_text(encoding="utf-8"))
UNIVERSE = {"159652.SZ", "510300.SS", "512400.SS", "512890.SS", "513870.SS",
            "515050.SS", "515130.SS", "515170.SS", "515300.SS", "515880.SS",
            "516220.SS", "518850.SS", "562590.SS", "588000.SS"}
results: dict = {}


def validated_ids(bundle):
    res = validate_evidence_bundle(bundle, root=ROOT, universe=UNIVERSE)
    return ({r["record_id"] for r in res["validated"]},
            {r["record_id"]: r["reasons"] for r in res["rejected"]})


# S1-a 基准：512890 拆分日改成 10-23（绑定不动）→ 应被拒
b = copy.deepcopy(BUNDLE)
rec = next(r for r in b["records"] if r["record_id"] == "512890-official-split")
rec["facts"]["ex_date"] = "2021-10-23"
ok, rej = validated_ids(b)
results["S1-a-date-tamper-binding-untouched"] = {
    "rejected_as_expected": "512890-official-split" not in ok,
    "rejected_reasons": rej.get("512890-official-split", [])[:2]}

# S1-b 反例：删掉 fields 里的 ex_date 并按剩余字段重算指纹 → 当前会通过
b = copy.deepcopy(BUNDLE)
rec = next(r for r in b["records"] if r["record_id"] == "512890-official-split")
rec["facts"]["ex_date"] = "2021-10-23"
fields = [f for f in rec["fact_binding"]["fields"] if f != "ex_date"]


def _field_value(r, field):
    if field.startswith("time_evidence."):
        return (r.get("time_evidence") or {}).get(field.split(".", 1)[1])
    return r["facts"][field]


entry = {f: _field_value(rec, f) for f in fields}
rec["fact_binding"]["fields"] = fields
rec["fact_binding"]["fingerprint"] = fact_tuple_fingerprint(
    rec["instrument_id"], rec["event_id"], rec["fact_type"], entry)
ok, rej = validated_ids(b)
results["S1-b-shrink-fields-passes"] = {
    "defect_present": "512890-official-split" in ok,
    "note": "消费中的拆分日被移出核验范围后，改动日期通过"}

# S1-c 反例：只改 time_evidence.published_date（绑定不含时间字段）→ 通过
b = copy.deepcopy(BUNDLE)
rec = next(r for r in b["records"] if r["record_id"] == "512890-official-split")
rec["time_evidence"]["published_date"] = "2021-10-01"
ok, rej = validated_ids(b)
results["S1-c-time-value-tamper-passes"] = {
    "defect_present": "512890-official-split" in ok,
    "note": "已核时间值不在绑定合同内，改动通过"}

# ---------------------------------------------------------------------------
# S2：参考表删一行 + 合法更新协议声明 SHA → 仍 complete_consistent
spec = importlib.util.spec_from_file_location(
    "tqi", ROOT / "tests/integration/test_momentum_qualified_inputs.py")
tqi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tqi)

with tempfile.TemporaryDirectory() as td:
    tmp = Path(td)
    protocol, bundle, values_path = tqi._build_fixture(tmp)
    lines = values_path.read_text().splitlines()
    del lines[1]  # 删一行正式参考键
    values_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    prot = json.loads(protocol.read_text())
    prot["derived_reference"] = {"path": str(values_path),
                                 "sha256": tqi._sha(values_path.read_bytes())}
    protocol2 = tmp / "protocol-sha-updated.json"
    protocol2.write_text(json.dumps(prot, ensure_ascii=False),
                         encoding="utf-8")
    out = tmp / "derived"
    proc = subprocess.run(
        [sys.executable, str(tqi.PREPARE), "--protocol", str(protocol2),
         "--evidence-bundle", str(bundle), "--run04-values", str(values_path),
         "--out", str(out)], capture_output=True, text=True, timeout=300)
    manifest = (json.loads((out / "manifest.json").read_text())
                if (out / "manifest.json").exists() else None)
    results["S2-reference-row-removed-still-complete"] = {
        "exit_code": proc.returncode,
        "manifest_written": manifest is not None,
        "complete_consistent": (manifest or {}).get("result", {}).get(
            "momentum_key_check", {}).get("complete_consistent"),
        "defect_present": proc.returncode == 0,
        "note": "少一个正式参考键仍报完整一致：算法没有独立键集合基准"}

results["_meta"] = {
    "purpose": "S1/S2 反例：repro-run-01=v1.1 包/旧接口留证（缺陷在）；"
               "repro-run-02=v1.2 包/新接口验证反转",
    "date": "2026-09-13",
    "bundle_schema": SCHEMA,
    "s3_note": "task2_extract_facts_v2.py 旧版对正式位置 write_text 直接"
               "覆盖（代码事实，repro-run-01 留证）；新版已改排他写+字节"
               "比较，见 rework-s123/bundle-v1.2 复现记录"}
(OUT / "summary.json").write_text(
    json.dumps(results, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
cases = {
    "S1-a-date-tamper-binding-untouched": lambda v: v["rejected_as_expected"],
    "S1-b-shrink-fields-passes": lambda v: not v["defect_present"],
    "S1-c-time-value-tamper-passes": lambda v: not v["defect_present"],
    "S2-reference-row-removed-still-complete": lambda v: not v["defect_present"],
}
all_ok = True
for k, check in cases.items():
    ok = bool(check(results[k]))
    all_ok &= ok
    print(f"{'✓' if ok else '✗ 缺陷在'}: {k}")
print("ALL EXPECTATIONS MET" if all_ok else "SOME DEFECTS REMAIN")
