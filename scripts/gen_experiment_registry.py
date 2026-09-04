#!/usr/bin/env python3
"""一次性：为 docs/experiments + docs/research-* 生成 registry.json 种子。

分类用「路径/标题/一句话结论」关键词规则推断；结论状态只在高置信
关键词命中时标注，否则留空（界面显示为未标，不乱猜）。
产出后人工过目再提交。此后新增实验按 AGENTS.md 规约手工登记。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lei_signal.api import experiment_reports as er  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

# (类别, [关键词]) —— 按顺序首个命中即归类；prompt-* 强制任务书。
RULES: list[tuple[str, list[str]]] = [
    ("研究总纲", ["research-overview", "research-round", "research-playbook",
                "research-momentum", "research-ma-deviation", "research-sentiment",
                "research-factor", "system-architecture", "next-steps",
                "CROSS-GROUP-SYNTHESIS"]),
    ("数据与质量", ["coverage-sync", "data-quality", "pool-recovery", "etf-expansion",
                 "pool_manifest", "broad-index-coverage", "broad-index-gap"]),
    ("美股与跨市场", ["us-treasury", "vix", "us-erp", "tsy10y", "spx-vs-ndx",
                 "us-merge", "us-stocks", "cross-market", "美股", "美债"]),
    ("宽度择时", ["breadth", "kuandu", "出清", "宽度", "crash", "capitulation",
               "broad-index-portfolio", "broad-index-summary",
               "broad-index-comprehensive"]),
    ("组合与仓位", ["binary", "hysteresis", "二元", "滞回", "三档", "定投", "vt-grid",
                "position-mapping", "cash-leg", "gold-expand", "portfolio",
                "price-ladder", "阶梯", "dca", "switch-walkforward", "换档",
                "astock-panel", "timing",
                "csi500-fee", "fee-sensitivity", "staged-entry", "分批",
                "extreme-bottom", "binary-vs-tiered"]),
    ("出场与止损", ["exit", "stop-loss", "timestop", "time-stop", "止损", "出场",
                "knife", "staged-exit", "tsx"]),
    ("模块与信号", ["module", "b-adaptation", "bcd-retrial", "bform", "m5-final",
                 "signal-density", "dense", "false-breakout", "rs26", "siphon",
                 "虹吸", "top-structure", "lei-ARCHIVE", "a6"]),
    ("语义组合", ["master-slave", "multi-confirm", "timescale", "overnight",
              "semantic", "todo-new-composition", "antifragile", "反脆弱",
              "主从", "多重确认", "时间尺度", "隔夜"]),
    ("宏观与情绪", ["macro", "valuation", "sentiment",
                "huanjing", "heiti", "估值", "情绪"]),
    ("方法论与验证", ["orthogonality", "walkforward", "robustness", "meta-scan",
                  "full-stack", "lifecycle", "regime-gate", "trd-gate",
                  "combined-certification", "system-fragility", "holdings-correlation",
                  "FINAL-VERDICT", "final-report", "experiment-log", "filters-round4",
                  "shrink-filter", "p1-increment", "pollution"]),
]

FALSIFIED_KW = ["证伪", "无效", "全灭", "不成立", "否决", "失败", "无增量", "不通过", "已废弃", "死亡"]
PASSED_KW = ["通过", "有效", "占优", "胜出", "全过", "验证成立", "维持", "确认有效", "正面回答"]


def classify(rel: str, title: str, oneliner: str, is_prompt: bool) -> str:
    if is_prompt:
        return "任务书"
    hay = f"{rel} {title} {oneliner}"
    for cat, kws in RULES:
        if any(k.lower() in hay.lower() for k in kws):
            return cat
    return ""


def verdict_of(oneliner: str, archived: bool) -> str:
    if any(k in oneliner for k in FALSIFIED_KW):
        return "falsified"
    if any(k in oneliner for k in PASSED_KW):
        return "passed"
    return ""


def main() -> None:
    items = er.scan_reports()
    entries: dict[str, dict[str, str]] = {}
    unclassified: list[str] = []
    for it in items:
        cat = classify(it["name"], it["title"], it["oneLiner"], it["isPrompt"])
        if not cat:
            unclassified.append(it["name"])
            continue
        e: dict[str, str] = {"category": cat}
        v = verdict_of(it["oneLiner"], it["archived"])
        if v:
            e["verdict"] = v
        entries[it["name"]] = e
    out = {
        "version": 1,
        "note": "实验报告库登记簿：category 必填且取自固定枚举；verdict 选填 passed/falsified/mixed/watch。新实验归档时必须同步登记（见 AGENTS.md 归档规约）。",
        "categories": er.CATEGORIES + ["任务书"] if "任务书" not in er.CATEGORIES else er.CATEGORIES,
        "entries": dict(sorted(entries.items())),
    }
    (ROOT / er.REGISTRY_PATH).write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"登记 {len(entries)}/{len(items)}；未分类 {len(unclassified)}：")
    for u in unclassified:
        print("  ", u)


if __name__ == "__main__":
    main()
