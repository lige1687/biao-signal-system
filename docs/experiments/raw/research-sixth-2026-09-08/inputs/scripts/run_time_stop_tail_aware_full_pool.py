#!/usr/bin/env python3
"""时间止损接受右尾——前置「持仓分类器」事件研究 / **全池 175 标的复验**（2026-09-02，任务 R1）。

===========================================================================
任务定位（与原 M 任务一字不差，仅换数据源）
===========================================================================
原 M 任务（`scripts/run_time_stop_tail_aware.py`）事后欠账：分类器统计
上成立（Δp=+28.6pp, Fisher p=0.0058）但 n(G_lo) 26 < 30，P0 功效门槛
差 4 笔未达，归档"观察档"。**第 6 节下一步方向第 1 条明确写：
"全池复验分类器（转正前置条件）"**——本任务即该全池复验。

数据源切换（与原 M 任务的差异，仅 1 项）：
- 原 M 用仓库内 9 个 git 归档 run（lifecycle_combo / stage_b200 /
  breadth_overlay），结果是 291 笔替代样本（CN 股票 K 线 2023-05
  起，C_cn 159 笔中 124 笔因无覆盖被排除——**样本构成偏差**）。
- 本任务用 8-31 矩阵的 3 个 a6_1_costbasis 基准 run
  （`20260831-231254/231715/231944`），共 1521+563+225=2309 笔，
  **全为 175 per_symbol 池内标的**，K 线从 `docs/experiments/raw/
  pool-snapshot-2026-08-25/*.bars.parquet`（177 标的，pool - 2 个多余
  标的 = 175）读，覆盖 100%（G1 锚定：2309/2309 全覆盖）。

**判定标准、网格、bootstrap 方法、Fisher 检验，全部逐字复用 M 任务
docstring 的定义**（已写死在下方「判定标准」节）。本任务是补充复验
不是替代——不删除/修改原 M 任务 `time-stop-tail-aware-ARCHIVE-2026-09-02.md`，
只在结论上与原 M 任务对齐或对比。

===========================================================================
锚定校验（必须 100% 通过才跑判定统计，参照 Prompt R 收口条款）
===========================================================================
- 175 标的清单：A/B/C 三个 run 的 per_symbol 完全一致（各 175）。
  pool-snapshot 目录（177 标的）减 159165.SZ + 560390.SS = 175
  （=A.per_symbol 集合）。本任务过滤 = pool 目录 ∖ {159165.SZ, 560390.SS}。
- 笔数锚定：A 1521 / B 563 / C 225 = 8-31 三个 run 的 trades 长度。
  复现 = 直接读 JSON trades 列表的 len；任何过滤后不等于即停。

===========================================================================
机制假设（与原 M 一字不差）
===========================================================================
不问「能不能设计不伤右尾的时间止损」（stop_loss_matrix 已答），反向问：
**入场后第 K 日的浮盈状态能否提前识别右尾潜质**——若能，则时间止损只对
「无右尾潜质」的持仓生效（豁免有潜质组，默认出场 a6_1_costbasis 不变）；
若不能，则「右尾早期不可分类」归档证伪。**明确不测**「持仓超 N 日无条件
离场」（stop-loss-matrix 先验判定为自杀式配置）；不产生买卖点。

===========================================================================
事件研究设计（事前固化，与原 M 一字不差）
===========================================================================
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
- 主检验（唯一，其余全部标注敏感性/探索性）：pooled 全样本（按
  (module, symbol, signal_date) 去重），K=10，θ=0：
  Δp = p(Y=1|G_hi) − p(Y=1|G_lo)，逐笔 bootstrap（10000 次，固定种子
  numpy RandomState(20260902)，percentile 95% CI）+ Fisher 精确检验
  （双侧，自实现）交叉核对。显著 = CI 下界 > 0 且 Fisher p < 0.05。

===========================================================================
判定标准（事前写死，跑后不得调整——与原 M 一字不差）
===========================================================================
- G0 价格基准预检：structure_stop_C 可核验笔失配率 ≤5%（否则 K 线源作废、
  全实验中止报欠账）。
- P0 功效门槛：主检验样本 n(G_lo,θ=0) ≥ 30 且 41+ 事件总数 ≥ 50。
- V1 统计有效：主检验 CI 下界 > 0 且 Fisher p<0.05。
- V2 右尾保护：θ=0 下 41+ 单落入 G_lo 的比例 ≤20%（即 ≥80% 右尾被豁免）。
- V3 经济梯度：G_lo 组 final r_net 均值 < G_hi 组（方向性支持，不设显著性）。
- 分类有效 = V1 且 V2（V3 仅报告）；否则归档证伪/不可判定，**不进入第二步**。
- 第二步（仅当分类有效；网格事前固化 θ∈{0,0.5} × M∈{5,10}，外加参照臂）：
  规则 R(K,θ,M)：K 日 r_at_k ≤ θ 的持仓，若 K+M 日 r_at_{K+M} 仍 ≤ θ，
  则 K+M 收盘确认、次根开盘离场；r_at_k > θ 的持仓完全豁免（默认出场不变）。
  参照臂 = 无条件无进展时间止损 N=K+M（stop_loss_matrix 同型，同样本内重放）。
  执行：OHLCV 源按引擎语义（收盘确认、次根开盘、CN 跌停跳过
  open≤0.905×prev_close、FeeModel standard=单边 max(5bp, $0.005/股)）。
  判定：ΔexpR ≥ +0.05R（显著高于 stop_loss_matrix 的 ≤0.014R 经济意义线）
  且配对 bootstrap 95% CI 下界>0 且 41+ 单净 R 保留率 ≥95% → 通过；
  否则判负。分模块分解表（均盈/均亏/持仓/触发/41+ 保留）对齐
  exit-structural-stop-revival 格式。
- 敏感性（K=5/15、θ 网格、斜率变体、分模块）全部只标注方向，
  不得 overturn 或补强主判定。

===========================================================================
安全约束
===========================================================================
只读研究：不改 src/ 生产代码（FeeModel 公式按 engine.py 62-85
行逐字复刻，不 import 以避免账本依赖）、不 push、不删文件；新增产出仅
本脚本 + docs/experiments/raw/time_stop_tail_aware_full_pool/。

===========================================================================
复现
===========================================================================
解释器：/Users/liyongbiao/Desktop/biao-signal-system/.venv/bin/python
（pandas 2.3.3 / numpy 2.5.2；系统 python3 无 pandas）。
PYTHONHASHSEED=0 / 42 各跑一次 --dump-hash，md5 一致才入档。
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
RUNS_DIR = RAW_BASE / "backtest-runs-snapshot-2026-08-31"
POOL_DIR = RAW_BASE / "pool-snapshot-2026-08-25"
OUT_DIR = RAW_BASE / "time_stop_tail_aware_full_pool"

K_PRIMARY = 10
K_SENS = (5, 15)
THETA_GRID = (0.0, 0.25, 0.5, 1.0)
HOLD_TAIL = 41
BOOT_N = 10_000
BOOT_SEED = 20_260_902
INVALID_REASONS = {
    "invalid_nonpositive_risk", "skipped_limit_up_at_entry", "signal_at_end_not_entered",
}
#: 8-31 矩阵 a6_1_costbasis 三个基准 run（与 stop_loss_matrix-ARCHIVE 复刻口径同源）
RUN_FILES = [
    ("A", "20260831-231254-88cb12.json", "A"),   # early / a6_1 / clock_mult=0.5 / volume_filter=shrink
    ("B", "20260831-231715-1bb6f2.json", "B"),   # breakout / a6_1 / cluster_thr=0.03 / cb=30
    ("C", "20260831-231944-b87a6b.json", "C"),   # v3 / a6_1 / bias_filter=-0.15
]
#: 8-31 矩阵三 run 笔数锚定（必须 100% 对齐才能继续）
ANCHOR_TRADES = {"A": 1521, "B": 563, "C": 225}
#: pool 目录中需剔除的 2 个多余标的（pool 177 - 2 = 175 = per_symbol 集合）
EXCLUDE_FROM_POOL = ("159165.SZ", "560390.SS")
#: 第二步网格（事前固化，与原 M 一字不差）
STEP2_THETA = (0.0, 0.5)
STEP2_M = (5, 10)


# ---------------------------------------------------------------- 工具
def is_cn(symbol: str) -> bool:
    return symbol.endswith(".SS") or symbol.endswith(".SZ")


def fee_round_trip(price: float) -> float:
    """engine.FeeModel(standard) 逐字复刻：2 × max(5bp, $0.005/price)。"""
    if price <= 0:
        return 0.0
    per_side = max(5.0 / 10_000.0, 0.005 / price)
    return 2.0 * per_side


def r_net_of(entry: float, exitp: float, risk: float) -> float:
    fees = fee_round_trip(entry)
    return ((exitp / entry - 1.0) - fees) * (entry / risk)


# ---------------------------------------------------------------- 数据装载
def load_pool_bars(allowed: set[str]) -> dict[str, pd.DataFrame]:
    """从 pool-snapshot 目录加载 175 per_symbol 池内标的的 K 线（OHLCV）。"""
    bars: dict[str, pd.DataFrame] = {}
    missing = []
    for sym in sorted(allowed):
        p = POOL_DIR / f"{sym}.bars.parquet"
        if not p.exists():
            missing.append(sym)
            continue
        df = pd.read_parquet(p)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
        df = df[~df.index.duplicated(keep="last")]
        keep_cols = [c for c in ("open", "high", "low", "close") if c in df.columns]
        df = df[keep_cols].astype(float)
        bars[sym] = df
    return bars, missing


def get_175_per_symbol() -> set[str]:
    """A.per_symbol 集合即 175 per_symbol 池（三个 run 完全一致）。"""
    A = json.loads((RUNS_DIR / RUN_FILES[0][1]).read_text(encoding="utf-8"))
    return {p["symbol"] for p in A["per_symbol"]}


# ---------------------------------------------------------------- 锚定校验
def anchor_check() -> dict:
    """读 3 个 8-31 基准 run → 核对 per_symbol 集合 / trades 笔数 / 池差集。"""
    out = {}
    pool_files = sorted(POOL_DIR.glob("*.bars.parquet"))
    pool_syms = {p.name.replace(".bars.parquet", "") for p in pool_files}
    per_sym_sets = {}
    trade_counts = {}
    for module, fname, _m in RUN_FILES:
        d = json.loads((RUNS_DIR / fname).read_text(encoding="utf-8"))
        per_sym_sets[module] = {p["symbol"] for p in d["per_symbol"]}
        trade_counts[module] = len(d["trades"])
    out["per_symbol_counts"] = {k: len(v) for k, v in per_sym_sets.items()}
    out["per_symbol_identical"] = (
        per_sym_sets["A"] == per_sym_sets["B"] == per_sym_sets["C"]
    )
    out["per_symbol_union"] = len(per_sym_sets["A"] | per_sym_sets["B"] | per_sym_sets["C"])
    out["trade_counts"] = trade_counts
    out["trade_counts_match_anchor"] = (
        trade_counts == ANCHOR_TRADES
    )
    target = pool_syms - set(EXCLUDE_FROM_POOL)
    out["pool_minus_2_size"] = len(target)
    out["per_symbol_A_size"] = len(per_sym_sets["A"])
    out["pool_minus_2_equals_per_symbol_A"] = (target == per_sym_sets["A"])
    out["pool_minus_2_minus_per_symbol_A"] = sorted(target - per_sym_sets["A"])
    out["per_symbol_A_minus_pool_minus_2"] = sorted(per_sym_sets["A"] - target)
    out["pool_extras"] = sorted(pool_syms & set(EXCLUDE_FROM_POOL))
    out["pool_parquet_count"] = len(pool_files)
    out["anchor_pass"] = bool(
        out["per_symbol_identical"]
        and out["trade_counts_match_anchor"]
        and out["pool_minus_2_equals_per_symbol_A"]
    )
    return out


# ---------------------------------------------------------------- G0 价格基准预检
def validate_price_basis(trades_rows: list[dict], bars) -> dict:
    """structure_stop_C 笔的确认 bar（exit 前一根）收盘必须 < stop_price。"""
    ok = bad = nodata = 0
    for t in trades_rows:
        if t["exit_reason"] != "structure_stop_C" or t.get("r_net") is None:
            continue
        ser = bars.get(t["symbol"])
        if ser is None or "close" not in ser.columns:
            nodata += 1
            continue
        xd = pd.Timestamp(t["exit_date"])
        if xd not in ser.index:
            nodata += 1
            continue
        pos = ser.index.get_loc(xd)
        if pos == 0:
            nodata += 1
            continue
        if float(ser["close"].iloc[pos - 1]) < float(t["stop_price"]):
            ok += 1
        else:
            bad += 1
    checked = ok + bad
    rate = (bad / checked) if checked else float("nan")
    return {"checked": checked, "ok": ok, "bad": bad, "nodata": nodata,
            "mismatch_rate": rate}


# ---------------------------------------------------------------- 事件表构建
def build_events(trades: list[tuple[str, dict]], bars) -> tuple[list[dict], dict]:
    """从 8-31 三个 run 的逐笔交易构建事件表；分类总体 = alive@K10。"""
    seen: dict[tuple, int] = {}
    events: list[dict] = []
    coverage = {"by_module": {}, "totals": {}}
    for module, fname, _m in RUN_FILES:
        module_rows = [t for m, t in trades if m == module]
        kept = dropped_dup = not_closed = no_cov = 0
        for t in module_rows:
            if t["r_net"] is None or t.get("exit_reason") in INVALID_REASONS:
                not_closed += 1
                continue
            s = t["symbol"]
            ed = pd.Timestamp(t["entry_date"])
            ser = bars.get(s)
            if ser is None or ed not in ser.index:
                no_cov += 1
                continue
            pos = ser.index.get_loc(ed)
            kmax = max(K_SENS + (K_PRIMARY,))
            if pos + kmax - 1 >= len(ser):
                no_cov += 1
                continue
            if (ser.index[pos + K_PRIMARY - 1] - ed).days > 60:
                no_cov += 1
                continue
            dedup = (module, s, t["signal_date"])
            if dedup in seen:
                dropped_dup += 1
                continue
            seen[dedup] = 1
            risk = float(t["entry_price"]) - float(t["stop_price"])
            if risk <= 0:
                not_closed += 1
                continue
            row = {
                "module": module, "symbol": s, "signal_date": t["signal_date"],
                "entry_date": t["entry_date"],
                "entry_price": float(t["entry_price"]),
                "stop_price": float(t["stop_price"]),
                "exit_date": t["exit_date"],
                "exit_reason": t["exit_reason"],
                "holding_bars": int(t["holding_bars"]),
                "r_net": float(t["r_net"]),
                "is_tail": int(t["holding_bars"]) >= HOLD_TAIL,
                "src": "ohlcv", "risk": risk,
            }
            close = ser["close"].to_numpy()
            for K in (K_SENS + (K_PRIMARY,)):
                row[f"r_at_{K}"] = (float(close[pos + K - 1]) - row["entry_price"]) / risk
                peaks = [float(close[pos + i]) for i in range(K)]
                row[f"peak_r_at_{K}"] = (max(peaks) - row["entry_price"]) / risk
            for K in (K_SENS + (K_PRIMARY,)):
                c_k = float(close[pos + K - 1])
                c_prev = float(close[max(pos, pos + K - 6)])
                row[f"slope5_r_at_{K}"] = (c_k - c_prev) / risk
            row["_ser_close"] = close
            row["_pos"] = pos
            row["_bars"] = ser
            events.append(row)
            kept += 1
        coverage["by_module"][module] = {
            "file": fname,
            "raw_trades": len(module_rows),
            "kept": kept, "dropped_dup": dropped_dup,
            "not_closed": not_closed, "no_coverage_or_guard": no_cov,
        }
    coverage["totals"] = {
        "raw_trades": sum(c["raw_trades"] for c in coverage["by_module"].values()),
        "kept": sum(c["kept"] for c in coverage["by_module"].values()),
        "dropped_dup": sum(c["dropped_dup"] for c in coverage["by_module"].values()),
        "not_closed": sum(c["not_closed"] for c in coverage["by_module"].values()),
        "no_coverage_or_guard": sum(c["no_coverage_or_guard"] for c in coverage["by_module"].values()),
    }
    return events, coverage


# ---------------------------------------------------------------- 统计工具
def prop_boot_ci(hi: np.ndarray, lo: np.ndarray) -> tuple[float, float, float]:
    """分层 bootstrap（与原 M 一字不差）。"""
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
    """双侧 Fisher 精确检验（自实现，与原 M 一字不差）。"""
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
        p = math.comb(col1, k) * math.comb(n - col1, k2) / denom
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
        "tail_rate_alive": (sum(e["is_tail"] for e in alive) / len(alive)) if alive else None,
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

    tail_in_lo = int(((hb == 1) & lo_m).sum())
    out["step1_V2_protection"] = {
        "tail_total": int(hb.sum()), "tail_in_G_lo": tail_in_lo,
        "protection_rate": (1 - tail_in_lo / int(hb.sum())) if int(hb.sum()) else None,
        "V2_pass": bool(int(hb.sum()) and tail_in_lo / int(hb.sum()) <= 0.20),
    }

    m_hi = float(rn[hi_m].mean()) if hi_m.sum() else None
    m_lo = float(rn[lo_m].mean()) if lo_m.sum() else None
    out["step1_V3_gradient"] = {
        "mean_rnet_hi": m_hi, "mean_rnet_lo": m_lo,
        "median_rnet_hi": float(np.median(rn[hi_m])) if hi_m.sum() else None,
        "median_rnet_lo": float(np.median(rn[lo_m])) if lo_m.sum() else None,
        "V3_directional": (m_hi is not None and m_lo is not None and m_lo < m_hi),
    }

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
            "median": float(np.median([e[f"peak_r_at_{K_PRIMARY}"] for e in tails])),
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
def run_step2(events: list[dict], out: dict) -> None:
    alive = [e for e in events if e["holding_bars"] >= K_PRIMARY]

    def exit_price_at(e, T):
        ser_close, ops, pos = e["_ser_close"], e["_bars"]["open"].to_numpy(), e["_pos"]
        if is_cn(e["symbol"]):
            exit_pos = pos + T
            cls = ser_close
            while (
                is_cn(e["symbol"])
                and exit_pos + 1 < len(cls)
                and float(cls[exit_pos]) > 0
                and exit_pos >= 1
                and float(ops[exit_pos]) <= float(cls[exit_pos - 1]) * 0.905
            ):
                exit_pos += 1
            if exit_pos >= len(cls):
                return None, None, "limit_guard_reached_end"
            return float(ops[exit_pos]), exit_pos - pos, None
        return float(ser_close[pos + T - 1]), T, "cn_or_us_close_fallback"

    base_r = np.array([e["r_net"] for e in alive])
    cells = []
    for theta in STEP2_THETA:
        for M in STEP2_M:
            T = K_PRIMARY + M
            var_r, notes = [], []
            trig = trig_tail = 0
            tail_cut_r = tail_keep_r = 0.0
            for e in alive:
                if e["holding_bars"] < T or e[f"r_at_{K_PRIMARY}"] > theta:
                    var_r.append(e["r_net"])
                    if e["is_tail"]:
                        tail_keep_r += e["r_net"]
                    continue
                r_t = (float(e["_ser_close"][e["_pos"] + T - 1]) - e["entry_price"]) / e["risk"]
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
    for N in (K_PRIMARY + 5, K_PRIMARY + 10):
        var_r = []
        trig = trig_tail = 0
        tail_cut_r = tail_keep_r = 0.0
        for e in alive:
            if e["holding_bars"] >= N:
                peak_N = max(float(e["_ser_close"][e["_pos"] + i]) for i in range(N))
                if peak_N <= e["entry_price"]:
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
                r_t = (float(e["_ser_close"][e["_pos"] + T - 1]) - e["entry_price"]) / e["risk"]
                if r_t > theta:
                    vec.append(e["r_net"]); continue
                xp, _, note = exit_price_at(e, T)
                vec.append(e["r_net"] if xp is None else r_net_of(e["entry_price"], xp, e["risk"]))
            vec_map[f"conditional_theta{theta}_M{M}"] = np.array(vec)
    for N in (K_PRIMARY + 5, K_PRIMARY + 10):
        vec = []
        for e in alive:
            if e["holding_bars"] >= N:
                peak_N = max(float(e["_ser_close"][e["_pos"] + i]) for i in range(N))
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
                    r_t = (float(e["_ser_close"][e["_pos"] + T - 1]) - e["entry_price"]) / e["risk"]
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
    anchor = anchor_check()
    if not anchor["anchor_pass"]:
        print("!! 锚定校验失败，先停（按 Prompt R 收口条款）：")
        print(json.dumps(anchor, ensure_ascii=False, indent=1))
        sys.exit(2)
    print("锚定校验通过：")
    print(json.dumps({k: v for k, v in anchor.items() if k != "anchor_pass"},
                     ensure_ascii=False, indent=1))

    per_sym = get_175_per_symbol()
    bars, missing = load_pool_bars(per_sym)
    print(f"K 线加载：{len(bars)} 标的 成功，{len(missing)} 缺失（应为 0）")
    if missing:
        print(f"  缺失标的: {missing}")

    trades = []
    for module, fname, _m in RUN_FILES:
        d = json.loads((RUNS_DIR / fname).read_text(encoding="utf-8"))
        for t in d["trades"]:
            if t["symbol"] in per_sym:
                trades.append((module, t))
    raw_trades = len(trades)
    print(f"原始 trades: {raw_trades}（来自 3 个 8-31 run，过滤 175 per_symbol 池）")

    basis = validate_price_basis([t for _m, t in trades], bars)
    print(f"G0 价格基准预检: {basis}")
    if basis["mismatch_rate"] > 0.05:
        raise RuntimeError(f"价格基准预检失败: {basis}")

    events, coverage = build_events(trades, bars)
    print(f"事件表构建: kept={coverage['totals']['kept']} / raw={coverage['totals']['raw_trades']}")
    print(json.dumps(coverage, ensure_ascii=False, indent=1))

    out: dict = {
        "meta": {
            "task": "R1: M 全池 175 标的复验",
            "script": "scripts/run_time_stop_tail_aware_full_pool.py",
            "date": "2026-09-02",
            "bars_source": str(POOL_DIR),
            "runs_source": str(RUNS_DIR),
            "per_symbol_count": len(per_sym),
            "anchor": anchor,
            "population": "alive@K10（holding_bars≥10）",
            "dedup": "(module, symbol, signal_date)，frozen 优先（这里三个 run 即冻结）",
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
    res_path = OUT_DIR / "time_stop_tail_aware_full_pool_results.json"
    res_path.write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=str),
        encoding="utf-8",
    )

    csv_path = OUT_DIR / "events_per_trade.csv"
    fields = [
        "module", "symbol", "signal_date", "entry_date",
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

    print("\n落盘:", res_path)
    print("落盘:", csv_path)
    print("\n=== Step1 判定 ===")
    print(json.dumps(verdict, ensure_ascii=False, indent=1))
    print(json.dumps(out.get("step1_primary", {}), ensure_ascii=False, indent=1))
    print(json.dumps(out.get("step1_V2_protection", {}), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
