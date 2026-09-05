#!/usr/bin/env python3
"""散户过热阈值回测（research_proxy，发现性分析）。

问题：散户热度（档位净流入强度、小单−超大单分化）进入横截面最热区间时，
板块未来 5/10/20 日下跌概率是否显著高于其余板块？情境化（仅上升/派发阶段
触发）是否提升区分度？

数据（全部本地，~/.lei_signal_lab/cache）：
- sector_flow_history.json  东财五档资金流（单次上限 120 交易日，本地累积变长）
- sector_trend_history.json 板块等权指数日线（close/b50）
- sector_trend_snapshot.json 当日快照（total_mv_yi 作市值分母回溯锚点）

方法与诚实约定：
- 市值分母回溯：mv(t) = 当日总市值 × close(t)/close(最新)（股本不变近似，
  半年窗口内误差可接受，报告须声明）；
- 阶段为回算值（照抄 classify_stage 条件顺序向量化，抽样与原函数比对校验）；
- 过热 = 口径值当日横截面分位 ≥ --pctile（当日有效板块 < 200 则该日不计）；
- 显著性：按交易日聚合（触发组均值 − 非触发组均值的逐日差值序列），
  正态近似 t 检验 + 按日 bootstrap 95% CI——避免把数百个板块日当独立样本；
  另给「隔 --stride 日抽样」敏感性（缓解相邻日信号重叠导致的显著性高估）；
- 多重比较：口径 × 窗口 × 前向期组合较多，结论只认「方向一致 + 多组合
  显著」的口径，单点显著不采信。

输出：markdown 表（ stdout ），供实验报告引用。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lei_signal.market_context.retail_heat import METRIC_LABELS, point_ratios  # noqa: E402
from lei_signal.market_context import sector_trend as st  # noqa: E402

CACHE = Path(os.environ.get("LEI_CACHE_ROOT", Path.home() / ".lei_signal_lab/cache"))


# ─────────────────────────── 数据装载 ───────────────────────────
def load_panels() -> dict:
    flows = json.loads((CACHE / "sector_flow_history.json").read_text())
    rows = json.loads((CACHE / "sector_trend_history.json").read_text())
    snap = json.loads((CACHE / "sector_trend_snapshot.json").read_text())

    close = pd.DataFrame(
        {r["date"]: {c: v.get("close") for c, v in r["boards"].items()} for r in rows}
    ).T.sort_index()
    close.index = pd.to_datetime(close.index)
    b50 = pd.DataFrame(
        {r["date"]: {c: v.get("b50") for c, v in r["boards"].items()} for r in rows}
    ).T.sort_index()
    b50.index = pd.to_datetime(b50.index)

    # 交易日历对齐与缺口处理：sector_trend_history 有洞（预计算个别日未跑，
    # 实测 2026-08 下旬连缺数日），用 parquet 全市场交易日历补齐，指数/宽度
    # 按持平前向填充（缺日≈无更新，日收益 0 近似）；同时过滤资金流源里偶发
    # 的周末杂日（如 07-04/08-22）。
    cal = pd.read_parquet(CACHE / "a_share_klines.parquet", columns=["date"])
    days = pd.DatetimeIndex(sorted(set(pd.to_datetime(cal["date"]))))
    days = days[(days >= close.index[0]) & (days <= close.index[-1])]
    close = close.reindex(days).ffill()
    b50 = b50.reindex(days).ffill()

    snap_row = {x["code"]: x for x in snap["boards"]}
    return {
        "flows": flows,
        "close": close,
        "b50": b50,
        "mv_today": {c: x.get("total_mv_yi") for c, x in snap_row.items()},
        "hit_count": {c: x.get("hit_count") for c, x in snap_row.items()},
        "level": {c: x.get("level") for c, x in snap_row.items()},
    }


# ─────────────────────── 阶段回算（照抄 classify_stage） ───────────────────────
def backfill_stages(close: pd.DataFrame, b50: pd.DataFrame,
                    hit_counts: dict[str, int]) -> pd.DataFrame:
    """向量化回算历史阶段：条件顺序照抄 sector_trend.classify_stage
    （markup → distribution → accumulation → decline → None），
    slope 取一阶差分符号（features/indicators.py 的 ``{col}_slope = diff()``），
    bench 为板块等权基准（与快照同口径的合成近似）。"""
    ret = close.pct_change(fill_method=None)
    bench = (1.0 + ret.mean(axis=1).fillna(0.0)).cumprod()

    out = pd.DataFrame(index=close.index, columns=close.columns, dtype=object)
    for code in close.columns:
        if (hit_counts.get(code) or 0) < st._MIN_HIT_FOR_INDEX:
            continue  # 样本不足，整列 None（与快照口径一致）
        s = close[code]
        sma60 = s.rolling(60).mean()
        ema20 = s.ewm(span=20, adjust=False).mean()
        rs = s / bench
        rs_above = rs > rs.rolling(20).mean()

        s60_up = sma60.diff() > 0
        e20_up = ema20.diff() >= 0
        idx_high60 = s >= s.rolling(60).max()
        b = b50[code]
        bdiv = (idx_high60 & (b < b.rolling(60).mean())).fillna(False)

        above = s > sma60
        conds = [
            above & s60_up & rs_above.fillna(False),
            above & (~s60_up.fillna(True) | bdiv),
            rs_above.fillna(False) & e20_up.fillna(False),
            (~above).fillna(False) & (sma60.diff() < 0).fillna(False),
        ]
        labels = ["markup", "distribution", "accumulation", "decline"]
        stage = pd.Series(None, index=s.index, dtype=object)
        for cond, lab in zip(conds, labels):
            stage[cond.fillna(False) & stage.isna() & sma60.notna()] = lab
        out[code] = stage
    return out


def verify_stages(close: pd.DataFrame, b50: pd.DataFrame, stage_panel: pd.DataFrame,
                  hit_counts: dict[str, int], n: int = 20, seed: int = 7) -> bool:
    """随机抽 n 个 (板块, 日) 与 classify_stage 原函数输出比对。"""
    rng = np.random.default_rng(seed)
    codes = [c for c in close.columns if stage_panel[c].notna().any()]
    ok = bad = 0
    bench = (1.0 + close.pct_change(fill_method=None).mean(axis=1).fillna(0.0)).cumprod()
    for _ in range(n):
        code = codes[int(rng.integers(len(codes)))]
        ts = stage_panel[code].dropna()
        if ts.empty:
            continue
        t = ts.index[int(rng.integers(len(ts)))]
        s = close[code].loc[:t]
        sma60 = s.rolling(60).mean()
        rs = s / bench.loc[:t]
        ref, _ = st.classify_stage(
            idx_close=s, sma60_series=sma60,
            sma60_slope_sign=int(np.sign(sma60.diff().iloc[-1])),
            ema20_slope_sign=int(np.sign(s.ewm(span=20, adjust=False).mean().diff().iloc[-1])),
            rs_above_ma20=bool((rs.iloc[-1] > rs.rolling(20).mean().iloc[-1]))
            if rs.rolling(20).mean().iloc[-1] == rs.rolling(20).mean().iloc[-1] else None,
            breadth_divergence=st.breadth_divergence(s, b50[code].loc[:t]),
            hit_count=hit_counts.get(code) or 0,
        )
        if ref == stage_panel.at[t, code]:
            ok += 1
        else:
            bad += 1
            print(f"  mismatch {code} @{t.date()}: backfill={stage_panel.at[t, code]} ref={ref}")
    print(f"stage 回算抽样校验: {ok} 一致 / {bad} 不一致（n={ok + bad}）")
    return bad == 0


# ─────────────────────── 资金流口径面板 ───────────────────────
def build_metric_series(flows: dict, close: pd.DataFrame,
                        mv_today: dict[str, float | None]) -> dict[str, dict[str, pd.Series]]:
    """每板块逐日四口径 ratio 序列（date→ratio），市值分母按 close 回溯。"""
    last_close = close.iloc[-1]
    per_metric: dict[str, dict[str, pd.Series]] = {m: {} for m in METRIC_LABELS}
    for code, points in flows.items():
        if code not in close.columns:
            continue
        s = close[code]
        mv_base = mv_today.get(code)
        rec: dict[str, dict[str, float]] = {m: {} for m in METRIC_LABELS}
        for p in points:
            t = pd.to_datetime(p.get("date"))
            if t not in s.index or pd.isna(s.loc[t]) or pd.isna(last_close[code]):
                continue
            mv_t = None if mv_base is None else mv_base * float(s.loc[t]) / float(last_close[code])
            ratios = point_ratios(p, mv_t)
            if ratios:
                for m, v in ratios.items():
                    rec[m][t] = v
        for m in METRIC_LABELS:
            per_metric[m][code] = pd.Series(rec[m]).sort_index()
    return per_metric


# ─────────────────────── 统计（按日聚合） ───────────────────────
def _norm_p(t: float) -> float:
    """标准正态双侧 p 值（erf 近似，n>30 时 t 检验的合理近似）。"""
    from math import erf, sqrt
    return 2.0 * (1.0 - 0.5 * (1.0 + erf(abs(t) / sqrt(2.0))))


def daily_diff_stats(trigger: pd.DataFrame, fwd: pd.DataFrame, *,
                     min_trig: int = 5, min_base: int = 20,
                     bootstrap: int = 1000, stride: int = 5, seed: int = 42) -> dict | None:
    """逐日（触发组 − 非触发组）差值序列的统计。"""
    rng = np.random.default_rng(seed)
    d_down: list[float] = []
    d_ret: list[float] = []
    n_trig: list[int] = []
    for t in trigger.index.intersection(fwd.index):
        f = fwd.loc[t]
        m = trigger.loc[t].fillna(False) & f.notna()
        nb = (~trigger.loc[t].fillna(False)) & f.notna()
        if m.sum() < min_trig or nb.sum() < min_base:
            continue
        d_down.append(float((f[m] < 0).mean() - (f[nb] < 0).mean()))
        d_ret.append(float(f[m].mean() - f[nb].mean()))
        n_trig.append(int(m.sum()))
    if len(d_down) < (15 if min_trig >= 5 else 5):
        return None
    d_down = np.array(d_down)
    d_ret = np.array(d_ret)

    def _agg(a: np.ndarray) -> dict:
        t = a.mean() / (a.std(ddof=1) / np.sqrt(len(a)))
        bs = np.array([a[rng.integers(0, len(a), len(a))].mean() for _ in range(bootstrap)])
        return {
            "mean": float(a.mean()), "t": float(t), "p": _norm_p(t),
            "ci_lo": float(np.percentile(bs, 2.5)), "ci_hi": float(np.percentile(bs, 97.5)),
        }

    sub = np.arange(0, len(d_down), stride)  # 隔 stride 日抽样敏感性
    return {
        "n_days": len(d_down), "n_trig_med": float(np.median(n_trig)),
        "down": _agg(d_down), "ret": _agg(d_ret),
        "down_spaced": _agg(d_down[sub]), "ret_spaced": _agg(d_ret[sub]),
    }


def raw_rates(trigger: pd.DataFrame, fwd: pd.DataFrame) -> tuple[float, float]:
    """池化（非独立性假设下，仅作量级参考）：触发组/对照组的下跌概率。"""
    f = fwd[trigger.fillna(False)].stack()
    g = fwd[(~trigger.fillna(False)) & fwd.notna()].stack()
    return (float((f < 0).mean()) if len(f) else float("nan"),
            float((g < 0).mean()) if len(g) else float("nan"))


# ─────────────────────────── main ───────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pctile", type=float, default=0.90, help="过热横截面分位阈值")
    ap.add_argument("--windows", type=str, default="5,20")
    ap.add_argument("--horizons", type=str, default="5,10,20")
    ap.add_argument("--bootstrap", type=int, default=1000)
    ap.add_argument("--min-valid", type=int, default=200,
                    help="当日有效板块数低于该值不计横截面（回填不满时可临时调低自检管道）")
    ap.add_argument("--focus", type=str, default="",
                    help="重点板块专项统计（BK 代码逗号分隔，如 BK1215,BK1036）。"
                         "横截面分位仍用全板块口径，专项只额外输出该子集的触发统计")
    args = ap.parse_args()
    windows = [int(x) for x in args.windows.split(",")]
    horizons = [int(x) for x in args.horizons.split(",")]

    data = load_panels()
    close, b50 = data["close"], data["b50"]
    print(f"close 面板: {close.shape[0]} 日 × {close.shape[1]} 板块 "
          f"({close.index[0].date()} ~ {close.index[-1].date()})")

    stage = backfill_stages(close, b50, data["hit_count"])
    verify_stages(close, b50, stage, data["hit_count"])
    ctx_ok = stage.isin(["markup", "distribution"])
    print("阶段分布（回算，全面板）:", stage.stack().value_counts().to_dict())

    per_metric = build_metric_series(data["flows"], close, data["mv_today"])

    # 口径面板 + 横截面分位
    rank_panels: dict[tuple[str, int], pd.DataFrame] = {}
    for m in METRIC_LABELS:
        panel = pd.DataFrame(per_metric[m]).reindex(close.index).sort_index()
        for w in windows:
            rolled = panel.rolling(w, min_periods=w).mean()
            valid_day = rolled.notna().sum(axis=1) >= args.min_valid
            rolled = rolled.where(valid_day, other=np.nan)
            rank_panels[(m, w)] = rolled.rank(axis=1, pct=True)

    hot_base = {k: (v >= args.pctile) for k, v in rank_panels.items()}
    cold_base = {k: (v <= (1.0 - args.pctile)) for k, v in rank_panels.items()}

    results = []
    focus_codes = [c.strip() for c in args.focus.split(",") if c.strip()]
    focus_mask = None
    if focus_codes:
        cols = [c for c in focus_codes if c in close.columns]
        focus_mask = pd.DataFrame(False, index=close.index, columns=close.columns)
        focus_mask[cols] = True
        print(f"重点板块专项: {len(cols)}/{len(focus_codes)} 个在面板中: {cols}")
    for (m, w), hot in hot_base.items():
        for h in horizons:
            fwd = (close.shift(-h) / close - 1.0).iloc[:-h]
            fwd = fwd.where(fwd.notna() & (fwd != 0))
            triggers = [("hot", hot, 5, 20),
                        ("hot+ctx", hot & ctx_ok.reindex_like(hot).fillna(False), 5, 20),
                        ("cold", cold_base[(m, w)], 5, 20)]
            if focus_mask is not None:
                # 重点子集板块数少，放宽门槛为描述性参考（统计功效低，不作显著性结论）
                triggers.append(("hot·重点子集", hot & focus_mask, 1, 1))
            for name, trig, min_t, min_b in triggers:
                st_ = daily_diff_stats(trig, fwd, min_trig=min_t, min_base=min_b,
                                       bootstrap=args.bootstrap)
                if st_ is None:
                    continue
                p_trig, p_base = raw_rates(trig, fwd)
                results.append({
                    "metric": m, "window": w, "horizon": h, "trigger": name,
                    **st_, "p_down_trig": p_trig, "p_down_base": p_base,
                })

    res = pd.DataFrame(results)
    if res.empty:
        print("样本不足：无任何有效统计（资金流历史太短？）")
        return 1

    # ── 十分位单调性（描述性，定阈值位置的核心依据）──
    # 按当日横截面分位把全部板块日分十组（D10=最热），看未来收益/下跌概率
    # 是否随热度单调——单调才有"阈值"可言；若中间组收益最好、两端都差，
    # 说明热度与收益非线性，单阈值口径不成立。
    print("\n## 十分位单调性（未来 10 日，D10=最热；描述性，未扣多重比较）")
    for (m, w), rank in rank_panels.items():
        fwd = (close.shift(-10) / close - 1.0).iloc[:-10]
        fwd = fwd.where(fwd.notna() & (fwd != 0))
        dec = np.floor(rank * 10).clip(upper=9)
        cells = []
        for k in range(10):
            mask = (dec == k) & fwd.notna()
            n = int(mask.sum().sum())
            if n < 30:
                cells.append("-")
                continue
            vals = fwd[mask].stack()
            cells.append(f"{(vals < 0).mean() * 100:.0f}%/{vals.mean() * 100:+.2f}")
        print(f"  {m:12s} w={w:2d}  P跌/均收益 D1..D10: {' | '.join(cells)}")

    res["显著"] = res["down"].apply(
        lambda d: "*" if (d["p"] < 0.05 and d["ci_lo"] > 0 or d["p"] < 0.05 and d["ci_hi"] < 0) else "")
    res = res.sort_values(["metric", "window", "trigger", "horizon"])
    pd.set_option("display.width", 220)
    for name, g in res.groupby("trigger"):
        print(f"\n## 触发定义: {name}")
        print(g[["metric", "window", "horizon", "n_days", "n_trig_med",
                 "p_down_trig", "p_down_base"]].to_string(
            index=False, float_format=lambda x: f"{x:.4f}"))
        print(g.assign(
            down_mean=g["down"].apply(lambda d: f"{d['mean']:+.4f}"),
            down_ci=g["down"].apply(lambda d: f"[{d['ci_lo']:+.4f},{d['ci_hi']:+.4f}]"),
            down_p=g["down"].apply(lambda d: f"{d['p']:.3f}"),
            ret_mean=g["ret"].apply(lambda d: f"{d['mean']:+.4f}"),
            ret_p=g["ret"].apply(lambda d: f"{d['p']:.3f}"),
            spaced_ok=g.apply(
                lambda r: "±" if (r["down_spaced"]["p"] < 0.05) == (r["down"]["p"] < 0.05) else "✗", axis=1),
        )[["metric", "window", "horizon", "down_mean", "down_ci", "down_p",
           "ret_mean", "ret_p", "spaced_ok", "显著"]].to_string(index=False))

    print(f"\n口径说明: {METRIC_LABELS}")
    print("多重比较警示: 上述为发现性筛选，单点显著不足为凭；结论须方向一致+多组合稳健。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
