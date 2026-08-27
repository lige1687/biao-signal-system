"""B 模块全谱参数 × 标的类型分组适配实验（handoff-b-adaptation 任务一）。

彪哥方向：参数可调是用来适配不同标的的。按 5 组各自独立扫全谱找最优档：
  宽基ETF(7) / 行业ETF(33) / A股指数(8) / 82只个股 / 美股ETF(3, IGV/SOXX/XLK)
参数空间（全谱）：
  consolidation_bars [20,30,40,63,90,126,180] × cluster_threshold
  [0.02,0.03,0.04,0.05,0.06,0.08,0.10] = 49 档
每档 × 2 退出(b3_dual/a6_3) × 2 量能(vc0/vc1) × breakout = 196 组/组；
ambush 附带（b3_dual × vc0 × 49 档）；另跑 5 组并集「全池」b3_dual×vc0 全谱
49 档（作为「全池一套参数」基线，供适配增量对比）。

方法纪律（防过拟合红线）：按组选最优、绝不按单标的选；组内最优须
OOS>0、排 top1 后不塌、N>=30（不足 30 标「样本不足」不参与排名）。
口径：rr_min=None、fee=standard、limit_guard=True、volume_confirm_window=1。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
RAW = ROOT / "docs" / "experiments" / "raw" / "b_adaptation"
RAW.mkdir(parents=True, exist_ok=True)
POOL_FILE = ROOT / "docs" / "experiments" / "raw" / "bcd_retrial" / "stock_pool_symbols.txt"

sys.path.insert(0, str(ROOT / "scripts"))
from run_filters_round4 import _summarize  # type: ignore # noqa: E402

EXIT_SHORT = {"b3_dual": "b3", "a6_3_structure_stop": "ss"}

# ---- 标的分组（与既往轮次同口径） ----
POOL_BROAD = (
    "510050.SS", "510300.SS", "510500.SS", "512100.SS",
    "159901.SZ", "159915.SZ", "588000.SS",
)
POOL_INDUSTRY = (
    "512000.SS", "512010.SS", "512170.SS", "512200.SS", "512400.SS",
    "512480.SS", "512580.SS", "512660.SS", "512690.SS", "512760.SS",
    "512800.SS", "512890.SS", "512980.SS", "515030.SS", "515050.SS",
    "515130.SS", "515170.SS", "515210.SS", "515220.SS", "515300.SS",
    "515790.SS", "515880.SS", "516010.SS", "516220.SS", "516510.SS",
    "518850.SS", "562590.SS", "159611.SZ", "159819.SZ", "159825.SZ",
    "159865.SZ", "159928.SZ", "159992.SZ",
)
POOL_INDEX = (
    "000001.SS", "000001.SZ", "000016.SS", "000300.SS", "000688.SS",
    "000698.SZ", "000905.SS", "399006.SZ",
)
POOL_US = ("IGV", "SOXX", "XLK")


def _stock_symbols() -> tuple[str, ...]:
    from lei_signal.backtest import service as svc

    wanted = tuple(
        line.strip() for line in POOL_FILE.read_text().splitlines() if line.strip()
    )
    frames = svc._cached_frames()
    return tuple(s for s in wanted if s in frames)


GROUPS: dict[str, tuple[str, ...]] = {
    "宽基ETF": POOL_BROAD,
    "行业ETF": POOL_INDUSTRY,
    "A股指数": POOL_INDEX,
    "个股": (),          # main() 里填充
    "美股ETF": POOL_US,
}

# ---- 全谱参数空间 ----
CB_LEVELS = (20, 30, 40, 63, 90, 126, 180)
CL_LEVELS = (0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10)


def _cl_tag(cl: float) -> str:
    return f"cl{round(cl * 100):02d}"


def _fmt(v: float | None) -> str:
    return f"{v:+.3f}" if v is not None else "  -   "


def _run(tag: str, group: str, symbols: tuple[str, ...], extra: dict) -> None:
    fp = RAW / f"{tag}__{group}.json"
    if fp.exists():
        return
    from lei_signal.backtest.service import BacktestParams, execute_run

    t0 = time.time()
    res = execute_run(BacktestParams(symbols=symbols, **extra))
    s = _summarize(res, tag)
    s["pool_symbols"] = list(symbols)
    fp.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
    ov = s["overview"]
    print(
        f"[done] {group:<5s} {tag:<30s}  N={ov['trade_count'] or 0:>4}  "
        f"expR={_fmt(ov['expectancy_r'])}  IS={_fmt(s['is_expectancy'])}  "
        f"OOS={_fmt(s['oos_expectancy'])}  top1={s['top1_symbol'] or '-'}  "
        f"{time.time() - t0:.0f}s",
        flush=True,
    )


def main() -> None:
    GROUPS["个股"] = _stock_symbols()
    union = tuple(
        s for g in ("宽基ETF", "行业ETF", "A股指数", "个股", "美股ETF")
        for s in GROUPS[g]
    )
    print(
        "groups: " + ", ".join(f"{g}({len(v)})" for g, v in GROUPS.items())
        + f", 全池({len(union)})",
        flush=True,
    )
    base = dict(
        rr_min=None,
        fee_label="standard",
        limit_guard=True,
        volume_confirm_window=1,
    )
    # 阶段顺序：主轴先行（breakout × b3 × vc0 各组跑完即可出热力表初稿）
    stages = (
        ("breakout", "b3_dual", False),
        ("breakout", "b3_dual", True),
        ("breakout", "a6_3_structure_stop", False),
        ("breakout", "a6_3_structure_stop", True),
        ("ambush", "b3_dual", False),
    )
    for variant, exit_variant, vc in stages:
        print(
            f"=== {variant} × {EXIT_SHORT[exit_variant]} × {'vc1' if vc else 'vc0'} ===",
            flush=True,
        )
        for cb in CB_LEVELS:
            for cl in CL_LEVELS:
                tag = (
                    f"B_{variant[:3]}_cb{cb}_{_cl_tag(cl)}_"
                    f"{EXIT_SHORT[exit_variant]}_{'vc1' if vc else 'vc0'}"
                )
                extra = dict(
                    base,
                    module="B",
                    entry_variant=variant,
                    exit_variant=exit_variant,
                    volume_confirm=vc,
                    overrides=(("consolidation_bars", cb), ("cluster_threshold", cl)),
                )
                for group, symbols in GROUPS.items():
                    _run(tag, group, symbols, extra)
    # 全池基线（一套参数视角）：breakout × b3_dual × vc0 × 49 档
    print("=== 全池(5组并集) × b3 × vc0 ===", flush=True)
    for cb in CB_LEVELS:
        for cl in CL_LEVELS:
            tag = f"ALL_bre_cb{cb}_{_cl_tag(cl)}_b3_vc0"
            extra = dict(
                base,
                module="B",
                entry_variant="breakout",
                exit_variant="b3_dual",
                volume_confirm=False,
                overrides=(("consolidation_bars", cb), ("cluster_threshold", cl)),
            )
            _run(tag, "全池", union, extra)


if __name__ == "__main__":
    main()
