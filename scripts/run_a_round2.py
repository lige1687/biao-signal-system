"""A 模块收紧实验：clock_mult × touch_atr × rr_min 18 组合批跑。"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
RAW = ROOT / "docs" / "experiments" / "raw"
OUT = RAW / "A_round2"
OUT.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT / "scripts"))
from run_backtest_grid import _summary_one  # type: ignore


def main() -> None:
    from lei_signal.backtest.service import BacktestParams, execute_run

    grid = []
    for cm in (0.5, 1.0):
        for ta in (0.5, 1.0, 1.5):
            for rr in (None, 3.0, 4.0):
                grid.append((cm, ta, rr))

    rows = []
    for cm, ta, rr in grid:
        rr_tag = "None" if rr is None else f"{rr:.1f}"
        tag = f"cm{int(cm*10):02d}_ta{int(ta*10)}_rr{rr_tag.replace('.', '_')}"
        fp = OUT / f"{tag}.json"
        if fp.exists():
            print(f"[skip] {tag} 已有")
            rows.append(json.loads(fp.read_text(encoding="utf-8")))
            continue
        t0 = time.time()
        res = execute_run(
            BacktestParams(
                module="A",
                symbols=None,
                rr_min=rr,
                entry_variant="early",
                exit_variant="a6_1_costbasis",
                fee_label="standard",
                limit_guard=True,
                overrides=(("clock_mult", cm), ("touch_atr", ta)),
            )
        )
        s = _summary_one(res)
        fp.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
        rows.append(s)
        ov = s["overview"]
        is_exp = s["is_expectancy"] if s["is_expectancy"] is not None else float("nan")
        oos_exp = s["oos_expectancy"] if s["oos_expectancy"] is not None else float("nan")
        print(
            f"[done] {tag}  N={ov['trade_count']:>4}  expR={ov['expectancy_r']:+.3f}  "
            f"PF={ov['profit_factor']}  IS={is_exp:+.3f}({s['is_trade_count'] or 0})  "
            f"OOS={oos_exp:+.3f}({s['oos_trade_count'] or 0})  "
            f"{time.time()-t0:.1f}s"
        )

    (OUT / "_grid.json").write_text(
        json.dumps({"grid": [list(g) for g in grid], "cells": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
