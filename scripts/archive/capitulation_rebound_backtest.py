#!/usr/bin/env python3
"""出清反弹信号·事件研究回测（research_proxy，2026-09-05）。

信号定义（预注册，右侧确认版——不做左侧抄底）：
- 条件1 出清：super_large 口径（超大单净流入/市值）20 日均值处于当日横截面
  最冷 P10（机构资金流出极端）；
- 条件2 右侧确认：close > MA20 且 MA20 斜率 ≥ 0（站回均线，道路修复的
  第一确认；策略语言对应「先判断道路」）；
- 触发 = 条件2 当天成立 且 条件1 在近 20 个交易日内曾成立；
  同板块 60 日内去重（首个触发日计事件）。

事件研究输出（回答"成功率/收益率/最佳持有期"）：
- 持有 5/10/20/40/60 日：上涨概率、平均/中位收益、跑赢全板块基准概率、超额
- MFE（最大有利偏移）到达日分布：信号后第几日见峰（回答"成功的时间范围"）
- 对照：同日全板块均值
- 情境分层：全市场融资余额 20 日变化率 正/负（散户杠杆扩张期 vs 收缩期，
  数据源东财 datacenter 两融余额，独立情绪源双确认）
- 稳健性：按事件日聚合的 t 检验 + 隔 5 日抽样

用法：PYTHONPATH=src python3 scripts/capitulation_rebound_backtest.py \
      [--flows-file ~/.lei_signal_lab/cache/tx_sector_flow_pilot.json]
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
sys.path.insert(0, str(Path(__file__).resolve().parent))

from retail_mania_backtest import load_panels, _norm_p  # noqa: E402
from lei_signal.fundamentals import sources  # noqa: E402

CACHE = Path(os.environ.get("LEI_CACHE_ROOT", Path.home() / ".lei_signal_lab/cache"))
HOLD_DAYS = (5, 10, 20, 40, 60)


def build_signal(data: dict, *, window: int = 20, cold_pct: float = 0.10,
                 version: str = "v1") -> tuple[pd.DataFrame, pd.DataFrame]:
    """返回 (触发面板 bool, super_large 口径面板)。

    v1（原定义）：出清=卖压最大——super_large 20日均值处于横截面 P10
    （近 20 日内曾成立）；右侧确认=站回 MA20 且斜率≥0。
    v2（2026-09-05 预注册修订，语义=卖压衰竭）：出清完成=近 60 日曾 P10
    且当前 rank > 0.25（离开极端区）；右侧确认=v1 基础上再加 近 20 日未创
    20 日新低 且 近 5 日收益 > 全板块等权基准。
    """
    close = data["close"]
    import retail_mania_backtest as rb
    series = rb.build_metric_series(data["flows"], close, data["mv_today"])
    panel = pd.DataFrame(series["super_large"]).reindex(close.index).sort_index()
    rolled = panel.rolling(window, min_periods=window).mean()
    valid_day = rolled.notna().sum(axis=1) >= 100
    rolled = rolled.where(valid_day, other=np.nan)
    rank = rolled.rank(axis=1, pct=True)
    cold = (rank <= cold_pct).fillna(False).astype(bool)

    ma20 = close.rolling(20, min_periods=20).mean()
    right = (close > ma20) & (ma20.diff() >= 0)

    if version == "v2":
        # 出清完成：曾极端 + 已离开极端区（卖压衰竭）
        was_cold_60 = cold.rolling(60, min_periods=1).max().astype(bool)
        left_extreme = (rank > 0.25).fillna(False).astype(bool)
        # 右侧确认追加：近 20 日最低价高于再前 20 日最低价（跌不动）；
        # 近 5 日收益跑赢全板块等权（开始转强）
        low_recent = close.rolling(20, min_periods=20).min()
        low_prior = low_recent.shift(20)
        no_new_low = (low_recent > low_prior).fillna(False).astype(bool)
        bench5 = close.pct_change(5, fill_method=None).mean(axis=1)
        beat_bench = (close.pct_change(5, fill_method=None).sub(bench5, axis=0) > 0)
        beat_bench = beat_bench.fillna(False).astype(bool)
        trigger = right.fillna(False).astype(bool) & was_cold_60 & left_extreme & no_new_low & beat_bench
    else:
        recent_cold = cold.rolling(20, min_periods=1).max().astype(bool)
        trigger = right.fillna(False).astype(bool) & recent_cold

    # 60 日去重
    trig = trigger.values.copy()
    for j in range(trig.shape[1]):
        last = -10**9
        for i in range(trig.shape[0]):
            if trig[i, j]:
                if i - last < 60:
                    trig[i, j] = False
                else:
                    last = i
    trigger = pd.DataFrame(trig, index=trigger.index, columns=trigger.columns)
    return trigger, panel


def margin_regime() -> pd.Series | None:
    """全市场融资余额 20 日变化率（>0=散户杠杆扩张期）。失败返回 None。"""
    try:
        hist = sources.fetch_margin_history(lookback_days=900)
    except Exception:
        return None
    s = pd.Series({pd.to_datetime(d): v.get("rzye_yi") for d, v in hist.items()
                   if v.get("rzye_yi") is not None}).sort_index()
    return s.pct_change(20)


def event_study(trigger: pd.DataFrame, close: pd.DataFrame, *, label: str,
                 regime: pd.Series | None = None) -> None:
    bench_ret = close.pct_change(fill_method=None).mean(axis=1)  # 全板块等权基准日收益
    events = trigger.stack()[lambda x: x].index.tolist()  # [(date, code)]
    if not events:
        print(f"[{label}] 无事件")
        return
    print(f"\n== [{label}] 事件数 {len(events)}，板块数 {len({c for _, c in events})} ==")
    rows = []
    for t, c in events:
        i, j = close.index.get_loc(t), close.columns.get_loc(c)
        row = {"date": t, "code": c}
        base = close.iat[i, j]
        for h in HOLD_DAYS:
            if i + h < len(close.index):
                b = close.iat[i + h, j]
                row[f"ret_{h}"] = b / base - 1.0 if pd.notna(base) and pd.notna(b) and base > 0 else None
                row[f"exc_{h}"] = (row[f"ret_{h}"] - ((1 + bench_ret.iloc[i + 1:i + h + 1]).prod() - 1)) if row[f"ret_{h}"] is not None else None
        # MFE 到达日（60 日窗口内最高收盘出现的第几日）
        if i + 60 < len(close.index):
            seg = close.iloc[i + 1:i + 61, j]
            base = close.iat[i, j]
            if pd.notna(base) and base > 0 and seg.notna().any():
                row["mfe_day"] = int(np.nanargmax(seg.values)) + 1
                row["mfe"] = float(np.nanmax(seg.values)) / base - 1.0
                row["mae"] = float(np.nanmin(seg.values)) / base - 1.0
        if regime is not None:
            k = regime.index.searchsorted(t)
            if 0 < k < len(regime.index):
                row["regime"] = "扩张" if regime.iloc[min(k, len(regime) - 1)] > 0 else "收缩"
        rows.append(row)
    df = pd.DataFrame(rows)

    def _stat(g: pd.DataFrame, name: str) -> None:
        cells = []
        for h in HOLD_DAYS:
            r, e = g[f"ret_{h}"].dropna(), g[f"exc_{h}"].dropna()
            if len(r) < 10:
                cells.append(f"{h}日:样本不足")
                continue
            cells.append(
                f"{h}日: 胜率{(r > 0).mean() * 100:.0f}% 均收{r.mean() * 100:+.2f}% "
                f"中位{r.median() * 100:+.2f}% 超额胜率{(e > 0).mean() * 100:.0f}% (n={len(r)})")
        print(f"  [{name}] " + " | ".join(cells))

    _stat(df, "全部")
    if "regime" in df.columns:
        for reg, g in df.groupby("regime"):
            _stat(g, f"融资{reg}期")
    if "mfe_day" in df.columns:
        md = df["mfe_day"].dropna()
        print(f"  MFE 峰值到达日: 中位 {md.median():.0f} 日, P25 {md.quantile(.25):.0f}, "
              f"P75 {md.quantile(.75):.0f}; 平均峰值收益 {df['mfe'].mean() * 100:+.2f}%, "
              f"平均最大回撤 {df['mae'].mean() * 100:+.2f}%")

    # 按事件日聚合的稳健性（20 日口径）
    if "ret_20" in df.columns:
        g = df.dropna(subset=["ret_20"]).groupby("date")["ret_20"].mean()
        if len(g) >= 15:
            t = g.mean() / (g.std(ddof=1) / np.sqrt(len(g)))
            print(f"  20日收益按日聚合: 均值 {g.mean() * 100:+.2f}%, t={t:.2f}, p={_norm_p(t):.3f}, n_days={len(g)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--flows-file", default=str(CACHE / "tx_sector_flow_pilot.json"))
    ap.add_argument("--window", type=int, default=20)
    ap.add_argument("--cold-pct", type=float, default=0.10)
    args = ap.parse_args()

    data = load_panels(args.flows_file)
    close = data["close"]
    print(f"面板: {close.shape[0]} 日 × {close.shape[1]} 板块")

    reg = margin_regime()
    print("融资余额环境: OK" if reg is not None else "融资余额环境: 不可用（跳过分层）")

    for ver in ("v1", "v2"):
        trigger, _ = build_signal(data, window=args.window, cold_pct=args.cold_pct, version=ver)
        event_study(trigger, close, label=f"出清反弹·{ver}", regime=reg)

    # 对照：仅右侧确认（无出清条件）——衡量出清条件的增量
    ma20 = close.rolling(20, min_periods=20).mean()
    right_only = ((close > ma20) & (ma20.diff() >= 0)).fillna(False).astype(bool)
    # 同样 60 日去重
    trig = right_only.values.copy()
    for j in range(trig.shape[1]):
        last = -10**9
        for i in range(trig.shape[0]):
            if trig[i, j]:
                if i - last < 60:
                    trig[i, j] = False
                else:
                    last = i
    right_only = pd.DataFrame(trig, index=close.index, columns=close.columns)
    event_study(right_only, close, label="对照·仅站回MA20（无出清条件）", regime=reg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
