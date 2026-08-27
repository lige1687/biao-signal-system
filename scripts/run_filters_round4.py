"""第四轮过滤器增量实验：量能 / 筹码 / trend_stage 分组 / 缺口（动能 + 目标档）。

基线 = A 稳健档（cm=0.5、ta=1.0、无 RR 门槛，etf-expansion 同口径）。
两个池：全池（symbols=None，180 标的）与 A股ETF（20 标的，round4 分组口径）。

实验矩阵（每格落一个 JSON，已存在则跳过）：
  baseline          过滤器全关（对照，应复现既有结论）
  E1  vol1 / vol5   量能确认（窗口 1 / 5）
  E2  prof_*        筹码峰（poc_support / vacuum / both）
  E4a gapmom        缺口动能过滤（近 10 日未回补向上缺口）
  E4b rr3 / rr3_gap RR 门槛 3.0 下缺口目标档开/关（通过率与期望变化）

E3（trend_stage 分组 + 周线引力）不新增跑：baseline 的
「趋势五步（入场时 stage）」「大周期（周线环境）」分组即载体。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
RAW = ROOT / "docs" / "experiments" / "raw" / "filters_round4"
RAW.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT / "scripts"))
from run_backtest_grid import _summary_one  # type: ignore # noqa: E402

# A 稳健档（round2/round3 结论，etf-expansion 同口径）
PARAMS = dict(
    module="A",
    rr_min=None,
    entry_variant="early",
    exit_variant="a6_1_costbasis",
    fee_label="standard",
    limit_guard=True,
    overrides=(("clock_mult", 0.5), ("touch_atr", 1.0)),
)

POOL_ETF = (
    "159165.SZ", "159652.SZ", "159915.SZ", "159995.SZ",
    "510300.SS", "512400.SS", "512480.SS", "512760.SS", "512890.SS",
    "513870.SS", "515050.SS", "515130.SS", "515170.SS", "515300.SS",
    "515880.SS", "516220.SS", "518850.SS", "560390.SS", "562590.SS", "588000.SS",
)
POOLS: dict[str, tuple[str, ...] | None] = {"A股ETF": POOL_ETF, "全池": None}


def _extra_groups(g: dict) -> dict:
    """抽 E3/E4 归因要用的分组：趋势五步 + 大周期（周线引力）。"""
    stage = {
        s["label"]: {
            "expectancy_r": s["expectancy_r"],
            "profit_factor": s["profit_factor"],
            "trade_count": s["trade_count"],
            "total_r": s["total_r"],
        }
        for s in g.get("趋势五步（入场时 stage）", [])
    }
    weekly = {
        s["label"]: {
            "expectancy_r": s["expectancy_r"],
            "profit_factor": s["profit_factor"],
            "trade_count": s["trade_count"],
            "total_r": s["total_r"],
        }
        for s in g.get("大周期（周线环境）", [])
    }
    return {"trend_stage": stage, "weekly_env": weekly}


def _summarize(result: dict, tag: str) -> dict:
    s = _summary_one(result)
    s["tag"] = tag
    s["trend_stage_groups"] = _extra_groups(result["groups"]["True"])["trend_stage"]
    s["weekly_env_groups"] = _extra_groups(result["groups"]["True"])["weekly_env"]
    # E2 逐笔归因 + E4b 缺口救回归因需要明细（symbol+signal_date 为主键）
    s["trades_detail"] = [
        {
            "symbol": t["symbol"],
            "signal_date": t["signal_date"],
            "entry_date": t["entry_date"],
            "ma_period": t["ma_period"],
            "trend_stage": t["trend_stage"],
            "benchmark_clock_type": t["benchmark_clock_type"],
            "reward_risk": t["reward_risk"],
            "r_net": t["r_net"],
            "exit_reason": t["exit_reason"],
            "holding_bars": t["holding_bars"],
        }
        for t in result["trades"]
    ]
    return s


def _fmt(v: float | None) -> str:
    return f"{v:+.3f}" if v is not None else "  -   "


def _run(tag: str, pool: str, extra: dict) -> None:
    fp = RAW / f"{tag}__{pool}.json"
    if fp.exists():
        print(f"[skip] {tag}__{pool}")
        return
    from lei_signal.backtest.service import BacktestParams, execute_run

    t0 = time.time()
    syms = POOLS[pool]
    params = dict(PARAMS)
    params.update(extra)
    res = execute_run(
        BacktestParams(symbols=tuple(syms) if syms else None, **params)
    )
    s = _summarize(res, tag)
    fp.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
    ov = s["overview"]
    is_e = s["is_expectancy"]
    oos_e = s["oos_expectancy"]
    print(
        f"[done] {tag}__{pool:<7s}  N={ov['trade_count'] or 0:>4}  "
        f"expR={_fmt(ov['expectancy_r'])}  PF={ov['profit_factor']}  "
        f"IS={_fmt(is_e)}({s['is_trade_count'] or 0})  "
        f"OOS={_fmt(oos_e)}({s['oos_trade_count'] or 0})  "
        f"top1={s['top1_symbol'] or '-'}  {time.time()-t0:.0f}s"
    )


def main() -> None:
    stages = sys.argv[1:] or ["base", "e1", "e2_etf", "e4a", "e4b", "e2_all"]

    if "base" in stages:
        print("=== baseline：过滤器全关（两池）===")
        for pool in POOLS:
            _run("baseline", pool, {})

    if "e1" in stages:
        print("=== E1 量能确认：开（窗口 1 / 5）===")
        for pool in POOLS:
            _run("vol1", pool, {"volume_confirm": True, "volume_confirm_window": 1})
            _run("vol5", pool, {"volume_confirm": True, "volume_confirm_window": 5})

    if "e4a" in stages:
        print("=== E4a 缺口动能过滤：开（近 10 日未回补向上缺口）===")
        for pool in POOLS:
            _run("gapmom", pool, {"gap_momentum": True})

    if "e4b" in stages:
        print("=== E4b RR 门槛 3.0 下缺口目标档开/关 ===")
        for pool in POOLS:
            _run("rr3", pool, {"rr_min": 3.0})
            _run("rr3_gap", pool, {"rr_min": 3.0, "gap_target": True})

    if "e2_etf" in stages:
        print("=== E2 筹码峰：先单池（A股ETF）验证性能 ===")
        for mode in ("poc_support", "vacuum", "both"):
            _run(f"prof_{mode}", "A股ETF", {"profile_filter": mode})

    if "e2_all" in stages:
        print("=== E2 筹码峰：全池 ===")
        for mode in ("poc_support", "vacuum", "both"):
            _run(f"prof_{mode}", "全池", {"profile_filter": mode})


if __name__ == "__main__":
    main()
