#!/usr/bin/env python3
"""B200 宽度牛熊口径 vs 沪深300/标普 时钟口径（任务三，handoff-stage-b200）。

口径：
- B200 = market_breadth_snapshots 的 breadth_200（站上 200 日均线的成分占比%，
  data_status='complete'）。注意：handoff 所指 coverage/eligible 列实测为
  数据覆盖率（逐年单调升、危机中不下滑），已纠正为 breadth_200；
  按 as_of <= 信号日对齐（取最近一个已知值，无未来函数）；
- 档位：coverage > bull_thr 为牛、< bear_thr 为熊、其间为横；
  基准档 60/40，扫描 bull∈{55,60,65}% × bear∈{35,40,45}% 共 9 档；
- 时钟口径 = trades 自带 benchmark_clock_type（1,2=牛 3=横 4,5=熊）。

判定（事前写死）：B200 口径可用 =
  (a) 同池同信号的牛熊组期望分离度 |exp(牛)-exp(熊)| >= 时钟口径，且
  (b) 2026 段 B200 能提前/更准标记 A 的失效段（月末值口径下月预警：
      上月末 B200=熊 的月份，本月 A 是否失血；命中数/误报数对照时钟口径）。

用法：python3 scripts/run_b200_regime.py [us|cn|both]
产出：docs/experiments/raw/stage_b200/b200_regime_summary.json
"""
from __future__ import annotations

import json
import sqlite3
import sys
from bisect import bisect_right
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

RAW = REPO / "docs/experiments/raw/stage_b200"
BENCHMARK_CN, BENCHMARK_US = "000300.SS", "^GSPC"
CLOCK_CN = {1: "牛", 2: "牛", 3: "横", 4: "熊", 5: "熊"}
THR_GRID = [(b, s) for b in (0.55, 0.60, 0.65) for s in (0.35, 0.40, 0.45)]


def load_breadth(market_id: str) -> list[tuple[str, float]]:
    """(as_of, B200) 序列，归一到 0..1。

    - SP500：lab.db market_breadth_snapshots.breadth_200（注意 coverage_* 是
      数据覆盖率不是宽度，已纠正）；
    - CN_ALL_A：读预计算缓存 a_share_ma_breadth_history.json（ma200_pct），
      lab.db 的 CN_ALL_A 行为空壳（handoff 已注明），缓存文件才是实数据。
    """
    if market_id == "CN_ALL_A":
        p = Path.home() / ".lei_signal_lab" / "cache" / "a_share_ma_breadth_history.json"
        h = json.loads(p.read_text(encoding="utf-8"))
        return [(x["date"], float(x["ma200_pct"]) / 100.0) for x in h]
    db = Path.home() / ".lei_signal_lab" / "lab.db"
    con = sqlite3.connect(str(db))
    rows = con.execute(
        "SELECT as_of, breadth_200 FROM market_breadth_snapshots "
        "WHERE market_id=? AND data_status='complete' ORDER BY as_of",
        (market_id,),
    ).fetchall()
    con.close()
    return [(r[0], float(r[1]) / 100.0) for r in rows if r[1] is not None]


class B200Mapper:
    def __init__(self, series: list[tuple[str, float]]):
        self.dates = [d for d, _ in series]
        self.vals = [v for _, v in series]

    def value(self, day: str) -> float | None:
        i = bisect_right(self.dates, day) - 1
        return self.vals[i] if i >= 0 else None

    def regime(self, day: str, bull: float, bear: float) -> str | None:
        v = self.value(day)
        if v is None:
            return None
        return "牛" if v > bull else "熊" if v < bear else "横"


def group_exp(trades: list[dict], keyfn) -> dict:
    agg = defaultdict(list)
    for t in trades:
        k = keyfn(t)
        if k is not None:
            agg[k].append(t["r_net"])
    return {k: {"N": len(v), "expR": round(sum(v) / len(v), 4)}
            for k, v in agg.items()}


def separation(groups: dict) -> float | None:
    if "牛" not in groups or "熊" not in groups:
        return None
    return round(abs(groups["牛"]["expR"] - groups["熊"]["expR"]), 4)


def closed(ts):
    return [t for t in ts if t["exit_date"] is not None]


def us_part(out: dict) -> None:
    from lei_signal.backtest.service import BacktestParams, execute_run
    for name, params in (
        ("A_us", BacktestParams(
            module="A", symbols=("IGV", "SOXX", "XLK", BENCHMARK_US),
            rr_min=None, entry_variant="early", exit_variant="a6_1_costbasis",
            fee_label="standard", limit_guard=True,
            overrides=(("clock_mult", 0.5),), volume_filter="shrink")),
        ("B_us", BacktestParams(
            module="B", symbols=("IGV", "SOXX", "XLK", BENCHMARK_US),
            rr_min=None, entry_variant="breakout", exit_variant="a6_1_costbasis",
            fee_label="standard", limit_guard=True,
            overrides=(("consolidation_bars", 20), ("cluster_threshold", 0.10)))),
    ):
        r = execute_run(params)
        r["trades"] = [t for t in r["trades"] if t["symbol"] != BENCHMARK_US]
        (RAW / f"{name}.json").write_text(
            json.dumps(r, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8")
        ts = closed(r["trades"])
        print(f"[us] {name}: N={len(ts)}")
        res = {"N": len(ts), "clock": {}, "b200": {}}
        clock_groups = group_exp(ts, lambda t: CLOCK_CN.get(t["benchmark_clock_type"]))
        res["clock"]["groups"] = clock_groups
        res["clock"]["separation"] = separation(clock_groups)
        mapper = B200Mapper(load_breadth("SP500"))
        for bull, bear in THR_GRID:
            g = group_exp(ts, lambda t, b=bull, s=bear: mapper.regime(t["signal_date"], b, s))
            tag = f"{int(bull*100)}/{int(bear*100)}"
            res["b200"][tag] = {"groups": g, "separation": separation(g)}
        res["b200_available"] = mapper.dates[0] if mapper.dates else None
        out[name] = res
        print(f"    clock: {clock_groups} sep={res['clock']['separation']}")
        for tag in ("60/40", "55/35", "65/45"):
            d = res["b200"][tag]
            print(f"    B200[{tag}]: {d['groups']} sep={d['separation']}")


def _monthly_flag_check(ts: list[dict], mapper: B200Mapper, bull: float,
                        bear: float, label: str) -> dict:
    """月末 B200 状态预警下月；统计命中（A 失血月被预警）与误报。"""
    monthly: dict[str, float] = defaultdict(float)
    monthly_n: dict[str, int] = defaultdict(int)
    for t in ts:
        m = t["entry_date"][:7]
        monthly[m] += t["r_net"]
        monthly_n[m] += 1
    months = sorted(monthly)
    hit = miss = false_alarm = correct_quiet = 0
    detail = []
    for i, m in enumerate(months):
        prev = months[i - 1] if i > 0 else None
        if prev is None:
            continue
        prev_end = prev + "-31"
        flag = mapper.regime(prev_end, bull, bear)
        bleed = monthly[m] < 0
        flagged = flag == "熊"
        if bleed and flagged:
            hit += 1
        elif bleed and not flagged:
            miss += 1
        elif not bleed and flagged:
            false_alarm += 1
        else:
            correct_quiet += 1
        detail.append({"month": m, "cumR": round(monthly[m], 2), "N": monthly_n[m],
                       "prev_b200_regime": flag})
    return {"label": label, "hit": hit, "miss": miss, "false_alarm": false_alarm,
            "correct_quiet": correct_quiet, "detail": detail}


def _monthly_clock_check(ts: list[dict], label: str) -> dict:
    """时钟口径的同型检查：上月基准时钟状态（取上月最后信号日前推不可靠，
    改用本月每笔信号自带的 clock——但那是同期而非提前。此处给同期口径，
    与 B200 月末预警对比时注明口径差（时钟无月末值，只能同期）。"""
    monthly: dict[str, list] = defaultdict(list)
    for t in ts:
        monthly[t["entry_date"][:7]].append(t)
    hit = miss = false_alarm = correct_quiet = 0
    detail = []
    for m, v in sorted(monthly.items()):
        # 月内基准态取多数（同期口径，非预测）
        clocks = defaultdict(int)
        for t in v:
            clocks[CLOCK_CN.get(t["benchmark_clock_type"], "?")] += 1
        flag = max(clocks, key=lambda k: clocks[k])
        bleed = sum(t["r_net"] for t in v) < 0
        flagged = flag == "熊"
        if bleed and flagged:
            hit += 1
        elif bleed and not flagged:
            miss += 1
        elif not bleed and flagged:
            false_alarm += 1
        else:
            correct_quiet += 1
        detail.append({"month": m, "cumR": round(sum(t["r_net"] for t in v), 2),
                       "N": len(v), "regime": flag})
    return {"label": label, "hit": hit, "miss": miss, "false_alarm": false_alarm,
            "correct_quiet": correct_quiet, "note": "同期多数票口径（非提前预警）",
            "detail": detail}


def cn_part(out: dict) -> None:
    a_run = json.loads((RAW / "A_ETF_cm05_shrink.json").read_text(encoding="utf-8"))
    b_run = json.loads((RAW / "Bp_stocks_30_3_a61.json").read_text(encoding="utf-8"))
    series = load_breadth("CN_ALL_A")
    print(f"[cn] CN_ALL_A complete rows={len(series)}",
          f"range={series[0][0]}~{series[-1][0]}" if series else "无数据")
    if len(series) < 200:
        out["cn"] = {"status": "insufficient", "rows": len(series)}
        print("    数据不足 200 行，A 股对照跳过")
        return
    mapper = B200Mapper(series)
    for name, run in (("A_cn", a_run), ("Bp_cn", b_run)):
        ts = closed(run["trades"])
        res = {"N": len(ts), "clock": {}, "b200": {}}
        cg = group_exp(ts, lambda t: CLOCK_CN.get(t["benchmark_clock_type"]))
        res["clock"]["groups"] = cg
        res["clock"]["separation"] = separation(cg)
        for bull, bear in THR_GRID:
            g = group_exp(ts, lambda t, b=bull, s=bear: mapper.regime(t["signal_date"], b, s))
            res["b200"][f"{int(bull*100)}/{int(bear*100)}"] = {
                "groups": g, "separation": separation(g)}
        out[name] = res
        print(f"[cn] {name} N={len(ts)} clock sep={res['clock']['separation']}"
              f" | B200[60/40] sep={res['b200']['60/40']['separation']}")

    # (b) 2026 段提前预警检验（A ETF 池）
    ts_a = closed(a_run["trades"])
    ts_2026 = [t for t in ts_a if t["entry_date"] >= "2026-01-01"]
    out["cn_2026_flag"] = {
        "b200_60_40": _monthly_flag_check(ts_2026, mapper, 0.60, 0.40, "B200 60/40 月末预警(仅2026)"),
        "b200_60_40_full": _monthly_flag_check(ts_a, mapper, 0.60, 0.40, "B200 60/40 月末预警(全期)"),
        "clock_same_period": _monthly_clock_check(ts_2026, "时钟多数票(仅2026,同期)"),
    }
    for k, v in out["cn_2026_flag"].items():
        print(f"[cn] {k}: hit={v['hit']} miss={v['miss']}"
              f" false_alarm={v['false_alarm']} correct_quiet={v['correct_quiet']}")


def main() -> None:
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    out_path = RAW / "b200_regime_summary.json"
    out = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}
    out.setdefault("date", "2026-08-27")
    if which in ("us", "both"):
        us_part(out)
    if which in ("cn", "both"):
        cn_part(out)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"落盘: {out_path}")


if __name__ == "__main__":
    main()
