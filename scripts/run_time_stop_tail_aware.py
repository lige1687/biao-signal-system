#!/usr/bin/env python3
"""时间止损接受右尾——前置「持仓分类器」事件研究（2026-09-02，任务 M）。

【研究问题与任务定位（机制假设，事前写死）】
stop-loss-matrix-ARCHIVE-2026-09-01 已证：①41+ 天长持单占 A/B/C 合计利润
134%（本仓口径），是系统收益核心；②「无进展」型时间止损（N=10：入场以来
最高收盘≤入场价才触发）不砍右尾但代价是收益趋近于零（ΔexpR≈0.014R 封顶）。
本任务反向设计：不问「能不能设计不伤右尾的时间止损」，而问「入场后第 K 日
的浮盈状态能否提前识别右尾潜质」——若能，则时间止损只需对**无右尾潜质**
的持仓生效（分类器豁免有潜质组）；若不能，则「右尾早期不可分类」本身
归档证伪。**明确不测**「持仓超 N 日无条件离场」（stop-loss-matrix 先验
判定为自杀式配置）；不产生买卖点。

【数据基础（与 stop_loss_matrix 不同源的声明，必读）】
stop_loss_matrix 的 175 标的全池逐笔（~/.lei_signal_lab/backtest_runs/
20260831-*.json）与池数据（~/.lei_signal_lab/backtest_pool/）在本次实验
开机排查时已确认**丢失**（目录不存在，stash 已清空，服务进程已停）。本实验
改用仓库内已归档的**其他实验逐笔 run**（同一引擎口径 a6_1_costbasis 出场、
含 entry/exit 日期与价格、r_net、holding_bars）：
- 冻结配置组（与 stop_loss_matrix 模块冻结配置一致）：
  A_cn = raw/lifecycle_combo/T2_A_ETF_cm05_shrink.json（A=early+shrink+cm0.5，45 只 CN ETF）
  Bp_cn = raw/lifecycle_combo/T1_Bp_a61.json（B=breakout+cb30/cl3%，CN 股票）
  C_cn = raw/lifecycle_combo/T2_C_stocks_v3_b15.json（C=v3+深乖离-0.15，83 只 CN 股票）
  A_us = raw/stage_b200/A_us.json（A=early+shrink+cm0.5，IGV/SOXX/XLK）
- 变体组（配置偏离冻结值，事前声明、用于机制层加功率，不单独下结论）：
  B_us（B=cb20/cl10%）、wf_a_noshrink（A 去量缩过滤）、wf_a_cm10（A cm1.0）、
  wf_bp_202（B=cb20/cl2%）、wf_bp_404（B=cb40/cl4%）。
K 线来源（离线，不重跑信号）：~/.lei_signal_lab/cache/*.bars.parquet 与
tests/*.bars.parquet（OHLCV，取并集按更长者）+ ~/.lei_signal_lab/cache/
a_share_klines.parquet（仅 close，2023-05 起，用于 CN 股票）。**价格基准
一致性预检（判定标准 G0）**：structure_stop_C 笔的确认 bar（exit 前一交易
bar）收盘必须 < stop_price，失配率 >5% 则该 K 线源整体作废。
预检实测（2026-09-02）：可核验 36 笔，失配 0，通过。

【事件研究设计（事前固化）】
- 分类时点 K=10（主），敏感性 K∈{5,15}。分类总体 = 当日仍持仓的交易
  （holding_bars ≥ K；holding_bars 口径与引擎一致 = exit_pos − entry_pos，
  第 K 日收盘存在于 entry_pos+K−1 ≤ exit_pos−1）。
- 状态变量（R 单位，risk = entry_price − stop_price）：
  r_at_k = (close[K] − entry_price)/risk；
  peak_r_at_k = max close[1..K] 相对 entry 的 R（对齐「无进展」定义）。
- 分类器（预注册阈值网格，主判定 θ=0）：
  G_hi(θ) = {r_at_k > θ}（有右尾潜质），G_lo(θ) = {r_at_k ≤ θ}（低质量）。
  网格 θ∈{0, 0.25, 0.5, 1.0}；斜率变体（近 5 bar 斜率>0 且 r>θ）仅敏感性。
- 终点：主终点 Y = 1[holding_bars ≥ 41]（stop_loss_matrix 右尾同口径，
  交易 bar 数）；次终点（探索性）：final r_net 均值/中位数、1[r_net ≥ 5R]。
- 主检验（唯一，其余全部标注敏感性/探索性）：pooled 全样本（冻结+变体，
  按 (module, symbol, signal_date) 去重、冻结优先），K=10，θ=0：
  Δp = p(Y=1|G_hi) − p(Y=1|G_lo)，逐笔 bootstrap（10000 次，固定种子
  numpy RandomState(20260902)，percentile 95% CI）+ Fisher 精确检验
  （双侧，自实现）交叉核对。显著 = CI 下界 > 0 且 Fisher p < 0.05。

【判定标准（事前写死，跑后不得调整）】
- G0 价格基准预检：structure_stop_C 可核验笔失配率 ≤5%（否则 K 线源作废、
  全实验中止报欠账）。
- P0 功效门槛：主检验样本 n(G_lo,θ=0) ≥ 30 且 41+ 事件总数 ≥ 50；冻结组
  单独复算但只作方向参考（样本量如实报告，不单独下结论）。
- V1 统计有效：主检验 CI 下界 > 0 且 Fisher p<0.05。
- V2 右尾保护：θ=0 下 41+ 单落入 G_lo 的比例 ≤20%（即 ≥80% 右尾被豁免）。
- V3 经济梯度：G_lo 组 final r_net 均值 < G_hi 组（方向性支持，不设显著性）。
- 分类有效 = V1 且 V2（V3 仅报告）；否则归档证伪/不可判定，**不进入第二步**。
- 第二步（仅当分类有效；网格事前固化 θ∈{0,0.5} × M∈{5,10}，外加参照臂）：
  规则 R(K,θ,M)：K 日 r_at_k ≤ θ 的持仓，若 K+M 日 r_at_{K+M} 仍 ≤ θ，
  则 K+M 收盘确认、次根开盘离场；r_at_k > θ 的持仓完全豁免（默认出场不变）。
  参照臂 = 无条件无进展时间止损 N=K+M（stop_loss_matrix 同型，同样本内重放）。
  执行：OHLCV 源按引擎语义（收盘确认、次根开盘、CN 跌停跳过
  open≤0.905×prev_close、FeeModel standard=单边 max(5bp, $0.005/股)）；
  close-only 源无开盘价，退化为触发日收盘价成交（声明口径，单独报告、
  不并入 OHLCV 主行）。判定：ΔexpR ≥ +0.05R（显著高于 stop_loss_matrix
  的 ≤0.014R 经济意义线）且配对 bootstrap 95% CI 下界>0 且 41+ 单净 R
  保留率 ≥95% → 通过；否则判负。分模块分解表（均盈/均亏/持仓/触发/
  41+ 保留）对齐 exit-structural-stop-revival 格式。
- 敏感性（K=5/15、θ 网格、斜率变体、冻结组单独、去 US）全部只标注方向，
  不得 overturn 或补强主判定。

【安全约束】只读研究：不改 src/ 生产代码（FeeModel 公式按 engine.py 62-85
行逐字复刻，不 import 以避免账本依赖）、不 push、不删文件；新增产出仅
本脚本 + docs/experiments/raw/time_stop_tail_aware/。

【复现】解释器：/Users/liyongbiao/Desktop/biao-signal-system/.venv/bin/python
（pandas 2.3.3 / numpy 2.5.2；系统 python3 无 pandas）。
PYTHONHASHSEED=0 / 42 各跑一次 --dump-hash，md5 一致才入档。

【与策略体系的溯源关系】本实验属于出场/风控纪律层研究：检验「入场触发后
的持仓质量分类」是否可承载时间止损的差异化施加（规格第 2.3 节「什么逻辑
进场，就用什么逻辑退出」的延伸问句：出场纪律能否按持仓早期状态分型）。
一切结论为 research_proxy 建议级。
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
RAW_BASE = REPO / "docs" / "experiments" / "raw"
OUT_DIR = RAW_BASE / "time_stop_tail_aware"
CACHE_BARS = Path.home() / ".lei_signal_lab" / "cache"
KLINES = Path.home() / ".lei_signal_lab" / "cache" / "a_share_klines.parquet"
TESTS_BARS = REPO / "tests"

K_PRIMARY = 10
K_SENS = (5, 15)
THETA_GRID = (0.0, 0.25, 0.5, 1.0)
HOLD_TAIL = 41  # holding_bars >= 41 = 右尾长持单（stop_loss_matrix 同口径）
BOOT_N = 10_000
BOOT_SEED = 20_260_902
INVALID_REASONS = {
    "invalid_nonpositive_risk", "skipped_limit_up_at_entry", "signal_at_end_not_entered",
}
# 模块冻结配置（对齐 stop_loss_matrix / exit-matrix）：
# A=early+shrink+cm0.5；B'=breakout+cb30/cl3%；C=v3+深乖离-0.15。
RUN_FILES = [
    # (样本键, 相对路径, 模块, 组别 frozen/variant, 去重优先级)
    ("A_cn", "lifecycle_combo/T2_A_ETF_cm05_shrink.json", "A", "frozen", 0),
    ("Bp_cn", "lifecycle_combo/T1_Bp_a61.json", "B", "frozen", 0),
    ("C_cn", "lifecycle_combo/T2_C_stocks_v3_b15.json", "C", "frozen", 0),
    ("A_us", "stage_b200/A_us.json", "A", "frozen", 0),
    ("B_us", "stage_b200/B_us.json", "B", "variant", 1),
    ("A_noshrink", "breadth_overlay/wf_a_noshrink.json", "A", "variant", 2),
    ("A_cm10", "breadth_overlay/wf_a_cm10.json", "A", "variant", 3),
    ("Bp202", "breadth_overlay/wf_bp_202.json", "B", "variant", 4),
    ("Bp404", "breadth_overlay/wf_bp_404.json", "B", "variant", 5),
]
# 第二步网格（事前固化）
STEP2_THETA = (0.0, 0.5)
STEP2_M = (5, 10)


# ---------------------------------------------------------------- 数据装载
def load_bars() -> dict[str, pd.DataFrame]:
    bars: dict[str, pd.DataFrame] = {}
    for root in (CACHE_BARS, TESTS_BARS):
        for p in sorted(root.glob("*.bars.parquet")):
            sym = p.name[: -len(".bars.parquet")]
            df = pd.read_parquet(p)
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
                df = df.set_index("date")
            df = df[~df.index.duplicated(keep="last")]
            df = df[[c for c in ("open", "high", "low", "close") if c in df.columns]]
            df = df.astype(float)
            if sym not in bars or len(df) > len(bars[sym]):
                bars[sym] = df
    return bars


def load_close_only() -> dict[str, pd.Series]:
    df = pd.read_parquet(KLINES)
    out: dict[str, pd.Series] = {}
    for sym, g in df.groupby("symbol", sort=True):
        g = g.set_index(pd.to_datetime(g["date"]))
        g = g[~g.index.duplicated(keep="last")]
        out[str(sym)] = g["close"].astype(float)
    return out


def sym_to_kl(symbol: str) -> str | None:
    if "." not in symbol:
        return None
    code, mkt = symbol.split(".")
    return ("sh" if mkt == "SS" else "sz") + code


def is_cn(symbol: str) -> bool:
    return symbol.endswith(".SS") or symbol.endswith(".SZ")


class PriceBasisError(RuntimeError):
    pass


def validate_price_basis(trades_rows: list[dict], bars, close_only) -> dict:
    """G0：structure_stop_C 笔的确认 bar（exit 前一根）收盘必须 < stop_price。"""
    ok = bad = nodata = 0
    for t in trades_rows:
        if t["exit_reason"] != "structure_stop_C" or t["r_net"] is None:
            continue
        ser = None
        s = t["symbol"]
        xd = pd.Timestamp(t["exit_date"])
        if s in bars:
            ser = bars[s]["close"]
        else:
            ks = sym_to_kl(s)
            ser = close_only.get(ks) if ks else None
        if ser is None or xd not in ser.index:
            nodata += 1
            continue
        pos = ser.index.get_loc(xd)
        if pos == 0:
            nodata += 1
            continue
        if float(ser.iloc[pos - 1]) < float(t["stop_price"]):
            ok += 1
        else:
            bad += 1
    checked = ok + bad
    rate = (bad / checked) if checked else float("nan")
    return {"checked": checked, "ok": ok, "bad": bad, "nodata": nodata,
            "mismatch_rate": rate}


# ---------------------------------------------------------------- 事件表构建
def build_events(bars, close_only) -> tuple[list[dict], dict]:
    """逐笔事件表：分类总体 = alive@K（holding_bars ≥ K_PRIMARY）。"""
    seen: dict[tuple, int] = {}
    events: list[dict] = []
    coverage = {}
    for key, rel, module, group, prio in RUN_FILES:
        data = json.loads((RAW_BASE / rel).read_text(encoding="utf-8"))
        kept = dropped_dup = not_closed = no_cov = 0
        for t in data["trades"]:
            if t["r_net"] is None or t["exit_reason"] in INVALID_REASONS:
                not_closed += 1
                continue
            s = t["symbol"]
            ed = pd.Timestamp(t["entry_date"])
            src = ser = None
            if s in bars and ed in bars[s]["close"].index:
                ser, src = bars[s]["close"], "ohlcv"
            else:
                ks = sym_to_kl(s)
                if ks and ks in close_only and ed in close_only[ks].index:
                    ser, src = close_only[ks], "close"
            if ser is None:
                no_cov += 1
                continue
            pos = ser.index.get_loc(ed)
            kmax = max(K_SENS + (K_PRIMARY,))
            if pos + kmax - 1 >= len(ser):
                no_cov += 1
                continue
            if (ser.index[pos + K_PRIMARY - 1] - ed).days > 60:  # 停牌防护
                no_cov += 1
                continue
            dedup = (module, s, t["signal_date"])
            if dedup in seen and seen[dedup] <= prio:
                dropped_dup += 1
                continue
            seen[dedup] = prio
            risk = float(t["entry_price"]) - float(t["stop_price"])
            row = {
                "sample": key, "module": module, "group": group,
                "symbol": s, "signal_date": t["signal_date"],
                "entry_date": t["entry_date"],
                "entry_price": float(t["entry_price"]),
                "stop_price": float(t["stop_price"]),
                "exit_date": t["exit_date"],
                "exit_reason": t["exit_reason"],
                "holding_bars": int(t["holding_bars"]),
                "r_net": float(t["r_net"]),
                "is_tail": int(t["holding_bars"]) >= HOLD_TAIL,
                "src": src, "risk": risk,
            }
            for K in (K_SENS + (K_PRIMARY,)):
                row[f"r_at_{K}"] = (
                    float(ser.iloc[pos + K - 1]) - row["entry_price"]
                ) / risk
                peaks = [float(ser.iloc[pos + i]) for i in range(K)]
                row[f"peak_r_at_{K}"] = (
                    max(peaks) - row["entry_price"]
                ) / risk
            # 斜率敏感性（近5bar）：close[K]−close[K−5] 的 R 化
            for K in (K_SENS + (K_PRIMARY,)):
                c_k = float(ser.iloc[pos + K - 1])
                c_prev = float(ser.iloc[max(pos, pos + K - 6)])
                row[f"slope5_r_at_{K}"] = (c_k - c_prev) / risk
            row["_ser"] = ser
            row["_pos"] = pos
            events.append(row)
            kept += 1
        coverage[key] = {
            "file": rel, "module": module, "group": group,
            "kept": kept, "dropped_dup": dropped_dup,
            "not_closed": not_closed, "no_coverage_or_guard": no_cov,
        }
    return events, coverage


# ---------------------------------------------------------------- 统计工具
def prop_boot_ci(hi: np.ndarray, lo: np.ndarray) -> tuple[float, float, float]:
    """逐笔 bootstrap：重采样合并总体后按原组大小分配（分层 bootstrap，
    与 stop_loss_matrix 配对 bootstrap 同族、固定种子）。返回 (Δp 点估计, lo, hi)。"""
    rng = np.random.RandomState(BOOT_SEED)
    n_hi, n_lo = len(hi), len(lo)
    p_hi = hi.mean() if n_hi else float("nan")
    p_lo = lo.mean() if n_lo else float("nan")
    deltas = np.empty(BOOT_N)
    for b in range(BOOT_N):
        bh = hi[rng.randint(0, n_hi, n_hi)] if n_hi else np.array([0.0])
        bl = lo[rng.randint(0, n_lo, n_lo)] if n_lo else np.array([0.0])
        deltas[b] = bh.mean() - bl.mean()
    clo, chi = np.percentile(deltas, [2.5, 97.5])
    return float(p_hi - p_lo), float(clo), float(chi)


def fisher_exact_2x2(a: int, b: int, c: int, d: int) -> float:
    """双侧 Fisher 精确检验（自实现，无 scipy 依赖）。a/b/c/d = [[a,b],[c,d]]。"""
    n = a + b + c + d
    if n == 0:
        return float("nan")
    probs = []
    row1, col1 = a + b, a + c
    lo_k = max(0, row1 + col1 - n)
    hi_k = min(row1, col1)
    denom = math.comb(n, row1)
    pmass = {}
    for k in range(lo_k, hi_k + 1):
        k2 = row1 - k
        c2 = col1 - k
        d2 = n - row1 - col1 + k
        if k2 < 0 or c2 < 0 or d2 < 0:
            continue
        p = (
            math.comb(col1, k) * math.comb(n - col1, k2) / denom
        )
        pmass[k] = p
    p_obs = pmass.get(a, 0.0)
    return float(sum(p for p in pmass.values() if p <= p_obs + 1e-12))


# ---------------------------------------------------------------- Step 1
def run_step1(events: list[dict], out: dict) -> dict:
    alive = [e for e in events if e["holding_bars"] >= K_PRIMARY]
    dead = [e for e in events if e["holding_bars"] < K_PRIMARY]
    out["step1_population"] = {
        "total_events": len(events),
        "alive_at_K10": len(alive),
        "alive_tail_count": sum(e["is_tail"] for e in alive),
        "tail_rate_alive": sum(e["is_tail"] for e in alive) / len(alive),
        "alive_by_src": {
            src: sum(1 for e in alive if e["src"] == src)
            for src in sorted({e["src"] for e in alive})
        },
        "exited_before_K10": {
            "n": len(dead),
            "sum_r_net": sum(e["r_net"] for e in dead),
            "mean_r_net": (sum(e["r_net"] for e in dead) / len(dead)) if dead else None,
            "by_exit_reason": {
                r: sum(1 for e in dead if e["exit_reason"] == r)
                for r in sorted({e["exit_reason"] for e in dead})
            },
        },
    }
    st = np.array([e[f"r_at_{K_PRIMARY}"] for e in alive])
    hb = np.array([e["is_tail"] for e in alive])
    rn = np.array([e["r_net"] for e in alive])

    # 主检验：K=10, θ=0, pooled 全样本
    hi_m = st > 0.0
    lo_m = ~hi_m
    a = int(((hb == 1) & hi_m).sum()); b = int(((hb == 1) & lo_m).sum())
    c = int(((hb == 0) & hi_m).sum()); d = int(((hb == 0) & lo_m).sum())
    dp, clo, chi = prop_boot_ci(hb[hi_m], hb[lo_m])
    fisher = fisher_exact_2x2(a, b, c, d)
    power_ok = int(lo_m.sum()) >= 30 and int(hb.sum()) >= 50
    primary = {
        "n_hi": int(hi_m.sum()), "n_lo": int(lo_m.sum()),
        "p_tail_hi": float(hb[hi_m].mean()) if hi_m.sum() else None,
        "p_tail_lo": float(hb[lo_m].mean()) if lo_m.sum() else None,
        "delta_p": dp, "boot_ci95": [clo, chi],
        "fisher_p": fisher, "fisher_table": [[a, b], [c, d]],
        "power_gate_P0": power_ok,
        "V1_significant": bool(clo > 0 and fisher < 0.05),
    }
    out["step1_primary"] = primary

    # V2：θ=0 下右尾保护率
    tail_in_lo = int(((hb == 1) & lo_m).sum())
    out["step1_V2_protection"] = {
        "tail_total": int(hb.sum()), "tail_in_G_lo": tail_in_lo,
        "protection_rate": 1 - tail_in_lo / int(hb.sum()),
        "V2_pass": tail_in_lo / int(hb.sum()) <= 0.20,
    }

    # V3：经济梯度
    m_hi = float(rn[hi_m].mean()) if hi_m.sum() else None
    m_lo = float(rn[lo_m].mean()) if lo_m.sum() else None
    out["step1_V3_gradient"] = {
        "mean_rnet_hi": m_hi, "mean_rnet_lo": m_lo,
        "median_rnet_hi": float(np.median(rn[hi_m])) if hi_m.sum() else None,
        "median_rnet_lo": float(np.median(rn[lo_m])) if lo_m.sum() else None,
        "V3_directional": (m_hi is not None and m_lo is not None and m_lo < m_hi),
    }

    # θ 网格 & K 敏感性（预注册敏感性，不作判定）
    grid = []
    for K in (K_SENS + (K_PRIMARY,)):
        stk = np.array([e[f"r_at_{K}"] for e in alive if e["holding_bars"] >= K])
        hbk = np.array([e["is_tail"] for e in alive if e["holding_bars"] >= K])
        rnk = np.array([e["r_net"] for e in alive if e["holding_bars"] >= K])
        for th in THETA_GRID:
            hi = stk > th
            lo = ~hi
            if not lo.sum() or not hi.sum():
                continue
            dpk, clok, chik = prop_boot_ci(hbk[hi], hbk[lo])
            fk = fisher_exact_2x2(
                int(((hbk == 1) & hi).sum()), int(((hbk == 1) & lo).sum()),
                int(((hbk == 0) & hi).sum()), int(((hbk == 0) & lo).sum()),
            )
            grid.append({
                "K": K, "theta": th, "n": int(len(stk)),
                "n_hi": int(hi.sum()), "n_lo": int(lo.sum()),
                "p_tail_hi": float(hbk[hi].mean()), "p_tail_lo": float(hbk[lo].mean()),
                "delta_p": dpk, "boot_ci95": [clok, chik], "fisher_p": fk,
                "tail_in_G_lo": int(((hbk == 1) & lo).sum()),
                "mean_rnet_hi": float(rnk[hi].mean()),
                "mean_rnet_lo": float(rnk[lo].mean()),
            })
    out["step1_theta_grid"] = grid

    # 斜率变体（敏感性，仅 K=10 θ=0）
    slope = np.array([e[f"slope5_r_at_{K_PRIMARY}"] for e in alive])
    hi_s = (st > 0.0) & (slope > 0)
    lo_s = ~hi_s
    if lo_s.sum() and hi_s.sum():
        dps, clos, chis = prop_boot_ci(hb[hi_s], hb[lo_s])
        out["step1_slope_variant"] = {
            "n_hi": int(hi_s.sum()), "n_lo": int(lo_s.sum()),
            "p_tail_hi": float(hb[hi_s].mean()), "p_tail_lo": float(hb[lo_s].mean()),
            "delta_p": dps, "boot_ci95": [clos, chis],
        }

    # 冻结组单独复算（方向参考）
    fz = [e for e in alive if e["group"] == "frozen"]
    stf = np.array([e[f"r_at_{K_PRIMARY}"] for e in fz])
    hbf = np.array([e["is_tail"] for e in fz])
    rnf = np.array([e["r_net"] for e in fz])
    hif = stf > 0.0
    if hif.sum() and (~hif).sum():
        dpf, clof, chif = prop_boot_ci(hbf[hif], hbf[~hif])
        ff = fisher_exact_2x2(
            int(((hbf == 1) & hif).sum()), int(((hbf == 1) & (~hif)).sum()),
            int(((hbf == 0) & hif).sum()), int(((hbf == 0) & (~hif)).sum()),
        )
        out["step1_frozen_only"] = {
            "n": len(fz), "n_hi": int(hif.sum()), "n_lo": int((~hif).sum()),
            "tail_total": int(hbf.sum()),
            "p_tail_hi": float(hbf[hif].mean()), "p_tail_lo": float(hbf[~hif].mean()),
            "delta_p": dpf, "boot_ci95": [clof, chif], "fisher_p": ff,
            "declared_underpowered": True,
        }

    # 分模块（样本量如实报告）
    bymod = {}
    for mod in sorted({e["module"] for e in alive}):
        sub = [e for e in alive if e["module"] == mod]
        stm = np.array([e[f"r_at_{K_PRIMARY}"] for e in sub])
        hbm = np.array([e["is_tail"] for e in sub])
        him = stm > 0.0
        bymod[mod] = {
            "n": len(sub), "n_hi": int(him.sum()), "n_lo": int((~him).sum()),
            "tail_total": int(hbm.sum()),
            "p_tail_hi": float(hbm[him].mean()) if him.sum() else None,
            "p_tail_lo": float(hbm[~him].mean()) if (~him).sum() else None,
            "note_module_level_no_verdict": True,
        }
    out["step1_by_module"] = bymod

    # 机制描述：右尾单的早期 R 分布（对 stop_loss_matrix「早期必有浮盈」量化）
    tails = [e for e in alive if e["is_tail"]]
    out["step1_mechanism"] = {
        "tail_early_r_at_10": {
            "n": len(tails),
            "min": min(e[f"r_at_{K_PRIMARY}"] for e in tails),
            "p25": float(np.percentile([e[f"r_at_{K_PRIMARY}"] for e in tails], 25)),
            "median": float(np.median([e[f"r_at_{K_PRIMARY}"] for e in tails])),
            "max": max(e[f"r_at_{K_PRIMARY}"] for e in tails),
        },
        "tail_peak_r_at_10": {
            "n": len(tails),
            "min": min(e[f"peak_r_at_{K_PRIMARY}"] for e in tails),
            "median": float(np.median([e[f"peak_r_at_{K_PRIMARY}"] for e in tails]),
                            ),
        },
        "tail_with_no_profit_by_K10": sum(
            1 for e in tails if e[f"peak_r_at_{K_PRIMARY}"] <= 0
        ),
        "nortail_median_r_at_10": float(np.median(
            [e[f"r_at_{K_PRIMARY}"] for e in alive if not e["is_tail"]])),
    }

    verdict = {
        "V1": primary["V1_significant"],
        "V2": out["step1_V2_protection"]["V2_pass"],
        "V3": out["step1_V3_gradient"]["V3_directional"],
        "P0": power_ok,
        "classifier_effective": bool(
            primary["V1_significant"] and out["step1_V2_protection"]["V2_pass"]
        ),
    }
    out["step1_verdict"] = verdict
    return verdict


# ---------------------------------------------------------------- Step 2
def fee_round_trip(price: float) -> float:
    """engine.FeeModel(standard) 逐字复刻：2 × max(5bp, $0.005/price)。"""
    if price <= 0:
        return 0.0
    per_side = max(5.0 / 10_000.0, 0.005 / price)
    return 2.0 * per_side


def r_net_of(entry: float, exitp: float, risk: float) -> float:
    fees = fee_round_trip(entry)
    return ((exitp / entry - 1.0) - fees) * (entry / risk)


def run_step2(events: list[dict], out: dict) -> None:
    """第二步：条件时间止损 vs 无条件 N 参照 vs 基线（同一归档样本内重放）。"""
    alive = [e for e in events if e["holding_bars"] >= K_PRIMARY]
    # 重新绑定 OHLCV open 序列（build_events 只存了 close series）
    bars = load_bars()

    def open_series(e):
        return bars[e["symbol"]]["open"] if e["src"] == "ohlcv" else None

    def exit_price_at(e, T):
        """T 收盘确认 → 次根开盘（OHLCV，CN 跌停跳过）；close-only 退化收盘。"""
        ser, pos = e["_ser"], e["_pos"]
        if e["src"] == "ohlcv":
            ops = open_series(e)
            exit_pos = pos + T
            cls = ser
            while (
                is_cn(e["symbol"])
                and exit_pos + 1 < len(cls)
                and float(cls.iloc[exit_pos]) > 0
                and exit_pos >= 1
                and float(ops.iloc[exit_pos])
                <= float(cls.iloc[exit_pos - 1]) * 0.905
            ):
                exit_pos += 1
            if exit_pos >= len(cls):
                return None, None, "limit_guard_reached_end"
            return float(ops.iloc[exit_pos]), exit_pos - pos, None
        return float(ser.iloc[pos + T - 1]), T, "close_only_exit_at_trigger_close"

    base_r = np.array([e["r_net"] for e in alive])
    cells = []
    for theta in STEP2_THETA:
        for M in STEP2_M:
            T = K_PRIMARY + M
            var_r, notes = [], []
            trig = trig_tail = 0
            tail_cut_r = 0.0
            tail_keep_r = 0.0
            for e in alive:
                if e["holding_bars"] < T or e[f"r_at_{K_PRIMARY}"] > theta:
                    var_r.append(e["r_net"])
                    if e["is_tail"]:
                        tail_keep_r += e["r_net"]
                    continue
                r_t = (float(e["_ser"].iloc[e["_pos"] + T - 1]) - e["entry_price"]) / e["risk"]
                if r_t > theta:
                    var_r.append(e["r_net"])
                    if e["is_tail"]:
                        tail_keep_r += e["r_net"]
                    continue
                xp, hb_new, note = exit_price_at(e, T)
                if xp is None:
                    var_r.append(e["r_net"])
                    notes.append(note)
                    if e["is_tail"]:
                        tail_keep_r += e["r_net"]
                    continue
                new_r = r_net_of(e["entry_price"], xp, e["risk"])
                var_r.append(new_r)
                trig += 1
                if e["is_tail"]:
                    trig_tail += 1
                    tail_cut_r += e["r_net"]
                notes.append(note or "triggered")
            var_r = np.array(var_r)
            cells.append({
                "kind": "conditional", "K": K_PRIMARY, "theta": theta, "M": M,
                "n": len(alive), "triggered": trig,
                "triggered_tail": trig_tail,
                "expR": float(var_r.mean()), "base_expR": float(base_r.mean()),
                "delta_expR": float(var_r.mean() - base_r.mean()),
                "tail_R_kept": tail_keep_r, "tail_R_cut_baseline": tail_cut_r,
                "tail_R_retention": (
                    tail_keep_r / (tail_keep_r + tail_cut_r)
                    if (tail_keep_r + tail_cut_r) else None
                ),
                "exit_notes": {n: notes.count(n) for n in sorted(set(notes))},
            })
    # 无条件无进展 N 参照（stop_loss_matrix 同型，同一样本重放）
    for N in (K_PRIMARY + 5, K_PRIMARY + 10):
        var_r = []
        trig = trig_tail = 0
        tail_cut_r = tail_keep_r = 0.0
        for e in alive:
            if e["holding_bars"] >= N:
                peak_N = max(float(e["_ser"].iloc[e["_pos"] + i]) for i in range(N))
                if peak_N <= e["entry_price"]:
                    # N 日收盘确认次根开盘（无进展 → exit at N）
                    xp, hb_new, note = exit_price_at(e, N)
                    if xp is None:
                        var_r.append(e["r_net"])
                        continue
                    new_r = r_net_of(e["entry_price"], xp, e["risk"])
                    var_r.append(new_r)
                    trig += 1
                    if e["is_tail"]:
                        trig_tail += 1
                        tail_cut_r += e["r_net"]
                    continue
            var_r.append(e["r_net"])
            if e["is_tail"]:
                tail_keep_r += e["r_net"]
        var_r = np.array(var_r)
        cells.append({
            "kind": "plain_N_noprogress", "N": N, "n": len(alive),
            "triggered": trig, "triggered_tail": trig_tail,
            "expR": float(var_r.mean()), "base_expR": float(base_r.mean()),
            "delta_expR": float(var_r.mean() - base_r.mean()),
            "tail_R_kept": tail_keep_r, "tail_R_cut_baseline": tail_cut_r,
            "tail_R_retention": (
                tail_keep_r / (tail_keep_r + tail_cut_r)
                if (tail_keep_r + tail_cut_r) else None
            ),
        })
    # 配对 bootstrap ΔexpR（种子沿用主检验常量；逐笔向量按确定性顺序重放）
    rng = np.random.RandomState(BOOT_SEED)
    n = len(alive)
    vec_map = {}
    for theta in STEP2_THETA:
        for M in STEP2_M:
            T = K_PRIMARY + M
            vec = []
            for e in alive:
                if e["holding_bars"] < T or e[f"r_at_{K_PRIMARY}"] > theta:
                    vec.append(e["r_net"]); continue
                r_t = (float(e["_ser"].iloc[e["_pos"] + T - 1]) - e["entry_price"]) / e["risk"]
                if r_t > theta:
                    vec.append(e["r_net"]); continue
                xp, _, note = exit_price_at(e, T)
                vec.append(e["r_net"] if xp is None else r_net_of(e["entry_price"], xp, e["risk"]))
            vec_map[f"conditional_theta{theta}_M{M}"] = np.array(vec)
    for N in (K_PRIMARY + 5, K_PRIMARY + 10):
        vec = []
        for e in alive:
            if e["holding_bars"] >= N:
                peak_N = max(float(e["_ser"].iloc[e["_pos"] + i]) for i in range(N))
                if peak_N <= e["entry_price"]:
                    xp, _, note = exit_price_at(e, N)
                    vec.append(e["r_net"] if xp is None else r_net_of(e["entry_price"], xp, e["risk"]))
                    continue
            vec.append(e["r_net"])
        vec_map[f"plain_N{N}"] = np.array(vec)
    for cell in cells:
        key = (
            f"conditional_theta{cell['theta']}_M{cell['M']}"
            if cell["kind"] == "conditional" else f"plain_N{cell['N']}"
        )
        var = vec_map[key]
        deltas = np.empty(BOOT_N)
        for b in range(BOOT_N):
            idx = rng.randint(0, n, n)
            deltas[b] = var[idx].mean() - base_r[idx].mean()
        clo, chi = np.percentile(deltas, [2.5, 97.5])
        cell["boot_ci95"] = [float(clo), float(chi)]
        cell["pass"] = bool(
            cell["delta_expR"] >= 0.05 and clo > 0
            and (cell.get("tail_R_retention") is None
                 or cell["tail_R_retention"] >= 0.95)
        )
    out["step2_cells"] = cells

    # 分模块分解表（均盈/均亏/持仓/触发/41+保留）——对齐 exit-revival 格式
    decomp = {}
    for mod in sorted({e["module"] for e in alive}):
        sub = [e for e in alive if e["module"] == mod]
        br = np.array([e["r_net"] for e in sub])
        rows = {}
        for theta in STEP2_THETA:
            for M in STEP2_M:
                T = K_PRIMARY + M
                vec = []
                trig = 0
                hold = []
                for e in sub:
                    if e["holding_bars"] < T or e[f"r_at_{K_PRIMARY}"] > theta:
                        vec.append(e["r_net"]); hold.append(e["holding_bars"]); continue
                    r_t = (float(e["_ser"].iloc[e["_pos"] + T - 1]) - e["entry_price"]) / e["risk"]
                    if r_t > theta:
                        vec.append(e["r_net"]); hold.append(e["holding_bars"]); continue
                    xp, hb_new, _ = exit_price_at(e, T)
                    if xp is None:
                        vec.append(e["r_net"]); hold.append(e["holding_bars"]); continue
                    vec.append(r_net_of(e["entry_price"], xp, e["risk"]))
                    hold.append(hb_new); trig += 1
                vec = np.array(vec)
                wins = vec[vec > 0]; losses = vec[vec <= 0]
                tails = [e for e in sub if e["is_tail"]]
                rows[f"cond_th{theta}_M{M}"] = {
                    "n": len(sub), "triggered": trig,
                    "expR": float(vec.mean()), "delta_expR": float(vec.mean() - br.mean()),
                    "avg_win": float(wins.mean()) if len(wins) else None,
                    "avg_loss": float(losses.mean()) if len(losses) else None,
                    "avg_hold": float(np.mean(hold)),
                    "base": {
                        "expR": float(br.mean()),
                        "avg_win": float(br[br > 0].mean()) if (br > 0).any() else None,
                        "avg_loss": float(br[br <= 0].mean()) if (br <= 0).any() else None,
                        "avg_hold": float(np.mean([e["holding_bars"] for e in sub])),
                        "tail_n": len(tails),
                        "tail_R": sum(e["r_net"] for e in tails),
                    },
                }
        decomp[mod] = rows
    out["step2_module_decomposition"] = decomp


# ---------------------------------------------------------------- 主流程
def main() -> None:
    bars = load_bars()
    close_only = load_close_only()

    all_rows = []
    for key, rel, _m, _g, _p in RUN_FILES:
        data = json.loads((RAW_BASE / rel).read_text(encoding="utf-8"))
        all_rows.extend(data["trades"])

    basis = validate_price_basis(all_rows, bars, close_only)
    if basis["mismatch_rate"] > 0.05:
        raise PriceBasisError(f"价格基准预检失败: {basis}")

    events, coverage = build_events(bars, close_only)
    out: dict = {
        "meta": {
            "script": "scripts/run_time_stop_tail_aware.py",
            "date": "2026-09-02",
            "bars_sources": {
                "ohlcv": f"{CACHE_BARS} + {TESTS_BARS}（并集取更长）",
                "close_only": str(KLINES),
            },
            "k_lines_note": "close-only 源仅含 close（2023-05 起），无法执行次根开盘，第二步退化口径已声明",
            "population": "alive@K10（holding_bars≥10）",
            "dedup": "(module, symbol, signal_date)，frozen 优先",
        },
        "price_basis_check_G0": basis,
        "coverage": coverage,
    }
    verdict = run_step1(events, out)
    if verdict["classifier_effective"]:
        run_step2(events, out)
        out["step2_executed"] = True
    else:
        out["step2_executed"] = False
        out["step2_skip_reason"] = (
            "分类器未过 V1+V2 判定（或功效门槛未达），按预注册不进入第二步"
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    res_path = OUT_DIR / "time_stop_tail_aware_results.json"
    res_path.write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=str),
        encoding="utf-8",
    )

    # 逐笔事件表 CSV（去 _ser/_pos 内部字段）
    csv_path = OUT_DIR / "events_per_trade.csv"
    fields = [
        "sample", "module", "group", "symbol", "signal_date", "entry_date",
        "entry_price", "stop_price", "exit_date", "exit_reason",
        "holding_bars", "r_net", "is_tail", "src",
        "r_at_5", "r_at_10", "r_at_15",
        "peak_r_at_5", "peak_r_at_10", "peak_r_at_15",
        "slope5_r_at_10",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for e in events:
            w.writerow({k: e.get(k) for k in fields})

    if "--dump-hash" in sys.argv:
        payload = json.dumps(out, sort_keys=True, default=str).encode()
        print("HASH", hashlib.md5(payload).hexdigest())

    print("落盘:", res_path)
    print("落盘:", csv_path)
    print("\n=== Step1 判定 ===")
    print(json.dumps(verdict, ensure_ascii=False, indent=1))
    print(json.dumps(out.get("step1_primary", {}), ensure_ascii=False, indent=1))
    print(json.dumps(out.get("step1_V2_protection", {}), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
