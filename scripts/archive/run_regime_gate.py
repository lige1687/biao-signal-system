#!/usr/bin/env python3
"""市场状态门禁 + A/B 轮动实验（docs/handoff-regime-gate-prompt.md，2026-08-27）。

任务一：B 门禁 {仅横(=3), 横+熊(3,4,5), 不限} × 池 {个股30/3%, 行业ETF63/10%,
        宽基ETF20/4%} × 退出 {a6_1_costbasis, b3_dual}，共 18 组。
任务二：A/B 按基准状态轮动（牛/熊→A·ETF池·cm0.5·shrink，横→B'·个股30/3%），
        对照 全A / 全B' / 五五混合（信号日奇偶各半）。
任务三：黑天鹅窗口（2020-01~02 / 2022-03~04 / 2024-09~10）A 与 B' 损耗占比。

纪律：不改 src/、不改 configs/；门禁/轮动全部脚本层过滤；基准时钟取自
execute_run 落在 trades 里的 benchmark_clock_type（1,2=牛 3=横 4,5=熊）。
注意：池内必须包含 000300.SS（cn 基准），其自身交易在汇总前剔除。

判定标准（事前写死，防事后找理由）：
  任务一「B 在某池复活」= 门禁后 OOS>0 且 排top1后期望>0 且 N>=20
    （top1=该组累计 r_net 最大的标的，剔除其全部交易后重算期望）
  任务二「轮动有效」= 轮动组累计R >= 1.15×max(全A, 全B') 且 分年不塌
    （不塌 = 每个有信号的年份，轮动组当年累计R >= min(全A,全B'同年) - 2.0R）

产出：docs/experiments/raw/regime_gate/*.json + regime_gate_summary.json
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from lei_signal.backtest.runner import load_pool_frames  # noqa: E402
from lei_signal.backtest.service import BacktestParams, execute_run  # noqa: E402

RAW_DIR = REPO / "docs/experiments/raw/regime_gate"
RAW_DIR.mkdir(parents=True, exist_ok=True)

BENCHMARK = "000300.SS"  # cn 基准（沪深300 指数本体）；入池只为产出时钟状态
BROAD_CODES = {"510300", "510500", "512100", "510050", "159915",
               "159901", "588000", "515300", "159652"}

GATES: dict[str, frozenset[int] | None] = {
    "仅横市": frozenset({3}),
    "横+熊": frozenset({3, 4, 5}),
    "不限": None,
}
REGIME_NAME = {1: "牛", 2: "牛", 3: "横", 4: "熊", 5: "熊", 0: "无基准"}

SWAN_WINDOWS = [  # 任务三黑天鹅窗口（入场日口径）
    ("2020疫情", date(2020, 1, 1), date(2020, 2, 29)),
    ("2022俄乌+上海", date(2022, 3, 1), date(2022, 4, 30)),
    ("2024九二四前夜", date(2024, 9, 1), date(2024, 10, 31)),
]


def build_pools() -> dict[str, dict]:
    frames = load_pool_frames()
    available = set(frames)

    stocks: list[str] = []
    pool_txt = REPO / "docs/experiments/raw/bcd_retrial/stock_pool.txt"
    for line in pool_txt.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        sym = line.split()[0]
        if sym in available:
            stocks.append(sym)

    etf_all = sorted(
        s for s in available
        if (s.split(".")[0].startswith(("51", "56", "58", "159"))
            and not s.split(".")[0].startswith("513"))
    )
    broad = sorted(s for s in etf_all if s.split(".")[0] in BROAD_CODES)
    industry = sorted(set(etf_all) - set(broad))
    return {
        "个股": {"symbols": stocks, "cb": 30, "cl": 0.03},
        "行业ETF": {"symbols": industry, "cb": 63, "cl": 0.10},
        "宽基ETF": {"symbols": broad, "cb": 20, "cl": 0.04},
        "_etf_all": etf_all,
        "_available_n": len(available),
    }


def run_and_save(name: str, params: BacktestParams) -> dict:
    """跑一次 execute_run，剔除基准自身交易后落盘 raw/，返回 run 结果。"""
    t0 = time.time()
    r = execute_run(params)
    r["trades"] = [t for t in r["trades"] if t["symbol"] != BENCHMARK]
    r["wall_seconds"] = round(time.time() - t0, 1)
    out = RAW_DIR / f"{name}.json"
    out.write_text(
        json.dumps(r, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"[run] {name}: N={len(r['trades'])} symbols={r['data_range']['symbols_count']}"
          f" {r['wall_seconds']}s -> {out.name}")
    return r


def closed(trades: list[dict]) -> list[dict]:
    return [t for t in trades if t["exit_date"] is not None]


def exp_r(trades: list[dict]) -> float | None:
    if not trades:
        return None
    return sum(t["r_net"] for t in trades) / len(trades)


def exp4(trades: list[dict]) -> float | None:
    v = exp_r(trades)
    return None if v is None else round(v, 4)


def cum_r(trades: list[dict]) -> float:
    return sum(t["r_net"] for t in trades)


def is_oos(trade: dict, oos_start: str) -> bool:
    return trade["signal_date"] >= oos_start  # 与 service 同口径：按信号日切


def drop_top1(trades: list[dict]) -> tuple[list[dict], str, float]:
    """剔除累计 r_net 最大标的的全部交易。"""
    by_sym: dict[str, float] = defaultdict(float)
    for t in trades:
        by_sym[t["symbol"]] += t["r_net"]
    if not by_sym:
        return [], "", 0.0
    top = max(by_sym, key=lambda s: by_sym[s])
    return [t for t in trades if t["symbol"] != top], top, by_sym[top]


def yearly(trades: list[dict]) -> dict[str, dict]:
    agg: dict[int, list[dict]] = defaultdict(list)
    for t in trades:
        agg[int(t["entry_date"][:4])].append(t)
    return {
        str(y): {"N": len(ts), "cumR": round(cum_r(ts), 3),
                 "expR": None if not ts else round(exp_r(ts), 3)}
        for y, ts in sorted(agg.items())
    }


def max_drawdown_r(trades: list[dict]) -> float:
    """按平仓日排序的累计 R 峰谷最大回撤。"""
    seq = sorted(closed(trades), key=lambda t: t["exit_date"])
    peak = cum = 0.0
    mdd = 0.0
    for t in seq:
        cum += t["r_net"]
        peak = max(peak, cum)
        mdd = max(mdd, peak - cum)
    return mdd


def group_metrics(trades: list[dict], oos_start: str) -> dict:
    """任务一组级指标：N/期望/IS/OOS/排top1/分年。"""
    ts = closed(trades)
    ex_ts, top_sym, top_r = drop_top1(ts)
    return {
        "N": len(ts),
        "open": len(trades) - len(ts),
        "expR": exp4(ts),
        "cumR": round(cum_r(ts), 3),
        "IS_expR": exp4([t for t in ts if not is_oos(t, oos_start)]),
        "OOS_expR": exp4([t for t in ts if is_oos(t, oos_start)]),
        "IS_N": sum(1 for t in ts if not is_oos(t, oos_start)),
        "OOS_N": sum(1 for t in ts if is_oos(t, oos_start)),
        "ex_top1_expR": exp4(ex_ts),
        "top1": {"symbol": top_sym, "cumR": round(top_r, 3)},
        "by_year": yearly(ts),
    }


def regime_split(trades: list[dict]) -> dict[str, dict]:
    agg: dict[str, list[dict]] = defaultdict(list)
    for t in closed(trades):
        agg[REGIME_NAME.get(t["benchmark_clock_type"], "?")].append(t)
    return {
        k: {"N": len(v), "expR": exp4(v), "cumR": round(cum_r(v), 3)}
        for k, v in agg.items()
    }


# ---------------------------------------------------------------- 任务一
def task1(pools: dict) -> dict:
    print("\n===== 任务一：B 门禁 3×3×2 =====")
    out: dict = {"runs": {}, "gate_matrix": {}, "revival": {}, "regime_split": {}}
    for pool_name in ("个股", "行业ETF", "宽基ETF"):
        p = pools[pool_name]
        for exit_v in ("a6_1_costbasis", "b3_dual"):
            key = f"{pool_name}_{exit_v}"
            r = run_and_save(
                f"task1_{pool_name}_{exit_v}",
                BacktestParams(
                    module="B",
                    symbols=tuple(sorted(set(p["symbols"]) | {BENCHMARK})),
                    rr_min=None,
                    entry_variant="breakout",
                    exit_variant=exit_v,
                    fee_label="standard",
                    limit_guard=True,
                    overrides=(("consolidation_bars", p["cb"]),
                               ("cluster_threshold", p["cl"])),
                ),
            )
            oos_start = r["data_range"]["out_of_sample_start"]
            trades = r["trades"]
            out["runs"][key] = {
                "cb": p["cb"], "cl": p["cl"], "exit": exit_v,
                "symbols_n": len(p["symbols"]),
                "oos_start": oos_start,
            }
            out["regime_split"][key] = regime_split(trades)
            out["gate_matrix"][key] = {}
            for gate_name, allow in GATES.items():
                gated = ([t for t in trades
                          if t["benchmark_clock_type"] in allow]
                         if allow is not None else trades)
                m = group_metrics(gated, oos_start)
                m["revival"] = bool(
                    (m["OOS_expR"] or 0) > 0 and (m["ex_top1_expR"] or 0) > 0
                    and m["N"] >= 20
                )
                out["gate_matrix"][key][gate_name] = m
    return out


# ---------------------------------------------------------------- 任务二
def task2(pools: dict) -> dict:
    print("\n===== 任务二：A/B 按基准状态轮动 =====")
    etf_all = pools["_etf_all"]
    stocks = pools["个股"]["symbols"]

    r_a = run_and_save(
        "task2_A_ETF",
        BacktestParams(
            module="A",
            symbols=tuple(sorted(set(etf_all) | {BENCHMARK})),
            rr_min=None,
            entry_variant="early",
            exit_variant="a6_1_costbasis",
            fee_label="standard",
            limit_guard=True,
            overrides=(("clock_mult", 0.5),),
            volume_filter="shrink",
        ),
    )
    r_b = run_and_save(
        "task2_Bp_stocks",
        BacktestParams(
            module="B",
            symbols=tuple(sorted(set(stocks) | {BENCHMARK})),
            rr_min=None,
            entry_variant="breakout",
            exit_variant="b3_dual",
            fee_label="standard",
            limit_guard=True,
            overrides=(("consolidation_bars", 30), ("cluster_threshold", 0.03)),
            volume_filter="none",
        ),
    )
    # 两个池数据末端一致（同一回测池），OOS 切分以 A 为准并校验
    oos_a = r_a["data_range"]["out_of_sample_start"]
    oos_b = r_b["data_range"]["out_of_sample_start"]
    a_tr, b_tr = r_a["trades"], r_b["trades"]

    def clock(t: dict) -> int:
        return t["benchmark_clock_type"]

    no_clock = {"A": sum(1 for t in a_tr if clock(t) == 0),
                "B'": sum(1 for t in b_tr if clock(t) == 0)}
    rot = ([t for t in a_tr if clock(t) in (1, 2, 4, 5)]
           + [t for t in b_tr if clock(t) == 3])
    # 五五混合：信号日奇偶各半（A 取奇数日，B' 取偶数日；同期对照）
    mix = ([t for t in a_tr if date.fromisoformat(t["signal_date"]).toordinal() % 2 == 1]
           + [t for t in b_tr if date.fromisoformat(t["signal_date"]).toordinal() % 2 == 0])

    def port(name: str, trades: list[dict]) -> dict:
        ts = closed(trades)
        return {
            "name": name, "N": len(ts),
            "expR": exp4(ts),
            "cumR": round(cum_r(ts), 3),
            "IS_expR": exp4([t for t in ts if not is_oos(t, oos_a)]),
            "OOS_expR": exp4([t for t in ts if is_oos(t, oos_a)]),
            "maxDD_R": round(max_drawdown_r(ts), 3),
            "by_year": yearly(ts),
        }

    ports = {
        "全A": port("全A（ETF池 cm0.5 shrink）", a_tr),
        "全B'": port("全B'（个股 30/3% b3）", b_tr),
        "轮动": port("轮动（牛熊→A，横→B'）", rot),
        "五五混合": port("五五混合（信号日奇偶）", mix),
    }

    # 判定（事前写死）：累计R超最好单模块15%+ 且 每年不比两模块较差者差2R以上
    cum_best_single = max(ports["全A"]["cumR"], ports["全B'"]["cumR"])
    yearly_ok = True
    yearly_detail = {}
    for y, row in ports["轮动"]["by_year"].items():
        a_y = ports["全A"]["by_year"].get(y, {"cumR": 0.0})
        b_y = ports["全B'"]["by_year"].get(y, {"cumR": 0.0})
        floor = min(a_y["cumR"], b_y["cumR"]) - 2.0
        ok = row["cumR"] >= floor
        yearly_ok = yearly_ok and ok
        yearly_detail[y] = {"轮动": row["cumR"], "全A": a_y["cumR"],
                            "全B'": b_y["cumR"], "floor": round(floor, 3), "ok": ok}
    verdict = {
        "cum_best_single": round(cum_best_single, 3),
        "rotation_cumR": ports["轮动"]["cumR"],
        "threshold_115": round(1.15 * cum_best_single, 3),
        "cum_pass": ports["轮动"]["cumR"] >= 1.15 * cum_best_single,
        "yearly_ok": yearly_ok,
        "yearly_detail": yearly_detail,
        "effective": bool(ports["轮动"]["cumR"] >= 1.15 * cum_best_single and yearly_ok),
        "oos_start_A": oos_a, "oos_start_B": oos_b,
        "no_clock_trades": no_clock,
        "rotation_n_by_source": {
            "from_A": sum(1 for t in rot if clock(t) in (1, 2, 4, 5)),
            "from_B": sum(1 for t in rot if clock(t) == 3),
        },
    }
    return {"ports": ports, "verdict": verdict}


# ---------------------------------------------------------------- 任务三
def task3(a_tr: list[dict], b_tr: list[dict]) -> dict:
    print("\n===== 任务三：黑天鹅窗口损耗（入场日口径） =====")
    out = {}
    for name, trades in (("A", a_tr), ("B'", b_tr)):
        ts = closed(trades)
        total_loss = -sum(t["r_net"] for t in ts if t["r_net"] < 0)
        rows = {}
        swan_loss_sum = 0.0
        for wname, start, end in SWAN_WINDOWS:
            in_w = [t for t in ts if start.isoformat() <= t["entry_date"] <= end.isoformat()]
            loss = -sum(t["r_net"] for t in in_w if t["r_net"] < 0)
            swan_loss_sum += loss
            rows[wname] = {
                "N": len(in_w), "netR": round(cum_r(in_w), 3),
                "lossR": round(loss, 3),
                "share_of_total_loss": round(loss / total_loss, 4) if total_loss else None,
            }
        out[name] = {
            "windows": rows,
            "total_lossR": round(total_loss, 3),
            "swan_total_lossR": round(swan_loss_sum, 3),
            "swan_share": round(swan_loss_sum / total_loss, 4) if total_loss else None,
            "swan_netR_total": round(
                sum(w["netR"] for w in rows.values()), 3),
        }
    return out


def main() -> None:
    pools = build_pools()
    print(f"池可用标的 {pools['_available_n']} 只；个股 {len(pools['个股']['symbols'])}"
          f" / 行业ETF {len(pools['行业ETF']['symbols'])} / 宽基ETF {len(pools['宽基ETF']['symbols'])}"
          f" / ETF全集 {len(pools['_etf_all'])}")

    t1 = task1(pools)
    t2 = task2(pools)
    t3 = task3(
        json.loads((RAW_DIR / "task2_A_ETF.json").read_text(encoding="utf-8"))["trades"],
        json.loads((RAW_DIR / "task2_Bp_stocks.json").read_text(encoding="utf-8"))["trades"],
    )

    summary = {
        "date": "2026-08-27",
        "handoff": "docs/handoff-regime-gate-prompt.md",
        "benchmark": BENCHMARK,
        "pool_sizes": {k: len(v["symbols"]) if isinstance(v, dict) and "symbols" in v else len(v)
                       for k, v in pools.items() if not k.startswith("_")},
        "task1": t1,
        "task2": t2,
        "task3": t3,
    }
    (RAW_DIR / "regime_gate_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")

    print("\n===== 摘要 =====")
    print("\n-- 任务一 门禁矩阵（N | expR | OOS | ex-top1 | 复活）--")
    for key, gates in t1["gate_matrix"].items():
        for g, m in gates.items():
            print(f"{key:26s} {g:4s} N={m['N']:4d} exp={m['expR']!s:>7s}"
                  f" OOS={m['OOS_expR']!s:>7s} exTop1={m['ex_top1_expR']!s:>7s}"
                  f" 复活={'√' if m['revival'] else '×'}")
    print("\n-- 任务二 四组 --")
    for name, p in t2["ports"].items():
        print(f"{name:6s} N={p['N']:4d} exp={p['expR']} cum={p['cumR']:9.3f}"
              f" IS={p['IS_expR']} OOS={p['OOS_expR']} maxDD={p['maxDD_R']}")
    v = t2["verdict"]
    print(f"判定: 轮动cum={v['rotation_cumR']} vs 1.15×最好单模块={v['threshold_115']}"
          f" cum_pass={v['cum_pass']} yearly_ok={v['yearly_ok']} => "
          f"{'有效' if v['effective'] else '未达有效'}")
    print("\n-- 任务三 黑天鹅 --")
    for mod, d in t3.items():
        print(f"{mod}: 总亏损R={d['total_lossR']} 三窗口合计净R={d['swan_netR_total']}"
              f" 窗口亏损R={d['swan_total_lossR']} 占比={d['swan_share']}")
    print(f"\n落盘: {RAW_DIR}/regime_gate_summary.json")


if __name__ == "__main__":
    main()
