"""BCD 公平重测 · 第一步：C × 过滤器矩阵（handoff-bcd-retrial）。

问题：缩量/真空过滤器能否把 C（2B 破底翻）从零轴劈开？
C 原判决：全池 3800+ 笔、扣费后期望 +0.12 -- 真打平，无肉。

矩阵：C v1/v2/v3 × {shrink 开/关} × {vacuum 开/关}（12 配置）
      × 退出两版（a6_1_costbasis / a6_3_structure_stop=C 原生失效）= 24 配置
      × 三口径（A股ETF 20 / 行业ETF 33 / 全池）= 72 跑。

口径与缩量轮一致：rr_min=None、fee=standard、limit_guard=True、
无参数覆盖（two_b_reclaim_bars 默认 5）。每格一 JSON（已存在跳过）。
复活判据（事前定死）：全池期望>0 且 OOS>0 且排 top3 后仍>0 且 N≥100。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
RAW = ROOT / "docs" / "experiments" / "raw" / "bcd_retrial" / "c_matrix"
RAW.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT / "scripts"))
from run_filters_round4 import _summarize  # type: ignore # noqa: E402
from run_shrink_filter import POOL_ETF, POOL_INDUSTRY  # type: ignore # noqa: E402

POOLS: dict[str, tuple[str, ...] | None] = {
    "A股ETF": POOL_ETF,
    "行业ETF": POOL_INDUSTRY,
    "全池": None,
}

EXIT_SHORT = {"a6_1_costbasis": "cb", "a6_3_structure_stop": "ss"}
FILT_SHORT = {
    "": "base",
    "shrink": "shrink",
    "vacuum": "vacuum",
    "shrink+vacuum": "shvac",
}


def _fmt(v: float | None) -> str:
    return f"{v:+.3f}" if v is not None else "  -   "


def _run(tag: str, symbols: tuple[str, ...] | None, extra: dict, pool_label: str) -> None:
    fp = RAW / f"{tag}__{pool_label}.json"
    if fp.exists():
        print(f"[skip] {tag}__{pool_label}")
        return
    from lei_signal.backtest.service import BacktestParams, execute_run

    t0 = time.time()
    base = dict(
        module="C",
        rr_min=None,
        fee_label="standard",
        limit_guard=True,
        overrides=(),
    )
    base.update(extra)
    res = execute_run(BacktestParams(symbols=symbols, **base))
    s = _summarize(res, tag)
    fp.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
    ov = s["overview"]
    print(
        f"[done] {tag}__{pool_label:<6s}  N={ov['trade_count'] or 0:>4}  "
        f"expR={_fmt(ov['expectancy_r'])}  PF={ov['profit_factor']}  "
        f"IS={_fmt(s['is_expectancy'])}({s['is_trade_count'] or 0})  "
        f"OOS={_fmt(s['oos_expectancy'])}({s['oos_trade_count'] or 0})  "
        f"top1={s['top1_symbol'] or '-'}  {time.time()-t0:.0f}s",
        flush=True,
    )


def main() -> None:
    stages = sys.argv[1:] or ["matrix"]
    if "matrix" not in stages:
        return

    filter_sets = [
        ("", {}),
        ("shrink", {"volume_filter": "shrink"}),
        ("vacuum", {"profile_filter": "vacuum"}),
        ("shrink+vacuum", {"volume_filter": "shrink", "profile_filter": "vacuum"}),
    ]
    for pool, syms in POOLS.items():
        for version in ("v1", "v2", "v3"):
            for exit_variant in ("a6_1_costbasis", "a6_3_structure_stop"):
                for filt_name, extra in filter_sets:
                    tag = f"C_{version}_{EXIT_SHORT[exit_variant]}_{FILT_SHORT[filt_name]}"
                    _run(tag, syms, {**extra, "entry_variant": version,
                                     "exit_variant": exit_variant}, pool)


if __name__ == "__main__":
    main()
