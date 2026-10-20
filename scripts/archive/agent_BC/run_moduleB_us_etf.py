#!/usr/bin/env python3
"""任务 BC：模块B（密集突破）美股核心 ETF 池边界测试 · 预注册（跑前写死，跑后不得调）。

【核心问题（唯一要回答的）】模块B 参数原封不动跑在美股核心 ETF 上，正期望
是否保留？域外复现测试——参数零改动，测不过就是测不过。

【被测结论】（Y/AI/AO/AQ 已入库）
  宽基 ETF 7 池（510050/510300/510500/512100/159901/159915/588000），
  模块B breakout × b3_dual × vc0，cb=40/cl=8%，fee=standard，limit_guard=True：
  N=37, expR=+0.9441, 胜率 37.84%, 赢单均 +3.515R, 输单均 -0.621R；
  AI 判"稳健（低冗余）"；AQ 高流动性 A 股个股池 15 只复现（N=98, expR=+0.726,
  胜率 36.7%, 盈亏比 5.48）。AO 栖息地 = 标的自身波动中等偏上（rv60 非贴地）
  + 短期热度不极端。先验不利因素：美股大盘 ETF 波动显著低于创业板 ETF 与
  个股，可能整体落入 AO 的"波动贴地"毒药区——也可能不是，边界测试回答之。

【标的池（跑前写死；名单以 pool_manifest.json ok 者为准，预期 8/8）】
  QQQ、SPY、DIA、IWM、XLK、XLF、XLV、XLE（美股核心 ETF：三大指数+小盘+
  五大行业），yfinance auto_adjust 全史（上市 1993-1999 起）。
  数据客观不可得的剔除并逐只记录（fetch manifest error 原文），唯一合法
  剔除理由，禁止删标的洗结果。
  池构成偏差（登记）：8 只全部是"活到今天且规模最大"的 ETF——用今天仍
  存续的核心池回测历史，存在与 AQ 池同类的幸存者偏差上限；ETF 的幸存者
  偏差弱于个股（被动跟踪指数、无个股级衰败），但 1998-1999 年成立时点
  本身处于互联网泡沫前的行业格局，方向性判断时须连同此限定引用。

【参数（与 Y/AI/AQ 完全同一，零改动）】module=B, entry=breakout,
  exit=b3_dual, volume_confirm=False（窗口 1）, rr_min=None, fee=standard
  （单边 max(5bp 名义值, $0.005/股)，账本 fees_and_slippage V2.1 本就按
  美股口径标定）, limit_guard=True, overrides=(cb=40, cl=8%)。

【美股适配点（零代码改动，全部为引擎既有语义，逐点写明）】
 1. 交易日历：V2 引擎逐标的在自身帧索引上推进（信号日 t → t+1 开盘入场；
    退出收盘确认 → 次根开盘执行），无 A 股日历假设；注入美股日线帧后
    日历即美股自身。OOS 切分 = 选中帧最大日期往前 730 自然日（引擎原逻辑）。
 2. limit_guard=True 原样传入：涨跌停守卫仅作用于 .SS/.SZ 标的
    （engine.is_cn_symbol），美股代码自动惰性化——美股无个股涨跌停制度，
    惰性即正确语义，无需改任何代码。
 3. 市场基准时钟（美股→^GSPC）仅用于 benchmark_clock_type 描述性标签；
    选中 8 只不含 ^GSPC → 无基准帧 → 标签全 0，不影响 r_net 与任何判定
    输入（与 AQ 个股池选中集不含 000300 的同款行为）。
 4. 深池已有 XLK 短版（2016-08 起，yahoo_v8）——本任务一律以自己的全史版
    覆盖注入（AQ 个股池先例：同名短版一律被本任务长版覆盖）。

【环境锚（预注册匹配线）】先在深池 ETF 7 池原参数原样重跑：须 N=37
  ∧ |ΔexpR|≤0.02 ∧ top1=512100.SS ∧ top1 份额∈[40%,50%] ∧ 512100 两笔
  r_net 逐位一致（-0.1395 / +15.9697）。不匹配 → 一切判定只能为
  "样本/数据不足（环境不等价）"。

【预注册三选一判定线（跑前写死，按序求值，命中即止）】
 0. 环境锚不匹配                      → 样本/数据不足（环境不等价）。
 1. 有效标的 <5 ∨ 合并池已平仓 N<15   → 样本/数据不足。
    （有效标的 = manifest ok 且进入回测帧的标的。任务书池 6-8 只，<5 表示
      预注册池多数数据不可得、池本身失效。A 股 ETF 密度 37笔/7只≈5.3笔/只，
      美股池单标的历史更长（约 27-33 年 vs A 股池 10 年），N<15 表示信号
      密度塌陷超八成且不足以估计期望。）
 2. 合并池 expR ≤ 0                   → 不复现。
 3. 结构完全变形                      → 不复现。
    变形（写死，AQ 同款）：avg_loss_r ≤ -1.5（预设止损截断失效成常态：
    美股隔夜跳空穿越止损）∨ (win_rate ≥ 0.60 ∧ avg_win_r/|avg_loss_r| < 2)
    （胜率与盈亏比结构倒挂，不再是"少数大赢覆盖多数小亏"的突破形态）。
 4. expR>0 ∧ 逐标的为正比例>1/2（分母=全部有效标的，含 0 笔交易标的）
    ∧ 结构同型（win_rate<0.60 ∧ avg_win_r/|avg_loss_r|≥2.0 ∧
    avg_loss_r>-1.5）→ 复现。
 5. 其余（expR>0 但未达复现线且非完全变形）→ 不复现（未达复现线，报告
    写明缺哪一维）。
 阈值论证（AQ 同款）：ETF 池 LOO 全正（AI D3）→ 域外复现最低要求降为
 "过半标的方向为正"；ETF 池实测胜率 37.8%/盈亏比 5.66 → 胜率<0.60 且
 比值≥2 是突破形态最宽松包络；avg_loss>-1.5 = 出场规则未失效；N≥15 =
 期望估计最低样本量。
 【若判不复现】追加机制登记（任务书要求）：逐笔 rv60 分位桶分布 vs AO
 "波动贴地"栖息地——检查美股 ETF 信号是否集中在 rv60-Q1（贴地桶），
 作为机制解释登记（描述性，不改变判定）。

【AO 标签对照（登记不判定，跑前冻结）】每笔打两个标签：
  - rv60_pctl：标的 60 日已实现波动（日对数收益 std×√252×100）在自身近
    756 交易日内的分位；分位口径 (#<x + 0.5×#==)/n×100，桶边界
    Q1[0,20)|Q2[20,40)|Q3[40,60)|Q4[60,80)|Q5[80,100]，与 AO/AQ 一致。
  - b20 替代标签（冻结决策）：任务书给定两选一（"标的自身 20 日涨幅分位"
    替代 或 省略）。本任务选择替代，但替代口径取仓库既有美股市场层宽度
    breadth_sp500 的 b20（标普500 成分股收盘价站上自身 20 日均线的比例%，
    1986-01 起全史，AJ/AW 任务已在用）的 5 年（1260 交易日）分位——与 AO
    的 cn_all b20 同一构造（市场参与广度温度计），比"标的自身涨幅分位"
    更忠实于 AO 原意（AO 的 H2 是市场层短线过热假设）。数据源为本任务
    目录副本 pool/breadth_sp500_b20.parquet（截至 2026-08-27，晚于此的
    信号记 null）。已知错配登记：QQQ 跟踪纳斯达克100、用标普500 宽度标注
    是错配近似；桶边界与 AO 一致。

【红线】参数零改动；禁止为美股调参；禁止删标的洗结果（数据不可得除外，
逐只记录）；不使用买卖指令类词汇；结论不回答"该不该在美股用"——只回答
期望是否复现。输出只新增 docs/experiments/raw/agent_BC/。
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
BREADTH_COPY = POOL_DIR / "breadth_sp500_b20.parquet"
OUT = RAW / "moduleB_us_etf.json"

POOL_BROAD = ("510050.SS", "510300.SS", "510500.SS", "512100.SS",
              "159901.SZ", "159915.SZ", "588000.SS")
POOL_US_PREREG = ("QQQ", "SPY", "DIA", "IWM", "XLK", "XLF", "XLV", "XLE")
CB, CL = 40, 0.08
ANCHOR = {"N": 37, "expR": 0.9441, "top1": "512100.SS",
          "top1_share": (0.40, 0.50),
          "t512100_r_net": sorted([-0.1395, 15.9697])}
ETF_STRUCT = {"win_rate": 0.3784, "avg_win_r": 3.515, "avg_loss_r": -0.621}
AQ_STRUCT = {"win_rate": 0.367, "avg_win_r": 2.882, "avg_loss_r": -0.526}

STASH_TRACKED = "a816485"
STASH_UNTRACKED = "1a321ce"

B_Q = [("Q1[0,20)", 0.0, 20.0), ("Q2[20,40)", 20.0, 40.0), ("Q3[40,60)", 40.0, 60.0),
       ("Q4[60,80)", 60.0, 80.0), ("Q5[80,100]", 80.0, 100.0001)]


def build_v2_env(env_dir: Path) -> dict:
    """与 run_pollution_recheck.py / agent_AI / agent_AQ 完全同一的环境重建（只读 git）。"""
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
    manifest = json.loads(MANIFEST.read_text())
    pool_meta = [m for m in manifest["symbols"] if m["ok"]]
    pool_syms = tuple(m["symbol"] for m in pool_meta)
    assert set(pool_syms) <= set(POOL_US_PREREG), f"池外标的: {pool_syms}"
    meta_by_sym = {m["symbol"]: m for m in pool_meta}

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

    # ---------- B. 美股 ETF 池（全史帧注入/覆盖） ----------
    us_bars = {}
    for sym in pool_syms:
        df = pd.read_parquet(POOL_DIR / f"{sym}.bars.parquet")
        df = df[~df.index.duplicated(keep="last")].sort_index()
        assert len(df) >= 300, f"{sym} 行数不足: {len(df)}"
        us_bars[sym] = df
    frames_us = load_pool_frames()
    for sym in pool_syms:
        frames_us[sym] = classify_colors(compute_features(us_bars[sym]))
    reset_caches(frames_us)
    s_us = _summarize(execute_run(run_params(pool_syms)), "US_ETF_pool_full_history")
    ov = s_us["overview"]
    trades = s_us["trades_detail"]

    # ---------- 判定输入 ----------
    n_syms = len(pool_syms)
    by_sym = {b["symbol"]: b for b in s_us["by_symbol"]}
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

    # ---------- AO 栖息地标签（对照登记，描述性不参与判定） ----------
    b20 = pd.read_parquet(BREADTH_COPY)["b20"].dropna()
    b20_idx = {d: i for i, d in enumerate(b20.index)}
    rv_cache = {}
    for sym in pool_syms:
        df = us_bars[sym].copy()
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

    rv_q1 = bucket_stats("rv60_bucket")["Q1[0,20)"]
    mechanism_note = None
    if verdict.startswith("不复现"):
        mech = []
        if rv_q1["n"]:
            share_q1 = rv_q1["n"] / max(len(labels), 1)
            mech.append(
                f"rv60-Q1（波动贴地）桶 {rv_q1['n']}/{len(labels)} 笔"
                f"（{share_q1:.0%}），桶内均值 {rv_q1['mean_r']}R"
                + ("——信号集中在 AO 毒药区（波动贴地），机制解释成立"
                   if share_q1 >= 0.5 else
                   "——未过半集中在波动贴地桶，毒药区机制解释不充分"))
        mechanism_note = "；".join(mech) if mech else "无标签数据"

    # ---------- 输出 ----------
    results = {
        "task": "模块B（密集突破）美股核心 ETF 池边界测试（预注册域外复现）",
        "params": {"pool": list(pool_syms), "module": "B", "cb": CB, "cl": CL,
                   "entry": "breakout", "exit": "b3_dual", "volume_confirm": False,
                   "fee": "standard", "limit_guard": True, "rr_min": None,
                   "limit_guard_note": "涨跌停守卫仅对 .SS/.SZ 生效，美股标的自动惰性（美股无涨跌停制度，惰性即正确语义）",
                   "data": "yfinance auto_adjust 全史（本任务 pool/ 目录，未动共享缓存）"},
        "env_snapshot_sha256_16": env_sha,
        "pool_bias_declared": ("8 只均为存续至今的核心 ETF（被动跟踪指数）——"
                               "幸存者偏差弱于个股池但非零；1998-1999 成立时点"
                               "处于互联网泡沫前行业格局"),
        "pool_manifest": [{k: m.get(k) for k in ("symbol", "rows", "start", "end",
                                                 "adjusted", "envelope_repair",
                                                 "corp_action_jumps",
                                                 "big_days_gt12pct")}
                          for m in pool_meta],
        "pool_manifest_excluded": [{"symbol": m["symbol"], "error": m.get("error")}
                                   for m in manifest["symbols"] if not m["ok"]],
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
        "us_pool": {
            "N": ov["trade_count"], "expR": None if exp_r is None else round(exp_r, 4),
            "IS": None if s_us["is_expectancy"] is None else round(s_us["is_expectancy"], 4),
            "OOS": None if s_us["oos_expectancy"] is None else round(s_us["oos_expectancy"], 4),
            "win_rate": None if win_rate is None else round(win_rate, 4),
            "avg_win_r": None if avg_win is None else round(avg_win, 4),
            "avg_loss_r": None if avg_loss is None else round(avg_loss, 4),
            "win_loss_ratio": None if ratio is None else round(ratio, 4),
            "profit_factor": ov["profit_factor"], "total_r": ov["total_r"],
            "max_consecutive_losses": ov["max_consecutive_losses"],
            "max_drawdown_1r": ov["max_drawdown_1r"],
            "avg_holding_bars": ov["avg_holding_bars"],
            "data_range": s_us["data_range"],
            "n_symbols_traded": n_traded, "n_symbols_total": n_syms,
            "n_symbols_positive": n_pos_syms, "positive_symbol_share": round(share_pos, 4),
            "etf_struct_reference": ETF_STRUCT, "a_stock_pool_struct_reference": AQ_STRUCT,
            "by_symbol": s_us["by_symbol"],
            "by_year": s_us["by_year"],
        },
        "conditions": {
            "anchor_ok": anchor_ok, "n_symbols_ok": n_syms >= 5,
            "N_ok": (ov["trade_count"] or 0) >= 15,
            "expR_positive": exp_r is not None and exp_r > 0,
            "positive_symbol_share_gt_half": share_pos > 0.5,
            "shape_same_type": same_shape, "shape_deformed": deformed,
        },
        "habitat_labels_descriptive": {
            "note": ("AO 两栖息地标签对照登记，不参与判定。rv60=标的自身 60 日波动"
                     "的近 3 年分位；b20 替代口径=仓库既有美股市场层宽度 "
                     "breadth_sp500.b20 的 5 年分位（与 cn_all b20 同构造；QQQ 用"
                     "标普500 宽度标注为错配近似，登记）"),
            "bucket_stats_rv60": bucket_stats("rv60_bucket"),
            "bucket_stats_b20": bucket_stats("b20_bucket"),
            "trades": labels,
        },
        "failure_mechanism_note": mechanism_note,
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
    print(f"美股池: N={ov['trade_count']} expR={exp_r:+.4f} "
          f"胜率={win_rate:.2%} 赢单均={avg_win:+.3f} 输单均={avg_loss:+.3f} "
          f"盈亏比={ratio:.2f}" if exp_r is not None and win_rate is not None
          else f"美股池: N={ov['trade_count']} expR={exp_r}")
    print(f"逐标的为正: {n_pos_syms}/{n_syms}（有交易 {n_traded} 只）")
    print(f"条件: {results['conditions']}")
    if mechanism_note:
        print(f"机制登记: {mechanism_note}")
    print(f"判定（预注册）: {verdict}")
    print(f"HASH(规范化JSON): {hashlib.sha256(canon.encode()).hexdigest()}")
    shutil.rmtree(env, ignore_errors=True)


if __name__ == "__main__":
    main()
