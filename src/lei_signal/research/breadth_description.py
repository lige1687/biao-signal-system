"""B200 宽度 × 510300 21 段目标的受限历史描述：配对/统计/重叠纯函数。

研究家族 ``breadth-unit-csi300-b200-21-v1``，用途 ``restricted_post_hoc_description``
（主控裁定的受限事后描述；不是预测、不是选股 IC、不是收益因子）。

边界（执行计划 §1/§2 冻结）：
- 本模块不读任何真实文件、不联网；输入由调用方加载为 DataFrame/字符串序列。
- 主指标是同一标的跨日期的时间序列 Spearman（并列平均名次），复用
  ``momentum_prototype.rank_diagnostic``，仅把宽度列重命名为其内部 momentum 列；
  输出不叫动量、不叫横截面 IC。
- 宽度实际输入为百分数（0–100），消费时转换为比例（/100），只转换一次。
- 观察轴由调用方先按交易日历推导完整传入；本函数在轴上左连接宽度与目标，
  缺失按日期保留原因，不前填、不顺延、不把 0 冒充缺失值。
- 过滤绝不依赖 B1 的 state/flag_*/in_comparison/primary_exclusion 等旧状态字段。
- 不足 3 对或任一列名次常数返回 null+原因；min_pairs=3 是数学核的输出约定，
  不是统计可信阈值。本轮不算 p 值/置信区间/重抽样，不证明不是巧合。
"""
from __future__ import annotations

import math
from datetime import date

import numpy as np
import pandas as pd

from .momentum_prototype import rank_diagnostic

# 互斥主排除原因，按优先级排序（先宽度后目标）。
EXCLUSION_PRIORITY = (
    "breadth_row_missing",     # 当日无宽度行
    "breadth_invalid",         # valid=false 或 coverage 不足 0.90
    "breadth_value_missing",   # 宽度行存在但 b200 缺失（NaN）
    "target_row_missing",      # 观察表无该日目标行
    "label_not_mature",        # x 日 15:00 晚于协议截止，标签未成熟
    "target_missing",          # 目标行存在但 main 缺失
)

BREADTH_PERCENT_MIN = 0.0
BREADTH_PERCENT_MAX = 100.0
COVERAGE_MIN = 0.9
RATIO_TOLERANCE = 1e-12
COVERAGE_TOLERANCE = 1e-12
DECISION_TIMEZONE = "Asia/Shanghai"
DECISION_HOUR = 15
TARGET_OFFSETS = (1, 22)  # e = t 后第 1 个交易日；x = t 后第 22 个交易日

_PAIR_COLUMNS = (
    "session", "session_pos", "e_date", "e_pos", "x_date", "x_pos", "label_mature",
    "pool_total", "eligible", "coverage", "b200_percent", "b200_fraction",
    "target", "target_recomputed", "included", "primary_exclusion", "exclusion_reasons",
)

_BREADTH_COLUMNS = ("date", "pool_total", "quoted", "eligible", "coverage", "valid", "b200")
_PRICES_COLUMNS = ("date", "close")
_OBS_COLUMNS = ("session", "e_date", "x_date", "main")


def _require_columns(df: pd.DataFrame, required, name: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{name} missing columns: {missing}")


def _iso_date(value, name: str) -> str:
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError(f"{name} invalid date {value!r}")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} invalid date {value!r}") from exc
    return value


def validate_sessions(sessions) -> list[str]:
    """交易日期序列：ISO 字符串、唯一、严格递增；不静默排序。"""
    out: list[str] = []
    prev: str | None = None
    for raw in sessions:
        day = _iso_date(raw, "session")
        if prev is not None:
            if day == prev:
                raise ValueError(f"duplicate session date {day!r}")
            if day < prev:
                raise ValueError(f"sessions not increasing at {day!r}")
        out.append(day)
        prev = day
    return out


def _check_unique_iso(series: pd.Series, name: str) -> list[str]:
    days = [_iso_date(v, name) for v in series]
    if len(set(days)) != len(days):
        raise ValueError(f"duplicate {name} date in input")
    return days


def _integer_series(series: pd.Series, name: str) -> np.ndarray:
    if pd.api.types.is_integer_dtype(series):
        return series.to_numpy(dtype=np.int64)
    if pd.api.types.is_float_dtype(series):
        arr = series.to_numpy(dtype=float)
        if not np.isfinite(arr).all() or not np.all(arr == np.floor(arr)):
            raise ValueError(f"{name} count must be integer-valued")
        return arr.astype(np.int64)
    raise ValueError(f"{name} count must be integer-typed, got {series.dtype}")


def validate_breadth_frame(breadth: pd.DataFrame) -> None:
    """宽度输入结构与数值硬校验；违反即 ValueError，不做静默修补。"""
    _require_columns(breadth, _BREADTH_COLUMNS, "breadth")
    _check_unique_iso(breadth["date"], "breadth")
    pool = _integer_series(breadth["pool_total"], "pool_total")
    quoted = _integer_series(breadth["quoted"], "quoted")
    eligible = _integer_series(breadth["eligible"], "eligible")
    if not ((eligible >= 0) & (eligible <= quoted) & (quoted <= pool)).all():
        raise ValueError("count constraint violated: need 0<=eligible<=quoted<=pool_total")
    if not pd.api.types.is_bool_dtype(breadth["valid"]):
        raise ValueError("breadth valid must be real boolean, not string")
    coverage = pd.to_numeric(breadth["coverage"], errors="raise").to_numpy(dtype=float)
    if not np.isfinite(coverage).all() or (coverage < 0).any() or (coverage > 1).any():
        raise ValueError("coverage must be finite within [0,1]")
    b200 = pd.to_numeric(breadth["b200"], errors="raise").to_numpy(dtype=float)
    is_valid = breadth["valid"].to_numpy(dtype=bool)
    for i in np.flatnonzero(is_valid):
        # 有效资格条件（pool_total>0、coverage≥0.90）不满足者按日期保留为
        # breadth_invalid 排除；整体拒绝保留给结构性矛盾（一致性/越界/类型）。
        if pool[i] <= 0:
            continue
        if abs(coverage[i] - eligible[i] / pool[i]) > COVERAGE_TOLERANCE:
            raise ValueError(
                f"coverage inconsistent with eligible/pool_total at {breadth['date'].iloc[i]!r}"
            )
        value = b200[i]
        if np.isnan(value):
            continue  # 合法行缺值按日期保留为 breadth_value_missing，不在此拒绝
        if not np.isfinite(value):
            raise ValueError(f"b200 non-finite at {breadth['date'].iloc[i]!r}")
        if not BREADTH_PERCENT_MIN <= value <= BREADTH_PERCENT_MAX:
            raise ValueError(f"b200 percent out of range [0,100] at {breadth['date'].iloc[i]!r}")


def validate_prices_frame(prices: pd.DataFrame) -> None:
    _require_columns(prices, _PRICES_COLUMNS, "prices")
    _check_unique_iso(prices["date"], "price")
    close = pd.to_numeric(prices["close"], errors="raise").to_numpy(dtype=float)
    if not np.isfinite(close).all() or (close <= 0).any():
        raise ValueError("price close must be finite and positive")


def validate_observations_frame(observations: pd.DataFrame) -> None:
    _require_columns(observations, _OBS_COLUMNS, "observations")
    _check_unique_iso(observations["session"], "observation session")
    _check_unique_iso(observations["e_date"], "entry date")
    _check_unique_iso(observations["x_date"], "exit date")
    try:
        pd.to_numeric(observations["main"], errors="raise")
    except (ValueError, TypeError) as exc:
        raise ValueError("observation main not numeric") from exc


def _x_decision_moment(x_date: str) -> pd.Timestamp:
    day = pd.Timestamp(x_date).normalize()
    return day.tz_localize(DECISION_TIMEZONE) + pd.Timedelta(hours=DECISION_HOUR)


def build_pairs(
    breadth: pd.DataFrame,
    observations: pd.DataFrame,
    prices: pd.DataFrame,
    sessions,
    *,
    evaluation_start: str,
    evaluation_end: str,
    cutoff,
) -> pd.DataFrame:
    """在完整观察轴上左连接宽度与目标，输出逐日配对明细。

    轴 = ``sessions`` 内 ``[evaluation_start, evaluation_end]`` 的全部交易日，先有轴
    再连接；宽度/目标缺失按日期保留并给原因，主排除原因按
    :data:`EXCLUSION_PRIORITY` 互斥取最先命中者。端点与日历推导不一致、目标与
    冻结价格比率差超过 1e-12 属一致性错误：整体拒绝（ValueError），不悄悄删行。
    """
    _iso_date(evaluation_start, "evaluation_start")
    _iso_date(evaluation_end, "evaluation_end")
    if evaluation_start > evaluation_end:
        raise ValueError("evaluation window inverted")
    sess = validate_sessions(sessions)
    validate_breadth_frame(breadth)
    validate_prices_frame(prices)
    validate_observations_frame(observations)
    cutoff_ts = pd.Timestamp(cutoff)

    pos = {d: i for i, d in enumerate(sess)}
    in_window = lambda d: evaluation_start <= d <= evaluation_end  # noqa: E731
    for day in breadth["date"]:
        day = _iso_date(day, "breadth")
        if in_window(day) and day not in pos:
            raise ValueError(f"breadth quote on non-trading day {day!r}")
    close_by_day: dict[str, float] = {}
    for row in prices.itertuples(index=False):
        day = _iso_date(row.date, "price")
        if day not in pos:
            raise ValueError(f"price quote on non-trading day {day!r}")
        close_by_day[day] = float(row.close)
    obs_by_day: dict[str, pd.Timestamp | float] = {}
    for row in observations.itertuples(index=False):
        day = _iso_date(row.session, "observation")
        if in_window(day) and day not in pos:
            raise ValueError(f"observation session on non-trading day {day!r}")
        obs_by_day[day] = row

    breadth_by_day: dict[str, pd.Timestamp | float] = {}
    for row in breadth.itertuples(index=False):
        breadth_by_day[_iso_date(row.date, "breadth")] = row

    records: list[dict] = []
    for t in [d for d in sess if in_window(d)]:
        i = pos[t]
        e_exists, x_exists = i + 1 < len(sess), i + TARGET_OFFSETS[1] < len(sess)
        e_date = sess[i + 1] if e_exists else ""
        x_date = sess[i + TARGET_OFFSETS[1]] if x_exists else ""
        mature = bool(x_exists and _x_decision_moment(x_date) <= cutoff_ts)

        reasons: list[str] = []
        b_row = breadth_by_day.get(t)
        pool_total = eligible = None
        coverage = b200_percent = b200_fraction = None
        if b_row is None:
            reasons.append("breadth_row_missing")
        else:
            pool_total = int(b_row.pool_total)
            eligible = int(b_row.eligible)
            coverage = float(b_row.coverage)
            raw = float(b_row.b200)
            if (not bool(b_row.valid) or pool_total <= 0
                    or coverage < COVERAGE_MIN - COVERAGE_TOLERANCE):
                reasons.append("breadth_invalid")
            if math.isnan(raw):
                reasons.append("breadth_value_missing")
            else:
                b200_percent = raw
                b200_fraction = raw / 100.0

        target = target_recomputed = None
        o_row = obs_by_day.get(t)
        if o_row is None:
            reasons.append("target_row_missing")
        else:
            if o_row.e_date != e_date or o_row.x_date != x_date:
                raise ValueError(
                    f"target endpoint mismatch at {t}: observations say "
                    f"({o_row.e_date!r}, {o_row.x_date!r}) but calendar derives "
                    f"({e_date!r}, {x_date!r})"
                )
            if mature:
                ce, cx = close_by_day.get(e_date), close_by_day.get(x_date)
                if ce is None or cx is None:
                    raise ValueError(f"price endpoint missing for target at {t}")
                ratio = cx / ce - 1.0
                target_recomputed = ratio
                main = float(o_row.main)
                if math.isnan(main):
                    reasons.append("target_missing")
                elif abs(main - ratio) > RATIO_TOLERANCE:
                    raise ValueError(
                        f"target ratio mismatch at {t}: observations main {main!r} vs "
                        f"frozen price ratio {ratio!r} (tolerance {RATIO_TOLERANCE})"
                    )
                else:
                    target = main
            else:
                reasons.append("label_not_mature")

        included = not reasons
        primary = ""
        if reasons:
            primary = min(reasons, key=lambda r: EXCLUSION_PRIORITY.index(r))
        records.append({
            "session": t, "session_pos": i,
            "e_date": e_date, "e_pos": pos[e_date] if e_date else None,
            "x_date": x_date, "x_pos": pos[x_date] if x_date else None,
            "label_mature": mature,
            "pool_total": pool_total, "eligible": eligible, "coverage": coverage,
            "b200_percent": b200_percent, "b200_fraction": b200_fraction,
            "target": target, "target_recomputed": target_recomputed,
            "included": included, "primary_exclusion": primary,
            "exclusion_reasons": "|".join(reasons),
        })
    frame = pd.DataFrame(records, columns=list(_PAIR_COLUMNS))
    frame["included"] = frame["included"].astype(bool)
    return frame


def rank_summary(clean: pd.DataFrame) -> dict:
    """时间序列 Spearman：复用数学核，只把宽度列改名为其内部 momentum 列。"""
    pair = pd.DataFrame({
        "momentum": pd.to_numeric(clean["b200_fraction"], errors="coerce"),
        "target": pd.to_numeric(clean["target"], errors="coerce"),
    })
    result = rank_diagnostic(pair)
    return {
        "n": result["n"], "time_series_spearman": result["value"],
        "reason": result["reason"], "axis": "dates",
        "use": "restricted_post_hoc_description",
    }


def _num(value):
    if value is None:
        return None
    value = float(value)
    return None if not np.isfinite(value) else value


def _describe(values: pd.Series) -> dict:
    vals = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
    if len(vals) == 0:
        return {"mean": None, "median": None, "min": None, "max": None}
    return {
        "mean": _num(np.mean(vals)), "median": _num(np.median(vals)),
        "min": _num(np.min(vals)), "max": _num(np.max(vals)),
    }


def _table(sub_all: pd.DataFrame, sub_clean: pd.DataFrame) -> dict:
    exclusions = {
        reason: int((sub_all["primary_exclusion"] == reason).sum())
        for reason in EXCLUSION_PRIORITY
    }
    up = pd.to_numeric(sub_clean["target"], errors="coerce").dropna()
    return {
        "n_all": int(len(sub_all)),
        "n_included": int(len(sub_clean)),
        "exclusions": exclusions,
        "breadth_percent": _describe(sub_clean["b200_percent"]),
        "breadth_fraction": _describe(sub_clean["b200_fraction"]),
        "target": _describe(sub_clean["target"]),
        "target_up_fraction": _num((up > 0).mean()) if len(up) else None,
        "rank": rank_summary(sub_clean),
    }


def summarize_pairs(pairs: pd.DataFrame, years) -> dict:
    """全期 + 逐年（按观察日所属年份，年度内重新排名）的固定统计表。

    年度列表全量保留（含空年）；n=0 也形成报告行。统计只帮助理解数据，
    不产生分档或策略收益；不取年度相关平均作第二主指标。
    """
    included = pairs["included"].astype(bool) if len(pairs) else pd.Series(dtype=bool)
    clean = pairs[included]
    full = _table(pairs, clean)
    by_year = {}
    for year in years:
        key = str(year)
        if len(pairs):
            mask = pairs["session"].str.slice(0, 4) == key
            sub_all, sub_clean = pairs[mask], clean[clean["session"].str.slice(0, 4) == key]
        else:
            sub_all = sub_clean = pairs
        by_year[key] = _table(sub_all, sub_clean)
    return {"full": full, "years": by_year}


def audit_overlap(pairs: pd.DataFrame, sessions) -> dict:
    """合法配对行的 (e,x] 相邻区间重叠对账。

    区间一律换算回原日历位置（close_i → close_{i+1} 记为一段），不把删除缺失
    后的行号当交易日。相邻两条合法观察最多共享 20 段（各 21 段），不估有效
    样本量。
    """
    sess = validate_sessions(sessions)
    pos = {d: i for i, d in enumerate(sess)}
    included = pairs["included"].astype(bool) if len(pairs) else pd.Series(dtype=bool)
    clean = pairs[included]
    seg_sets: list[set[int]] = []
    for row in clean.itertuples(index=False):
        start = pos[row.session] + TARGET_OFFSETS[0]
        end = pos[row.session] + TARGET_OFFSETS[1]
        seg_sets.append(set(range(start, end)))
    histogram: dict[int, int] = {}
    for prev, cur in zip(seg_sets, seg_sets[1:], strict=False):
        shared = len(prev & cur)
        histogram[shared] = histogram.get(shared, 0) + 1
    union: set[int] = set()
    for segs in seg_sets:
        union |= segs
    return {
        "included_pairs": int(len(seg_sets)),
        "segments_per_pair": TARGET_OFFSETS[1] - TARGET_OFFSETS[0],
        "total_interval_references": int(sum(len(s) for s in seg_sets)),
        "unique_intervals": int(len(union)),
        "consecutive_shared_histogram": {
            str(k): histogram[k] for k in sorted(histogram, reverse=True)
        },
        "note": (
            "相邻观察的21段区间互相重叠（相邻日观察共享20段），不得当作多次独立"
            "成功；区间按原日历位置计，不因缺失行压缩轴。"
        ),
    }
