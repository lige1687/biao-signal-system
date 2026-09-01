#!/usr/bin/env python3
"""模块 E 美股极值周检（2026-08-28 上线版·手册 3.6 口径）。

检查项（数据 = lab.db SP500 宽度，注意回填管线滞后，如实标注）：
- v1 底部区：B20<=15 且 B50<=15（双线共振）
- v3 底部区：三线同 <=15（中长期级别，信号最少级别最大）
- 顶部对冲区：B20>=85 且 B50>=85（用户只做多：此状态=停止加仓提示）
- 冷却：4 周内已触发过则标注冷却中
输出：控制台 + ~/.lei_signal_lab/paper/module_e_check_YYYY-MM-DD.md
用法：python3 scripts/check_module_e_signals.py （建议每周五收盘后）
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

DB = Path.home() / ".lei_signal_lab/lab.db"
OUT = Path.home() / ".lei_signal_lab/paper"


def main() -> int:
    con = sqlite3.connect(DB)
    rows = con.execute(
        "SELECT as_of, breadth_20, breadth_50, breadth_200 FROM"
        " market_breadth_snapshots WHERE market_id='SP500'"
        " AND breadth_20 IS NOT NULL ORDER BY as_of DESC LIMIT 30"
    ).fetchall()
    con.close()
    if not rows:
        print("✗ SP500 宽度数据缺失（需跑 backfill_breadth_full --market us"
              " + ingest）")
        return 1
    last = rows[0]
    b20, b50, b200 = last[1], last[2], last[3]
    as_of = last[0][:10]
    lag = (datetime.now() - datetime.strptime(as_of, "%Y-%m-%d")).days
    lines = [f"# 模块 E 美股极值周检 {datetime.now().date()}",
             f"\n数据截至 {as_of}（滞后 {lag} 天——回填管线为手动，"
             f"重大波动期请先刷新）",
             f"\n当前：B20 {b20:.1f}% / B50 {b50:.1f}% / B200 {b200:.1f}%"]
    v1 = b20 <= 15 and b50 <= 15
    v3 = v1 and b200 <= 15
    top = b20 >= 85 and b50 >= 85
    lines.append(f"\n- v1 双线底部区（B20&B50≤15）：{'★ 触发中' if v1 else '否'}"
                 f"（距 15 线：B20 {b20-15:+.1f}pp / B50 {b50-15:+.1f}pp）")
    lines.append(f"- v3 三线底部区（加 B200≤15）：{'★★ 触发中' if v3 else '否'}"
                 f"（B200 距 15 线 {b200-15:+.1f}pp）")
    lines.append(f"- 顶部区（B20&B50≥85）：{'▲ 触发中（只做多：停加仓提示）' if top else '否'}"
                 f"（距 85 线：B20 {b20-85:+.1f}pp / B50 {b50-85:+.1f}pp）")
    # 最近一次各区触发日期（30 日窗口）
    for name, cond in (("v1 底部", lambda r: r[1] <= 15 and r[2] <= 15),
                       ("顶部", lambda r: r[1] >= 85 and r[2] >= 85)):
        hit = next((r[0][:10] for r in rows if cond(r)), None)
        lines.append(f"- 近 30 日最近一次 {name}触发：{hit or '无'}")
        if hit:
            days = (datetime.now() - datetime.strptime(hit, "%Y-%m-%d")).days
            if days < 28:
                lines.append(f"  （{days} 天前 < 4 周冷却期，新信号未解锁）")
    txt = "\n".join(lines)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"module_e_check_{datetime.now().date()}.md").write_text(
        txt, encoding="utf-8")
    print(txt)
    return 0 if (v1 or v3 or top) else 2


if __name__ == "__main__":
    raise SystemExit(main())
