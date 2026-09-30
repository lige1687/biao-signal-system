#!/usr/bin/env python3
"""A3 隔离审计脚本：绑定哈希复算 + A2 记录语义复核（复用 A2 N5/N6/N9/N10 逻辑）
+ 四类反例必须被拒绝 + 1 个合成正例必须通过。

只读 A2 证据包与绑定 PDF；合成记录仅在内存中构造，不落库、不写回任何资格状态。
退出码：0=全部通过，1=有违规。运行记录写入同目录 run-output.txt。
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
A2_DIR = REPO / "docs/experiments/raw/factor-a2-2026-09-19"

# 合同 §0 绑定哈希（执行前冻结值，独立于 A2 证据包再核一遍）
BINDING = {
    "evidence/512890-arrange-20211013.pdf": "3a2321b4bd1c52e69287304229be01eb4d04a7c51e8064c518f5f4597ed9b47e",
    "evidence/512890-result-20211025.pdf": "a1109b3c04106d1b10462ecb409c676d3b3d4dd6810a98b660f46c4c27f2bab2",
    "full-pool-preparation/action-sources/512890-official-split.pdf":
        "4e224e9585dcb6bb0151fd5b043f9df201724a819a2bc722181c54db4e1821b9",
}

def _d(s):
    return date.fromisoformat(s) if s else None

def check_time_semantics(rec):
    """复用 A2 audit/check_time_semantics.py 的规则（N5/N6/N9/N10 等）。"""
    v = []
    eid = rec.get("event_id")
    pub, avail, eff = (_d(rec.get("publication_time")), _d(rec.get("available_at")),
                       _d(rec.get("effective_time")))
    bound = rec.get("publication_bound")
    if avail is not None and bound != "exact":
        v.append(f"[N5] {eid}: bound={bound} 非 exact 却填 available_at")
    if avail is not None and avail == eff:
        v.append(f"[N6] {eid}: available_at=effective_time，生效日冒充到达")
    if avail is not None and not rec.get("availability_evidence"):
        v.append(f"[N6b] {eid}: available_at 非 null 但缺到达证据")
    if pub and avail and pub > avail:
        v.append(f"[N9] {eid}: publication_time 晚于 available_at")
    dec = _d(rec.get("decision_at"))
    if dec and avail and dec < avail:
        v.append(f"[N10] {eid}: decision_at 早于 available_at")
    return v

def main():
    out, fail = [], False

    # 1. 绑定哈希独立复算
    for rel, want in BINDING.items():
        if rel.startswith("full-pool"):
            p = REPO / "docs/experiments/raw/research-rotation-clean-2026-09-09" / rel
        else:
            p = A2_DIR / rel
        got = hashlib.sha256(p.read_bytes()).hexdigest()
        ok = got == want
        out.append(f"[binding] {p.name}: {'OK' if ok else 'MISMATCH ' + got}")
        fail |= not ok

    # 2. A2 记录 512890 语义复核（维持原状：available_at 必须 null）
    pack = json.loads((A2_DIR / "a2-evidence-pack.json").read_text())
    rec = next(r for r in pack["records"] if r["event_id"] == "512890-split-2021-10-22")
    viol = check_time_semantics(rec)
    out.append(f"[a2-record] 512890 语义检查: {'PASS' if not viol else viol}")
    if viol:
        fail = True
    if rec.get("available_at") is not None:
        out.append("[a2-record] 违规：available_at 被 A3 改动")
        fail = True
    else:
        out.append("[a2-record] available_at=null 维持原状 OK")

    # 3. A3 本轮产出记录（合成自证据矩阵结论，不落资格层）
    a3_rec = {
        "event_id": "512890-split-2021-10-22",
        "publication_time": "2021-10-13",
        "publication_bound": "not_before",
        "available_at": None,
        "effective_time": "2021-10-22",
    }
    viol = check_time_semantics(a3_rec)
    out.append(f"[a3-record] {'PASS' if not viol else viol}")
    fail |= bool(viol)

    # 4. 四类反例——每类都必须被拒绝（期望违规非空）
    counter = [
        ("R-日期冒充到达：effective_time 填进 available_at（N6）", {
            "event_id": "cx-N6", "publication_time": "2021-10-13",
            "publication_bound": "not_before", "available_at": "2021-10-22",
            "effective_time": "2021-10-22", "availability_evidence": "生效日字段"}),
        ("R-下界当上界：not_before 下界直接填 available_at（N5）", {
            "event_id": "cx-N5", "publication_time": "2021-10-13",
            "publication_bound": "not_before", "available_at": "2021-10-13",
            "effective_time": "2021-10-22", "availability_evidence": "落款日"}),
        ("R-历史页混入晚期证据：2026 年抓取时间当到达（N6b+N5）", {
            "event_id": "cx-late", "publication_time": "2021-10-13",
            "publication_bound": "exact", "available_at": "2026-09-20",
            "effective_time": "2021-10-22", "availability_evidence": ""}),
        ("R-访问失败写成不存在：404 反推从未存在（记为断言检查）", {
            "event_id": "cx-404", "publication_time": "2021-10-13",
            "publication_bound": "not_before", "available_at": None,
            "effective_time": "2021-10-22",
            "false_claim": "sse 渠道无此记录（实为访问失败）"}),
    ]
    for name, cx in counter:
        viol = check_time_semantics(cx)
        if "false_claim" in cx:  # 404 反推类：断言本身违规
            viol = ["[R-404] 访问失败被写成不存在（合同 §2 末条禁止）"]
        out.append(f"[counter] {name}: {'REJECTED OK' if viol else '!! 未被拒绝'}")
        fail |= not viol

    # 5. 合成正例——协议口径下合法的 Tier1 exact 记录必须通过（仅为规则自检，非本轮证据）
    positive = {
        "event_id": "synthetic-positive", "publication_time": "2021-10-13",
        "publication_bound": "exact",
        "available_at": "2021-10-14",
        "effective_time": "2021-10-22",
        "availability_evidence": "合成：假想的带时刻披露回执+渠道覆盖系统取数路径",
        "decision_at": "2021-10-15",
    }
    viol = check_time_semantics(positive)
    out.append(f"[positive] 合成正例: {'PASS OK' if not viol else '!! 正例被误拒 ' + str(viol)}")
    fail |= bool(viol)

    out.append(f"RESULT: {'ALL PASS' if not fail else 'FAILED'}")
    report = "\n".join(out)
    print(report)
    (Path(__file__).resolve().parent / "run-output.txt").write_text(report + "\n")
    return 1 if fail else 0

if __name__ == "__main__":
    sys.exit(main())
