"""Deterministic display metrics from the frozen factor curve library.

This module only summarizes catalog-pinned files. It never constructs trades or
fills missing observations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from collections import defaultdict
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOG = Path("web/public/research/factor-curve-library-20261022/catalog.json")
DEFAULT_OUTPUT = Path("web/public/research/factor-workbench-20261024/metrics.json")


def _finite(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _month(value: str) -> int:
    try:
        year, month = map(int, value[:7].split("-"))
        date(year, month, 1)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid month: {value!r}") from exc
    return year * 12 + month


def _unique_months(points: list, *, date_index: int = 0) -> None:
    seen: set[int] = set()
    for point in points:
        month = _month(point[date_index])
        if month in seen:
            raise ValueError(f"duplicate month: {point[date_index]}")
        seen.add(month)


def _metric(values: list[float], *, annualize: bool = False) -> tuple[float | None, float | None, str | None]:
    if len(values) < 2:
        return None, None, "fewer_than_two_finite_months"
    sd = statistics.stdev(values)
    if sd == 0:
        return None, 0.0, "zero_sample_standard_deviation"
    mean = statistics.mean(values)
    return mean / sd * (math.sqrt(12) if annualize else 1), sd, None


def _rolling(points: list[tuple[str, float | None]], *, annualize: bool) -> list[list]:
    out: list[list] = []
    for end in range(len(points)):
        window = points[max(0, end - 11) : end + 1]
        valid = len(window) == 12 and all(
            _finite(value) for _, value in window
        ) and all(_month(window[i][0]) == _month(window[i - 1][0]) + 1 for i in range(1, 12))
        if valid:
            values = [value for _, value in window]
            ratio, _, _ = _metric(values, annualize=annualize)
            out.append([points[end][0], statistics.mean(values) if not annualize else ratio,
                        ratio if not annualize else None])
        else:
            out.append([points[end][0], None, None])
    return out


def _read_pinned(root: Path, url: str, sha256: str, sources: dict[str, str]) -> dict:
    if not url.startswith("/research/"):
        raise ValueError(f"unapproved source URL: {url}")
    path = Path("web/public") / url.lstrip("/")
    research_root = (root / "web/public/research").resolve()
    if not (root / path).resolve().is_relative_to(research_root):
        raise ValueError(f"source path escapes research directory: {url}")
    data = (root / path).read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != sha256:
        raise ValueError(f"source hash mismatch: {path}: expected {sha256}, got {actual}")
    sources[path.as_posix()] = actual
    return json.loads(data)


def _ic_record(dataset: dict, item: dict) -> dict:
    points = item["points"]
    _unique_months(points)
    point_months = sorted(_month(point[0]) for point in points)
    expected_months = list(range(_month(item["range"][0]), _month(item["range"][1]) + 1))
    if point_months != expected_months:
        raise ValueError("IC points do not match exact formation range")
    values = [point[1] for point in points if _finite(point[1])]
    if len(values) != item["nPeriods"]:
        raise ValueError("IC valid count does not match source")
    ratio, _, reason = _metric(values)
    series = [(point[0][:7], point[1] if _finite(point[1]) else None) for point in points]
    rolling = _rolling(series, annualize=False)
    source_limitations = item.get("limitations")
    if isinstance(source_limitations, str):
        source_limitations = [source_limitations] if source_limitations else []
    elif source_limitations is None:
        source_limitations = []
    elif not isinstance(source_limitations, list) or any(not isinstance(value, str) for value in source_limitations):
        raise ValueError("IC limitations must be text or a list of text")
    return {
        "datasetId": dataset["id"], "factorId": item["factorId"],
        "poolId": item["poolId"], "periodId": item["periodId"],
        "range": item["range"], "nPeriods": len(values), "mean": statistics.mean(values) if values else None,
        "icir": ratio, "icirReason": reason, "coverage": item.get("coverage"),
        "labelDefinition": item.get("labelDefinition"), "horizon": item.get("horizon"),
        "uncertainty": item.get("uncertainty"), "points": points,
        "rolling": rolling, "limitations": [*source_limitations, *dataset.get("limitations", []),
                                             "均值的不确定区间不代表ICIR的不确定区间。"],
    }


def _ir_record(dataset: dict, period_id: str, period_range: list[str], stream_id: str, monthly: list[dict]) -> dict:
    pool_id, factor_id, group_id, fee = stream_id.split("__")
    if group_id != "G5" or not fee.startswith("fee"):
        raise ValueError(f"unexpected diagnostic stream: {stream_id}")
    fee_bps = int(fee[3:])
    rows = [row for row in monthly if _month(period_range[0]) <= _month(row["month"]) <= _month(period_range[1])]
    _unique_months([[row["month"]] for row in rows])
    verified_excess: dict[str, float | None] = {}
    for row in rows:
        returns = (row.get("return"), row.get("benchmarkReturn"), row.get("excessReturn"))
        if all(_finite(value) for value in returns):
            if not math.isclose(returns[0] - returns[1], returns[2], rel_tol=1e-10, abs_tol=1e-12):
                raise ValueError(f"monthly excess does not equal G5 minus benchmark: {stream_id} {row['month']}")
            verified_excess[row["month"]] = returns[2]
        else:
            verified_excess[row["month"]] = None
    if not rows:
        values = []
        complete = False
    else:
        rows.sort(key=lambda row: row["month"])
        complete = (_month(rows[0]["month"]) == _month(period_range[0]) and
                    _month(rows[-1]["month"]) == _month(period_range[1]) and
                    len(rows) == _month(period_range[1]) - _month(period_range[0]) + 1)
        values = [verified_excess[row["month"]] for row in rows if verified_excess[row["month"]] is not None]
        complete = complete and len(values) == len(rows)
    ratio, sd, reason = _metric(values, annualize=True)
    if not complete:
        ratio, sd, reason = None, None, "missing_or_invalid_month_in_period"
    series = [(row["month"], verified_excess[row["month"]]) for row in rows]
    rolling = _rolling(series, annualize=True)
    unknown = [row.get("unknownMax") for row in rows if _finite(row.get("unknownMax"))]
    return {
        "datasetId": dataset["id"], "factorId": factor_id, "poolId": pool_id,
        "periodId": period_id, "feeBps": fee_bps, "range": period_range,
        "nPeriods": len(values), "ir": ratio, "trackingError": sd,
        "trackingErrorFrequency": "monthly", "irAnnualization": 12,
        "meanExcess": statistics.mean(values) if complete and values else None,
        "reason": reason, "unknownMax": max(unknown) if unknown else None,
        "feeLabel": f"模拟单边费率 {fee_bps} 基点；并非个人实际净收益",
        "points": [[month, value, rolling[i][1]] for i, (month, value) in enumerate(series)],
        "limitations": ["历史报价模拟含未知估值；指标仅供观察，不能当成可执行或个人净收益。",
                        "超额=G5月收益减同池、同费率基准月收益；缺月时整段IR留空。",
                        "乘以√12仅作月度年化近似，月收益若连续相关，IR可能失真。", *dataset.get("limitations", [])],
    }


def _correlations(records: list[dict]) -> list[dict]:
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for record in records:
        grouped[(record["datasetId"], record["poolId"], record["periodId"], record["feeBps"])].append(record)
    result = []
    for (dataset_id, pool_id, period_id, fee_bps), members in sorted(grouped.items()):
        members.sort(key=lambda item: item["factorId"])
        series = [{month: value for month, value in member["returns"]} for member in members]
        matrix, counts = [], []
        for left in series:
            mr, cr = [], []
            for right in series:
                dates = sorted(set(left) & set(right))
                pairs = [(left[d], right[d]) for d in dates if _finite(left[d]) and _finite(right[d])]
                cr.append(len(pairs))
                if len(pairs) < 2 or statistics.stdev(x for x, _ in pairs) == 0 or statistics.stdev(y for _, y in pairs) == 0:
                    mr.append(None)
                else:
                    mr.append(statistics.correlation([x for x, _ in pairs], [y for _, y in pairs]))
            matrix.append(mr); counts.append(cr)
        result.append({"datasetId": dataset_id, "poolId": pool_id, "periodId": period_id,
                       "feeBps": fee_bps, "factorIds": [m["factorId"] for m in members],
                       "matrix": matrix, "counts": counts, "kind": "g5_monthly_return",
                       "limitations": ["仅比较G5账户月收益同涨同跌；不是因子分数、持仓或行业重合度。",
                                       "历史报价模拟含未知估值；并非个人净收益。"]})
    return result


def build_metrics(root: Path = REPO_ROOT) -> dict:
    catalog_bytes = (root / CATALOG).read_bytes()
    catalog = json.loads(catalog_bytes)
    sources = {CATALOG.as_posix(): hashlib.sha256(catalog_bytes).hexdigest()}
    ic_records, ir_records, correlation_inputs = [], [], []
    for dataset in catalog["datasets"]:
        summary = _read_pinned(root, dataset["dataUrl"], dataset["summarySha256"], sources)
        diagnostic = _read_pinned(root, dataset["diagnostics"]["dataUrl"], dataset["diagnostics"]["sha256"], sources)
        assessment = _read_pinned(root, dataset["assessment"]["dataUrl"], dataset["assessment"]["sha256"], sources)
        for item in (diagnostic, assessment):
            if item["datasetId"] != dataset["id"] or item["sourceSummarySha256"] != dataset["summarySha256"]:
                raise ValueError(f"dataset/summary binding mismatch: {dataset['id']}")
        valid_factors = {factor["id"] for factor in dataset["factors"]}
        valid_pools = {pool["id"] for pool in dataset["stockPools"]}
        for item in assessment["rankIC"]:
            if item["factorId"] not in valid_factors or item["poolId"] not in valid_pools or item["periodId"] not in summary["periods"]:
                raise ValueError("IC identity not in catalog")
            if item.get("evaluationRange") != summary["periods"][item["periodId"]]:
                raise ValueError("IC evaluation range does not match frozen period")
            ic_records.append(_ic_record(dataset, item))
        for stream_id, values in diagnostic["series"].items():
            parts = stream_id.split("__")
            if len(parts) != 4 or parts[2] != "G5":
                continue
            if parts[0] not in valid_pools or parts[1] not in valid_factors:
                raise ValueError("diagnostic identity not in catalog")
            if stream_id not in summary["streams"]:
                raise ValueError("diagnostic stream does not match frozen summary")
            for period_id, period_range in summary["periods"].items():
                record = _ir_record(dataset, period_id, period_range, stream_id, values["monthly"])
                ir_records.append(record)
                months = set()
                returns = []
                for row in values["monthly"]:
                    if _month(period_range[0]) <= _month(row["month"]) <= _month(period_range[1]):
                        if row["month"] in months:
                            raise ValueError(f"duplicate month: {row['month']}")
                        months.add(row["month"])
                        returns.append((row["month"], row.get("return")))
                correlation_inputs.append({**record, "returns": returns})
    return {
        "schemaVersion": 1, "generatedAt": catalog["generatedAt"],
        "sources": [{"path": path, "sha256": sha} for path, sha in sorted(sources.items())],
        "methods": {"icir": "逐月RankIC算术均值÷样本标准差；不乘年度系数；至少2个有限值。来源给出的均值不确定区间不是ICIR的不确定区间。",
                    "ir": "G5与同池同费率基准账户逐月收益差的均值÷月度样本标准差×√12；整段有缺月则留空。年化近似未校正连续月份的相关性。",
                    "rolling": "仅连续12个月、全部有值时计算；缺月不跨越。",
                    "correlation": "同数据集、股票池、时期、费率的G5账户月收益两两相关。"},
        "missingCapabilities": ["Pearson IC", "残差alpha", "历史成分行业及前十大持仓重合", "真实账户边际贡献", "多期限IC衰减"],
        "icRecords": ic_records, "irRecords": ir_records,
        "correlations": _correlations(correlation_inputs),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = build_metrics()
    output = (args.output if args.output.is_absolute() else REPO_ROOT / args.output).resolve()
    try:
        data_url = "/" + output.relative_to((REPO_ROOT / "web/public").resolve()).as_posix()
    except ValueError as exc:
        raise ValueError("manifest requires output under web/public") from exc
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(result, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    output.write_bytes(payload)
    manifest = {
        "schemaVersion": 1,
        "dataUrl": data_url,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "sources": result["sources"],
        "generatorVersion": 1,
    }
    (output.parent / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(f"{output}: {len(result['icRecords'])} IC, {len(result['irRecords'])} IR records")


if __name__ == "__main__":
    main()
