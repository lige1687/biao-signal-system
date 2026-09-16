#!/usr/bin/env python3
"""任务 AQ：模块B（密集突破）在高流动性 A 股个股池的边界测试 · 预注册（跑前写死，跑后不得调）。

【核心问题（唯一要回答的）】模块B 在 ETF 池上的正期望能否迁移到高流动性
A 股个股？这是"域外复现"测试：参数一字不改地跑在新池上，看期望结构是否
保留。测不过就是测不过；绝不许为新池调参。

【被测结论】（Y/AI/AO 三任务已入库）
  宽基 ETF 7 池（510050/510300/510500/512100/159901/159915/588000），
  模块B breakout × b3_dual × vc0，cb=40/cl=8%，fee=standard，limit_guard=True：
  N=37, expR=+0.9441, 胜率 37.84%, 赢单均 +3.515R, 输单均 -0.621R；
  AI 判"稳健（低冗余）"；AO 栖息地 = 标的自身波动中等偏上 + 短期热度不极端。

【个股池（跑前写死；名单以 fetch_stock_pool.py 落盘 manifest 为准）】
  15 只高流动性 A 股大盘股（千亿级市值、日成交额长期居前，跨 13 个行业）：
  贵州茅台/五粮液/中国平安/招商银行/宁德时代(2018-06 起)/比亚迪/长江电力/
  紫金矿业/美的集团/中信证券/恒瑞医药/海康威视/中兴通讯/中国石油/京东方A。
  幸存者偏差（大白话，报告开头必须重复）：用今天还活着的大公司回测历史，
  天然高估收益——当年同样大但后来衰败的公司不在样本里。这是本测试的已知
  上限，结论只能用于方向性判断。

【数据】docs/experiments/raw/agent_AQ/pool/（本任务自己的池目录，未动
  ~/.lei_signal_lab 共享缓存）：腾讯 hfq 后复权日线 2016-01-04~2026-09-03
  （宁德时代自上市日 2018-06-11），已过 AK 隔夜比 >1.5/<1/1.5 复权兜底
  （全部无跳变）与超板大幅日扫描（全部为 0）。qfq 口径对长历史个股负值化
  （茅台 2016 起为负、宁德空返回），客观不可用，故用 hfq——对同一股票两
  口径在除权日之外只差乘性常数，模块B 的均线/突破/R 归一计算数学等价。
  注：深池存在 10 只同名个股的 qfq 短版数据（2018/2020 起），本任务个股
  池一律以自己的 hfq 长版覆盖，环境锚跑（ETF 池）不涉这些代码。

【环境】与 Y/AI 完全同一：git 悬空对象 a816485 + 1a321ce 重建 V2 代码快照
  运行（只读 git，不改仓库）。

【环境锚（预注册）】先在深池 ETF 7 池原参数重跑（深池原样数据）：须
  N=37 ∧ |ΔexpR|≤0.02 ∧ top1=512100.SS ∧ top1 份额∈[40%,50%] ∧ 512100
  两笔 r_net 逐位一致（-0.1395 / +15.9697）。不匹配 → 一切判定只能为
  "样本/数据不足（环境不等价）"。

【预注册三选一判定线（跑前写死，按序求值，命中即止）】
  0. 环境锚不匹配                     → 样本/数据不足（环境不等价）。
  1. 有效标的 <10 ∨ 合并池已平仓 N<15  → 样本/数据不足。
     （有效标的 = manifest ok 且进入回测帧的标的，本池 15/15。
       ETF 密度 37笔/7只≈5.3笔/只 → 15 只预期 ~80 笔；N<15 表示信号密度
       塌陷超 8 成且 15 笔以下单笔大赢会主导期望估计。）
  2. 合并池 expR ≤ 0                  → 不复现。
  3. 结构完全变形                      → 不复现。
     变形（写死）：avg_loss_r ≤ -1.5（预设止损截断失效成常态：个股跳空
     穿越止损）∨ (win_rate ≥ 0.60 ∧ avg_win_r/|avg_loss_r| < 2)（胜率与
     盈亏比结构倒挂，不再是"少数大赢覆盖多数小亏"的突破形态）。
  4. expR>0 ∧ 逐股为正比例>1/2（分母=全部有效标的，含 0 笔交易标的）
     ∧ 结构同型（win_rate<0.60 ∧ avg_win_r/|avg_loss_r|≥2.0 ∧
     avg_loss_r>-1.5）→ 复现。
  5. 其余（expR>0 但未达复现线且非完全变形）→ 不复现（未达复现线，报告
     写明缺哪一维）。

  阈值论证：
  - 逐股为正 >1/2：ETF 池 LOO 全正（AI D3），域外复现最低要求降为"过半
    标的方向为正"——期望结构属于池整体而非个别标的。
  - 结构同型线：ETF 池实测胜率 37.8%、盈亏比 5.66；突破形态本质是少数
    大赢覆盖多数小亏，胜率<0.60 且比值≥2 是该结构的最宽松包络。
  - avg_loss>-1.5：R 按入场预设风险归一，正常截断下单笔亏≈1R；平均亏
    1.5R+ 说明出场规则在个股跳空下失效——结构变形的核心证据。
  - N≥15：期望估计的最低样本量。

【对照登记（描述性，不参与判定）】每笔打 AO 两个栖息地标签：
  rv60_pctl = 标的 60 日已实现波动（日对数收益 std×√252×100）在自身近
  756 交易日内的分位；b20_pctl5y = cn_all 20日宽度读数在近 1260 交易日
  （5年）的分位。分位口径 (#<x + 0.5×#==)/n×100，桶边界 Q1[0,20)|
  Q2[20,40)|Q3[40,60)|Q4[60,80)|Q5[80,100]，与 AO 报告一致。b20 共用
  同一宽度序列 breadth_cn_all.parquet（截至 2026-08-27，晚于此的信号
  标签记 null）。个股池共用同一宽度序列（宽度是市场层变量）。

【红线】参数零改动；不删标的"洗干净"结果（本池 15/15 数据可得，无剔除）；
不使用买卖指令类词汇；结论不回答"该不该在个股上用模块B"——只回答期望
是否复现。输出只新增 docs/experiments/raw/agent_AQ/。
复现：PYTHONHASHSEED=0 / =42 各跑一次，规范化 JSON sha256 须一致。
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
RAW = REPO / "docs/experiments/raw/agent_AQ"
POOL_DIR = RAW / "pool"
MANIFEST = RAW / "pool_manifest.json"
OUT = RAW / "moduleB_stock_pool.json"
BREADTH = Path.home() / ".lei_signal_lab/cache/timing/breadth_cn_all.parquet"

POOL_BROAD = ("510050.SS", "510300.SS", "510500.SS", "512100.SS",
              "159901.SZ", "159915.SZ", "588000.SS")
CB, CL = 40, 0.08
ANCHOR = {"N": 37, "expR": 0.9441, "top1": "512100.SS",
          "top1_share": (0.40, 0.50),
          "t512100_r_net": sorted([-0.1395, 15.9697])}
ETF_STRUCT = {"win_rate": 0.3784, "avg_win_r": 3.515, "avg_loss_r": -0.621}

EXPECTED_POOL = (
    "600519.SS", "000858.SZ", "601318.SS", "600036.SS", "300750.SZ",
    "002594.SZ", "600900.SS", "601899.SS", "000333.SZ", "600030.SS",
    "600276.SS", "002415.SZ", "000063.SZ", "601857.SS", "000725.SZ",
)

STASH_TRACKED = "a816485"
STASH_UNTRACKED = "1a321ce"

B_Q = [("Q1[0,20)", 0.0, 20.0), ("Q2[20,40)", 20.0, 40.0), ("Q3[40,60)", 40.0, 60.0),
       ("Q4[60,80)", 60.0, 80.0), ("Q5[80,100]", 80.0, 100.0001)]


def build_v2_env(env_dir: Path) -> dict:
    """与 run_pollution_recheck.py / agent_AI 完全同一的环境重建（只读 git）。"""
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
    Path("/tmp/agent_AQ").mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text())
    pool_meta = [m for m in manifest["pool"] if m["ok"]]
    pool_syms = tuple(m["symbol"] for m in pool_meta)
    assert set(pool_syms) == set(EXPECTED_POOL), f"池与预注册名单不一致: {pool_syms}"
    meta_by_sym = {m["symbol"]: m for m in pool_meta}

    env = tempfile.mkdtemp(prefix="lei_v2env_aq_", dir="/tmp/agent_AQ")
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

    # ---------- A. 环境锚：深池 ETF 7 池原参数原样 ----------
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

    # ---------- B. 个股池（hfq 帧覆盖/注入） ----------
    stock_bars = {}
    for sym in pool_syms:
        df = pd.read_parquet(POOL_DIR / f"{sym}.bars.parquet")
        df = df[~df.index.duplicated(keep="last")].sort_index()
        assert len(df) >= 300, f"{sym} 行数不足: {len(df)}"
        stock_bars[sym] = df
    frames_stock = load_pool_frames()
    for sym in pool_syms:
        frames_stock[sym] = classify_colors(compute_features(stock_bars[sym]))
    reset_caches(frames_stock)
    s_stock = _summarize(execute_run(run_params(pool_syms)), "STOCK_POOL_hfq")
    ov = s_stock["overview"]
    trades = s_stock["trades_detail"]

    # ---------- 判定输入 ----------
    n_syms = len(pool_syms)
    by_sym = {b["symbol"]: b for b in s_stock["by_symbol"]}
    n_pos_syms = sum(1 for sym in pool_syms
                     if by_sym.get(sym) and (by_sym[sym]["expectancy_r"] or 0) > 0)
    n_traded = sum(1 for sym in pool_syms if by_sym.get(sym))
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

    # 预注册判定（按序）
    if not anchor_ok:
        verdict = "样本/数据不足（环境锚不匹配，环境不等价）"
    elif n_syms < 10 or (ov["trade_count"] or 0) < 15:
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
            miss.append(f"逐股为正比例 {n_pos_syms}/{n_syms} 未过半")
        if not same_shape:
            miss.append(f"结构未同型（胜率 {win_rate:.2%}，盈亏比 {ratio:.2f}，"
                        f"均亏 {avg_loss:+.3f}R）")
        verdict = "不复现（未达复现线：" + "；".join(miss) + "）"

    # ---------- AO 栖息地标签（对照登记，描述性） ----------
    b20 = pd.read_parquet(BREADTH)["b20"].dropna()
    b20_idx = {d: i for i, d in enumerate(b20.index)}
    rv_cache = {}
    for sym in pool_syms:
        df = stock_bars[sym].copy()
        df["lr"] = np.log(df["close"]).diff()
        df["rv60"] = df["lr"].rolling(60).std() * np.sqrt(252) * 100
        rv_cache[sym] = df
    labels = []
    for t in sorted(trades, key=lambda t: (t["signal_date"], t["symbol"])):
        sym, sd = t["symbol"], t["signal_date"]
        ts = pd.Timestamp(sd)
        df = rv_cache[sym]
        i = df.index.get_loc(ts)
        rv60 = float(df["rv60"].iloc[i])
        rv_series = df["rv60"].iloc[: i + 1].dropna().iloc[-756:].to_numpy()
        if ts in b20_idx:
            k = b20_idx[ts]
            b20_cur = float(b20.iloc[k])
            w1 = b20.iloc[max(0, k - 1259): k + 1].to_numpy()
            b20_pctl = round(pct_rank(w1, b20_cur), 1)
            b20_bucket = bucket_q(b20_pctl)
        else:
            b20_cur = b20_pctl = b20_bucket = None
        rv_pctl = round(pct_rank(rv_series, rv60), 1)
        labels.append({
            "symbol": sym, "signal_date": sd, "r_net": round(t["r_net"], 4),
            "rv60_pctl": rv_pctl, "rv60_bucket": bucket_q(rv_pctl),
            "rv60_ann": round(rv60, 1), "rv_series_n": int(len(rv_series)),
            "b20_raw": round(b20_cur, 2) if b20_cur is not None else None,
            "b20_pctl5y": b20_pctl, "b20_bucket": b20_bucket,
            "exit_reason": t["exit_reason"],
        })

    # 桶内均值（描述性）
    def bucket_stats(key):
        out = {}
        for lab, _, _ in B_Q:
            grp = [r["r_net"] for r in labels if r[key] == lab]
            out[lab] = {"n": len(grp),
                        "mean_r": round(float(np.mean(grp)), 4) if grp else None,
                        "sum_r": round(float(np.sum(grp)), 4) if grp else None}
        none_grp = [r["r_net"] for r in labels if r[key] is None]
        if none_grp:
            out["null"] = {"n": len(none_grp),
                           "mean_r": round(float(np.mean(none_grp)), 4)}
        return out

    # ---------- 输出 ----------
    results = {
        "task": "模块B（密集突破）高流动性A股个股池边界测试（预注册域外复现）",
        "params": {"pool": list(pool_syms), "module": "B", "cb": CB, "cl": CL,
                   "entry": "breakout", "exit": "b3_dual", "volume_confirm": False,
                   "fee": "standard", "limit_guard": True, "rr_min": None,
                   "data": "腾讯 hfq 后复权 2016-01-04~2026-09-03（宁德时代 2018-06-11 起）"},
        "env_snapshot_sha256_16": env_sha,
        "survivorship_bias_declared": ("名单按当前市值/流动性挑选，用今天还活着的大公司"
                                       "回测历史天然高估收益；结论只用于方向性判断"),
        "pool_manifest": [{k: m[k] for k in ("symbol", "name", "industry", "rows",
                                             "start", "end", "adjusted",
                                             "corp_action_jumps", "big_days")}
                          for m in pool_meta],
        "anchor_ETF": {
            "N": ov_a["trade_count"], "expR": round(ov_a["expectancy_r"], 4),
            "IS": None if s_anchor["is_expectancy"] is None else round(s_anchor["is_expectancy"], 4),
            "OOS": None if s_anchor["oos_expectancy"] is None else round(s_anchor["oos_expectancy"], 4),
            "top1_symbol": s_anchor["top1_symbol"], "top1_share": round(top1_share_a, 4),
            "t512100_r_net": t512, "anchor_ok": anchor_ok,
            "by_symbol_positive_share_etf": round(sum(
                1 for b in s_anchor["by_symbol"] if (b["expectancy_r"] or 0) > 0
            ) / len(POOL_BROAD), 4),
        },
        "stock_pool": {
            "N": ov["trade_count"], "expR": None if exp_r is None else round(exp_r, 4),
            "IS": None if s_stock["is_expectancy"] is None else round(s_stock["is_expectancy"], 4),
            "OOS": None if s_stock["oos_expectancy"] is None else round(s_stock["oos_expectancy"], 4),
            "win_rate": None if win_rate is None else round(win_rate, 4),
            "avg_win_r": None if avg_win is None else round(avg_win, 4),
            "avg_loss_r": None if avg_loss is None else round(avg_loss, 4),
            "win_loss_ratio": None if ratio is None else round(ratio, 4),
            "profit_factor": ov["profit_factor"], "total_r": ov["total_r"],
            "max_consecutive_losses": ov["max_consecutive_losses"],
            "max_drawdown_1r": ov["max_drawdown_1r"],
            "n_symbols_traded": n_traded, "n_symbols_total": n_syms,
            "n_symbols_positive": n_pos_syms, "positive_symbol_share": round(share_pos, 4),
            "etf_struct_reference": ETF_STRUCT,
            "by_symbol": s_stock["by_symbol"],
            "by_year": s_stock["by_year"],
        },
        "conditions": {
            "anchor_ok": anchor_ok, "n_symbols_ok": n_syms >= 10,
            "N_ok": (ov["trade_count"] or 0) >= 15,
            "expR_positive": exp_r is not None and exp_r > 0,
            "positive_symbol_share_gt_half": share_pos > 0.5,
            "shape_same_type": same_shape, "shape_deformed": deformed,
        },
        "habitat_labels_descriptive": {
            "note": "AO 两栖息地标签对照登记，不参与判定；b20 为市场层宽度，个股共用",
            "bucket_stats_rv60": bucket_stats("rv60_bucket"),
            "bucket_stats_b20": bucket_stats("b20_bucket"),
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
          f"expR={ov_a['expectancy_r']:+.4f} top1={s_anchor['top1_symbol']} "
          f"share={top1_share_a:.1%}")
    print(f"个股池: N={ov['trade_count']} expR={exp_r:+.4f} "
          f"胜率={win_rate:.2%} 赢单均={avg_win:+.3f} 输单均={avg_loss:+.3f} "
          f"盈亏比={ratio:.2f}")
    print(f"逐股为正: {n_pos_syms}/{n_syms}（有交易 {n_traded} 只）")
    print(f"条件: {results['conditions']}")
    print(f"判定（预注册）: {verdict}")
    print(f"HASH(规范化JSON): {hashlib.sha256(canon.encode()).hexdigest()}")
    shutil.rmtree(env, ignore_errors=True)


if __name__ == "__main__":
    main()
