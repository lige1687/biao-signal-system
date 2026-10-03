"""Research-only shape candidates using native STUMPY; no financial qualification.

JSON inputs have exactly asset, dates (ISO quotation dates), and close (positive
prices or null). Missing quotation rows must be supplied as null by the caller;
this tool cannot verify a vendor calendar or historical availability.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path

import numpy as np

SCHEMA = "shape-candidates/1.0"


def _digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def _engine():
    try:
        import stumpy
    except ImportError as exc:
        raise RuntimeError("STUMPY1.14.1 and its dependencies are required; use the recorded isolated environment") from exc
    if importlib.metadata.version("stumpy") != "1.14.1":
        raise RuntimeError("This adapter was checked with STUMPY1.14.1 only")
    return stumpy


def _input(data):
    if set(data) != {"asset", "dates", "close"}:
        raise ValueError("Input must contain only asset, dates, close; no outcome columns")
    if not isinstance(data["asset"], str) or not data["asset"]:
        raise ValueError("asset must identify one series")
    dates = data["dates"]
    if not isinstance(dates, list) or not dates:
        raise ValueError("dates must be a nonempty list")
    if any(not isinstance(d, str) or date.fromisoformat(d).isoformat() != d for d in dates):
        raise ValueError("dates must be ISO dates")
    if dates != sorted(set(dates)):
        raise ValueError("dates must be strictly increasing, without duplicates")
    prices = data["close"]
    if not isinstance(prices, list) or len(prices) != len(dates):
        raise ValueError("prices and dates must align")
    for value in prices:
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                                  or not math.isfinite(value) or value <= 0):
            raise ValueError("close must be positive finite values or null")
    x = np.array([np.nan if v is None else math.log(v) for v in prices], dtype=np.float64)
    return dates, x


def _valid_windows(x, window):
    if len(x) < window:
        return np.zeros(0, dtype=bool)
    view = np.lib.stride_tricks.sliding_window_view(x, window)
    return np.isfinite(view).all(axis=1) & (np.ptp(view, axis=1) > 1e-12)


def discover(data: dict, discovery_end: str, window: int = 20,
             max_candidates: int = 3) -> dict:
    """Freeze at most three native motif representatives from an earlier prefix."""
    dates, x = _input(data)
    if isinstance(window, bool) or not isinstance(window, int) or window < 3:
        raise ValueError("window must be an integer >= 3")
    if isinstance(max_candidates, bool) or not isinstance(max_candidates, int) or not 1 <= max_candidates <= 3:
        raise ValueError("max_candidates must be 1..3")
    if discovery_end not in dates:
        raise ValueError("discovery_end must be an actual input date")
    count = dates.index(discovery_end) + 1
    x = x[:count].copy()
    dates = dates[:count]
    if count < 2 * window:
        raise ValueError("Need at least two full windows before discovery_end")
    valid = _valid_windows(x, window)
    engine = _engine()
    cutoff = 0.5 * math.sqrt(window)
    candidates = []
    rejected = []
    used = []
    native_groups = 0
    if valid.sum() >= 2:
        profile = engine.stump(x, m=window)[:, 0].astype(float)
        profile[~valid] = np.inf
        distances, indices = engine.motifs(
            x, profile, min_neighbors=1, max_distance=cutoff, cutoff=cutoff,
            max_matches=count, max_motifs=max_candidates)
        native_groups = sum(len(row) > 0 for row in indices)
        for group, (drow, irow) in enumerate(zip(distances, indices)):
            if len(irow) == 0:
                continue  # Native no-match result has shape (1, 0).
            native_anchor = int(irow[0])
            if native_anchor < 0 or any(abs(native_anchor - old) < window for old in used):
                rejected.append({"native_group": group, "reason": "representative overlaps a previously kept occurrence"})
                continue
            starts = []
            selected_distances = []
            for distance, start in zip(drow, irow):
                start = int(start)
                if start < 0 or not math.isfinite(float(distance)) or not valid[start]:
                    continue
                if any(abs(start - old) < window for old in starts + used):
                    continue
                starts.append(start)
                selected_distances.append(float(distance))
            if len(starts) < 2:
                rejected.append({"native_group": group, "reason": "fewer than two nonoverlapping occurrences"})
                continue
            anchor = starts[0]
            template = x[anchor:anchor + window].tolist()
            duplicate = False
            for old in candidates:
                d = float(engine.mass(np.array(old["template"], dtype=float), np.array(template, dtype=float))[0])
                if d <= 1e-8:
                    duplicate = True
            if duplicate:
                rejected.append({"native_group": group, "reason": "same normalized template"})
                continue
            used.extend(starts)
            candidates.append({"candidate_id": f"shape_{len(candidates)+1}",
                               "status": "research_unqualified", "template": template,
                               "template_dates": dates[anchor:anchor + window],
                               "occurrences": [{"start": start, "start_date": dates[start],
                                                "end_date": dates[start+window-1], "native_distance": d}
                                               for start, d in zip(starts, selected_distances)]})
    prefix = {"asset": data["asset"], "dates": dates, "close": data["close"][:count]}
    result = {"schema": SCHEMA, "status": "research_unqualified", "asset": data["asset"],
              "discovery_start": dates[0], "discovery_end": discovery_end,
              "window": window, "max_candidates": max_candidates,
              "geometry_cutoff": cutoff, "representation": "z-normalized log-close; amplitude discarded",
              "training_input_sha256": _digest(prefix),
              "engine": {name: importlib.metadata.version(name) for name in ["stumpy", "numba", "llvmlite", "numpy", "scipy"]},
              "coverage": {"rows": count, "valid_windows": int(valid.sum()),
                           "native_groups": native_groups, "kept_candidates": len(candidates)},
              "rejected_native_groups": rejected, "candidates": candidates,
              "calendar_and_historical_availability": "not certified by this tool"}
    result["library_sha256"] = _digest(result)
    return result


def apply_library(data: dict, library: dict) -> dict:
    """Distances use a fixed library and windows ending no later than each date."""
    dates, x = _input(data)
    content = {k: v for k, v in library.items() if k != "library_sha256"}
    if library.get("schema") != SCHEMA or _digest(content) != library.get("library_sha256"):
        raise ValueError("Invalid or altered frozen library")
    if data["asset"] != library["asset"]:
        raise ValueError("Input asset differs from frozen library")
    window = library["window"]
    if len(library["candidates"]) > 3 or any(len(c["template"]) != window for c in library["candidates"]):
        raise ValueError("Invalid candidate lengths")
    # When the original training prefix is included, detect source revisions too.
    if dates[0] == library["discovery_start"] and library["discovery_end"] in dates:
        count = dates.index(library["discovery_end"]) + 1
        prefix = {"asset": data["asset"], "dates": dates[:count], "close": data["close"][:count]}
        if _digest(prefix) != library["training_input_sha256"]:
            raise ValueError("Training source prefix differs from frozen discovery")
    valid = _valid_windows(x, window)
    rows = []
    for end, d in enumerate(dates):
        row = {"date": d, "distances": {}}
        start = end - window + 1
        for c in library["candidates"]:
            value = None
            if d > library["discovery_end"] and start >= 0 and valid[start]:
                # Per-window native call excludes the future computationally too:
                # a full-series FFT can introduce future-dependent rounding.
                native = _engine().mass(np.array(c["template"], dtype=float), x[start:end+1])
                distance = float(native[0])
                if math.isfinite(distance):
                    value = distance
            row["distances"][c["candidate_id"]] = value
        rows.append(row)
    return {"schema": "shape-observations/1.0", "status": "research_unqualified",
            "asset": data["asset"], "library_sha256": library["library_sha256"],
            "input_sha256": _digest(data), "rows": rows,
            "meaning": "Lower distance means similar normalized past shape; no return or trading interpretation"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["discover", "apply"])
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--discovery-end")
    parser.add_argument("--library", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; refusing to overwrite evidence")
    data = json.loads(args.input.read_text())
    if args.mode == "discover":
        if not args.discovery_end:
            parser.error("discover requires --discovery-end")
        result = discover(data, args.discovery_end)
        filename = "library.json"
    else:
        if not args.library:
            parser.error("apply requires --library")
        result = apply_library(data, json.loads(args.library.read_text()))
        filename = "observations.json"
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / filename).write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"output": str(args.output / filename), "status": result["status"]}))


if __name__ == "__main__":
    main()
