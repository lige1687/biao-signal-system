"""Derived indicators for fixed-member market observation packets.

Rows use each market's supplied trading calendar. The producer must preserve
sessions with missing values as null rows and join source data by date.
"""

from __future__ import annotations

import argparse
from bisect import bisect_left, bisect_right
from datetime import date, datetime, timezone
import json
from math import isfinite, sqrt
from pathlib import Path
from statistics import fmean, stdev
from tempfile import NamedTemporaryFile

RULES = {
    "window": 252,
    "min_samples": 60,
    "high_disp": 60,
    "extreme_disp": 70,
    "low_disp": 40,
    "healthy_breadth": 50,
    "thin_breadth": 35,
    "broad_breadth": 65,
    "panic_breadth": 20,
    "high_rv": 70,
    "divergence_days": 5,
}
_CARD_IDS = {
    "cn-current-members-daily-dispersion",
    "us-current-members-daily-dispersion",
}
_SOURCE_KEYS = ("members", "breadth", "index", "sectors")
_VALUE_FIELDS = (
    "disp_raw",
    "index_close",
    "pct_above_ma20",
    "pct_above_ma60",
    "sector_disp_raw",
)


def _validate_points(points: object) -> None:
    if not isinstance(points, list):
        raise ValueError("points must be a list")
    previous = ""
    for point in points:
        if not isinstance(point, dict):
            raise ValueError("each point must be an object")
        day = point.get("date")
        try:
            if not isinstance(day, str) or date.fromisoformat(day).isoformat() != day:
                raise ValueError
        except ValueError:
            raise ValueError(f"date must be YYYY-MM-DD: {day!r}") from None
        if day <= previous:
            raise ValueError(f"date must be unique and increasing: {day}")
        previous = day
        for field in _VALUE_FIELDS:
            if field not in point:
                raise ValueError(f"{day} missing {field}; use null for a missing observation")
            value = point[field]
            if value is None:
                continue
            if type(value) not in (int, float) or not isfinite(value) or value < 0:
                raise ValueError(f"{day} invalid {field}: {value!r}")
            if field == "index_close" and value == 0:
                raise ValueError(f"{day} index_close must be positive")
            if field in ("pct_above_ma20", "pct_above_ma60") and value > 100:
                raise ValueError(f"{day} {field} must be between 0 and 100")


def _strict_window(series: list, end: int, length: int) -> list | None:
    start = end + 1 - length
    if start < 0:
        return None
    window = series[start:end + 1]
    return None if None in window else window


def _rolling_mean(series: list, end: int, length: int) -> float | None:
    window = _strict_window(series, end, length)
    return fmean(window) if window is not None else None


def _index_rv(series: list, end: int) -> float | None:
    window = _strict_window(series, end, 21)
    if window is None:
        return None
    returns = [current / previous - 1 for previous, current in zip(window, window[1:])]
    return stdev(returns) * sqrt(252) * 100


def _reference(series: list, end: int) -> list:
    start = max(0, end - RULES["window"])
    return sorted(value for value in series[start:end] if value is not None)


def _percentile(value: float | None, reference: list) -> float | None:
    if value is None or len(reference) < RULES["min_samples"]:
        return None
    left = bisect_left(reference, value)
    right = bisect_right(reference, value)
    return 50 * (left + right) / len(reference)


def _quantile(reference: list, fraction: float) -> float | None:
    if len(reference) < RULES["min_samples"]:
        return None
    position = (len(reference) - 1) * fraction
    lower = int(position)
    return reference[lower] + (reference[lower + 1] - reference[lower]) * (position - lower)


def _breadth_divergence(breadth: list, closes: list, end: int) -> bool | None:
    length = RULES["divergence_days"] + 1
    breadth_window = _strict_window(breadth, end, length)
    close_window = _strict_window(closes, end, length)
    if breadth_window is None or close_window is None:
        return None
    return close_window[-1] >= close_window[0] and all(
        current < previous for previous, current in zip(breadth_window, breadth_window[1:])
    )


def _high_disp_low_breadth(disp: float | None, breadth: float | None) -> bool | None:
    if disp is None or breadth is None:
        return None
    return disp >= RULES["extreme_disp"] and breadth < RULES["thin_breadth"]


def _diagnose(
    disp: float | None, breadth: float | None, rv: float | None, divergence: bool | None
) -> str | None:
    if disp is None or breadth is None or rv is None:
        return None
    if disp <= RULES["low_disp"] and breadth <= RULES["panic_breadth"] and rv >= RULES["high_rv"]:
        return "PANIC"
    if disp >= RULES["extreme_disp"] and rv >= RULES["high_rv"]:
        return "VOLATILE_DISAGREEMENT"
    if _high_disp_low_breadth(disp, breadth) or divergence:
        return "SIPHON_WARNING"
    if disp >= RULES["high_disp"] and breadth >= RULES["healthy_breadth"] and rv < RULES["high_rv"]:
        return "HEALTHY_ROTATION"
    if disp <= RULES["low_disp"] and breadth >= RULES["broad_breadth"]:
        return "BROAD_TREND"
    return "BALANCED"


def _derive_points(points: list[dict]) -> list[dict]:
    dispersion = [point["disp_raw"] for point in points]
    dispersion_ma5 = [_rolling_mean(dispersion, end, 5) for end in range(len(points))]
    closes = [point["index_close"] for point in points]
    breadth = [point["pct_above_ma20"] for point in points]
    sector_ratios = [
        point["sector_disp_raw"] / disp
        if disp and point["sector_disp_raw"] is not None else None
        for point, disp in zip(points, dispersion)
    ]
    ratios_ma5 = [_rolling_mean(sector_ratios, end, 5) for end in range(len(points))]
    rv20 = [_index_rv(closes, end) for end in range(len(points))]

    derived = []
    for end, point in enumerate(points):
        disp_ref = _reference(dispersion_ma5, end)
        rv_ref = _reference(rv20, end)
        disp_pct = _percentile(dispersion_ma5[end], disp_ref)
        rv_pct = _percentile(rv20[end], rv_ref)
        b20 = breadth[end]
        divergence = _breadth_divergence(breadth, closes, end)
        derived.append({
            **point,
            "disp_ma5": dispersion_ma5[end],
            "disp_ma20": _rolling_mean(dispersion, end, 20),
            "disp_pct_252d": disp_pct,
            "disp_p20": _quantile(disp_ref, 0.20),
            "disp_p50": _quantile(disp_ref, 0.50),
            "disp_p80": _quantile(disp_ref, 0.80),
            "disp_sample_count": len(disp_ref),
            "index_rv20": rv20[end],
            "rv20_pct_252d": rv_pct,
            "rv_sample_count": len(rv_ref),
            "sector_dominance_ratio": ratios_ma5[end],
            "sector_dominance_pct": _percentile(ratios_ma5[end], _reference(ratios_ma5, end)),
            "high_disp_low_breadth": _high_disp_low_breadth(disp_pct, b20),
            "breadth_divergence": divergence,
            "regime_diagnosis": _diagnose(disp_pct, b20, rv_pct, divergence),
        })
    return derived


def build_member_dispersion(packet: dict) -> dict:
    """Build a new version-1 observation packet without mutating the input."""
    if not isinstance(packet, dict) or type(packet.get("schemaVersion")) is not int or packet["schemaVersion"] != 1:
        raise ValueError("schemaVersion must be 1")
    raw_cards = packet.get("cards")
    if not isinstance(raw_cards, list):
        raise ValueError("cards must be a list")
    seen = set()
    cards = []
    for card in raw_cards:
        if not isinstance(card, dict):
            raise ValueError("each card must be an object")
        card_id = card.get("id")
        if not isinstance(card_id, str) or card_id not in _CARD_IDS or card_id in seen:
            raise ValueError(f"invalid or duplicate card id: {card_id!r}")
        seen.add(card_id)
        sources = card.get("sources")
        if not isinstance(sources, dict) or any(
            not isinstance(sources.get(key), str) or not sources[key].strip()
            for key in _SOURCE_KEYS
        ):
            raise ValueError(f"{card_id} sources must name members, breadth, index and sectors")
        points = card.get("points")
        _validate_points(points)
        cards.append({**card, "points": _derive_points(points)})
    return {
        **packet,
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rules": RULES.copy(),
        "cards": cards,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path, help="JSON path. Defaults to stdout.")
    args = parser.parse_args()
    packet = json.loads(args.input.read_text(encoding="utf-8"))
    payload = json.dumps(build_member_dispersion(packet), ensure_ascii=False, allow_nan=False)
    if args.output is None:
        print(payload)
        return
    with NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=args.output.parent, delete=False
    ) as stream:
        temporary_path = Path(stream.name)
        try:
            stream.write(payload + "\n")
            stream.close()
            temporary_path.replace(args.output)
        finally:
            temporary_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
