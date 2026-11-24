"""Export the frozen focus-stock observation as a historical display bundle.

This module reads small archived results. It never calculates a trading signal,
extends the series, or imports the original experiment runner.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import date
from pathlib import Path
from typing import Any, Mapping


DEFINITION_ID = "research.observation.focus_amount20_momentum20_top5pct@0.1.0-local"
AS_OF = "2025-12-31"
EXPECTED_ROWS = 2674
SOURCE_DIR = "docs/experiments/raw/focus-stock-momentum-evaluation-2026-10-25"
DAILY_REL = f"{SOURCE_DIR}/core-v1/daily_features.csv"
SUMMARY_REL = f"{SOURCE_DIR}/core-v1/summary.json"
WEEKLY_REL = f"{SOURCE_DIR}/core-v1/weekly_observations.csv"
VERIFICATION_REL = f"{SOURCE_DIR}/verification.json"
EXPECTED_SHA256 = {
    DAILY_REL: "a7977c4f688eeac406bef5e9266c73c8459012a1887df9390a2e1f0a4cbcab5d",
    SUMMARY_REL: "2f06535f408de9f3efb2ca5c09637beaeb2fdd48d461311f744a110c6bd98713",
    WEEKLY_REL: "d9728a8abc3c01b58f81db161d8f1cd27ec6098bceb1d42aac4d4b969a35887f",
}
DAILY_COLUMNS = (
    "date", "qualified_count", "signal_valid", "focus_count", "focus",
    "pool_momentum", "breadth", "concentration", "top1_contribution", "focus_members",
)
TARGET_LABELS = {"CSI300": "沪深300全收益", "CSI1000": "中证1000全收益"}
WEEKLY_COLUMNS = ("target", "date", "signal_valid", "focus", "label", "label_end")
WEEKLY_COUNT = 560
WEEKLY_START = "2015-01-09"
WEEKLY_END = "2025-12-12"
LABEL_END_MAX = "2026-01-13"
CALENDAR_END = "2026-01-15"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _finite(value: Any, label: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}: invalid number") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{label}: nonfinite number")
    return parsed


def _count(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label}: invalid integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}: invalid integer") from exc
    if str(parsed) != str(value) or parsed < 0:
        raise ValueError(f"{label}: invalid integer")
    return parsed


def _date(value: Any) -> str:
    if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
        raise ValueError("invalid date")
    return value


def _validated_paths(repo_root: Path, expected_hashes: Mapping[str, str]) -> tuple[Path, Path, Path]:
    verification = json.loads((repo_root / VERIFICATION_REL).read_text(encoding="utf-8"))
    recorded = verification.get("core_hashes")
    if not isinstance(recorded, dict):
        raise ValueError("verification core hashes missing")
    for relative in (DAILY_REL, SUMMARY_REL, WEEKLY_REL):
        expected = expected_hashes.get(relative)
        if not isinstance(expected, str) or len(expected) != 64:
            raise ValueError(f"expected hash missing: {relative}")
        if recorded.get(Path(relative).name) != expected:
            raise ValueError(f"verification hash differs: {relative}")
        actual = _sha256(repo_root / relative)
        if actual != expected:
            raise ValueError(f"archived source hash differs: {relative}")
    return repo_root / DAILY_REL, repo_root / SUMMARY_REL, repo_root / WEEKLY_REL


def _mapping(csv_path: Path, series: list[dict[str, Any]]) -> dict[str, Any]:
    daily_focus = {row["date"]: row["focus"] for row in series}
    grouped: dict[str, list[dict[str, Any]]] = {target: [] for target in TARGET_LABELS}
    previous: dict[str, str | None] = {target: None for target in TARGET_LABELS}
    seen_weeks: dict[str, set[tuple[int, int]]] = {target: set() for target in TARGET_LABELS}
    with csv_path.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("weekly CSV header missing or duplicated")
        if not set(WEEKLY_COLUMNS) <= set(reader.fieldnames):
            raise ValueError("weekly CSV required column missing")
        for raw in reader:
            if None in raw or any(value is None for value in raw.values()):
                raise ValueError("weekly CSV row has missing or extra cells")
            target = raw["target"]
            if target not in TARGET_LABELS:
                raise ValueError("weekly CSV target invalid")
            day = _date(raw["date"])
            label_end = _date(raw["label_end"])
            if raw["signal_valid"] != "True":
                raise ValueError("weekly CSV invalid signal row")
            if not WEEKLY_START <= day <= WEEKLY_END or not day < label_end <= CALENDAR_END:
                raise ValueError("weekly observation or label date outside frozen window")
            if previous[target] is not None and day <= previous[target]:
                raise ValueError("weekly dates duplicated or unordered")
            previous[target] = day
            iso = date.fromisoformat(day).isocalendar()
            week = (iso.year, iso.week)
            if week in seen_weeks[target]:
                raise ValueError("multiple observations in one calendar week")
            seen_weeks[target].add(week)
            focus = _finite(raw["focus"], "weekly focus")
            forward = _finite(raw["label"], "weekly forward return")
            if day not in daily_focus or focus != daily_focus[day]:
                raise ValueError("weekly focus differs from daily archive")
            grouped[target].append({"date": day, "labelEnd": label_end,
                                    "focus": focus, "forwardReturn": forward})
    for target, points in grouped.items():
        if (len(points) != WEEKLY_COUNT or points[0]["date"] != WEEKLY_START
                or points[-1]["date"] != WEEKLY_END
                or max(point["labelEnd"] for point in points) != LABEL_END_MAX):
            raise ValueError(f"weekly coverage differs from frozen study: {target}")
    first, second = (grouped[target] for target in TARGET_LABELS)
    if [(p["date"], p["focus"], p["labelEnd"]) for p in first] != [
            (p["date"], p["focus"], p["labelEnd"]) for p in second]:
        raise ValueError("weekly targets do not share observation dates and focus values")
    return {
        "horizonSessions": 20,
        "frequency": "weekly",
        "sampleStart": WEEKLY_START,
        "sampleEnd": WEEKLY_END,
        "labelEndMax": LABEL_END_MAX,
        "targets": [{"target": target, "label": TARGET_LABELS[target],
                     "baselineMean": math.fsum(point["forwardReturn"] for point in grouped[target]) / WEEKLY_COUNT,
                     "points": grouped[target]} for target in TARGET_LABELS],
        "us": {"status": "unavailable", "reason": "缺少合格的美股逐股历史范围、每日成交额与复权价格；不能以现今名单或ETF行情代替。"},
    }


def _daily(csv_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    series: list[dict[str, Any]] = []
    latest_members: list[str] = []
    previous: str | None = None
    with csv_path.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("daily CSV header missing or duplicated")
        if not set(DAILY_COLUMNS) <= set(reader.fieldnames):
            raise ValueError("daily CSV required column missing")
        for raw in reader:
            if None in raw or any(value is None for value in raw.values()):
                raise ValueError("daily CSV row has missing or extra cells")
            day = _date(raw["date"])
            if previous is not None and day <= previous:
                raise ValueError("daily dates duplicated or unordered")
            previous = day
            if not "2015-01-01" <= day <= AS_OF:
                raise ValueError("daily date outside historical observation window")
            if raw["signal_valid"] != "True":
                raise ValueError("daily archive contains invalid signal row")
            eligible = _count(raw["qualified_count"], "qualified_count")
            selected = _count(raw["focus_count"], "focus_count")
            if eligible < 100 or selected != math.ceil(eligible * 0.05):
                raise ValueError("daily focus count differs from frozen selection")
            focus = _finite(raw["focus"], "focus")
            pool = _finite(raw["pool_momentum"], "pool_momentum")
            breadth = _finite(raw["breadth"], "breadth")
            concentration = _finite(raw["concentration"], "concentration")
            top1 = _finite(raw["top1_contribution"], "top1_contribution")
            if any(not 0 <= value <= 1 for value in (breadth, concentration, top1)):
                raise ValueError("share outside [0,1]")
            members = json.loads(raw["focus_members"])
            if (not isinstance(members, list) or len(members) != selected
                    or any(not isinstance(code, str) or not code for code in members)
                    or len(set(members)) != selected):
                raise ValueError("focus members malformed")
            latest_members = members
            series.append({"date": day, "focus": focus, "poolMomentum": pool,
                           "breadth": breadth, "concentration": concentration,
                           "qualifiedCount": eligible, "focusCount": selected,
                           "top1Contribution": top1})
    if len(series) != EXPECTED_ROWS or series[-1]["date"] != AS_OF:
        raise ValueError("daily archive coverage differs from frozen study")
    latest = {**series[-1], "members": latest_members,
              "changeFocus": series[-1]["focus"] - series[-2]["focus"] if len(series) > 1 else None}
    return series, latest, latest_members


def _comparisons(summary: Mapping[str, Any]) -> list[dict[str, Any]]:
    predictions = summary.get("prediction")
    if not isinstance(predictions, list):
        raise ValueError("prediction summary missing")
    selected = {}
    for row in predictions:
        if row.get("period") == "2020-2025" and row.get("model") in ("baseline", "baseline_focus_zero"):
            key = (row.get("target"), row.get("model"))
            if key in selected:
                raise ValueError("duplicate comparison summary")
            selected[key] = row
    comparisons = []
    for target in TARGET_LABELS:
        baseline = selected.get((target, "baseline"))
        candidate = selected.get((target, "baseline_focus_zero"))
        if not baseline or not candidate:
            raise ValueError(f"comparison missing: {target}")
        if _count(baseline.get("n"), "baseline n") != 305 or _count(candidate.get("n"), "candidate n") != 305:
            raise ValueError("comparison sample count differs")
        base_mae = _finite(baseline.get("mae"), "baseline MAE")
        zero_mae = _finite(candidate.get("mae"), "candidate MAE")
        gain = _finite(candidate.get("mae_improvement_vs_baseline"), "improvement")
        interval = candidate.get("improvement_95pct")
        if (not isinstance(interval, list) or len(interval) != 2
                or abs((base_mae - zero_mae) - gain) > 1e-12):
            raise ValueError("comparison improvement inconsistent")
        bounds = [_finite(value, "interval") for value in interval]
        if bounds[0] > bounds[1]:
            raise ValueError("comparison interval inverted")
        comparisons.append({"target": target, "label": TARGET_LABELS[target],
                            "baselineMae": base_mae, "withZeroMae": zero_mae,
                            "improvement": gain, "interval": bounds})
    return comparisons


def build_observation_bundle(
    repo_root: Path, *, expected_hashes: Mapping[str, str] = EXPECTED_SHA256,
) -> dict[str, Any]:
    """Validate archived inputs and build a historical-only JSON object."""
    csv_path, summary_path, weekly_path = _validated_paths(repo_root, expected_hashes)
    series, latest, _ = _daily(csv_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    comparisons = _comparisons(summary)
    mapping = _mapping(weekly_path, series)
    return {
        "schemaVersion": 1,
        "definitionId": DEFINITION_ID,
        "label": "焦点股动量",
        "market": "cn",
        "historicalOnly": True,
        "asOf": AS_OF,
        "current": None,
        "scope": {
            "label": "A股固定300股历史样本",
            "sampleSize": 300,
            "selection": "供应商2014-12-31历史名单，排除旧研究600股后于2026年按固定哈希抽取300股；包含后来退出者。",
            "method": "收盘后在合格股票中按近20交易日人民币平均成交额取前5%，等权平均其近20交易日复权价格涨跌。",
            "limitations": [
                "固定300股不是沪深300成分，也不是全A股；遗漏2014年后上市股票。",
                "截至2025-12-31的历史研究资料，不表示今天或近期市场状态。",
                "量化舵原模型未公开完整参数，本序列是独立定义，不能称原式复现。",
                "负值未见稳定预测增量，不是买入、加仓或底部信号。",
                "供应商历史资料的当年到达与修订时间未核，不是实时前向记录。",
            ],
        },
        "series": series,
        "latest": latest,
        "research": {
            "asOf": "2026-10-25", "conclusion": "未见稳定预测增量",
            "reportPath": "docs/experiments/focus-stock-momentum-evaluation-2026-10-25.md",
            "period": "2020—2025", "horizonSessions": 20,
            "comparisons": comparisons,
        },
        "mapping": mapping,
        "source": {"paths": [DAILY_REL, SUMMARY_REL, WEEKLY_REL],
                   "sha256": {key: expected_hashes[key] for key in (DAILY_REL, SUMMARY_REL, WEEKLY_REL)}},
    }


def export_observation_bundle(repo_root: Path, output_path: Path) -> dict[str, Any]:
    """Write only after full validation, using the caller's approved path."""
    bundle = build_observation_bundle(repo_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(bundle, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
                           encoding="utf-8")
    return bundle
