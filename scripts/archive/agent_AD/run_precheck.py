"""语义七前置验证（agent AD）——美股隔夜表现 × 次日A股宽度信号质量 关联性事件研究。

============================= 预注册（跑前写死，跑后不得改） =============================

研究问题
  A股与美股交易时间不重叠。检验：美股"隔夜"（A股下一交易日开盘前最近一个已收盘
  美股交易日）的当日涨跌，与次日 A 股开盘后的宽度信号质量之间是否存在统计关联。
  只做关联性检验，不设计任何接力机制、不产生任何买卖规则。

数据（见 prep_data.py；全部为已落盘机械数据）
  美股 X：^GSPC（标普500，主）与 ^IXIC（纳斯达克综合，对照），日收益
          r_us(u) = close(u)/close(u-1) - 1（yfinance 现有 provider）。
  A股宽度 B50(t)：全A 收盘价站上 50 日均线的股票占比（%，预计算缓存，券商金工口径）。
  A股指数：沪深300（000300.SS，腾讯前复权缓存），用于前瞻收益与参考统计。

因变量（信号质量代理，两个）
  Q1 主代理：ΔB50(t) = B50(t) - B50(t_prev)，t 为 A 股交易日，t_prev 为其前一 A 股
     交易日。即"次日 A 股全市场宽度读数的逐日变化"——系统宽度信号（创业板三档、
     档位定调等）的直接原料。任务书示例二（宽度指标的变化）的实现。
  Q2 副代理：fwd10(t) = close_csi300(t+10)/close_csi300(t) - 1，t+10 为 t 之后第 10 个
     A 股交易日（沪深300 收盘计）。即"信号质量=此后 10 日的指数前瞻收益"——任务书
     示例一（信号其后 N 日收益）的连续式实现（事件式"上穿20"在 5 年样本内仅个位数次，
     无检验力，不做判定用，仅在报告中说明）。
  参考统计（不参与判定，仅校验联动方向常识）：A股次日指数日收益 ret_cn(t) 与
     次日开盘跳空 gap_cn(t)=open(t)/close(t_prev)-1。隔夜联动若存在，最先体现在这里。

时间对齐规则（节假日错位显式处理）
  对每个 A 股交易日 t（B50 与 B50(t_prev) 均存在）：
    U(t) = {美股交易日 u（自然日）：t_prev <= u <= t-1}
    （u 的收盘时刻为北京 u+1 日凌晨，恒早于 A 股 t 日 09:30 开盘；u >= t_prev 保证
     该收盘晚于 A 股 t_prev 日 15:00 收盘、即信息未被上一交易日消化。）
    |U(t)| == 1 → 保留，X(t) = r_us(唯一元素)。
    |U(t)| == 0 → 剔除，计「美股休市错位日」（美股假日/周末间隔）。
    |U(t)| >= 2 → 剔除，计「A股长假错位日」（A股休市期间美股多日交易，隔夜信息堆积，
                 不再是单一隔夜事件）。剔除数量分别写进报告。

分桶（桶边界预注册）
  大涨 up：r_us >= +1.0%；大跌 down：r_us <= -1.0%；平 flat：-1.0% < r_us < +1.0%。

检验方法（预注册）
  Q1：全期三桶均值；Welch 双样本 t 检验（up vs down / up vs flat / down vs flat），
      双边 α=0.05；另报 Kruskal-Wallis 三桶整体检验（非参数参考）。
  Q2：全期三桶均值照报；显著性一律用「非重叠抽样」：观察按 t 升序每 10 个取 1 个
      （消除 10 日重叠窗口的自相关），对子样本做 up vs down Welch 检验。
      全样本（重叠）显著性不作判定依据，防方差被自相关虚假压缩。
  参考统计 ret_cn / gap_cn：日度不重叠，直接 Welch。

滚动窗口稳定性（预注册）
  主窗口 2 个：W1 = 2021-06-16 ~ 2023-12-31；W2 = 2024-01-01 ~ 2026-09-02。
  年度窗 6 个：2021H2、2022、2023、2024、2025、2026YTD(至9-02)。
  每窗报 n、三桶均值、up-down 差与 Welch p。

判定线（预注册，三选一；主判定 = ^GSPC × Q1）
  条件 A（幅度且单调）：全期 mean(up)、mean(flat)、mean(down) 三者单调
        （up>flat>down 或 up<flat<down），且 |mean(up)-mean(down)| >= 0.5 个百分点。
        （0.5pp ≈ ΔB50 无条件日波动的三分之一；低于此幅度即使显著也无机械利用价值，
         此为跑前判断，非事后拟合。）
  条件 B（全期显著性）：全期 Welch up vs down，p < 0.05。
  条件 C（窗口稳定）：W1 与 W2 的 (mean_up - mean_down) 同号，且至少一个窗口
        Welch p < 0.05；同时年度窗中同号年 >= 4/6（不满足则 C 不成立但如实报数）。
  判「关联存在」：A 且 B 且 C 全部成立。
  判「关联不存在」：A 不成立（幅度不足 0.5pp 或不单调）。
  判「证据不足」：A 成立但 B 或 C 任一不成立；或有效观察数 < 800（数据缺口条款）；
        或任一输入序列缺失致主检验无法进行。
  ^IXIC 与 Q2、参考统计为佐证：不改变主判定，但方向相反且显著时必须在报告中如实呈现。

确定性纪律
  脚本只依赖排序数组与确定性统计函数，无 set/dict 迭代顺序依赖；
  双跑（PYTHONHASHSEED=0 / 42）输出文件 sha256 必须一致，哈希写入报告。

红线
  不设计接力机制、不产生买卖规则；不修改任何现有文件；数据缺口如实报，不编造。
=========================================================================================
"""
from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from bisect import bisect_left, bisect_right
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
RAW_DIR = REPO / "docs" / "experiments" / "raw" / "overnight-us-cn-2026-09-03"

# ── 预注册常量（跑前写死） ──────────────────────────────────────────────────
UP_EDGE = 1.0        # %，美股日收益分桶边界 ±1%
DOWN_EDGE = -1.0
MAG_LINE_PP = 0.5    # 条件A幅度线：|mean(up)-mean(down)| >= 0.5 个百分点
ALPHA = 0.05         # 显著性水平（双边）
FWD_N = 10           # Q2 前瞻 10 个 A 股交易日
OVERLAP_STRIDE = 10  # Q2 非重叠抽样步长
MIN_OBS = 800        # 有效观察下限（数据缺口条款）
WINDOWS = {          # 滚动主窗口
    "W1_2021H2-2023": ("2021-06-16", "2023-12-31"),
    "W2_2024-2026": ("2024-01-01", "2026-09-02"),
}
YEAR_WINDOWS = {     # 年度窗
    "2021H2": ("2021-06-16", "2021-12-31"),
    "2022": ("2022-01-01", "2022-12-31"),
    "2023": ("2023-01-01", "2023-12-31"),
    "2024": ("2024-01-01", "2024-12-31"),
    "2025": ("2025-01-01", "2025-12-31"),
    "2026YTD": ("2026-01-01", "2026-09-02"),
}


def load_inputs() -> dict[str, pd.DataFrame]:
    gspc = pd.read_parquet(RAW_DIR / "us_gspc_daily.parquet")
    ixic = pd.read_parquet(RAW_DIR / "us_ixic_daily.parquet")
    breadth = pd.read_parquet(RAW_DIR / "cn_breadth.parquet")
    csi = pd.read_parquet(RAW_DIR / "cn_csi300_daily.parquet")
    return {"gspc": gspc, "ixic": ixic, "breadth": breadth, "csi300": csi}


def align(
    us: pd.DataFrame, breadth: pd.DataFrame, csi: pd.DataFrame
) -> tuple[pd.DataFrame, dict]:
    """按预注册对齐规则构造观察表。

    返回 (obs, audit)。obs 索引 = A 股交易日 t，列：
      r_us（美股隔夜收益%）、us_date（对应美股交易日）、dB50（Q1）、
      fwd10（Q2，含 NaN 尾部）、ret_cn、gap_cn（参考统计）。
    audit 含剔除计数。
    """
    us_close = us["close"].sort_index()
    us_ret = us_close.pct_change() * 100.0
    us_days = [d.date() for d in us_close.index]  # 已排序

    b = breadth["ma50_pct"].astype(float).sort_index()
    db50 = b.diff()  # ΔB50（相邻宽度记录日）

    csi = csi.sort_index()
    csi_close = csi["close"].astype(float)
    csi_open = csi["open"].astype(float)
    csi_ret = csi_close.pct_change() * 100.0
    csi_gap = (csi_open / csi_close.shift(1) - 1.0) * 100.0
    csi_pos = {d.date(): i for i, d in enumerate(csi.index)}

    obs_rows: list[dict] = []
    n_zero = 0   # |U|=0 美股休市错位
    n_multi = 0  # |U|>=2 A股长假错位
    n_nous_ret = 0  # 美股收益缺失（序列首日）
    idx = b.index
    for i in range(1, len(idx)):
        t_prev = idx[i - 1].date()
        t = idx[i].date()
        t_minus_1 = t - timedelta(days=1)
        lo = bisect_left(us_days, t_prev)
        hi = bisect_right(us_days, t_minus_1)
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
            n_nous_ret += 1
            continue
        # Q2 前瞻收益与参考统计：t 必须在沪深300日历内
        if t not in csi_pos:
            continue
        j = csi_pos[t]
        fwd10 = (
            csi_close.iloc[j + FWD_N] / csi_close.iloc[j] - 1.0
        ) * 100.0 if j + FWD_N < len(csi_close) else float("nan")
        ret_cn = csi_ret.iloc[j]
        gap_cn = csi_gap.iloc[j]
        obs_rows.append(
            {
                "t": t,
                "us_date": us_day,
                "r_us": float(r_us),
                "dB50": float(db50.iloc[i]),
                "fwd10": float(fwd10) if not pd.isna(fwd10) else float("nan"),
                "ret_cn": float(ret_cn) if not pd.isna(ret_cn) else float("nan"),
                "gap_cn": float(gap_cn) if not pd.isna(gap_cn) else float("nan"),
            }
        )
    obs = pd.DataFrame(obs_rows).set_index("t")
    audit = {
        "us_market_holiday_skips": n_zero,
        "cn_long_holiday_skips": n_multi,
        "us_ret_missing_skips": n_nous_ret,
        "kept_observations": len(obs),
    }
    return obs, audit


def bucketize(r_us: float) -> str:
    if r_us >= UP_EDGE:
        return "up"
    if r_us <= DOWN_EDGE:
        return "down"
    return "flat"


def welch(a: np.ndarray, b: np.ndarray) -> dict:
    a = a[np.isfinite(a)]
    b = b[np.isfinite(b)]
    if len(a) < 2 or len(b) < 2:
        return {"n_a": len(a), "n_b": len(b), "t": float("nan"), "p": float("nan")}
    res = stats.ttest_ind(a, b, equal_var=False)
    return {
        "n_a": int(len(a)),
        "n_b": int(len(b)),
        "t": float(res.statistic),
        "p": float(res.pvalue),
    }


def bucket_stats(obs: pd.DataFrame, col: str) -> dict:
    """三桶均值 + 预注册检验。"""
    s = obs[["r_us", col]].dropna()
    buckets = {k: s.loc[s["r_us"].apply(bucketize) == k, col].to_numpy()
               for k in ("up", "flat", "down")}
    out: dict = {
        "n": {k: int(len(v)) for k, v in buckets.items()},
        "mean": {k: (float(np.mean(v)) if len(v) else None) for k, v in buckets.items()},
        "median": {k: (float(np.median(v)) if len(v) else None) for k, v in buckets.items()},
        "std": {k: (float(np.std(v, ddof=1)) if len(v) > 1 else None) for k, v in buckets.items()},
    }
    m = out["mean"]
    out["diff_up_down"] = (
        m["up"] - m["down"] if m["up"] is not None and m["down"] is not None else None
    )
    out["welch"] = {
        "up_vs_down": welch(buckets["up"], buckets["down"]),
        "up_vs_flat": welch(buckets["up"], buckets["flat"]),
        "down_vs_flat": welch(buckets["down"], buckets["flat"]),
    }
    if all(len(buckets[k]) > 0 for k in ("up", "flat", "down")):
        kw = stats.kruskal(buckets["up"], buckets["flat"], buckets["down"])
        out["kruskal_wallis_p"] = float(kw.pvalue)
    return out


def window_slice(obs: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    s = pd.Timestamp(start).date()
    e = pd.Timestamp(end).date()
    return obs.loc[(obs.index >= s) & (obs.index <= e)]


def q2_nonoverlap_test(obs: pd.DataFrame) -> dict:
    """Q2 预注册非重叠抽样 up vs down Welch。"""
    s = obs[["r_us", "fwd10"]].dropna().sort_index()
    sub = s.iloc[::OVERLAP_STRIDE]
    buckets = {k: sub.loc[sub["r_us"].apply(bucketize) == k, "fwd10"].to_numpy()
               for k in ("up", "flat", "down")}
    return {
        "n_sub": int(len(sub)),
        "mean": {k: (float(np.mean(v)) if len(v) else None) for k, v in buckets.items()},
        "welch_up_vs_down": welch(buckets["up"], buckets["down"]),
    }


def evaluate_verdict(gspc_q1_full: dict, gspc_q1_windows: dict, year_windows: dict,
                     n_obs: int) -> dict:
    """执行预注册判定线（三选一），返回条件明细与结论。"""
    m = gspc_q1_full["mean"]
    up, flat, down = m["up"], m["flat"], m["down"]
    diff = up - down
    monotone = (up > flat > down) or (up < flat < down)
    cond_a = monotone and abs(diff) >= MAG_LINE_PP
    cond_b = gspc_q1_full["welch"]["up_vs_down"]["p"] < ALPHA
    w1 = gspc_q1_windows["W1_2021H2-2023"]
    w2 = gspc_q1_windows["W2_2024-2026"]
    same_sign = (w1["diff_up_down"] is not None and w2["diff_up_down"] is not None
                 and np.sign(w1["diff_up_down"]) == np.sign(w2["diff_up_down"]))
    any_sig = min(w1["welch"]["up_vs_down"]["p"], w2["welch"]["up_vs_down"]["p"]) < ALPHA
    year_signs = [
        (np.sign(y["diff_up_down"]) == np.sign(diff))
        for y in year_windows.values() if y["diff_up_down"] is not None
    ]
    years_same_sign = int(sum(year_signs))
    years_total = len(year_signs)
    cond_c = same_sign and any_sig and (years_total == 0 or years_same_sign >= 4)
    enough_obs = n_obs >= MIN_OBS
    if not enough_obs:
        verdict = "证据不足（有效观察不足 800，数据缺口）"
    elif cond_a and cond_b and cond_c:
        verdict = "关联存在"
    elif not cond_a:
        verdict = "关联不存在"
    else:
        verdict = "证据不足"
    return {
        "verdict": verdict,
        "conditions": {
            "A_magnitude_and_monotone": bool(cond_a),
            "B_full_period_significance": bool(cond_b),
            "C_window_stability": bool(cond_c),
            "n_obs": n_obs,
        },
        "detail": {
            "full_diff_up_down_pp": diff,
            "monotone": monotone,
            "full_p_up_vs_down": gspc_q1_full["welch"]["up_vs_down"]["p"],
            "w1_diff": w1["diff_up_down"],
            "w2_diff": w2["diff_up_down"],
            "w1_p": w1["welch"]["up_vs_down"]["p"],
            "w2_p": w2["welch"]["up_vs_down"]["p"],
            "years_same_sign": f"{years_same_sign}/{years_total}",
        },
    }


def data_crosscheck(gspc: pd.DataFrame) -> dict:
    """与本地腾讯缓存 ^GSPC（2024-09 起 501 根）重叠段交叉校验日收益一致性。"""
    cache_path = Path("/Users/yongbiaoli/.lei_signal_lab/cache/^GSPC.bars.parquet")
    if not cache_path.exists():
        return {"skipped": "no cache file"}
    c = pd.read_parquet(cache_path)["close"].sort_index()
    g = gspc["close"].sort_index()
    joined = pd.concat([g, c], axis=1, keys=["yf", "tx"]).dropna()
    if len(joined) < 100:
        return {"skipped": f"overlap only {len(joined)}"}
    r_yf = joined["yf"].pct_change()
    r_tx = joined["tx"].pct_change()
    mask = r_yf.notna() & r_tx.notna()
    corr = float(np.corrcoef(r_yf[mask], r_tx[mask])[0, 1])
    mad = float(np.mean(np.abs(r_yf[mask] - r_tx[mask])) * 100)
    return {
        "overlap_days": int(mask.sum()),
        "daily_return_corr": corr,
        "mean_abs_diff_pct_points": mad,
    }


def main() -> None:
    data = load_inputs()
    results: dict = {"preregistration": "见 scripts/agent_AD/run_precheck.py 模块 docstring（跑前写死）"}

    obs_g, audit_g = align(data["gspc"], data["breadth"], data["csi300"])
    obs_i, audit_i = align(data["ixic"], data["breadth"], data["csi300"])
    results["alignment_audit"] = {"gspc": audit_g, "ixic": audit_i}

    # 主判定：^GSPC × Q1
    q1_full_g = bucket_stats(obs_g, "dB50")
    q1_full_i = bucket_stats(obs_i, "dB50")
    q2_full_g = bucket_stats(obs_g, "fwd10")
    q2_full_i = bucket_stats(obs_i, "fwd10")
    q2_nono_g = q2_nonoverlap_test(obs_g)
    q2_nono_i = q2_nonoverlap_test(obs_i)
    ref_ret_g = bucket_stats(obs_g, "ret_cn")
    ref_gap_g = bucket_stats(obs_g, "gap_cn")

    q1_windows_g = {
        name: bucket_stats(window_slice(obs_g, s, e), "dB50")
        for name, (s, e) in WINDOWS.items()
    }
    q1_year_g = {
        name: bucket_stats(window_slice(obs_g, s, e), "dB50")
        for name, (s, e) in YEAR_WINDOWS.items()
    }

    verdict = evaluate_verdict(q1_full_g, q1_windows_g, q1_year_g, len(obs_g))

    results["bucket_edges_pct"] = {"up": UP_EDGE, "down": DOWN_EDGE}
    results["q1_gspc_full"] = q1_full_g
    results["q1_ixic_full"] = q1_full_i
    results["q2_fwd10_gspc_full"] = q2_full_g
    results["q2_fwd10_ixic_full"] = q2_full_i
    results["q2_fwd10_gspc_nonoverlap"] = q2_nono_g
    results["q2_fwd10_ixic_nonoverlap"] = q2_nono_i
    results["ref_csi300_nextday_return_gspc"] = ref_ret_g
    results["ref_csi300_nextday_open_gap_gspc"] = ref_gap_g
    results["q1_gspc_windows"] = q1_windows_g
    results["q1_gspc_year_windows"] = q1_year_g
    results["verdict"] = verdict
    results["data_crosscheck_gspc_vs_tencent_cache"] = data_crosscheck(data["gspc"])

    out_path = RAW_DIR / "results.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2, sort_keys=False,
                                   default=str))
    digest = hashlib.sha256(out_path.read_bytes()).hexdigest()

    # 摘要 stdout
    print("=" * 72)
    print("对齐审计:", json.dumps(results["alignment_audit"], ensure_ascii=False))
    print(f"有效观察: {len(obs_g)}  (判定下限 {MIN_OBS})")
    print(f"桶样本量(gspc): {q1_full_g['n']}")
    print(f"Q1 ΔB50 均值(gspc)  up={q1_full_g['mean']['up']:.4f}  "
          f"flat={q1_full_g['mean']['flat']:.4f}  down={q1_full_g['mean']['down']:.4f} pp")
    print(f"Q1 up-down 差={q1_full_g['diff_up_down']:.4f}pp  "
          f"Welch p={q1_full_g['welch']['up_vs_down']['p']:.4f}  "
          f"KW p={q1_full_g.get('kruskal_wallis_p', float('nan')):.4f}")
    for name, w in q1_windows_g.items():
        print(f"  {name}: diff={w['diff_up_down']:.4f}pp  "
              f"p={w['welch']['up_vs_down']['p']:.4f}  n={sum(w['n'].values())}")
    for name, w in q1_year_g.items():
        d = w['diff_up_down']
        print(f"  {name}: diff={'nan' if d is None else f'{d:.4f}'}pp  "
              f"n={sum(w['n'].values())}")
    print(f"Q2 fwd10 均值(gspc)  up={q2_full_g['mean']['up']:.3f}%  "
          f"flat={q2_full_g['mean']['flat']:.3f}%  down={q2_full_g['mean']['down']:.3f}%")
    print(f"Q2 非重叠 up-down p={q2_nono_g['welch_up_vs_down']['p']:.4f} "
          f"(n_sub={q2_nono_g['n_sub']})")
    print(f"参考 ret_cn 均值  up={ref_ret_g['mean']['up']:.3f}%  "
          f"flat={ref_ret_g['mean']['flat']:.3f}%  down={ref_ret_g['mean']['down']:.3f}%  "
          f"up-down p={ref_ret_g['welch']['up_vs_down']['p']:.5f}")
    print(f"参考 gap_cn 均值  up={ref_gap_g['mean']['up']:.3f}%  "
          f"flat={ref_gap_g['mean']['flat']:.3f}%  down={ref_gap_g['mean']['down']:.3f}%  "
          f"up-down p={ref_gap_g['welch']['up_vs_down']['p']:.5f}")
    print("交叉校验:", json.dumps(
        results["data_crosscheck_gspc_vs_tencent_cache"], ensure_ascii=False))
    print("判定:", verdict["verdict"])
    print(json.dumps(verdict["conditions"], ensure_ascii=False))
    print(json.dumps(verdict["detail"], ensure_ascii=False, default=str))
    print(f"results.json sha256 = {digest}")
    print("=" * 72)


if __name__ == "__main__":
    main()
