"""任务三：指数本体 vs 对应 ETF 差异归因（A 稳健档）。"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
RAW = ROOT / "docs" / "experiments" / "raw" / "etf_expansion"
OUT = RAW / "index_vs_etf"
OUT.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT / "scripts"))
from run_backtest_grid import _summary_one  # type: ignore

PARAMS = dict(
    module="A",
    rr_min=None,
    entry_variant="early",
    exit_variant="a6_1_costbasis",
    fee_label="standard",
    limit_guard=True,
    overrides=(("clock_mult", 0.5), ("touch_atr", 1.0)),
)

PAIRS = [
    ("创业板", "159915.SZ", "399006.SZ"),
    ("沪深300", "510300.SS", "000300.SS"),
    ("标普500", "513500.SS", "^GSPC"),
]


def main() -> None:
    from lei_signal.backtest.service import BacktestParams, execute_run

    for label, etf, idx in PAIRS:
        for kind, sym in [("ETF", etf), ("指数", idx)]:
            tag = f"{label}_{kind}_{sym}".replace("^", "")
            fp = OUT / f"{tag}.json"
            if fp.exists():
                print(f"[skip] {tag}")
                continue
            t0 = time.time()
            res = execute_run(BacktestParams(**PARAMS, symbols=(sym,)))
            s = _summary_one(res)
            fp.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
            ov = s["overview"]
            is_e = s["is_expectancy"] if s["is_expectancy"] is not None else float("nan")
            oos_e = s["oos_expectancy"] if s["oos_expectancy"] is not None else float("nan")
            print(
                f"[done] {tag:<28s}  N={ov['trade_count'] or 0:>3}  expR={ov['expectancy_r'] if ov['expectancy_r'] is not None else float('nan'):+.3f}  "
                f"PF={ov['profit_factor']}  IS={is_e:+.3f}({s['is_trade_count'] or 0})  "
                f"OOS={oos_e:+.3f}({s['oos_trade_count'] or 0})  top1={s['top1_symbol'] or '-'}  "
                f"{time.time()-t0:.1f}s"
            )

        # 联合（不当独立样本叠加，只为查看合并表现）
        tag_pair = f"{label}_both".replace("^", "")
        fp = OUT / f"{tag_pair}.json"
        if fp.exists():
            print(f"[skip] {tag_pair}")
            continue
        t0 = time.time()
        res = execute_run(BacktestParams(**PARAMS, symbols=(etf, idx)))
        s = _summary_one(res)
        s["pair_note"] = "同资产两影子不独立；仅作合并展示"
        fp.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
        ov = s["overview"]
        is_e = s["is_expectancy"] if s["is_expectancy"] is not None else float("nan")
        oos_e = s["oos_expectancy"] if s["oos_expectancy"] is not None else float("nan")
        print(
            f"[done] {tag_pair:<28s}  N={ov['trade_count'] or 0:>3}  expR={ov['expectancy_r'] if ov['expectancy_r'] is not None else float('nan'):+.3f}  "
            f"PF={ov['profit_factor']}  IS={is_e:+.3f}({s['is_trade_count'] or 0})  "
            f"OOS={oos_e:+.3f}({s['oos_trade_count'] or 0})  top1={s['top1_symbol'] or '-'}  "
            f"{time.time()-t0:.1f}s"
        )


if __name__ == "__main__":
    main()
