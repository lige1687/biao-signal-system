"""数据充足性盘点（V2 回测体系第一步，规格 §15/§18 前置）。

扫描本地行情缓存 ``~/.lei_signal_lab/cache/*.bars.parquet``，输出：

1. 每个标的的总根数 / 年限 / 预热后有效样本（两档：日线最小 120 根 vs
   周线环境 120 个已完成周）；
2. 第一轮模块 A 门禁能筛出的候选事件数（趋势段数、20/60/120 各均线组
   首次回撤触碰数）；
3. 分年份候选分布，用于判断样本内外切分与回填深度。

口径（V2 第一轮门禁的原型，规格 §4.4/§4.5/§6/§9；非现行 v1 检测器）：

- s60 = ln(SMA60(t)/SMA60(t-60))/60*252（年化对数斜率），s20 同理 20 日窗；
  时钟一类 = s60 > 100% 或（s20 >= 2*s60 且 s60 > 40%）；二类 = 10% <= s60
  且非一类；三类 = |s60| < 10%（账本 clock_classifier 参数）。
- 日线多头排列 = SMA20>SMA60>SMA120 且 EMA20>EMA60>EMA120（规格 §4.5）。
- 周线环境 = 已完成周（该周最后一个交易日收盘后可用，规格 §3.2）的周线
  多头排列（周线同参数 20/60/120 镜像）。
- A2 触碰（V2 口径原型）= Low <= SMA_N + 1*ATR(20) 且 Close > close_lag_N
  （对应 SMA_N 仍在上行，规格 §4.2/§9 A2；ATR20 用 simple_average，与全局
  atr_method 一致，ATR 口径本身是待拍板项）。
- 趋势段 = 「时钟二类 + 日线多头排列 + 周线多头环境」连续为 true 的极大段；
  每段每均线组只计一次首次触碰（「第一次回撤要特别重视」，规格 §9 A2）。

本脚本是盘点工具，不是回测引擎：不做成交记账、不做 A3 结构/A4 入场/
A6 退出/盈亏比过滤，只数 A1+A2 层面的候选。候选数是模块 A 样本量的
上界，实际入场数只会更少。

来源可信度：provider 为 parquet_cache / local_upload 等非行情源的缓存
（cache.py::UNTRUSTED_PROVIDERS 语义）单列一节，不进汇总行。
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lei_signal.data.cache import DEFAULT_CACHE_DIR  # noqa: E402
from lei_signal.domain.rules_config import get_rule  # noqa: E402
from lei_signal.features.indicators import average_true_range, compute_features, seeded_ema  # noqa: E402

# 与 cache.py::UNTRUSTED_PROVIDERS 完全一致的整串精确匹配：
# 'parquet_cache+tencent_rt' 这类实时叠加层写回的组合名不在黑名单内，视为可信
# （cache.read 同一口径；本机后台服务会用组合名重写 meta，属正常行为）。
UNTRUSTED_PROVIDERS = frozenset(
    {"fixture", "synthetic", "upload", "parquet_cache", "unknown", "", "local_upload"}
)

MA_PERIODS = (20, 60, 120)


def provider_trusted(provider: str) -> bool:
    return provider.strip().lower() not in UNTRUSTED_PROVIDERS


@dataclass(slots=True)
class SymbolAudit:
    symbol: str
    provider: str
    trusted: bool
    bars: int
    first_date: str
    last_date: str
    years: float
    weeks: int
    eff_bars_daily: int          # 日线最小预热（120 根）后有效根数
    eff_bars_weekly_env: int     # 周线环境（120 个已完成周）后有效根数
    gate_days_daily: int         # 时钟二类 + 日线多头排列（不含周线门禁）天数
    gate_days_full: int          # 加上周线多头环境后的天数
    episodes: int                # 趋势段数（gate_full 连续极大段）
    first_touches: dict[str, int]  # 各均线组首次触碰数
    touch_days: dict[str, int]     # 各均线组全部触碰天数（参考）
    candidates_by_year: dict[int, int]


def _weekly_frame(daily: pd.DataFrame) -> pd.DataFrame:
    """按 ISO 年-周聚合周线，索引 = 该周最后一个实际交易日（规格 §3.2 可用日）。"""
    iso = daily.index.isocalendar()
    keys = pd.Series([f"{y}-{w:02d}" for y, w in zip(iso.year, iso.week)], index=daily.index)
    rows = []
    for _, seg in daily.groupby(keys):
        rows.append(
            {
                "week_end": seg.index[-1],
                "open": float(seg["open"].iloc[0]),
                "high": float(seg["high"].max()),
                "low": float(seg["low"].min()),
                "close": float(seg["close"].iloc[-1]),
            }
        )
    weekly = pd.DataFrame(rows).set_index("week_end").sort_index()
    close = weekly["close"]
    for period in MA_PERIODS:
        weekly[f"wsma{period}"] = close.rolling(period, min_periods=period).mean()
        weekly[f"wema{period}"] = seeded_ema(close, period)
    weekly["bull_align"] = (
        (weekly["wsma20"] > weekly["wsma60"])
        & (weekly["wsma60"] > weekly["wsma120"])
        & (weekly["wema20"] > weekly["wema60"])
        & (weekly["wema60"] > weekly["wema120"])
    )
    return weekly


def _clock_type(s60: float, s20: float, p: dict) -> int:
    """V2.1 标定的五类分类，返回 1..5（0 = 数据不足）。正负镜像，一类优先于二类。"""
    if np.isnan(s60):
        return 0
    t1_min = float(p["type1_min_s60"])
    t1_mult = float(p["type1_s20_multiple"])
    t1_floor = float(p["type1_s60_floor"])
    t3 = float(p["type3_max_abs_s60"])
    t2 = float(p["type2_min_s60"])
    if s60 > 0:
        if s60 > t1_min or (not np.isnan(s20) and s20 >= t1_mult * s60 and s60 > t1_floor):
            return 1
        if s60 >= t2:
            return 2
        return 3
    if s60 < 0:
        if s60 < -t1_min or (not np.isnan(s20) and s20 <= t1_mult * s60 and s60 < -t1_floor):
            return 5
        if s60 <= -t2:
            return 4
        return 3
    return 3


def audit_symbol(symbol: str, frame: pd.DataFrame, provider: str, clock_params: dict,
                 touch_atr: float) -> SymbolAudit:
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()
    feats = compute_features(frame)
    atr20 = average_true_range(feats, 20)

    sma60 = feats["sma60"]
    sma20 = feats["sma20"]
    w60 = int(clock_params["window"])
    w20 = int(clock_params["window_s20"])
    ann = float(clock_params["annualization"])
    s60 = (np.log(sma60 / sma60.shift(w60)) / w60 * ann).rename("s60")
    s20 = (np.log(sma20 / sma20.shift(w20)) / w20 * ann).rename("s20")

    clock = np.array([
        _clock_type(float(a), float(b), clock_params) for a, b in zip(s60, s20)
    ])
    clock2 = clock == 2

    daily_align = (
        (feats["sma20"] > feats["sma60"])
        & (feats["sma60"] > feats["sma120"])
        & (feats["ema20"] > feats["ema60"])
        & (feats["ema60"] > feats["ema120"])
    )
    gate_daily = pd.Series(clock2 & daily_align, index=feats.index).fillna(False)

    weekly = _weekly_frame(feats)
    # 周线环境：对每个交易日 d，用最后一个 week_end <= d 的已完成周状态。
    week_ends = weekly.index
    bull = weekly["bull_align"].to_numpy()
    pos = np.searchsorted(week_ends, feats.index, side="right") - 1
    weekly_bull = np.array([bull[i] if i >= 0 else False for i in pos])
    gate_full = gate_daily & weekly_bull

    warmup_daily = 120
    weeks_total = len(weekly)
    if weeks_total > 120:
        weekly_warmup_end = week_ends[119]
        eff_weekly = int((feats.index > weekly_warmup_end).sum())
    else:
        eff_weekly = 0
    eff_daily = int(len(feats) - warmup_daily)

    # 趋势段与首次触碰（V2 A2 口径原型：Low <= SMA_N + touch_atr*ATR20 且
    # close > close_lag_N；触碰日 gate_full 需成立）。
    touch = {}
    for n in MA_PERIODS:
        band = feats[f"sma{n}"] + touch_atr * atr20
        touch[n] = (
            (feats["low"] <= band)
            & (feats["close"] > feats[f"close_lag{n}"])
            & gate_full
        ).fillna(False)

    gate_values = gate_full.to_numpy()
    touch_values = {n: touch[n].to_numpy() for n in MA_PERIODS}
    episodes = 0
    first_touches = {n: 0 for n in MA_PERIODS}
    touch_days = {n: int(touch_values[n].sum()) for n in MA_PERIODS}
    candidates_by_year: dict[int, int] = {}
    in_episode = False
    consumed = {n: False for n in MA_PERIODS}
    years = feats.index.year.to_numpy()
    for i in range(len(feats)):
        if gate_values[i]:
            if not in_episode:
                episodes += 1
                in_episode = True
                consumed = {n: False for n in MA_PERIODS}
            for n in MA_PERIODS:
                if not consumed[n] and touch_values[n][i]:
                    first_touches[n] += 1
                    consumed[n] = True
                    candidates_by_year[int(years[i])] = (
                        candidates_by_year.get(int(years[i]), 0) + 1
                    )
        else:
            in_episode = False

    total_days = len(feats)
    return SymbolAudit(
        symbol=symbol,
        provider=provider,
        trusted=provider_trusted(provider),
        bars=total_days,
        first_date=str(feats.index[0].date()),
        last_date=str(feats.index[-1].date()),
        years=round((feats.index[-1] - feats.index[0]).days / 365.25, 1),
        weeks=weeks_total,
        eff_bars_daily=eff_daily,
        eff_bars_weekly_env=eff_weekly,
        gate_days_daily=int(gate_daily.sum()),
        gate_days_full=int(gate_full.sum()),
        episodes=episodes,
        first_touches={f"ma{n}": v for n, v in first_touches.items()},
        touch_days={f"ma{n}": v for n, v in touch_days.items()},
        candidates_by_year=dict(sorted(candidates_by_year.items())),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=str(Path.home() / ".lei_signal_lab" / "backtest_pool"),
        help="缓存根目录（默认回测深池）",
    )
    args = parser.parse_args()
    clock_spec = get_rule("clock_classifier")
    clock_params = {
        "window": clock_spec.param("window", 60),
        "window_s20": clock_spec.param("window_s20", 20),
        "annualization": clock_spec.param("annualization", 252),
        "type3_max_abs_s60": clock_spec.param("type3_max_abs_s60", 0.10),
        "type2_min_s60": clock_spec.param("type2_min_s60", 0.10),
        "type1_min_s60": clock_spec.param("type1_min_s60", 1.00),
        "type1_s20_multiple": clock_spec.param("type1_s20_multiple", 2.0),
        "type1_s60_floor": clock_spec.param("type1_s60_floor", 0.40),
    }
    pullback_spec = get_rule("first_ma_pullback")
    touch_atr = float(pullback_spec.param("ma_touch_distance_atr", 1.0))

    cache = Path(args.root)
    files = sorted(cache.glob("*.bars.parquet"))
    audits: list[SymbolAudit] = []
    skipped: list[tuple[str, str]] = []
    for path in files:
        symbol = path.name[: -len(".bars.parquet")]
        meta_path = path.with_suffix(".meta.json")
        provider = ""
        if meta_path.exists():
            try:
                provider = str(json.loads(meta_path.read_text()).get("provider", ""))
            except (OSError, json.JSONDecodeError):
                provider = ""
        try:
            frame = pd.read_parquet(path)
        except Exception:  # noqa: BLE001
            skipped.append((symbol, "parquet 读取失败"))
            continue
        if frame.empty or not {"open", "high", "low", "close"}.issubset(frame.columns):
            skipped.append((symbol, "列不完整"))
            continue
        audits.append(audit_symbol(symbol, frame, provider, clock_params, touch_atr))

    trusted = [a for a in audits if a.trusted]
    untrusted = [a for a in audits if not a.trusted]

    # ---------- 汇总 ----------
    print(f"缓存标的 {len(files)} 个，读取成功 {len(audits)}，跳过 {len(skipped)}")
    print(f"可信来源 {len(trusted)} 个 / 不可信来源 {len(untrusted)} 个"
          f"（parquet_cache / local_upload 等）\n")

    def dist(rows: list[SymbolAudit]) -> str:
        if not rows:
            return "-"
        bars = sorted(a.bars for a in rows)
        cands = [sum(a.first_touches.values()) for a in rows]
        return (f"n={len(rows)}，根数中位 {int(np.median(bars))}（{bars[0]}~{bars[-1]}），"
                f"候选中位 {np.median(cands):.0f}，候选合计 {sum(cands)}")

    print(f"[可信来源] {dist(trusted)}")
    print(f"[不可信]   {dist(untrusted)}\n")

    bins = [(500, 576), (1000, 1000), (1500, 1500), (2500, 2500)]
    for label, _ in bins:
        pass
    thresholds = [576, 1000, 1500, 2500]
    labels = ["≥576根(周线环境可跑)", "≥1000根(约4年)", "≥1500根(约6年)", "≥2500根(约10年)"]
    for label, threshold in zip(labels, thresholds):
        n = sum(1 for a in trusted if a.bars >= threshold)
        c = sum(sum(a.first_touches.values()) for a in trusted if a.bars >= threshold)
        print(f"可信来源中 {label}: {n}/{len(trusted)} 个标的，模块A候选 {c} 个")

    # ---------- 明细 ----------
    header = (f"{'symbol':<16}{'根数':>6}{'年限':>6}{'周数':>6}{'有效(日)':>8}"
              f"{'有效(周env)':>10}{'门禁日':>8}{'段数':>6}{'A20':>5}{'A60':>5}{'A120':>6}{'候选':>5}")
    for title, rows in (("可信来源", trusted), ("不可信来源（仅参考）", untrusted)):
        print(f"\n== {title} ==")
        print(header)
        for a in sorted(rows, key=lambda x: -x.bars):
            cand = sum(a.first_touches.values())
            print(f"{a.symbol:<16}{a.bars:>6}{a.years:>6}{a.weeks:>6}{a.eff_bars_daily:>8}"
                  f"{a.eff_bars_weekly_env:>10}{a.gate_days_full:>8}{a.episodes:>6}"
                  f"{a.first_touches['ma20']:>5}{a.first_touches['ma60']:>5}"
                  f"{a.first_touches['ma120']:>6}{cand:>5}")

    # ---------- 分年份 ----------
    year_total: dict[int, int] = {}
    for a in trusted:
        for year, count in a.candidates_by_year.items():
            year_total[year] = year_total.get(year, 0) + count
    print("\n== 可信来源模块 A 候选分年份（首次触碰口径）==")
    for year in sorted(year_total):
        print(f"{year}: {year_total[year]}")

    if skipped:
        print("\n跳过：", skipped)


if __name__ == "__main__":
    main()
