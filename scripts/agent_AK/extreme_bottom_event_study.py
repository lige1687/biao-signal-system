# -*- coding: utf-8 -*-
"""任务 AK：双≤20 极端底部事件全景研究（跨标的）——"底部是过程还是事件"。

预注册（跑前写死，跑后不得回头调整；本 docstring 即预注册全文）。

背景：双≤20 定心丸警报 = 全A宽度 b50<=20 且 b200<=20 同日成立
（src/lei_signal/timing_backtest/service.py::alert_state, market="cn" → cn_all）。
本任务是描述性事件研究：不设计任何分批规则、不做策略回测收益比较。

事件定义（机械可复现）：
  - 事件日 = cn_all 宽度当日 b50<=20 且 b200<=20、且前一交易日不同时满足（状态进入日）。
  - 簇合并（参照 AE 口径）：与前一保留事件日间隔 <40 个宽度交易日的新触发，
    并入同簇不另计。主分析用簇合并后事件。

标的网格（事件日须落在该标的有效样本内才计入该标的）：
  - 创业板指 399006（2010-06 起）
  - 沪深300 000300（2002-01 起）
  - 中证1000ETF 512100（2016-11 起，ETF 上市晚于指数，样本期如实记录）
  - 科创50 000688.SH（2020-07 起）
  - 半导体ETF 512480（2019-06 起）

逐事件度量（事件日收盘价为基准，全部 close-to-close）：
  - 前瞻收益 r20/r60/r120/r250（交易日；不足记缺失）。
  - 后续下探：事件后 60 交易日内最低收盘相对事件日收盘的深度 dd60 = min/close-1，
    及最低点出现的交易日序号 t_low60（晚到 = 有过程）。
  - 收复耗时 recover：事件日之后首个收盘 >= 事件日收盘的交易日数（<=250 窗口内，
    超出记 250+ 截尾）。

"过程 vs 事件"逐事件机械判据（跑前写死，三分类）：
  - 过程型（process）：dd60 <= -5%（事件后 60 日内继续深跌 ≥5%）——分批有更低的价。
  - 事件型（V 型）：dd60 >= -2%（几乎不再下探）且 recover <= 20 交易日（快速收复，
    晚买就贵）。不满足两者任一即不判 V。
  - 中间型：其余。

预注册判定线（三选一）：
  - 判"过程"：可分类事件合计 >=8 个，且合并池中过程型占比 >=60%，
    且有 >=3 个标的各自过程型占比 >=50%（各自事件数 >=2 才参与多数判定）。
  - 判"事件"：对称（事件型占比 >=60% 且 >=3 个标的事件型占比 >=50%）。
  - 其余：混合/证据不足（写明每个标的哪一型占优）。
  - 若合并簇总数 <5：直接证据不足。

数据清洗修正（跑后诚实登记、跑前机械规则）：发现 512100 缓存 2022-09-01→09-05
收盘 0.982→2.698（+175%），为 ETF 份额拆分未复权。机械修正规则：任一标的出现
隔夜收盘比 >1.5 或 <1/1.5 视为公司行为，将其之前全部价格乘以该比率做前复权
（市场真实涨跌不会单日 ±50%）。该修正不影响 dd60/收复/分类（相关窗口在拆分
之前），只修正受污染的前瞻收益。

输出：docs/experiments/raw/agent_AK/extreme_bottom_events.json
"""
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

CACHE = Path.home() / ".lei_signal_lab/cache"
TIMING = CACHE / "timing"
OUT_DIR = Path(__file__).resolve().parents[2] / "docs/experiments/raw/agent_AK"

INSTRUMENTS = {
    "399006": ("创业板指", TIMING / "399006.parquet"),
    "000300": ("沪深300", TIMING / "000300.parquet"),
    "512100": ("中证1000ETF", TIMING / "512100.parquet"),
    "000688.SH": ("科创50", CACHE / "000688.SS.bars.parquet"),
    "512480": ("半导体ETF", TIMING / "512480.parquet"),
}

WINDOWS = [20, 60, 120, 250]
CLUSTER_GAP = 40          # 簇合并间隔（交易日，宽度日历）
DD_DEPTH_PROC = -5.0       # 过程型：60 日内下探 <= -5%
DD_DEPTH_V = -2.0          # 事件型：下探 >= -2%（更浅）
RECOVER_V = 20             # 事件型：20 交易日内收复
MIN_EVENTS_TOTAL = 8       # 判定型最低合并样本
DOMINANT_SHARE = 0.60      # 合并池占比线
MIN_INSTR_FOR_MAJORITY = 3  # 多数标的线
MIN_EVENTS_PER_INSTR = 2   # 单标的参与多数判定的最低事件数


def adjust_corporate_actions(close: pd.Series) -> tuple[pd.Series, list]:
    """机械公司行为修正：隔夜 |涨跌| >50% 视为拆分/合并，前复权。"""
    ret = close / close.shift(1)
    jumps = []
    adj = close.copy()
    for idx in ret.index[(ret > 1.5) | (ret < 1 / 1.5)]:
        pos = close.index.get_loc(idx)
        ratio = float(close.iloc[pos] / close.iloc[pos - 1])
        adj.iloc[:pos] = adj.iloc[:pos] * ratio
        jumps.append({"date": str(pd.Timestamp(idx).date()),
                      "overnight_ratio": round(ratio, 4)})
    return adj, jumps


def classify(dd60: float, recover) -> str:
    """预注册三分类。recover 为 None 表示 250 日内未收复（截尾，按 >250 处理）。"""
    rec = recover if recover is not None else 999
    if dd60 <= DD_DEPTH_PROC:
        return "process"
    if dd60 >= DD_DEPTH_V and rec <= RECOVER_V:
        return "event_v"
    return "middle"


def main() -> None:
    breadth = pd.read_parquet(TIMING / "breadth_cn_all.parquet")
    b = breadth[["b50", "b200"]].dropna()
    cond = (b["b50"] <= 20) & (b["b200"] <= 20)
    entry = cond & (~cond.shift(1, fill_value=False))
    raw_triggers = list(b.index[entry])

    # 簇合并（宽度交易日历上间隔 <40 并入）
    clusters = []
    for d in raw_triggers:
        if clusters and (b.index.get_loc(d) - b.index.get_loc(clusters[-1])) < CLUSTER_GAP:
            continue
        clusters.append(d)

    events = []
    per_instr = []
    all_jumps = []
    for sym, (name, path) in INSTRUMENTS.items():
        raw_px = pd.read_parquet(path)["close"].dropna()
        raw_px = raw_px[~raw_px.index.duplicated(keep="last")].sort_index()
        px, jumps = adjust_corporate_actions(raw_px)
        all_jumps.extend({"symbol": sym, **j} for j in jumps)
        inst_rows = []
        for d in clusters:
            # 事件日须落在标的有效样本内（用宽度事件日在价格日历上向后对齐不超过
            # 3 个交易日，处理 ETF 停牌/日历差；对齐后仍在样本末端之后则跳过）
            loc = px.index.searchsorted(d)
            if loc >= len(px):
                continue
            aligned = px.index[loc]
            if (aligned - d).days > 7:
                continue
            i = loc
            c0 = float(px.iloc[i])
            if not c0 > 0:
                continue
            row = {
                "symbol": sym, "name": name,
                "event_date": str(pd.Timestamp(d).date()),
                "event_trade_date": str(pd.Timestamp(aligned).date()),
            }
            for w in WINDOWS:
                j = i + w
                row[f"r{w}"] = round((float(px.iloc[j]) / c0 - 1) * 100, 2) if j < len(px) else None
            win = px.iloc[i + 1: i + 1 + 60]
            if len(win) > 0:
                dd60 = round((float(win.min()) / c0 - 1) * 100, 2)
                t_low60 = int(win.index.get_loc(win.idxmin())) + 1
            else:
                dd60, t_low60 = None, None
            big = px.iloc[i + 1: i + 1 + 250]
            rec = None
            for k, v in enumerate(big.values, start=1):
                if v >= c0:
                    rec = k
                    break
            row["dd60_pct"] = dd60
            row["t_low60_days"] = t_low60
            row["recover_days"] = rec
            row["type"] = classify(dd60, rec) if dd60 is not None else None
            events.append(row)
            inst_rows.append(row)
        per_instr.append({
            "symbol": sym, "name": name,
            "sample_start": str(pd.Timestamp(px.index.min()).date()),
            "sample_end": str(pd.Timestamp(px.index.max()).date()),
            "n_events": len(inst_rows),
            "n_classifiable": sum(r["type"] is not None for r in inst_rows),
            "n_process": sum(r["type"] == "process" for r in inst_rows),
            "n_event_v": sum(r["type"] == "event_v" for r in inst_rows),
            "n_middle": sum(r["type"] == "middle" for r in inst_rows),
            "r60_median": _med([r["r60"] for r in inst_rows]),
            "r250_median": _med([r["r250"] for r in inst_rows]),
            "dd60_median": _med([r["dd60_pct"] for r in inst_rows]),
            "t_low60_median": _med([r["t_low60_days"] for r in inst_rows]),
            "recover_median": _med([r["recover_days"] for r in inst_rows]),
        })

    # 合并池判定
    pool = [e for e in events if e["type"] is not None]
    n_proc = sum(e["type"] == "process" for e in pool)
    n_v = sum(e["type"] == "event_v" for e in pool)
    n_mid = sum(e["type"] == "middle" for e in pool)
    qualified = [p for p in per_instr if p["n_events"] >= MIN_EVENTS_PER_INSTR]
    n_proc_majority = sum(
        p["n_process"] > max(p["n_event_v"], p["n_middle"]) for p in qualified)
    n_v_majority = sum(
        p["n_event_v"] > max(p["n_process"], p["n_middle"]) for p in qualified)

    if len(clusters) < 5:
        verdict = "insufficient"
    elif (n_proc >= DOMINANT_SHARE * len(pool)
          and n_proc_majority >= MIN_INSTR_FOR_MAJORITY):
        verdict = "process"
    elif (n_v >= DOMINANT_SHARE * len(pool)
          and n_v_majority >= MIN_INSTR_FOR_MAJORITY):
        verdict = "event"
    else:
        verdict = "mixed"

    result = {
        "corporate_action_adjustments": all_jumps,
        "raw_trigger_days": [str(pd.Timestamp(d).date()) for d in raw_triggers],
        "clusters": [str(pd.Timestamp(d).date()) for d in clusters],
        "n_raw_triggers": len(raw_triggers),
        "n_clusters": len(clusters),
        "per_instrument": per_instr,
        "events": events,
        "pool_counts": {"process": n_proc, "event_v": n_v, "middle": n_mid,
                        "total": len(pool)},
        "majority_counts": {"process_majority_instr": n_proc_majority,
                            "event_v_majority_instr": n_v_majority,
                            "qualified_instr": len(qualified)},
        "verdict": verdict,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True,
                         default=str)
    (OUT_DIR / "extreme_bottom_events.json").write_text(payload)
    print("hash:", hashlib.sha256(payload.encode()).hexdigest())
    print("clusters:", len(clusters), "verdict:", verdict)
    print("pool:", result["pool_counts"], "majority:", result["majority_counts"])
    for p in per_instr:
        print(p["symbol"], p["name"], p["sample_start"], "events=", p["n_events"],
              "proc/v/mid=", p["n_process"], p["n_event_v"], p["n_middle"],
              "r60_med=", p["r60_median"], "r250_med=", p["r250_median"],
              "dd60_med=", p["dd60_median"], "recov_med=", p["recover_median"])


def _med(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    s = sorted(xs)
    m = len(s) // 2
    return round((s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2), 2)


if __name__ == "__main__":
    sys.exit(main())
