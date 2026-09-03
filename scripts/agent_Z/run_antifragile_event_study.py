#!/usr/bin/env python3
"""语义三前置验证 · "反脆弱补偿效应"事件研究 · 预注册协议（2026-09-03，跑前写死，跑后不改）。

任务：Prompt Z（总纲语义三）。唯一要回答的问题：半导体(512480)、科创50(588000)、
科创100(000698) 这三个"跟不上全A宽度冷热信号"的标的，是否【恰好】在主策略
（创业板三档宽度规则）最脆弱的时刻表现更好——即"失效时段是否真的错开"。
只验证假设，不搭组合、不给权重、不回答要不要买。

═══════════════════════════════════════════════════════════════════
【第 0 节 · 主策略定义（跑前写死）】
主策略 = 创业板三档宽度规则（kuandu-quanzhan 冠军口径，第 8/14 轮协议）：
  标的 399006 创业板指 × cn_all 全A等权 B200 宽度，三档逆势档位
  （参数边界 30/70 → 档位线 43.33/56.67：B200<43.33 满仓、43.33~56.67 半仓、
  ≥56.67 清仓），contrarian，gamma=1.0，min_weight=0，无闸；
  fee 10bp，min_trade 0.05，T 收盘信号 → T+1 开盘执行（引擎 simulate）。
  窗口 = 399006 与 cn_all 宽度对齐后 2010-06-01→2026-08-27（3945 行）。
【复现校准锚（跑前写死）】全窗 strategy_cagr≈+12.3%/MDD≈-41%、
  benchmark(一直拿着创业板)≈+8.5%/MDD≈-70%（kuandu-quanzhan 归档第 9 行）。
  若 |策略年化-12.3%|>1pp 或 |持有年化-8.5%|>1pp → 判"复现失败"，本次研究
  停止且不得出判定（防止在错误的净值序列上定义失效窗口）。

═══════════════════════════════════════════════════════════════════
【第 1 节 · "主策略失效时段"定义（跑前写死，机械可复现，覆盖全部历史）】
主判据（唯一参与总判定）：
  rel(t) = equity[t]/equity[t-120] − benchmark[t]/benchmark[t-120]
         （过去 120 个交易日，策略累计收益 − "什么都不做一直拿着创业板"累计收益）
  失效日 = rel(t) ≤ −0.10（过去约半年，策略比一直拿着少赚/多亏 ≥10 个百分点）
  失效段 = 连续失效日合并；相邻两段间隔 ≤5 个交易日则再合并（消除边界抖动）。
依据（预注册论证）：
  · N=120 = 本仓库标准诊断视界（执行手册"B200 区间→未来120日年化"、双极值
    警报 120 日窗，与既有结论同量纲可比）；
  · −10pp ≈ 策略全历史年化超额（+3.8pp/年）的 2.6 倍在半年内亏掉，
    即"给回两年半保费"级别的明确跑输；同时 10pp 也是创业板独立上涨段
    （策略半仓/清仓踏空）的典型量级；
  · 间隔 ≤5 日合并：档位信号在边界抖动会造成段破碎，5 日为预注册固定值。
灵敏度（仅披露，不参与判定，跑前写死）：(N=60, 线=−0.05) 与 (N=250, 线=−0.15)。
红线遵守：本定义只使用主策略自身净值，禁止看半导体/科创行情图挑窗口；
  覆盖策略全部历史（2010-06 起），不是事后选窗。

═══════════════════════════════════════════════════════════════════
【第 2 节 · 候选资产与数据口径（跑前写死）】
主口径（参与判定的三个标的）：
  · 半导体 = 512480 ETF 修平版（缓存 2019-06-12→2026-08-27；
    跳变 2021-03-29 −48.9%、2026-07-03 −50.7% 两处复权断裂，按
    data-quality-jump-audit §3 预注册修平法：跳变日起价格同除跳变比。
    审计结论：512480 判负维持，修平是"无断裂下界"）；
  · 科创50 = 588000 ETF（缓存 2020-11-16→2026-08-27，审计"不修"名单=干净）；
  · 科创100 = sh000698 指数（raw/gap_fill 2020-01-02→，阶段二已确认无污染）。
披露口径（延长窗交叉核对，不参与判定）：
  · 国证芯片 980017 指数 2019-08-16→（半导体跟踪指数，干净、无折算）；
  · 科创50指数 sh000688（本任务抓取，2020-01-02→，2020-07 发布前的回溯值）。
大盘基准（相对大盘超额的分母）= 000300 沪深300 指数（2002→，干净，
本仓库宽基基准惯例）。所有序列统一截至 2026-08-27（cn_all 宽度右端）。
统计口径：全部用收盘价对收盘价的日简单收益；事件日 = 资产自身交易日历
与失效日的交集（资产无数据的日子不计入该资产的样本）。
无前视声明：失效日标签只用截至 t 的后向 120 日信息；标签变量不含候选资产
信息，与候选资产 t 日收益无机械同时性。

═══════════════════════════════════════════════════════════════════
【第 3 节 · 事件研究指标与单资产补偿判定线（跑前写死）】
每个资产在自身窗口内计算：
  inside_ann / outside_ann = 失效日内 / 外 日均收益 × 252（年化，算术口径）；
  exc_in / exc_out = 日超额（资产−沪深300）inside / outside 年化；
  t_in = exc_in 序列均值的 t 值（mean/se×√n，ddof=1）；
  exc_strat_in = 资产日收益 − 主策略净值日收益（inside 年化，描述性）。
单资产判定（三条全过 = PASS）：
  (c) 样本下限：该资产窗内失效覆盖 ≥60 个交易日 且（合并后）失效段 ≥3 段；
      不满足 → 该资产单独判"样本不足"，不参与 PASS 计数；
  (a) 窗口内相对大盘超额年化 > 0 且 t_in > 2 且 ≥ +10pp；
  (b) 窗口内超额年化 > 窗口外超额年化（点估计方向判据，"恰好更好"的
      时间对齐证据；不设显著性线，t 差值如实披露——设双显著将使 6 年内
      样本几乎不可能通过，方向判据是诚实的折中）。
阈值论证：+10pp/年 = 补偿腿必须在主策略最难受的时段跑赢大盘到"有意义"
  的量级（半导体 2019→2026 独立牛市段持有年化 +24.3% vs 大盘个位数，
  双位数超额正是文献所记载的量级；低于 10pp 无组合意义）；t>2 = 常规 95%
  证据线（与仓库 p95 惯例一致）；60 交易日 ≈ 一个季度，是 t>2 有意义的最小
  样本量级；≥3 段 = 非孤例。
辅助披露（不参与判定）：inside 超额均值的平稳 bootstrap 95% 区间
  （循环块长 21 日，1000 次，seed 20260903）；逐段明细（每段起止、天数、
  资产/大盘/主策略累计收益）。

═══════════════════════════════════════════════════════════════════
【第 4 节 · 同机制检验判定线（跑前写死）】
日收益 Pearson 相关（Spearman 披露）：
  R1 全历史（主口径三标的共同窗）；R2 全历史（披露口径 {980017, sh000688,
  sh000698} 共同窗=最长干净共同窗）；R3 失效日内（主口径）。
机制三选一：
  M1 同一机制 = 三对全历史 Pearson 在 R1 与 R2 【全部】≥ 0.85；
  M3 互相独立 = 三对在 R1 与 R2 【全部】< 0.75；
  M2 部分同源 = 其余情形。
阈值论证：0.85（R²≈0.72）= "加三个等于加一个"的共动水平；0.75 为本仓库
  holdings-correlation-study 的"高相关"线（A股跨行业指数对典型 0.5–0.8）。
  灵敏度表 {0.75, 0.80, 0.85, 0.90} 逐档披露（仓库惯例，不用于事后选阈值）。

═══════════════════════════════════════════════════════════════════
【第 5 节 · 三选一总判定（跑前写死，跑后不得调整）】
  证据不足：主策略全历史总失效覆盖 <120 个交易日；或 ≥2/3 资产未过 (c)。
  不成立：PASS 数 ≤1（补偿路径：窗口内无补偿或太弱）；
          或 PASS ≥2 且 M1（机制路径：三者本是同一机制的三遍重复）。
  成立：PASS ≥2 且 M3；
  成立（附同源折扣限定语）：PASS ≥2 且 M2——结论必须写明"三者部分同源，
        分散价值打折，下一步应先按一条腿合并再验证"。
  主判定只依第 1 节主判据 (120, −0.10) 与主口径数据；灵敏度变体与披露口径
  若与主判据方向不一致 → 如实披露"不稳健"，判定仍依主判据（预注册语义）。

═══════════════════════════════════════════════════════════════════
【第 6 节 · 边界与红线】
不设计组合权重、不做组合回测、不回答"要不要买"；不碰语义八（动态权重）；
不使用买卖指令类词汇。不改 src/ 生产代码（只 import 纯函数）。禁止手工
编造/修补行情（512480 仅用审计预注册修平法，跳变日期来自审计清单）。
【双跑】PYTHONHASHSEED=0 / =42 各完整跑一遍，规范化 JSON 的 SHA256 必须
一致，哈希写入报告。输出：docs/experiments/raw/antifragile/
  antifragile_event_study_results.json（含全部判定数字与逐段明细）。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from lei_signal.timing_backtest.data import (  # noqa: E402
    TIMING_CACHE_DIR,
    align_index_breadth,
    load_breadth,
)
from lei_signal.timing_backtest.engine import simulate  # noqa: E402
from lei_signal.timing_backtest.metrics import summarize_run  # noqa: E402
from lei_signal.timing_backtest.strategies import (  # noqa: E402
    LadderParams,
    TrendGate,
    build_target,
)

RAW = REPO / "docs/experiments/raw/antifragile"
OUT = RAW / "antifragile_event_study_results.json"

# ── 预注册常量（跑前写死，与 docstring 一一对应）──
FEE_BPS = 10.0
MIN_TRADE = 0.05
CALIB_STRAT_CAGR = 0.123   # 复现锚（±1pp 容差）
CALIB_BENCH_CAGR = 0.085
CALIB_TOL = 0.01
FAIL_N = 120               # 主判据滚动窗
FAIL_TH = -0.10            # 主判据跑输线
SENS = [(60, -0.05), (250, -0.15)]   # 灵敏度（仅披露）
MERGE_GAP = 5              # 相邻失效段间隔 ≤5 交易日合并
EXC_TH = 0.10              # (a) 窗口内相对大盘超额年化下限 +10pp
T_TH = 2.0                 # (a) t 值线
MIN_DAYS = 60              # (c) 资产窗内失效覆盖下限
MIN_EPISODES = 3           # (c) 失效段数下限
TOTAL_COV_MIN = 120        # 总判定"证据不足"线：全历史失效覆盖下限
CORR_SAME = 0.85           # M1 同一机制线
CORR_INDEP = 0.75          # M3 互相独立线
CORR_SENS = [0.75, 0.80, 0.85, 0.90]
BOOT_N = 1000              # 平稳 bootstrap 次数（辅助披露）
BOOT_BLOCK = 21
BOOT_SEED = 20260903

JUMPS_512480 = ["2021-03-29", "2026-07-03"]  # data-quality-jump-audit §2 修清单


def load_bars(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    for col, fn in (("high", "max"), ("low", "min")):
        if col not in df.columns:
            df[col] = df[["open", "close"]].agg(fn, axis=1)
    return df[["open", "high", "low", "close"]]


def flatten_jumps(bars: pd.DataFrame, dates: list[str]) -> tuple[pd.DataFrame, list[dict]]:
    """审计预注册修平法（scripts/run_data_quality_jump_audit.py 同款）：跳变日起价格同除跳变比。"""
    df = bars.copy()
    log = []
    for d in sorted(dates):
        ts = pd.Timestamp(d)
        i = df.index.get_loc(ts)
        ratio = float(df["close"].iloc[i] / df["close"].iloc[i - 1])
        mask = df.index >= ts
        for c in ("open", "high", "low", "close"):
            df.loc[mask, c] = df.loc[mask, c] / ratio
        log.append({"date": d, "ratio": round(ratio, 4),
                    "single_day_return": round(ratio - 1.0, 4)})
    return df, log


def champion_netvalue() -> pd.DataFrame:
    """主策略逐日净值（equity）与持有基准（benchmark），复用仓库引擎。"""
    bars = load_bars(TIMING_CACHE_DIR / "399006.parquet")
    breadth = load_breadth("cn_all")
    aligned = align_index_breadth(bars, breadth)
    ladder = LadderParams(
        indicator="b200", n_bands=3, edge_mode="fixed", direction="contrarian",
        min_weight=0.0, gamma=1.0, low_edge=30.0, high_edge=70.0,
    )
    target = build_target(aligned, ladder, None, TrendGate(mode="off"), None, vol_target=0.0)
    res = simulate(aligned, target, fee_bps=FEE_BPS, min_trade=MIN_TRADE)
    return aligned, res


def failure_flag(eq: pd.Series, bench: pd.Series, n: int, th: float) -> pd.Series:
    rel = (eq / eq.shift(n)) - (bench / bench.shift(n))
    return rel <= th


def episodes(flag: pd.Series, merge_gap: int) -> list[dict]:
    """连续失效日 → 段；相邻段间隔 ≤ merge_gap 个交易日再合并。"""
    days = flag.index[flag.to_numpy()]
    if len(days) == 0:
        return []
    segs: list[list[pd.Timestamp]] = [[days[0]]]
    pos = flag.index
    for d in days[1:]:
        gap = pos.get_loc(d) - pos.get_loc(segs[-1][-1])
        if gap <= merge_gap:
            segs[-1].append(d)
        else:
            segs.append([d])
    return [
        {"start": str(s[0].date()), "end": str(s[-1].date()),
         "days": int((s[-1] - s[0]).days), "n_trading": len(s)}
        for s in segs
    ]


def flag_from_episodes(aligned_index: pd.DatetimeIndex, eps: list[dict]) -> pd.Series:
    f = pd.Series(False, index=aligned_index)
    for e in eps:
        f.loc[e["start"]:e["end"]] = True
    return f


def ann_mean(r: pd.Series) -> float:
    return float(r.mean() * 252.0) if len(r) else float("nan")


def t_stat(r: pd.Series) -> float:
    if len(r) < 3 or r.std(ddof=1) < 1e-12:
        return float("nan")
    return float(r.mean() / r.std(ddof=1) * np.sqrt(len(r)))


def stationary_bootstrap_ci(r: pd.Series, n_boot: int, block: int, seed: int) -> list[float]:
    """循环块（平稳）bootstrap 的日超额均值年化 95% 区间（辅助披露）。"""
    x = r.dropna().to_numpy(dtype=float)
    if len(x) < block:
        return [float("nan"), float("nan")]
    rng = np.random.default_rng(seed)
    n = len(x)
    n_blocks = int(np.ceil(n / block))
    means = np.empty(n_boot)
    for b in range(n_boot):
        starts = rng.integers(0, n, size=n_blocks)
        idx = (starts[:, None] + np.arange(block)[None, :]) % n
        means[b] = x[idx.ravel()][:n].mean() * 252.0
    return [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))]


def asset_event_study(
    name: str, bars: pd.DataFrame, flag_main: pd.Series,
    bench_close: pd.Series, strat_ret: pd.Series,
) -> dict:
    """单资产事件研究：inside/outside 表现 + (a)(b)(c) 判定。"""
    idx = bars.index
    r = bars["close"].pct_change()
    rb = bench_close.reindex(idx).pct_change()
    f = flag_main.reindex(idx).fillna(False)
    valid = r.notna() & rb.notna()
    r, rb, f = r[valid], rb[valid], f[valid]
    exc = r - rb
    exc_strat = r - strat_ret.reindex(idx).reindex(r.index)

    fin, fout = exc[f], exc[~f]
    eps = episodes(f, MERGE_GAP)
    # 逐段明细
    detail = []
    for e in eps:
        m = (r.index >= e["start"]) & (r.index <= e["end"])
        if m.sum() == 0:
            continue
        seg_r = (1.0 + r[m]).prod() - 1.0
        seg_b = (1.0 + rb[m]).prod() - 1.0
        detail.append({
            "start": e["start"], "end": e["end"], "n_trading": int(m.sum()),
            "asset_cum": round(float(seg_r), 4),
            "hs300_cum": round(float(seg_b), 4),
            "asset_minus_hs300": round(float(seg_r - seg_b), 4),
        })
    n_in_days = int(f.sum())
    n_eps_asset = len([e for e in eps if any(
        (r.index >= e["start"]) & (r.index <= e["end"]))])
    c_pass = bool(n_in_days >= MIN_DAYS and n_eps_asset >= MIN_EPISODES)
    exc_in_ann, exc_out_ann = ann_mean(fin), ann_mean(fout)
    t_in = t_stat(fin)
    a_pass = bool(exc_in_ann > 0 and t_in > T_TH and exc_in_ann >= EXC_TH)
    b_pass = bool(exc_in_ann > exc_out_ann)
    return {
        "window": [str(r.index[0].date()), str(r.index[-1].date())],
        "n_days": int(len(r)),
        "inside_days": n_in_days, "inside_episodes": n_eps_asset,
        "inside_share": round(n_in_days / len(r), 4),
        "own_ann_in": round(ann_mean(r[f]), 4), "own_ann_out": round(ann_mean(r[~f]), 4),
        "exc_hs300_ann_in": round(exc_in_ann, 4), "exc_hs300_ann_out": round(exc_out_ann, 4),
        "t_exc_in": round(t_in, 3),
        "t_exc_out": round(t_stat(fout), 3),
        "exc_strategy_ann_in": round(ann_mean(exc_strat[f.reindex(exc_strat.index).fillna(False)]), 4),
        "boot_ci_exc_in": [round(v, 4) for v in stationary_bootstrap_ci(fin, BOOT_N, BOOT_BLOCK, BOOT_SEED)],
        "criteria": {"c_sample": c_pass, "a_compensation": a_pass, "b_timing": b_pass},
        "pass": bool(c_pass and a_pass and b_pass),
        "if_c_fails_reason": None if c_pass else (
            f"失效覆盖 {n_in_days} 日 / {n_eps_asset} 段（下限 {MIN_DAYS} 日 / {MIN_EPISODES} 段）"),
        "episode_detail": detail,
    }


def corr_matrix(bars_map: dict[str, pd.DataFrame], flag: pd.Series | None = None) -> dict:
    rets = {}
    for k, b in bars_map.items():
        r = b["close"].pct_change()
        rets[k] = r
    df = pd.DataFrame(rets).dropna()
    if flag is not None:
        df = df[flag.reindex(df.index).fillna(False)]
    pear = df.corr(method="pearson")
    spear = df.corr(method="spearman")
    keys = list(bars_map)
    out = {"n_days": int(len(df)), "pearson": {}, "spearman": {}}
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            pair = f"{keys[i]}×{keys[j]}"
            out["pearson"][pair] = round(float(pear.iloc[i, j]), 4)
            out["spearman"][pair] = round(float(spear.iloc[i, j]), 4)
    return out


def main() -> None:
    results: dict = {"preregistration": {
        "failure_rule": f"rel(t)={FAIL_N}日策略累计-持有累计 ≤ {FAIL_TH}；段间隔≤{MERGE_GAP}交易日合并",
        "sensitivity": [f"N={n},th={th}" for n, th in SENS],
        "asset_criteria": f"(c)失效覆盖≥{MIN_DAYS}日且≥{MIN_EPISODES}段；(a)窗口内相对沪深300超额年化>0且t>{T_TH}且≥+{EXC_TH:.0%}；(b)窗口内超额>窗口外",
        "mechanism_rule": f"M1同一机制=三对全历史Pearson两口径全≥{CORR_SAME}；M3独立=全<{CORR_INDEP}；其余M2部分同源",
        "verdict_rule": "证据不足:总覆盖<120日或≥2资产不过(c)；不成立:PASS≤1，或PASS≥2且M1；成立:PASS≥2且M3；成立(同源折扣):PASS≥2且M2",
        "market_benchmark": "000300 沪深300",
    }}

    # ── 1. 主策略净值 + 复现校准 ──
    aligned, res = champion_netvalue()
    s = summarize_run(res.daily, res.trades)
    calib_ok = (abs(s["strategy_cagr"] - CALIB_STRAT_CAGR) <= CALIB_TOL
                and abs(s["benchmark_cagr"] - CALIB_BENCH_CAGR) <= CALIB_TOL)
    results["champion_calibration"] = {
        "window": [str(aligned.index[0].date()), str(aligned.index[-1].date())],
        "strategy_cagr": round(s["strategy_cagr"], 4),
        "strategy_mdd": round(s["strategy_mdd"], 4),
        "benchmark_cagr": round(s["benchmark_cagr"], 4),
        "benchmark_mdd": round(s["benchmark_mdd"], 4),
        "excess_cagr": round(s["excess_cagr"], 4),
        "anchor": "kuandu-quanzhan 归档 +12.3%/-41% vs +8.5%/-70%（±1pp 容差）",
        "match": bool(calib_ok),
    }
    print(f"[校准] 策略 {s['strategy_cagr']:+.2%}/{s['strategy_mdd']:.1%} vs 持有 "
          f"{s['benchmark_cagr']:+.2%}/{s['benchmark_mdd']:.1%} → {'通过' if calib_ok else '复现失败，停止'}")
    if not calib_ok:
        OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1))
        return

    eq, bench = res.daily["equity"], res.daily["benchmark"]
    strat_ret = eq.pct_change()

    # ── 2. 失效窗口（主判据 + 灵敏度）──
    flag_main = failure_flag(eq, bench, FAIL_N, FAIL_TH)
    eps_main = episodes(flag_main, MERGE_GAP)
    results["failure_windows"] = {
        "primary": {
            "rule": f"N={FAIL_N}, th={FAIL_TH}",
            "n_episodes": len(eps_main),
            "total_days": int(flag_main.sum()),
            "coverage_share": round(float(flag_main.mean()), 4),
            "episodes": eps_main,
        },
        "sensitivity": {},
    }
    for n, th in SENS:
        fl = failure_flag(eq, bench, n, th)
        eps_s = episodes(fl, MERGE_GAP)
        results["failure_windows"]["sensitivity"][f"N={n},th={th}"] = {
            "n_episodes": len(eps_s), "total_days": int(fl.sum()),
            "coverage_share": round(float(fl.mean()), 4),
            "episodes": eps_s,
        }
    print(f"[失效窗] 主判据: {len(eps_main)} 段 / {int(flag_main.sum())} 日 / "
          f"覆盖 {flag_main.mean():.1%}")
    for e in eps_main:
        print(f"   {e['start']} → {e['end']}  ({e['n_trading']} 交易日)")

    # ── 3. 数据装载（主口径 + 披露口径）──
    semi_raw = load_bars(TIMING_CACHE_DIR / "512480.parquet")
    semi_flat, flatten_log = flatten_jumps(semi_raw, JUMPS_512480)
    primary_bars = {
        "512480": semi_flat.loc[:"2026-08-27"],
        "588000": load_bars(TIMING_CACHE_DIR / "588000.parquet").loc[:"2026-08-27"],
        "sh000698": load_bars(REPO / "docs/experiments/raw/gap_fill/sh000698_index.parquet").loc[:"2026-08-27"],
    }
    disclose_bars = {
        "980017": load_bars(TIMING_CACHE_DIR / "980017.parquet").loc[:"2026-08-27"],
        "sh000688": load_bars(RAW / "sh000688_index.parquet").loc[:"2026-08-27"],
        "sh000698": primary_bars["sh000698"],
    }
    bench_close = load_bars(TIMING_CACHE_DIR / "000300.parquet")["close"]
    results["data"] = {
        "primary": {k: [str(v.index[0].date()), str(v.index[-1].date()), int(len(v))]
                    for k, v in primary_bars.items()},
        "disclose": {k: [str(v.index[0].date()), str(v.index[-1].date()), int(len(v))]
                     for k, v in disclose_bars.items()},
        "flatten_512480": flatten_log,
    }

    # ── 4. 事件研究（主口径判定 + 披露口径对照）──
    names = {"512480": "半导体(ETF修平)", "588000": "科创50(ETF)", "sh000698": "科创100(指数)"}
    event = {}
    for k, b in primary_bars.items():
        event[k] = asset_event_study(names[k], b, flag_main, bench_close, strat_ret)
        e = event[k]
        print(f"[事件] {names[k]:12s} 窗口{e['window'][0]}→{e['window'][1]} "
              f"inside {e['inside_days']}日/{e['inside_episodes']}段 "
              f"超额(in) {e['exc_hs300_ann_in']:+.1%} t={e['t_exc_in']} "
              f"vs (out) {e['exc_hs300_ann_out']:+.1%} → "
              f"c{'✓' if e['criteria']['c_sample'] else '✗'}"
              f"a{'✓' if e['criteria']['a_compensation'] else '✗'}"
              f"b{'✓' if e['criteria']['b_timing'] else '✗'}")
    results["event_study"] = event

    disclose_event = {}
    for k, b in disclose_bars.items():
        disclose_event[k] = asset_event_study(k, b, flag_main, bench_close, strat_ret)
    results["event_study_disclose"] = {
        k: {kk: vv for kk, vv in v.items() if kk != "episode_detail"}
        for k, v in disclose_event.items()
    }

    # 灵敏度变体上的事件研究（仅披露，主口径三资产）
    sens_event = {}
    for n, th in SENS:
        fl = flag_from_episodes(aligned.index, results["failure_windows"]["sensitivity"][f"N={n},th={th}"]["episodes"])
        sens_event[f"N={n},th={th}"] = {
            k: {kk: vv for kk, vv in asset_event_study(names[k], b, fl, bench_close, strat_ret).items()
                if kk != "episode_detail"}
            for k, b in primary_bars.items()
        }
    results["sensitivity_event_study"] = sens_event

    # ── 5. 同机制检验 ──
    r1 = corr_matrix(primary_bars)
    r2 = corr_matrix(disclose_bars)
    r3 = corr_matrix(primary_bars, flag=flag_main)
    results["mechanism"] = {"R1_full_primary": r1, "R2_full_disclose": r2, "R3_inside_primary": r3}
    print(f"[相关] 全历史主口径 {r1['pearson']}（n={r1['n_days']}）")
    print(f"[相关] 全历史指数口径 {r2['pearson']}（n={r2['n_days']}）")
    print(f"[相关] 失效窗内主口径 {r3['pearson']}（n={r3['n_days']}）")

    pairs = list(r1["pearson"].keys())

    def all_pairs_ge(c: dict, th: float) -> bool:
        return all(v >= th for v in c["pearson"].values())

    def all_pairs_lt(c: dict, th: float) -> bool:
        return all(v < th for v in c["pearson"].values())

    if all_pairs_ge(r1, CORR_SAME) and all_pairs_ge(r2, CORR_SAME):
        mech = "M1_同一机制"
    elif all_pairs_lt(r1, CORR_INDEP) and all_pairs_lt(r2, CORR_INDEP):
        mech = "M3_互相独立"
    else:
        mech = "M2_部分同源"
    # 灵敏度表
    corr_sens = {f"≥{th}": {
        "R1": {p: bool(v >= th) for p, v in r1["pearson"].items()},
        "R2": {p: bool(v >= th) for p, v in r2["pearson"].items()},
        "R1_all": all_pairs_ge(r1, th), "R2_all": all_pairs_ge(r2, th),
    } for th in CORR_SENS}
    results["mechanism"]["verdict"] = mech
    results["mechanism"]["sensitivity"] = corr_sens
    print(f"[机制] {mech}")

    # ── 6. 总判定 ──
    n_assets_with_sample = sum(1 for k in event.values() if k["criteria"]["c_sample"])
    n_pass = sum(1 for k in event.values() if k["pass"])
    total_fail_days = int(flag_main.sum())
    if total_fail_days < TOTAL_COV_MIN or (3 - n_assets_with_sample) >= 2:
        verdict = "证据不足"
    elif n_pass <= 1 or (n_pass >= 2 and mech == "M1_同一机制"):
        verdict = "不成立"
    elif n_pass >= 2 and mech == "M3_互相独立":
        verdict = "成立"
    else:
        verdict = "成立(同源折扣：三者部分同源，分散价值需打折表述)"
    results["verdict"] = {
        "n_pass": n_pass, "n_assets_with_sample": n_assets_with_sample,
        "total_failure_days": total_fail_days, "mechanism": mech,
        "verdict": verdict,
    }
    print(f"\n[总判定] {verdict}（PASS {n_pass}/3，有样本 {n_assets_with_sample}/3，{mech}）")

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1))
    h = hashlib.sha256(json.dumps(results, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    print(f"输出: {OUT}")
    print(f"HASH(规范化JSON): {h}")


if __name__ == "__main__":
    main()
