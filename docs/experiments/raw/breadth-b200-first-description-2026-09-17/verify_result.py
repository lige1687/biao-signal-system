#!/usr/bin/env python3
"""独立复算核验：从冻结输入与 run 明细独立推导，不使用被测代码。

硬性边界：
- 不 import ``breadth_description`` / ``breadth_description_contract``；
- 不调用 ``momentum_prototype.rank_diagnostic``；
- 名次相关用本文件内置的平均名次 + 标准算术独立重算；
- 浮点绝对容差 1e-12；整数/键集/null 理由严格一致；多行/少行/重复键都拒绝。

用法：python3 verify_result.py --run <run目录> --inputs <冻结输入目录>
退出码：0 全部一致；1 存在不一致。
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import pandas as pd

TOL = 1e-12
EVAL_START, EVAL_END = "2019-10-08", "2025-12-31"
CAL_START, CAL_END = "2019-09-02", "2026-02-03"
OFF_E, OFF_X = 1, 22
COVERAGE_MIN = 0.9
YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
REASONS = [
    "breadth_row_missing", "breadth_invalid", "breadth_value_missing",
    "target_row_missing", "label_not_mature", "target_missing",
]


def _avg_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        average = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = average
        i = j + 1
    return ranks


def _pearson(a: list[float], b: list[float]) -> float:
    n = len(a)
    mean_a, mean_b = sum(a) / n, sum(b) / n
    cov = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b, strict=False))
    var_a = sum((x - mean_a) ** 2 for x in a)
    var_b = sum((y - mean_b) ** 2 for y in b)
    return cov / ((var_a ** 0.5) * (var_b ** 0.5))


def _spearman(xs: list[float], ys: list[float]):
    n = len(xs)
    if n < 3:
        return n, None, "fewer_than_three_pairs"
    rank_x, rank_y = _avg_ranks(xs), _avg_ranks(ys)
    if len(set(rank_x)) == 1 or len(set(rank_y)) == 1:
        return n, None, "constant_rank"
    return n, _pearson(rank_x, rank_y), None


def _num_or_none(text: str):
    return None if text == "" else float(text)


def _bool_or_fail(text: str, errors: list[str], where: str) -> bool:
    if text == "True":
        return True
    if text == "False":
        return False
    errors.append(f"{where}: boolean 字段非法 {text!r}")
    return False


def _expected_rows(inputs_dir: Path, errors: list[str], eval_start: str, eval_end: str):
    """从冻结输入独立推导：完整轴、逐日端点/单位/目标/排除原因。"""
    cal = json.loads((inputs_dir / "calendar.json").read_text(encoding="utf-8"))
    days = sorted(d for d, rec in cal["days"].items()
                  if rec.get("is_trading_day") and CAL_START <= d <= CAL_END)
    pos = {d: i for i, d in enumerate(days)}
    axis = [d for d in days if eval_start <= d <= eval_end]

    breadth = pd.read_parquet(inputs_dir / "breadth_csi300.parquet")
    if "date" not in breadth.columns:
        breadth = breadth.reset_index()
    breadth["date"] = [pd.Timestamp(v).strftime("%Y-%m-%d") for v in breadth["date"]]
    b_by_day = {str(row.date): row for row in breadth.itertuples(index=False)}

    prices = pd.read_csv(inputs_dir / "prices.csv", dtype={"date": str},
                         keep_default_na=False)
    close = {row.date: float(row.close) for row in prices.itertuples(index=False)}

    obs = pd.read_csv(inputs_dir / "observations.csv", dtype=str, keep_default_na=False)
    o_by_day = {}
    for row in obs.itertuples(index=False):
        main = float(row.main) if row.main != "" else None
        o_by_day[row.session] = (row.e_date, row.x_date, main)

    expected = {}
    for t in axis:
        i = pos[t]
        e = days[i + OFF_E] if i + OFF_E < len(days) else ""
        x = days[i + OFF_X] if i + OFF_X < len(days) else ""
        mature = bool(x) and (pd.Timestamp(x).tz_localize("Asia/Shanghai")
                              + pd.Timedelta(hours=15)) <= pd.Timestamp("2026-09-17T00:00:00+08:00")
        reasons = []
        b = b_by_day.get(t)
        percent = fraction = None
        if b is None:
            reasons.append("breadth_row_missing")
        else:
            if (not bool(b.valid)) or float(b.coverage) < COVERAGE_MIN - 1e-12:
                reasons.append("breadth_invalid")
            raw = float(b.b200)
            if math.isnan(raw):
                reasons.append("breadth_value_missing")
            else:
                percent, fraction = raw, raw / 100.0
        target = recomputed = None
        o = o_by_day.get(t)
        if o is None:
            reasons.append("target_row_missing")
        else:
            if o[0] != e or o[1] != x:
                errors.append(f"input inconsistency: obs endpoint mismatch at {t}")
            elif mature:
                ratio = close[x] / close[e] - 1.0
                recomputed = ratio
                if o[2] is None:
                    reasons.append("target_missing")
                elif abs(o[2] - ratio) > TOL:
                    errors.append(
                        f"input inconsistency: obs main {o[2]!r} vs price ratio {ratio!r} "
                        f"at {t}")
                else:
                    target = ratio  # 完全独立地从冻结价格重算，不复用观察表数值
            else:
                reasons.append("label_not_mature")
        expected[t] = {
            "e_date": e, "x_date": x, "mature": mature, "percent": percent,
            "fraction": fraction, "target": target, "recomputed": recomputed,
            "reasons": reasons,
            "primary": min(reasons, key=REASONS.index) if reasons else "",
            "coverage": None if b is None else float(b.coverage),
            "pool_total": None if b is None else int(b.pool_total),
            "eligible": None if b is None else int(b.eligible),
        }
    return expected, days, pos


def _independent_summary(expected: dict) -> dict:
    clean = [v for v in expected.values() if not v["reasons"]]
    result = {"full": _table(expected, clean)}
    years = {}
    for year in YEARS:
        key = str(year)
        sub_all = {t: v for t, v in expected.items() if t[:4] == key}
        sub_clean = [v for t, v in sub_all.items() if not v["reasons"]]
        years[key] = _table(sub_all, sub_clean)
    result["years"] = years
    return result


def _table(sub_all: dict, sub_clean: list[dict]) -> dict:
    def describe(key: str):
        vals = [v[key] for v in sub_clean if v[key] is not None]
        if not vals:
            return {"mean": None, "median": None, "min": None, "max": None}
        s = sorted(vals)
        n = len(s)
        median = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
        return {"mean": sum(vals) / n, "median": median, "min": s[0], "max": s[-1]}

    targets = [v["target"] for v in sub_clean if v["target"] is not None]
    n, value, reason = _spearman(
        [v["fraction"] for v in sub_clean], targets)
    exclusions = {r: 0 for r in REASONS}
    for v in sub_all.values():
        if v["primary"]:
            exclusions[v["primary"]] += 1
    return {
        "n_all": len(sub_all), "n_included": len(sub_clean), "exclusions": exclusions,
        "breadth_percent": describe("percent"), "breadth_fraction": describe("fraction"),
        "target": describe("target"),
        "target_up_fraction": (sum(1 for t in targets if t > 0) / len(targets))
        if targets else None,
        "rank": {"n": n, "time_series_spearman": value, "reason": reason},
    }


def _independent_overlap(expected: dict, pos: dict) -> dict:
    seg_sets = []
    for t, v in expected.items():
        if v["reasons"]:
            continue
        start = pos[t] + OFF_E
        end = pos[t] + OFF_X
        seg_sets.append(set(range(start, end)))
    histogram = {}
    for prev, cur in zip(seg_sets, seg_sets[1:], strict=False):
        shared = len(prev & cur)
        histogram[shared] = histogram.get(shared, 0) + 1
    union = set()
    for segs in seg_sets:
        union |= segs
    return {
        "included_pairs": len(seg_sets),
        "segments_per_pair": OFF_X - OFF_E,
        "total_interval_references": sum(len(s) for s in seg_sets),
        "unique_intervals": len(union),
        "consecutive_shared_histogram": {str(k): histogram[k]
                                         for k in sorted(histogram, reverse=True)},
    }


def _close(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(float(a) - float(b)) <= TOL


def _compare_summary(expected_summary: dict, actual_summary: dict, errors: list[str]) -> None:
    for scope in ["full", *[str(y) for y in YEARS]]:
        if scope == "full":
            exp = expected_summary["full"]
            act = actual_summary.get("full")
        else:
            exp = expected_summary["years"].get(scope)
            act = actual_summary.get("years", {}).get(scope)
        if act is None or exp is None:
            errors.append(f"summary missing scope {scope}")
            continue
        for key in ("n_all", "n_included"):
            if exp[key] != act.get(key):
                errors.append(f"summary {scope}.{key}: expected {exp[key]} got {act.get(key)}")
        for reason, count in exp["exclusions"].items():
            if act.get("exclusions", {}).get(reason) != count:
                errors.append(
                    f"summary {scope}.exclusions.{reason}: expected {count} "
                    f"got {act.get('exclusions', {}).get(reason)}")
        for stat in ("breadth_percent", "breadth_fraction", "target"):
            for agg in ("mean", "median", "min", "max"):
                if not _close(exp[stat][agg], act.get(stat, {}).get(agg)):
                    errors.append(f"summary {scope}.{stat}.{agg} mismatch: "
                                  f"{exp[stat][agg]} vs {act.get(stat, {}).get(agg)}")
        if not _close(exp["target_up_fraction"], act.get("target_up_fraction")):
            errors.append(f"summary {scope}.target_up_fraction mismatch")
        exp_rank, act_rank = exp["rank"], act.get("rank", {})
        if exp_rank["n"] != act_rank.get("n"):
            errors.append(f"summary {scope}.rank.n: {exp_rank['n']} vs {act_rank.get('n')}")
        if exp_rank["reason"] != act_rank.get("reason"):
            errors.append(
                f"summary {scope}.rank.reason: {exp_rank['reason']} vs {act_rank.get('reason')}")
        if exp_rank["time_series_spearman"] is None:
            if act_rank.get("time_series_spearman") is not None:
                errors.append(f"summary {scope}.rank value should be null")
        elif not _close(exp_rank["time_series_spearman"],
                        act_rank.get("time_series_spearman")):
            errors.append(f"summary {scope}.rank.value mismatch")


def verify_run(run_dir: Path, inputs_dir: Path, *, strict: bool = False) -> dict:
    """strict=True 用于正式 run：缺协议原字节/quality.json 即错误；
    合成夹具核验可用默认宽松模式（这两个文件由 CLI 生成，夹具没有）。"""
    errors: list[str] = []
    checks: list[str] = []
    meta = json.loads((run_dir / "pairs.meta.json").read_text(encoding="utf-8"))
    eval_start = meta.get("evaluation_start")
    eval_end = meta.get("evaluation_end")
    if not eval_start or not eval_end:
        errors.append("pairs.meta.json missing evaluation window")
        return {"ok": False, "errors": errors, "checks": []}
    protocol_path = run_dir / "protocol.source.json"
    if protocol_path.exists():
        # 正式包必须带协议原字节；窗口常量与本核验脚本独立持有的冻结值核对。
        proto = json.loads(protocol_path.read_text(encoding="utf-8"))
        window = proto.get("date_window", {})
        if (window.get("evaluation_start"), window.get("evaluation_end")) != \
                (EVAL_START, EVAL_END):
            errors.append("protocol evaluation window != frozen window")
        if (window.get("calendar_verify_start"), window.get("calendar_verify_end")) != \
                (CAL_START, CAL_END):
            errors.append("protocol calendar verify window != frozen window")
        if (eval_start, eval_end) != (EVAL_START, EVAL_END):
            errors.append("meta evaluation window != frozen window")
        checks.append("protocol.source.json window constants match frozen spec")
    elif strict:
        errors.append("package missing protocol.source.json (required in strict mode)")
    expected, days, pos = _expected_rows(inputs_dir, errors, eval_start, eval_end)

    pairs = pd.read_csv(run_dir / "pairs.csv", dtype=str, keep_default_na=False)
    actual_sessions = list(pairs["session"])
    if len(actual_sessions) != len(set(actual_sessions)):
        errors.append("pairs.csv duplicate session rows")
    seen = set(actual_sessions)
    for t in expected:
        if t not in seen:
            errors.append(f"pairs.csv missing row for session {t}")
    for t in actual_sessions:
        if t not in expected:
            errors.append(f"pairs.csv extra row for session {t}")
    checks.append(f"key set: expected {len(expected)} rows, file has {len(actual_sessions)}")

    col = {name: list(pairs[name]) for name in pairs.columns}
    for idx, t in enumerate(actual_sessions):
        if t not in expected:
            continue
        exp = expected[t]
        where = f"row {t}"
        for key, name in (("e_date", "e_date"), ("x_date", "x_date")):
            if col[name][idx] != exp[key]:
                errors.append(f"{where}: {name} {col[name][idx]!r} != expected {exp[key]!r}")
        mature = _bool_or_fail(col["label_mature"][idx], errors, where)
        if mature != exp["mature"]:
            errors.append(f"{where}: label_mature mismatch")
        included = _bool_or_fail(col["included"][idx], errors, where)
        if included != (not exp["reasons"]):
            errors.append(f"{where}: included mismatch")
        if col["primary_exclusion"][idx] != exp["primary"]:
            errors.append(f"{where}: primary_exclusion mismatch")
        if col["exclusion_reasons"][idx] != "|".join(exp["reasons"]):
            errors.append(f"{where}: exclusion_reasons mismatch")
        if not _close(_num_or_none(col["b200_percent"][idx]), exp["percent"]):
            errors.append(f"{where}: b200_percent mismatch")
        fraction = _num_or_none(col["b200_fraction"][idx])
        if not _close(fraction, exp["fraction"]):
            errors.append(f"{where}: b200_fraction mismatch")
        # 单位核对：比例必须等于百分数/100（抓住改单位）
        if (exp["percent"] is not None and fraction is not None
                and abs(fraction - exp["percent"] / 100.0) > TOL):
            errors.append(f"{where}: unit broken, fraction != percent/100")
        if not _close(_num_or_none(col["target"][idx]), exp["target"]):
            errors.append(f"{where}: target mismatch")
        if not _close(_num_or_none(col["target_recomputed"][idx]), exp["recomputed"]):
            errors.append(f"{where}: target_recomputed mismatch")
        if not _close(_num_or_none(col["coverage"][idx]), exp["coverage"]):
            errors.append(f"{where}: coverage mismatch")
        for key, name in (("pool_total", "pool_total"), ("eligible", "eligible")):
            actual = col[name][idx]
            actual_val = None if actual == "" else int(actual)
            if actual_val != exp[key]:
                errors.append(f"{where}: {name} mismatch")
    checks.append(f"row-level identity/unit/target/exclusion: {len(actual_sessions)} rows checked")

    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    _compare_summary(_independent_summary(expected), summary, errors)
    checks.append("summary full+7years independently recomputed (rank & descriptive stats)")

    actual_overlap = json.loads((run_dir / "overlap.json").read_text(encoding="utf-8"))
    want_overlap = _independent_overlap(expected, pos)
    for key in ("included_pairs", "segments_per_pair", "total_interval_references",
                "unique_intervals"):
        if want_overlap[key] != actual_overlap.get(key):
            errors.append(f"overlap.{key}: {want_overlap[key]} vs {actual_overlap.get(key)}")
    if want_overlap["consecutive_shared_histogram"] != \
            actual_overlap.get("consecutive_shared_histogram"):
        errors.append("overlap.consecutive_shared_histogram mismatch")
    checks.append("overlap recomputed from calendar positions")

    quality_path = run_dir / "quality.json"
    if quality_path.exists():
        quality = json.loads(quality_path.read_text(encoding="utf-8"))
        if quality.get("qualification") != "restricted":
            errors.append("quality.qualification must stay restricted")
        if quality.get("available_at") is not None:
            errors.append("quality.available_at must be null (unknown, not fabricated)")
        if quality.get("historical_availability_verified") is not False:
            errors.append("quality.historical_availability_verified must be false")
        if quality.get("source_price_basis") != "unverified_per_column":
            errors.append("quality.source_price_basis must be unverified_per_column")
        checks.append("quality labels: restricted / unknown availability, not upgraded")
    elif strict:
        errors.append("package missing quality.json (required in strict mode)")

    if meta.get("target", {}).get("offsets") != [OFF_E, OFF_X]:
        errors.append("meta.target.offsets must be [1,22]")
    if meta.get("unit_conversion", {}).get("scale") != 100:
        errors.append("meta.unit_conversion.scale must be 100")
    if meta.get("common_calculate_called") is not False:
        errors.append("meta must state common.calculate was not called")
    checks.append("meta: offsets/units/no-rebuild statements verified")

    return {"ok": not errors, "errors": errors, "checks": checks}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--inputs", required=True)
    parser.add_argument("--strict", action="store_true",
                        help="正式 run 核验：缺协议原字节/quality.json 即失败")
    args = parser.parse_args(argv)
    report = verify_run(Path(args.run), Path(args.inputs), strict=args.strict)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
