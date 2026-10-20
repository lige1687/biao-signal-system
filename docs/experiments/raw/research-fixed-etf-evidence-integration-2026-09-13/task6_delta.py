"""Task 6：qualification-delta.csv——证据接入前后的发现对照（只读两次运行产物）。"""
from __future__ import annotations

import csv
import json
from pathlib import Path

THIS = Path("/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/"
            "research-fixed-etf-evidence-integration-2026-09-13")


def findings_by_key(run_dir: str) -> dict[tuple[str, str], dict]:
    q = json.loads((THIS / run_dir / "quality.json").read_text())
    out = {}
    for f in q["price_findings"]:
        key = (f.get("instrument") or "—", f["code"])
        # 同产品同码多条时保留首条（本轮发现均为产品级单条）
        out.setdefault(key, f)
    return out


def main() -> int:
    before = findings_by_key("run-03")  # v1.0.0：无证据接入
    after = findings_by_key("run-05")   # v1.0.1：listing 桥接接入
    rows = []
    for key in sorted(set(before) | set(after)):
        sym, code = key
        b, a = before.get(key), after.get(key)
        if b is None and a is None:
            continue
        resolved = bool(b) and not a
        changed = (b is None) != (a is None) or (
            b is not None and a is not None and b["message"] != a["message"])
        rows.append({
            "instrument_id": sym,
            "finding_code": code,
            "before_message": (b or {}).get("message", "（无该发现）"),
            "after_message": (a or {}).get("message", "（无该发现）"),
            "evidence_used": (
                "515050/562590 官方上市公告 PDF（listing 桥接）"
                if changed and sym in {"515050.SS", "562590.SS"} else ""),
            "finding_changed": "是" if changed else "否",
            "finding_removed": "是" if resolved else "否",
            "still_blocks_uses": (
                "是" if a is not None else "否"),
            "next_material_needed": (
                "交易所/管理人官方披露的历史可得依据（资格授予仍需另建准入标准）"
                if a is not None and sym in {"515050.SS", "562590.SS"} else
                "官方上市公告原文" if code == "starts_after_window" else
                "官方分红/拆分公告原文与公布日期依据"),
        })
    out = THIS / "qualification-delta.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"rows={len(rows)} changed={sum(1 for r in rows if r['finding_changed']=='是')} "
          f"removed={sum(1 for r in rows if r['finding_removed']=='是')}")
    print("wrote", out.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
