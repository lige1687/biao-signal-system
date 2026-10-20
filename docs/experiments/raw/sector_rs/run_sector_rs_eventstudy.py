#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""任务 L：板块级 RS 加权——板块专属证据的事件研究（预注册协议，判定线先写死）。

溯源：
- CROSS-GROUP-SYNTHESIS-2026-09-01.md 第四节开放冲突第 2 条：LEI 组标的级 RS 倾斜
  已判负（lei-ARCHIVE-2026-09-01.md 第二节，机制=与左侧早入场错位，双跑 f76fd445），
  板块级"先验转弱但非直接证伪——需板块级专属证据才可开轮"。
- 本脚本产出该专属证据：**事件研究**——回答"板块级 RS 强度的变化节奏，与该板块内
  A 模块信号的后续表现，时间关系是 同步 / 领先 / 滞后"，用数据判定标的级判负机制
  （左侧早入场错位）在板块尺度是否成立。**不是**把标的级 RS 三档加权公式换皮重跑，
  也不产生任何买卖点 / 仓位建议（板块层结论只能是确认层候选，research_proxy）。

═══════════════════════════════════════════════════════════════════════════
【预注册协议——以下判定线在运行前写死，跑后不得调整】
═══════════════════════════════════════════════════════════════════════════

数据（全部现成，只读，不新造）：
- D1 板块指数：~/.lei_signal_lab/cache/TH*.SECTOR.bars.parquet，日 close。
  现存 16/20 个（缺养殖业 TH881102、化学制品 TH881109、金属新材料 TH881114、
  能源金属 TH881267；2026-08-27 原 backtest_pool 已清空，此为现存唯一长史源），
  覆盖 2018-01-02→2026-08-20（TH881272/273 自 2018-11-26）。
- D2 基准：000300.SS（沪深300，手册口径"行业÷大盘"、BENCHMARK_BY_MARKET 先例），
  现仅 1500 根（2020-06-16→2026-08-20）→ RS 面板有效窗口被硬性截短，
  rs60 首个有效日约 2020-09-10。这是数据边界，如实接受，不外推。
- D3 逐笔信号：docs/experiments/raw/breadth_overlay/wf_a_noshrink.json
  （cn A 模块全量逐笔，early/a6_1_costbasis/cm0.5，655 笔，44 只 ETF，
  与 macd-strength-layering-ARCHIVE 同一信号本体口径；未加任何门禁）。
- D4 ETF→板块映射：scripts/run_sector_layer.py 的 ETF_SECTOR_MAP（22 只，
  多对多）。映射板块全部缺数据的 ETF 剔除（159825/159865/516220 → 剩 19 只）。
  多板块 ETF 的 RS 状态 = 各映射板块（有数据者）rank 的均值。
- B/C/D 个股逐笔无板块归属字段（已全量排查 raw 目录）→ 本轮不进事件研究，
  登记数据工程欠账。us 侧 XLK/IGV/SOXX 同属科技、无截面方差 → 不可检验。

RS 口径（research_proxy，与 prior F2 过滤器同口径以便对照）：
- rs = 板块 close / 000300 close（手册 §3.7 行业÷大盘）；
- rs60 = rs / rs.shift(60) − 1；
- rank(t) = rs60 在 16 板块内的当日截面百分位（0~1，pandas average tie）。
  全部只用 t 日及以前收盘，无未来函数。

研究问题与统计设计：
- E1 板块面板（不需要信号，机制层）：周采样（每第 5 个交易日，自 rs60 首个
  有效日起），按 rank 三分位（low ≤1/3 < mid < 2/3 ≤ high）分组，
  结果变量 = 板块未来超额收益（vs 000300）fwd_exc_H，H∈{20,60,120}，
  主判 H=60。同时算 trail60（过去 60 日已兑现超额）与 high 组
  "动量剩余比"= mean(fwd60)/mean(trail60)。附：rank 自相关（20/60/120）、
  top-8 成员资格 spell 时长（rank>0.5，spell≥5 日）——直接检验
  "板块轮动时间尺度更长"假设。
- E2 信号事件（任务核心）：映射后且 signal_date ≥ rs60 首有效日的 A 信号，
  T=signal_date。板块 RS 状态 = 映射板块 rank 均值在 T 的值，三分位分组，
  结果变量 = r_net（引擎净 R）。胜/负（r_net>0 / ≤0）两组的 RS 轨迹
  （T−60…T+60 交易日，偏移 ∈ ±{10,20,40,60}）。
- 零假设检验（统一置换法）：对每个板块的 rs60 序列做独立循环平移
  （offset ∈ [120, L−120] 交易日，torus permutation，保留各序列自身自相关、
  破坏与结果变量时间对齐），重算 rank→分组→统计量，2000 次，
  双侧 p = (1 + #{|null|≥|obs|}) / (1 + 2000)。
  主判统计量：
    T1 = mean(fwd_exc_60 | high) − mean(fwd_exc_60 | low)   【E1 主判】
    T2 = mean(r_net | high)   − mean(r_net | low)           【E2 主判】
  轨迹对照（描述性 + 各自置换 p）：
    D_pre  = mean_rank(胜, T−60) − mean_rank(负, T−60)
    D_at   = mean_rank(胜, T)   − mean_rank(负, T)
    D_post = mean_rank(胜, T+60) − mean_rank(负, T+60)

判定线（事前写死，α=0.05 双侧，格样本量护栏 N≥20 双侧）：
- P1 := (T1 > 0 且 p_T1 < 0.05 且 high/low 周观测格各 ≥ 50)
- P2 := (T2 > 0 且 p_T2 < 0.05 且 high/low 信号格各 ≥ 20)
- 分类（三选一）：
  * 领先（leading）= P1 ∧ P2 ∧ D_pre > 0
    ——板块 RS 在信号前已携带信息且高位板块后续仍跑赢 → 标的级"左侧错位"
    机制在板块尺度不成立 → 允许进入第 3 步（确认层深检）。
  * 滞后（lagging）= (T1 < 0 且 p_T1 < 0.05) ∨ (¬P1 ∧ T2 < 0 且 p_T2 < 0.05)
    ——板块 RS 高位后板块跑输 / 或 RS 高位时新信号更差 → 标的级机制在板块
    尺度同样成立 → 直接证伪，不跑第 3 步。
  * 同步（synchronous / 无信息）= 其余全部情形（含样本不足导致 P2 不可判：
    任一格 N<20 时 T2 记 inconclusive，只能落同步类）→ 证伪，不跑第 3 步。
- 稳健性切片（描述性，不参与判定）：剔除 518850.SS（黄金/贵金属，最大单格）、
  分年、分标的、delta20（rank 20 日改善 vs 恶化）分组、H=20/120 次级视野。

诚实条款：
- 16 板块小池（vs 标的级全市场）、周采样重叠窗口、结果变量多重视野——
  全部显式披露；主判只取 H=60 一条线，其余降为描述，防多重比较税。
- 逐笔信号为已归档 execute_run 产物（本分支引擎半重构无法重跑，同
  macd-strength-layering 口径），选择规则全文披露于上。
- 不改 src/，不产生买卖点，不接仓位系数；MACD 概念不涉及（红线 3 自然满足）。

复现（双跑哈希核对）：
  cd /Users/liyongbiao/Desktop/biao-signal-system-recovery
  PYTHONHASHSEED=0  <python-with-pandas> docs/experiments/raw/sector_rs/run_sector_rs_eventstudy.py
  PYTHONHASHSEED=42 <python-with-pandas> docs/experiments/raw/sector_rs/run_sector_rs_eventstudy.py
  两次输出的 records/analysis JSON sha256 须一致（脚本尾行打印）。

产出（全部本目录）：
  records_sector_rs.json   逐信号标注（rank@偏移、三分位、r_net、前瞻超额）
  analysis_sector_rs.json  全统计量 + 置换 p + 判定
  panel_weekly_sector_rs.csv  E1 周面板（date, sector, rank, tercile, trail/fwd 超额）
"""
from __future__ import annotations

import bisect
import hashlib
import json
import os
import platform
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

# ═══════════════ 冻结常量（判定线的一部分，不得改） ═══════════════
REPO = Path(__file__).resolve().parents[4]
RAW = Path(__file__).resolve().parent
CACHE = Path(os.environ.get("LEI_CACHE_ROOT",
                            str(Path.home() / ".lei_signal_lab" / "cache")))
BENCH_SYMBOL = "000300.SS"
TRADES_JSON = REPO / "docs/experiments/raw/breadth_overlay/wf_a_noshrink.json"

RS_LOOKBACK = 60                 # rs60（与 prior F2 / 标的级 RS_60 同窗口）
TERC_LO, TERC_HI = 1.0 / 3.0, 2.0 / 3.0
HORIZONS = (20, 60, 120)         # 次级视野；H=60 为主判
PRIMARY_H = 60
WEEKLY_STRIDE = 5
N_PERM = 2000
SHIFT_MIN = 120                  # 循环平移最小偏移（交易日）
SEED = 20260902                  # 主种子（SeedSequence.spawn 派生 4 条独立流）
ALPHA = 0.05
MIN_CELL_WEEKLY = 50             # E1 格样本量护栏（周观测）
MIN_CELL_SIGNAL = 20             # E2 格样本量护栏（信号笔数）
SPELL_MIN_DAYS = 5
TOP8_THRESHOLD = 0.5             # rank>0.5 = 16 板块的前 8（prior F2 top8 的池内化）
TRAJ_OFFSETS = (-60, -40, -20, -10, 0, 10, 20, 40, 60)

SECTOR_NAMES = {
    "TH881121.SECTOR": "半导体", "TH881129.SECTOR": "通信设备",
    "TH881134.SECTOR": "食品加工制造", "TH881145.SECTOR": "电力",
    "TH881155.SECTOR": "银行", "TH881156.SECTOR": "保险",
    "TH881157.SECTOR": "证券", "TH881168.SECTOR": "工业金属",
    "TH881169.SECTOR": "贵金属", "TH881170.SECTOR": "小金属",
    "TH881272.SECTOR": "软件开发", "TH881273.SECTOR": "白酒",
    "TH881278.SECTOR": "电网设备", "TH881279.SECTOR": "光伏设备",
    "TH881280.SECTOR": "风电设备", "TH881281.SECTOR": "电池",
}

#: ETF→TH 板块映射（名称对应，多对多；照抄 scripts/run_sector_layer.py，只读）
ETF_SECTOR_MAP: dict[str, tuple[str, ...]] = {
    "159611.SZ": ("TH881145.SECTOR",),
    "159652.SZ": ("TH881168.SECTOR", "TH881170.SECTOR", "TH881267.SECTOR"),
    "159819.SZ": ("TH881272.SECTOR", "TH881129.SECTOR"),
    "159825.SZ": ("TH881102.SECTOR",),
    "159865.SZ": ("TH881102.SECTOR",),
    "159928.SZ": ("TH881134.SECTOR", "TH881273.SECTOR"),
    "159995.SZ": ("TH881121.SECTOR",),
    "512000.SS": ("TH881157.SECTOR",),
    "512400.SS": ("TH881168.SECTOR", "TH881170.SECTOR", "TH881267.SECTOR"),
    "512480.SS": ("TH881121.SECTOR",),
    "512690.SS": ("TH881273.SECTOR",),
    "512760.SS": ("TH881121.SECTOR",),
    "512800.SS": ("TH881155.SECTOR",),
    "515030.SS": ("TH881281.SECTOR",),
    "515050.SS": ("TH881129.SECTOR",),
    "515170.SS": ("TH881134.SECTOR", "TH881273.SECTOR"),
    "515790.SS": ("TH881279.SECTOR",),
    "515880.SS": ("TH881129.SECTOR",),
    "516220.SS": ("TH881109.SECTOR",),
    "516510.SS": ("TH881272.SECTOR",),
    "518850.SS": ("TH881169.SECTOR",),
    "562590.SS": ("TH881121.SECTOR",),
}


# ═══════════════ 工具 ═══════════════
def r2(x, n=4):
    if x is None:
        return None
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(xf):
        return None
    return round(xf, n)


def tercile_label(rank_pct: float) -> str | None:
    if rank_pct is None or not np.isfinite(rank_pct):
        return None
    if rank_pct <= TERC_LO:
        return "low"
    if rank_pct >= TERC_HI:
        return "high"
    return "mid"


def perm_p_two_sided(obs: float, nulls: np.ndarray) -> float:
    """双侧置换 p：(1 + #{|null| >= |obs|}) / (1 + n)。"""
    if obs is None or not np.isfinite(obs):
        return float("nan")
    return float((1 + int(np.sum(np.abs(nulls) >= abs(obs)))) / (1 + len(nulls)))


# ═══════════════ 数据加载 ═══════════════
def load_sector_closes() -> tuple[pd.DataFrame, pd.Series, dict]:
    files = sorted(CACHE.glob("TH*.bars.parquet"))
    closes: dict[str, pd.Series] = {}
    coverage = {}
    for f in files:
        sym = f.name[: -len(".bars.parquet")]
        s = pd.read_parquet(f)["close"].astype(float)
        closes[sym] = s
        coverage[sym] = {
            "first": str(s.index[0].date()), "last": str(s.index[-1].date()),
            "rows": int(len(s)),
        }
    bench = pd.read_parquet(CACHE / f"{BENCH_SYMBOL}.bars.parquet")["close"].astype(float)
    sec_df = pd.DataFrame(closes).sort_index()
    return sec_df, bench, coverage


def build_rs_panel(sec_df: pd.DataFrame, bench: pd.Series):
    """rs = 板块/基准；rs60；16 板块截面 rank（0~1）。索引 = 基准交易日。"""
    aligned = sec_df.reindex(bench.index).ffill()
    ratio = aligned.div(bench, axis=0)
    rs60 = ratio / ratio.shift(RS_LOOKBACK) - 1.0
    rank = rs60.rank(axis=1, pct=True)
    return aligned, ratio, rs60, rank


# ═══════════════ E1 板块面板 ═══════════════
def forward_excess(aligned: pd.DataFrame, bench: pd.Series, positions: np.ndarray,
                   horizon: int) -> pd.DataFrame:
    """未来 H 交易日超额收益（板块 − 基准），位置数组进、位置数组出。"""
    close = aligned.values            # (L, n_sector)
    b = bench.values                  # (L,)
    L = len(b)
    out = np.full((len(positions), close.shape[1]), np.nan)
    for i, p in enumerate(positions):
        q = p + horizon
        if q >= L:
            continue
        sec_ret = close[q, :] / close[p, :] - 1.0
        bench_ret = b[q] / b[p] - 1.0
        out[i, :] = sec_ret - bench_ret
    return pd.DataFrame(out, index=positions, columns=aligned.columns)


def trailing_excess(aligned: pd.DataFrame, bench: pd.Series, positions: np.ndarray,
                    window: int) -> pd.DataFrame:
    out = np.full((len(positions), aligned.shape[1]), np.nan)
    close = aligned.values
    b = bench.values
    for i, p in enumerate(positions):
        q = p - window
        if q < 0:
            continue
        out[i, :] = (close[p, :] / close[q, :] - 1.0) - (b[p] / b[q] - 1.0)
    return pd.DataFrame(out, index=positions, columns=aligned.columns)


def e1_panel_study(aligned, bench, rs60, rank) -> dict:
    idx = rank.index
    L = len(idx)
    valid_mask = rs60.notna().any(axis=1).values
    first_valid = int(np.argmax(valid_mask))
    positions = np.arange(first_valid, L, WEEKLY_STRIDE)
    cols = sorted(rank.columns)

    fwd = {h: forward_excess(aligned, bench, positions, h) for h in HORIZONS}
    trail60 = trailing_excess(aligned, bench, positions, 60)

    by_terc: dict[int, dict[str, dict]] = {}
    tv = rank.loc[idx[positions]].values
    for h in HORIZONS:
        cell: dict[str, dict] = {}
        fh = fwd[h].values
        for lab in ("low", "mid", "high"):
            sel = np.where((tv <= TERC_LO) if lab == "low"
                           else ((tv >= TERC_HI) if lab == "high"
                                 else ((tv > TERC_LO) & (tv < TERC_HI))))
            vals = fh[sel]
            vals = vals[np.isfinite(vals)]
            cell[lab] = {"n_obs": int(vals.size),
                         "mean": r2(float(np.mean(vals)) if vals.size else None)}
        by_terc[h] = cell

    trv = trail60.values
    tv = rank.loc[idx[positions]].values
    sel_high = tv >= TERC_HI
    sel_low = tv <= TERC_LO
    trail_by = {}
    for lab, sel in (("high", sel_high), ("low", sel_low)):
        vals = trv[sel]
        vals = vals[np.isfinite(vals)]
        trail_by[lab] = {"n_obs": int(vals.size),
                         "mean": r2(float(np.mean(vals)) if vals.size else None)}
    fwd60_vals_high = fwd[PRIMARY_H].values[sel_high]
    fwd60_vals_high = fwd60_vals_high[np.isfinite(fwd60_vals_high)]
    m_trail_high = float(np.mean(trv[sel_high][np.isfinite(trv[sel_high])])) \
        if np.any(np.isfinite(trv[sel_high])) else float("nan")
    m_fwd_high = float(np.mean(fwd60_vals_high)) if fwd60_vals_high.size else float("nan")
    momentum_spent_ratio = (r2(m_fwd_high / m_trail_high, 4)
                            if np.isfinite(m_trail_high) and abs(m_trail_high) > 1e-9
                            else None)

    # rank 自相关（逐板块时间自相关，均值）
    persistence = {}
    rv = rank.values
    for lag in (20, 60, 120):
        cs = []
        for j in range(rv.shape[1]):
            a, b = rv[:-lag, j], rv[lag:, j]
            ok = np.isfinite(a) & np.isfinite(b)
            if ok.sum() > 60:
                cs.append(float(np.corrcoef(a[ok], b[ok])[0, 1]))
        persistence[lag] = r2(float(np.mean(cs)) if cs else None)

    # top-8 spell 时长
    member = (rv > TOP8_THRESHOLD)
    spells = []
    share = {}
    for j, col in enumerate(rank.columns):
        m = member[:, j]
        ok = np.isfinite(rv[:, j])
        m = m & ok
        start = None
        for i in range(len(m)):
            if m[i] and start is None:
                start = i
            elif not m[i] and start is not None:
                if i - start >= SPELL_MIN_DAYS:
                    spells.append(i - start)
                start = None
        if start is not None and len(m) - start >= SPELL_MIN_DAYS:
            spells.append(len(m) - start)
        valid_days = int(ok.sum())
        share[col] = r2(float(m.sum()) / valid_days, 4) if valid_days else None
    spells = np.array(spells, dtype=float)
    spell_stats = {
        "n_spells": int(spells.size),
        "median_days": r2(float(np.median(spells)) if spells.size else None, 1),
        "mean_days": r2(float(np.mean(spells)) if spells.size else None, 1),
        "p90_days": r2(float(np.percentile(spells, 90)) if spells.size else None, 1),
        "reference": {"rs60_lookback_days": RS_LOOKBACK,
                      "one_quarter_days": 63},
        "membership_share_by_sector": share,
    }

    # 周面板落盘
    rows = []
    for i, p in enumerate(positions):
        d = idx[p]
        for j, col in enumerate(cols):
            rows.append({
                "date": str(d.date()),
                "sector": col,
                "name_cn": SECTOR_NAMES.get(col),
                "rank_pct": r2(float(tv[i, j]), 4) if np.isfinite(tv[i, j]) else None,
                "tercile": tercile_label(float(tv[i, j])) if np.isfinite(tv[i, j]) else None,
                "trail_exc_60": r2(float(trv[i, j]), 5) if np.isfinite(trv[i, j]) else None,
                "fwd_exc_20": r2(float(fwd[20].values[i, j]), 5) if np.isfinite(fwd[20].values[i, j]) else None,
                "fwd_exc_60": r2(float(fwd[60].values[i, j]), 5) if np.isfinite(fwd[60].values[i, j]) else None,
                "fwd_exc_120": r2(float(fwd[120].values[i, j]), 5) if np.isfinite(fwd[120].values[i, j]) else None,
            })
    pd.DataFrame(rows).to_csv(RAW / "panel_weekly_sector_rs.csv",
                              index=False, encoding="utf-8")

    return {
        "weekly_positions": int(len(positions)),
        "window": {"first": str(idx[positions[0]].date()),
                   "last": str(idx[positions[-1]].date())},
        "fwd_excess_by_tercile": {str(h): by_terc[h] for h in HORIZONS},
        "trail60_by_tercile": trail_by,
        "momentum_spent_ratio_high_fwd60_over_trail60": momentum_spent_ratio,
        "rank_autocorr_avg": {str(k): v for k, v in persistence.items()},
        "top8_spells": spell_stats,
        "_fwd": fwd, "_trail60": trail60, "_tv": tv, "_positions": positions,
    }


# ═══════════════ E2 信号事件 ═══════════════
def mapped_rank_at(rank_df: pd.DataFrame, day_str: str,
                    sectors: list[str], date_strs: list[str],
                    offset: int = 0) -> float | None:
    """映射板块 rank 均值（有数据者）；位置 = T 的 as-of 下标 + offset 交易日。"""
    base = bisect.bisect_right(date_strs, day_str) - 1
    pos = base + offset
    if base < 0 or pos < 0 or pos >= len(date_strs):
        return None
    row = rank_df.loc[pd.Timestamp(date_strs[pos])]
    vals = [row[s] for s in sectors]
    vals = [float(v) for v in vals if np.isfinite(v)]
    return float(np.mean(vals)) if vals else None


def sector_fwd_excess_at(aligned: pd.DataFrame, bench: pd.Series,
                         date_strs: list[str], day_str: str,
                         sectors: list[str], horizon: int) -> float | None:
    base = bisect.bisect_right(date_strs, day_str) - 1
    q = base + horizon
    if base < 0 or q >= len(date_strs):
        return None
    t0, t1 = pd.Timestamp(date_strs[base]), pd.Timestamp(date_strs[q])
    vals = []
    for s in sectors:
        c0, c1 = aligned.at[t0, s], aligned.at[t1, s]
        if not (np.isfinite(c0) and np.isfinite(c1)):
            continue
        vals.append((c1 / c0 - 1.0)
                    - (bench.at[t1] / bench.at[t0] - 1.0))
    return float(np.mean(vals)) if vals else None


def e2_signal_study(trades: list[dict], rank: pd.DataFrame,
                    aligned: pd.DataFrame, bench: pd.Series) -> tuple[dict, list[dict]]:
    idx = rank.index
    date_strs = [str(d.date()) for d in idx]
    available = set(rank.columns)
    mapped = {k: sorted(s for s in v if s in available)
              for k, v in ETF_SECTOR_MAP.items()}
    mapped = {k: v for k, v in mapped.items() if v}
    dropped_etfs = sorted(set(ETF_SECTOR_MAP) - set(mapped))

    first_rs_day = date_strs[0]
    n_total = len(trades)
    n_mapped = sum(1 for t in trades if t["symbol"] in mapped)
    inwin: list[dict] = []
    n_pre_window = 0
    for t in trades:
        if t["symbol"] not in mapped:
            continue
        if t["signal_date"] < first_rs_day:
            n_pre_window += 1
            continue
        inwin.append(t)

    records = []
    for t in sorted(inwin, key=lambda x: (x["signal_date"], x["symbol"])):
        sym = t["symbol"]
        secs = mapped[sym]
        rank_t = mapped_rank_at(rank, t["signal_date"], secs, date_strs, 0)
        rec = {
            "symbol": sym,
            "signal_date": t["signal_date"],
            "entry_date": t["entry_date"],
            "exit_date": t["exit_date"],
            "exit_reason": t.get("exit_reason"),
            "sectors_mapped": secs,
            "sector_names": [SECTOR_NAMES.get(s) for s in secs],
            "r_net": r2(t["r_net"], 4),
            "rank_at_T": r2(rank_t, 4),
            "tercile_at_T": tercile_label(rank_t) if rank_t is not None else None,
            "rank_offsets": {},
            "fwd_sector_exc": {},
        }
        for off in TRAJ_OFFSETS:
            v = mapped_rank_at(rank, t["signal_date"], secs, date_strs, off)
            rec["rank_offsets"][str(off)] = r2(v, 4)
        for h in HORIZONS:
            v = sector_fwd_excess_at(aligned, bench, date_strs,
                                     t["signal_date"], secs, h)
            rec["fwd_sector_exc"][str(h)] = r2(v, 5)
        records.append(rec)

    valid = [r for r in records if r["tercile_at_T"] is not None]
    cells: dict[str, dict] = {}
    for lab in ("low", "mid", "high"):
        sub = [r["r_net"] for r in valid if r["tercile_at_T"] == lab]
        cells[lab] = {"n": len(sub),
                      "mean_r_net": r2(float(np.mean(sub)) if sub else None),
                      "win_rate": r2(float(np.mean([x > 0 for x in sub])) if sub else None)}

    # 轨迹（胜/负）
    winners = [r for r in valid if r["r_net"] > 0]
    losers = [r for r in valid if r["r_net"] <= 0]
    traj = {"n_winners": len(winners), "n_losers": len(losers), "offsets": {}}
    for off in TRAJ_OFFSETS:
        w = [r["rank_offsets"][str(off)] for r in winners
             if r["rank_offsets"][str(off)] is not None]
        l = [r["rank_offsets"][str(off)] for r in losers
             if r["rank_offsets"][str(off)] is not None]
        traj["offsets"][str(off)] = {
            "winners_mean_rank": r2(float(np.mean(w)) if w else None),
            "losers_mean_rank": r2(float(np.mean(l)) if l else None),
            "diff_win_minus_lose": r2((float(np.mean(w)) - float(np.mean(l)))
                                      if w and l else None),
        }

    # delta20 分组（描述性）
    d20 = {"improving": [], "deteriorating": []}
    for r in valid:
        r20 = r["rank_offsets"]["-20"]
        if r20 is None or r["rank_at_T"] is None:
            continue
        (d20["improving"] if r["rank_at_T"] > r20 else
         d20["deteriorating"]).append(r["r_net"])
    delta20_split = {
        k: {"n": len(v), "mean_r_net": r2(float(np.mean(v)) if v else None)}
        for k, v in d20.items()}

    # 分年 / 分标的（描述性）
    by_year: dict[str, dict] = defaultdict(lambda: {"n": 0, "sum": 0.0})
    by_symbol: dict[str, dict] = defaultdict(
        lambda: {"n": 0, "sum": 0.0, "high": 0, "low": 0})
    for r in valid:
        y = r["signal_date"][:4]
        by_year[y]["n"] += 1
        by_year[y]["sum"] += r["r_net"]
        by_symbol[r["symbol"]]["n"] += 1
        by_symbol[r["symbol"]]["sum"] += r["r_net"]
        if r["tercile_at_T"] == "high":
            by_symbol[r["symbol"]]["high"] += 1
        elif r["tercile_at_T"] == "low":
            by_symbol[r["symbol"]]["low"] += 1
    by_year_out = {y: {"n": v["n"], "mean_r_net": r2(v["sum"] / v["n"])}
                   for y, v in sorted(by_year.items())}
    by_symbol_out = {s: {"n": v["n"], "mean_r_net": r2(v["sum"] / v["n"]),
                         "n_high": v["high"], "n_low": v["low"]}
                     for s, v in sorted(by_symbol.items())}

    no_gold = [r for r in valid if r["symbol"] != "518850.SS"]
    ng_cells = {}
    for lab in ("low", "high"):
        sub = [r["r_net"] for r in no_gold if r["tercile_at_T"] == lab]
        ng_cells[lab] = {"n": len(sub),
                         "mean_r_net": r2(float(np.mean(sub)) if sub else None)}

    out = {
        "signal_source": str(TRADES_JSON.relative_to(REPO)),
        "n_total": n_total,
        "n_mapped_universe": n_mapped,
        "mapped_etfs": sorted(mapped),
        "dropped_etfs_all_sectors_missing": dropped_etfs,
        "n_pre_rs_window": n_pre_window,
        "n_in_window": len(records),
        "n_valid_tercile": len(valid),
        "tercile_cells": cells,
        "trajectory": traj,
        "delta20_split": delta20_split,
        "by_year": by_year_out,
        "by_symbol": by_symbol_out,
        "no_gold_robustness": ng_cells,
        "_records": records,
        "_mapped": mapped,
        "_date_strs": date_strs,
    }
    return out, records


# ═══════════════ 置换零假设 ═══════════════
def shifted_rank_panel(rs60: pd.DataFrame, offsets: dict[str, int]) -> pd.DataFrame:
    shifted = {}
    for col in sorted(rs60.columns):
        shifted[col] = np.roll(rs60[col].values, offsets[col])
    return pd.DataFrame(shifted, index=rs60.index).rank(axis=1, pct=True)


def run_permutations(rs60: pd.DataFrame, rank: pd.DataFrame,
                     e1: dict, e2: dict, rng_t1, rng_t2, rng_traj) -> dict:
    idx = rank.index
    cols = sorted(rs60.columns)
    col_pos = {c: j for j, c in enumerate(cols)}
    L = len(idx)

    positions = e1["_positions"]
    fwd60 = e1["_fwd"][PRIMARY_H].values

    records = e2["_records"]
    date_strs = e2["_date_strs"]
    mapped = e2["_mapped"]
    # 预计算每条信号的 base 位置（T 在面板中的 as-of 下标）与板块列下标
    sig_base = []
    for r in records:
        base = bisect.bisect_right(date_strs, r["signal_date"]) - 1
        sig_base.append((base, [col_pos[s] for s in mapped[r["symbol"]]]))

    winners_idx = [i for i, r in enumerate(records) if r["r_net"] > 0]
    losers_idx = [i for i, r in enumerate(records) if r["r_net"] <= 0]
    rnet_arr = np.array([r["r_net"] for r in records], dtype=float)

    nulls_t1 = np.empty(N_PERM)
    nulls_t2 = np.empty(N_PERM)
    nulls_dpre = np.empty(N_PERM)
    nulls_dat = np.empty(N_PERM)
    nulls_dpost = np.empty(N_PERM)

    for k in range(N_PERM):
        offsets = {c: int(rng_t1.integers(SHIFT_MIN, L - SHIFT_MIN)) for c in cols}
        rp = shifted_rank_panel(rs60, offsets)   # pandas rank：tie=average，与观测端一致
        rp_vals = rp.values

        # T1 null：周面板三分位 → fwd60 差
        tvp = rp_vals[positions]
        fh = fwd60
        sel_hi = tvp >= TERC_HI
        sel_lo = tvp <= TERC_LO
        hi = fh[sel_hi]
        lo = fh[sel_lo]
        hi = hi[np.isfinite(hi)]
        lo = lo[np.isfinite(lo)]
        nulls_t1[k] = (hi.mean() - lo.mean()) if hi.size and lo.size else np.nan

        # T2 / 轨迹 null：重算每条信号的映射 rank（numpy 行取值）
        rk = [None] * len(records)
        for i, (base, js) in enumerate(sig_base):
            if base < 0:
                continue
            vals = rp_vals[base, js]
            vals = vals[np.isfinite(vals)]
            rk[i] = float(vals.mean()) if vals.size else None
        hi_r = rnet_arr[[i for i in range(len(records))
                         if rk[i] is not None and rk[i] >= TERC_HI]]
        lo_r = rnet_arr[[i for i in range(len(records))
                         if rk[i] is not None and rk[i] <= TERC_LO]]
        nulls_t2[k] = (hi_r.mean() - lo_r.mean()) \
            if hi_r.size and lo_r.size else np.nan

        def _rank_off(i: int, off: int) -> float | None:
            base, js = sig_base[i]
            p = base + off
            if base < 0 or p < 0 or p >= L:
                return None
            vals = rp_vals[p, js]
            vals = vals[np.isfinite(vals)]
            return float(vals.mean()) if vals.size else None

        for tag, off, arr in (("pre", -60, nulls_dpre), ("at", 0, nulls_dat),
                              ("post", 60, nulls_dpost)):
            w = [_rank_off(i, off) for i in winners_idx]
            l = [_rank_off(i, off) for i in losers_idx]
            w = [x for x in w if x is not None]
            l = [x for x in l if x is not None]
            arr[k] = (np.mean(w) - np.mean(l)) if w and l else np.nan

    return {"t1": nulls_t1, "t2": nulls_t2,
            "d_pre": nulls_dpre, "d_at": nulls_dat, "d_post": nulls_dpost}


# ═══════════════ 主流程 ═══════════════
def main() -> None:
    seed_seq = np.random.SeedSequence(SEED)
    ss_t1, ss_t2, ss_traj, _ = seed_seq.spawn(4)
    rng_t1 = np.random.default_rng(ss_t1)
    rng_t2 = np.random.default_rng(ss_t2)
    rng_traj = np.random.default_rng(ss_traj)

    sec_df, bench, coverage = load_sector_closes()
    aligned, ratio, rs60, rank = build_rs_panel(sec_df, bench)
    trades_doc = json.loads(TRADES_JSON.read_text(encoding="utf-8"))
    trades = [t for t in trades_doc["trades"] if t.get("exit_date") is not None]

    e1 = e1_panel_study(aligned, bench, rs60, rank)
    e2, records = e2_signal_study(trades, rank, aligned, bench)

    # —— 观测统计量 ——
    fh = e1["_fwd"][PRIMARY_H].values
    tv = e1["_tv"]
    hi = fh[tv >= TERC_HI]
    lo = fh[tv <= TERC_LO]
    hi = hi[np.isfinite(hi)]
    lo = lo[np.isfinite(lo)]
    t1_obs = float(hi.mean() - lo.mean())
    n_hi_week = int(hi.size)
    n_lo_week = int(lo.size)

    valid = [r for r in records if r["tercile_at_T"] is not None]
    hi_r = [r["r_net"] for r in valid if r["tercile_at_T"] == "high"]
    lo_r = [r["r_net"] for r in valid if r["tercile_at_T"] == "low"]
    t2_obs = float(np.mean(hi_r) - np.mean(lo_r)) if hi_r and lo_r else float("nan")
    n_hi_sig, n_lo_sig = len(hi_r), len(lo_r)

    traj_off = e2["trajectory"]["offsets"]
    d_pre_obs = traj_off["-60"]["diff_win_minus_lose"]
    d_at_obs = traj_off["0"]["diff_win_minus_lose"]
    d_post_obs = traj_off["60"]["diff_win_minus_lose"]

    nulls = run_permutations(rs60, rank, e1, e2, rng_t1, rng_t2, rng_traj)

    p_t1 = perm_p_two_sided(t1_obs, nulls["t1"])
    p_t2 = perm_p_two_sided(t2_obs, nulls["t2"])
    p_dpre = perm_p_two_sided(d_pre_obs, nulls["d_pre"])
    p_dat = perm_p_two_sided(d_at_obs, nulls["d_at"])
    p_dpost = perm_p_two_sided(d_post_obs, nulls["d_post"])

    # —— 判定（预注册线） ——
    p1 = bool(t1_obs > 0 and p_t1 < ALPHA
              and n_hi_week >= MIN_CELL_WEEKLY and n_lo_week >= MIN_CELL_WEEKLY)
    t2_ok = bool(np.isfinite(t2_obs) and n_hi_sig >= MIN_CELL_SIGNAL
                 and n_lo_sig >= MIN_CELL_SIGNAL)
    p2 = bool(t2_ok and t2_obs > 0 and p_t2 < ALPHA)
    t2_inconclusive = not t2_ok

    if p1 and p2 and (d_pre_obs is not None and d_pre_obs > 0):
        classification = "leading"
    elif (t1_obs < 0 and p_t1 < ALPHA) or (
            (not p1) and t2_ok and t2_obs < 0 and p_t2 < ALPHA):
        classification = "lagging"
    else:
        classification = "synchronous"

    reasons = []
    reasons.append(f"T1={r2(t1_obs)} p={r2(p_t1)} (n_high={n_hi_week}, n_low={n_lo_week} 周观测)")
    reasons.append(f"T2={r2(t2_obs)} p={r2(p_t2)} (n_high={n_hi_sig}, n_low={n_lo_sig} 信号)"
                   + ("【样本不足→inconclusive】" if t2_inconclusive else ""))
    reasons.append(f"D_pre={d_pre_obs} p={r2(p_dpre)}；D_at={d_at_obs} p={r2(p_dat)}；"
                   f"D_post={d_post_obs} p={r2(p_dpost)}")
    reasons.append(f"P1={p1} P2={p2} → 分类={classification}")

    # —— 汇总落盘 ——
    e1.pop("_fwd")
    e1.pop("_trail60"), e1.pop("_tv"), e1.pop("_positions")
    e2.pop("_records"), e2.pop("_mapped"), e2.pop("_date_strs")

    analysis = {
        "meta": {
            "task": "任务L：板块级RS加权——板块专属证据事件研究（预注册）",
            "provenance": "research_proxy",
            # 注：不写运行时间戳，保证双跑 sha256 可比（哈希即复现凭证）
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "seed": SEED,
            "n_perm": N_PERM,
            "rules": {
                "tercile": f"low≤{TERC_LO:.4f}<mid<{TERC_HI:.4f}≤high (rank pct)",
                "primary_horizon": PRIMARY_H,
                "alpha": ALPHA,
                "min_cell_weekly": MIN_CELL_WEEKLY,
                "min_cell_signal": MIN_CELL_SIGNAL,
                "perm": f"per-sector circular shift ≥{SHIFT_MIN}d, two-sided",
                "classification": (
                    "leading = P1∧P2∧D_pre>0；"
                    "lagging = (T1<0∧p<α) ∨ (¬P1∧T2<0∧p<α)；"
                    "synchronous = 其余（含T2样本不足）"),
            },
            "data_quality": {
                "sectors_available": sorted(rank.columns),
                "sector_coverage": coverage,
                "bench": {"symbol": BENCH_SYMBOL,
                          "first": str(bench.index[0].date()),
                          "last": str(bench.index[-1].date()),
                          "rows": int(len(bench))},
                "aligned_nan_after_ffill": int(aligned.isna().sum().sum()),
                "rs_window": {"first": str(rank.index[0].date()),
                              "last": str(rank.index[-1].date())},
            },
        },
        "e1_sector_panel": e1,
        "e2_signals": e2,
        "primary_tests": {
            "T1_fwd60_high_minus_low": {
                "obs": r2(t1_obs, 5), "p": r2(p_t1, 4),
                "n_high": n_hi_week, "n_low": n_lo_week,
                "null_mean": r2(float(np.nanmean(nulls["t1"])), 5),
                "null_abs_p95": r2(float(np.nanpercentile(np.abs(nulls["t1"]), 95)), 5),
            },
            "T2_rnet_high_minus_low": {
                "obs": r2(t2_obs, 4), "p": r2(p_t2, 4),
                "n_high": n_hi_sig, "n_low": n_lo_sig,
                "null_mean": r2(float(np.nanmean(nulls["t2"])), 4),
                "null_abs_p95": r2(float(np.nanpercentile(np.abs(nulls["t2"]), 95)), 4),
                "inconclusive_sample": t2_inconclusive,
            },
            "trajectory_contrasts": {
                "D_pre_Tm60": {"obs": d_pre_obs, "p": r2(p_dpre, 4)},
                "D_at_T": {"obs": d_at_obs, "p": r2(p_dat, 4)},
                "D_post_Tp60": {"obs": d_post_obs, "p": r2(p_dpost, 4)},
            },
        },
        "verdict": {
            "P1": p1, "P2": p2,
            "classification": classification,
            "core_question": (
                "标的级失败机制（左侧早入场错位）在板块尺度上是否成立："
                + ("不成立（板块RS领先）" if classification == "leading"
                   else ("成立（板块RS滞后/同样错位）" if classification == "lagging"
                         else "无法拒绝机制成立（同步/无信息）"))),
            "step3_entered": classification == "leading",
            "reasons": reasons,
        },
    }
    # 补一个准确的 missing 清单（20 − 16）
    analysis["meta"]["data_quality"]["sectors_missing_of_20"] = sorted(
        {s for v in ETF_SECTOR_MAP.values() for s in v} - set(rank.columns))

    (RAW / "analysis_sector_rs.json").write_text(
        json.dumps(analysis, ensure_ascii=False, indent=1, sort_keys=True),
        encoding="utf-8")
    (RAW / "records_sector_rs.json").write_text(
        json.dumps({"n_records": len(records),
                    "traj_offsets": list(TRAJ_OFFSETS),
                    "records": records},
                   ensure_ascii=False, indent=1, sort_keys=True),
        encoding="utf-8")

    for name in ("records_sector_rs.json", "analysis_sector_rs.json"):
        h = hashlib.sha256((RAW / name).read_bytes()).hexdigest()
        print(f"PYTHONHASHSEED={os.environ.get('PYTHONHASHSEED', '<unset>')} "
              f"sha256({name}) = {h}")
    print("\n===== 判定 =====")
    for line in reasons:
        print(" ", line)
    print("  E1 fwd60 by tercile:", json.dumps(
        analysis["e1_sector_panel"]["fwd_excess_by_tercile"]["60"],
        ensure_ascii=False))
    print("  E2 cells:", json.dumps(e2["tercile_cells"], ensure_ascii=False))
    print("  spells:", json.dumps(
        {k: v for k, v in e1["top8_spells"].items()
         if k != "membership_share_by_sector"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
