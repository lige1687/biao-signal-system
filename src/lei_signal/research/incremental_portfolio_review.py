"""Describe a saved monthly portfolio comparison without generating holdings."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
from pathlib import Path

SCHEMA = "incremental-portfolio-review/1"
ROLES = ("candidate", "baseline", "benchmark")
MAX_MONTHS = 1200
# Finite inputs can still overflow sums, variance and pairwise differences.
MAX_ABS_INPUT = 1e100


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _number(value: object) -> bool:
    return type(value) in (int, float) and abs(value) <= MAX_ABS_INPUT and math.isfinite(value)


def _month(value: object) -> int:
    _require(
        isinstance(value, str) and re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", value),
        "month must be YYYY-MM",
    )
    year, month = map(int, value.split("-"))
    _require(year >= 1, "month year must be at least 0001")
    return year * 12 + month - 1


def _finite(value: float, label: str) -> float:
    _require(math.isfinite(value), f"{label} overflows finite arithmetic")
    return value


def _correlation(left: list[float], right: list[float]) -> float | None:
    if len(left) < 2 or statistics.pstdev(left) == 0 or statistics.pstdev(right) == 0:
        return None
    return _finite(statistics.correlation(left, right), "correlation")


def _performance(values: list[float], benchmark: list[float]) -> dict:
    active = [
        _finite(value - base, "active return")
        for value, base in zip(values, benchmark, strict=True)
    ]
    if not values:
        return {
            "n": 0,
            "mean_monthly_return": None,
            "mean_monthly_active": None,
            "annualized_te": None,
            "ir": None,
        }
    mean_return = _finite(statistics.mean(values), "mean return")
    mean_active = _finite(statistics.mean(active), "mean active return")
    sd = _finite(statistics.stdev(active), "active standard deviation") if len(active) > 1 else None
    te = _finite(sd * math.sqrt(12), "tracking error") if sd is not None else None
    ir = _finite(mean_active / sd * math.sqrt(12), "information ratio") if sd else None
    return {
        "n": len(values),
        "mean_monthly_return": mean_return,
        "mean_monthly_active": mean_active,
        "annualized_te": te,
        "ir": ir,
    }


def _segments(rows: list[dict]) -> list[dict]:
    segments: list[dict] = []
    for row in rows:
        month = row["month"]
        if not segments or _month(month) != _month(segments[-1]["end"]) + 1:
            segments.append({"start": month, "end": month, "months": 1})
        else:
            segments[-1]["end"] = month
            segments[-1]["months"] += 1
    return segments


def review(payload: object) -> dict:
    """Check a declared full calendar and compare paired saved return series.

    Returns use decimal units. A null return is unknown, while zero is observed.
    The source fingerprint and all economic claims remain unverified declarations.
    """
    _require(
        isinstance(payload, dict) and payload.get("schema") == SCHEMA, "unsupported request schema"
    )
    scope = payload.get("scope")
    _require(isinstance(scope, dict), "scope must be an object")
    for key in ("universe_id", "benchmark_id", "currency", "return_basis", "cost_model"):
        _require(
            isinstance(scope.get(key), str) and bool(scope[key].strip()), "missing scope: " + key
        )
    _require(scope.get("frequency") == "monthly", "only monthly inputs supported")
    _require(scope.get("unit") == "decimal_return", "returns must use decimal units")
    _require(
        scope.get("history_status") in ("previously_seen", "unseen_holdout", "forward"),
        "declare history status",
    )
    fingerprint = scope.get("source_artifact_sha256")
    _require(
        isinstance(fingerprint, str) and re.fullmatch(r"[0-9a-f]{64}", fingerprint),
        "invalid source fingerprint",
    )

    rows = payload.get("rows")
    _require(
        isinstance(rows, list) and 1 <= len(rows) <= MAX_MONTHS,
        "provide 1..1200 full-calendar rows",
    )
    previous = None
    for index, row in enumerate(rows):
        where = f"rows[{index}]"
        _require(isinstance(row, dict), f"{where} must be an object")
        month = _month(row.get("month"))
        _require(
            previous is None or month == previous + 1,
            "rows must contain consecutive months including unknowns",
        )
        previous = month
        for role in ROLES:
            item = row.get(role)
            _require(
                isinstance(item, dict) and "gross" in item and "net" in item,
                f"{where}.{role} needs gross and net",
            )
            for basis in ("gross", "net"):
                value = item[basis]
                _require(
                    value is None or (_number(value) and value >= -1),
                    f"invalid {where}.{role}.{basis} long-only return",
                )
            _require(
                item["net"] is None or item["gross"] is not None,
                f"{where}.{role} net without gross",
            )
            if item["net"] is not None:
                _require(
                    item["net"] <= item["gross"] + 1e-12,
                    f"{where}.{role} net exceeds gross under nonnegative-cost convention",
                )
            if "traded_fraction" in item:
                traded = item["traded_fraction"]
                _require(
                    traded is None or (_number(traded) and traded >= 0),
                    f"invalid {where}.{role}.traded_fraction",
                )

    gross_rows = [row for row in rows if all(row[role]["gross"] is not None for role in ROLES)]
    common = [row for row in gross_rows if all(row[role]["net"] is not None for role in ROLES)]
    performance = {}
    for label, selected, basis in (
        ("gross_available", gross_rows, "gross"),
        ("gross_common", common, "gross"),
        ("net_common", common, "net"),
    ):
        benchmark = [row["benchmark"][basis] for row in selected]
        performance[label] = {
            role: _performance([row[role][basis] for row in selected], benchmark) for role in ROLES
        }

    def difference(basis: str) -> float | None:
        return (
            _finite(
                statistics.mean(
                    [
                        _finite(
                            row["candidate"][basis] - row["baseline"][basis], "paired difference"
                        )
                        for row in common
                    ]
                ),
                "mean paired difference",
            )
            if common
            else None
        )

    gross_difference, net_difference = difference("gross"), difference("net")
    cost_effect = _finite(net_difference - gross_difference, "cost difference") if common else None
    candidate = [row["candidate"]["net"] for row in common]
    baseline = [row["baseline"]["net"] for row in common]
    benchmark = [row["benchmark"]["net"] for row in common]
    active_candidate = [
        _finite(value - base, "active candidate")
        for value, base in zip(candidate, benchmark, strict=True)
    ]
    active_baseline = [
        _finite(value - base, "active baseline")
        for value, base in zip(baseline, benchmark, strict=True)
    ]

    traded = [
        row
        for row in common
        if all(_number(row[role].get("traded_fraction")) for role in ("candidate", "baseline"))
    ]
    turnover = {
        "common_months": len(traded),
        "candidate": None,
        "baseline": None,
        "relative_reduction": None,
    }
    if traded:
        for role in ("candidate", "baseline"):
            turnover[role] = _finite(
                statistics.mean([row[role]["traded_fraction"] for row in traded]),
                "mean traded fraction",
            )
        if turnover["baseline"] > 0:
            turnover["relative_reduction"] = _finite(
                1 - turnover["candidate"] / turnover["baseline"], "relative turnover reduction"
            )

    return {
        "schema": "incremental-portfolio-review-result/1",
        "status": "descriptive_comparison_only"
        if len(common) >= 2
        else "insufficient_common_months",
        "scope": scope,
        "calendar_months": len(rows),
        "gross_months": len(gross_rows),
        "common_months": len(common),
        "omitted_months": [row["month"] for row in rows if row not in common],
        "common_segments": _segments(common),
        "performance": performance,
        "increment": {"gross": gross_difference, "net": net_difference, "cost_effect": cost_effect},
        "correlation": {
            "total_net": _correlation(candidate, baseline),
            "active_net": _correlation(active_candidate, active_baseline),
        },
        "traded_fraction": turnover,
        "confidence_interval": None,
        "limitations": [
            "No holdings generation, factor IC, factor-score redundancy, regression alpha, "
            "or PIT validation.",
            "Scope, history status and source fingerprint are declarations; "
            "external artifacts are not verified.",
            "Cost effect is net increment minus gross increment on identical months; "
            "no causal attribution.",
            "Turnover uses only common net months with both traded fractions; "
            "partial metadata is not imputed.",
            "No stitched CAGR or full-period drawdown across missing months.",
            "No efficacy conclusion or production authorization; "
            "no confidence interval is estimated.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True)
    args = parser.parse_args(argv)
    path = Path(args.request)
    _require(path.stat().st_size <= 4 * 1024 * 1024, "request exceeds 4 MiB")
    data = path.read_bytes()
    result = review(json.loads(data))
    result["request_sha256"] = hashlib.sha256(data).hexdigest()
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
