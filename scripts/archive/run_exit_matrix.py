#!/usr/bin/env python3
"""出场变体矩阵·侧向探索（2026-08-31）：3 模块 × 4 出场变体，走工作台 API。

目的：工作台 22 条历史记录里 exit_variant 有 21 条是 a6_1_costbasis、
1 条 a6_3_structure_stop——a6_2_top_plus_keywave（顶部构造+关键性波动）
与 b3_dual（双条件退出）从未跑过，docs/experiments/ 也无出场专项报告。
本实验补全出场侧矩阵（入场侧已被 filters-round4 系统覆盖）。

模块冻结配置（与 full_stack 信号口径一致）：
- A: early + volume_filter=shrink + clock_mult=0.5
- B: breakout + cb30/cl3%（B'）
- C: v3 + bias_filter=-0.15
公共：全池 53 标的、rr_min=None、fee=standard、limit_guard=True。

不做判定（探索性矩阵，非预注册认证）——产出各组合 expR/PF/胜率/笔数
对照表，报告级。
"""
from __future__ import annotations

import json
import time
import urllib.request

BASE = "http://127.0.0.1:8000"

MODULES = {
    "A": {"module": "A", "entry_variant": "early", "volume_filter": "shrink",
          "overrides": {"clock_mult": 0.5}},
    "B": {"module": "B", "entry_variant": "breakout", "volume_filter": "none",
          "overrides": {"consolidation_bars": 30, "cluster_threshold": 0.03}},
    "C": {"module": "C", "entry_variant": "v3", "volume_filter": "none",
          "bias_filter": -0.15, "overrides": None},
}
EXITS = ["a6_1_costbasis", "a6_2_top_plus_keywave", "a6_3_structure_stop", "b3_dual"]


def post_run(payload: dict) -> str:
    req = urllib.request.Request(
        f"{BASE}/api/backtest/runs",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)["run_id"]


def get_run(run_id: str) -> dict:
    with urllib.request.urlopen(f"{BASE}/api/backtest/runs/{run_id}", timeout=60) as resp:
        return json.load(resp)


def main() -> None:
    results = []
    for mkey, mcfg in MODULES.items():
        for exit_v in EXITS:
            payload = {
                "symbols": None, "module": mcfg["module"],
                "rr_min": None,
                "entry_variant": mcfg.get("entry_variant"),
                "exit_variant": exit_v,
                "fee_label": "standard", "limit_guard": True,
                "volume_filter": mcfg.get("volume_filter", "none"),
                "bias_filter": mcfg.get("bias_filter"),
                "overrides": mcfg.get("overrides") or {},
            }
            try:
                run_id = post_run(payload)
            except Exception as exc:  # noqa: BLE001
                results.append({"module": mkey, "exit": exit_v, "error": str(exc)})
                print(f"[{mkey}/{exit_v}] 提交失败: {exc}")
                continue
            print(f"[{mkey}/{exit_v}] run_id={run_id} 已提交，轮询...")
            status, detail = None, {}
            for _ in range(240):  # 最多等 20 分钟
                time.sleep(5)
                detail = get_run(run_id)
                status = detail.get("status")
                if status in ("done", "failed"):
                    break
            row = {"module": mkey, "exit": exit_v, "run_id": run_id,
                   "status": status}
            if status == "done":
                row.update({
                    "trades": detail.get("trade_count"),
                    "open": detail.get("open_count"),
                    "expR": detail.get("expectancy_r"),
                    "pf": detail.get("profit_factor"),
                    "win": detail.get("win_rate"),
                })
            else:
                row["error"] = str(detail)[:200]
            results.append(row)
            print("   ->", json.dumps(row, ensure_ascii=False))
    from pathlib import Path
    out_path = (Path(__file__).resolve().parents[1]
                / "docs/experiments/raw/exit_matrix/exit_matrix_results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=1))
    print("\n落盘:", out_path)


if __name__ == "__main__":
    main()
