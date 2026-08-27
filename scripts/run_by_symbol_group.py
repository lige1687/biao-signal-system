"""第 4 轮：候选最优点在 4 个标的分组上分别跑，检验参数是否随池子类型漂移。"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
RAW = ROOT / "docs" / "experiments" / "raw"
OUT = RAW / "by_symbol_group"
OUT.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT / "scripts"))
from run_backtest_grid import _summary_one  # type: ignore

GROUPS = {
    "A股指数": (
        "000001.SS", "000001.SZ", "000300.SS", "000688.SS", "000698.SZ",
    ),
    "美股/港股/韩国指数": (
        "^GSPC", "^IXIC", "^HSI", "^HSTECH", "^KS11",
    ),
    "A股ETF": (
        "159165.SZ", "159652.SZ", "159915.SZ", "159995.SZ",
        "510300.SS", "512400.SS", "512480.SS", "512760.SS", "512890.SS",
        "513870.SS", "515050.SS", "515130.SS", "515170.SS", "515300.SS",
        "515880.SS", "516220.SS", "518850.SS", "560390.SS", "562590.SS", "588000.SS",
    ),
    "申万行业板块": tuple(
        f"TH881{s}.SECTOR" for s in (
            "102", "109", "114", "121", "129", "134", "145", "155", "156", "157",
            "168", "169", "170", "267", "272", "273", "278", "279", "280", "281",
        )
    ),
    "美股行业ETF": ("XLK", "IGV", "SOXX"),
    "A股个股": ("600519.SS", "002555.SZ"),
}

# 候选：稳健冠军 + 高赔率三档 + B 对照
CANDIDATES = [
    ("A_cm05_ta10_rrNone", "A", (("clock_mult", 0.5), ("touch_atr", 1.0)), "early", None),
    ("A_cm10_ta10_rr4", "A", (("clock_mult", 1.0), ("touch_atr", 1.0)), "early", 4.0),
    ("A_cm10_ta15_rr4", "A", (("clock_mult", 1.0), ("touch_atr", 1.5)), "early", 4.0),
    ("B_cb40_cl05", "B", (("consolidation_bars", 40), ("cluster_threshold", 0.05)), "breakout", None),
    ("B_cb40_cl03", "B", (("consolidation_bars", 40), ("cluster_threshold", 0.03)), "breakout", None),
]


def main() -> None:
    from lei_signal.backtest.service import BacktestParams, execute_run

    for cand_label, mod, ov, ev, rr in CANDIDATES:
        for grp_name, syms in GROUPS.items():
            tag = f"{cand_label}__{grp_name}".replace("/", "_")
            fp = OUT / f"{tag}.json"
            if fp.exists():
                print(f"[skip] {tag}")
                continue
            t0 = time.time()
            try:
                res = execute_run(
                    BacktestParams(
                        module=mod,
                        symbols=syms,
                        rr_min=rr,
                        entry_variant=ev,
                        exit_variant="a6_1_costbasis",
                        fee_label="standard",
                        limit_guard=True,
                        overrides=tuple(ov),
                    )
                )
            except ValueError as e:
                print(f"[skip] {tag}  {e}")
                fp.write_text(json.dumps({"error": str(e)}, ensure_ascii=False), encoding="utf-8")
                continue
            s = _summary_one(res)
            s["candidate"] = cand_label
            s["group"] = grp_name
            fp.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
            ov2 = s["overview"]
            is_e = s["is_expectancy"] if s["is_expectancy"] is not None else float("nan")
            oos_e = s["oos_expectancy"] if s["oos_expectancy"] is not None else float("nan")
            exp_e = ov2["expectancy_r"] if ov2["expectancy_r"] is not None else float("nan")
            print(
                f"[done] {tag}  N={ov2['trade_count'] or 0:>4}  expR={exp_e:+.3f}  "
                f"PF={ov2['profit_factor']}  IS={is_e:+.3f}({s['is_trade_count'] or 0})  "
                f"OOS={oos_e:+.3f}({s['oos_trade_count'] or 0})  "
                f"{time.time()-t0:.1f}s"
            )


if __name__ == "__main__":
    main()
