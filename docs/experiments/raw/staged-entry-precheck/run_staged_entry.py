"""Prompt AE · 语义九前置验证：创业板三档冠军信号的"分批建仓 vs 一次性"事件研究
（2026-09-03）。

任务书：docs/experiments/prompt-AE-staged-entry-precheck-2026-09-03.md。
两种分批思路分开测分开判（阶梯式 / 定投式），不发明新信号、不改档位参数、
不做大规模网格；本脚本只做"执行层对照"的最基础事件研究。

数据（全部只读复用认证产物，不新增数据源）：
- 事件源：docs/experiments/raw/kuandu-quanzhan/champion_cyb.json 的
  daily.weight 序列（创业板三档冠军认证仓位，2010-06-01→2026-08-27，
  仅取 {0, 0.5, 1.0} 三值）。
- 价格：同文件 daily.benchmark（冠军回测自用的指数收盘序列，与认证结果
  同源）。执行口径偏差声明：本实验用 T 收盘信号 → T+1 收盘执行（数据集
  无开盘价；仓库标准为 T+1 开盘，收盘执行对 A 股指数单日高波动而言误差
  双向、不构成系统性前视）。
- 费用：单边 10bp（出处：kuandu-quanzhan-ARCHIVE"费用 10bp 双边"/
  champion params fee_bps=10）；本实验只有买入侧，卖出不计费且各执行方式
  同口径（净收益对比公平性声明）。

事件定义（机械提取）：weight 由 <1.0 变为 1.0 的当日为信号日 t；执行日
t+1。20 交易日内多次切换只记首枚（去重，敏感性：不去重）。

执行方式（每事件独立小账本，100 万）：
- 全仓基准：t+1 收盘一次买满（10bp）。
- 阶梯式：k∈{3,4,5} 批 × 间隔 s∈{5,10,20} 交易日，等权 1/k，首批 t+1、
  后续各批 t+1+s, t+1+2s, …；主臂=3 批×10 日（预注册中间值，其余 8 臂
  仅敏感性，跑后不选优）。
- 定投式：每日一份=60 个交易日各 1/60；每周一份=24 周各 1/24（参数来源：
  CROSS-GROUP-SYNTHESIS"双≤20 正确形态应是 12 个月分批建仓"教训）。
- 信号反向条款（跑前写死）：建仓期间 weight 跌回 <1.0 → 剩余批次作废，
  已投部分保留，事件标记 interrupted；全仓基准另记此后 20 交易日内 weight
  是否跌回（weight_back_20td，供分组解释，不作废）。

度量（每事件×每执行方式）：
1. 建仓完成后 60/120 交易日净收益（主口径=任务书字面：以各自完成日锚定；
   固定锚=信号日 t+1+60/120 收盘，作敏感性，供跨臂可比解释）。
2. 建仓平均成本 vs 一次性成本：批次 VWAP（含费）相对全仓单价（含费）
   之差，负=更便宜。
3. 建仓期最大回撤（口径：各臂自身建仓窗 [t+1, 完成日]；全仓基准用与被比
   主臂相同长度的窗口 [t+1, t+1+完成窗长]，保证日历窗可比）。
4. 费用已含于净收益；买入次数单列。

判定标准（事前写死，跑完不许改）：
- 阶梯式主臂（3×10）与定投式主臂（每日 60 份）分别判，n≥5 才判：
  - 收益维：mean(建仓完成后 120 交易日净收益) ≥ 全仓基准 − 1.0pp；
  - 回撤维：mean(建仓期回撤) 较全仓基准改善 ≥2pp 且 worst 事件改善 ≥5pp；
  - 两维同过→「有实质改善」；仅回撤过→「回撤换收益的取舍型（观察）」；
    仅收益过→「无实质增量」；双不过→「分批吃亏」。
- 分组（只报告不判定）：触发时 breadth≤20（极端底部，双≤20 口径）vs >20；
  前仓 0.0 vs 0.5；interrupted vs 未中断。
- 敏感性：阶梯 8 邻域臂、每周 24 份、固定锚收益口径。
- 本实验不构成买卖指令；结论限定"创业板三档冠军信号 + 本价格序列"。

输出：本目录（docs/experiments/raw/staged-entry-precheck/）
- staged_entry_results.json（全臂+判定+分组）+ events 明细 CSV + hash_<seed>.json
复现：PYTHONHASHSEED=0 python3 run_staged_entry.py（离线，<10 秒）
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[4]
CHAMP = REPO / "docs/experiments/raw/kuandu-quanzhan/champion_cyb.json"

FEE = 0.001            # 单边 10bp（kuandu 冠军口径）
CAPITAL = 1_000_000.0
DEDUP_TD = 20          # 事件去重窗口（交易日）
K_GRID = (3, 4, 5)
S_GRID = (5, 10, 20)
MAIN_K, MAIN_S = 3, 10
DCA_DAILY_N = 60       # 每日一份 ×60
DCA_WEEKLY_N = 24      # 每周一份 ×24（≈12 个月）
HORIZONS = (60, 120)   # 建仓完成后 N 交易日
LINE_RET_PP = 0.010    # 收益维：不低于全仓 −1pp
LINE_DD_MEAN_PP = 0.02  # 回撤维：均值改善 ≥2pp
LINE_DD_WORST_PP = 0.05  # 回撤维：最差事件改善 ≥5pp
N_MIN = 5


def load():
    d = json.loads(CHAMP.read_text())
    dates = pd.to_datetime(d["daily"]["date"])
    w = np.array([x if x is not None else np.nan for x in d["daily"]["weight"]],
                 dtype=float)
    bm = np.array(d["daily"]["benchmark"], dtype=float)
    br = np.array([x if x is not None else np.nan for x in d["daily"]["breadth"]],
                  dtype=float)
    return dates, w, bm, br


def extract_events(w) -> list[dict]:
    """weight <1.0 → 1.0 的切换日（信号日索引）；20 交易日去重。"""
    evs, last = [], -10**9
    for i in range(1, len(w)):
        if np.isnan(w[i]) or np.isnan(w[i - 1]):
            continue
        if w[i] >= 0.99 and w[i - 1] < 0.99 and i - last >= DEDUP_TD:
            evs.append({"i": i, "prev_w": float(w[i - 1])})
            last = i
    return evs


def _weight_dipped(w, a: int, b: int) -> bool:
    """[a,b] 窗口内 weight 是否跌回 <0.99（NaN 忽略）。"""
    seg = w[max(0, a):b + 1]
    seg = seg[~np.isnan(seg)]
    return bool(len(seg) and seg.min() < 0.99)


def sim(bm, w, ev, spec) -> dict:
    """单事件×单执行方式。spec: ('allin',) | ('ladder',k,s) | ('dca',n,step)。"""
    i0, n = ev["i"], len(bm)
    if spec[0] == "allin":
        entries = [i0 + 1]
    elif spec[0] == "ladder":
        entries = [i0 + 1 + j * spec[2] for j in range(spec[1])]
    else:
        entries = [i0 + 1 + j * spec[2] for j in range(spec[1])]
    if entries[-1] >= n - 1:
        return {"ok": False}
    entries_used = []
    for j, e in enumerate(entries):
        if j > 0 and _weight_dipped(w, entries[j - 1] + 1, e):
            break  # 信号反向：剩余批次作废
        entries_used.append(e)
    interrupted = len(entries_used) < len(entries)
    m = len(entries_used)
    per = CAPITAL / len(entries)      # 预算按原批数（作废批次留存现金）
    units, cost_amt, cash = 0.0, 0.0, CAPITAL
    for e in entries_used:
        units += (per - per * FEE) / bm[e]
        cost_amt += per
        cash -= per
    px0 = bm[entries[0]]
    vwap = cost_amt / units if units > 0 else np.nan
    res = {"ok": True, "completion_i": entries_used[-1],
           "interrupted": interrupted, "n_buys": m,
           "avg_cost_vs_allin": round(vwap / (px0 / (1 - FEE)) - 1, 4)}
    # 建仓期回撤（自身建仓窗）
    e0 = entries_used[0]
    path = bm[e0:entries_used[-1] + 1] if entries_used[-1] > e0 \
        else np.array([px0, px0])
    eqp = cash + units * path
    res["dd_construct"] = round(float((eqp / np.maximum.accumulate(eqp)).min() - 1), 4)
    # 补充字段（非判定）：与全仓基准同长的 21 交易日窗回撤，跨臂日历可比用
    win = bm[e0:min(e0 + MAIN_K * MAIN_S + 1, n)]
    eqw = cash + units * win
    res["dd_window21"] = round(
        float((eqw / np.maximum.accumulate(eqw)).min() - 1), 4)
    for h in HORIZONS:
        j = res["completion_i"] + h
        res[f"ret{h}"] = round(float((cash + units * bm[j]) / CAPITAL - 1), 4) \
            if j < n else None
        jf = i0 + 1 + h
        res[f"ret{h}_fixed"] = round(
            float((cash + units * bm[jf]) / CAPITAL - 1), 4) if jf < n else None
    if spec[0] == "allin":
        res["weight_back_20td"] = _weight_dipped(w, i0 + 2, i0 + 21)
    return res


def main() -> None:
    dates, w, bm, br = load()
    evs = extract_events(w)
    n = len(bm)

    specs = ([("allin",)] + [("ladder", k, s) for k in K_GRID for s in S_GRID]
             + [("dca", DCA_DAILY_N, 1), ("dca", DCA_WEEKLY_N, 5)])
    arms: dict = {}
    for spec in specs:
        tag = ("allin" if spec[0] == "allin" else
               (f"ladder{spec[1]}x{spec[2]}" if spec[0] == "ladder"
                else f"dca_{'daily' if spec[2] == 1 else 'weekly'}{spec[1]}"))
        rs = [sim(bm, w, e, spec) for e in evs]
        # 全仓基准建仓期回撤可比窗：与阶梯主臂 3×10 同长（21 交易日）
        if spec[0] == "allin":
            for e, r in zip(evs, rs):
                if not r.get("ok"):
                    continue
                e0 = e["i"] + 1
                win = bm[e0:min(e0 + MAIN_K * MAIN_S + 1, n)]
                u = (CAPITAL * (1 - FEE)) / bm[e0]
                eqp = u * win
                r["dd_construct"] = round(
                    float((eqp / np.maximum.accumulate(eqp)).min() - 1), 4)
                r["dd_window21"] = r["dd_construct"]
        ok = [r for r in rs if r.get("ok")]
        blk: dict = {"n_events": len(evs), "n_ok": len(ok)}
        for h in HORIZONS:
            for suf in ("", "_fixed"):
                vals = [r[f"ret{h}{suf}"] for r in ok
                        if r.get(f"ret{h}{suf}") is not None]
                blk[f"mean_ret{h}{suf}"] = round(float(np.mean(vals)), 4) \
                    if vals else None
        for k in ("dd_construct",):
            dds = [r[k] for r in ok]
            blk["mean_dd"] = round(float(np.mean(dds)), 4) if dds else None
            blk["worst_dd"] = round(float(np.min(dds)), 4) if dds else None
        ddw = [r.get("dd_window21") for r in ok if r.get("dd_window21") is not None]
        blk["mean_dd_window21"] = round(float(np.mean(ddw)), 4) if ddw else None
        blk["worst_dd_window21"] = round(float(np.min(ddw)), 4) if ddw else None
        costs = [r["avg_cost_vs_allin"] for r in ok]
        blk["mean_cost_vs_allin"] = round(float(np.mean(costs)), 4) if costs else None
        blk["n_interrupted"] = sum(1 for r in ok if r["interrupted"])
        blk["mean_buys"] = round(float(np.mean([r["n_buys"] for r in ok])), 2)
        blk["events"] = [
            {"date": str(dates[e["i"]].date()), "prev_w": e["prev_w"],
             "breadth": None if np.isnan(br[e["i"]]) else round(float(br[e["i"]]), 1),
             **{k: v for k, v in r.items() if k != "ok"}}
            for e, r in zip(evs, rs)]
        arms[tag] = blk

    # ---- 判定（事前线）----
    def judge(tag):
        a, base = arms[tag], arms["allin"]
        if a["n_ok"] < N_MIN:
            return {"verdict": "report_only_n<5"}
        ret_ok = (a["mean_ret120"] is not None and base["mean_ret120"] is not None
                  and a["mean_ret120"] >= base["mean_ret120"] - LINE_RET_PP)
        dd_ok = (a["mean_dd"] is not None and base["mean_dd"] is not None
                 and a["mean_dd"] >= base["mean_dd"] + LINE_DD_MEAN_PP
                 and a["worst_dd"] >= base["worst_dd"] + LINE_DD_WORST_PP)
        v = ("substantial_improvement" if (ret_ok and dd_ok)
             else ("dd_tradeoff_watch" if dd_ok
                   else ("no_increment" if ret_ok else "tranche_penalty")))
        return {"verdict": v, "ret_ok": bool(ret_ok), "dd_ok": bool(dd_ok)}

    verdicts = {"ladder_main_3x10": judge("ladder3x10"),
                "dca_daily60": judge("dca_daily60")}

    # ---- 分组（只报告：全仓 / 两主臂）----
    groups: dict = {}
    conds = {
        "breadth_le20": lambda e: e.get("breadth") is not None and e["breadth"] <= 20,
        "breadth_gt20": lambda e: e.get("breadth") is not None and e["breadth"] > 20,
        "from_w0": lambda e: e["prev_w"] <= 0.01,
        "from_w05": lambda e: 0.01 < e["prev_w"] < 0.99,
        "interrupted": lambda e: bool(e.get("interrupted")),
        "clean": lambda e: not e.get("interrupted"),
    }
    for gname, key in conds.items():
        for tag in ("allin", "ladder3x10", "dca_daily60"):
            sel = [e for e in arms[tag]["events"] if key(e)]
            if sel:
                v120 = [e["ret120"] for e in sel if e.get("ret120") is not None]
                dds = [e["dd_construct"] for e in sel
                       if e.get("dd_construct") is not None]
                groups.setdefault(gname, {})[tag] = {
                    "n": len(sel),
                    "mean_ret120": round(float(np.mean(v120)), 4) if v120 else None,
                    "mean_dd": round(float(np.mean(dds)), 4) if dds else None}

    out = {
        "config": dict(FEE=FEE, DEDUP_TD=DEDUP_TD, MAIN=(MAIN_K, MAIN_S),
                       DCA=(DCA_DAILY_N, DCA_WEEKLY_N), HORIZONS=HORIZONS,
                       LINES=dict(ret_pp=LINE_RET_PP, dd_mean_pp=LINE_DD_MEAN_PP,
                                  dd_worst_pp=LINE_DD_WORST_PP, n_min=N_MIN)),
        "window": [str(dates[0].date()), str(dates[-1].date())],
        "n_events": len(evs),
        "arms": {k: {kk: vv for kk, vv in v.items() if kk != "events"}
                 for k, v in arms.items()},
        "verdicts": verdicts,
        "groups": groups,
    }
    res_json = json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True,
                          default=str)
    (RAW / "staged_entry_results.json").write_text(res_json)
    rows = [{"arm": tag, **{k: e.get(k) for k in
             ("date", "prev_w", "breadth", "interrupted", "ret60", "ret120",
              "dd_construct", "dd_window21", "avg_cost_vs_allin", "n_buys")}}
            for tag in ("allin", "ladder3x10", "dca_daily60")
            for e in arms[tag]["events"]]
    pd.DataFrame(rows).to_csv(RAW / "staged_entry_events.csv", index=False)
    digest = hashlib.sha256(res_json.encode()).hexdigest()
    seed = os.environ.get("PYTHONHASHSEED", "unset")
    (RAW / f"hash_{seed}.json").write_text(json.dumps(
        {"pythonhashseed": seed, "sha256_results": digest}, indent=2))
    print(json.dumps({"window": out["window"], "n_events": len(evs),
                      "arms": out["arms"], "verdicts": verdicts,
                      "groups": groups, "sha256": digest},
                     indent=2, ensure_ascii=False))
    return None


if __name__ == "__main__":
    sys.exit(main())
