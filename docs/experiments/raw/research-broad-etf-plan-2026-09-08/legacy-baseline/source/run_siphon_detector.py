#!/usr/bin/env python3
"""虹吸/结构牛判别器·存在性检验（预注册 2026-08-27，跑前写死，跑后不改）。

背景（两份交接书整合）：
- 冠军 = B200 逆势三档（<43.3 满仓 / 43.3-56.7 半仓 / ≥56.7 空仓，周频）。
- 已证失效模式：结构牛/科技牛中 B200 长期 ≥56.7（2024-09→2026-08 占 72%
  时间）→ 冠军 74% 时间空仓踏空（创业板超额年化 −21%）。
- 架构第 4 层「失效即下岗」已立项但无实现。本实验回答：**宽度结构层是否
  含有可当时判别的信息，能把高位段分成「该下岗（续涨）」与「该防守（将崩）」。
  判负即收案：结构牛只能靠执行层止损兜底。**

【预注册协议】
数据：
- A 股 B200：docs/experiments/raw/breadth_overlay/a_share_breadth_33y_snapshot.json
  （1993-04-22→2026-08-18；早年幸存者偏差 → 主窗 2005-01-01 起）。
- 美股 B200：~/.lei_signal_lab/cache/sp500_ma_breadth_history.json（1986-01→2026-08-14）。
- A 股参照指数 = 等权全 A（a_share_klines_full.parquet 逐日等权收益累乘，
  停牌/复牌/新股噪声如实保留，与宽度分母同源）；美股参照 = ^GSPC 缓存。
- 创业板指 399006：raw/siphon_detector/cyb_399006_close.parquet（不复权指数，无分红问题）。
口径：周频（W-FRI，取周内最后交易日的观测），信号 t 收盘 → 次一交易日收盘执行，
单边成本 10bp。前瞻收益 = 13 周后周收盘/当周收盘 − 1。

P1 高位段事件表：周频 B200≥56.7 的极大连续段，段长 ≥4 周纳入。
  段末标签：崩 = 段末起 13 周参照收益 < −15%；续 = ≥ +5%；平 = 其间。

P2 存在性检验（每候选独立判定，候选 5 个，全部仅用 ≤t 信息）：
  C1 dwell13 = 过去 13 周 B200≥56.7 周占比；C2 dwell26（26 周口径）；
  C3 ext200 = 参照指数收盘/MA200 − 1；C4 slope13 = B200 − 13 周前 B200；
  C5 mean13 = B200 的 13 周均值。
  样本 = 长段（≥4 周）内的全部高位周。按市场内中位数二分，两组前瞻均值差为
  spread。PASS = |pooled spread(A+US 拼池)| ≥ 3pp 且 A/美两市场 spread 同号
  且 按高位段聚类的 block bootstrap（1000 次，seed=0，90% CI）不含 0。
  全部候选 FAIL → 整方向判负收案。

P3 关键事件判决（仅用 P2 的 PASS 候选中 |pooled spread| 最大者）：
  规则 = 高位周内候选值 ≥ 该市场高位周自分位 P75 → 该周 ON。
  ① 2018-12-28→2021-02-19 抱团牛：窗内 ON 周占比 ≥30% 记对；
  ② 2024-09-19→2026-08-18 科技牛：窗内 ON 周占比 ≥30% 记对；
  ③ 2014-10-31→2015-06-12 疯牛：2015-03-13 之后（峰前 13 周）不得出现 ON，记对。
  ≥2 对 → 进 P4；否则判负。LOEO 核验：P75 阈值剔除该窗口自身周后重算，
  三个窗口的对/错不得翻转。

P4 三臂覆盖（仅 P3 通过；标的 = 创业板指(2010-06→) 主 + 等权全A(2005→) 辅）：
  臂1 冠军三档；臂2 冠军+判别器（ON 周档位失效→满仓持有，OFF 周恢复档位，
  v1 极简无止损）；臂3 买入持有。
  基线验证门：臂1 在创业板指 2010-06→2026-08-18 年化与交接书 +13.4% 偏差
  >3pp 时，追加日频信号变体作诊断，取接近者用于 P4 并披露。
  PASS（主判创业板指）= ① 科技牛窗(2024-09-19→)臂2 相对臂3 超额年化
  较 臂1−臂3 改善 ≥15pp；② 全窗臂2 Calmar ≥ 臂1 Calmar；
  ③ 2015-06-12→2016-01-28 股灾段臂2 最大回撤 ≥ −60%。

输出：docs/experiments/raw/siphon_detector/siphon_detector_results.json
复现：PYTHONHASHSEED=0 python3 scripts/run_siphon_detector.py（约 2-3 分钟）
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "docs/experiments/raw/siphon_detector"
CACHE = Path("~/.lei_signal_lab/cache").expanduser()
A_BREADTH_SNAP = REPO / "docs/experiments/raw/breadth_overlay/a_share_breadth_33y_snapshot.json"
US_BREADTH = CACHE / "sp500_ma_breadth_history.json"
A_PANEL = CACHE / "a_share_klines_full.parquet"
GSPC_PARQUET = REPO / "docs/experiments/raw/breadth_position/gspc_long_close.parquet"
CYB_PARQUET = RAW / "cyb_399006_close.parquet"

# ── 预注册参数 ──
HIGH = 56.7
MID = 43.3
COST = 0.001
FWD_WEEKS = 13
CRASH_TH, CONT_TH = -15.0, 5.0  # 崩/续阈值（%）
MIN_EPISODE = 4
A_START = "2005-01-01"
EQW_BUILD_START = "2002-01-01"
MIN_STOCKS = 200
N_BOOT, BOOT_SEED = 1000, 0
P2_MIN_SPREAD = 3.0  # pp
P3_PCT = 75
P3_WINDOWS = {
    "抱团牛": ("2018-12-28", "2021-02-19"),
    "科技牛": ("2024-09-19", "2026-08-18"),
}
P3_2015_WIN = ("2014-10-31", "2015-06-12")
P3_2015_DANGER = "2015-03-13"  # 峰前 13 周
P3_ON_FRAC_TH = 0.30
P4_TECH_WIN = ("2024-09-19", "2026-08-18")
P4_CRASH_WIN = ("2015-06-12", "2016-01-28")
P4_GATE_REF, P4_GATE_TOL = 13.4, 3.0
P4_IMPROVE_TH, P4_CRASH_DD_TH = 15.0, -60.0


# ── 数据构建 ──────────────────────────────────────────────────────────────

def weekly_last(s: pd.Series) -> tuple[pd.Series, pd.Series]:
    """周频取周内最后观测。返回 (周值[Fri 标签], 信号日=周内最后交易日)。"""
    s = s.sort_index().dropna()
    idx = s.index
    labels = idx + pd.to_timedelta(4 - np.asarray(idx.weekday), unit="D")
    g = s.groupby(labels)
    vals = g.last()
    # g.indices 给出各周行位置，取每组最后一行的原交易日作为信号日
    sig = pd.Series([s.index[d].max() for d in g.indices.values() if len(d)], index=vals.index)
    return vals, sig


def build_market(breadth_daily: pd.Series, ref_daily: pd.Series, name: str) -> dict:
    """构建单市场周频分析框：B200、参照指数、候选、前瞻收益、高位段。"""
    bw, bsig = weekly_last(breadth_daily)
    rw, _ = weekly_last(ref_daily)
    ma200 = ref_daily.rolling(200).mean()
    ext_daily = ref_daily / ma200 - 1.0
    ew, _ = weekly_last(ext_daily)

    df = pd.DataFrame({"b200": bw, "ref": rw, "ext200": ew}).dropna(subset=["b200", "ref"])
    df["dwell13"] = (df["b200"] >= HIGH).astype(float).rolling(FWD_WEEKS).mean()
    df["dwell26"] = (df["b200"] >= HIGH).astype(float).rolling(26).mean()
    df["slope13"] = df["b200"] - df["b200"].shift(FWD_WEEKS)
    df["mean13"] = df["b200"].rolling(FWD_WEEKS).mean()
    df["fwd13"] = df["ref"].shift(-FWD_WEEKS) / df["ref"] - 1.0
    df["high"] = df["b200"] >= HIGH

    # 高位段（≥4 周的连续段）
    grp = (df["high"] != df["high"].shift()).cumsum()
    df["ep"] = np.nan
    episodes = []
    for k, seg in df.groupby(grp):
        if not seg["high"].iloc[0] or len(seg) < MIN_EPISODE:
            continue
        df.loc[seg.index, "ep"] = len(episodes)
        end = seg.index[-1]
        fwd = df.loc[end, "fwd13"]
        after = df.loc[end:, "ref"].iloc[1:27]
        if len(after) >= 13 and fwd == fwd:
            dd26 = float((after / after.cummax() - 1.0).min()) * 100 if len(after) else np.nan
            label = "崩" if fwd * 100 < CRASH_TH else ("续" if fwd * 100 >= CONT_TH else "平")
        else:
            dd26, label = np.nan, "未完"
        episodes.append({
            "ep": len(episodes), "start": str(seg.index[0].date()), "end": str(end.date()),
            "weeks": int(len(seg)), "mean_b200": round(float(seg["b200"].mean()), 2),
            "fwd13_pct": round(fwd * 100, 2) if fwd == fwd else None,
            "dd26_pct": round(dd26, 2) if dd26 == dd26 else None,
            "label": label,
        })
    df["sig_date"] = bsig.reindex(df.index)
    return {"name": name, "df": df, "episodes": episodes}


def load_data() -> dict:
    # A 股 B200
    with open(A_BREADTH_SNAP) as f:
        rows = json.load(f)
    ab = pd.Series(
        {pd.Timestamp(r["date"]): r["ma200_pct"] for r in rows if r.get("ma200_pct") is not None},
    ).astype(float).sort_index()
    ab = ab[ab.index >= pd.Timestamp("2002-01-01")]

    # 美股 B200
    with open(US_BREADTH) as f:
        urows = json.load(f)
    ub = pd.Series(
        {pd.Timestamp(r["date"]): r["breadth_200"] for r in urows if r.get("breadth_200") is not None},
    ).astype(float).sort_index()

    # 等权全 A 指数（与宽度分母同源）
    panel = pd.read_parquet(A_PANEL).astype(np.float32)
    rets = panel.pct_change(fill_method=None)
    n = rets.notna().sum(axis=1)
    day = rets.mean(axis=1)
    eqw = (1.0 + day.where(n >= MIN_STOCKS)).cumprod()
    eqw = eqw[eqw.index >= pd.Timestamp(EQW_BUILD_START)]

    # GSPC / 创业板指
    gspc = pd.read_parquet(GSPC_PARQUET)["close"].astype(float)
    gspc.index = pd.to_datetime(gspc.index)
    cyb = pd.read_parquet(CYB_PARQUET)["close"].astype(float)
    cyb.index = pd.to_datetime(cyb.index)

    a = build_market(ab, eqw, "A")
    a["df"] = a["df"][a["df"].index >= pd.Timestamp(A_START)]
    a["df"], a["episodes"] = _relabel(a)  # 截窗后重算段（2005 起点截断的段重切）
    us = build_market(ub, gspc, "US")
    return {"A": a, "US": us, "eqw": eqw, "cyb": cyb, "ab_daily": ab}


def _relabel(m: dict) -> tuple[pd.DataFrame, list]:
    """截窗后重算高位段（复用 build_market 的段逻辑）。"""
    fresh = build_market(
        pd.Series(m["df"]["b200"], index=m["df"].index),
        pd.Series(m["df"]["ref"], index=m["df"].index), m["name"])
    df = m["df"].copy()
    df["ep"] = fresh["df"]["ep"]
    # 保留原 df 的全部列（fwd/ext 等不因截窗改变），只更新段标签
    return df, fresh["episodes"]


# ── P2 存在性 ────────────────────────────────────────────────────────────

CANDS = ["dwell13", "dwell26", "ext200", "slope13", "mean13"]


def p2_spread(df: pd.DataFrame, cand: str) -> dict:
    """单市场：高位长段周按候选中位数二分的前瞻收益差（pp）。"""
    s = df[df["high"] & df["ep"].notna() & df["fwd13"].notna()]
    if len(s) < 20:
        return {"n": len(s), "spread": np.nan}
    med = s[cand].median()
    above = s[s[cand] >= med]["fwd13"]
    below = s[s[cand] < med]["fwd13"]
    if len(below) == 0:
        above, below = s[s[cand] > med]["fwd13"], s[s[cand] <= med]["fwd13"]
    return {"n": int(len(s)), "spread": float((above.mean() - below.mean()) * 100),
            "above": {"n": int(len(above)), "mean_fwd13": round(float(above.mean()) * 100, 2)},
            "below": {"n": int(len(below)), "mean_fwd13": round(float(below.mean()) * 100, 2)},
            "median": round(float(med), 4)}


def p2_bootstrap(markets: dict, cand: str) -> tuple[float, float, float]:
    """按高位段聚类的 block bootstrap：池化 spread 的 90% CI（pp）。"""
    eps = []
    for m in markets.values():
        s = m["df"][m["df"]["high"] & m["df"]["ep"].notna() & m["df"]["fwd13"].notna()]
        med = s[cand].median()
        s = s.assign(_ab=np.where(s[cand] >= med, 1.0, 0.0))
        for _, seg in s.groupby("ep"):
            eps.append(seg[["fwd13", "_ab"]].values)
    pooled = np.concatenate(eps)
    pooled_spread = float((pooled[pooled[:, 1] == 1, 0].mean()
                           - pooled[pooled[:, 1] == 0, 0].mean()) * 100)
    rng = np.random.default_rng(BOOT_SEED)
    draws = np.empty(N_BOOT)
    for i in range(N_BOOT):
        pick = rng.integers(0, len(eps), len(eps))
        arr = np.concatenate([eps[j] for j in pick])
        draws[i] = (arr[arr[:, 1] == 1, 0].mean() - arr[arr[:, 1] == 0, 0].mean()) * 100
    lo, hi = np.percentile(draws, [5, 95])
    return pooled_spread, float(lo), float(hi)


# ── P3 关键事件 ───────────────────────────────────────────────────────────

def on_state(df: pd.DataFrame, cand: str, pct: float = P3_PCT) -> pd.Series:
    s = df[df["high"] & df["ep"].notna() & df["fwd13"].notna()]
    if len(s) == 0:
        return pd.Series(False, index=df.index)
    thr = np.percentile(s[cand], pct)
    return (df["high"] & (df[cand] >= thr)).fillna(False)


def p3_verdict(a_df: pd.DataFrame, cand: str) -> dict:
    on = on_state(a_df, cand)
    out = {"windows": {}, "correct": 0}
    for name, (lo, hi) in P3_WINDOWS.items():
        w = on[(on.index >= pd.Timestamp(lo)) & (on.index <= pd.Timestamp(hi))]
        frac = float(w.mean()) if len(w) else np.nan
        ok = frac >= P3_ON_FRAC_TH
        out["windows"][name] = {"on_frac": round(frac, 3), "expected": "ON", "ok": bool(ok)}
        out["correct"] += int(ok)
    w15 = on[(on.index >= pd.Timestamp(P3_2015_DANGER)) & (on.index <= pd.Timestamp(P3_2015_WIN[1]))]
    bad = bool(w15.any())
    out["windows"]["疯牛2015"] = {"on_weeks_in_danger": int(w15.sum()), "expected": "OFF",
                                 "ok": not bad}
    out["correct"] += int(not bad)
    out["verdict"] = "PASS" if out["correct"] >= 2 else "FAIL"

    # LOEO：剔除各窗口自身周后重算阈值，对错不得翻转
    loeo = {}
    for name, (lo, hi) in {**P3_WINDOWS, "疯牛2015": P3_2015_WIN}.items():
        excl = a_df[(a_df.index >= pd.Timestamp(lo)) & (a_df.index <= pd.Timestamp(hi))].index
        keep = a_df.drop(index=excl)
        on2 = on_state(keep, cand).reindex(a_df.index).fillna(False)
        if name in P3_WINDOWS:
            w = on2[(on2.index >= pd.Timestamp(lo)) & (on2.index <= pd.Timestamp(hi))]
            flip = (float(w.mean()) >= P3_ON_FRAC_TH) != out["windows"][name]["ok"]
        else:
            w = on2[(on2.index >= pd.Timestamp(P3_2015_DANGER)) & (on2.index <= pd.Timestamp(hi))]
            flip = (not bool(w.any())) != out["windows"][name]["ok"]
        loeo[name] = {"flipped": bool(flip)}
    out["loeo"] = loeo
    return out


# ── P4 三臂覆盖 ───────────────────────────────────────────────────────────

def tier_weight(b200: float) -> float:
    if b200 < MID:
        return 1.0
    if b200 < HIGH:
        return 0.5
    return 0.0


def run_arm(price: pd.Series, sig_dates: pd.Series, targets: pd.Series) -> pd.Series:
    """周信号 → 次一交易日收盘执行的资金曲线（10bp 单边按换手计）。"""
    price = price.sort_index()
    dates = price.index
    w = pd.Series(np.nan, index=dates)
    pos = dates.searchsorted(list(sig_dates.values))
    for p, tgt in zip(pos, targets.values):
        if p + 1 < len(dates):
            w.iloc[p + 1] = tgt
    w = w.ffill().fillna(0.0)
    ret = price.pct_change().fillna(0.0)
    turn = w.diff().abs()
    turn.iloc[0] = abs(w.iloc[0])
    sr = w.shift(1).fillna(0.0) * ret - COST * turn
    return (1.0 + sr).cumprod()


def metrics(eq: pd.Series, lo=None, hi=None) -> dict:
    if lo is not None:
        eq = eq[eq.index >= pd.Timestamp(lo)]
    if hi is not None:
        eq = eq[eq.index <= pd.Timestamp(hi)]
    eq = eq / eq.iloc[0]
    n = len(eq)
    if n < 20:
        return {"n": n}
    ann = float(eq.iloc[-1] ** (252.0 / n) - 1.0) * 100
    dd = float((eq / eq.cummax() - 1.0).min()) * 100
    return {"ann_pct": round(ann, 2), "maxdd_pct": round(dd, 2),
            "calmar": round(ann / abs(dd), 3) if dd < 0 else None}


def run_arm_daily(price: pd.Series, b200_daily: pd.Series) -> pd.Series:
    """日频信号诊断变体：当日 B200 定档 → 次日收盘执行（基线门不过时用）。"""
    price = price.sort_index()
    b = b200_daily.reindex(price.index).ffill()
    w = b.map(tier_weight).shift(1).fillna(0.0)
    ret = price.pct_change().fillna(0.0)
    turn = w.diff().abs()
    turn.iloc[0] = abs(w.iloc[0])
    sr = w.shift(1).fillna(0.0) * ret - COST * turn
    return (1.0 + sr).cumprod()


def p4(markets: dict, data: dict, cand: str | None) -> dict:
    a = markets["A"]["df"]
    tiers = a["b200"].map(tier_weight)
    sig = a["sig_date"].reindex(a.index)

    arms = {}
    for tname, price, start in [("创业板指", data["cyb"], "2010-06-01"),
                                ("等权全A", data["eqw"], A_START)]:
        pr = price[price.index >= pd.Timestamp(start)]
        pr = pr[pr.index <= a.index[-1]]
        common = a.index[a.index >= pd.Timestamp(start)]
        a_win = a.loc[common]
        sig_c, tiers_c = sig.reindex(common), tiers.reindex(common)
        t1 = run_arm(pr, sig_c, tiers_c)
        t3 = pr / pr.iloc[0]
        row = {"窗口": f"{start}→{a.index[-1].date()}", "冠军": metrics(t1),
               "买入持有": metrics(t3)}
        if cand is not None:
            on = on_state(a, cand)
            t2tgt = pd.Series([1.0 if on.get(d, False) else w for d, w in tiers_c.items()])
            t2 = run_arm(pr, sig_c, t2tgt)
            row["冠军+判别器"] = metrics(t2)
            tech = metrics(t2, *P4_TECH_WIN)
            tech1 = metrics(t1, *P4_TECH_WIN)
            tech3 = metrics(t3, *P4_TECH_WIN)
            row["科技牛窗"] = {"冠军+判别器": tech, "冠军": tech1, "买入持有": tech3}
            if tname == "创业板指":
                crash2 = metrics(t2, *P4_CRASH_WIN)
                row["股灾段2015"] = {"冠军+判别器": crash2}
        arms[tname] = row

    gate = None
    if "创业板指" in arms:
        ann1 = arms["创业板指"]["冠军"].get("ann_pct")
        gate = {"champion_ann": ann1, "handoff_ref": P4_GATE_REF,
                "diff": round(abs(ann1 - P4_GATE_REF), 2),
                "within_tol": bool(abs(ann1 - P4_GATE_REF) <= P4_GATE_TOL)}
        if not gate["within_tol"]:
            cyb = data["cyb"]
            cyb_win = cyb[cyb.index <= markets["A"]["df"].index[-1]]
            eq = run_arm_daily(cyb_win, data["ab_daily"])
            gate["daily_variant_ann"] = metrics(eq).get("ann_pct")
    return {"arms": arms, "gate": gate}


def p4_verdict(arms: dict) -> dict:
    cyb = arms.get("创业板指", {})
    need = ("冠军+判别器" in cyb and "科技牛窗" in cyb)
    if not need:
        return {"verdict": "SKIP(判别器未过 P3)"}
    tech2 = cyb["科技牛窗"]["冠军+判别器"].get("ann_pct")
    tech1 = cyb["科技牛窗"]["冠军"].get("ann_pct")
    tech3 = cyb["科技牛窗"]["买入持有"].get("ann_pct")
    improve = (tech2 - tech3) - (tech1 - tech3)
    cal2 = cyb["冠军+判别器"].get("calmar")
    cal1 = cyb["冠军"].get("calmar")
    dd2 = cyb.get("股灾段2015", {}).get("冠军+判别器", {}).get("maxdd_pct")
    c1 = improve >= P4_IMPROVE_TH
    c2 = cal2 is not None and cal1 is not None and cal2 >= cal1
    c3 = dd2 is not None and dd2 >= P4_CRASH_DD_TH
    return {"improve_pp": round(improve, 2), "c1_tech_improve": bool(c1),
            "c2_calmar": bool(c2), "c3_crash_dd": bool(c3), "dd2": dd2,
            "verdict": "PASS" if (c1 and c2 and c3) else "FAIL"}


# ── 主流程 ────────────────────────────────────────────────────────────────

def main() -> None:
    data = load_data()
    markets = {"A": data["A"], "US": data["US"]}

    p2 = {}
    for cand in CANDS:
        r = {}
        for mk, m in markets.items():
            r[mk] = p2_spread(m["df"], cand)
        pooled, lo, hi = p2_bootstrap(markets, cand)
        same_sign = all(np.sign(r[mk]["spread"]) == np.sign(pooled)
                        for mk in markets if not np.isnan(r[mk]["spread"]))
        big = abs(pooled) >= P2_MIN_SPREAD
        ci_ok = (lo > 0 and hi > 0) or (lo < 0 and hi < 0)
        r.update({"pooled_spread": round(pooled, 2), "ci90": [round(lo, 2), round(hi, 2)],
                  "same_sign": bool(same_sign), "ci_excl_0": bool(ci_ok),
                  "PASS": bool(big and same_sign and ci_ok)})
        p2[cand] = r

    passed = [c for c in CANDS if p2[c]["PASS"]]
    best = max(passed, key=lambda c: abs(p2[c]["pooled_spread"])) if passed else None

    p3 = p3_verdict(markets["A"]["df"], best) if best else {"verdict": "SKIP(P2 无 PASS)"}
    p4r = p4(markets, data, best if (best and p3["verdict"] == "PASS") else None)
    verdict = p4_verdict(p4r["arms"])

    out = {
        "meta": {"date": "2026-08-27", "protocol": "预注册见脚本 docstring",
                 "data_end_A": str(markets["A"]["df"].index[-1].date()),
                 "data_end_US": str(markets["US"]["df"].index[-1].date())},
        "p1_episodes": {mk: m["episodes"] for mk, m in markets.items()},
        "p2_existence": p2, "p2_passed": passed,
        "p3_key_events": p3,
        "p4_overlay": p4r, "p4_verdict": verdict,
    }
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / "siphon_detector_results.json"
    text = json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True, default=str)
    path.write_text(text)
    digest = hashlib.sha256(text.encode()).hexdigest()

    print("=" * 64)
    print("P1 高位段：A 股", len(markets["A"]["episodes"]), "段 / 美股",
          len(markets["US"]["episodes"]), "段")
    for mk, m in markets.items():
        labs = pd.Series([e["label"] for e in m["episodes"]]).value_counts().to_dict()
        print(f"  {mk}: {labs}")
    print("-" * 64)
    print("P2 存在性（spread=高位周二分后前瞻13周收益差,pp）")
    for cand in CANDS:
        r = p2[cand]
        print(f"  {cand:8s} A={r['A']['spread']:+.2f} US={r['US']['spread']:+.2f} "
              f"pooled={r['pooled_spread']:+.2f} CI={r['ci90']} PASS={r['PASS']}")
    print("-" * 64)
    if best:
        print("P3 候选 =", best, "→", p3["verdict"], "correct =", p3["correct"], "/3")
        for w, r in p3["windows"].items():
            print("  ", w, r)
    else:
        print("P3 SKIP（P2 无 PASS）")
    print("-" * 64)
    if p4r["gate"]:
        print("P4 基线门:", p4r["gate"])
    for tname, row in p4r["arms"].items():
        print(f"  [{tname}] {row['窗口']}")
        for arm in ("冠军", "冠军+判别器", "买入持有"):
            if arm in row:
                print(f"    {arm:10s}", row[arm])
    print("P4 判定:", verdict)
    print("=" * 64)
    print("sha256:", digest, "→", path)


if __name__ == "__main__":
    main()
