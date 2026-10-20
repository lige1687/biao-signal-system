#!/usr/bin/env python3
"""动态入池与动态权重·预注册实验（2026-08-28，跑前写死，跑后不改）。

用户立项背景：① 为什么是这 9 只？能否用系统化规则动态选池（此前只测过
往固定池加 4 只被排除成员=判负）；② 池内动态权重（此前只测过 60 日动量
±1.5 倍=判负）。

【A 组·动态入池】
候选宇宙（18，历史起点均 ≤2015-06-16）：沪深300/上证50/中证白酒/国证地产/
创业板指/证券公司/新能车/中证医疗/国证有色/中证1000/上证红利/中证军工/
中证银行/中证煤炭/国证钢铁/中证传媒/中证计算机/中证家电。
规则（系统元规律「有效性=与全A分母同频」）：每个选样日（2015-06-16 首选
+ 此后每年 12 月末），按「过去 52 周周收益与等权全 A 的相关系数」降序取
前 9；并列以 52 周方差低者优先；次日生效，年度换仓含 10bp。
对照 = 固定 9 池（B 形态 v1-final）。采纳线同前：Calmar ≥ 0.375 且
年化 ≥ 10.99。附：逐年入池名单。

【B 组·动态权重（固定 9 池底盘）】
W1 逆波动率：权重 ∝ 1/σ(60 日)，周频重算。
W2 温和慢动量：120 日收益排名，前半 ×1.3 / 后半 ×0.7，季频重算。
W3 满仓档动量：W2 的倾斜仅在预算=1.0（B200<43.3）时启用，半/空档恢复
等权（防 O1 判负的「崩盘期高贝塔超配」失效模式）。
采纳线同上。声明：本轮共 4 个新假设在同一窗口检验，多重比较风险已
知，采纳线从严且全部披露。

输出：docs/experiments/raw/portfolio_split/bform_dynamic_results.json
复现：PYTHONHASHSEED=0 python3 scripts/run_bform_dynamic.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "docs/experiments/raw"
sys.path.insert(0, str(REPO / "scripts"))

import run_portfolio_split as rps  # noqa: E402
from run_siphon_detector import load_data  # noqa: E402

CAL_BAR, ANN_BAR, POOL_K = 0.375, 10.99, 9

UNIVERSE = {
    "沪深300": "sh000300", "上证50": "sh000016", "中证白酒": "sz399997",
    "国证地产": "sz399393", "创业板指": "399006x", "证券公司": "399975x",
    "新能车": "sz399976", "中证医疗": "sz399989", "国证有色": "sz399395",
    "中证1000": "sh000852", "上证红利": "sh000015", "中证军工": "sz399967",
    "中证银行": "sz399986", "中证煤炭": "sz399998", "国证钢铁": "sz399440",
    "中证传媒": "sz399971", "中证计算机": "sz399363", "中证家电": "sz399994",
}
PATH_FIX = {"399006x": "siphon_detector/cyb_399006_close.parquet",
            "399975x": "siphon_detector/sec_399975_close.parquet"}
FIXED9 = ["沪深300", "上证50", "中证白酒", "国证地产", "创业板指", "证券公司",
          "新能车", "中证医疗", "国证有色"]


def load_all() -> pd.DataFrame:
    frames = {}
    for name, code in UNIVERSE.items():
        rel = PATH_FIX.get(code, f"portfolio_split/{code}_close.parquet")
        s = pd.read_parquet(SRC / rel)["close"].astype(float)
        s.index = pd.to_datetime(s.index)
        frames[name] = s
    px = pd.DataFrame(frames)
    px = px[(px.index >= pd.Timestamp(rps.WIN_START))
            & (px.index <= pd.Timestamp(rps.WIN_END))].dropna(axis=0, how="any")
    return px


def simulate_direct(prices: pd.DataFrame, target: pd.DataFrame) -> pd.Series:
    """target 为完整目标权重矩阵（列=prices 列），5% 带 + 10bp。"""
    rets = prices.pct_change().fillna(0.0)
    names = list(prices.columns)
    actual = np.zeros(len(names))
    eq = []
    port = 1.0
    tgt_vals = target[names].values
    for i in range(len(prices)):
        if i > 0:
            port *= 1.0 + float(actual @ rets.iloc[i].values)
        t = tgt_vals[i]
        trade = np.abs(t - actual) >= 0.05
        new = np.where(trade, t, actual)
        port *= 1.0 - 0.001 * float(np.abs(new - actual).sum())
        actual = new
        eq.append(port)
    return pd.Series(eq, index=prices.index)


def tier_weekly_matrix(prices, b200):
    bw, bsig = rps.weekly_last(b200)
    w = bw.map(lambda v: 1.0 if v < 43.3 else (0.5 if v < 56.7 else 0.0))
    daily = pd.Series(np.nan, index=prices.index)
    pos = prices.index.searchsorted(list(bsig.values))
    for p, wt in zip(pos, w.values):
        if p + 1 < len(prices.index):
            daily.iloc[p + 1] = wt
    return daily.ffill().fillna(0.0)


def judge(name, m, out):
    out[name] = {**m, "adopt": bool(m["calmar"] is not None
                                    and m["calmar"] >= CAL_BAR and m["ann_pct"] >= ANN_BAR)}


def main() -> None:
    data = load_data()
    eqw, b200 = data["eqw"], data["ab_daily"]
    px18 = load_all()
    prices = px18  # 18 列全窗口可用
    tier = tier_weekly_matrix(prices, b200)

    out = {}
    # 固定 9 池基线（在 18 列矩阵上重建，等价校验）
    tgt_fixed = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    for c in FIXED9:
        tgt_fixed[c] = tier / len(FIXED9)
    judge("基线_固定9池", rps.metrics(simulate_direct(prices, tgt_fixed)), out)

    # ── A 组：动态入池 ──
    ew_w = eqw.resample("W-FRI").last()
    sel_dates = [prices.index[0]] + [d for d in prices.index if (d.month == 12 and
                                 d == prices.index[prices.index.to_period("M") == d.to_period("M")][-1])]
    weekly_px = prices.resample("W-FRI").last()
    wret = weekly_px.pct_change(fill_method=None)
    ewret = ew_w.pct_change(fill_method=None)
    tgt_dyn = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    yearly_members = {}
    cur = None
    for sd in sel_dates:
        hist = wret[(wret.index <= sd) & (wret.index > sd - pd.Timedelta(weeks=52))]
        ewh = ewret[(ewret.index <= sd) & (ewret.index > sd - pd.Timedelta(weeks=52))]
        if len(hist) < 40:
            continue
        corr = {c: hist[c].corr(ewh) for c in prices.columns}
        var = {c: float(hist[c].var()) for c in prices.columns}
        ranked = sorted(prices.columns, key=lambda c: (-corr[c], var[c]))
        cur = ranked[:POOL_K]
        yearly_members[str(sd.date())] = {m: round(corr[m], 3) for m in cur}
    # 应用：每个选样日生效次日
    seg_start = 0
    dyn_plan = []  # (生效日index, 成员集)
    for sd in sel_dates:
        hist = wret[(wret.index <= sd) & (wret.index > sd - pd.Timedelta(weeks=52))]
        if len(hist) < 40:
            continue
        ewh = ewret[(ewret.index <= sd) & (ewret.index > sd - pd.Timedelta(weeks=52))]
        corr = {c: hist[c].corr(ewh) for c in prices.columns}
        var = {c: float(hist[c].var()) for c in prices.columns}
        ranked = sorted(prices.columns, key=lambda c: (-corr[c], var[c]))
        members = ranked[:POOL_K]
        i = prices.index.searchsorted(sd)
        if i + 1 < len(prices.index):
            dyn_plan.append((i + 1, members))
    cur_members = set()
    cur_i = 0
    plan_i = 0
    for i in range(len(prices.index)):
        if plan_i < len(dyn_plan) and i == dyn_plan[plan_i][0]:
            cur_members = set(dyn_plan[plan_i][1])
            plan_i += 1
        row = np.zeros(len(prices.columns))
        if cur_members:
            for j, c in enumerate(prices.columns):
                if c in cur_members:
                    row[j] = tier.iloc[i] / POOL_K
        tgt_dyn.iloc[i] = row
    judge("A_动态入池_耦合度", rps.metrics(simulate_direct(prices, tgt_dyn)), out)

    # ── B 组：动态权重（固定 9 池） ──
    p9 = prices[FIXED9]
    tier9 = tier_weekly_matrix(p9, b200)
    n = len(FIXED9)

    # W1 逆波动率（周频）
    vol60 = p9.pct_change().rolling(60).std()
    inv = (1.0 / vol60).div((1.0 / vol60).sum(axis=1), axis=0)
    inv = inv.ffill().fillna(1.0 / n).shift(1).fillna(1.0 / n)
    t_w1 = inv.mul(tier9, axis=0)
    judge("W1_逆波动率", rps.metrics(simulate_direct(p9, t_w1)), out)

    # W2 温和慢动量（季频，120 日）
    r120 = p9.pct_change(120)
    above = r120.sub(r120.mean(axis=1), axis=0) > 0
    # 季末重算：取每季最后交易日
    q_lab = p9.index.to_period("Q")
    q_days = [p9.index[np.flatnonzero(q_lab == q)[-1]] for q in sorted(set(q_lab))]
    tilt = pd.Series(index=p9.index, dtype=object)
    tilt_map = {}
    for d in q_days:
        tilt_map[d] = above.loc[:d].iloc[-1]
    cur_t = None
    t_w2 = pd.DataFrame(0.0, index=p9.index, columns=FIXED9)
    keys = sorted(tilt_map.keys())
    ki = 0
    for i, d in enumerate(p9.index):
        if ki < len(keys) and d >= keys[ki]:
            cur_t = tilt_map[keys[ki]]
            ki += 1
        if cur_t is not None:
            rel = pd.Series(np.where(cur_t.values, 1.3, 0.7), index=FIXED9)
            rel = rel / rel.sum() * n
            t_w2.iloc[i] = rel.values * tier9.iloc[i] / n
        else:
            t_w2.iloc[i] = tier9.iloc[i] / n
    judge("W2_温和慢动量", rps.metrics(simulate_direct(p9, t_w2)), out)

    # W3 满仓档动量（W2 倾斜仅在 tier==1 时）
    t_w3 = t_w2.copy()
    mask_eq = tier9 < 1.0
    t_w3[mask_eq] = np.tile((tier9[mask_eq] / n).values.reshape(-1, 1), (1, n))
    judge("W3_满仓档动量", rps.metrics(simulate_direct(p9, t_w3)), out)

    out["动态池逐年名单"] = yearly_members
    out["baseline_ref"] = {"ann_pct": 11.99, "maxdd_pct": -34.73, "calmar": 0.345}
    path = SRC / "portfolio_split/bform_dynamic_results.json"
    text = json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True, default=str)
    path.write_text(text)
    show = {k: v for k, v in out.items() if k != "动态池逐年名单"}
    print(json.dumps(show, ensure_ascii=False, indent=1, default=str))
    print("动态池逐年名单:")
    for k, v in yearly_members.items():
        print(" ", k, list(v.keys()))
    print("sha256:", hashlib.sha256(text.encode()).hexdigest())


if __name__ == "__main__":
    main()
