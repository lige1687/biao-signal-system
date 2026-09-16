#!/usr/bin/env python3
"""R1–R4 返修协议生成：fixed-etf 协议 v1.0.2（排他保存）。

以 protocol-v1.0.1.json 为基底，只做返修要求的身份更新：

- codes 十个键全部刷新为当前文件哈希（qualification_bundle /
  prepare_momentum_qualified_inputs / run_momentum_research_prototype 随
  返修实现变化；删键不能免核由派生入口强制）；
- research_evidence 改指证据包 v1.1（task2_extract_facts_v2.py 重抽；
  含事实绑定/指纹/引用原件哈希/文内时间字段）；inputs.evidence_bundle
  同步指向 v1.1；
- 新增 derived_reference：run-04 values.csv（0db2492a…，独立既有算术
  基准）的身份声明，派生入口强制核验；
- revisions 追加 1.0.2 条目，记录 R1–R4 返修与版本断点（run-02 的
  7ad3c330、旧 v1.0.4/本任务 v1.0.0 丢失）。

保存纪律（返修 R4）：版本文件用 O_EXCL 排他创建（已存在即失败，不覆盖），
写出后读回核哈希一致才更新 current 指针。不改动动量任务目录（其指针保持
v1.0.7）。
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
TASK = ROOT / "docs/experiments/raw/research-fixed-etf-evidence-integration-2026-09-13"
BASE = TASK / "protocol-v1.0.1.json"
OUT = TASK / "protocol-v1.0.3.json"
SUPERSEDED = TASK / "protocol-v1.0.2.json"
POINTER = TASK / "protocol.json"
MOMENTUM_V107 = (ROOT / "docs/experiments/raw/research-momentum-prototype-2026-09-13"
                 "/protocol-v1.0.7.json")
RUN04_VALUES = (ROOT / "docs/experiments/raw/research-momentum-prototype-2026-09-13"
                "/run-04/values.csv")
BUNDLE_V11 = TASK / "evidence-bundle-v1.1.json"

CODE_FILES = {
    "data_quality": "src/lei_signal/research/data_quality.py",
    "data_snapshot": "src/lei_signal/research/data_snapshot.py",
    "definitions": "src/lei_signal/research/definitions.py",
    "factor_runtime": "src/lei_signal/research/factor_runtime.py",
    "momentum_prototype": "src/lei_signal/research/momentum_prototype.py",
    "run_momentum_research_prototype": "scripts/run_momentum_research_prototype.py",
    "symbol_identity": "src/lei_signal/research/symbol_identity.py",
    "trading_calendar": "src/lei_signal/research/trading_calendar.py",
    "qualification_bundle": "src/lei_signal/research/qualification_bundle.py",
    "prepare_momentum_qualified_inputs": "scripts/prepare_momentum_qualified_inputs.py",
}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


protocol = json.loads(BASE.read_text(encoding="utf-8"))
assert protocol["protocol_version"] == "1.0.1", "基底版本不符"

# 派生输入必须是原始名义快照（与 run-02 的 derived_from 一致）；
# v1.0.1 的 inputs.snapshot_dir 指向 run-02 派生快照（那是 run-05/06 的
# CLI 消费输入），直接继承会在派生时追加出第二列 economic_index。
momentum_inputs = json.loads(MOMENTUM_V107.read_text(encoding="utf-8"))["inputs"]
assert (momentum_inputs["calendar"] == protocol["inputs"]["calendar"]
        and momentum_inputs["publication"] == protocol["inputs"]["publication"]
        and momentum_inputs["actions"] == protocol["inputs"]["actions"]
        and momentum_inputs["evaluation_start"]
        == protocol["inputs"]["evaluation_start"]), "其余冻结输入必须一致"
protocol["inputs"]["snapshot_dir"] = dict(momentum_inputs["snapshot_dir"])

protocol["protocol_version"] = "1.0.3"
protocol["date"] = "2026-09-13"
protocol["codes"] = {
    k: {"path": rel, "sha256": sha(ROOT / rel)}
    for k, rel in CODE_FILES.items()
}
assert set(protocol["codes"]) == set(CODE_FILES), "codes 键集必须完整"
protocol["research_evidence"] = {
    "path": str(BUNDLE_V11.relative_to(ROOT)), "sha256": sha(BUNDLE_V11)}
protocol["inputs"]["evidence_bundle"] = dict(protocol["research_evidence"])
protocol["derived_reference"] = {
    "path": str(RUN04_VALUES.relative_to(ROOT)), "sha256": sha(RUN04_VALUES)}
protocol["revisions"].append({
    "version": "1.0.2",
    "date": "2026-09-13",
    "changes": [
        "主控复核 v1.3.0 §11 R1–R4 集中返修：证据包升 v1.1（事实绑定/指纹/"
        "引用原件哈希/文内时间字段；515050 公布日修正为 2019-10-11、"
        "512890 补登记日 2021-10-21 与拆分日 2021-10-22 并以落款 10-25 "
        "为公布参照）；桥接消费强制 listing_evidence_bridge 用途与同产品"
        "日期冲突排除；派生比对改双向键集核对（缺键/重复/非有限分别可见）；"
        "codes 十键刷新为当前哈希并新增 derived_reference 声明；"
        "协议以排他创建保存（已存在即失败）。",
    ],
    "impact": ("固定池/区间/对象/目标/公式不变；run-03~06 封存保留。"
               "版本断点如实保留：run-02 所引 7ad3c330 与旧动量 v1.0.4、"
               "本任务 v1.0.0（54a306d7）均不可恢复，旧产物按有限历史"
               "证据保留，不靠新版本洗成终版。"),
})
protocol["revisions"].append({
    "version": "1.0.3",
    "date": "2026-09-13",
    "changes": [
        "inputs.snapshot_dir 由 run-02 派生快照改回原始名义快照"
        "（canonical-snapshot-v2，与动量 v1.0.7 冻结一致；其余输入逐字段"
        "相同）：派生入口的输入必须是名义快照，v1.0.2 直接继承 v1.0.1 的"
        "消费侧输入导致 run-07 追加出第二列 economic_index 而被读回核验"
        "拒绝（run-07 保留失败留痕）。",
    ],
    "impact": "测量参数/对象/目标/公式不变；v1.0.2 文件保留不覆盖。",
})

text = json.dumps(protocol, indent=1, ensure_ascii=False) + "\n"
expected_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()

# 排他创建：已存在即失败（v1.0.4 覆盖事故的纪律性修复）
try:
    fd = os.open(OUT, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
except FileExistsError:
    print(f"拒绝覆盖已存在的协议版本文件：{OUT}", file=sys.stderr)
    raise SystemExit(1) from None
with os.fdopen(fd, "w", encoding="utf-8") as f:
    f.write(text)
read_back = sha(OUT)
assert read_back == expected_sha, (
    f"读回哈希不一致：{read_back} != {expected_sha}")

POINTER.write_text(text, encoding="utf-8")
assert sha(POINTER) == read_back, "current 指针更新后与版本文件不一致"

print(f"{OUT.name} saved exclusively: {read_back}")
print("pointer protocol.json updated to same content")
print(json.dumps({
    "codes": {k: v["sha256"][:16] for k, v in protocol["codes"].items()},
    "research_evidence": protocol["research_evidence"]["sha256"][:16],
    "derived_reference": protocol["derived_reference"]["sha256"][:16],
}, indent=1))
