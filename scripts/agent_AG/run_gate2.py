"""语义七第二道门（agent AG）——控制 A 股开盘跳空后，美股隔夜表现是否还有增量信息。

============================= 预注册（跑前写死，跑后不得改） =============================

研究问题（唯一）
  在同一天 A 股开盘跳空幅度相同的日子里，美股隔夜表现还能区分出次日后续走势
  （开盘之后的日内宽度变化 / 日内指数收益）的差异吗？
  若不能——美股隔夜的全部信息都已打进 A 股开盘价，语义七终止；
  若能——存在开盘价之外的增量，接力机制才有信息基础（本任务只检验，不设计机制）。

数据（全部复用 AD 已落盘并交叉校验过的数据，不重抓不另起炉灶）
  docs/experiments/raw/overnight-us-cn-2026-09-03/ 四个 parquet：
  us_gspc_daily / us_ixic_daily / cn_breadth(ma50_pct) / cn_csi300_daily(open, close)。
  数据交叉校验结论引用 AD 报告（Yahoo vs 腾讯缓存日收益相关≈1），本任务不重做。

时间对齐（与 AD 完全相同的代码路径复制）
  U(t) = 落在 [A 股前一交易日, t−1] 自然日区间的美股交易日集合；
  |U|=1 保留；|U|=0（美股休市）剔除；|U|≥2（A 股长假）剔除。

变量
  控制变量（第一道门确立的主通道）：gap_cn(t) = 沪深300 open(t)/close(t_prev) − 1（%）。
  自变量：r_us = ^GSPC 前一美股交易日收益（%），主；^IXIC 为对照。
  因变量（开盘之后的部分，跳空无法解释的部分）：
    Y1 主：dB50(t)（次日全A 宽度逐日变化，pp，AD 的 Q1 同款——其本质由日内涨跌驱动）；
    Y2 副：intraday_cn(t) = 沪深300 close(t)/open(t) − 1（%），次日开盘后的日内收益，
          纯"开盘之后"量，跳空定义上完全不含。
  补充：ret_cn（全日收益）与 fwd10 照 AD 口径报参考，不参与判定。

分桶（边界跑前写死）
  跳空桶（主口径 ±0.3%）：gap_up: gap ≥ +0.3%；gap_flat: −0.3% < gap < +0.3%；
    gap_down: gap ≤ −0.3%。论证：跳空无条件分布约 N(−0.02%, 0.7%)（AD 参考
    统计三桶均值可推），±0.3% ≈ 0.4 倍标准差，既能把"明显跳空"与"无跳空"分开，
    又保证每桶有足够美股大涨/大跌交叉样本；±0.5%（≈0.7 倍标准差）做稳健性副口径。
  美股桶（沿用 AD）：up: r_us ≥ +1%；down: r_us ≤ −1%；flat: 其余。

检验一（主）：双重分桶
  在每个跳空桶 g 内、美股大涨组 vs 大跌组：Welch 双样本 t 检验（双边 α=0.05），
  报 n、两 组均值、差（pp 或 %）、p。

检验二（主）：回归替代口径（主口径 = 线性控制）
  OLS：Y = a + b_gap * gap_cn + b_us * r_us + e，HC1 稳健标准误（手写实现，
  cov = (X'X)^-1 (Σ e_i^2 x_i x_i') (X'X)^-1 * n/(n-k)）。判定看 b_us。
  对 Y1 与 Y2 分别跑；另跑加二次项 gap+gap^2 的稳健性版（非线性控制），仅参考。

滚动窗口稳定性：主窗口 W1 2021-06-16~2023-12-31、W2 2024-01-01~2026-09-02
  （与 AD 相同），各跑主回归，报 b_us 与稳健 p。

判定线（预注册三选一，主判定 = ^GSPC）
  「增量存在」须同时满足：
    (i) 主回归 b_us 显著（HC1 p < 0.05，Y1 与 Y2 同号且至少 Y2 显著——Y2 是定义上
         纯开盘之后的量，跳空不可能污染，作为主依据；Y1 作同向佐证）；
    (ii) 幅度：Y2 口径下，美股大涨 vs 大跌（跨跳空桶合并的残差法或直接组内合并）
         组间差 ≥ 0.15%（≈0.1 倍日内收益无条件标准差，量级论证：跳空主通道已占
         全日差 0.52%，留 0.15% 约三成，低于此没有机械价值）——实现为主回归
         b_us × 2%（up−down 区间宽 2 个百分点对应幅度）≥ 0.15%，即 |b_us| ≥ 0.075；
    (iii) W1、W2 两窗 b_us 同号，且至少一窗显著；
    (iv) 双重分桶：三个跳空桶中至少两个桶 up−down 差同号且其中至少一个 p < 0.05
         （副口径 ±0.5% 不参与判定，只作如实呈现）。
  「无增量」：主回归 b_us（Y2）不显著，且 (iv) 不满足（桶内差异既不齐也不显著）。
  「证据不足」：其余一切中间情形（如 Y2 显著但窗口反号、只有单一跳空桶显著等），
    以及交叉样本不足（任一跳空桶内美股大涨或大跌组 n < 15，导致桶内检验无法进行）。
  若增量只出现在个别跳空桶：判定仍按上述线走，但报告必须写明边界、禁止外推。

确定性纪律
  无 set/dict 迭代顺序依赖；PYTHONHASHSEED=0 与 =42 双跑 results.json sha256 一致。

红线
  不设计接力机制、不产生买卖规则；不修改任何现有文件；缺数据如实报。
=========================================================================================
"""
from __future__ import annotations

import hashlib
import json
from bisect import bisect_left, bisect_right
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
RAW_DIR = REPO / "docs" / "experiments" / "raw" / "overnight-us-cn-2026-09-03"
OUT_DIR = REPO / "docs" / "experiments" / "raw" / "overnight-gate2-2026-09-03"

# ── 预注册常量（跑前写死） ──────────────────────────────────────────────────
UP_EDGE = 1.0        # %，美股桶边界（沿用 AD）
DOWN_EDGE = -1.0
GAP_EDGE_MAIN = 0.3  # %，跳空桶边界主口径 ±0.3%
GAP_EDGE_ALT = 0.5   # %，稳健性副口径 ±0.5%
ALPHA = 0.05
FWD_N = 10
MIN_CELL_N = 15      # 交叉桶最低样本量（证据不足条款）
MIN_BETA_US = 0.075  # |b_us| 幅度线（b_us×2pp ≥ 0.15%）
WINDOWS = {
    "W1_2021H2-2023": ("2021-06-16", "2023-12-31"),
    "W2_2024-2026": ("2024-01-01", "2026-09-02"),
}


def load_inputs() -> dict[str, pd.DataFrame]:
    return {
        "gspc": pd.read_parquet(RAW_DIR / "us_gspc_daily.parquet"),
        "ixic": pd.read_parquet(RAW_DIR / "us_ixic_daily.parquet"),
        "breadth": pd.read_parquet(RAW_DIR / "cn_breadth.parquet"),
        "csi300": pd.read_parquet(RAW_DIR / "cn_csi300_daily.parquet"),
    }


def align(us: pd.DataFrame, breadth: pd.DataFrame, csi: pd.DataFrame):
    """与 AD 完全相同的对齐（复制），另加 intraday_cn。"""
    us_close = us["close"].sort_index()
    us_ret = us_close.pct_change() * 100.0
    us_days = [d.date() for d in us_close.index]

    b = breadth["ma50_pct"].astype(float).sort_index()
    db50 = b.diff()

    csi = csi.sort_index()
    csi_close = csi["close"].astype(float)
    csi_open = csi["open"].astype(float)
    csi_ret = csi_close.pct_change() * 100.0
    csi_gap = (csi_open / csi_close.shift(1) - 1.0) * 100.0
    csi_intraday = (csi_close / csi_open - 1.0) * 100.0
    csi_pos = {d.date(): i for i, d in enumerate(csi.index)}

    rows: list[dict] = []
    n_zero = n_multi = n_noret = 0
    idx = b.index
    for i in range(1, len(idx)):
        t_prev = idx[i - 1].date()
        t = idx[i].date()
        lo = bisect_left(us_days, t_prev)
        hi = bisect_right(us_days, t - timedelta(days=1))
        n_in = hi - lo
        if n_in == 0:
            n_zero += 1
            continue
        if n_in >= 2:
            n_multi += 1
            continue
        us_day = us_days[lo]
        r_us = us_ret.loc[pd.Timestamp(us_day)]
        if pd.isna(r_us):
            n_noret += 1
            continue
        if t not in csi_pos:
            continue
        j = csi_pos[t]
        fwd10 = (csi_close.iloc[j + FWD_N] / csi_close.iloc[j] - 1.0) * 100.0 \
            if j + FWD_N < len(csi_close) else float("nan")
        rows.append({
            "t": t, "us_date": us_day, "r_us": float(r_us),
            "dB50": float(db50.iloc[i]),
            "intraday_cn": float(csi_intraday.iloc[j]),
            "ret_cn": float(csi_ret.iloc[j]),
            "gap_cn": float(csi_gap.iloc[j]),
            "fwd10": float(fwd10) if not pd.isna(fwd10) else float("nan"),
        })
    obs = pd.DataFrame(rows).set_index("t")
    audit = {"us_holiday_skips": n_zero, "cn_long_holiday_skips": n_multi,
             "us_ret_missing": n_noret, "kept": len(obs)}
    return obs, audit


def us_bucket(r: float) -> str:
    return "up" if r >= UP_EDGE else ("down" if r <= DOWN_EDGE else "flat")


def gap_bucket(g: float, edge: float) -> str:
    return "gap_up" if g >= edge else ("gap_down" if g <= -edge else "gap_flat")


def welch(a: np.ndarray, b: np.ndarray) -> dict:
    a, b = a[np.isfinite(a)], b[np.isfinite(b)]
    if len(a) < 2 or len(b) < 2:
        return {"n_a": len(a), "n_b": len(b), "t": float("nan"), "p": float("nan")}
    res = stats.ttest_ind(a, b, equal_var=False)
    return {"n_a": int(len(a)), "n_b": int(len(b)),
            "t": float(res.statistic), "p": float(res.pvalue)}


def ols_hc1(y: np.ndarray, X: np.ndarray) -> dict:
    """OLS + HC1 稳健标准误。X 不含常数列（内部加）。返回系数、se、t、p。"""
    n, k = X.shape
    Xc = np.column_stack([np.ones(n), X])
    xtx_inv = np.linalg.inv(Xc.T @ Xc)
    beta = xtx_inv @ Xc.T @ y
    e = y - Xc @ beta
    meat = (Xc * (e ** 2)[:, None]).T @ Xc
    cov = xtx_inv @ meat @ xtx_inv * (n / (n - k - 1))
    se = np.sqrt(np.diag(cov))
    tvals = beta / se
    pvals = 2.0 * stats.t.sf(np.abs(tvals), df=n - k - 1)
    return {"beta": beta.tolist(), "se": se.tolist(),
            "t": tvals.tolist(), "p": pvals.tolist(), "n": int(n)}


def double_bucket(obs: pd.DataFrame, ycol: str, edge: float) -> dict:
    """跳空桶 × 美股桶：桶内美股 up vs down 的 Y 差异（Y 先对同跳空桶均值中心化
    不改变组内差，直接用原值即可）。"""
    s = obs[["r_us", "gap_cn", ycol]].dropna()
    out = {}
    for gb in ("gap_down", "gap_flat", "gap_up"):
        sub = s[s["gap_cn"].apply(lambda g: gap_bucket(g, edge)) == gb]
        up = sub.loc[sub["r_us"].apply(us_bucket) == "up", ycol].to_numpy()
        down = sub.loc[sub["r_us"].apply(us_bucket) == "down", ycol].to_numpy()
        flat = sub.loc[sub["r_us"].apply(us_bucket) == "flat", ycol].to_numpy()
        out[gb] = {
            "n_us_up": int(len(up)), "n_us_down": int(len(down)),
            "n_us_flat": int(len(flat)),
            "mean_up": float(np.mean(up)) if len(up) else None,
            "mean_down": float(np.mean(down)) if len(down) else None,
            "mean_flat": float(np.mean(flat)) if len(flat) else None,
            "diff_up_down": (float(np.mean(up) - np.mean(down))
                             if len(up) and len(down) else None),
            "welch_up_vs_down": welch(up, down),
        }
    return out


def regressions(obs: pd.DataFrame, ycol: str) -> dict:
    s = obs[["r_us", "gap_cn", ycol]].dropna()
    y = s[ycol].to_numpy()
    X_lin = s[["gap_cn", "r_us"]].to_numpy()
    lin = ols_hc1(y, X_lin)
    X_quad = np.column_stack([s["gap_cn"], s["gap_cn"] ** 2, s["r_us"]])
    quad = ols_hc1(y, X_quad)
    win = {}
    for name, (a, bnd) in WINDOWS.items():
        sub = s.loc[(s.index >= pd.Timestamp(a).date())
                    & (s.index <= pd.Timestamp(bnd).date())]
        win[name] = ols_hc1(sub[ycol].to_numpy(), sub[["gap_cn", "r_us"]].to_numpy())
    return {"linear": lin, "quad_control": quad, "windows": win}


def pooled_cell_check(obs: pd.DataFrame) -> dict:
    """交叉桶样本量审计（证据不足条款）。"""
    s = obs[["r_us", "gap_cn"]].dropna()
    counts = {}
    for gb in ("gap_down", "gap_flat", "gap_up"):
        sub = s[s["gap_cn"].apply(lambda g: gap_bucket(g, GAP_EDGE_MAIN)) == gb]
        counts[gb] = {
            "us_up": int((sub["r_us"] >= UP_EDGE).sum()),
            "us_down": int((sub["r_us"] <= DOWN_EDGE).sum()),
        }
    short = [f"{gb}:{k}" for gb, c in counts.items()
             for k, v in c.items() if v < MIN_CELL_N]
    return {"counts": counts, "cells_below_min": short}


def evaluate(obs: pd.DataFrame, results: dict) -> dict:
    y2 = results["regressions"]["Y2_intraday_cn"]["linear"]
    y1 = results["regressions"]["Y1_dB50"]["linear"]
    b_y2, p_y2 = y2["beta"][2], y2["p"][2]
    b_y1, p_y1 = y1["beta"][2], y1["p"][2]
    w = results["regressions"]["Y2_intraday_cn"]["windows"]
    b_w1, b_w2 = w["W1_2021H2-2023"]["beta"][2], w["W2_2024-2026"]["beta"][2]
    p_w1, p_w2 = w["W1_2021H2-2023"]["p"][2], w["W2_2024-2026"]["p"][2]
    db = results["double_bucket_main"]["Y2_intraday_cn"]
    diffs = [db[g]["diff_up_down"] for g in ("gap_down", "gap_flat", "gap_up")
             if db[g]["diff_up_down"] is not None]
    ps = [db[g]["welch_up_vs_down"]["p"] for g in ("gap_down", "gap_flat", "gap_up")
          if db[g]["welch_up_vs_down"]["p"] == db[g]["welch_up_vs_down"]["p"]]
    pos = sum(1 for d in diffs if d > 0)
    same_sign = len(diffs) == 3 and max(pos, len(diffs) - pos) >= 2
    n_sig = int(sum(1 for p in ps if p < ALPHA))
    cells_ok = not results["cell_check"]["cells_below_min"]

    cond_i = (np.sign(b_y2) == np.sign(b_y1)) and (p_y2 < ALPHA)
    cond_ii = abs(b_y2) >= MIN_BETA_US
    cond_iii = (np.sign(b_w1) == np.sign(b_w2)) and min(p_w1, p_w2) < ALPHA
    cond_iv = same_sign and n_sig >= 1

    if not cells_ok:
        verdict = "证据不足（交叉桶样本不足，桶内检验无法可靠进行）"
    elif cond_i and cond_ii and cond_iii and cond_iv:
        verdict = "增量存在"
    elif (p_y2 >= ALPHA) and (not cond_iv):
        verdict = "无增量"
    else:
        verdict = "证据不足"
    return {
        "verdict": verdict,
        "conditions": {
            "i_reg_sig_Y2_and_Y1_same_sign": bool(cond_i),
            "ii_magnitude_abs_b_us_ge_0.075": bool(cond_ii),
            "iii_windows_same_sign_one_sig": bool(cond_iii),
            "iv_double_bucket_2of3_same_sign_1_sig": bool(cond_iv),
            "cells_min_n_ok": bool(cells_ok),
        },
        "detail": {
            "b_us_Y2": b_y2, "p_us_Y2": p_y2,
            "b_us_Y1": b_y1, "p_us_Y1": p_y1,
            "b_us_W1": b_w1, "p_W1": p_w1,
            "b_us_W2": b_w2, "p_W2": p_w2,
            "bucket_diffs_up_down_Y2": diffs,
            "bucket_welch_p_Y2": ps,
            "n_sig_buckets": n_sig,
        },
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = load_inputs()
    obs_g, audit_g = align(data["gspc"], data["breadth"], data["csi300"])
    obs_i, audit_i = align(data["ixic"], data["breadth"], data["csi300"])

    results: dict = {
        "preregistration": "见 scripts/agent_AG/run_gate2.py 模块 docstring（跑前写死）",
        "alignment_audit": {"gspc": audit_g, "ixic": audit_i},
        "edges": {"us_up": UP_EDGE, "us_down": DOWN_EDGE,
                  "gap_main": GAP_EDGE_MAIN, "gap_alt": GAP_EDGE_ALT},
        "unconditional": {
            "gap_cn_std": float(obs_g["gap_cn"].std(ddof=1)),
            "gap_cn_mean": float(obs_g["gap_cn"].mean()),
            "intraday_cn_std": float(obs_g["intraday_cn"].std(ddof=1)),
            "dB50_std": float(obs_g["dB50"].std(ddof=1)),
        },
    }

    results["cell_check"] = pooled_cell_check(obs_g)
    results["double_bucket_main"] = {
        "Y1_dB50": double_bucket(obs_g, "dB50", GAP_EDGE_MAIN),
        "Y2_intraday_cn": double_bucket(obs_g, "intraday_cn", GAP_EDGE_MAIN),
    }
    results["double_bucket_alt"] = {
        "Y1_dB50": double_bucket(obs_g, "dB50", GAP_EDGE_ALT),
        "Y2_intraday_cn": double_bucket(obs_g, "intraday_cn", GAP_EDGE_ALT),
    }
    results["regressions"] = {
        "Y1_dB50": regressions(obs_g, "dB50"),
        "Y2_intraday_cn": regressions(obs_g, "intraday_cn"),
    }
    results["regressions_ixic_Y2"] = regressions(obs_i, "intraday_cn")
    results["double_bucket_main_ixic_Y2"] = double_bucket(obs_i, "intraday_cn",
                                                          GAP_EDGE_MAIN)

    # 参考统计（不参与判定）：回归 R^2、fwd10 控制跳空后
    s = obs_g[["r_us", "gap_cn", "fwd10"]].dropna()
    results["reference_fwd10_controlled"] = ols_hc1(
        s["fwd10"].to_numpy(), s[["gap_cn", "r_us"]].to_numpy())
    for ycol in ("dB50", "intraday_cn"):
        s2 = obs_g[["r_us", "gap_cn", ycol]].dropna()
        lin = results["regressions"][("Y1_dB50" if ycol == "dB50"
                                      else "Y2_intraday_cn")]["linear"]
        yhat = lin["beta"][0] + (np.array(lin["beta"][1:]) @
                                 s2[["gap_cn", "r_us"]].to_numpy().T)
        ss_res = float(((s2[ycol].to_numpy() - yhat) ** 2).sum())
        ss_tot = float(((s2[ycol] - s2[ycol].mean()) ** 2).sum())
        results.setdefault("r_squared", {})[ycol] = 1 - ss_res / ss_tot

    results["verdict"] = evaluate(obs_g, results)

    out_path = OUT_DIR / "results.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2,
                                   default=str))
    digest = hashlib.sha256(out_path.read_bytes()).hexdigest()

    v = results["verdict"]
    print("=" * 72)
    print("对齐审计:", json.dumps(results["alignment_audit"], ensure_ascii=False))
    print("无条件: gap_std={gap_cn_std:.3f}% intraday_std={intraday_cn_std:.3f}% "
          "dB50_std={dB50_std:.2f}pp".format(**results["unconditional"]))
    print("交叉桶样本(主口径):", json.dumps(results["cell_check"]["counts"]))
    print("主回归 Y2=intraday_cn: b_gap={:.4f}(p={:.3g}) b_us={:.4f}(p={:.3g}) n={}".format(
        results["regressions"]["Y2_intraday_cn"]["linear"]["beta"][1],
        results["regressions"]["Y2_intraday_cn"]["linear"]["p"][1],
        results["regressions"]["Y2_intraday_cn"]["linear"]["beta"][2],
        results["regressions"]["Y2_intraday_cn"]["linear"]["p"][2],
        results["regressions"]["Y2_intraday_cn"]["linear"]["n"]))
    for wn in WINDOWS:
        wr = results["regressions"]["Y2_intraday_cn"]["windows"][wn]
        print(f"  {wn}: b_us={wr['beta'][2]:.4f} p={wr['p'][2]:.3g} n={wr['n']}")
    print("主回归 Y1=dB50: b_us={:.4f}(p={:.3g})".format(
        results["regressions"]["Y1_dB50"]["linear"]["beta"][2],
        results["regressions"]["Y1_dB50"]["linear"]["p"][2]))
    for ycol in ("Y1_dB50", "Y2_intraday_cn"):
        print(f"双重分桶(主口径±{GAP_EDGE_MAIN}%) {ycol}:")
        for gb, d in results["double_bucket_main"][ycol].items():
            dd = d["diff_up_down"]
            dp = d["welch_up_vs_down"]["p"]
            print(f"  {gb}: n_up={d['n_us_up']} n_down={d['n_us_down']} "
                  f"up={'' if d['mean_up'] is None else format(d['mean_up'], '.3f')} "
                  f"down={'' if d['mean_down'] is None else format(d['mean_down'], '.3f')} "
                  f"diff={'NA' if dd is None else format(dd, '.3f')} "
                  f"p={'NA' if dp != dp else format(dp, '.3g')}")
    print("R^2:", json.dumps(results["r_squared"]))
    print("fwd10 控制后 b_us p={:.3g}".format(
        results["reference_fwd10_controlled"]["p"][2]))
    print("判定:", v["verdict"])
    print(json.dumps(v["conditions"], ensure_ascii=False))
    print(json.dumps(v["detail"], ensure_ascii=False, default=str))
    print(f"results.json sha256 = {digest}")
    print("=" * 72)


if __name__ == "__main__":
    main()
