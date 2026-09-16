# -*- coding: utf-8 -*-
"""任务 AN：双≥85 顶部结构事件研究（跨标的）——"顶部是事件还是过程"（卖出侧证据登记）。

预注册（跑前写死，跑后不得回头调整；本 docstring 即预注册全文）。

背景：双≥85 热度警戒 = 全A宽度 b50>=85 且 b200>=85 同日成立
（src/lei_signal/timing_backtest/service.py::alert_state, market="cn" → cn_all，
该文件不在在途修改集内，口径以工作区 HEAD 版本为准）。
本任务是描述性事件结构研究：不测任何卖出策略、不设计分批卖出规则、
不产生任何买卖规则。它是 AK（双≤20 底部结构研究）在高位侧的镜像登记。

事件定义（机械可复现）：
  - 事件日 = cn_all 宽度当日 b50>=85 且 b200>=85、且前一宽度交易日不同时满足
    （状态进入日）。
  - 簇合并（与 AK 同规则）：与前一保留事件日在宽度交易日历上间隔 <40 个交易日
    的新触发并入同簇不另计。主分析用簇合并后事件。
  - 稳健性预注册：同一管线在更严的 双≥90（b50>=90 且 b200>=90）线上重跑一遍，
    只登记计数与判定方向，不参与主判定。

标的网格（事件日须落在该标的有效样本内才计入；与 AK 完全同网格同路径）：
  - 创业板指 399006、沪深300 000300、中证1000ETF 512100、
    科创50 000688.SH、半导体ETF 512480。
  - 价格复用 AK 的公司行为修正规则：任一隔夜收盘比 >1.5 或 <1/1.5 视为
    拆分/合并，将其之前全部价格乘以该比率做前复权（同
    scripts/agent_AK/extreme_bottom_event_study.py）。
  - 宽度事件日在价格日历上向后对齐不超过 7 个自然日（同 AK）。

逐事件度量（事件日收盘 c0 为基准，全部 close-to-close；截尾窗口 250 交易日）：
  - 深度耗时 t5/t10/t20：事件日之后 250 交易日内首个 收盘<=c0*0.95 / 0.90 / 0.80
    的交易日序号；250 日内未出现记 None（截尾）。
  - t_below：事件日之后 250 交易日内首个 收盘<c0 的交易日序号（回落到警报日
    价之下要多久）；None=250 日内从未低于警报日收盘。
  - upside120 与 t_peak120：警报日及其后 120 交易日（含警报日共 121 个）窗口内
    最高收盘相对 c0 的剩余涨幅（磨顶期还能涨多少），及该最高点距警报日的
    交易日数（0 = 警报日即窗口最高）。new_high120 = 警报日之后是否出现
    收盘>c0（120 日窗口内）。
  - 前瞻收益 r20/r60/r120/r250（不足记缺失）。
  - dd60：事件后 60 交易日内最低收盘相对 c0 深度（AK 底部侧同名度量的镜像）。

"事件 vs 过程"逐事件机械判据（跑前写死，三分类；阈值来自任务书镜像 AK）：
  - 可分类条件：事件日后至少有 60 个交易日样本（不足则记不可分类、不入池）。
  - 急跌型（crash，事件）：t10 非空且 <=20 交易日（警报后 20 交易日内即跌穿
    -10%，晚离场价格惩罚大）。
  - 磨顶型（grind，过程）：t10 非空且 >40 交易日，或 t10 为空（250 交易日内
    未跌穿 -10%，单独打 censored 标记如实登记）。
  - 中间型（middle）：21 <= t10 <= 40。

预注册判定线（三选一，与 AK 完全同线）：
  - 簇总数 <5：直接证据不足。
  - 判"顶部偏事件（急跌）"：可分类样本合计 >=8，且合并池急跌型占比 >=60%，
    且 >=3 个标的（各自可分类事件数 >=2 才参与多数判定）急跌型严格占多数。
  - 判"顶部偏过程（磨顶）"：对称（磨顶型占比 >=60% 且 >=3 个标的磨顶型
    严格占多数；censored 样本计入磨顶型，其占比单列）。
  - 其余：混合（写明每个标的哪一型占优）。

红线遵守：不测卖出策略、不设计分批卖出规则、不产生任何买卖规则；
本报告全部为事件结构统计（描述性登记）。

输出：docs/experiments/raw/agent_AN/top_structure_events.json
"""
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

CACHE = Path.home() / ".lei_signal_lab/cache"
TIMING = CACHE / "timing"
OUT_DIR = Path(__file__).resolve().parents[2] / "docs/experiments/raw/agent_AN"

INSTRUMENTS = {
    "399006": ("创业板指", TIMING / "399006.parquet"),
    "000300": ("沪深300", TIMING / "000300.parquet"),
    "512100": ("中证1000ETF", TIMING / "512100.parquet"),
    "000688.SH": ("科创50", CACHE / "000688.SS.bars.parquet"),
    "512480": ("半导体ETF", TIMING / "512480.parquet"),
}

CLUSTER_GAP = 40            # 簇合并间隔（宽度交易日）
CENSOR = 250                # 深度耗时截尾窗口（交易日）
DEPTHS = {"t5": 0.95, "t10": 0.90, "t20": 0.80}
UPSIDE_WIN = 120            # 剩余涨幅窗口（交易日，警报日后）
FWD_RETS = [20, 60, 120, 250]
CRASH_T = 20                # 急跌型：t10 <= 20
GRIND_T = 40                # 磨顶型：t10 > 40（或 censored）
MIN_CLASS_FWD = 60          # 可分类最低前瞻样本量
MIN_EVENTS_TOTAL = 8        # 判定型最低合并样本
DOMINANT_SHARE = 0.60       # 合并池占比线
MIN_INSTR_FOR_MAJORITY = 3  # 多数标的线
MIN_EVENTS_PER_INSTR = 2    # 单标的参与多数判定的最低事件数
THRESH_MAIN = (85.0, 85.0)     # 主分析：双≥85（系统已验证高侧警报口径）
THRESH_ROBUST = (90.0, 90.0)   # 稳健性：双≥90


def adjust_corporate_actions(close: pd.Series) -> tuple[pd.Series, list]:
    """机械公司行为修正：隔夜 |涨跌| >50% 视为拆分/合并，前复权（同 AK）。"""
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


def build_clusters(b: pd.DataFrame, thr: tuple[float, float]):
    cond = (b["b50"] >= thr[0]) & (b["b200"] >= thr[1])
    entry = cond & (~cond.shift(1, fill_value=False))
    raw = list(b.index[entry])
    clusters = []
    for d in raw:
        if clusters and (b.index.get_loc(d) - b.index.get_loc(clusters[-1])) < CLUSTER_GAP:
            continue
        clusters.append(d)
    return raw, clusters


def measure(px: pd.Series, i: int) -> dict:
    c0 = float(px.iloc[i])
    n_fwd = len(px) - 1 - int(i)
    lim = min(CENSOR, n_fwd)
    row = {"n_fwd": n_fwd}
    for key, lvl in DEPTHS.items():
        t = None
        for k in range(1, lim + 1):
            if float(px.iloc[i + k]) <= c0 * lvl:
                t = k
                break
        row[key] = t
    t = None
    for k in range(1, lim + 1):
        if float(px.iloc[i + k]) < c0:
            t = k
            break
    row["t_below"] = t
    for w in FWD_RETS:
        j = i + w
        row[f"r{w}"] = round((float(px.iloc[j]) / c0 - 1) * 100, 2) if j < len(px) else None
    win60 = px.iloc[i + 1: i + 61]
    row["dd60_pct"] = round((float(win60.min()) / c0 - 1) * 100, 2) if len(win60) else None
    w120 = px.iloc[i: i + 1 + UPSIDE_WIN]
    if len(w120) > 1:
        row["upside120_pct"] = round((float(w120.max()) / c0 - 1) * 100, 2)
        row["t_peak120"] = int(w120.index.get_loc(w120.idxmax()))
        row["new_high120"] = bool(float(w120.iloc[1:].max()) > c0)
    else:
        row["upside120_pct"] = None
        row["t_peak120"] = None
        row["new_high120"] = None
    return row


def classify(t10, n_fwd):
    """预注册三分类。返回 (type, censored) 或 (None, False)=不可分类。"""
    if n_fwd < MIN_CLASS_FWD:
        return None, False
    if t10 is None:
        return "grind", True
    if t10 <= CRASH_T:
        return "crash", False
    if t10 <= GRIND_T:
        return "middle", False
    return "grind", False


def _med(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    s = sorted(xs)
    m = len(s) // 2
    return round((s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2), 2)


def _quart(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return {}
    s = pd.Series(xs, dtype=float)
    q1, q2, q3 = (round(float(s.quantile(q)), 2) for q in (0.25, 0.5, 0.75))
    return {"q1": q1, "med": q2, "q3": q3, "n": len(xs)}


def run_threshold(b: pd.DataFrame, thr) -> dict:
    raw, clusters = build_clusters(b, thr)
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
            m = measure(px, i)
            typ, censored = classify(m["t10"], m["n_fwd"])
            row = {
                "symbol": sym, "name": name,
                "event_date": str(pd.Timestamp(d).date()),
                "event_trade_date": str(pd.Timestamp(aligned).date()),
                **m, "type": typ, "censored": censored if typ else False,
            }
            events.append(row)
            inst_rows.append(row)
        per_instr.append({
            "symbol": sym, "name": name,
            "sample_start": str(pd.Timestamp(px.index.min()).date()),
            "sample_end": str(pd.Timestamp(px.index.max()).date()),
            "n_events": len(inst_rows),
            "n_classifiable": sum(r["type"] is not None for r in inst_rows),
            "n_crash": sum(r["type"] == "crash" for r in inst_rows),
            "n_grind": sum(r["type"] == "grind" for r in inst_rows),
            "n_censored": sum(r["censored"] for r in inst_rows),
            "n_middle": sum(r["type"] == "middle" for r in inst_rows),
            "t5_quart": _quart([r["t5"] for r in inst_rows]),
            "t10_quart": _quart([r["t10"] for r in inst_rows]),
            "t20_quart": _quart([r["t20"] for r in inst_rows]),
            "t10_censored_share": (
                round(sum(r["t10"] is None for r in inst_rows) / len(inst_rows), 3)
                if inst_rows else None),
            "t_below_quart": _quart([r["t_below"] for r in inst_rows]),
            "upside120_quart": _quart([r["upside120_pct"] for r in inst_rows]),
            "t_peak120_quart": _quart([r["t_peak120"] for r in inst_rows]),
            "new_high120_share": (
                round(sum(bool(r["new_high120"]) for r in inst_rows) / len(inst_rows), 3)
                if inst_rows else None),
            "dd60_median": _med([r["dd60_pct"] for r in inst_rows]),
            "r60_median": _med([r["r60"] for r in inst_rows]),
            "r120_median": _med([r["r120"] for r in inst_rows]),
            "r250_median": _med([r["r250"] for r in inst_rows]),
        })

    pool = [e for e in events if e["type"] is not None]
    n_crash = sum(e["type"] == "crash" for e in pool)
    n_grind = sum(e["type"] == "grind" for e in pool)
    n_cens = sum(e["censored"] for e in pool)
    n_mid = sum(e["type"] == "middle" for e in pool)
    qualified = [p for p in per_instr if p["n_classifiable"] >= MIN_EVENTS_PER_INSTR]
    n_crash_maj = sum(
        p["n_crash"] > max(p["n_grind"], p["n_middle"]) for p in qualified)
    n_grind_maj = sum(
        p["n_grind"] > max(p["n_crash"], p["n_middle"]) for p in qualified)

    if len(clusters) < 5:
        verdict = "insufficient"
    elif (len(pool) >= MIN_EVENTS_TOTAL
          and n_crash >= DOMINANT_SHARE * len(pool)
          and n_crash_maj >= MIN_INSTR_FOR_MAJORITY):
        verdict = "event_crash"
    elif (len(pool) >= MIN_EVENTS_TOTAL
          and n_grind >= DOMINANT_SHARE * len(pool)
          and n_grind_maj >= MIN_INSTR_FOR_MAJORITY):
        verdict = "process_grind"
    else:
        verdict = "mixed"

    pooled = {
        "t5_quart": _quart([e["t5"] for e in pool]),
        "t10_quart": _quart([e["t10"] for e in pool]),
        "t20_quart": _quart([e["t20"] for e in pool]),
        "t10_censored_share": round(n_cens / len(pool), 3) if pool else None,
        "t_below_quart": _quart([e["t_below"] for e in pool]),
        "upside120_quart": _quart([e["upside120_pct"] for e in pool]),
        "t_peak120_quart": _quart([e["t_peak120"] for e in pool]),
        "new_high120_share": (
            round(sum(bool(e["new_high120"]) for e in pool) / len(pool), 3)
            if pool else None),
        "dd60_median": _med([e["dd60_pct"] for e in pool]),
        "r60_median": _med([e["r60"] for e in pool]),
        "r250_median": _med([e["r250"] for e in pool]),
    }
    return {
        "threshold": {"b50_min": thr[0], "b200_min": thr[1]},
        "corporate_action_adjustments": all_jumps,
        "raw_trigger_days": [str(pd.Timestamp(d).date()) for d in raw],
        "clusters": [str(pd.Timestamp(d).date()) for d in clusters],
        "n_raw_triggers": len(raw),
        "n_clusters": len(clusters),
        "per_instrument": per_instr,
        "events": events,
        "pool_counts": {"crash": n_crash, "grind": n_grind,
                        "grind_censored": n_cens, "middle": n_mid,
                        "total": len(pool)},
        "majority_counts": {"crash_majority_instr": n_crash_maj,
                            "grind_majority_instr": n_grind_maj,
                            "qualified_instr": len(qualified)},
        "pooled_stats": pooled,
        "verdict": verdict,
    }


def main() -> None:
    breadth = pd.read_parquet(TIMING / "breadth_cn_all.parquet")
    b = breadth[["b50", "b200"]].dropna()
    result = {
        "main_85": run_threshold(b, THRESH_MAIN),
        "robust_90": run_threshold(b, THRESH_ROBUST),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True,
                         default=str)
    (OUT_DIR / "top_structure_events.json").write_text(payload)
    print("hash:", hashlib.sha256(payload.encode()).hexdigest())
    for key in ("main_85", "robust_90"):
        r = result[key]
        print(f"== {key} (b50>={r['threshold']['b50_min']}, b200>={r['threshold']['b200_min']}) ==")
        print("clusters:", r["n_clusters"], "verdict:", r["verdict"])
        print("pool:", r["pool_counts"], "majority:", r["majority_counts"])
        print("pooled:", r["pooled_stats"])
        for p in r["per_instrument"]:
            print(p["symbol"], p["name"], p["sample_start"], "ev=", p["n_events"],
                  "crash/grind(cens)/mid=", p["n_crash"], p["n_grind"],
                  f"({p['n_censored']})", p["n_middle"],
                  "t10=", p["t10_quart"], "up120=", p["upside120_quart"],
                  "newhigh=", p["new_high120_share"])


if __name__ == "__main__":
    sys.exit(main())
