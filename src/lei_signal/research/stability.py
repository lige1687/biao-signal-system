"""统计稳定性：整块 Bootstrap、匹配基准、删除大赢家、分组拆分。

统计约束（架构 8.4）：
  * 使用年度/季度**整块** Bootstrap，不随机打散相邻日期
    （相邻交易日高度相关，独立重采样会严重低估区间宽度）。
  * 报告样本数、均值、中位数、胜率与 95% 区间。
  * 删除最大 1/3/5 个事件，检查右尾依赖。
  * 与同标的相似市场阶段的普通日期比较，判断信号是否有增量信息。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_ITERATIONS = 2000
MIN_SAMPLES_FOR_CI = 8


def block_bootstrap_ci(
    outcomes: pd.DataFrame,
    *,
    column: str = "fwd_return_20",
    block: str = "quarter",
    iterations: int = DEFAULT_ITERATIONS,
    confidence: float = 0.95,
    seed: int = 20260801,
) -> tuple[float | None, float | None]:
    """整块 Bootstrap 的均值 95% 区间。

    以季度或年度为块整体重采样，保留块内相邻日期的相关结构。
    样本不足时返回 (None, None)，不伪造区间。
    """
    if outcomes.empty or column not in outcomes.columns:
        return (None, None)

    frame = outcomes.dropna(subset=[column]).copy()
    if len(frame) < MIN_SAMPLES_FOR_CI:
        return (None, None)

    dates = pd.to_datetime(frame["available_date"])
    if block == "year":
        frame["_block"] = dates.dt.year.astype(str)
    else:
        frame["_block"] = (
            dates.dt.year.astype(str) + "Q" + dates.dt.quarter.astype(str)
        )

    blocks = [group[column].to_numpy() for _, group in frame.groupby("_block")]
    if len(blocks) < 2:
        return (None, None)

    rng = np.random.default_rng(seed)
    means = np.empty(iterations, dtype=float)
    count = len(blocks)
    for index in range(iterations):
        picked = rng.integers(0, count, size=count)
        sample = np.concatenate([blocks[position] for position in picked])
        means[index] = sample.mean()

    alpha = (1.0 - confidence) / 2.0
    return (
        float(np.quantile(means, alpha)),
        float(np.quantile(means, 1.0 - alpha)),
    )


def drop_top_k_analysis(
    outcomes: pd.DataFrame,
    *,
    column: str = "fwd_return_20",
    ks: tuple[int, ...] = (0, 1, 3, 5),
) -> pd.DataFrame:
    """删除最大 K 个事件后的均值，检查是否依赖少数大赢家。"""
    if outcomes.empty or column not in outcomes.columns:
        return pd.DataFrame()
    values = outcomes[column].dropna().sort_values(ascending=False)
    rows: list[dict[str, object]] = []
    for k in ks:
        remaining = values.iloc[k:]
        rows.append(
            {
                "删除最大N个": k,
                "剩余样本": len(remaining),
                "均值%": round(float(remaining.mean()), 3) if not remaining.empty else None,
                "中位数%": round(float(remaining.median()), 3) if not remaining.empty else None,
                "胜率": (
                    round(float((remaining > 0).mean()), 3) if not remaining.empty else None
                ),
            }
        )
    result = pd.DataFrame(rows)
    if len(result) > 1 and result["均值%"].iloc[0] is not None:
        baseline = result["均值%"].iloc[0]
        result["相对基准变化"] = [
            None if value is None else round(value - baseline, 3)
            for value in result["均值%"]
        ]
    return result


def split_by_group(
    outcomes: pd.DataFrame,
    *,
    group: str = "year",
    column: str = "fwd_return_20",
) -> pd.DataFrame:
    """按年份 / 市场状态 / 资产类别拆分，检查稳定性。"""
    if outcomes.empty or group not in outcomes.columns:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for key, subset in outcomes.groupby(group):
        valid = subset[column].dropna()
        rows.append(
            {
                group: key,
                "样本数": len(subset),
                "有效样本": len(valid),
                "均值%": round(float(valid.mean()), 3) if not valid.empty else None,
                "中位数%": round(float(valid.median()), 3) if not valid.empty else None,
                "胜率": round(float((valid > 0).mean()), 3) if not valid.empty else None,
            }
        )
    return pd.DataFrame(rows).sort_values(group).reset_index(drop=True)


def baseline_comparison(
    outcomes: pd.DataFrame,
    frame: pd.DataFrame,
    signal_key: str,
    *,
    horizon: int = 20,
) -> pd.DataFrame:
    """与同标的、相似市场阶段的普通日期比较。

    回答：该信号后的 N 日收益，是否比这个标的平常的 N 日收益更好？
    还是只是搭上了长期上涨资产的自然漂移？
    """
    column = f"fwd_return_{horizon}"
    if outcomes.empty or column not in outcomes.columns:
        return pd.DataFrame()

    subset = outcomes[outcomes["signal_key"] == signal_key].dropna(subset=[column])
    if subset.empty:
        return pd.DataFrame()

    close = frame["close"].astype(float)
    all_forward = (close.shift(-horizon) / close - 1.0) * 100.0

    from lei_signal.research.outcomes import _market_state

    states = _market_state(frame)
    signal_dates = {pd.Timestamp(day) for day in subset["available_date"]}
    signal_states = set(subset["market_state"].unique())

    # 匹配基准：相同市场状态、且不是信号日的普通交易日
    mask = states.isin(signal_states) & ~states.index.isin(signal_dates)
    baseline_values = all_forward[mask].dropna()
    signal_values = subset[column]

    rows = [
        {
            "组别": f"信号日（{signal_key}）",
            "样本数": len(signal_values),
            "均值%": round(float(signal_values.mean()), 3),
            "中位数%": round(float(signal_values.median()), 3),
            "胜率": round(float((signal_values > 0).mean()), 3),
        },
        {
            "组别": "匹配基准（相同市场状态的普通日期）",
            "样本数": len(baseline_values),
            "均值%": round(float(baseline_values.mean()), 3) if not baseline_values.empty else None,
            "中位数%": (
                round(float(baseline_values.median()), 3) if not baseline_values.empty else None
            ),
            "胜率": (
                round(float((baseline_values > 0).mean()), 3)
                if not baseline_values.empty
                else None
            ),
        },
    ]
    if not baseline_values.empty:
        rows.append(
            {
                "组别": "差值（信号 − 基准）",
                "样本数": None,
                "均值%": round(float(signal_values.mean() - baseline_values.mean()), 3),
                "中位数%": round(
                    float(signal_values.median() - baseline_values.median()), 3
                ),
                "胜率": round(
                    float((signal_values > 0).mean() - (baseline_values > 0).mean()), 3
                ),
            }
        )
    return pd.DataFrame(rows)


def cluster_by_structure(outcomes: pd.DataFrame) -> pd.DataFrame:
    """按 structure_id 聚类：同一结构的多次阶段升级不应被当作独立样本。"""
    if outcomes.empty or "structure_id" not in outcomes.columns:
        return pd.DataFrame()
    linked = outcomes[outcomes["structure_id"].notna()]
    if linked.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for structure_id, group in linked.groupby("structure_id"):
        rows.append(
            {
                "structure_id": str(structure_id)[-12:],
                "关联信号数": len(group),
                "信号种类": ", ".join(sorted(group["signal_key"].unique())[:4]),
                "首个信号日": group["available_date"].min(),
                "20日均值%": round(float(group["fwd_return_20"].dropna().mean()), 3)
                if not group["fwd_return_20"].dropna().empty
                else None,
            }
        )
    return pd.DataFrame(rows).sort_values("关联信号数", ascending=False).reset_index(drop=True)


__all__ = [
    "DEFAULT_ITERATIONS",
    "MIN_SAMPLES_FOR_CI",
    "baseline_comparison",
    "block_bootstrap_ci",
    "cluster_by_structure",
    "drop_top_k_analysis",
    "split_by_group",
]
