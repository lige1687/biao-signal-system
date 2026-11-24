"""Read-only Alphalens rank diagnostics on a complete, explicit date/asset grid.

Only two unchanged upstream function AST nodes are executed. Real dates are mapped
to consecutive artificial days so upstream ``asfreq`` shifts by supplied calendar
rows; results are mapped back to the original dates. These are observations, not
natural-day periods or return/effectiveness measures.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path

import pandas as pd

_VENDOR = Path(__file__).parent / "vendor" / "alphalens_components"
_NAMES = ("quantile_turnover", "factor_rank_autocorrelation")
_PROVENANCE_SHA256 = "8b89ef6f0c2617f5b63cafb0c015499346c6bd3fb88a28fcd9ebe735a597a036"
_PERFORMANCE_SHA256 = "49cb32d4670314911fb1d205b73ffece0f3cfa49a6b4fea05dc215adac07f505"


def _upstream_functions():
    provenance_path = _VENDOR / "PROVENANCE.json"
    if hashlib.sha256(provenance_path.read_bytes()).hexdigest() != _PROVENANCE_SHA256:
        raise ValueError("vendor provenance SHA-256 mismatch")
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    if provenance["commit"] != "f0a07c22d554e4b4036983cc80320b432714fe7e":
        raise ValueError("unexpected upstream commit")
    for item in provenance["files"]:
        path = _VENDOR / Path(item["path"]).name
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != item["sha256"]:
            raise ValueError(f"vendor source SHA-256 mismatch: {path.name}")
    source = _VENDOR / "performance.py"
    if hashlib.sha256(source.read_bytes()).hexdigest() != _PERFORMANCE_SHA256:
        raise ValueError("unexpected upstream performance source")
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    nodes = [
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in _NAMES
    ]
    if {node.name for node in nodes} != set(_NAMES):
        raise ValueError("required upstream function missing")
    selected = ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[]))
    namespace = {"pd": pd}
    exec(compile(selected, str(source), "exec"), namespace)  # noqa: S102 - pinned local source
    return namespace, provenance


def _calendar(values):
    if not values:
        raise ValueError("calendar must not be empty")
    dates = pd.to_datetime(list(values), errors="raise")
    if dates.isna().any() or dates.has_duplicates or not dates.is_monotonic_increasing:
        raise ValueError("calendar must contain ordered unique dates")
    if any(date != date.normalize() for date in dates):
        raise ValueError("calendar entries must be dates without times")
    return pd.DatetimeIndex(dates)


def _number(value):
    return None if pd.isna(value) else float(value)


def _stats(values):
    valid = [x for x in values if x is not None]
    return {
        "calculable": len(valid),
        "uncalculable": len(values) - len(valid),
        "mean": float(pd.Series(valid).mean()) if valid else None,
        "median": float(pd.Series(valid).median()) if valid else None,
    }


def analyze_ranks(
    frame: pd.DataFrame,
    *,
    calendar,
    assets,
    group_size: int = 2,
    periods=(1, 5),
    date_column="date",
    asset_column="asset",
    factor_column="factor",
) -> dict:
    """Calculate descriptive persistence on the supplied complete score grid."""
    dates = _calendar(calendar)
    assets = tuple(assets)
    if (
        len(assets) != len(set(assets))
        or not assets
        or any(not isinstance(a, str) or not a for a in assets)
    ):
        raise ValueError("assets must be nonempty, unique names")
    if not isinstance(group_size, int) or group_size < 1 or len(assets) <= 2 * group_size:
        raise ValueError("group_size requires nonempty bottom, middle and top groups")
    periods = tuple(periods)
    if (
        not periods
        or len(periods) != len(set(periods))
        or any(not isinstance(p, int) or p < 1 for p in periods)
    ):
        raise ValueError("periods must be distinct positive integers")
    needed = [date_column, asset_column, factor_column]
    if len(set(needed)) != 3 or any(col not in frame.columns for col in needed):
        raise ValueError("three distinct date, asset and factor columns are required")
    data = frame.loc[:, needed].copy()
    data.columns = ["date", "asset", "factor"]
    data["date"] = pd.to_datetime(data["date"], errors="raise")
    data["factor"] = pd.to_numeric(data["factor"], errors="raise")
    if data["date"].isna().any() or data[["date", "asset"]].duplicated().any():
        raise ValueError("missing date or duplicate date/asset pair")
    if not data["date"].isin(dates).all() or not data["asset"].isin(assets).all():
        raise ValueError("date or asset outside explicit grid")
    if len(data) != len(dates) * len(assets):
        raise ValueError("missing date/asset row")
    if data["factor"].isin((float("inf"), float("-inf"))).any():
        raise ValueError("infinite factor score")
    grid = pd.MultiIndex.from_product([dates, assets], names=["date", "asset"])
    scores = data.set_index(["date", "asset"])["factor"].reindex(grid)
    if len(scores) != len(data):
        raise ValueError("incomplete score grid")

    artificial = pd.date_range("2000-01-01", periods=len(dates), freq="D")
    synthetic_index = pd.MultiIndex.from_product([artificial, assets], names=["date", "asset"])
    synthetic = pd.DataFrame({"factor": scores.to_numpy()}, index=synthetic_index)
    quantiles = pd.Series(0, index=synthetic_index, dtype="int64")
    date_status = []
    for ordinal, real_date in enumerate(dates):
        day = scores.loc[real_date]
        if day.isna().any():
            date_status.append(
                {"whole_day": "missing_score", "bottom": "missing_score", "top": "missing_score"}
            )
            continue
        ordered = day.sort_values(kind="stable")
        low_tie = ordered.iloc[group_size - 1] == ordered.iloc[group_size]
        high_tie = ordered.iloc[-group_size - 1] == ordered.iloc[-group_size]
        status = {
            "whole_day": None,
            "bottom": "bottom_boundary_tie" if low_tie else None,
            "top": "top_boundary_tie" if high_tie else None,
        }
        date_status.append(status)
        if not low_tie:
            quantiles.loc[(artificial[ordinal], ordered.index[:group_size])] = 1
        if not high_tie:
            quantiles.loc[(artificial[ordinal], ordered.index[-group_size:])] = 3
        if not low_tie and not high_tie:
            quantiles.loc[(artificial[ordinal], ordered.index[group_size:-group_size])] = 2

    upstream, provenance = _upstream_functions()
    outputs = {}
    for period in periods:
        rank = upstream["factor_rank_autocorrelation"](synthetic, period=period).reindex(artificial)
        turnover = {
            name: upstream["quantile_turnover"](quantiles, code, period=period).reindex(artificial)
            for name, code in (("bottom", 1), ("top", 3))
        }
        daily = []
        for i, real_date in enumerate(dates):
            earlier = i - period
            rank_reason = None
            group_reason = {"bottom": None, "top": None}
            if earlier < 0:
                rank_reason = "no_lag_date"
                group_reason = {"bottom": "no_lag_date", "top": "no_lag_date"}
            elif date_status[i]["whole_day"] or date_status[earlier]["whole_day"]:
                rank_reason = "missing_score"
                group_reason = {"bottom": "missing_score", "top": "missing_score"}
            else:
                for name in group_reason:
                    group_reason[name] = date_status[i][name] or date_status[earlier][name]
                if scores.loc[dates[i]].nunique() == 1 or scores.loc[dates[earlier]].nunique() == 1:
                    rank_reason = "constant_rank"
            rank_value = None if rank_reason else _number(rank.iloc[i])
            if rank_value is None and rank_reason is None:
                rank_reason = "uncalculable_rank"
            record = {
                "date": real_date.strftime("%Y-%m-%d"),
                "rank_correlation": rank_value,
                "rank_reason": rank_reason,
            }
            for name in ("bottom", "top"):
                value = None if group_reason[name] else _number(turnover[name].iloc[i])
                if value is None and group_reason[name] is None:
                    group_reason[name] = "upstream_empty_group"
                record[f"{name}_turnover"] = value
                record[f"{name}_reason"] = group_reason[name]
            daily.append(record)
        both = [
            row
            for row in daily
            if row["bottom_turnover"] is not None and row["top_turnover"] is not None
        ]
        outputs[str(period)] = {
            "daily": daily,
            "summary": {
                "rank_correlation": _stats([r["rank_correlation"] for r in daily]),
                "bottom_turnover": _stats([r["bottom_turnover"] for r in daily]),
                "top_turnover": _stats([r["top_turnover"] for r in daily]),
                "both_groups_calculable": len(both),
                "both_groups_unchanged_fraction": (
                    sum(r["bottom_turnover"] == 0 and r["top_turnover"] == 0 for r in both)
                    / len(both)
                )
                if both
                else None,
                "reasons": {
                    field: {
                        reason: sum(r[field] == reason for r in daily)
                        for reason in sorted({r[field] for r in daily if r[field]})
                    }
                    for field in ("rank_reason", "bottom_reason", "top_reason")
                },
            },
        }
    return {
        "calendar_step_mapping": (
            "real calendar row i maps to artificial consecutive day i; "
            "period counts supplied calendar rows"
        ),
        "calendar": [d.strftime("%Y-%m-%d") for d in dates],
        "assets": list(assets),
        "group_size": group_size,
        "source": {
            "repository": provenance["repository"],
            "commit": provenance["commit"],
            "performance_sha256": next(
                x["sha256"] for x in provenance["files"] if x["path"].endswith("performance.py")
            ),
            "functions": list(_NAMES),
        },
        "periods": outputs,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("input", "calendar", "assets", "output"):
        parser.add_argument(f"--{name}", required=True)
    parser.add_argument("--date-column", default="date")
    parser.add_argument("--asset-column", default="asset")
    parser.add_argument("--factor-column", default="factor")
    parser.add_argument("--group-size", type=int, default=2)
    parser.add_argument("--periods", default="1,5")
    args = parser.parse_args(argv)
    calendar = json.loads(Path(args.calendar).read_text(encoding="utf-8"))
    if not isinstance(calendar, list):
        parser.error("calendar JSON must be a date array")
    selected = [args.date_column, args.asset_column, args.factor_column]
    frame = pd.read_csv(args.input, usecols=selected)
    result = analyze_ranks(
        frame,
        calendar=calendar,
        assets=args.assets.split(","),
        group_size=args.group_size,
        periods=tuple(int(x) for x in args.periods.split(",")),
        date_column=args.date_column,
        asset_column=args.asset_column,
        factor_column=args.factor_column,
    )
    result["input"] = {
        "path": str(Path(args.input).resolve()),
        "sha256": hashlib.sha256(Path(args.input).read_bytes()).hexdigest(),
        "columns_read": selected,
    }
    target = Path(args.output)
    payload = json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    with os.fdopen(
        os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644), "w", encoding="utf-8"
    ) as output:
        output.write(payload)


if __name__ == "__main__":
    main()
