"""BCD 重测 · 第二步 2.2：个股池 B/C/D/A 矩阵（handoff-bcd-retrial）。

池：docs/experiments/raw/bcd_retrial/stock_pool_symbols.txt 里在回测池就绪的
个股（>=300 根），symbols= 显式传参，不与 ETF 池混跑。费用 standard、
limit_guard=True、rr_min=None（与第一步 C 矩阵同口径）。

矩阵：
  C: v1/v2/v3 × {shrink, bias -15%, bias -25%, shrink+bias 两档, 无} × 退出两版
  B: {埋伏,突破} × {原生 126/2, 宽松 40/3} × {放量确认开/关} × 退出 {b3_dual, a6_3}
  D: {B1 默认 126/2, B1 放宽 63/3} × a6_3（D 原生失效=假跌破低点）
  A: 稳健档（cm=0.5/ta=1.0）× {shrink 开/关}（个股基准对照）

复活判据（事前定死）：
  C（样本充分类）：全池期望>0 且 OOS>0 且排 top3 后仍>0 且 N>=100
  B/D（稀疏形态类）：允许 N>=30，但 OOS>0 且排 top1 后不塌，标注「统计力弱」
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
RAW = ROOT / "docs" / "experiments" / "raw" / "bcd_retrial" / "stocks"
RAW.mkdir(parents=True, exist_ok=True)
POOL_FILE = ROOT / "docs" / "experiments" / "raw" / "bcd_retrial" / "stock_pool_symbols.txt"

sys.path.insert(0, str(ROOT / "scripts"))
from run_filters_round4 import _summarize  # type: ignore # noqa: E402

EXIT_SHORT = {"a6_1_costbasis": "cb", "a6_3_structure_stop": "ss", "b3_dual": "b3"}


def _fmt(v: float | None) -> str:
    return f"{v:+.3f}" if v is not None else "  -   "


def _stock_symbols() -> tuple[tuple[str, ...], dict[str, str]]:
    """就绪个股列表 + 每只有效起点（首次数据日）。"""
    from lei_signal.backtest import service as svc

    wanted = tuple(
        line.strip() for line in POOL_FILE.read_text().splitlines() if line.strip()
    )
    frames = svc._cached_frames()
    stocks = tuple(s for s in wanted if s in frames)
    starts = {s: str(frames[s].index[0].date()) for s in stocks}
    return stocks, starts


_STOCKS: tuple[str, ...] | None = None
_STARTS: dict[str, str] = {}


def _run(tag: str, extra: dict) -> None:
    fp = RAW / f"{tag}.json"
    if fp.exists():
        print(f"[skip] {tag}")
        return
    from lei_signal.backtest.service import BacktestParams, execute_run

    t0 = time.time()
    base = dict(
        rr_min=None,
        fee_label="standard",
        limit_guard=True,
    )
    base.update(extra)
    res = execute_run(BacktestParams(symbols=_STOCKS, **base))
    s = _summarize(res, tag)
    s["pool_symbols"] = list(_STOCKS)
    s["effective_starts"] = _STARTS
    fp.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
    ov = s["overview"]
    print(
        f"[done] {tag:<26s}  N={ov['trade_count'] or 0:>4}  "
        f"expR={_fmt(ov['expectancy_r'])}  PF={ov['profit_factor']}  "
        f"IS={_fmt(s['is_expectancy'])}({s['is_trade_count'] or 0})  "
        f"OOS={_fmt(s['oos_expectancy'])}({s['oos_trade_count'] or 0})  "
        f"top1={s['top1_symbol'] or '-'}  {time.time()-t0:.0f}s",
        flush=True,
    )


def stage_c() -> None:
    print("=== C × 乖离 × 缩量 × 退出两版（个股池）===", flush=True)
    filter_sets = [
        ("base", {}),
        ("shrink", {"volume_filter": "shrink"}),
        ("b15", {"bias_filter": -0.15}),
        ("b25", {"bias_filter": -0.25}),
        ("shb15", {"volume_filter": "shrink", "bias_filter": -0.15}),
        ("shb25", {"volume_filter": "shrink", "bias_filter": -0.25}),
    ]
    for version in ("v1", "v2", "v3"):
        for exit_variant in ("a6_1_costbasis", "a6_3_structure_stop"):
            for filt, extra in filter_sets:
                _run(
                    f"C_{version}_{EXIT_SHORT[exit_variant]}_{filt}",
                    {"module": "C", "entry_variant": version,
                     "exit_variant": exit_variant, **extra},
                )


def stage_b() -> None:
    print("=== B × 参数档 × 放量确认 × 退出（个股池）===", flush=True)
    param_sets = [
        ("nat", ()),  # 原生 126 / 2%
        ("loose", (("consolidation_bars", 40), ("cluster_threshold", 0.03))),
    ]
    for variant in ("ambush", "breakout"):
        for ptag, overrides in param_sets:
            for vc in (False, True):
                for exit_variant in ("b3_dual", "a6_3_structure_stop"):
                    _run(
                        f"B_{variant[:3]}_{ptag}_{'vc1' if vc else 'vc0'}"
                        f"_{EXIT_SHORT[exit_variant]}",
                        {
                            "module": "B",
                            "entry_variant": variant,
                            "exit_variant": exit_variant,
                            "overrides": overrides,
                            "volume_confirm": vc,
                            "volume_confirm_window": 1,  # 仅信号日（突破日量比>=2）
                        },
                    )


def stage_d() -> None:
    print("=== D × B1 档（个股池）===", flush=True)
    _run(
        "D_nat_ss",
        {"module": "D", "exit_variant": "a6_3_structure_stop"},
    )
    _run(
        "D_loose_ss",
        {
            "module": "D",
            "exit_variant": "a6_3_structure_stop",
            "overrides": (("consolidation_bars", 63), ("cluster_threshold", 0.03)),
        },
    )


def stage_a() -> None:
    print("=== A 稳健档基准对照（个股池）===", flush=True)
    stable = dict(
        module="A",
        entry_variant="early",
        exit_variant="a6_1_costbasis",
        overrides=(("clock_mult", 0.5), ("touch_atr", 1.0)),
    )
    _run("A_stocks_base", dict(stable))
    _run("A_stocks_shrink", dict(stable, volume_filter="shrink"))


def main() -> None:
    global _STOCKS, _STARTS  # noqa: PLW0603
    stages = sys.argv[1:] or ["c", "b", "d", "a"]
    _STOCKS, _STARTS = _stock_symbols()
    print(f"stock pool ready: {len(_STOCKS)} symbols", flush=True)
    if "c" in stages:
        stage_c()
    if "b" in stages:
        stage_b()
    if "d" in stages:
        stage_d()
    if "a" in stages:
        stage_a()


if __name__ == "__main__":
    main()
