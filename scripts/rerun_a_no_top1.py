"""第 3 轮补充：A 候选点用真正 top1 排除后重跑。"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
RAW = ROOT / "docs" / "experiments" / "raw"
OUT = RAW / "cross_check"
OUT.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT / "scripts"))
from run_backtest_grid import _summary_one  # type: ignore

# 用真正 top1 排除（前一轮已扫到具体值）
RERUN = [
    ("A_cm10_ta10_rr4", "A", (("clock_mult", 1.0), ("touch_atr", 1.0)), "early", "159652.SZ", 4.0),
    ("A_cm10_ta15_rr4", "A", (("clock_mult", 1.0), ("touch_atr", 1.5)), "early", "TH881129.SECTOR", 4.0),
    # 加一组：cm=1.0/ta=1.0/rr=3（候选对照）排除 top1
    ("A_cm10_ta10_rr3", "A", (("clock_mult", 1.0), ("touch_atr", 1.0)), "early", "518850.SS", 3.0),
    ("A_cm10_ta15_rr3", "A", (("clock_mult", 1.0), ("touch_atr", 1.5)), "early", "515130.SS", 3.0),
]


def _pool_minus(exclude: str) -> tuple[str, ...]:
    from lei_signal.backtest.runner import load_pool_frames

    frames = load_pool_frames()
    return tuple(sorted(s for s in frames.keys() if s != exclude))


def main() -> None:
    from lei_signal.backtest.service import BacktestParams, execute_run

    for label, mod, ov, ev, exclude, rr in RERUN:
        tag = f"{label}__no_top1_v2"
        fp = OUT / f"{tag}.json"
        if fp.exists():
            print(f"[skip] {tag}")
            continue
        t0 = time.time()
        params = BacktestParams(
            module=mod,
            symbols=_pool_minus(exclude),
            rr_min=rr,
            entry_variant=ev,
            exit_variant="a6_1_costbasis",
            fee_label="standard",
            limit_guard=True,
            overrides=tuple(ov),
        )
        res = execute_run(params)
        s = _summary_one(res)
        s["variant"] = "no_top1_v2"
        s["exclude"] = exclude
        s["candidate"] = label
        fp.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
        ov2 = s["overview"]
        print(
            f"[done] {tag}  N={ov2['trade_count'] or 0:>4}  expR={ov2['expectancy_r'] if ov2['expectancy_r'] is not None else float('nan'):+.3f}  "
            f"PF={ov2['profit_factor']}  IS={s['is_expectancy']:+.3f}({s['is_trade_count'] or 0})  "
            f"OOS={s['oos_expectancy']:+.3f}({s['oos_trade_count'] or 0})  "
            f"top1={s['top1_symbol'] or '-'}  {time.time()-t0:.1f}s"
        )


if __name__ == "__main__":
    main()
