"""分标的×模块胜率表生成：从回测 runs 明细聚合，供推荐/讨论查每笔的历史依据。

数据资产（docs/experiments/module_winrate.json）：
- 键 = f"{symbol}|{module}"，值 = 全期与近两年（entry≥两年前）两个窗口的
  笔数/胜率/平均R/最差R；
- 用户口径（2026-09-06）：给当前信号时结合历史经验报「这笔胜率怎么样」，
  Agent 据此给倾向——胜率是**标注层**（叙事参考），不参与技术判定。

用法：python scripts/build_module_winrate.py <run_id:module> [<run_id:module> ...]
（run_id 可从 /api/backtest/runs 列表取；脚本拉明细、同日同标去重后聚合）
"""
from __future__ import annotations

import json
import sys
import urllib.request
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "docs" / "experiments" / "module_winrate.json"


def fetch_trades(run_id: str) -> list[dict]:
    url = f"http://localhost:8000/api/backtest/runs/{run_id}"
    with urllib.request.urlopen(url, timeout=30) as r:
        d = json.load(r)
    if d.get("status") != "done":
        raise SystemExit(f"{run_id}: {d.get('status')} {d.get('error', '')}")
    return [t for t in d["trades"] if t.get("r_net") is not None]


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    recent_cut = (date.today() - timedelta(days=730)).isoformat()
    all_t: list[dict] = []
    for arg in sys.argv[1:]:
        run_id, _, module = arg.rpartition(":")
        if not run_id:
            raise SystemExit(f"参数需 run_id:module 形式: {arg}")
        for t in fetch_trades(run_id):
            t["module"] = module
            all_t.append(t)
    # 同日同标去重（引擎按均线组出笔，实盘一天只做一次）
    dedup: dict[tuple, dict] = {}
    for t in sorted(all_t, key=lambda x: (str(x["entry_date"]), x["symbol"])):
        dedup.setdefault((t["symbol"], str(t["entry_date"])), t)
    by_key: dict[str, list[dict]] = defaultdict(list)
    for t in dedup.values():
        by_key[f"{t['symbol']}|{t['module']}"].append(t)
    out = {
        "version": 1,
        "note_cn": (
            "分标的×模块历史胜率（标注层参考，不参与技术判定）。窗口："
            "all=全部样本、recent=近两年。同日同标去重；来源回测 run 明细。"
        ),
        "entries": {},
    }
    for key, ts in sorted(by_key.items()):
        def stats(rows: list[dict]) -> dict:
            rs = [t["r_net"] for t in rows]
            return {
                "n": len(rs),
                "win_rate": round(sum(1 for r in rs if r > 0) / len(rs), 3),
                "avg_r": round(sum(rs) / len(rs), 2),
                "worst_r": round(min(rs), 2),
                "best_r": round(max(rs), 2),
            }
        rec = [t for t in ts if str(t["entry_date"]) >= recent_cut]
        out["entries"][key] = {
            "all": stats(ts),
            **({"recent": stats(rec)} if rec else {}),
        }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"{len(out['entries'])} 个 标的|模块 条目 → {OUT}")


if __name__ == "__main__":
    main()
