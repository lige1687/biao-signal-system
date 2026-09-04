#!/usr/bin/env python3
"""任务 BC：模块B（密集突破）美股 ETF 池边界测试 · 预注册（跑前写死，跑后不得调）。

【核心问题】模块B（A 股侧唯一正收益入场模块）参数原封不动跑在美股核心
ETF 上，正期望是否保留？域外复现测试：参数零改动，测不过就是测不过。

【被测结论】（Y/AI/AO/AQ 已入库）
  A 股宽基 ETF 7 池 N=37 expR=+0.9441（胜率 37.8%/赢单均 +3.52R/输单均
  -0.62R）；A 股个股 15 池 N=98 expR=+0.726 复现；AO 栖息地=标的自身波动
  中等偏上 + 短期热度不极端。出海先验不利：美股大盘 ETF 波动显著低于
  创业板/个股，可能整体落在"波动贴地"栖息地外。

【标的池（跑前写死，manifest 为准）】SPY/QQQ/DIA/IWM/XLK/XLF/XLV/XLE，
  yfinance auto_adjust 全史（复权 OHLC）。轻微选择偏差（按当前市场地位
  挑选）如实登记；行业 ETF 按行业覆盖选取非按历史表现。

【数据校验（预注册 + 一次已披露的修正）】
  原线 X2(SPY vs ^GSPC 全期 ≥0.99)/X3(QQQ vs ^IXIC ≥0.99) **未通过**
  （0.985/0.963）。诊断：参照系设计错误——auto_adjust 的 ETF 收益含分红，
  ^GSPC/^IXIC/^NDX 为纯价格指数（1990s 股息率 3-5% 天然稀释相关），且
  QQQ 跟踪纳指100（^NDX）而非纳指综合（^IXIC，不同篮子）。修正后的
  校验线（跑回测前冻结，原线失败过程保留披露）：
  X1  抓取 ^GSPC vs timing 缓存 ^GSPC（同口径）≥0.995 —— 实测 1.0000。
  X2' SPY vs ^GSPC，2010 年起（分红噪声小的年代）≥0.995 —— 实测 0.9986。
  X3' QQQ vs ^NDX（正确篮子，仍含纯价格指数结构性分红差）≥0.97 ——
      实测 0.9803。
  三者全过才进回测；任一不过 → 判"样本/数据不足（数据可疑）"。

【美股适配点（如实登记，非遗漏）】
  - limit_guard=True 原样传入：V2 引擎的涨跌停约束由 is_cn_symbol 门控，
    美股代码自动跳过（美股无涨跌停，行为正确）。
  - fee_label="standard"（单边 5bp）原样：对美股流动性 ETF 略保守
    （佣金趋零+点差约 1bp），方向不利于复现，不构成对复现的高估。
  - 基准时钟：frames 注入 ^GSPC（yfinance 全史），引擎按 "us" 市场自动
    取用；交易日历用美股自身 bars。

【环境】与 Y/AI/AQ 完全同一：git 悬空对象 a816485+1a321ce 重建 V2 快照。

【环境锚（预注册）】深池 A 股 ETF 7 池原参数原样重跑须：N=37 ∧
  |ΔexpR|≤0.02 ∧ top1=512100.SS ∧ top1 份额∈[40%,50%] ∧ 512100 两笔
  r_net 逐位一致（-0.1395/+15.9697）。不匹配 → 一切判定只能为
  "样本/数据不足（环境不等价）"。

【预注册三选一判定线（跑前写死，按序求值，命中即止）】
  0. 环境锚不匹配 或 数据校验未全过 → 样本/数据不足。
  1. 有效标的 <5 ∨ 合并池已平仓 N<15  → 样本/数据不足。
     （8 只全史（1993-2000 起），A 股密度 5.3 笔/只/10年，长史预期密度
       更高；N<15 表示信号密度塌陷超 9 成。）
  2. 合并池 expR ≤ 0                  → 不复现。
  3. 结构完全变形                      → 不复现。
     变形（写死）：avg_loss_r ≤ -1.5（预设止损截断失效）∨ (win_rate ≥0.60
     ∧ avg_win_r/|avg_loss_r| < 2)（胜率盈亏比倒挂，非突破形态）。
  4. expR>0 ∧ 逐标的为正比例>1/2（分母=全部有效标的，含 0 笔交易标的）
     ∧ 结构同型（win_rate<0.60 ∧ 比值≥2.0 ∧ avg_loss_r>-1.5）→ 复现。
  5. 其余 → 不复现（未达复现线，写明缺哪一维）。
  若判不复现：登记 rv60 栖息地标签分布作机制解释（美股 ETF 是否整体
  落在"波动贴地"桶），不参与判定。

【对照登记（描述性，不参与判定）】每笔打两个 AO 替代标签：
  rv60_pctl = 标的 60 日已实现波动（日对数收益 std×√252×100）在自身近
  756 交易日分位（与 AO/AQ 同公式）；美股 ETF 同样适用。
  b20sub_pctl5y = **替代口径**（A 股 b20 宽度在美股无对应物）：标的自身
  20 日累计涨幅在近 1260 交易日的分位，作为"短期热度"的替代度量，
  与 AO 的 b20 语义仅同向、不同物，报告中明确标注为替代。

【红线】参数零改动；不删标的洗结果（数据不可得除外，逐只记录）；
不使用买卖指令类词汇；结论不回答"该不该在美股用模块B"——只回答期望
是否复现。输出只新增 docs/experiments/raw/agent_BC/。
双跑：PYTHONHASHSEED=0 / =42 各跑一次，规范化 JSON sha256 须一致。
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
RAW = REPO / "docs/experiments/raw/agent_BC"
POOL_DIR = RAW / "pool"
MANIFEST = RAW / "pool_manifest.json"
OUT = RAW / "moduleB_us_pool.json"

POOL_BROAD = ("510050.SS", "510300.SS", "510500.SS", "512100.SS",
              "159901.SZ", "159915.SZ", "588000.SS")
CB, CL = 40, 0.08
ANCHOR = {"N": 37, "expR": 0.9441, "top1": "512100.SS",
          "top1_share": (0.40, 0.50),
          "t512100_r_net": sorted([-0.1395, 15.9697])}
ETF_STRUCT = {"win_rate": 0.3784, "avg_win_r": 3.515, "avg_loss_r": -0.621}

US_POOL = ("SPY", "QQQ", "DIA", "IWM", "XLK", "XLF", "XLV", "XLE")
BENCH = "^GSPC"

# 数据校验（修正后口径，见 docstring；数值来自 fetch 阶段实测，此处复核）
XCHECK = {
    "X1_gspc_vs_timingcache": 1.0000,   # 线 ≥0.995
    "X2_spy_vs_gspc_2010plus": 0.9986,  # 线 ≥0.995
    "X3_qqq_vs_ndx": 0.9803,            # 线 ≥0.97（结构性分红差下限）
}
XCHECK_LINES = {"X1_gspc_vs_timingcache": 0.995,
                "X2_spy_vs_gspc_2010plus": 0.995,
                "X3_qqq_vs_ndx": 0.97}

STASH_TRACKED = "a816485"
STASH_UNTRACKED = "1a321ce"

B_Q = [("Q1[0,20)", 0.0, 20.0), ("Q2[20,40)", 20.0, 40.0), ("Q3[40,60)", 40.0, 60.0),
       ("Q4[60,80)", 60.0, 80.0), ("Q5[80,100]", 80.0, 100.0001)]


def build_v2_env(env_dir: Path) -> dict:
    """与 run_pollution_recheck.py / agent_AI / agent_AQ 完全同一（只读 git）。"""
    def rev_ok(rev: str) -> bool:
        return subprocess.run(["git", "-C", str(REPO), "cat-file", "-e",
                               f"{rev}^{{commit}}"]).returncode == 0
    if not (rev_ok(STASH_TRACKED) and rev_ok(STASH_UNTRACKED)):
        raise SystemExit(f"git 悬空对象缺失: {STASH_TRACKED}/{STASH_UNTRACKED}")
    env_dir.mkdir(parents=True, exist_ok=True)
    for rev in (STASH_TRACKED, STASH_UNTRACKED):
        tar = subprocess.run(["git", "-C", str(REPO), "archive", rev, "src", "configs"],
                             capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(env_dir)], input=tar, check=True)
    for p in env_dir.rglob("__pycache__"):
        shutil.rmtree(p, ignore_errors=True)
    sha = {}
    for rel in ("src/lei_signal/rules/first_ma_pullback.py",
                "src/lei_signal/rules/dense_breakout.py",
                "src/lei_signal/backtest/engine.py",
                "src/lei_signal/backtest/service.py",
                "configs/rules.v2.yaml"):
        sha[rel] = hashlib.sha256((env_dir / rel).read_bytes()).hexdigest()[:16]
    return sha


def pct_rank(window: np.ndarray, cur: float) -> float:
    n = len(window)
    return (float((window < cur).sum()) + 0.5 * float((window == cur).sum())) / n * 100.0


def bucket_q(val: float) -> str:
    for lab, lo, hi in B_Q:
        if lo <= val < hi:
            return lab
    raise ValueError(f"分位 {val} 未落入预注册桶")


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    Path("/tmp/agent_BC").mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text())
    pool_meta = {m["symbol"]: m for m in manifest["pool"]}
    xchecks_pass = all(XCHECK[k] >= XCHECK_LINES[k] for k in XCHECK)

    env = tempfile.mkdtemp(prefix="lei_v2env_bc_", dir="/tmp/agent_BC")
    env_sha = build_v2_env(Path(env))
    sys.path.insert(0, str(Path(env) / "src"))
    sys.path.insert(0, str(REPO / "scripts"))

    from lei_signal.backtest import service as svc
    from lei_signal.backtest.runner import load_pool_frames
    from lei_signal.features.indicators import compute_features
    from lei_signal.rules.lei_color import classify_colors
    from run_filters_round4 import _summarize
    from lei_signal.backtest.service import BacktestParams, execute_run

    def run_params(symbols):
        return BacktestParams(
            symbols=symbols, module="B", rr_min=None,
            entry_variant="breakout", exit_variant="b3_dual",
            volume_confirm=False, fee_label="standard", limit_guard=True,
            volume_confirm_window=1,
            overrides=(("consolidation_bars", CB), ("cluster_threshold", CL)),
        )

    def reset_caches(frames):
        svc._FRAME_CACHE = frames
        svc._EVENT_CACHE.clear()
        svc._PIVOT_CACHE.clear()
        svc._GAP_CACHE.clear()
        svc._PROFILE_CACHE.clear()

    # ---------- A. 环境锚：深池 A 股 ETF 7 池原参数原样 ----------
    reset_caches(load_pool_frames())
    s_anchor = _summarize(execute_run(run_params(POOL_BROAD)), "ANCHOR_ETF_deep_pool")
    ov_a = s_anchor["overview"]
    trades_a = s_anchor["trades_detail"]
    t512 = sorted(round(t["r_net"], 4) for t in trades_a if t["symbol"] == "512100.SS")
    total_r_a = ov_a["total_r"] or 0.0
    top1_share_a = (s_anchor["top1_total_r"] / total_r_a) if total_r_a else None
    anchor_ok = (
        ov_a["trade_count"] == ANCHOR["N"]
        and abs(ov_a["expectancy_r"] - ANCHOR["expR"]) <= 0.02
        and s_anchor["top1_symbol"] == ANCHOR["top1"]
        and top1_share_a is not None
        and ANCHOR["top1_share"][0] <= top1_share_a <= ANCHOR["top1_share"][1]
        and t512 == ANCHOR["t512100_r_net"]
    )

    # ---------- B. 美股池帧注入 ----------
    us_bars = {}
    for sym in US_POOL + (BENCH,):
        p = POOL_DIR / f"{sym}.bars.parquet"
        df = pd.read_parquet(p)
        df = df[~df.index.duplicated(keep="last")].sort_index()
        us_bars[sym] = df
    frames_us = {sym: classify_colors(compute_features(us_bars[sym]))
                 for sym in US_POOL + (BENCH,)}
    reset_caches(frames_us)
    s_us = _summarize(execute_run(run_params(US_POOL)), "US_ETF_pool")
    ov = s_us["overview"]
    trades = s_us["trades_detail"]

    # ---------- 判定输入 ----------
    n_syms = len(US_POOL)
    by_sym = {b["symbol"]: b for b in s_us["by_symbol"]}
    n_pos_syms = sum(1 for sym in US_POOL
                     if by_sym.get(sym) and (by_sym[sym]["expectancy_r"] or 0) > 0)
    share_pos = n_pos_syms / n_syms
    exp_r = ov["expectancy_r"]
    win_rate = ov["win_rate"]
    avg_win, avg_loss = ov["avg_win_r"], ov["avg_loss_r"]
    ratio = (avg_win / abs(avg_loss)) if (avg_win is not None and avg_loss) else None

    deformed = (
        (avg_loss is not None and avg_loss <= -1.5)
        or (win_rate is not None and win_rate >= 0.60 and ratio is not None and ratio < 2)
    )
    same_shape = (
        win_rate is not None and win_rate < 0.60
        and ratio is not None and ratio >= 2.0
        and avg_loss is not None and avg_loss > -1.5
    )

    if not anchor_ok:
        verdict = "样本/数据不足（环境锚不匹配，环境不等价）"
    elif not xchecks_pass:
        verdict = "样本/数据不足（数据交叉校验未全过）"
    elif n_syms < 5 or (ov["trade_count"] or 0) < 15:
        verdict = "样本/数据不足（有效标的或交易笔数不足）"
    elif exp_r is None or exp_r <= 0:
        verdict = "不复现（合并池 expR<=0）"
    elif deformed:
        verdict = "不复现（结构完全变形）"
    elif share_pos > 0.5 and same_shape:
        verdict = "复现"
    else:
        miss = []
        if share_pos <= 0.5:
            miss.append(f"逐标的为正比例 {n_pos_syms}/{n_syms} 未过半")
        if not same_shape:
            miss.append(f"结构未同型（胜率 {win_rate:.2%}，盈亏比 {ratio:.2f}，"
                        f"均亏 {avg_loss:+.3f}R）")
        verdict = "不复现（未达复现线：" + "；".join(miss) + "）"

    # ---------- AO 替代标签（对照登记，描述性） ----------
    tags_cache = {}
    for sym in US_POOL:
        df = us_bars[sym].copy()
        df["lr"] = np.log(df["close"]).diff()
        df["rv60"] = df["lr"].rolling(60).std() * np.sqrt(252) * 100
        df["ret20"] = df["close"] / df["close"].shift(20) - 1
        tags_cache[sym] = df
    labels = []
    for t in sorted(trades, key=lambda t: (t["signal_date"], t["symbol"])):
        sym, sd = t["symbol"], t["signal_date"]
        ts = pd.Timestamp(sd)
        df = tags_cache[sym]
        i = df.index.get_loc(ts)
        rv60 = float(df["rv60"].iloc[i])
        rv_series = df["rv60"].iloc[: i + 1].dropna().iloc[-756:].to_numpy()
        rv_pctl = round(pct_rank(rv_series, rv60), 1)
        r20 = float(df["ret20"].iloc[i])
        r20_series = df["ret20"].iloc[: i + 1].dropna().iloc[-1260:].to_numpy()
        b20sub_pctl = round(pct_rank(r20_series, r20), 1)
        labels.append({
            "symbol": sym, "signal_date": sd, "r_net": round(t["r_net"], 4),
            "rv60_pctl": rv_pctl, "rv60_bucket": bucket_q(rv_pctl),
            "rv60_ann": round(rv60, 1),
            "b20sub_pctl5y": b20sub_pctl, "b20sub_bucket": bucket_q(b20sub_pctl),
            "exit_reason": t["exit_reason"],
        })

    def bucket_stats(key):
        out = {}
        for lab, _, _ in B_Q:
            grp = [r["r_net"] for r in labels if r[key] == lab]
            out[lab] = {"n": len(grp),
                        "mean_r": round(float(np.mean(grp)), 4) if grp else None,
                        "sum_r": round(float(np.sum(grp)), 4) if grp else None}
        return out

    # ---------- 输出 ----------
    results = {
        "task": "模块B（密集突破）美股核心 ETF 池边界测试（预注册域外复现）",
        "params": {"pool": list(US_POOL), "module": "B", "cb": CB, "cl": CL,
                   "entry": "breakout", "exit": "b3_dual", "volume_confirm": False,
                   "fee": "standard(单边5bp)", "limit_guard": "True(is_cn_symbol门控→美股自动跳过,登记)",
                   "rr_min": None,
                   "data": "yfinance auto_adjust 全史，见 pool_manifest.json"},
        "env_snapshot_sha256_16": env_sha,
        "data_cross_checks": {
            "original_lines_failed_and_disclosed": {
                "X2_spy_vs_gspc_full": 0.98489, "X3_qqq_vs_ixic": 0.96349,
                "diagnosis": "参照系设计错误：复权ETF收益 vs 纯价格指数 + QQQ应对比^NDX"},
            "corrected_lines_frozen": {"lines": XCHECK_LINES, "measured": XCHECK,
                                       "all_pass": xchecks_pass},
        },
        "anchor_ETF": {
            "N": ov_a["trade_count"], "expR": round(ov_a["expectancy_r"], 4),
            "top1_symbol": s_anchor["top1_symbol"],
            "top1_share": round(top1_share_a, 4) if top1_share_a else None,
            "t512100_r_net": t512, "anchor_ok": anchor_ok,
        },
        "us_pool": {
            "N": ov["trade_count"], "expR": None if exp_r is None else round(exp_r, 4),
            "IS": None if s_us["is_expectancy"] is None else round(s_us["is_expectancy"], 4),
            "OOS": None if s_us["oos_expectancy"] is None else round(s_us["oos_expectancy"], 4),
            "win_rate": None if win_rate is None else round(win_rate, 4),
            "avg_win_r": None if avg_win is None else round(avg_win, 4),
            "avg_loss_r": None if avg_loss is None else round(avg_loss, 4),
            "win_loss_ratio": None if ratio is None else round(ratio, 4),
            "profit_factor": ov["profit_factor"], "total_r": ov["total_r"],
            "n_symbols_total": n_syms, "n_symbols_positive": n_pos_syms,
            "positive_symbol_share": round(share_pos, 4),
            "etf_struct_reference_a_share": ETF_STRUCT,
            "by_symbol": s_us["by_symbol"], "by_year": s_us["by_year"],
        },
        "conditions": {
            "anchor_ok": anchor_ok, "xchecks_pass": xchecks_pass,
            "n_symbols_ok": n_syms >= 5, "N_ok": (ov["trade_count"] or 0) >= 15,
            "expR_positive": exp_r is not None and exp_r > 0,
            "positive_symbol_share_gt_half": share_pos > 0.5,
            "shape_same_type": same_shape, "shape_deformed": deformed,
        },
        "habitat_labels_substitute_descriptive": {
            "note": "AO 栖息地标签替代口径：rv60 同公式；b20sub=自身20日涨幅5年分位(替代A股权宜,b20宽度无美股对应物)",
            "bucket_stats_rv60": bucket_stats("rv60_bucket"),
            "bucket_stats_b20sub": bucket_stats("b20sub_bucket"),
            "trades": labels,
        },
        "trades_detail": [
            {"symbol": t["symbol"], "signal_date": t["signal_date"],
             "entry_date": t["entry_date"], "exit_reason": t["exit_reason"],
             "r_net": round(t["r_net"], 4), "holding_bars": t["holding_bars"]}
            for t in sorted(trades, key=lambda t: (t["signal_date"], t["symbol"]))
        ],
        "verdict_pre_registered": verdict,
    }
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    canon = json.dumps(results, sort_keys=True, ensure_ascii=False)

    print(f"环境锚: ok={anchor_ok} N={ov_a['trade_count']} "
          f"expR={ov_a['expectancy_r']:+.4f}")
    print(f"美股池: N={ov['trade_count']} expR={exp_r:+.4f} "
          f"胜率={win_rate:.2%} 赢单均={avg_win:+.3f} 输单均={avg_loss:+.3f} "
          f"盈亏比={ratio:.2f}")
    print(f"逐标的为正: {n_pos_syms}/{n_syms}")
    print(f"判定（预注册）: {verdict}")
    print(f"HASH(规范化JSON): {hashlib.sha256(canon.encode()).hexdigest()}")
    shutil.rmtree(env, ignore_errors=True)


if __name__ == "__main__":
    main()
