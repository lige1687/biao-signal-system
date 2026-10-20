"""缩量回调过滤器全套纪律验证（补充 handoff：shrink-filter）。

口径：shrink(t) = 近3日均量 < 前3日均量（账本 volume_proxies 2.1.0 窗口，
t=信号日）。基线 = A 稳健档，与第四轮同口径。

实验矩阵（每格一 JSON，已存在则跳过）：
  1. 联合矩阵（两池）：none / shrink / vacuum / shrink+vacuum
  2. 敏感性（全池）：5/3、2/5 窗口变体；vr<0.7、vr<0.6 严格档
  3. 分标的类型：宽基ETF / 行业ETF / 指数本体 × (baseline + shrink)

对照锚点：主理人预检「缩量组 815 笔 +0.831R vs 非缩量 873 笔 +0.223R」
（全池）--shrink 全池跑应复现此数字。
全部结论待 walk-forward 终审（walk-forward 框架另轮实施）。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
RAW = ROOT / "docs" / "experiments" / "raw" / "shrink_filter"
RAW.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT / "scripts"))
from run_filters_round4 import PARAMS, POOL_ETF, _summarize  # type: ignore # noqa: E402

# 分标的类型池（etf-expansion 同口径）
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
SYM_POOLS: dict[str, tuple[str, ...]] = {
    "宽基ETF": POOL_BROAD,
    "行业ETF": POOL_INDUSTRY,
    "指数本体": POOL_INDEX,
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
    params = dict(PARAMS)
    params.update(extra)
    res = execute_run(BacktestParams(symbols=symbols, **params))
    s = _summarize(res, tag)
    fp.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
    ov = s["overview"]
    print(
        f"[done] {tag}__{pool_label:<7s}  N={ov['trade_count'] or 0:>4}  "
        f"expR={_fmt(ov['expectancy_r'])}  PF={ov['profit_factor']}  "
        f"IS={_fmt(s['is_expectancy'])}({s['is_trade_count'] or 0})  "
        f"OOS={_fmt(s['oos_expectancy'])}({s['oos_trade_count'] or 0})  "
        f"top1={s['top1_symbol'] or '-'}  {time.time()-t0:.0f}s"
    )


def main() -> None:
    stages = sys.argv[1:] or ["matrix", "sens", "symtype"]

    if "matrix" in stages:
        print("=== 联合矩阵：none / shrink / vacuum / shrink+vacuum（两池）===")
        for pool, syms in (("A股ETF", POOL_ETF), ("全池", None)):
            _run("baseline", syms, {}, pool)
            _run("shrink", syms, {"volume_filter": "shrink"}, pool)
            _run("vacuum", syms, {"profile_filter": "vacuum"}, pool)
            _run(
                "shrink_vacuum", syms,
                {"volume_filter": "shrink", "profile_filter": "vacuum"}, pool,
            )

    if "sens" in stages:
        print("=== 敏感性（全池）：窗口变体 + 严格档 ===")
        _run("shrink_5_3", None, {
            "volume_filter": "shrink", "shrink_recent": 5, "shrink_prior": 3,
        }, "全池")
        _run("shrink_2_5", None, {
            "volume_filter": "shrink", "shrink_recent": 2, "shrink_prior": 5,
        }, "全池")
        _run("shrink_vr70", None, {
            "volume_filter": "shrink", "volume_filter_vr_max": 0.7,
        }, "全池")
        _run("shrink_vr60", None, {
            "volume_filter": "shrink", "volume_filter_vr_max": 0.6,
        }, "全池")

    if "symtype" in stages:
        print("=== 分标的类型：宽基ETF / 行业ETF / 指数本体 ===")
        for name, syms in SYM_POOLS.items():
            _run("baseline", syms, {}, name)
            _run("shrink", syms, {"volume_filter": "shrink"}, name)


if __name__ == "__main__":
    main()
