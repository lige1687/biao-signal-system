"""任务四：B cb=40/cl=5% 在半导体/通信/AI 行业 ETF 集群上复核。"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
RAW = ROOT / "docs" / "experiments" / "raw" / "etf_expansion"
OUT = RAW / "B_industry"
OUT.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT / "scripts"))
from run_backtest_grid import _summary_one  # type: ignore

# 半导体 / 通信 / AI 行业 ETF 集群
CLUSTERS = {
    "半导体国联安": ["512480.SS"],
    "半导体华夏": ["512760.SS"],
    "半导体深证": ["159995.SZ"],
    "5G通信": ["515050.SS"],
    "通信": ["515880.SS"],
    "人工智能": ["159819.SZ"],
    "半导体组合": ["512480.SS", "512760.SS", "159995.SZ", "515050.SS", "515880.SS", "159819.SZ"],
    "半导体组合去IGV": ["512480.SS", "512760.SS", "159995.SZ", "515050.SS", "515880.SS", "159819.SZ"],
}

PARAMS_BASE = dict(
    module="B",
    rr_min=None,
    entry_variant="breakout",
    exit_variant="a6_1_costbasis",
    fee_label="standard",
    limit_guard=True,
)


def main() -> None:
    from lei_signal.backtest.service import BacktestParams, execute_run

    for label, syms in CLUSTERS.items():
        for cb, cl in [(40, 0.05), (40, 0.03), (126, 0.02)]:
            tag = f"{label}__cb{cb}_cl{int(cl*100):02d}"
            fp = OUT / f"{tag}.json"
            if fp.exists():
                print(f"[skip] {tag}")
                continue
            t0 = time.time()
            res = execute_run(BacktestParams(
                **PARAMS_BASE,
                symbols=tuple(syms),
                overrides=(("consolidation_bars", cb), ("cluster_threshold", cl)),
            ))
            s = _summary_one(res)
            fp.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
            ov = s["overview"]
            is_e = s["is_expectancy"] if s["is_expectancy"] is not None else float("nan")
            oos_e = s["oos_expectancy"] if s["oos_expectancy"] is not None else float("nan")
            print(
                f"[done] {tag:<32s}  N={ov['trade_count'] or 0:>3}  expR={ov['expectancy_r'] if ov['expectancy_r'] is not None else float('nan'):+.3f}  "
                f"PF={ov['profit_factor']}  IS={is_e:+.3f}({s['is_trade_count'] or 0})  "
                f"OOS={oos_e:+.3f}({s['oos_trade_count'] or 0})  top1={s['top1_symbol'] or '-'}  "
                f"{time.time()-t0:.1f}s"
            )


if __name__ == "__main__":
    main()
