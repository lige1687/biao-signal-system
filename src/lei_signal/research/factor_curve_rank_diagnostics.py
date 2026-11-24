"""Pure rank diagnostics against the immutable factor-curve formation pools.

The frozen target schedules, rather than future-return availability, authorize
membership. This module reads no files and never simulates an account.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Mapping, Sequence

from lei_signal.research.factor_curve_extension import (
    DERIVED,
    FACTORS,
    UNIVERSES,
    build_targets,
)
from lei_signal.research.fip import month_add
from lei_signal.research.momentum_increment_diagnostics import month_summary, rank_diagnostic


def _finite(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _axis(first: str, last: str) -> list[str]:
    if first > last:
        raise ValueError("inverted month range")
    months = [first]
    while months[-1] < last:
        months.append(month_add(months[-1], 1))
    if months[-1] != last:
        raise ValueError("invalid month range")
    return months


def _indexed(rows: Sequence[Mapping], label: str) -> dict[tuple[str, str], Mapping]:
    index = {}
    for row in rows:
        key = (row.get("month"), row.get("code"))
        if not all(isinstance(item, str) and item for item in key) or key in index:
            raise ValueError(f"invalid or duplicate {label} key: {key}")
        index[key] = row
    return index


def _scores(base: Mapping, prior: Mapping, extra: Mapping) -> dict[str, float]:
    sources = {
        "momentum": base.get("momentum"),
        "lowvol": -_finite(base.get("vol60")) if _finite(base.get("vol60")) is not None else None,
        "residual": prior.get("residual"),
        "scaled_momentum": prior.get("scaled_control"),
        **{name: extra.get(name) for name in DERIVED},
    }
    scores = {name: _finite(value) for name, value in sources.items()}
    if set(scores) != set(FACTORS) or any(value is None for value in scores.values()):
        raise ValueError("frozen pool has a missing formation score")
    return scores


def rank_records(
    old_input_rows: Sequence[Mapping],
    residual_features: Sequence[Mapping],
    derived_features: Sequence[Mapping],
    frozen_targets: Mapping,
    design: Mapping,
    source_manifest_sha256: str,
) -> list[dict]:
    """Return 80 display records after exact frozen-eligibility readback.

    Formation is 2016-01..2025-11; each outcome belongs to the next holding
    month and matures at its following month's first exchange-day open.
    """
    if len(source_manifest_sha256) != 64 or any(
        c not in "0123456789abcdef" for c in source_manifest_sha256
    ):
        raise ValueError("source manifest SHA-256 required")
    if list(design.get("formation", ())) != ["2016-01", "2025-11"]:
        raise ValueError("unexpected formation range")
    if design.get("minimum_names") != 30:
        raise ValueError("minimum formation pool must be 30")
    months = _axis(*design["formation"])
    if len(months) != 119 or frozen_targets.get("months") != months:
        raise ValueError("frozen formation month axis differs")
    periods = design.get("periods")
    expected_periods = {
        "all": ["2016-02", "2025-12"],
        "early": ["2016-02", "2018-12"],
        "middle": ["2019-01", "2021-12"],
        "late": ["2022-01", "2025-12"],
    }
    if periods != expected_periods:
        raise ValueError("unexpected holding-month periods")
    old = _indexed(old_input_rows, "old")
    prior = _indexed(residual_features, "residual")
    extra = _indexed(derived_features, "derived")
    monthly = frozen_targets.get("monthly")
    if not isinstance(monthly, list):
        raise ValueError("missing frozen monthly qualification")
    dates: dict[str, str] = {}
    for entry in monthly:
        month, day = entry.get("month"), entry.get("decision_date")
        if month not in months or not isinstance(day, str) or day[:7] != month:
            raise ValueError("invalid frozen formation date")
        if month in dates and dates[month] != day:
            raise ValueError("conflicting frozen formation date")
        dates[month] = day
    if set(dates) != set(months):
        raise ValueError("frozen formation calendar incomplete")
    label_dates: dict[str, tuple[str, str]] = {}
    for key, base in old.items():
        month = key[0]
        if month not in dates:
            continue
        day = dates[month]
        if base.get("decision_date") != day:
            raise ValueError(f"old decision date mismatch: {key}")
        if base.get("holding_month") != month_add(month, 1):
            raise ValueError(f"holding month mismatch: {key}")
        entry, exit_day = base.get("entry_date"), base.get("exit_date")
        if not isinstance(entry, str) or entry[:7] != month_add(month, 1):
            raise ValueError(f"entry month mismatch: {key}")
        if not isinstance(exit_day, str) or exit_day[:7] != month_add(month, 2):
            raise ValueError(f"exit month mismatch: {key}")
        pair = (entry, exit_day)
        if month in label_dates and label_dates[month] != pair:
            raise ValueError(f"future label date mismatch within month: {month}")
        label_dates[month] = pair
        for source, name in ((prior, "residual"), (extra, "derived")):
            row = source.get(key)
            if row is not None and row.get("decision_date") != day:
                raise ValueError(f"{name} decision date mismatch: {key}")
    if set(label_dates) != set(months) or label_dates[months[-1]][1][:7] != "2026-01":
        raise ValueError("last future label maturity is absent")
    for source, name in ((prior, "residual"), (extra, "derived")):
        for key, row in source.items():
            if key[0] in dates and row.get("decision_date") != dates[key[0]]:
                raise ValueError(f"{name} decision date mismatch: {key}")

    # The existing adapter reproduces every past-only qualification and group
    # boundary. Compare all schedules, including the common pool, before use.
    rebuilt = build_targets(
        old_input_rows,
        residual_features,
        derived_features,
        months,
        list(dates.values()),
        min_names=30,
    )
    for field in ("months", "factors", "monthly", "groups", "targets", "qualification"):
        if rebuilt[field] != frozen_targets.get(field):
            raise ValueError(f"frozen {field} mismatch")
    monthly_lookup = {(row["month"], row["universe"]): row for row in monthly}
    if len(monthly_lookup) != len(months) * len(UNIVERSES):
        raise ValueError("frozen monthly qualification keys incomplete or duplicate")
    target_schedules = frozen_targets["targets"]
    records = []
    for universe in UNIVERSES:
        for factor in FACTORS:
            for period_id, (first_holding, last_holding) in periods.items():
                holding_axis = _axis(first_holding, last_holding)
                formation_axis = [month_add(month, -1) for month in holding_axis]
                points = []
                by_month = {}
                known_total = eligible_total = 0
                sizes = []
                qualified_count = 0
                insufficient_count = 0
                for month in formation_axis:
                    day = dates[month]
                    target = target_schedules[f"{universe}__pool"][day]
                    formation_n = monthly_lookup[(month, universe)]["n"]
                    qualified = target["qualified"]
                    if qualified != monthly_lookup[(month, universe)]["qualified"]:
                        raise ValueError("frozen monthly pool qualification mismatch")
                    if qualified:
                        qualified_count += 1
                        codes = sorted(target["weights"])
                        if len(codes) < 30 or len(codes) != formation_n:
                            raise ValueError("qualified frozen pool size mismatch")
                        rows = []
                        for code in codes:
                            key = (month, code)
                            score = _scores(old[key], prior[key], extra[key])[factor]
                            rows.append({"score": score, "return": _finite(old[key].get("return"))})
                        diagnostic = rank_diagnostic(rows, "score")
                        value = diagnostic["spearman"]
                        known, eligible = diagnostic["known"], diagnostic["eligible"]
                        known_total += known
                        eligible_total += eligible
                        if value is not None:
                            sizes.append(known)
                    else:
                        insufficient_count += 1
                        value = None
                        known, eligible = 0, formation_n
                    points.append([day, value, known, eligible])
                    by_month[month] = value
                summary = month_summary(formation_axis, by_month)
                if summary["valid_count"] != len(sizes):
                    raise ArithmeticError("monthly valid-count mismatch")
                records.append(
                    {
                        "factorId": factor,
                        "poolId": universe,
                        "periodId": period_id,
                        "range": [formation_axis[0], formation_axis[-1]],
                        "evaluationRange": [first_holding, last_holding],
                        "horizon": "后续一个持有月",
                        "sourceManifestSha256": source_manifest_sha256,
                        "labelDefinition": (
                            "次月首交易日开盘至再下月首交易日开盘的调整后报价涨跌；"
                            "末期2025-12持有月标签在2026-01首交易日才成熟，缺失留空"
                        ),
                        "scoreDirection": (
                            "形成时分数越高排序越高；lowvol为负波动率，"
                            "downside已为负下行波动，距离为正且不预设优胜组"
                        ),
                        "nPeriods": len(sizes),
                        "minAssets": min(sizes) if sizes else 0,
                        "medianAssets": statistics.median(sizes) if sizes else 0,
                        "coverage": known_total / eligible_total if eligible_total else 0,
                        "mean": summary["mean"],
                        "uncertainty": {
                            "lower": (
                                max(-1.0, summary["ci_low"])
                                if summary["ci_low"] is not None
                                else None
                            ),
                            "upper": (
                                min(1.0, summary["ci_high"])
                                if summary["ci_high"] is not None
                                else None
                            ),
                            "method": (
                                "完整月轴Bartlett加权月度均值区间，滞后3月；"
                                "相关范围外截到正负1；有效月份不足2时区间留空"
                            ),
                        },
                        "rawUncertainty": {
                            "lower": summary["ci_low"],
                            "upper": summary["ci_high"],
                        },
                        "points": points,
                        "limitations": (
                            "仅固定300股既有形成时共同合格池的已看历史；每月先需至少30只形成时合格股票，"
                            f"本期间不足30只月份{insufficient_count}个、合格月份{qualified_count}个。"
                            "覆盖率为合格月份已知未来收益对数之和除以合格股票数之和；未知结果保留在分母。"
                            "相关值少于3个已知对或排名常数时留空，空月不压缩；"
                            "旧收益标签是报价涨跌，不能当成账户实得收益，末期标签晚于2025-12-31账户曲线终点。"
                        ),
                    }
                )
    if len(records) != 80:
        raise ArithmeticError("expected 80 factor-pool-period records")
    return records
