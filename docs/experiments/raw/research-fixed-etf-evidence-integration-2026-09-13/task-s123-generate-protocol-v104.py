#!/usr/bin/env python3
"""S1–S3 收尾协议生成：fixed-etf 协议 v1.0.4（排他保存）。

以 protocol-v1.0.3.json 为基底，仅更新证据包引用与修订记录：

- research_evidence / inputs.evidence_bundle 改指证据包 **v1.2**
  （evidence-bundle-v1.2.json：按 REQUIRED_BINDING_FIELDS 把已核时间值
  time_evidence.published_date 纳入绑定与抽取输出；返修 S1）；
- 其余（codes 十键、冻结输入、对象、目标、公式、窗口）不变；
- revisions 追加 1.0.4：S1 必需字段固定、S2 正式键双向核对、S3 抽取
  产物排他保护，以及 run-08 超预算偏差的声明（见执行报告 §10）。

保存纪律：O_EXCL 排他创建（已存在即失败），读回核哈希后才更新 current
指针。零真实派生、零真实运行、零联网。
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
TASK = ROOT / "docs/experiments/raw/research-fixed-etf-evidence-integration-2026-09-13"
BASE = TASK / "protocol-v1.0.3.json"
OUT = TASK / "protocol-v1.0.4.json"
POINTER = TASK / "protocol.json"
BUNDLE_V12 = TASK / "evidence-bundle-v1.2.json"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


protocol = json.loads(BASE.read_text(encoding="utf-8"))
assert protocol["protocol_version"] == "1.0.3", "基底版本不符"

protocol["protocol_version"] = "1.0.4"
protocol["date"] = "2026-09-13"
protocol["research_evidence"] = {
    "path": str(BUNDLE_V12.relative_to(ROOT)), "sha256": sha(BUNDLE_V12)}
protocol["inputs"]["evidence_bundle"] = dict(protocol["research_evidence"])
protocol["revisions"].append({
    "version": "1.0.4",
    "date": "2026-09-13",
    "changes": [
        "主控复核 v1.4.0 §12 S1–S3 收尾：证据包升 v1.2——已核时间值"
        " time_evidence.published_date 与消费必需字段（按三类事实固定，"
        "不可由输入删减）一并纳入 fact_binding 指纹与抽取输出比对（S1）；"
        "codes 十键不变（实现改动以现行哈希为准，由派生/动量入口强制核验）；"
        "v1.1 包保留，在新接口下不再作为已核事实消费。",
    ],
    "impact": ("固定池/区间/对象/目标/公式不变；零真实派生、零真实运行。"
               "run-08 超预算偏差声明见执行报告 §10.3；证据产物由"
               " task2_extract_facts_v2.py 排他写保护（S3）。"),
})

text = json.dumps(protocol, indent=1, ensure_ascii=False) + "\n"
expected_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()

try:
    fd = os.open(OUT, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
except FileExistsError:
    print(f"拒绝覆盖已存在的协议版本文件：{OUT}", file=sys.stderr)
    raise SystemExit(1) from None
with os.fdopen(fd, "w", encoding="utf-8") as f:
    f.write(text)
read_back = sha(OUT)
assert read_back == expected_sha, f"读回哈希不一致：{read_back} != {expected_sha}"

POINTER.write_text(text, encoding="utf-8")
assert sha(POINTER) == read_back, "current 指针更新后与版本文件不一致"

print(f"{OUT.name} saved exclusively: {read_back}")
print("pointer protocol.json updated to same content")
print("research_evidence:", protocol["research_evidence"]["sha256"][:16])
