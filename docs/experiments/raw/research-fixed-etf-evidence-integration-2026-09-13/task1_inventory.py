"""Task 1：固定输入盘点与需求清单（fixed-etf-evidence-integration-2026-09-13）。

只读四组本地材料；目录清单与逐文件 SHA-256 不计原文复核次数，
文本内容读取限定在索引/清单/已抽取文本（≤80 上限内记账）。
输出：source-inventory.json（源路径/SHA/绑定/可读性/重复关系）与
needs.csv（固定 14 只首报价/评价期 + 每条行动的事实与时间缺口）。
不扫描桌面、不恢复历史、不联网。
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
OUT = ROOT / "docs/experiments/raw/research-fixed-etf-evidence-integration-2026-09-13"
OLD_RAW = ROOT / "docs/experiments/raw/research-momentum-prototype-2026-09-13"

POOL = [
    "159652.SZ", "510300.SS", "512400.SS", "512890.SS", "513870.SS",
    "515050.SS", "515130.SS", "515170.SS", "515300.SS", "515880.SS",
    "516220.SS", "518850.SS", "562590.SS", "588000.SS",
]

GROUPS = {
    "listing-leads": ROOT / "docs/experiments/raw/research-mixed-evaluation-2026-09-09/historical-qualification",
    "action-sources": ROOT / "docs/experiments/raw/research-rotation-clean-2026-09-09/full-pool-preparation/action-sources",
    "515300-official": ROOT / "docs/experiments/raw/research-rotation-clean-2026-09-09/full-pool-preparation/515300-official-qualification",
    "calendar": ROOT / "docs/experiments/raw/research-calendar-completion-2026-09-10",
}

# 文本内容读取记账（≤80）
text_reads: list[str] = []


def read_text_capped(p: Path, limit: int = 20000) -> str:
    text_reads.append(str(p.relative_to(ROOT)))
    if len(text_reads) > 80:
        raise RuntimeError("文本读取超出 80 上限")
    return p.read_text(encoding="utf-8", errors="replace")[:limit]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    out_dir = OUT / "run-01"
    out_dir.mkdir(parents=True, exist_ok=False)  # 拒绝覆盖：重跑须换新编号

    # ---- 工作区状态 ----
    git_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    this_round_files = [
        "src/lei_signal/research/momentum_prototype.py",
        "scripts/run_momentum_prototype.py",
        "scripts/run_momentum_research_prototype.py",
        "tests/unit/test_momentum_prototype.py",
        "tests/integration/test_momentum_prototype_cli.py",
    ]
    code_hashes = {}
    for f in this_round_files:
        p = ROOT / f
        if p.exists():
            code_hashes[f] = sha(p)

    # ---- 冻结输入哈希（原动量协议 fixed_inputs） ----
    old_proto = json.loads(
        (OLD_RAW / "protocol.json").read_text())  # 现行 v1.0.5
    inputs = old_proto["inputs"]
    input_hashes = {}
    for key, entry in inputs.items():
        if isinstance(entry, dict) and "path" in entry:
            p = ROOT / entry["path"]
            if key == "snapshot_dir":
                p = p / "snapshot.json"
            input_hashes[key] = {"path": entry["path"], "sha256": sha(p)}

    # ---- 四组材料逐文件哈希与重复识别 ----
    inventory_groups: dict[str, list[dict]] = {}
    hash_index: dict[str, list[str]] = {}
    for gname, gdir in GROUPS.items():
        entries = []
        for p in sorted(gdir.rglob("*")):
            if not p.is_file():
                continue
            digest = sha(p)
            rel = str(p.relative_to(ROOT))
            hash_index.setdefault(digest, []).append(rel)
            entries.append({
                "path": rel, "sha256": digest, "bytes": p.stat().st_size,
                "kind": p.suffix.lower().lstrip(".") or "none",
            })
        inventory_groups[gname] = entries

    duplicates = {
        h: paths for h, paths in hash_index.items() if len(paths) > 1
    }

    # ---- 索引/清单内容（受限读取） ----
    index_notes: dict[str, object] = {}

    def try_read(rel: str, cap: int = 6000) -> dict:
        p = ROOT / rel
        if not p.exists():
            return {"path": rel, "missing": True}
        raw = read_text_capped(p, cap)
        try:
            return {"path": rel, "parsed": json.loads(raw)}
        except json.JSONDecodeError:
            return {"path": rel, "text_head": raw[:1200]}

    index_notes["listing-source-manifest"] = try_read(
        "docs/experiments/raw/research-mixed-evaluation-2026-09-09/"
        "historical-qualification/source-manifest.json")
    index_notes["listing-qualification-md"] = try_read(
        "docs/experiments/raw/research-mixed-evaluation-2026-09-09/"
        "historical-qualification/qualification.md")
    index_notes["listing-product-events"] = try_read(
        "docs/experiments/raw/research-mixed-evaluation-2026-09-09/"
        "historical-qualification/product-events.json", 12000)
    index_notes["listing-index-universe"] = try_read(
        "docs/experiments/raw/research-mixed-evaluation-2026-09-09/"
        "historical-qualification/index-universe.json", 8000)
    index_notes["515300-source-manifest"] = try_read(
        "docs/experiments/raw/research-rotation-clean-2026-09-09/"
        "full-pool-preparation/515300-official-qualification/source-manifest.json")
    index_notes["515300-events"] = try_read(
        "docs/experiments/raw/research-rotation-clean-2026-09-09/"
        "full-pool-preparation/515300-official-qualification/events.json", 12000)
    index_notes["515300-qualification-md"] = try_read(
        "docs/experiments/raw/research-rotation-clean-2026-09-09/"
        "full-pool-preparation/515300-official-qualification/qualification.md")
    index_notes["calendar-protocol"] = try_read(
        "docs/experiments/raw/research-calendar-completion-2026-09-10/protocol.json", 4000)

    # ---- needs.csv：先建需求集合，再谈证据 ----
    actions = json.loads(
        (ROOT / inputs["actions"]["path"]).read_text(encoding="utf-8"))["events"]
    needs_rows: list[dict] = []
    for sym in POOL:
        needs_rows.append({
            "scope": "listing",
            "instrument_id": sym, "event_id": "",
            "fact_gap": ("缺上市交易日官方证据（首报价≠上市日）"
                         if sym not in {"515050.SS", "562590.SS"} else
                         "已有上市公告 PDF 线索，需逐页核对上市交易日/单位/身份"),
            "time_gap": "缺历史可得时间依据",
            "affected_uses": "ranking/research_signal（starts_after_window 拒绝）",
        })
    for ev in actions:
        etype = ev.get("type")
        if etype == "trading_halt":
            needs_rows.append({
                "scope": "halt", "instrument_id": ev.get("symbol", ""),
                "event_id": ev.get("event_id", ""),
                "fact_gap": "停牌区间仅作缺口解释，不进经济指数（本轮无事实缺口）",
                "time_gap": "不适用",
                "affected_uses": "无（解释性）",
            })
            continue
        sym = ev.get("symbol", "")
        canon = f"{sym}.SS" if sym.isdigit() else sym
        official = ""
        if etype == "split" and canon in {"512890.SS", "515050.SS", "515880.SS"}:
            official = "已有官方拆分 PDF，需核对方向（旧1份变新几份）与日期"
        elif canon == "515300.SS":
            official = "已有六份官方分红原文线索，需逐份核对并确认第七次事件的二手限制"
        else:
            official = "仅有东方财富表格页（HTML/CSV），非官方公告原文"
        needs_rows.append({
            "scope": etype,
            "instrument_id": canon, "event_id": ev.get("event_id", ""),
            "fact_gap": official + "；金额/登记/除息/发放日期待逐字段核对",
            "time_gap": ("available_at 未知（20/20）；无公布日期下界证据"
                         if not ev.get("available_at") else "已声明"),
            "affected_uses": "research_signal（时间资格）；attribution",
        })

    # ---- 写产物 ----
    inventory = {
        "schema_version": "fixed-etf-source-inventory/1.0",
        "git_head": git_head,
        "code_hashes": code_hashes,
        "frozen_inputs": input_hashes,
        "groups": inventory_groups,
        "duplicates": duplicates,
        "index_notes": index_notes,
        "text_reads_used": len(text_reads),
        "text_reads": text_reads,
        "notes": [
            "哈希全量覆盖四组材料；文本内容仅读取索引/清单/已抽取文本",
            "『仓库保存了』不等于『官方内容已核实』；PDF 原文核对在 Task 2",
            "159516/516690 等名单外产品仅登记存在，不接入本轮",
        ],
    }
    (out_dir / "source-inventory.json").write_text(
        json.dumps(inventory, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    with open(OUT / "needs.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "scope", "instrument_id", "event_id", "fact_gap", "time_gap",
            "affected_uses"])
        w.writeheader()
        w.writerows(needs_rows)

    print(f"groups: {', '.join(f'{k}={len(v)}' for k, v in inventory_groups.items())}")
    print(f"duplicate hashes: {len(duplicates)}")
    print(f"needs rows: {len(needs_rows)} (listing 14 + actions {len(actions)})")
    print(f"text reads: {len(text_reads)}/80")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
