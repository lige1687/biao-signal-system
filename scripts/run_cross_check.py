"""第 3 轮：B/A 最优点样本外 + 集中度 + 排除头部标的复核。

为每个候选点跑两个变体：
  1) 全池（与第 1/2 轮落盘一致，作为基准）
  2) 排除头部 1 标的（top1）
复核口径：
  - 全池 IS / OOS 期望与笔数
  - 去 top1 后的总 R、IS、OOS、PF
  - 分年份 + 牛/熊/横盘分布
"""
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

# 候选最优点（来自第 1/2 轮汇总）
# (label, module, overrides, entry_variant, exclude)
CANDIDATES = [
    # B 突破版
    ("B_cb40_cl05", "B", (("consolidation_bars", 40), ("cluster_threshold", 0.05)), "breakout", "IGV"),
    ("B_cb40_cl03", "B", (("consolidation_bars", 40), ("cluster_threshold", 0.03)), "breakout", "IGV"),
    # A 模块
    ("A_cm10_ta10_rr4", "A", (("clock_mult", 1.0), ("touch_atr", 1.0)), "early", "518850.SS"),
    ("A_cm10_ta15_rr4", "A", (("clock_mult", 1.0), ("touch_atr", 1.5)), "early", "518850.SS"),
    ("A_cm05_ta10_rrNone", "A", (("clock_mult", 0.5), ("touch_atr", 1.0)), "early", "TH881114.SECTOR"),
    # 排除版 B 也要做：cb=63 / cb=90（IS 翻负的点）排除 IGV 后是真正检验
    ("B_cb63_cl03", "B", (("consolidation_bars", 63), ("cluster_threshold", 0.03)), "breakout", "IGV"),
    ("B_cb90_cl03", "B", (("consolidation_bars", 90), ("cluster_threshold", 0.03)), "breakout", "IGV"),
    # 对照：B 126/2（默认参数已知最差）排除 IGV
    ("B_cb126_cl02", "B", (("consolidation_bars", 126), ("cluster_threshold", 0.02)), "breakout", "IGV"),
]


def _pool_minus(exclude: str) -> tuple[str, ...]:
    from lei_signal.backtest.runner import load_pool_frames  # noqa: WPS433

    frames = load_pool_frames()
    syms = [s for s in frames.keys() if s != exclude]
    return tuple(sorted(syms))


def main() -> None:
    from lei_signal.backtest.service import BacktestParams, execute_run

    for label, mod, ov, ev, exclude in CANDIDATES:
        for variant in ("full", "no_top1"):
            tag = f"{label}__{variant}"
            fp = OUT / f"{tag}.json"
            if fp.exists():
                print(f"[skip] {tag} 已有")
                continue
            t0 = time.time()
            if variant == "full":
                symbols = None
            else:
                symbols = _pool_minus(exclude)
            params = BacktestParams(
                module=mod,
                symbols=symbols,
                rr_min=None,
                entry_variant=ev,
                exit_variant="a6_1_costbasis",
                fee_label="standard",
                limit_guard=True,
                overrides=tuple(ov),
            )
            res = execute_run(params)
            s = _summary_one(res)
            s["variant"] = variant
            s["exclude"] = exclude
            s["candidate"] = label
            fp.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
            ov2 = s["overview"]
            print(
                f"[done] {tag}  N={ov2['trade_count'] or 0:>3}  expR={ov2['expectancy_r'] if ov2['expectancy_r'] is not None else float('nan'):+.3f}  "
                f"PF={ov2['profit_factor']}  IS={s['is_expectancy']:+.3f}({s['is_trade_count'] or 0})  "
                f"OOS={s['oos_expectancy']:+.3f}({s['oos_trade_count'] or 0})  "
                f"top1={s['top1_symbol'] or '-'}  "
                f"{time.time()-t0:.1f}s"
            )


if __name__ == "__main__":
    main()
